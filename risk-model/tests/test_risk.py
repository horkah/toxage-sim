"""Tests of the risk model interface. Run with: python3 -m unittest discover risk-model/tests"""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import models as calc  # noqa: E402
import toxage_risk  # noqa: E402
from engine import generate  # noqa: E402
from schema import toxage_schema  # noqa: E402


class ModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = generate.generate(600, seed=2, scenarios=["usual_care"], validate=False)["baseline"]
        cls.cfg = calc.load_config()
        cls.models = {m.id: m for m in toxage_risk.load()}

    def patient(self, **changes):
        return dict(self.baseline[0], **changes)

    def test_all_registered_models_are_loaded_with_unique_ids(self):
        self.assertEqual(len(self.models), len(toxage_risk.MODELS))

    def test_describe_names_an_outcome_field(self):
        outcome_fields = set(toxage_schema.fields("outcome"))
        for model in self.models.values():
            info = model.describe()
            self.assertIn(info["outcome"], outcome_fields)
            self.assertIn(info["onset"], outcome_fields)
            self.assertGreater(info["window_days"], 0)

    def test_risks_are_probabilities(self):
        for model in self.models.values():
            for p in self.baseline:
                r = model.risk(p)
                self.assertEqual(r is None, not model.applies(p))
                if r is not None:
                    self.assertTrue(0 < r < 1)

    def test_models_equal_the_calculations(self):
        for p in self.baseline[:100]:
            self.assertEqual(self.models["severe90"].risk(p), calc.severe_toxicity_risk(p, self.cfg))
            self.assertEqual(self.models["ild"].risk(p), calc.ild_risk(p, self.cfg))
            self.assertEqual(self.models["cv"].risk(p), calc.cv_risk(p, self.cfg))

    def test_models_equal_the_score_table(self):
        scorer = calc.Scorer(self.cfg)
        for p in self.baseline[:100]:
            record = scorer.score(p)
            self.assertEqual(self.models["severe90"].risk(p), record["severe_toxicity_90d_risk"])
            self.assertEqual(self.models["ild"].risk(p), record["ild_risk"])
            self.assertEqual(self.models["cv"].risk(p), record["cv_risk"])

    def test_reference_patient_has_reference_risk(self):
        model = self.models["severe90"]
        p = self.patient(regimen="olaparib", age_years=65, ecog=0, ga_impaired_domains=0)
        self.assertAlmostEqual(model.risk(p), model.reference_risk(p))
        self.assertTrue(all(f.ratio == 1 for f in model.factors(p)))

    def test_factors_reproduce_the_risk(self):
        p = self.patient(regimen="trastuzumab_deruxtecan", age_years=58, ecog=2,
                         ga_impaired_domains=None, renal_function="mild_decrease",
                         years_since_diagnosis=6.0, spo2_percent=93, lung_comorbidity=False)
        severe = self.models["severe90"]
        odds = severe.reference_risk(p) / (1 - severe.reference_risk(p))
        odds *= math.prod(f.ratio for f in severe.factors(p))
        self.assertAlmostEqual(odds / (1 + odds), severe.risk(p), places=12)
        self.assertEqual([f.name for f in severe.factors(p)],
                         ["age", "ecog_2_or_higher", "ga_impaired_domains"])
        ild = self.models["ild"]
        ratio = math.prod(f.ratio for f in ild.factors(p))
        self.assertAlmostEqual(1 - (1 - ild.reference_risk(p)) ** ratio, ild.risk(p), places=12)
        self.assertEqual(len(ild.factors(p)), len(calc.ILD_FACTORS))
        self.assertEqual(sum(f.ratio != 1 for f in ild.factors(p)), 4)

    def test_cardiovascular_model(self):
        model = self.models["cv"]
        p = self.patient(tumour_type="prostate", regimen="olaparib", sex="male", adt_type="gnrh_agonist",
                         age_years=79, prior_cardiovascular_event=True, cardiovascular_disease=True,
                         diabetes=True, arterial_hypertension=False, smoking_status="former",
                         renal_function="normal")
        ratio = math.prod(f.ratio for f in model.factors(p))
        self.assertAlmostEqual(1 - (1 - model.reference_risk(p)) ** ratio, model.risk(p), places=12)
        self.assertEqual([f.name for f in model.factors(p)], list(calc.CV_LABELS))
        self.assertEqual(sum(f.ratio != 1 for f in model.factors(p)), 3)
        self.assertEqual(model.describe()["outcome"], "cv_event_1y")
        self.assertEqual(model.window_days, 364)
        other = self.patient(adt_type=None)
        self.assertFalse(model.applies(other))
        self.assertIsNone(model.risk(other))
        self.assertIsNone(model.reference_risk(other))
        self.assertEqual(model.factors(other), [])
        applies = [model.applies(q) for q in self.baseline]
        self.assertEqual(applies, [q["tumour_type"] == "prostate" for q in self.baseline])

    def test_lung_model_applies_only_to_regimens_with_a_rate(self):
        model = self.models["ild"]
        self.assertFalse(model.applies(self.patient(regimen="nalirifox")))
        self.assertIsNone(model.risk(self.patient(regimen="nalirifox")))
        self.assertIsNone(model.reference_risk(self.patient(regimen="nalirifox")))
        self.assertEqual(model.factors(self.patient(regimen="nalirifox")), [])
        self.assertTrue(model.applies(self.patient(regimen="trastuzumab_deruxtecan")))

    def test_other_configuration(self):
        cfg = calc.load_config()
        cfg["severe_toxicity_90d"]["odds_ratios"]["ecog_2_or_higher"]["value"] = 3.0
        model = toxage_risk.load(cfg)[0]
        factors = {f.name: f.ratio for f in model.factors(self.patient(ecog=2))}
        self.assertEqual(factors["ecog_2_or_higher"], 3.0)

    def test_factors_have_labels(self):
        p = self.patient(regimen="trastuzumab_deruxtecan")
        for model in self.models.values():
            for f in model.factors(p):
                self.assertNotEqual(f.label, f.name)

    def test_base_class_is_abstract(self):
        model = toxage_risk.RiskModel({})
        self.assertTrue(model.applies({}))
        for method in (model.risk, model.reference_risk, model.factors):
            with self.assertRaises(NotImplementedError):
                method({})


