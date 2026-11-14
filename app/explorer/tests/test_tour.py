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

    def other_browser(self):
        """A second browser that accepted the terms, without the demo's cookie."""
        from django.test import Client
        other = Client()
        other.cookies[COOKIE] = settings.DISCLAIMER_VERSION
        return other

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

    def test_a_new_round_starts_from_the_state_before_the_demo(self):
        self.client.post("/tour/snapshot/")
        self.change_everything()
        # The same browser starts its next round: the state before comes back first.
        self.assertTrue(json.loads(self.client.post("/tour/snapshot/").content)["taken"])
        self.assertEqual({**self.state(), "snapshot": False, "demo": False}, {**self.before, "demo": False})
        self.client.post("/tour/restore/")
        self.assertEqual(self.state(), self.before)

    def test_another_browser_leaves_a_running_demo_alone(self):
        self.client.post("/tour/snapshot/")
        self.change_everything()
        other = self.other_browser()
        self.assertEqual(json.loads(other.post("/tour/snapshot/").content)["taken"], False)
        self.assertEqual(json.loads(other.post("/tour/restore/").content), {"restored": False, "busy": True})
        self.assertContains(other.get("/data/"), 'data-tour-snapshot="0"')     # no "did not finish" note there
        self.assertEqual(len(self.state()["datasets"]), 2)                     # the demo's data set is still there

    def test_an_abandoned_demo_is_taken_back(self):
        self.client.post("/tour/snapshot/")
        self.change_everything()
        snapshot = Setting.objects.get(pk=tour.SNAPSHOT)
        snapshot.value["taken_at"] -= tour.DEMO_MINUTES * 60 + 1
        snapshot.save()
        self.other_browser().get("/about/")                                    # any page view
        self.assertEqual(json.loads(self.client.get("/tour/state/").content)["datasets"], self.before["datasets"])
        self.assertFalse(tour.has_snapshot())

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
    def test_read_only_mode_without_a_demo_changes_nothing(self):
        self.assertTrue(self.state()["read_only"])
        self.assertContains(self.client.get("/"), 'data-read-only="1"')
        self.assertEqual(self.client.post("/data/generate/", {"n": "6", "seed": "3"}).status_code, 403)
        self.assertEqual(self.client.post("/parameters/risk/", {"p:ild/window_days": "365"}).status_code, 403)

    @override_settings(READ_ONLY=True)
    def test_the_demo_may_make_its_changes_in_read_only_mode(self):
        answer = json.loads(self.client.post("/tour/snapshot/").content)
        self.assertEqual(answer, {"read_only": False, "taken": True})
        self.assertFalse(self.state()["read_only"])
        self.assertTrue(self.state()["demo"])
        self.assertContains(self.client.get("/data/"), 'data-read-only="0"')
        # What the demo does: generate, change and reset parameters, delete what it made.
        self.client.post("/data/generate/", {"n": "6", "seed": "3", "scenarios": ["usual_care"], "name": "Tour"})
        made = Dataset.objects.get(name="Tour")
        self.client.post("/parameters/interventions/", {"p:risk_adapted_start/share_flagged": "0.5"})
        self.assertEqual(params.changes("interventions"), {"risk_adapted_start/share_flagged": 0.5})
        # Its limits: no large data sets, nothing that was there before, no "delete all", no import.
        self.assertEqual(self.client.post("/data/generate/", {"n": "1500", "seed": "4"}).status_code, 403)
        self.assertEqual(self.client.post("/data/delete/", {"dataset": self.dataset.pk}).status_code, 403)
        self.assertEqual(self.client.post("/data/delete/", {"all": "yes"}).status_code, 403)
        self.assertEqual(self.client.post("/data/import/", {}).status_code, 403)
        self.assertEqual(self.client.post("/data/delete/", {"dataset": made.pk}).status_code, 302)
        self.assertFalse(Dataset.objects.filter(pk=made.pk).exists())
        # Others get no permission from the demo.
        self.assertEqual(self.other_browser().post("/data/generate/", {"n": "6", "seed": "5"}).status_code, 403)
        # The end of the demo takes everything back and the permission with it.
        self.client.post("/tour/restore/")
        self.assertEqual(self.state(), {**self.before, "read_only": True})
        self.assertEqual(self.client.post("/data/generate/", {"n": "6", "seed": "6"}).status_code, 403)

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
