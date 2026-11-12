"""Tests of the risk model. Run with: python3 -m unittest discover risk-model/tests"""
import math
import random
import sys
import tempfile
import unittest
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = MODEL_DIR.parent
sys.path.insert(0, str(REPO_DIR))
sys.path.insert(0, str(MODEL_DIR))
sys.path.insert(0, str(REPO_DIR / "engine"))

from schema import toxage_schema  # noqa: E402
import evaluate  # noqa: E402
import fit  # noqa: E402
import generate  # noqa: E402
import glm  # noqa: E402
import metrics  # noqa: E402
import models  # noqa: E402
import score  # noqa: E402

PATIENT = {
    "patient_id": "T1", "tumour_type": "breast", "regimen": "trastuzumab_deruxtecan",
    "age_years": 65, "sex": "female", "ecog": 1, "ga_impaired_domains": 0,
    "renal_function": "normal", "spo2_percent": 98, "lung_comorbidity": False,
    "years_since_diagnosis": 1.0,
}


class ModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = models.load_config()
        cls.model = models.Scorer(cls.cfg)

    def test_regimens_match_schema(self):
        self.assertEqual(
            set(self.cfg["severe_toxicity_90d"]["regimen_rates"]),
            set(toxage_schema.allowed_values("baseline", "regimen")),
        )

    def test_reference_patient_has_regimen_rate(self):
        for regimen, entry in self.cfg["severe_toxicity_90d"]["regimen_rates"].items():
            risk = models.severe_toxicity_risk(dict(PATIENT, regimen=regimen), self.cfg)
            self.assertAlmostEqual(risk, entry["rate"], places=9)

    def test_older_impaired_patient_is_close_to_gap70(self):
        # average GAP70+ participant: 77 years, 4.5 impaired domains, regimen rate 60%
        cfg = {"severe_toxicity_90d": dict(self.cfg["severe_toxicity_90d"],
                                           regimen_rates={"test": {"rate": 0.60}})}
        patient = dict(PATIENT, regimen="test", age_years=77, ga_impaired_domains=4.5)
        self.assertAlmostEqual(models.severe_toxicity_risk(patient, cfg), 0.71, delta=0.05)

    def test_risk_rises_with_each_factor(self):
        base = models.severe_toxicity_risk(PATIENT, self.cfg)
        for change in ({"age_years": 75}, {"ecog": 2}, {"ga_impaired_domains": 2}):
            self.assertGreater(models.severe_toxicity_risk(dict(PATIENT, **change), self.cfg), base)

    def test_ild_mean_risk_in_reference_population_equals_rate(self):
        hr = self.cfg["ild"]["hazard_ratios"]
        ref = self.cfg["ild"]["reference_population"]
        profiles = list(models._reference_profiles(ref))
        self.assertAlmostEqual(sum(s for s, _ in profiles), 1.0, places=9)
        for regimen, entry in self.cfg["ild"]["regimen_rates"].items():
            r0 = models.ild_baseline_risk(regimen, self.cfg)
            mean = sum(s * (1 - (1 - r0) ** math.prod(hr[n]["value"] for n in names))
                       for s, names in profiles)
            self.assertAlmostEqual(mean, entry["rate"], places=6)

    def test_ild_patient_without_factors_has_baseline_risk(self):
        r0 = models.ild_baseline_risk("trastuzumab_deruxtecan", self.cfg)
        self.assertEqual(models.ild_terms(PATIENT, self.cfg), [])
        self.assertAlmostEqual(models.ild_risk(PATIENT, self.cfg), r0, places=12)
        self.assertLess(r0, 0.121)

    def test_ild_hazard_ratios_multiply(self):
        patient = dict(PATIENT, spo2_percent=93, lung_comorbidity=True)
        r0 = models.ild_baseline_risk("trastuzumab_deruxtecan", self.cfg)
        expected = 1 - (1 - r0) ** (2.14 * 1.75)
        self.assertAlmostEqual(models.ild_risk(patient, self.cfg), expected, places=12)

    def test_ild_not_applicable(self):
        record = self.model.score(dict(PATIENT, regimen="olaparib", tumour_type="prostate", sex="male"))
        self.assertFalse(record["ild_applicable"])
        for key in ("ild_risk", "ild_grade2plus_risk", "ild_regimen_rate", "ild_category"):
            self.assertIsNone(record[key])

    def test_score_follows_schema(self):
        self.assertEqual(toxage_schema.errors("risk_score", self.model.score(PATIENT)), [])

    def test_categories(self):
        t = {"intermediate_from": 0.05, "high_from": 0.15}
        self.assertEqual(
            [models.category(r, t) for r in (0.01, 0.05, 0.1, 0.15, 0.5)],
            ["low", "intermediate", "intermediate", "high", "high"],
        )

    def test_explanation_reproduces_risk(self):
        patient = dict(PATIENT, age_years=58, ecog=2, renal_function="mild_decrease",
                       years_since_diagnosis=6.0)
        record = self.model.score(patient)
        info = self.model.explain(patient)
        c1 = info["severe_toxicity_90d"]
        odds = c1["start"]["risk"] / (1 - c1["start"]["risk"])
        odds *= math.prod(f["odds_ratio"] for f in c1["factors"])
        self.assertAlmostEqual(odds / (1 + odds), record["severe_toxicity_90d_risk"], places=12)
        c2 = info["ild"]
        ratio = math.prod(f["hazard_ratio"] for f in c2["factors"])
        self.assertAlmostEqual(1 - (1 - c2["start"]["risk"]) ** ratio, record["ild_risk"], places=12)
        self.assertEqual(len(c2["factors"]), 3)