class MetricTest(unittest.TestCase):
    def test_auc_perfect_and_inverse(self):
        self.assertEqual(toxage_risk.auc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]), 1.0)
        self.assertEqual(toxage_risk.auc([0.9, 0.8, 0.2, 0.1], [0, 0, 1, 1]), 0.0)

    def test_auc_ties_count_half(self):
        self.assertEqual(toxage_risk.auc([0.5, 0.5], [0, 1]), 0.5)

    def test_auc_skips_none_and_needs_both_classes(self):
        self.assertEqual(toxage_risk.auc([None, 0.1, 0.9], [1, 0, 1]), 1.0)
        self.assertIsNone(toxage_risk.auc([0.1, 0.2], [1, 1]))

    def test_brier(self):
        self.assertAlmostEqual(toxage_risk.brier([0.2, 0.6], [0, 1]), (0.04 + 0.16) / 2)
        self.assertIsNone(toxage_risk.brier([None], [1]))

    def test_calibration_groups(self):
        risks = [i / 10 for i in range(10)]
        events = [0] * 5 + [1] * 5
        groups = toxage_risk.calibration(risks, events, groups=2)
        self.assertEqual([n for *_, n in groups], [5, 5])
        self.assertAlmostEqual(groups[0][0], 0.2)
        self.assertEqual([g[1] for g in groups], [0, 1])

    def test_calibration_with_few_patients(self):
        self.assertEqual(len(toxage_risk.calibration([0.3, 0.4], [0, 1], groups=10)), 2)
        self.assertEqual(toxage_risk.calibration([], []), [])


if __name__ == "__main__":
    unittest.main()
