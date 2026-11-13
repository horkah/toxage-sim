import json

from django.conf import settings
from django.test import override_settings

from explorer import cohort, params, store, tour
from explorer.models import Dataset, Setting

from .helpers import CohortTestCase

COOKIE = settings.DISCLAIMER_COOKIE


@override_settings(ASYNC_JOBS=False)
class TourTest(CohortTestCase):
    n = 12

    def setUp(self):
        super().setUp()
        self.client.cookies[COOKIE] = settings.DISCLAIMER_VERSION
        params.save("risk", {"ild/window_days": "700"})
        self.before = self.state()

    def state(self):
        return json.loads(self.client.get("/tour/state/").content)

    def change_everything(self):
        params.save("risk", {"ild/window_days": "365"})
        params.save("interventions", {"risk_adapted_start/share_flagged": "0.5"})
        other = store.generate(6, 3, ["usual_care"], name="Tour cohort", wait=True)
        self.client.post("/data/use/", {"dataset": other.pk})
        return other

    def test_state(self):
        self.assertEqual(self.before["datasets"][0]["name"], self.dataset.name)
        self.assertEqual(self.before["datasets"][0]["status"], "ready")
        self.assertIn("combined", self.before["datasets"][0]["scenarios"])
        self.assertEqual(self.before["active"], self.dataset.pk)
        self.assertEqual(self.before["changes"], {"risk": 1})
        self.assertFalse(self.before["snapshot"])
        self.assertFalse(self.before["read_only"])

    def test_restore_brings_the_state_before_the_demo_back(self):
        self.assertEqual(json.loads(self.client.post("/tour/snapshot/").content), {"read_only": False, "taken": True})
        self.change_everything()
        changed = self.state()
        self.assertEqual(len(changed["datasets"]), 2)
        self.assertEqual(changed["changes"], {"interventions": 1, "risk": 1})
        self.assertTrue(changed["snapshot"])
        self.assertNotEqual(changed["active"], self.before["active"])

        response = self.client.post("/tour/restore/")
        self.assertEqual(json.loads(response.content), {"restored": True})
        self.assertEqual(self.state(), self.before)
        self.assertEqual(params.changes("risk"), {"ild/window_days": 700})
        self.assertFalse(Setting.objects.filter(pk=tour.SNAPSHOT).exists())
        self.assertEqual(list(Dataset.objects.all()), [self.dataset])

    def test_restore_keeps_the_chosen_data_set(self):
        first = store.generate(6, 3, ["usual_care"], name="Chosen", wait=True)
        self.client.post("/data/use/", {"dataset": self.dataset.pk})
        self.assertEqual(self.state()["active"], self.dataset.pk)
        self.client.post("/tour/snapshot/")
        self.client.post("/data/use/", {"dataset": first.pk})
        self.client.post("/tour/restore/")
        self.assertEqual(self.state()["active"], self.dataset.pk)

    def test_a_second_snapshot_does_not_replace_the_first(self):
        self.client.post("/tour/snapshot/")
        self.change_everything()
        self.assertEqual(json.loads(self.client.post("/tour/snapshot/").content)["taken"], False)
        self.client.post("/tour/restore/")
        self.assertEqual(self.state(), self.before)

    def test_restore_without_snapshot_changes_nothing(self):
        self.change_everything()
        changed = self.state()
        self.assertEqual(json.loads(self.client.post("/tour/restore/").content), {"restored": False})
        self.assertEqual(self.state(), changed)

    def test_resetting_parameters_keeps_the_snapshot(self):
        self.client.post("/tour/snapshot/")
        params.reset()
        self.assertTrue(tour.has_snapshot())
        self.assertEqual(params.all_changes(), {})
        self.client.post("/tour/restore/")
        self.assertEqual(params.all_changes(), {"risk": {"ild/window_days": 700}})

    def test_endpoints_need_post_and_the_disclaimer(self):
        self.assertEqual(self.client.get("/tour/snapshot/").status_code, 405)
        self.assertEqual(self.client.get("/tour/restore/").status_code, 405)
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/tour/state/").status_code, 302)
        self.assertEqual(self.client.post("/tour/restore/").status_code, 302)

    @override_settings(READ_ONLY=True)
    def test_read_only_mode_takes_no_snapshot(self):
        self.assertEqual(json.loads(self.client.post("/tour/snapshot/").content), {"read_only": True, "taken": False})
        self.assertFalse(tour.has_snapshot())
        self.assertTrue(self.state()["read_only"])
        self.assertContains(self.client.get("/"), 'data-read-only="1"')

    def test_pages_carry_the_tour(self):
        response = self.client.get("/")
        self.assertContains(response, "explorer/tour.js")
        self.assertContains(response, 'data-tour-start="tutorial"')
        self.assertContains(response, 'data-tour-start="demo"')
        self.assertContains(response, 'data-setting="welcome"')
        self.assertContains(response, 'data-tour-snapshot="0"')
        self.client.post("/tour/snapshot/")
        self.assertContains(self.client.get("/data/"), 'data-tour-snapshot="1"')
        self.assertContains(self.client.get("/data/"), f'data-id="{self.dataset.pk}"')

    def test_disclaimer_has_no_tour(self):
        self.client.cookies.clear()
        self.assertNotContains(self.client.get("/disclaimer/"), "tour.js")
