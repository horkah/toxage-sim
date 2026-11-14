import json

from django.test import SimpleTestCase

from explorer import cohort, survival, timeline
from explorer.survival import Record

from .helpers import CohortTestCase


class CurveTest(SimpleTestCase):
    def test_time_axis_ends_on_a_tick_at_or_after_the_end(self):
        unit, label, ticks = timeline._axis(3640)
        self.assertEqual((unit, ticks[-1], len(ticks)), (survival.YEAR, 10, 11))
        self.assertIn("years", label)
        unit, label, ticks = timeline._axis(2 * survival.YEAR)
        self.assertEqual((unit, ticks), (survival.MONTH, list(range(0, 25, 3))))
        self.assertEqual(timeline._axis(3 * survival.YEAR)[2], list(range(0, 37, 6)))

    def test_time_to_event_chart(self):
        named = [("A", [Record("1", 100, "death"), Record("2", 400, None)]),
                 ("B", [Record("1", 50, "death"), Record("2", 400, None)])]
        spec = timeline.time_to_event("Survival", named, survival.kaplan_meier, 400, "share alive", True, 100)
        self.assertEqual([s["cls"] for s in spec["series"]], ["sa", "sb"])
        self.assertTrue(all(s["step"] for s in spec["series"]))
        self.assertEqual(spec["at_risk"]["rows"][0]["values"][:2], [2, 2])
        self.assertEqual(spec["x"]["max"], spec["x"]["ticks"][-1])
        self.assertEqual(spec["marker"]["label"], "patient, day 100")
        self.assertTrue(timeline.time_to_event("t", [("A", [])], survival.kaplan_meier, 10, "y", True)["empty"])

    def test_event_name(self):
        self.assertEqual(timeline.event_name("interstitial_lung_disease"), "lung toxicity")
        self.assertEqual(timeline.event_name("febrile_neutropenia"), "febrile neutropenia")

    def test_empty_charts(self):
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

    def test_endpoint_table_agrees_with_the_curves(self):
        records = {"os": (survival.overall_survival(self.rows), "")}
        table = timeline.endpoint_table([("Usual care", records)], 7 * self.dataset.metadata["weeks"])
        alive = next(r for r in table if r["measure"] == "alive at 1 year")
        steps = survival.kaplan_meier(records["os"][0])
        self.assertEqual(alive["values"], [f"{100 * survival.value_at(steps, survival.YEAR):.1f}%"])
        self.assertIsNone(alive["diff"])

    def test_paired_endpoint_table(self):
        both = [(name, {"os": (survival.overall_survival(rows), "")})
                for name, rows in (("Combined", self.rows_of("combined")), ("Usual care", self.rows))]
        table = timeline.endpoint_table(both, 7 * self.dataset.metadata["weeks"])
        mean = table[0]
        self.assertTrue(mean["first"])
        self.assertIn("restricted mean", mean["measure"])
        self.assertTrue(mean["diff"].endswith("days"))
        self.assertIn(" to ", mean["ci"])
        self.assertEqual(table[2]["measure"], "median survival")
        self.assertIsNone(table[2]["diff"])

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
        self.assertIsNone(usual["d_os"])
        self.assertGreaterEqual(perfect["d_os"], 0)
        self.assertGreater(perfect["free_1y"], usual["free_1y"])
        # With perfect detection only cardiovascular events without a warning phase remain.
        self.assertLessEqual(perfect["severe_events"], perfect["cv_events"] / perfect["n"] + 1e-9)
        self.assertLessEqual(perfect["cv_events"], combined["cv_events"])
        self.assertEqual(usual["cv_events"], sum(r["cv_event"] for r in self.rows_of("usual_care")))
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

    def test_event_grades(self):
        for cid, kind, title in timeline.GRADED_EVENTS:
            spec = timeline.event_grades(self.dataset.scenarios, self.events_of, self.ids, "usual_care", kind, title)
            self.assertEqual(spec["title"], title)
            if not spec.get("empty"):
                self.assertEqual([s["cls"] for s in spec["series"]], ["g1", "g2", "g3", "g5"])
                self.assertEqual(spec["highlight"], 0)

    def test_cardiovascular_events_by_grade(self):
        spec = timeline.event_grades(self.dataset.scenarios, self.events_of, self.ids, "usual_care",
                                     timeline.CV, "Cardiovascular events by grade")
        low, _, high, fatal = (s["values"] for s in spec["series"])
        usual = [s["scenario_id"] for s in self.dataset.scenarios].index("usual_care")
        self.assertEqual(low[usual], 0)      # usual care sees no warning phase
        self.assertEqual(high[usual] + fatal[usual], sum(r["cv_event"] for r in self.rows_of("usual_care")))
        self.assertEqual(timeline.event_name(timeline.CV), "cardiovascular event")

    def test_patient_charts(self):
        pid = next(p for p, found in self.events_of("combined").items() if found)
        patient = cohort.find(self.rows_of("combined"), pid)
        courses = [(name, cohort.course(self.dataset, s, pid))
                   for name, s in (("Combined", "combined"), ("Usual care", "usual_care"))]
        specs = dict(timeline.patient_charts(courses, patient))
        self.assertEqual(set(specs), {"patient-dose", "patient-neutrophils", "patient-haemoglobin",
                                      "patient-platelets", "patient-spo2", "patient-pressure",
                                      "patient-symptoms"})
        self.assertIn("chest pain", [s["name"] for s in specs["patient-symptoms"]["series"]])
        dose = specs["patient-dose"]
        self.assertEqual(len(dose["series"]), 2)
        self.assertTrue(dose["series"][0]["step"])
        self.assertEqual(dose["series"][0]["points"][0][0], 0)
        self.assertTrue(any(m["cls"] == "ev" for m in dose["markers"]))
        self.assertEqual(len(specs["patient-symptoms"]["series"]), 5)
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