class GlmAndMetricsTest(unittest.TestCase):
    def simulate(self, link, beta, n=20000, seed=5):
        rng = random.Random(seed)
        x, y = [], []
        for _ in range(n):
            row = [1.0, rng.gauss(0, 1), float(rng.random() < 0.3)]
            eta = sum(b * v for b, v in zip(beta, row))
            p = 1 / (1 + math.exp(-eta)) if link == "logit" else 1 - math.exp(-math.exp(eta))
            x.append(row)
            y.append(int(rng.random() < p))
        return x, y

    def test_logit_fit_recovers_coefficients(self):
        beta = [-0.5, 0.8, 0.6]
        result = glm.fit(*self.simulate("logit", beta), link="logit")
        for est, se, true in zip(result["coefficients"], result["standard_errors"], beta):
            self.assertLess(abs(est - true), 4 * se)

    def test_cloglog_fit_recovers_coefficients(self):
        beta = [-2.5, 0.4, 0.7]
        x, y = self.simulate("cloglog", beta)
        result = glm.fit(x, y, link="cloglog", start=[-2.0, 0.0, 0.0])
        for est, se, true in zip(result["coefficients"], result["standard_errors"], beta):
            self.assertLess(abs(est - true), 4 * se)

    def test_auc(self):
        self.assertEqual(metrics.auc([0.1, 0.2, 0.3, 0.4], [0, 0, 1, 1]), 1.0)
        self.assertEqual(metrics.auc([0.4, 0.3, 0.2, 0.1], [0, 0, 1, 1]), 0.0)
        self.assertEqual(metrics.auc([0.5, 0.5, 0.5, 0.5], [0, 1, 0, 1]), 0.5)
        self.assertAlmostEqual(metrics.auc([0.1, 0.4, 0.35, 0.8], [0, 0, 1, 1]), 0.75)

    def test_brier(self):
        self.assertAlmostEqual(metrics.brier([0.2, 0.8], [0, 1]), 0.04)


class PipelineTest(unittest.TestCase):
    """The models on data of the engine. The engine generates outcomes with a
    richer process than the models assume, so the fit is not expected to be exact."""

    @classmethod
    def setUpClass(cls):
        data = generate.generate(15000, seed=11, validate=False)
        cls.baseline = data["baseline"]
        cls.outcomes = {o["patient_id"]: o for o in data["outcome"]}

    def test_csv_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "baseline.csv"
            toxage_schema.write_csv(path, "baseline", self.baseline[:200])
            self.assertEqual(toxage_schema.read_csv(path, "baseline"), self.baseline[:200])
            scores = score.score_all(self.baseline[:200])
            path = Path(folder) / "risk_score.csv"
            toxage_schema.write_csv(path, "risk_score", scores)
            self.assertEqual(toxage_schema.read_csv(path, "risk_score"), scores)

    def test_literature_model_on_engine_data(self):
        result = evaluate.evaluate(self.baseline, self.outcomes)
        for name in ("severe_toxicity_90d", "ild"):
            self.assertGreater(result[name]["model"]["auc"], result[name]["regimen_only"]["auc"])
        self.assertAlmostEqual(
            result["severe_toxicity_90d"]["model"]["observed_to_expected"], 1.0, delta=0.1)
        # The engine follows patients for 52 weeks, the model predicts 730 days,
        # so fewer events are observed than expected.
        ratio = result["ild"]["model"]["observed_to_expected"]
        self.assertGreater(ratio, 0.6)
        self.assertLess(ratio, 1.05)

    def test_fit_on_engine_data(self):
        cfg = fit.fit(self.baseline, self.outcomes)
        for name, entry in cfg["severe_toxicity_90d"]["odds_ratios"].items():
            self.assertGreater(entry["value"], 1.0, name)
        # The engine uses the published hazard ratios for lung toxicity.
        _, engine_params = generate.load_config()
        engine_hr = engine_params["hazards"]["ild"]["hazard_ratios"]
        for name, entry in cfg["ild"]["hazard_ratios"].items():
            low, high = entry["ci95"]
            se = (math.log(high) - math.log(low)) / (2 * 1.96)
            self.assertLess(abs(math.log(entry["value"]) - math.log(engine_hr[name])), 3.5 * se, name)
        # The fitted configuration works in place of the literature one and
        # describes the data it was fitted on at least as well.
        record = models.Scorer(cfg).score(self.baseline[0])
        self.assertEqual(toxage_schema.errors("risk_score", record), [])
        before = evaluate.evaluate(self.baseline, self.outcomes)
        after = evaluate.evaluate(self.baseline, self.outcomes, cfg)
        for name in ("severe_toxicity_90d", "ild"):
            self.assertLessEqual(after[name]["model"]["brier"], before[name]["model"]["brier"] + 1e-9)


if __name__ == "__main__":
    unittest.main()
