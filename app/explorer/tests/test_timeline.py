import json

from django.test import SimpleTestCase

from explorer import cohort, timeline

from .helpers import CohortTestCase


class CurveTest(SimpleTestCase):
    def test_share_curve_rises_to_the_share_with_event(self):
        points = timeline.share_curve([10, 20, None, None], 4, 40, 10, steps=4)
        self.assertEqual(points, [[0, 0], [1, 0.25], [2, 0.5], [3, 0.5], [4, 0.5]])

    def test_falling_curve(self):
        points = timeline.share_curve([10], 2, 20, 1, falling=True, steps=2)
        self.assertEqual([p[1] for p in points], [1, 0.5, 0.5])

    def test_first_severe_days(self):
        events = {"A": [{"grade": 2, "day": 3}, {"grade": 4, "day": 9}, {"grade": 3, "day": 5}], "B": []}
        self.assertEqual(timeline.first_severe_days(events, ["A", "B", "C"]), [5, None, None])

    def test_event_name(self):
        self.assertEqual(timeline.event_name("interstitial_lung_disease"), "lung toxicity")
        self.assertEqual(timeline.event_name("febrile_neutropenia"), "febrile neutropenia")

    def test_empty_charts(self):
        self.assertTrue(timeline.survival([("a", [])], 100)["empty"])
        self.assertTrue(timeline.lead_time({}, set())["empty"])
        self.assertTrue(timeline.grade_shift({}, set())["empty"])
        self.assertTrue(timeline.scenario_bars([], "t", [], "l", "num", "x")["empty"])
        self.assertEqual(timeline.scenario_table([{"scenario_id": "a"}], lambda s: [], lambda s: {}, set()), [])


