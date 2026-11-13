import gzip
import io
import json

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from explorer import archive, params, store
from explorer.models import Course, Dataset, Patient

from .helpers import CohortTestCase

COOKIE = settings.DISCLAIMER_COOKIE


def text_of(response):
    return gzip.decompress(b"".join(response.streaming_content)).decode()


def upload(text, name="archive.jsonl.gz", compress=True):
    data = text.encode()
    return SimpleUploadedFile(name, gzip.compress(data) if compress else data)


@override_settings(ASYNC_JOBS=False)
class ArchiveTest(CohortTestCase):
    n = 12

    def setUp(self):
        super().setUp()
        self.client.cookies[COOKIE] = settings.DISCLAIMER_VERSION
        params.save("risk", {"ild/window_days": "365"})

    def snapshot(self):
        """Everything an archive holds, without the database ids."""
        found = []
        for d in Dataset.objects.order_by("created", "name"):
            courses = sorted((c.patient.patient_id, c.scenario_id, json.dumps(c.outcome, sort_keys=True),
                              json.dumps(c.events), json.dumps(c.alerts), json.dumps(c.observations))
                             for c in Course.objects.filter(patient__dataset=d).select_related("patient"))
            patients = list(d.patients.order_by("patient_id").values_list("patient_id", "baseline"))
            found.append((d.name, d.n, d.seed, d.created, d.metadata, d.scenarios, d.settings, d.calibrated,
                          patients, courses))
        return found

    def test_export_of_everything(self):
        response = self.client.get("/data/archive/")
        self.assertEqual(response["Content-Type"], "application/gzip")
        self.assertIn('filename="toxage-sim-', response["Content-Disposition"])
        lines = [json.loads(line) for line in text_of(response).splitlines()]
        self.assertEqual(lines[0]["format"], archive.FORMAT)
        self.assertEqual(lines[0]["content"], "app")
        self.assertEqual(lines[1], {"type": "parameters", "changes": {"risk": {"ild/window_days": 365}}})
        self.assertEqual([r["type"] for r in lines].count("patient"), self.n)
        self.assertEqual(lines[-1], {"type": "end", "datasets": 1, "patients": self.n})
        patient = next(r for r in lines if r["type"] == "patient")
        self.assertEqual(len(patient["courses"]), 7)

    def test_replace_brings_back_exactly_what_was_exported(self):
        before = self.snapshot()
        text = text_of(self.client.get("/data/archive/"))
        store.generate(6, 3, ["usual_care"], name="Later", wait=True)
        params.reset()
        params.save("parameters", {"simulation/weeks": "104"})
        response = self.client.post("/data/import/", {"archive": upload(text), "mode": "replace"})
        self.assertRedirects(response, "/data/", fetch_redirect_response=False)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(params.all_changes(), {"risk": {"ild/window_days": 365}})

    def test_add_keeps_what_is_there(self):
        text = text_of(self.client.get(f"/data/{self.dataset.pk}/archive/"))
        self.assertNotIn('"type":"parameters"', text)
        params.save("parameters", {"simulation/weeks": "104"})
        response = self.client.post("/data/import/", {"archive": upload(text, compress=False), "mode": "add"},
                                    headers={"X-Toxage-Fetch": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Toxage-Location"], "/data/")
        self.assertContains(response, f"Imported 1 data set with {self.n} patients.")
        self.assertEqual(Dataset.objects.count(), 2)
        self.assertEqual(Patient.objects.count(), 2 * self.n)
        self.assertEqual(Course.objects.count(), 2 * 7 * self.n)
        self.assertEqual(params.changes("parameters"), {"simulation/weeks": 104})
        copy = Dataset.objects.exclude(pk=self.dataset.pk).get()
        self.assertEqual(list(store.records(copy, "event", "combined")),
                         list(store.records(self.dataset, "event", "combined")))

    def test_broken_files_change_nothing(self):
        good = text_of(self.client.get("/data/archive/"))
        lines = good.splitlines(keepends=True)
        header = json.loads(lines[0])
        newer = json.dumps({**header, "format_version": archive.FORMAT_VERSION + 1}) + "\n"
        damaged = good.replace('"patients":%d}' % self.n, '"patients":%d}' % (self.n + 1))
        cases = {
            "not an archive": "hello\n",
            "not toxage": json.dumps({"type": "archive", "format": "other"}) + "\n",
            "newer format": newer + "".join(lines[1:]),
            "cut off": "".join(lines[:-3]),
            "counts differ": damaged,
            "bad record": "".join(lines[:3]).replace('"tumour_type":"', '"tumour_type":"x') + lines[-1],
        }
        before = self.snapshot()
        for name, text in cases.items():
            with self.subTest(name):
                response = self.client.post("/data/import/", {"archive": upload(text), "mode": "replace"})
                self.assertContains(response, "The archive was not imported.")
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(params.all_changes(), {"risk": {"ild/window_days": 365}})
        self.assertContains(self.client.post("/data/import/", {"mode": "add"}), "Please choose an archive file.")

    def test_messages_name_the_problem(self):
        with self.assertRaisesMessage(archive.ArchiveError, "format version 99"):
            archive.load(io.BytesIO(b'{"type":"archive","format":"toxage-sim-archive","format_version":99}\n'))
        with self.assertRaisesMessage(archive.ArchiveError, "incomplete"):
            archive.load(io.BytesIO(b'{"type":"archive","format":"toxage-sim-archive","format_version":1}\n'))
        with self.assertRaisesMessage(archive.ArchiveError, "empty"):
            archive.load(io.BytesIO(b""))

    @override_settings(READ_ONLY=True)
    def test_read_only_mode_exports_but_does_not_import(self):
        self.assertEqual(self.client.get("/data/archive/").status_code, 200)
        text = text_of(self.client.get("/data/archive/"))
        self.assertEqual(self.client.post("/data/import/", {"archive": upload(text)}).status_code, 403)
        self.assertNotContains(self.client.get("/data/"), 'action="/data/import/"')

    def test_import_needs_post_and_unknown_data_sets_are_not_found(self):
        self.assertEqual(self.client.get("/data/import/").status_code, 405)
        self.assertEqual(self.client.get("/data/999/archive/").status_code, 404)
