"""Tests of the risk model interface. Run with: python3 -m unittest discover risk-model/tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import toxage_risk  # noqa: E402
from engine import generate, toxicity  # noqa: E402


class ModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline, cls.outcomes, cls.metadata = generate.generate(400, seed=2)
        cls.models = {m.id: m for m in toxage_risk.load(cls.metadata)}

    def patient(self, **changes):
        return dict(self.baseline[0], **changes)

    def test_all_registered_models_are_loaded_with_unique_ids(self):
        self.assertEqual(len(self.models), len(toxage_risk.MODELS))

    def test_describe_names_an_outcome_field(self):
        outcome_fields = set(self.outcomes[0])
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

    def test_severe_model_equals_engine(self):
        model = self.models["severe90"]
        p = self.baseline[5]
        self.assertEqual(model.risk(p),
                         toxicity.severe_toxicity_risk(p, model.regimens, model.params))

    def test_reference_patient_has_reference_risk(self):
        model = self.models["severe90"]
        p = self.patient(regimen="olaparib", age_years=65, ecog=0, ga_impaired_domains=0)
        self.assertAlmostEqual(model.risk(p), model.reference_risk(p))
        self.assertTrue(all(f.ratio == 1 for f in model.factors(p)))

    def test_lung_model_applies_only_to_calibrated_regimens(self):
        model = self.models["ild"]
        self.assertFalse(model.applies(self.patient(regimen="nalirifox")))
        self.assertIsNone(model.risk(self.patient(regimen="nalirifox")))
        self.assertEqual(model.factors(self.patient(regimen="nalirifox")), [])
        self.assertTrue(model.applies(self.patient(regimen="trastuzumab_deruxtecan")))

    def test_lung_model_without_metadata_applies_to_nobody(self):
        model = toxage_risk.LungToxicityModel({}, {}, {})
        self.assertFalse(model.applies(self.patient()))

    def test_factors_have_labels(self):
        p = self.patient(regimen="trastuzumab_deruxtecan")
        for model in self.models.values():
            for f in model.factors(p):
                self.assertNotEqual(f.label, f.name)

    def test_base_class_is_abstract(self):
        model = toxage_risk.RiskModel({}, {}, {})
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
