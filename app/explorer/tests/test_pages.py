from django.conf import settings
from django.test import TestCase, override_settings

from explorer import cohort, params, store
from explorer.models import Course, Dataset, Patient
from schema import toxage_schema

from .helpers import CohortTestCase

COOKIE = settings.DISCLAIMER_COOKIE


@override_settings(ASYNC_JOBS=False)
class DataTest(CohortTestCase):
    n = 30

    def setUp(self):
        super().setUp()
        self.client.cookies[COOKIE] = settings.DISCLAIMER_VERSION

    def test_data_page_lists_the_data_set(self):
        response = self.client.get("/data/")
        self.assertContains(response, self.dataset.name)
        self.assertContains(response, "shown in the explorer")
        self.assertContains(response, "Generate a data set")
        self.assertContains(response, "delete scenario", count=6)
        self.assertEqual(response.context["section"], "data")

    def test_generate_with_chosen_scenarios_and_name(self):
        response = self.client.post("/data/generate/", {"n": "12", "seed": "4", "name": "Small",
                                                        "scenarios": ["usual_care", "combined", "nonsense"]})
        self.assertRedirects(response, "/data/")
        new = Dataset.objects.get(name="Small")
        self.assertEqual((new.status, new.n, new.seed, new.progress), ("ready", 12, 4, 1))
        self.assertEqual(cohort.scenario_ids(new), ["usual_care", "combined"])
        self.assertEqual(new.patients.count(), 12)
        self.assertEqual(Course.objects.filter(patient__dataset=new).count(), 24)
        self.assertEqual(new.metadata["records"]["combined"]["observation"],
                         sum(1 for _ in store.records(new, "observation", "combined")))
        self.assertEqual(Dataset.objects.count(), 2)
        self.assertEqual(cohort.newest(), new)

    def test_generate_limits_the_input(self):
        self.client.post("/data/generate/", {"n": "1", "seed": "x"})
        new = Dataset.objects.first()
        self.assertEqual((new.n, new.seed, new.name), (3, 1, "3 patients, seed 1"))

    def test_generate_uses_changed_parameters_and_calibrates(self):
        params.save("parameters", {"calibration/patients": "300", "calibration/iterations": "1",
                                   "simulation/weeks": "60"})
        params.save("risk", {"ild/window_days": "365"})
        self.client.post("/data/generate/", {"n": "9", "seed": "2", "scenarios": ["usual_care"], "recalibrate": "yes"})
        new = Dataset.objects.first()
        self.assertEqual(new.status, "ready", new.message)
        self.assertTrue(new.calibrated)
        self.assertEqual(new.metadata["weeks"], 60)
        self.assertEqual(set(new.settings), {"parameters"})
        self.assertLessEqual(max(o["follow_up_days"] for o in store.records(new, "outcome", "usual_care")), 420)
        self.assertContains(self.client.get("/data/"), "3 parameters changed, event rates calibrated again")

    def test_failure_is_shown(self):
        params.save("parameters", {"simulation/weeks": "0"})
        self.client.post("/data/generate/", {"n": "9", "seed": "2"})
        failed = Dataset.objects.first()
        self.assertEqual(failed.status, "failed")
        self.assertContains(self.client.get("/data/"), "Failed:")
        self.assertEqual(cohort.newest(), self.dataset)

    def test_interrupted_data_sets_are_marked(self):
        Dataset.objects.create(name="Cut", n=3, seed=1)
        self.assertContains(self.client.get("/data/"), "Interrupted by a restart")

    def test_delete_scenario(self):
        self.client.post("/data/delete/", {"dataset": self.dataset.pk, "scenario": "combined"})
        self.dataset.refresh_from_db()
        self.assertNotIn("combined", cohort.scenario_ids(self.dataset))
        self.assertNotIn("combined", self.dataset.metadata["records"])
        self.assertFalse(Course.objects.filter(scenario_id="combined").exists())
        self.assertEqual(Course.objects.count(), 5 * self.n)
        self.assertFalse(store.delete_scenario(self.dataset, "unknown"))

    def test_last_scenario_stays(self):
        for sid in cohort.scenario_ids(self.dataset)[1:]:
            self.assertTrue(store.delete_scenario(self.dataset, sid))
        self.assertFalse(store.delete_scenario(self.dataset, "usual_care"))
        self.assertEqual(Course.objects.count(), self.n)

    def test_delete_data_set_and_all(self):
        other = store.generate(6, 3, ["usual_care"], wait=True)
        self.client.post("/data/delete/", {"dataset": other.pk})
        self.assertEqual(list(Dataset.objects.all()), [self.dataset])
        store.generate(6, 3, ["usual_care"], wait=True)
        self.client.post("/data/delete/", {"all": "yes"})
        self.assertEqual((Dataset.objects.count(), Patient.objects.count(), Course.objects.count()), (0, 0, 0))
        self.assertContains(self.client.get("/"), "No data yet")
        self.assertEqual(self.client.post("/data/delete/", {"dataset": 999}).status_code, 404)

    def test_use_chooses_the_data_set_of_the_explorer(self):
        other = store.generate(6, 3, ["usual_care"], name="Other", wait=True)
        self.assertEqual(self.client.get("/").context["dataset"], other)
        response = self.client.post("/data/use/", {"dataset": self.dataset.pk})
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(self.client.get("/").context["dataset"], self.dataset)
        self.assertEqual(self.client.get(f"/?dataset={other.pk}").context["dataset"], other)
        self.assertEqual(self.client.get("/").context["dataset"], other)

    def test_changes_need_post(self):
        for url in ("/data/generate/", "/data/delete/", "/data/use/"):
            self.assertEqual(self.client.get(url).status_code, 405)

    @override_settings(READ_ONLY=True)
    def test_read_only_mode(self):
        self.assertEqual(self.client.post("/data/generate/", {"n": "9"}).status_code, 403)
        self.assertEqual(self.client.post("/data/delete/", {"all": "yes"}).status_code, 403)
        self.assertEqual(self.client.post("/parameters/risk/", {"action": "reset_all"}).status_code, 403)
        self.assertEqual(Dataset.objects.count(), 1)
        self.assertNotContains(self.client.get("/data/"), "Generate a data set")
        self.assertEqual(self.client.post("/data/use/", {"dataset": self.dataset.pk}).status_code, 302)

    def test_records_of_every_table(self):
        for table in store.TABLES:
            response = self.client.get(f"/data/{self.dataset.pk}/records/?table={table}&scenario=combined")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["table"], table)
            self.assertEqual(len(response.context["fields"]), len(toxage_schema.fields(table)))
        self.assertEqual(self.client.get(f"/data/{self.dataset.pk}/records/?table=x").context["table"], "baseline")
        self.assertEqual(self.client.get("/data/999/records/").status_code, 404)

    def test_records_are_paged_and_follow_the_schema(self):
        url = f"/data/{self.dataset.pk}/records/?table=observation&scenario=usual_care"
        first = self.client.get(url).context
        self.assertEqual((len(first["rows"]), first["more"], first["page"]), (50, True, 1))
        second = self.client.get(url + "&page=2").context
        self.assertNotEqual(first["rows"], second["rows"])
        one = self.client.get(url + "&patient=3").context
        self.assertEqual({row[1] for row in one["rows"]}, {"P000003"})
        for table in store.TABLES:
            toxage_schema.validate(table, list(store.records(self.dataset, table, "combined")))

    def test_export(self):
        response = self.client.get(f"/data/{self.dataset.pk}/export/outcome.csv?scenario=combined")
        lines = b"".join(response.streaming_content).decode().splitlines()
        self.assertEqual(lines[0].split(","), toxage_schema.fields("outcome"))
        self.assertEqual(len(lines), self.n + 1)
        self.assertIn("attachment", response["Content-Disposition"])
        every = self.client.get(f"/data/{self.dataset.pk}/export/outcome.csv")
        self.assertEqual(len(b"".join(every.streaming_content).decode().splitlines()), 6 * self.n + 1)
        baseline = self.client.get(f"/data/{self.dataset.pk}/export/baseline.csv")
        self.assertEqual(len(b"".join(baseline.streaming_content).decode().splitlines()), self.n + 1)
        self.assertEqual(self.client.get(f"/data/{self.dataset.pk}/export/x.csv").status_code, 404)

    def test_exported_csv_can_be_read_back(self):
        import tempfile
        from pathlib import Path
        text = "".join(store.csv_lines(self.dataset, "event", ["combined"]))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "event.csv"
            path.write_text(text, encoding="utf-8")
            self.assertEqual(toxage_schema.read_csv(path, "event"),
                             list(store.records(self.dataset, "event", "combined")))


