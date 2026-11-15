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
    "years_since_diagnosis": 1.0, "adt_type": None, "prior_cardiovascular_event": False,
    "cardiovascular_disease": False, "arterial_hypertension": False, "diabetes": False,
    "smoking_status": "never", "systolic_bp_mmhg": 125,
    "haemoglobin_g_dl": 12.3, "albumin_g_l": 38, "starting_dose_level": 1.0, "prior_therapy_lines": 0,
    "egfr_ml_min": 80, "white_cells_10e9_l": 7.0, "ast_u_l": 20, "alkaline_phosphatase_u_l": 80,
    "bilirubin_ratio_uln": 0.6, "immunosuppressive_medication": False, "ugt1a1_28_homozygous": False,
    "gcsf_prophylaxis": False,
}
MAN = dict(PATIENT, tumour_type="prostate", regimen="olaparib", sex="male", age_years=71,
           adt_type="gnrh_agonist")


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
        for change in ({"age_years": 75}, {"ecog": 2}, {"ga_impaired_domains": 2},
                       {"haemoglobin_g_dl": 10.0}, {"albumin_g_l": 30}):
            self.assertGreater(models.severe_toxicity_risk(dict(PATIENT, **change), self.cfg), base)
        self.assertLess(models.severe_toxicity_risk(dict(PATIENT, starting_dose_level=0.8), self.cfg), base)
        # Extermann et al. (2012): odds ratio 0.90 per g/dl of haemoglobin, 0.74 per g/dl of albumin.
        odds = lambda r: r / (1 - r)
        ratio = odds(models.severe_toxicity_risk(dict(PATIENT, haemoglobin_g_dl=11.3), self.cfg)) / odds(base)
        self.assertAlmostEqual(ratio, 1 / 0.90, delta=0.005)
        ratio = odds(models.severe_toxicity_risk(dict(PATIENT, albumin_g_l=28), self.cfg)) / odds(base)
        self.assertAlmostEqual(ratio, 1 / 0.74, delta=0.005)

    def test_ild_mean_risk_in_reference_population_equals_rate(self):
        hr = self.cfg["ild"]["hazard_ratios"]
        ref = self.cfg["ild"]["reference_population"]
        profiles = list(models._reference_profiles(ref))
        self.assertAlmostEqual(sum(s for s, _ in profiles), 1.0, places=9)
        for regimen, entry in self.cfg["ild"]["regimen_rates"].items():
            r0 = models.ild_baseline_risk(regimen, self.cfg)
            if not models.ild_uses_factors(regimen, self.cfg):
                self.assertEqual(r0, entry["rate"])
                continue
            mean = sum(s * (1 - (1 - r0) ** math.prod(hr[n]["value"] for n in names))
                       for s, names in profiles)
            self.assertAlmostEqual(mean, entry["rate"], places=6)

    def test_ild_risk_factors_count_only_for_trastuzumab_deruxtecan(self):
        patient = dict(PATIENT, regimen="chemotherapy_single_agent", spo2_percent=93, lung_comorbidity=True)
        self.assertEqual(models.ild_terms(patient, self.cfg), [])
        self.assertAlmostEqual(models.ild_risk(patient, self.cfg), 0.006)

    def test_ild_risk_over_time(self):
        # Median onset on day 129, 87% of the events within 12 months.
        risk = models.ild_risk(PATIENT, self.cfg)
        by_day = lambda day: models.ild_risk_by_day(PATIENT, day, self.cfg)
        self.assertEqual(by_day(0), 0)
        self.assertAlmostEqual(by_day(730), risk)
        self.assertAlmostEqual(by_day(365) / risk, 0.87 / 0.97, delta=0.02)
        self.assertLess(by_day(90), by_day(180))
        remaining = lambda day: models.ild_remaining_risk(PATIENT, day, self.cfg)
        self.assertAlmostEqual(remaining(0), risk)
        self.assertLess(remaining(365), 0.2 * risk)
        self.assertEqual(remaining(730), 0)
        self.assertIsNone(models.ild_risk_by_day(dict(PATIENT, regimen="olaparib"), 100, self.cfg))

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

    def test_cv_mean_risk_in_reference_population_equals_rate(self):
        m = self.cfg["cardiovascular"]
        ref = m["reference_population"]
        for adt, entry in m["adt_rates"].items():
            r0 = models.cv_baseline_risk(adt, self.cfg)
            names = list(models.CV_FACTORS)
            mean = 0.0
            for bits in range(2 ** (len(names) + 1)):
                on = [bool(bits >> i & 1) for i in range(len(names) + 1)]
                share = ref["prior_cardiovascular_event"][adt] if on[0] else 1 - ref["prior_cardiovascular_event"][adt]
                ratio = m["prior_event_hazard_ratios"][adt]["value"] if on[0] else 1.0
                for flag, name in zip(on[1:], names):
                    share *= ref[name] if flag else 1 - ref[name]
                    ratio *= m["hazard_ratios"][name]["value"] if flag else 1.0
                mean += share * (1 - (1 - r0) ** ratio)
            target = models.cv_reference_rate(adt, self.cfg)
            self.assertAlmostEqual(mean, target, places=6)
            # The published rate holds for 48 weeks and counts death from any
            # cause, the model for 52 weeks and cardiovascular events.
            share = m["cardiovascular_share_of_events"]["value"]
            self.assertGreater(target, entry["rate"] * share)
            self.assertLess(target, entry["rate"] * share * 1.1)
            self.assertLess(r0, target)

    def test_cv_man_without_factors_has_baseline_risk(self):
        r0 = models.cv_baseline_risk("gnrh_agonist", self.cfg)
        self.assertEqual([t[0] for t in models.cv_terms(MAN, self.cfg)], ["cv_age"])
        self.assertAlmostEqual(models.cv_risk(MAN, self.cfg), r0, places=12)

    def test_cv_risk_rises_with_each_factor(self):
        base = models.cv_risk(MAN, self.cfg)
        for change in ({"age_years": 80}, {"diabetes": True}, {"arterial_hypertension": True},
                       {"smoking_status": "current"}, {"smoking_status": "former"},
                       {"renal_function": "moderate_severe_decrease"},
                       {"cardiovascular_disease": True}, {"prior_cardiovascular_event": True}):
            self.assertGreater(models.cv_risk(dict(MAN, **change), self.cfg), base, change)
        # Cardiovascular disease counts on its own only without an earlier event.
        self.assertEqual(models.cv_risk(dict(MAN, prior_cardiovascular_event=True), self.cfg),
                         models.cv_risk(dict(MAN, prior_cardiovascular_event=True, cardiovascular_disease=True), self.cfg))

    def test_cv_earlier_event_and_type_of_androgen_deprivation(self):
        # Pooled from HERO and PRONOUNCE: an earlier event raises the hazard by
        # 1.46 under an agonist and by 1.82 under an antagonist.
        risk = lambda **c: models.cv_risk(dict(MAN, **c), self.cfg)
        self.assertLess(risk(adt_type="gnrh_antagonist"), risk())
        self.assertLess(risk(adt_type="gnrh_antagonist", prior_cardiovascular_event=True),
                        risk(prior_cardiovascular_event=True))
        r0 = models.cv_baseline_risk("gnrh_agonist", self.cfg)
        self.assertAlmostEqual(risk(prior_cardiovascular_event=True, diabetes=True),
                               1 - (1 - r0) ** (1.46 * 1.5), places=12)
        r0 = models.cv_baseline_risk("gnrh_antagonist", self.cfg)
        self.assertAlmostEqual(risk(adt_type="gnrh_antagonist", prior_cardiovascular_event=True),
                               1 - (1 - r0) ** 1.82, places=12)
        self.assertAlmostEqual(models.cv_risk_on(MAN, "gnrh_antagonist", self.cfg), risk(adt_type="gnrh_antagonist"))

    def test_neutropenia_mean_risk_in_reference_population_equals_rate(self):
        m = self.cfg["neutropenia"]
        odds, ref = m["odds_ratios"], m["reference_population"]
        for regimen, entry in m["regimen_rates"].items():
            r0 = models.neutropenia_reference_risk(regimen, self.cfg)
            factors = [(entry["prior_chemotherapy_share"], "prior_chemotherapy"),
                       (entry["age_65_or_older_share"], "age_65_or_older"), (entry["gcsf_share"], "gcsf_prophylaxis"),
                       (ref["ast_above_35"], "ast_above_35"),
                       (ref["alkaline_phosphatase_above_120"], "alkaline_phosphatase_above_120"),
                       (ref["bilirubin_above_normal"], "bilirubin_above_normal"),
                       (1.0 if entry.get("corticosteroid") else ref["immunosuppressive_medication"],
                        "immunosuppressive_medication"),
                       (0.1 if entry.get("irinotecan") else 0.0, "ugt1a1_28_homozygous_with_irinotecan")]
            mean = 0.0
            for bits in range(2 ** len(factors)):
                share, logit = 1.0, math.log(r0 / (1 - r0))
                for i, (s, name) in enumerate(factors):
                    on = bits >> i & 1
                    share *= s if on else 1 - s
                    logit += math.log(odds[name]["value"]) if on else 0.0
                mean += share / (1 + math.exp(-logit))
            self.assertAlmostEqual(mean, entry["rate"], places=6, msg=regimen)

    def test_neutropenia_follows_lyman(self):
        patient = dict(PATIENT, regimen="gemcitabine_nab_paclitaxel", age_years=60)
        r0 = models.neutropenia_reference_risk("gemcitabine_nab_paclitaxel", self.cfg)
        self.assertAlmostEqual(models.neutropenia_risk(patient, self.cfg), r0, places=12)
        odds = lambda r: r / (1 - r)
        ratio = lambda **c: odds(models.neutropenia_risk(dict(patient, **c), self.cfg)) / odds(r0)
        self.assertAlmostEqual(ratio(gcsf_prophylaxis=True), 0.12)
        self.assertAlmostEqual(ratio(prior_therapy_lines=2), 1.925)
        self.assertAlmostEqual(ratio(age_years=70), 1.297)
        self.assertAlmostEqual(ratio(ast_u_l=40, alkaline_phosphatase_u_l=130), 1.422 * 1.469)
        self.assertAlmostEqual(ratio(bilirubin_ratio_uln=1.4), 2.152)
        self.assertAlmostEqual(ratio(egfr_ml_min=60), 0.993 ** -20)
        self.assertAlmostEqual(ratio(white_cells_10e9_l=4.0), 0.93 ** -3)
        self.assertAlmostEqual(ratio(immunosuppressive_medication=True), 1.554)
        self.assertAlmostEqual(ratio(starting_dose_level=0.8), 0.496)
        # The genotype counts only on a regimen with irinotecan.
        self.assertAlmostEqual(ratio(ugt1a1_28_homozygous=True), 1.0)
        nalirifox = dict(PATIENT, regimen="nalirifox", age_years=60)
        self.assertGreater(models.neutropenia_risk(dict(nalirifox, ugt1a1_28_homozygous=True), self.cfg),
                           models.neutropenia_risk(nalirifox, self.cfg))
        self.assertIsNone(models.neutropenia_risk(dict(PATIENT, regimen="olaparib"), self.cfg))

    def test_diarrhoea_model(self):
        m = self.cfg["diarrhoea"]
        patient = dict(PATIENT, regimen="nalirifox", age_years=60)
        r0 = models.diarrhoea_reference_risk("nalirifox", self.cfg)
        self.assertAlmostEqual(models.diarrhoea_risk(patient, self.cfg), r0, places=12)
        self.assertLess(r0, m["regimen_rates"]["nalirifox"]["rate"])
        for change in ({"age_years": 72}, {"ecog": 2}, {"albumin_g_l": 30}, {"ugt1a1_28_homozygous": True}):
            self.assertGreater(models.diarrhoea_risk(dict(patient, **change), self.cfg), r0, change)
        self.assertGreater(models.diarrhoea_risk(patient, self.cfg),
                           models.diarrhoea_risk(dict(patient, regimen="gemcitabine_nab_paclitaxel"), self.cfg))
        self.assertIsNone(models.diarrhoea_risk(PATIENT, self.cfg))
        record = self.model.score(PATIENT)
        self.assertFalse(record["diarrhoea_applicable"])
        self.assertTrue(record["neutropenia_applicable"])
        info = self.model.explain(dict(patient, ugt1a1_28_homozygous=True, age_years=75))
        for key in ("neutropenia", "diarrhoea"):
            odds = info[key]["start"]["risk"] / (1 - info[key]["start"]["risk"])
            odds *= math.prod(f["odds_ratio"] for f in info[key]["factors"])
            score = self.model.score(dict(patient, ugt1a1_28_homozygous=True, age_years=75))
            self.assertAlmostEqual(odds / (1 + odds), score[f"{key}_risk"], places=12)

    def test_cv_not_applicable(self):
        record = self.model.score(PATIENT)
        self.assertFalse(record["cv_applicable"])
        for key in ("cv_risk", "cv_reference_rate", "cv_category"):
            self.assertIsNone(record[key])
        self.assertIsNone(models.cv_risk(PATIENT, self.cfg))
        self.assertIsNone(self.model.explain(PATIENT)["cardiovascular"])

    def test_score_follows_schema(self):
        self.assertEqual(toxage_schema.errors("risk_score", self.model.score(PATIENT)), [])
        record = self.model.score(dict(MAN, age_years=85, prior_cardiovascular_event=True, diabetes=True,
                                       arterial_hypertension=True, smoking_status="current"))
        self.assertEqual(toxage_schema.errors("risk_score", record), [])
        self.assertEqual(record["cv_category"], "high")
        self.assertEqual(self.model.score(MAN)["cv_category"], "low")

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
        man = dict(MAN, age_years=78, prior_cardiovascular_event=True, diabetes=True)
        c5 = self.model.explain(man)["cardiovascular"]
        ratio = math.prod(f["hazard_ratio"] for f in c5["factors"])
        self.assertAlmostEqual(1 - (1 - c5["start"]["risk"]) ** ratio, self.model.score(man)["cv_risk"], places=12)
        self.assertEqual(len(c5["factors"]), 3)


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
        data = generate.generate(15000, seed=11, scenarios=["usual_care"], validate=False)
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
        for name in ("severe_toxicity_90d", "ild", "neutropenia", "diarrhoea", "cardiovascular"):
            self.assertGreater(result[name]["model"]["auc"], result[name]["regimen_only"]["auc"], name)
        self.assertGreater(result["cardiovascular"]["model"]["auc"], 0.6)
        self.assertGreater(result["neutropenia"]["model"]["auc"], 0.7)
        for name in ("neutropenia", "diarrhoea"):
            self.assertAlmostEqual(result[name]["model"]["observed_to_expected"], 1.0, delta=0.25, msg=name)
        # The engine adds frailty, former smoking and cardiovascular disease
        # without an event, which the model does not know.
        ratio = result["cardiovascular"]["model"]["observed_to_expected"]
        self.assertGreater(ratio, 0.9)
        self.assertLess(ratio, 1.6)
        self.assertAlmostEqual(
            result["severe_toxicity_90d"]["model"]["observed_to_expected"], 1.0, delta=0.1)
        # Many patients stop therapy before day 730, so the observed rate can
        # lie below the predicted one.
        ratio = result["ild"]["model"]["observed_to_expected"]
        self.assertGreater(ratio, 0.6)
        self.assertLess(ratio, 1.15)

    def test_fit_on_engine_data(self):
        cfg = fit.fit(self.baseline, self.outcomes)
        for name, entry in cfg["severe_toxicity_90d"]["odds_ratios"].items():
            if name != "reduced_starting_dose":
                self.assertGreater(entry["value"], 1.0, name)
        # The engine uses the odds ratios of Lyman et al. (2011) as hazard ratios.
        fitted = cfg["neutropenia"]["odds_ratios"]
        self.assertLess(fitted["gcsf_prophylaxis"]["value"], 0.5)
        # Earlier chemotherapy is the same for all patients of a regimen in the
        # engine, so it cannot be estimated and is part of the regimen's risk.
        self.assertEqual(fitted["prior_chemotherapy"]["value"], 1.0)
        self.assertGreater(fitted["age_65_or_older"]["value"], 1.0)
        self.assertGreater(fitted["ugt1a1_28_homozygous_with_irinotecan"]["value"], 1.2)
        self.assertGreater(cfg["diarrhoea"]["odds_ratios"]["ugt1a1_28_homozygous_with_irinotecan"]["value"], 1.2)
        # The engine uses the published hazard ratios for lung toxicity.
        _, engine_params = generate.load_config()
        engine_hr = engine_params["hazards"]["ild"]["hazard_ratios"]
        for name, entry in cfg["ild"]["hazard_ratios"].items():
            low, high = entry["ci95"]
            se = (math.log(high) - math.log(low)) / (2 * 1.96)
            self.assertLess(abs(math.log(entry["value"]) - math.log(engine_hr[name])), 3.5 * se, name)
        # The engine uses the pooled hazard ratios of HERO and PRONOUNCE for the earlier event.
        engine_cv = engine_params["hazards"]["cardiovascular"]
        entry = cfg["cardiovascular"]["prior_event_hazard_ratios"]["gnrh_agonist"]
        low, high = entry["ci95"]
        se = (math.log(high) - math.log(low)) / (2 * 1.96)
        truth = engine_cv["hazard_ratios"]["prior_event_with_agonist"]
        self.assertLess(abs(math.log(entry["value"]) - math.log(truth)), 3.5 * se)
        for name in ("per_10_years_of_age", "diabetes", "arterial_hypertension", "current_smoker"):
            self.assertGreater(cfg["cardiovascular"]["hazard_ratios"][name]["value"], 1.0, name)
        # The fitted configuration works in place of the literature one and
        # describes the data it was fitted on at least as well.
        record = models.Scorer(cfg).score(self.baseline[0])
        self.assertEqual(toxage_schema.errors("risk_score", record), [])
        before = evaluate.evaluate(self.baseline, self.outcomes)
        after = evaluate.evaluate(self.baseline, self.outcomes, cfg)
        for name in ("severe_toxicity_90d", "ild", "neutropenia", "diarrhoea", "cardiovascular"):
            self.assertLessEqual(after[name]["model"]["brier"], before[name]["model"]["brier"] + 1e-9, name)


