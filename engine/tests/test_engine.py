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
from draws import Draws  # noqa: E402

USUAL = generate.USUAL_CARE


def by_patient(records, scenario_id):
    found = {}
    for r in generate.of_scenario(records, scenario_id):
        found.setdefault(r["patient_id"], []).append(r)
    return found


def without(record, *keys):
    return {k: v for k, v in record.items() if k not in keys}


class DrawsTest(unittest.TestCase):
    def test_numbers_are_fixed_and_differ_by_purpose_week_and_patient(self):
        d = Draws(1, 5)
        self.assertEqual(d.u("death", 3), Draws(1, 5).u("death", 3))
        values = {d.u("death", 3), d.u("death", 4), d.u("stop", 3), Draws(1, 6).u("death", 3),
                  Draws(2, 5).u("death", 3)}
        self.assertEqual(len(values), 5)

    def test_numbers_are_uniform(self):
        values = [Draws(3, i).u("x", i % 7) for i in range(20000)]
        self.assertTrue(all(0 <= v < 1 for v in values))
        self.assertAlmostEqual(sum(values) / len(values), 0.5, delta=0.01)
        self.assertAlmostEqual(sum(v < 0.1 for v in values) / len(values), 0.1, delta=0.01)

    def test_pick_follows_probabilities(self):
        picks = Counter(Draws(4, i).pick("p", {"a": 0.2, "b": 0.8, "basis": "x"}) for i in range(5000))
        self.assertEqual(set(picks), {"a", "b"})
        self.assertAlmostEqual(picks["a"] / 5000, 0.2, delta=0.02)


class EngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.regimens, cls.params = generate.load_config()
        cls.iv = generate.load_interventions()
        cls.data = generate.generate(3000, seed=7, validate=False)
        cls.baseline = {p["patient_id"]: p for p in cls.data["baseline"]}
        cls.scenarios = [s["scenario_id"] for s in cls.data["scenario"]]
        cls.outcome = {s: {o["patient_id"]: o for o in generate.of_scenario(cls.data["outcome"], s)}
                       for s in cls.scenarios}
        cls.events = {s: by_patient(cls.data["event"], s) for s in cls.scenarios}
        cls.alerts = {s: by_patient(cls.data["alert"], s) for s in cls.scenarios}
        cls.observations = {s: by_patient(cls.data["observation"], s) for s in cls.scenarios}

    def rate(self, field, test, scenario=USUAL):
        ids = [i for i, p in self.baseline.items() if test(p)]
        return sum(bool(self.outcome[scenario][i][field]) for i in ids) / len(ids)

    def total(self, field, scenario):
        return sum(o[field] for o in self.outcome[scenario].values())

    # Structure -------------------------------------------------------------

    def test_records_follow_schema(self):
        small = generate.generate(300, seed=2)
        for table in generate.TABLES:
            self.assertTrue(small[table], table)

    def test_config_matches_schema(self):
        self.assertEqual(set(self.regimens), set(toxage_schema.allowed_values("baseline", "regimen")))
        types = set(self.params["hazards"]["event_types"]) | {hazards.ILD}
        self.assertEqual(types, set(toxage_schema.allowed_values("event", "event_type")))
        for regimen in self.regimens.values():
            self.assertLessEqual(set(regimen["severe_event_rates"]), types)
        self.assertIn(USUAL, self.iv["scenarios"])
        self.assertEqual(self.iv["scenarios"][USUAL]["components"], [])

    def test_three_tumour_types_in_equal_numbers(self):
        counts = Counter(p["tumour_type"] for p in self.data["baseline"])
        self.assertEqual(dict(counts), {"pancreas": 1000, "prostate": 1000, "breast": 1000})

    def test_regimen_fits_subgroup(self):
        for p in self.data["baseline"]:
            self.assertEqual(self.regimens[p["regimen"]]["subgroup"], p["subgroup"])

    def test_same_seed_gives_same_data(self):
        self.assertEqual(generate.generate(90, seed=3), generate.generate(90, seed=3))
        self.assertNotEqual(generate.generate(90, seed=3)["outcome"], generate.generate(90, seed=4)["outcome"])

    def test_validator_finds_errors(self):
        record = dict(self.data["baseline"][0], ecog=9, regimen="unknown")
        del record["sex"]
        self.assertEqual(len(toxage_schema.errors("baseline", record)), 3)

    def test_every_scenario_has_one_outcome_per_patient(self):
        for s in self.scenarios:
            self.assertEqual(set(self.outcome[s]), set(self.baseline))

    # Usual care against the literature ---------------------------------------

    def test_calibration_is_close_to_literature(self):
        with open(ENGINE_DIR / "config" / "calibration.json", encoding="utf-8") as f:
            check = json.load(f)["check"]
        for regimen, types in check.items():
            for event_type, v in types.items():
                self.assertAlmostEqual(v["realised"], v["target"], delta=0.03, msg=f"{regimen} {event_type}")

    def test_frail_patients_have_more_severe_toxicity(self):
        fit = self.rate("severe_toxicity_90d", lambda p: p["ecog"] == 0)
        frail = self.rate("severe_toxicity_90d", lambda p: p["ecog"] == 2)
        self.assertGreater(frail, fit + 0.05)

    def test_older_patients_with_impairments_are_close_to_gap70(self):
        rate = self.rate("severe_toxicity_90d",
                         lambda p: p["age_years"] >= 70 and (p["ga_impaired_domains"] or 0) >= 1)
        self.assertAlmostEqual(rate, 0.71, delta=0.07)

    def test_lung_toxicity(self):
        tdxd = [i for i, p in self.baseline.items() if p["regimen"] == "trastuzumab_deruxtecan"]
        first_year = sum(self.outcome[USUAL][i]["ild"] and self.outcome[USUAL][i]["ild_onset_day"] <= 364
                         for i in tdxd) / len(tdxd)
        self.assertAlmostEqual(first_year, 0.105, delta=0.04)
        self.assertEqual(self.rate("ild", lambda p: p["regimen"] == "nalirifox"), 0)

    def test_lung_toxicity_is_often_recognised_late(self):
        gaps = [o["ild_diagnosis_day"] - o["ild_onset_day"] for o in self.outcome[USUAL].values()
                if o["ild_diagnosis_day"] is not None]
        self.assertAlmostEqual(sum(g > 7 for g in gaps) / len(gaps), 0.53, delta=0.2)

    def test_usual_care_has_no_intervention(self):
        self.assertEqual(self.alerts[USUAL], {})
        for o in self.outcome[USUAL].values():
            self.assertEqual((o["cost_intervention"], o["alerts"], o["participating"], o["high_risk_flag"]),
                             (0, 0, False, False))
        for events in self.events[USUAL].values():
            for e in events:
                self.assertEqual((e["detected_by"], e["day"] >= e["usual_care_day"], e["grade"]),
                                 ("routine", True, e["usual_care_grade"]))

    # Course over time -----------------------------------------------------------

    def test_follow_up_runs_until_death_or_ten_years(self):
        horizon = 7 * self.params["simulation"]["weeks"]
        self.assertEqual(horizon, 3640)
        days = [o["follow_up_days"] for o in self.outcome[USUAL].values()]
        self.assertEqual(max(days), horizon)
        self.assertGreater(sum(d > 364 for d in days) / len(days), 0.4)
        for o in self.outcome[USUAL].values():
            if o["death_day"] is None:
                self.assertEqual(o["follow_up_days"], horizon)
            else:
                self.assertEqual(o["follow_up_days"], o["death_day"])

    def test_outcome_agrees_with_events_and_alerts(self):
        for s in self.scenarios:
            for pid, o in self.outcome[s].items():
                events = self.events[s].get(pid, [])
                alerts = self.alerts[s].get(pid, [])
                days = [e["day"] for e in events if e["grade"] >= 3 and e["day"] <= 90]
                self.assertEqual(o["severe_toxicity_90d"], bool(days))
                self.assertEqual(o["severe_toxicity_day"], min(days) if days else None)
                self.assertEqual(o["ild"], o["ild_onset_day"] is not None)
                self.assertEqual(o["treatment_end_reason"] == "ongoing", o["treatment_end_day"] is None)
                self.assertEqual(o["hospital_days"], sum(e["hospital_days"] for e in events))
                self.assertEqual(o["alerts"], len(alerts))
                self.assertEqual(o["false_alerts"], sum(not a["true_alert"] for a in alerts))
                self.assertEqual(o["death_from_toxicity"], any(e["grade"] == 5 for e in events))
                if o["death_from_toxicity"]:
                    self.assertIsNotNone(o["death_day"])
                self.assertLessEqual(o["qaly"], o["follow_up_days"] / 365.25)

    def test_course_is_consistent(self):
        for s in self.scenarios:
            for pid, rows in self.observations[s].items():
                o = self.outcome[s][pid]
                self.assertEqual([r["week"] for r in rows], list(range(len(rows))))
                self.assertLessEqual(rows[-1]["day"], o["follow_up_days"])
                doses = [r["dose_level"] for r in rows if r["dose_level"] is not None]
                self.assertEqual(doses, sorted(doses, reverse=True))
                stopped = [r["treatment_status"] == "stopped" for r in rows]
                self.assertEqual(stopped, sorted(stopped))
                for e in self.events[s].get(pid, []):
                    self.assertLessEqual(e["onset_day"], e["day"])
                    self.assertLessEqual(e["day"], o["follow_up_days"])
                    self.assertLessEqual(e["icu_days"], e["hospital_days"] + e["icu_days"])

    def test_lab_values_show_severe_events(self):
        for pid, events in self.events[USUAL].items():
            weeks = {r["week"]: r for r in self.observations[USUAL][pid]}
            for e in events:
                row = weeks.get((e["day"] - 1) // 7)
                if row is None:
                    continue
                if e["event_type"] == "neutropenia":
                    self.assertLess(row["neutrophils_10e9_l"], 1.0)
                if e["event_type"] == "anaemia":
                    self.assertLess(row["haemoglobin_g_dl"], 8.05)

    def test_oxygen_saturation_falls_before_diagnosis(self):
        changes = []
        for pid, o in self.outcome[USUAL].items():
            if o["ild_diagnosis_day"] is None or o["ild_grade"] < 2:
                continue
            if o["ild_diagnosis_day"] - o["ild_onset_day"] < 21:
                continue
            for r in self.observations[USUAL][pid]:
                if o["ild_onset_day"] + 14 <= r["day"] <= o["ild_diagnosis_day"] and r["spo2_percent"] is not None:
                    changes.append(r["spo2_percent"] - self.baseline[pid]["spo2_percent"])
        self.assertLess(sum(changes) / len(changes), -1.5)

    # Scenarios ----------------------------------------------------------------------

    def test_usual_care_does_not_depend_on_other_scenarios(self):
        alone = generate.generate(150, seed=9, scenarios=[USUAL], validate=False)
        full = generate.generate(150, seed=9, scenarios=[USUAL, "combined"], validate=False)
        for table in ("observation", "event", "outcome"):
            self.assertEqual(alone[table], generate.of_scenario(full[table], USUAL), table)

    def test_patients_outside_an_intervention_have_the_same_course(self):
        scenario = "lung_monitoring"
        outside = [i for i, o in self.outcome[scenario].items() if not o["participating"]]
        self.assertGreater(len(outside), 2000)
        for pid in outside:
            self.assertEqual(without(self.outcome[scenario][pid], "scenario_id"),
                             without(self.outcome[USUAL][pid], "scenario_id"))
            self.assertEqual([without(r, "scenario_id") for r in self.observations[scenario].get(pid, [])],
                             [without(r, "scenario_id") for r in self.observations[USUAL].get(pid, [])])
            self.assertEqual([without(e, "scenario_id") for e in self.events[scenario].get(pid, [])],
                             [without(e, "scenario_id") for e in self.events[USUAL].get(pid, [])])

    def test_monitoring_recognises_earlier_and_at_a_lower_grade(self):
        found = 0
        for s in self.scenarios:
            for events in self.events[s].values():
                for e in events:
                    self.assertLessEqual(e["grade"], e["usual_care_grade"])
                    if e["detected_by"] == "monitoring":
                        found += 1
                        self.assertLess(e["day"], e["usual_care_day"] + 7)
        self.assertGreater(found, 100)

    def test_alerts_are_consistent(self):
        for s in self.scenarios:
            for alerts in self.alerts[s].values():
                for a in alerts:
                    self.assertTrue(a["attended"] or not a["acted"])
                    self.assertEqual(a["true_alert"], a["event_type"] is not None)
                    if not a["true_alert"]:
                        self.assertFalse(a["acted"])

    def test_lung_monitoring_is_limited_to_its_regimen(self):
        for pid, o in self.outcome["lung_monitoring"].items():
            if o["participating"]:
                self.assertEqual(self.baseline[pid]["regimen"], "trastuzumab_deruxtecan")
        sources = {a["source"] for alerts in self.alerts["lung_monitoring"].values() for a in alerts}
        self.assertEqual(sources, {"lung_monitoring"})

    def test_lung_monitoring_lowers_the_grade_of_lung_toxicity(self):
        def severe(s):
            return sum(e["grade"] >= 3 for events in self.events[s].values() for e in events
                       if e["event_type"] == hazards.ILD)
        self.assertLess(severe("lung_monitoring"), severe(USUAL))

    def test_risk_adapted_start_flags_the_given_share_and_lowers_toxicity(self):
        s = "risk_adapted_start"
        flagged = [i for i, o in self.outcome[s].items() if o["high_risk_flag"]]
        self.assertAlmostEqual(len(flagged) / len(self.baseline),
                               self.iv["risk_adapted_start"]["share_flagged"], delta=0.01)
        taking_part = [i for i in flagged if self.outcome[s][i]["participating"]]
        self.assertTrue(0.5 < len(taking_part) / len(flagged) < 0.95)
        before = sum(self.outcome[USUAL][i]["severe_toxicity_90d"] for i in taking_part)
        after = sum(self.outcome[s][i]["severe_toxicity_90d"] for i in taking_part)
        self.assertLess(after, 0.92 * before)
        self.assertTrue(all(not self.outcome[s][i]["participating"]
                            for i in self.baseline if i not in flagged))

    def test_scenarios_order_by_effect(self):
        events = {s: sum(e["grade"] >= 3 for ev in self.events[s].values() for e in ev) for s in self.scenarios}
        self.assertLess(events["symptom_monitoring"], events[USUAL])
        self.assertLess(events["risk_adapted_start"], events[USUAL])
        self.assertLess(events["combined"], min(events["symptom_monitoring"], events["risk_adapted_start"]))
        self.assertLess(self.total("hospital_days", "combined"), self.total("hospital_days", USUAL))
        self.assertGreater(self.total("qaly", "combined"), self.total("qaly", USUAL))
        self.assertGreater(self.total("cost_intervention", "combined"), 0)

    def test_perfect_detection_is_the_upper_limit(self):
        s = "perfect_detection"
        self.assertTrue(all(o["participating"] for o in self.outcome[s].values()))
        self.assertEqual(self.total("death_from_toxicity", s), 0)
        self.assertEqual(self.total("false_alerts", s), 0)
        self.assertEqual(sum(e["grade"] >= 3 for ev in self.events[s].values() for e in ev), 0)
        self.assertGreaterEqual(self.total("qaly", s), self.total("qaly", "combined"))


if __name__ == "__main__":
    unittest.main()
