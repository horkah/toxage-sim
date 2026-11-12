"""Tests of the engine. Run with: python3 -m unittest discover engine/tests"""
import statistics
import sys
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_DIR.parent))
sys.path.insert(0, str(ENGINE_DIR))

from schema import toxage_schema  # noqa: E402
import generate  # noqa: E402
import toxicity  # noqa: E402


class EngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.regimens, cls.params = generate.load_config()
        cls.baseline, cls.outcomes, cls.metadata = generate.generate(30000, seed=7)
        cls.by_id = {o["patient_id"]: o for o in cls.outcomes}

    def group(self, regimen):
        return [self.by_id[p["patient_id"]] for p in self.baseline if p["regimen"] == regimen]

    def test_records_follow_schema(self):
        toxage_schema.validate("baseline", self.baseline)
        toxage_schema.validate("outcome", self.outcomes)

    def test_regimens_match_schema(self):
        self.assertEqual(
            set(self.regimens), set(toxage_schema.allowed_values("baseline", "regimen"))
        )

    def test_same_seed_gives_same_data(self):
        first = generate.generate(200, seed=3)
        second = generate.generate(200, seed=3)
        self.assertEqual(first, second)

    def test_validator_finds_errors(self):
        record = dict(self.baseline[0], ecog=9, regimen="unknown")
        del record["sex"]
        self.assertEqual(len(toxage_schema.errors("baseline", record)), 3)

    def test_reference_patient_has_regimen_rate(self):
        patient = dict(self.baseline[0], regimen="lu_psma_617", age_years=65, ecog=1,
                       ga_impaired_domains=0)
        risk = toxicity.severe_toxicity_risk(patient, self.regimens, self.params)
        self.assertAlmostEqual(risk, 0.527, places=6)

    def test_frail_older_patient_is_close_to_gap70(self):
        self.regimens["test"] = {"severe_toxicity_rate": 0.60}
        patient = {"regimen": "test", "age_years": 77, "ecog": 1, "ga_impaired_domains": 4.5}
        risk = toxicity.severe_toxicity_risk(patient, self.regimens, self.params)
        del self.regimens["test"]
        self.assertAlmostEqual(risk, 0.71, delta=0.05)

    def test_ild_rate_matches_literature(self):
        group = self.group("trastuzumab_deruxtecan")
        rate = sum(o["ild"] for o in group) / len(group)
        self.assertAlmostEqual(rate, 0.121, delta=0.02)

    def test_no_ild_without_reference_rate(self):
        self.assertFalse(any(o["ild"] for o in self.group("nalirifox")))

    def test_ild_onset_distribution(self):
        days = [o["ild_onset_day"] for o in self.group("trastuzumab_deruxtecan") if o["ild"]]
        self.assertAlmostEqual(statistics.median(days), 129, delta=25)
        within_year = sum(d <= 365 for d in days) / len(days)
        self.assertAlmostEqual(within_year, 0.87, delta=0.06)

    def test_risk_factor_raises_ild_rate(self):
        ids_low = {p["patient_id"] for p in self.baseline
                   if p["regimen"] == "trastuzumab_deruxtecan" and p["spo2_percent"] < 95}
        group = self.group("trastuzumab_deruxtecan")
        low = [o["ild"] for o in group if o["patient_id"] in ids_low]
        rest = [o["ild"] for o in group if o["patient_id"] not in ids_low]
        self.assertGreater(sum(low) / len(low), sum(rest) / len(rest))

    def test_outcome_fields_are_consistent(self):
        for o in self.outcomes:
            self.assertEqual(o["severe_toxicity_90d"], o["severe_toxicity_day"] is not None)
            self.assertEqual(o["ild"], o["ild_onset_day"] is not None)
            self.assertEqual(o["ild"], o["ild_grade"] is not None)


if __name__ == "__main__":
    unittest.main()
