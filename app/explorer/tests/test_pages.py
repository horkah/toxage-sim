from django.conf import settings
import threading
from unittest import mock

from django.db import OperationalError, connection
from django.test import TestCase, TransactionTestCase, override_settings

from explorer import cohort, params, store
from explorer.models import Course, Dataset, Patient, Setting
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
        self.assertContains(response, "delete scenario", count=7)
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
        # Stored directly: the parameters page refuses this value (see ParameterCheckTest).
        Setting.objects.create(pk="parameters", value={"simulation/weeks": 0})
        with self.assertLogs("explorer.store", "ERROR") as logged:
            self.client.post("/data/generate/", {"n": "9", "seed": "2"})
        self.assertIn("simulation weeks must be a whole number of at least 1", logged.output[0])
        failed = Dataset.objects.first()
        self.assertEqual(failed.status, "failed")
        self.assertIn("simulation weeks", failed.message)
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
        self.assertEqual(Course.objects.count(), 6 * self.n)
        self.assertFalse(store.delete_scenario(self.dataset, "unknown"))

    def test_a_busy_database_does_not_turn_a_deletion_into_an_error(self):
        other = store.generate(6, 3, ["usual_care"], wait=True)

        def busy(*args, **kwargs):
            raise OperationalError("database is locked")
        with mock.patch.object(store, "connection") as fake:
            fake.vendor, fake.in_atomic_block = "sqlite", False
            fake.cursor.return_value.__enter__.return_value.execute.side_effect = busy
            with self.assertLogs("explorer.store", "WARNING"):
                response = self.client.post("/data/delete/", {"dataset": other.pk})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Dataset.objects.filter(pk=other.pk).exists())

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

    def test_a_page_beyond_the_end_shows_the_last_page(self):
        url = f"/data/{self.dataset.pk}/records/?table=outcome&scenario=combined"
        context = self.client.get(url + "&page=100000").context
        self.assertEqual(context["page"], 1)       # 30 records: one page
        self.assertEqual(len(context["rows"]), self.n)

    def test_looking_for_interrupted_data_sets_writes_nothing_if_there_are_none(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as queries:
            store.mark_interrupted()
        self.assertFalse([q for q in queries if q["sql"].lstrip().upper().startswith("UPDATE")])

    def test_records_link_to_patients_and_the_schema(self):
        response = self.client.get(f"/data/{self.dataset.pk}/records/?table=outcome&scenario=combined&patient=3")
        self.assertContains(response, f'href="/?dataset={self.dataset.pk}&amp;scenario=combined&amp;patient=P000003"')
        self.assertContains(response, 'href="/schema/#outcome-qaly"')

    def test_data_page_links_and_warnings(self):
        response = self.client.get("/data/")
        self.assertContains(response, f'href="/?dataset={self.dataset.pk}&amp;scenario=combined"')
        self.assertContains(response, f'href="/data/{self.dataset.pk}/archive/"')
        self.assertContains(response, 'data-confirm-title="Delete this data set?"')
        self.assertContains(response, 'data-confirm-title="Delete this scenario?"', count=7)

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
        self.assertEqual(len(b"".join(every.streaming_content).decode().splitlines()), 7 * self.n + 1)
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
    PATH = "ild/hazard_ratios/low_spo2/value"

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

    def test_citations_in_the_notes_link_to_the_references(self):
        self.assertContains(self.client.get("/parameters/risk/"),
                            '<a href="/documents/references/#powell-2022">Powell et al. (2022)</a>')

    def test_saving_in_place_answers_with_the_page(self):
        response = self.client.post("/parameters/risk/", {f"p:{self.PATH}": "3"}, headers={"X-Toxage-Fetch": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Saved.")
        self.assertContains(response, 'class="changed"')
        self.assertContains(response, f'id="param-{self.PATH.replace("/", "--")}"')
        self.assertEqual(params.changes("risk"), {self.PATH: 3})

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


class AboutTest(TestCase):
    def setUp(self):
        self.client.cookies[COOKIE] = settings.DISCLAIMER_VERSION

    def test_about_page_and_footer_show_the_version(self):
        from toxage_app.version import BUILD, VERSION
        response = self.client.get("/about/")
        self.assertEqual(response.context["section"], "about")
        self.assertContains(response, f"Version {VERSION}")
        self.assertContains(response, f"Build {BUILD}")
        self.assertContains(response, "https://github.com/horkah")
        self.assertContains(response, "Authors and credits")
        self.assertContains(self.client.get("/schema/"), f"toxage-sim {VERSION} · build {BUILD}")

    def test_every_build_loads_new_scripts(self):
        from urllib.parse import quote
        from toxage_app.version import BUILD, VERSION
        page = self.client.get("/about/")
        self.assertContains(page, f"explorer/app.js?v={VERSION}-{quote(BUILD, safe='')}")
        script = self.client.get("/static/explorer/tour-steps.js")
        self.assertEqual(script["Cache-Control"], "no-cache")     # the browser asks every time
        self.assertTrue(script.has_header("Last-Modified"))

    def test_version_follows_the_environment_and_the_build_file(self):
        import importlib
        import os
        from unittest import mock
        from toxage_app import version
        with mock.patch.dict(os.environ, {"TOXAGE_BUILD": "20990101.0000 (abc1234)"}):
            self.assertEqual(importlib.reload(version).BUILD, "20990101.0000 (abc1234)")
        importlib.reload(version)
        self.assertRegex(version.VERSION, r"^\d+\.\d+\.\d+$")


class ReferenceTest(TestCase):
    def setUp(self):
        self.client.cookies[COOKIE] = settings.DISCLAIMER_VERSION

    def test_schema_page(self):
        response = self.client.get("/schema/")
        self.assertEqual([t["name"] for t in response.context["schema_tables"]], list(toxage_schema.TABLES))
        self.assertContains(response, 'id="outcome-qaly"')     # anchors of the fields, linked from other pages
        self.assertContains(response, "usual_care_grade")
        self.assertContains(response, "Quality-adjusted life years")

    def test_documents(self):
        response = self.client.get("/documents/")
        self.assertContains(response, "Toxicity report")
        response = self.client.get("/documents/report/")
        self.assertContains(response, "Candidates for risk models")
        self.assertContains(response, 'href="#8-candidates-for-risk-models"')     # headings in the side bar
        self.assertEqual(self.client.get("/documents/prompts/").status_code, 404)
        self.assertEqual(self.client.get("/documents/internal/").status_code, 404)
        self.assertEqual(self.client.get("/documents/x/").status_code, 404)

    def test_pages_need_the_disclaimer(self):
        self.client.cookies.clear()
        for url in ("/data/", "/parameters/", "/schema/", "/documents/"):
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_menu_reaches_every_section(self):
        response = self.client.get("/schema/")
        for url in ("/", "/data/", "/parameters/", "/documents/", "/about/", "/disclaimer/"):
            self.assertContains(response, f'href="{url}"')


class RunningTest(TransactionTestCase):
    """A request that looks for interrupted data sets while a new one is
    being created must not take the new one for interrupted."""

    def test_a_new_data_set_is_not_taken_for_interrupted(self):
        create = Dataset.objects.create
        others = []

        def create_while_another_request_looks(**kwargs):
            dataset = create(**kwargs)
            # Another request (another thread and connection) looks right now.
            def look():
                store.mark_interrupted()
                connection.close()
            other = threading.Thread(target=look)
            other.start()
            other.join(0.3)
            others.append(other)
            return dataset

        with mock.patch.object(Dataset.objects, "create", create_while_another_request_looks), \
                mock.patch.object(store, "_run"):     # no generating; the data set stays "running"
            dataset = store.generate(3, 1, ["usual_care"], wait=False)
        others[0].join(5)
        dataset.refresh_from_db()
        self.assertEqual(dataset.status, Dataset.RUNNING, dataset.message)
        store._RUNNING.discard(dataset.pk)
        store.mark_interrupted()
        dataset.refresh_from_db()
        self.assertEqual(dataset.message, "Interrupted by a restart of the app")


@override_settings(ASYNC_JOBS=False)
class ParameterCheckTest(CohortTestCase):
    """Values of the right type that break the models are refused (finding M1)."""
    n = 6
    RATE = "severe_toxicity_90d/regimen_rates/olaparib/rate"

    def setUp(self):
        super().setUp()
        self.client.cookies[COOKIE] = settings.DISCLAIMER_VERSION

    def test_values_that_break_the_risk_models_are_refused(self):
        for path, value in ((self.RATE, "1"), (self.RATE, "0"), (self.RATE, "2"),
                            ("ild/hazard_ratios/low_spo2/value", "-1")):
            with self.subTest(path=path, value=value):
                errors = params.save("risk", {path: value})
                self.assertIn("not saved", errors[path])
                self.assertEqual(params.changes("risk"), {})
        self.assertEqual(params.save("risk", {self.RATE: "0.6"}), {})
        self.assertEqual(params.changes("risk"), {self.RATE: 0.6})

    def test_values_that_break_the_engine_are_refused(self):
        for path, value in (("simulation/weeks", "0"), ("simulation/calibration_weeks", "0")):
            with self.subTest(path=path):
                errors = params.save("parameters", {path: value})
                self.assertIn("the simulation fails", errors[path])
        self.assertEqual(params.changes("parameters"), {})

    def test_the_page_shows_why(self):
        response = self.client.post("/parameters/risk/", {f"p:{self.RATE}": "1"}, headers={"X-Toxage-Fetch": "1"})
        self.assertContains(response, "not saved: the model")
        self.assertContains(response, 'value="1"')        # the refused value is shown again

    def test_stored_values_that_break_the_models_give_a_clear_page(self):
        rate = f"severe_toxicity_90d/regimen_rates/{self.rows[0]['regimen']}/rate"   # a regimen of the cohort
        Setting.objects.create(pk="risk", value={rate: 1})
        cohort.clear_cache()
        with self.assertLogs("explorer.views", "ERROR"):
            response = self.client.get("/")
        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "The risk models cannot be computed", status_code=500)
        self.assertContains(response, 'href="/parameters/risk/"', status_code=500)

    def test_an_archive_with_broken_parameters_is_refused(self):
        import gzip
        from django.core.files.uploadedfile import SimpleUploadedFile
        from explorer import archive
        lines = [line for line in archive.lines()]
        lines[1] = '{"type":"parameters","changes":{"risk":{"%s":1}}}\n' % self.RATE
        upload = SimpleUploadedFile("a.jsonl.gz", gzip.compress("".join(lines).encode()))
        response = self.client.post("/data/import/", {"archive": upload, "mode": "replace"})
        self.assertContains(response, "do not work in this app")
        self.assertEqual(params.all_changes(), {})
        self.assertEqual(Dataset.objects.count(), 1)


@override_settings(ASYNC_JOBS=False)
class GenerationTest(CohortTestCase):
    """One generation at a time, and deleting a data set stops its generation (finding M2)."""
    n = 6

    def setUp(self):
        super().setUp()
        self.client.cookies[COOKIE] = settings.DISCLAIMER_VERSION

    def test_a_second_generation_is_refused_while_one_runs(self):
        with mock.patch.object(store, "_run"):          # the first one stays "running"
            first = store.generate(6, 3, ["usual_care"], name="First", wait=False)
        try:
            response = self.client.post("/data/generate/", {"n": "6", "seed": "4"})
            self.assertContains(response, "A data set is being generated. Please wait until it is ready.")
            self.assertFalse(Dataset.objects.filter(seed=4).exists())
            with self.assertRaises(store.Busy):
                store.generate(6, 4, wait=True)
        finally:
            store._RUNNING.discard(first.pk)
        self.assertEqual(store.generate(6, 4, ["usual_care"], wait=True).status, Dataset.READY)

    def test_deleting_a_data_set_stops_its_generation_quietly(self):
        real = store.engine.generate

        def generate_and_meanwhile_delete(n, seed, scenarios, validate, config, progress):
            data = real(n, seed, scenarios, validate=validate, config=config)
            Dataset.objects.filter(name="Doomed").delete()      # e.g. "Stop the demo" or "Delete all"
            progress(1, 1)
            return data

        with mock.patch.object(store.engine, "generate", generate_and_meanwhile_delete), \
                self.assertNoLogs("explorer.store", "ERROR"):
            store.generate(6, 3, ["usual_care"], name="Doomed", wait=True)
        self.assertFalse(Dataset.objects.filter(name="Doomed").exists())
        self.assertFalse(store._RUNNING)


@override_settings(ASYNC_JOBS=False, DISK_LIMIT_MB=100)
class DiskLimitTest(CohortTestCase):
    """The database stays within its limit on disk (TOXAGE_DISK_LIMIT_MB)."""
    n = 6

    def setUp(self):
        super().setUp()
        self.client.cookies[COOKIE] = settings.DISCLAIMER_VERSION

    def test_a_data_set_that_would_not_fit_is_not_generated(self):
        # 90 MB used, 10 MB free; 1500 patients under 7 scenarios need about 25 MB
        # (5.5 KB for usual care and 11 KB for what the other six add).
        with mock.patch.object(store, "used_bytes", return_value=90e6):
            response = self.client.post("/data/generate/", {"n": "1500", "seed": "4"})
            self.assertContains(response, "Not generated: the new data set would need about 25 MB, "
                                          "but only 10 MB of the limit of 100 MB are free")
            self.assertContains(response, "Delete other data sets, or choose fewer patients or scenarios.")
            self.assertFalse(Dataset.objects.filter(seed=4).exists())
            self.assertContains(response, 'name="n" value="1500"')     # the form keeps what was entered
            self.assertContains(response, 'name="seed" value="4"')
            # One scenario of 300 patients (1.7 MB) fits.
            self.client.post("/data/generate/", {"n": "300", "seed": "4", "scenarios": ["usual_care"]})
        self.assertEqual(Dataset.objects.get(seed=4).status, Dataset.READY)

    def test_a_data_set_that_did_not_fit_is_deleted_again(self):
        # The estimate fits, but afterwards the database is larger than the limit.
        sizes = iter([20e6, 20e6, 130e6, 20e6])     # check, before filling, after filling, page
        with mock.patch.object(store, "used_bytes", side_effect=lambda: next(sizes)):
            dataset = store.generate(6, 4, ["usual_care"], name="Too big", wait=True)
        self.assertEqual(dataset.status, Dataset.FAILED)
        self.assertEqual(dataset.message, "Deleted again: the data set needed 110 MB, more than the 80 MB "
                                          "that were free of the limit of 100 MB. Delete other data sets, "
                                          "or generate a smaller one.")
        self.assertFalse(Patient.objects.filter(dataset=dataset).exists())
        self.assertFalse(Course.objects.filter(patient__dataset=dataset).exists())

    def test_the_data_page_shows_the_limit(self):
        with mock.patch.object(store, "used_bytes", return_value=21.7e6):
            response = self.client.get("/data/")
        self.assertContains(response, "The database uses 21.7 MB of 100 MB on disk.")
        self.assertContains(response, 'data-free-bytes="78300000"')
        self.assertContains(response, f'data-full-bytes="{store.BYTES_PER_COURSE}"')
        self.assertContains(response, 'value="lung_monitoring" data-extra-bytes="200"')