class TimelineTest(CohortTestCase):
    def setUp(self):
        super().setUp()
        self.ids = {r["patient_id"] for r in self.rows}
        self.rows_of = lambda s: cohort.rows(self.dataset, s, self.models)
        self.events_of = lambda s: cohort.events(self.dataset, s)
        self.table = timeline.scenario_table(self.dataset.scenarios, self.rows_of, self.events_of, self.ids)

    def test_cohort_curves(self):
        named = [("Usual care", self.rows), ("Combined", self.rows_of("combined"))]
        horizon = 7 * self.dataset.metadata["weeks"]
        survival = timeline.survival(named, horizon)
        self.assertEqual([s["cls"] for s in survival["series"]], ["sa", "sb"])
        self.assertTrue(survival["series"][1]["dash"])
        for s in survival["series"]:
            shares = [p[1] for p in s["points"]]
            self.assertEqual(shares[0], 1)
            self.assertEqual(shares, sorted(shares, reverse=True))
        dead = sum(r["death_day"] is not None for r in self.rows) / self.n
        self.assertAlmostEqual(survival["series"][0]["points"][-1][1], 1 - dead, places=3)
        therapy = timeline.on_therapy(named[:1], horizon)
        self.assertLessEqual(therapy["x"]["max"], 36.1)
        days = timeline.first_severe_days(self.events_of("usual_care"), self.ids)
        incidence = timeline.severe_incidence([("Usual care", days)], horizon)
        self.assertGreater(incidence["series"][0]["points"][-1][1], 0.4)

    def test_scenario_table(self):
        by_id = {t["scenario"]["scenario_id"]: t for t in self.table}
        usual, combined, perfect = by_id["usual_care"], by_id["combined"], by_id["perfect_detection"]
        self.assertEqual(len(self.table), len(self.dataset.scenarios))
        self.assertEqual((usual["participating"], usual["alerts"], usual["cost_intervention"]), (0, 0, 0))
        self.assertIsNone(usual["d_cost"])
        self.assertIsNone(usual["false_share"])
        self.assertLess(combined["severe_events"], usual["severe_events"])
        self.assertGreater(combined["early"], 0)
        self.assertAlmostEqual(combined["d_qaly"], combined["qaly"] - usual["qaly"])
        self.assertEqual(perfect["severe_events"], 0)
        self.assertEqual(perfect["participating"], 1)
        self.assertEqual(combined["cost"], combined["cost_care"] + combined["cost_intervention"])

    def test_table_respects_the_selection(self):
        ids = {r["patient_id"] for r in self.rows if r["tumour_type"] == "breast"}
        table = timeline.scenario_table(self.dataset.scenarios, self.rows_of, self.events_of, ids)
        self.assertEqual({t["n"] for t in table}, {len(ids)})

    def test_scenario_bars(self):
        spec = timeline.scenario_bars(self.table, "Costs", [("care", "sb", "cost_care"),
                                      ("intervention", "sa", "cost_intervention")], "euros", "int",
                                      "combined", stacked=True)
        self.assertEqual(len(spec["categories"]), len(self.table))
        self.assertEqual(spec["categories"][spec["highlight"]], "Combined")
        self.assertEqual(spec["links"][0], {"scenario": "usual_care"})
        self.assertEqual(spec["series"][1]["values"][0], 0)

    def test_early_recognition_charts(self):
        events = self.events_of("combined")
        found = timeline.monitored(events, self.ids)
        self.assertTrue(found)
        lead = timeline.lead_time(events, self.ids)
        self.assertEqual(sum(lead["series"][0]["values"]), len(found))
        shift = timeline.grade_shift(events, self.ids)
        before, after = (s["values"] for s in shift["series"])
        self.assertEqual(sum(before), sum(after))
        mean = lambda values: sum((i + 1) * v for i, v in enumerate(values)) / sum(values)
        self.assertLess(mean(after), mean(before))
        self.assertTrue(timeline.lead_time(self.events_of("usual_care"), self.ids)["empty"])

    def test_lung_grades(self):
        spec = timeline.lung_grades(self.dataset.scenarios, self.events_of, self.ids, "usual_care")
        if not spec.get("empty"):
            self.assertEqual([s["cls"] for s in spec["series"]], ["g1", "g2", "g3", "g5"])
            self.assertEqual(spec["highlight"], 0)

    def test_patient_charts(self):
        pid = next(p for p, found in self.events_of("combined").items() if found)
        patient = cohort.find(self.rows_of("combined"), pid)
        courses = [(name, cohort.course(self.dataset, s, pid))
                   for name, s in (("Combined", "combined"), ("Usual care", "usual_care"))]
        specs = dict(timeline.patient_charts(courses, patient))
        self.assertEqual(set(specs), {"patient-dose", "patient-neutrophils", "patient-haemoglobin",
                                      "patient-platelets", "patient-spo2", "patient-symptoms"})
        dose = specs["patient-dose"]
        self.assertEqual(len(dose["series"]), 2)
        self.assertTrue(dose["series"][0]["step"])
        self.assertEqual(dose["series"][0]["points"][0][0], 0)
        self.assertTrue(any(m["cls"] == "ev" for m in dose["markers"]))
        self.assertEqual(len(specs["patient-symptoms"]["series"]), 4)
        json.dumps(specs, allow_nan=False)
        rows = timeline.event_rows(courses[0][1])
        self.assertEqual([r["day"] for r in rows], sorted(r["day"] for r in rows))
        self.assertIn("name", rows[0])

    def test_markers(self):
        course = {"events": [{"event_type": "diarrhoea", "grade": 2, "day": 15, "detected_by": "monitoring"}],
                  "alerts": [{"day": 14, "true_alert": True, "event_type": "diarrhoea"},
                             {"day": 30, "true_alert": False, "event_type": None}]}
        outcome = {"treatment_end_day": 50, "treatment_end_reason": "lost_to_follow_up"}
        marks = timeline.markers(course, outcome)
        self.assertEqual([m["cls"] for m in marks], ["ev", "al", "al", "end"])
        self.assertEqual(marks[0]["x"], 2)
        self.assertIn("through monitoring", marks[0]["label"])
        self.assertIn("false alert", marks[2]["label"])
        self.assertIn("lost to follow up", marks[3]["label"])
        self.assertEqual(timeline.markers({"events": [], "alerts": []},
                                          {"treatment_end_day": 9, "treatment_end_reason": "death"}), [])