class ReviewFixesTest(unittest.TestCase):
    """Fixes of the code review (project/code-review-issues.md)."""

    def test_baseline_risk_with_protective_factors(self):
        # Half of the population has a hazard ratio of 0.5: r0 must lie above the target.
        profiles = [(0.5, 1.0), (0.5, 0.5)]
        r0 = models.solve_baseline_risk(profiles, 0.2)
        self.assertGreater(r0, 0.2)
        mean = sum(share * (1 - (1 - r0) ** ratio) for share, ratio in profiles)
        self.assertAlmostEqual(mean, 0.2, places=9)

    def test_fit_says_whether_it_converged(self):
        x = [[1.0, v] for v in (0, 0, 0, 1, 1, 1, 2, 2, 2)]
        y = [0, 0, 1, 0, 1, 1, 0, 1, 1]
        self.assertTrue(glm.fit(x, y)["converged"])
        self.assertFalse(glm.fit(x, y, max_iter=1)["converged"])
        # Separated data (all 0 at x = 0, all 1 at x = 2): the slope grows without end.
        separated = glm.fit([[1.0, v] for v in (0, 0, 1, 1, 2, 2)], [0, 0, 1, 0, 1, 1])
        self.assertFalse(separated["converged"])


if __name__ == "__main__":
    unittest.main()
