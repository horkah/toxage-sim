"""Tests of the engine. Run with: python3 -m unittest discover engine/tests"""
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_DIR.parent))
sys.path.insert(0, str(ENGINE_DIR))

from schema import toxage_schema  # noqa: E402
import generate  # noqa: E402
import hazards  # noqa: E402


class EngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.regimens, cls.params = generate.load_config()
        cls.data = generate.generate(12000, seed=7, validate=False)
        cls.baseline = {p["patient_id"]: p for p in cls.data["baseline"]}
        cls.outcome = {o["patient_id"]: o for o in cls.data["outcome"]}
        cls.events = {}
        for e in cls.data["event"]:
            cls.events.setdefault(e["patient_id"], []).append(e)
        cls.observations = {}
        for r in cls.data["observation"]:
            cls.observations.setdefault(r["patient_id"], []).append(r)

    def rate(self, field, test):
        ids = [i for i, p in self.baseline.items() if test(p)]
        return sum(bool(self.outcome[i][field]) for i in ids) / len(ids)

    def test_records_follow_schema(self):
        small = generate.generate(600, seed=2)
        for table in toxage_schema.TABLES:
            self.assertTrue(small[table])

    def test_config_matches_schema(self):
        self.assertEqual(set(self.regimens), set(toxage_schema.allowed_values("baseline", "regimen")))
        types = set(self.params["hazards"]["event_types"]) | {hazards.ILD}
        self.assertEqual(types, set(toxage_schema.allowed_values("event", "event_type")))
        for regimen in self.regimens.values():
            self.assertLessEqual(set(regimen["severe_event_rates"]), types)

    def test_three_tumour_types_in_equal_numbers(self):
        counts = Counter(p["tumour_type"] for p in self.data["baseline"])
        self.assertEqual(set(counts.values()), {4000})
        self.assertEqual(len(counts), 3)

    def test_regimen_fits_subgroup(self):
        for p in self.data["baseline"]:
            self.assertEqual(self.regimens[p["regimen"]]["subgroup"], p["subgroup"])
            self.assertEqual(self.regimens[p["regimen"]]["tumour_type"], p["tumour_type"])

    def test_same_seed_gives_same_data(self):
        self.assertEqual(generate.generate(150, seed=3), generate.generate(150, seed=3))
        self.assertNotEqual(generate.generate(150, seed=3)["outcome"], generate.generate(150, seed=4)["outcome"])

    def test_validator_finds_errors(self):
        record = dict(self.data["baseline"][0], ecog=9, regimen="unknown")
        del record["sex"]
        self.assertEqual(len(toxage_schema.errors("baseline", record)), 3)

    def test_calibration_is_close_to_literature(self):
        with open(ENGINE_DIR / "config" / "calibration.json", encoding="utf-8") as f:
            check = json.load(f)["check"]
        for regimen, types in check.items():
            for event_type, v in types.items():
                self.assertAlmostEqual(v["realised"], v["target"], delta=0.035, msg=f"{regimen} {event_type}")

    def test_outcome_agrees_with_events(self):
        for pid, o in self.outcome.items():
            days = [e["day"] for e in self.events.get(pid, []) if e["grade"] >= 3 and e["day"] <= 90]
            self.assertEqual(o["severe_toxicity_90d"], bool(days))
            self.assertEqual(o["severe_toxicity_day"], min(days) if days else None)
            self.assertEqual(o["ild"], o["ild_onset_day"] is not None)
            self.assertEqual(o["ild"], o["ild_grade"] is not None)
            if o["ild_diagnosis_day"] is not None:
                self.assertGreaterEqual(o["ild_diagnosis_day"], o["ild_onset_day"])
            self.assertEqual(o["treatment_end_reason"] == "ongoing", o["treatment_end_day"] is None)

    def test_course_is_consistent(self):
        for pid, rows in self.observations.items():
            o = self.outcome[pid]
            self.assertEqual([r["week"] for r in rows], list(range(len(rows))))
            self.assertLessEqual(rows[-1]["day"], o["follow_up_days"])
            self.assertEqual(rows[0]["dose_level"], self.baseline[pid]["starting_dose_level"])
            doses = [r["dose_level"] for r in rows if r["dose_level"] is not None]
            self.assertEqual(doses, sorted(doses, reverse=True))
            stopped = [r["treatment_status"] == "stopped" for r in rows]
            self.assertEqual(stopped, sorted(stopped))
            for e in self.events.get(pid, []):
                self.assertLessEqual(e["onset_day"], e["day"])
                self.assertLessEqual(e["day"], o["follow_up_days"])
            if any(e["grade"] == 5 for e in self.events.get(pid, [])):
                self.assertIsNotNone(o["death_day"])

    def test_lab_values_show_events(self):
        for pid, events in self.events.items():
            weeks = {r["week"]: r for r in self.observations[pid]}
            for e in events:
                row = weeks.get((e["day"] - 1) // 7)
                if row is None:
                    continue
                if e["event_type"] == "neutropenia":
                    self.assertLess(row["neutrophils_10e9_l"], 1.0)
                if e["event_type"] == "anaemia":
                    self.assertLess(row["haemoglobin_g_dl"], 8.05)

    def test_frail_patients_have_more_severe_toxicity(self):
        fit = self.rate("severe_toxicity_90d", lambda p: p["ecog"] == 0)
        frail = self.rate("severe_toxicity_90d", lambda p: p["ecog"] == 2)
        self.assertGreater(frail, fit + 0.05)

    def test_older_patients_with_impairments_are_close_to_gap70(self):
        rate = self.rate("severe_toxicity_90d",
                         lambda p: p["age_years"] >= 70 and (p["ga_impaired_domains"] or 0) >= 1)
        self.assertAlmostEqual(rate, 0.71, delta=0.06)

    def test_lung_toxicity(self):
        tdxd = lambda p: p["regimen"] == "trastuzumab_deruxtecan"
        self.assertAlmostEqual(self.rate("ild", tdxd), 0.105, delta=0.03)
        self.assertEqual(self.rate("ild", lambda p: p["regimen"] == "nalirifox"), 0)
        low = self.rate("ild", lambda p: tdxd(p) and p["renal_function"] == "moderate_severe_decrease")
        rest = self.rate("ild", lambda p: tdxd(p) and p["renal_function"] == "normal")
        self.assertGreater(low, rest)

    def test_lung_toxicity_is_often_recognised_late(self):
        gaps = [o["ild_diagnosis_day"] - o["ild_onset_day"] for o in self.outcome.values()
                if o["ild_diagnosis_day"] is not None]
        late = sum(g > 7 for g in gaps) / len(gaps)
        self.assertAlmostEqual(late, 0.53, delta=0.12)

    def test_oxygen_saturation_falls_before_diagnosis(self):
        changes = []
        for pid, o in self.outcome.items():
            if o["ild_diagnosis_day"] is None or o["ild_grade"] < 2:
                continue
            if o["ild_diagnosis_day"] - o["ild_onset_day"] < 21:
                continue
            for r in self.observations[pid]:
                if o["ild_onset_day"] + 14 <= r["day"] <= o["ild_diagnosis_day"] and r["spo2_percent"] is not None:
                    changes.append(r["spo2_percent"] - self.baseline[pid]["spo2_percent"])
        self.assertLess(sum(changes) / len(changes), -1.5)


if __name__ == "__main__":
    unittest.main()
