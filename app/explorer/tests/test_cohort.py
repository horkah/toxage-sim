from django.test import SimpleTestCase, TestCase

from explorer import cohort
from explorer.models import Dataset, Patient
from schema import toxage_schema

from .helpers import CohortTestCase


class FieldTest(SimpleTestCase):
    def test_fields_follow_schema(self):
        names = [f.name for f in cohort.fields()]
        expected = toxage_schema.fields("baseline") + toxage_schema.fields("outcome")
        self.assertEqual(names, [n for n in expected if n not in ("patient_id", "scenario_id")])

    def test_field_kinds(self):
        by_name = {f.name: f for f in cohort.fields()}
        self.assertEqual(by_name["regimen"].kind, "choice")
        self.assertEqual(by_name["lung_comorbidity"].kind, "bool")
        self.assertEqual(by_name["age_years"].kind, "number")
        self.assertTrue(by_name["age_years"].integer)
        self.assertFalse(by_name["years_since_diagnosis"].integer)
        self.assertTrue(by_name["ga_impaired_domains"].nullable)
        self.assertEqual(by_name["spo2_percent"].unit, "%")
        self.assertEqual(by_name["age_years"].label, "Age")

    def test_fields_of_one_table(self):
        self.assertTrue(all(f.table == "outcome" for f in cohort.fields("outcome")))

    def test_patient_id_is_a_string_field_and_skipped(self):
        self.assertNotIn("patient_id", [f.name for f in cohort.fields()])


class HelperTest(SimpleTestCase):
    def test_normalise_id(self):
        self.assertEqual(cohort.normalise_id(" 42 "), "P000042")
        self.assertEqual(cohort.normalise_id("p000042"), "P000042")
        self.assertEqual(cohort.normalise_id(None), "")

    def test_display(self):
        self.assertEqual(cohort.display(None), "–")
        self.assertEqual(cohort.display(True), "yes")
        self.assertEqual(cohort.display("mild_decrease"), "mild decrease")
        self.assertEqual(cohort.display(3.25, "years"), "3.2 years")
        self.assertEqual(cohort.display(97, "%"), "97%")
        self.assertEqual(cohort.display(2), "2")

    def test_find(self):
        rows = [{"patient_id": "A"}, {"patient_id": "B"}]
        self.assertIs(cohort.find(rows, "B"), rows[1])
        self.assertIsNone(cohort.find(rows, "C"))


class EmptyTest(TestCase):
    def test_current_without_data(self):
        self.assertIsNone(cohort.current())


class CurrentTest(CohortTestCase):
    def test_rows_hold_records_and_risks(self):
        self.assertEqual(len(self.rows), self.n)
        row = self.rows[0]
        self.assertEqual({f.name for f in cohort.fields()} - set(row), set())
        self.assertEqual(row["risk_severe90"], self.severe.risk(row))
        self.assertIn("risk_ild", row)

    def test_score(self):
        rows = cohort.score([dict(self.rows[0])], self.models)
        self.assertEqual(rows[0]["risk_ild"], self.ild.risk(self.rows[0]))

    def test_risk_key(self):
        self.assertEqual(cohort.risk_key(self.severe), "risk_severe90")

    def test_load_cohort_replaces_the_data_set(self):
        from django.core.management import call_command
        call_command("load_cohort", n=10, seed=1, stdout=open("/dev/null", "w"))
        self.assertEqual(Dataset.objects.count(), 1)
        self.assertEqual(Patient.objects.count(), 10)

    def test_model_methods(self):
        patient = Patient.objects.first()
        self.assertEqual(str(patient), patient.patient_id)
        self.assertIn(f"{self.n} patients", str(self.dataset))


class ScenarioTest(CohortTestCase):
    def test_scenarios_of_the_data_set(self):
        ids = cohort.scenario_ids(self.dataset)
        self.assertEqual(ids[0], cohort.USUAL_CARE)
        self.assertIn("combined", ids)
        self.assertEqual(cohort.scenario(self.dataset, "combined")["scenario_id"], "combined")
        self.assertEqual(cohort.scenario(self.dataset, "unknown")["scenario_id"], cohort.USUAL_CARE)

    def test_rows_of_another_scenario_share_baseline_and_risks(self):
        other = cohort.rows(self.dataset, "combined", self.models)
        self.assertEqual(len(other), self.n)
        for a, b in zip(self.rows, other):
            self.assertEqual((a["patient_id"], a["age_years"], a["risk_severe90"]),
                             (b["patient_id"], b["age_years"], b["risk_severe90"]))
        self.assertTrue(any(r["participating"] for r in other))
        self.assertFalse(any(r["participating"] for r in self.rows))

    def test_rows_are_cached_until_cleared(self):
        self.assertIs(cohort.rows(self.dataset, "combined", self.models),
                      cohort.rows(self.dataset, "combined", self.models))
        first = cohort.rows(self.dataset, "combined", self.models)
        cohort.clear_cache()
        self.assertIsNot(cohort.rows(self.dataset, "combined", self.models), first)

    def test_events_and_course(self):
        events = cohort.events(self.dataset, cohort.USUAL_CARE)
        self.assertEqual(set(events), {r["patient_id"] for r in self.rows})
        pid = next(p for p, found in events.items() if found)
        course = cohort.course(self.dataset, cohort.USUAL_CARE, pid)
        self.assertEqual(course["events"], events[pid])
        weeks = course["observations"]["week"]
        self.assertEqual(weeks, list(range(len(weeks))))
        self.assertEqual(len(course["observations"]["spo2_percent"]), len(weeks))
        self.assertIsNone(cohort.course(self.dataset, cohort.USUAL_CARE, "X"))

    def test_load_cohort_with_chosen_scenarios(self):
        from django.core.management import call_command
        call_command("load_cohort", n=9, seed=1, scenarios=["usual_care", "lung_monitoring"],
                     stdout=open("/dev/null", "w"))
        dataset = cohort.newest()
        self.assertEqual(cohort.scenario_ids(dataset), ["usual_care", "lung_monitoring"])
        self.assertEqual(Patient.objects.count(), 9)