class ParameterPageTest(TestCase):
    PATH = "ild/hazard_ratios/spo2_below_95/value"

    def setUp(self):
        self.client.cookies[COOKIE] = settings.DISCLAIMER_VERSION

    def test_pages_of_all_sources(self):
        self.assertEqual(self.client.get("/parameters/").context["source"].key, "parameters")
        for key in params.SOURCES:
            response = self.client.get(f"/parameters/{key}/")
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, params.SOURCES[key].path)
            self.assertEqual(response.context["section"], "parameters")
        self.assertEqual(self.client.get("/parameters/x/").status_code, 404)

    def test_save_and_reset_one_value(self):
        response = self.client.post("/parameters/risk/", {"action": "save", f"p:{self.PATH}": "3"})
        self.assertRedirects(response, "/parameters/risk/?saved=1")
        self.assertEqual(params.changes("risk"), {self.PATH: 3})
        page = self.client.get("/parameters/risk/?saved=1")
        self.assertContains(page, "Saved.")
        self.assertEqual((page.context["changed_here"], page.context["changed_total"]), (1, 1))
        self.client.post("/parameters/risk/", {"action": f"reset:{self.PATH}"})
        self.assertEqual(params.changes("risk"), {})

    def test_invalid_value_is_shown_again(self):
        response = self.client.post("/parameters/risk/", {"action": "save", f"p:{self.PATH}": "many"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "must be a number")
        self.assertContains(response, 'value="many"')
        self.assertEqual(params.changes("risk"), {})

    def test_reset_section_and_everything(self):
        params.save("risk", {self.PATH: "3"})
        params.save("parameters", {"simulation/weeks": "104"})
        self.client.post("/parameters/risk/", {"action": "reset_source"})
        self.assertEqual(set(params.all_changes()), {"parameters"})
        self.client.post("/parameters/risk/", {"action": "reset_all"})
        self.assertEqual(params.all_changes(), {})


class RiskParameterTest(CohortTestCase):
    n = 60

    def test_changed_risk_parameters_change_the_risks_shown(self):
        patient = next(r for r in self.rows if r["ecog"] >= 2)
        before = patient["risk_severe90"]
        params.save("risk", {"severe_toxicity_90d/odds_ratios/ecog_2_or_higher/value": "5"})
        cohort.clear_cache()
        _, _, rows = cohort.current()
        after = cohort.find(rows, patient["patient_id"])["risk_severe90"]
        self.assertGreater(after, before)


class ReferenceTest(TestCase):
    def setUp(self):
        self.client.cookies[COOKIE] = settings.DISCLAIMER_VERSION

    def test_schema_page(self):
        response = self.client.get("/schema/")
        self.assertEqual([t["name"] for t in response.context["tables"]], list(toxage_schema.TABLES))
        self.assertContains(response, "usual_care_grade")
        self.assertContains(response, "Quality-adjusted life years")

    def test_documents(self):
        response = self.client.get("/documents/")
        self.assertContains(response, "Toxicity report")
        response = self.client.get("/documents/report/")
        self.assertContains(response, "Candidates for risk models")
        self.assertContains(response, "On this page")
        self.assertContains(self.client.get("/documents/prompts/"), "prompting.log")
        self.assertEqual(self.client.get("/documents/x/").status_code, 404)

    def test_pages_need_the_disclaimer(self):
        self.client.cookies.clear()
        for url in ("/data/", "/parameters/", "/schema/", "/documents/"):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_menu_reaches_every_section(self):
        response = self.client.get("/schema/")
        for url in ("/data/", "/parameters/", "/schema/", "/documents/", "/?view=time", "/?view=interventions",
                    "/disclaimer/"):
            self.assertContains(response, f'href="{url}"')
