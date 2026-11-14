"""Courses are stored without duplicates and read back complete (courses.py)."""
import gzip
import importlib

from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings

from engine import generate as engine
from explorer import archive, cohort, courses, params, store
from explorer.models import Course, Dataset

FIELDS = courses.FIELDS
N, SEED = 30, 5


_ENGINE = {}


def engine_records(table, scenario_id):
    """The records of the engine itself for the test cohort, as truth."""
    if "data" not in _ENGINE:
        _ENGINE["data"] = engine.generate(N, SEED, validate=False, config=params.engine_config())
    data = _ENGINE["data"]
    return sorted((r for r in data[table] if r["scenario_id"] == scenario_id),
                  key=lambda r: (r["patient_id"], r.get("week", 0), r.get("day", 0)))


def app_records(dataset, table, scenario_id):
    """The records as the app reads them back."""
    return sorted(store.records(dataset, table, scenario_id),
                  key=lambda r: (r["patient_id"], r.get("week", 0), r.get("day", 0)))


def nulls(dataset, scenario_id=None):
    """Number of fields stored as "same as base"."""
    found = Course.objects.filter(patient__dataset=dataset)
    if scenario_id:
        found = found.filter(scenario_id=scenario_id)
    return sum(found.filter(**{f"{f}__isnull": True}).count() for f in FIELDS)


@override_settings(ASYNC_JOBS=False)
class DeduplicationTest(TestCase):
    TABLES = ("outcome", "event", "alert", "observation")

    def setUp(self):
        self.dataset = store.generate(N, SEED, wait=True)
        self.ids = [s["scenario_id"] for s in self.dataset.scenarios]
        self.truth = {(t, s): engine_records(t, s) for t in self.TABLES for s in self.ids}

    def assert_complete(self, dataset, ids):
        for table in self.TABLES:
            for sid in ids:
                with self.subTest(table=table, scenario=sid):
                    self.assertEqual(app_records(dataset, table, sid), self.truth[(table, sid)])

    def test_identical_fields_are_stored_once_and_read_back_complete(self):
        self.assertEqual(courses.base_of(self.dataset), "usual_care")
        self.assertEqual(self.dataset.metadata["base"], "usual_care")
        self.assertEqual(nulls(self.dataset, "usual_care"), 0)          # the base is complete
        self.assertGreater(nulls(self.dataset), N * 3)                  # duplicates are not stored
        self.assert_complete(self.dataset, self.ids)

    def test_the_explorer_reads_complete_courses(self):
        for sid in self.ids:
            rows = cohort.rows(self.dataset, sid, cohort.risk_models())
            truth = {r["patient_id"]: r for r in self.truth[("outcome", sid)]}
            plain = lambda r: {k: v for k, v in r.items() if k != "scenario_id"}
            self.assertEqual([{k: r[k] for k in plain(truth[r["patient_id"]])} for r in rows],
                             [plain(truth[r["patient_id"]]) for r in rows])
            events = cohort.events(self.dataset, sid)
            self.assertEqual(sorted(e for found in events.values() for e in map(repr, found)),
                             sorted(repr({k: v for k, v in e.items() if k not in ("scenario_id", "patient_id")})
                                    for e in self.truth[("event", sid)]))
            one = cohort.course(self.dataset, sid, "P000003")
            self.assertEqual(len(one["observations"]["week"]),
                             sum(r["patient_id"] == "P000003" for r in self.truth[("observation", sid)]))

    def test_deleting_the_base_scenario_keeps_every_other_course(self):
        self.assertTrue(store.delete_scenario(self.dataset, "usual_care"))
        self.dataset.refresh_from_db()
        left = [s for s in self.ids if s != "usual_care"]
        self.assertEqual(courses.base_of(self.dataset), left[0])
        self.assertEqual(nulls(self.dataset, left[0]), 0)               # the new base is complete
        self.assertGreater(nulls(self.dataset), 0)                      # duplicates against it removed
        self.assertFalse(Course.objects.filter(scenario_id="usual_care").exists())
        self.assert_complete(self.dataset, left)
        # And once more: the second base goes as well.
        store.delete_scenario(self.dataset, left[0])
        self.dataset.refresh_from_db()
        self.assertEqual(courses.base_of(self.dataset), left[1])
        self.assert_complete(self.dataset, left[1:])

    def test_deleting_another_scenario_keeps_the_base(self):
        store.delete_scenario(self.dataset, "combined")
        self.dataset.refresh_from_db()
        self.assertEqual(courses.base_of(self.dataset), "usual_care")
        self.assert_complete(self.dataset, [s for s in self.ids if s != "combined"])

    def test_archives_hold_complete_courses_and_import_deduplicates(self):
        text = gzip.decompress(b"".join(
            archive.gzipped(archive.lines([self.dataset])))).decode()
        self.assertNotIn('"outcome":null', text)
        self.assertNotIn('"observations":null', text)
        archive.load(SimpleUploadedFile("a.jsonl.gz", gzip.compress(text.encode())), replace=True)
        copy = Dataset.objects.get()
        self.assertEqual(copy.metadata["base"], "usual_care")
        self.assertGreater(nulls(copy), N * 3)
        self.assert_complete(copy, self.ids)

    def test_the_migration_compresses_data_sets_stored_before(self):
        # A data set as the old version stored it: every field complete, no base noted.
        courses._copy_from_base(self.dataset, "usual_care")
        Dataset.objects.filter(pk=self.dataset.pk).update(
            metadata={k: v for k, v in self.dataset.metadata.items() if k != "base"})
        self.assertEqual(nulls(self.dataset), 0)
        migration = importlib.import_module("explorer.migrations.0002_course_fields_same_as_base")

        class Editor:
            pass
        editor = Editor()
        editor.connection = connection
        migration.remove_duplicates(apps, editor)
        self.dataset.refresh_from_db()
        self.assertEqual(self.dataset.metadata["base"], "usual_care")
        self.assertGreater(nulls(self.dataset), N * 3)
        self.assert_complete(self.dataset, self.ids)
        migration.restore_duplicates(apps, editor)                     # and back
        self.assertEqual(nulls(self.dataset), 0)
        self.assert_complete(self.dataset, self.ids)

    def test_a_data_set_without_usual_care_has_its_first_scenario_as_base(self):
        other = store.generate(N, SEED, ["combined", "lung_monitoring"], wait=True)
        self.assertEqual(courses.base_of(other), "combined")
        self.assertEqual(nulls(other, "combined"), 0)
        for table in self.TABLES:
            for sid in ("combined", "lung_monitoring"):
                self.assertEqual(app_records(other, table, sid), self.truth[(table, sid)])

    def test_base_of_old_data_sets(self):
        self.assertEqual(courses.choose_base(["combined", "usual_care"]), "usual_care")
        self.assertEqual(courses.choose_base(["combined", "lung_monitoring"]), "combined")
        self.assertEqual(courses.base_of(Dataset(scenarios=[{"scenario_id": "combined"}], metadata={})), "combined")
