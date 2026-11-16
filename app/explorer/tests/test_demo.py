"""Demo installation: every visitor works in a space of their own (demo.py)."""
import gzip
import json

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings

from explorer import demo, params
from explorer.models import Dataset, Setting

from .helpers import CohortTestCase

COOKIE = settings.DISCLAIMER_COOKIE
RELOAD = {"HTTP_CACHE_CONTROL": "max-age=0", "HTTP_SEC_FETCH_DEST": "document"}


def browser():
    """A browser that accepted the terms."""
    client = Client()
    client.cookies[COOKIE] = settings.DISCLAIMER_VERSION
    return client


@override_settings(DEMO=True, ASYNC_JOBS=False)
class DemoTest(CohortTestCase):
    """The data set of CohortTestCase and a stored parameter change are permanent."""
    n = 12

    def setUp(self):
        super().setUp()
        params.save("risk", {"ild/window_days": "700"})
        demo._last_sweep[0] = 0
        self.alice, self.bob = browser(), browser()
        self.alice.get("/data/")
        self.bob.get("/data/")

    def generate(self, client, name):
        client.post("/data/generate/", {"n": "6", "seed": "3", "scenarios": ["usual_care"], "name": name})
        return Dataset.objects.get(name=name)

    def names(self, client):
        return [d["name"] for d in json.loads(client.get("/tour/state/").content)["datasets"]]

    def test_each_browser_gets_a_space(self):
        a, b = self.alice.cookies[demo.COOKIE].value, self.bob.cookies[demo.COOKIE].value
        self.assertEqual(len(a), 16)
        self.assertNotEqual(a, b)

    def test_data_sets_of_a_visitor_are_seen_only_by_that_visitor(self):
        mine = self.generate(self.alice, "Alice's")
        self.assertEqual(mine.owner, self.alice.cookies[demo.COOKIE].value)
        self.assertEqual(sorted(self.names(self.alice)), sorted([self.dataset.name, "Alice's"]))
        self.assertEqual(self.names(self.bob), [self.dataset.name])
        self.assertEqual(self.bob.get(f"/data/{mine.pk}/records/").status_code, 404)
        self.assertEqual(self.bob.post("/data/delete/", {"dataset": mine.pk}).status_code, 404)

    def test_permanent_data_sets_cannot_be_deleted(self):
        self.assertEqual(self.alice.post("/data/delete/", {"dataset": self.dataset.pk}).status_code, 403)
        self.assertEqual(self.alice.post("/data/delete/", {"dataset": self.dataset.pk, "scenario": "combined"})
                         .status_code, 403)
        mine = self.generate(self.alice, "Alice's")
        self.generate(self.bob, "Bob's")
        self.alice.post("/data/delete/", {"all": "yes"})                  # only her own
        self.assertEqual(sorted(Dataset.objects.values_list("name", flat=True)), sorted([self.dataset.name, "Bob's"]))
        self.assertFalse(Dataset.objects.filter(pk=mine.pk).exists())

    def test_parameter_changes_stay_in_the_space(self):
        self.alice.post("/parameters/risk/", {"p:ild/window_days": "365"})
        self.assertEqual(Setting.objects.get(pk="risk").value, {"ild/window_days": 700})     # permanent
        self.assertContains(self.alice.get("/parameters/risk/"), 'value="365"')
        self.assertContains(self.bob.get("/parameters/risk/"), 'value="700"')
        # "Reset everything" in the space means the defaults, the permanent change stays.
        self.alice.post("/parameters/risk/", {"action": "reset_all"})
        self.assertNotContains(self.alice.get("/parameters/risk/"), 'value="700"')
        self.assertEqual(Setting.objects.get(pk="risk").value, {"ild/window_days": 700})

    def test_a_reload_empties_the_space(self):
        self.generate(self.alice, "Alice's")
        self.alice.post("/parameters/risk/", {"p:ild/window_days": "365"})
        self.alice.get("/data/", HTTP_X_TOXAGE_FETCH="1", HTTP_CACHE_CONTROL="max-age=0")   # the page script
        self.alice.get("/data/")                                                            # a link, a new tab
        self.assertIn("Alice's", self.names(self.alice))
        self.alice.get("/data/", **RELOAD)                                                  # reload
        self.assertEqual(self.names(self.alice), [self.dataset.name])
        self.assertContains(self.alice.get("/parameters/risk/"), 'value="700"')

    def test_an_idle_space_is_emptied(self):
        self.generate(self.alice, "Alice's")
        owner = self.alice.cookies[demo.COOKIE].value
        seen = Setting.objects.get(pk=demo.SEEN + owner)
        seen.value["at"] -= settings.DEMO_IDLE_MINUTES * 60 + 1
        seen.save()
        demo._last_sweep[0] = 0
        self.bob.get("/about/")                                       # any request of anyone
        self.assertFalse(Dataset.objects.filter(owner=owner).exists())
        self.assertFalse(Setting.objects.filter(pk=demo.SEEN + owner).exists())
        self.assertTrue(Dataset.objects.filter(pk=self.dataset.pk).exists())

    def test_the_tour_works_in_the_space(self):
        self.assertEqual(json.loads(self.alice.post("/tour/snapshot/").content), {"taken": True})
        self.assertEqual(json.loads(self.bob.post("/tour/snapshot/").content), {"taken": True})   # both at once
        self.generate(self.alice, "Tour")
        self.alice.post("/parameters/interventions/", {"p:risk_adapted_start/share_flagged": "0.5"})
        self.assertEqual(json.loads(self.alice.post("/tour/restore/").content), {"restored": True})
        self.assertEqual(self.names(self.alice), [self.dataset.name])
        self.assertEqual(json.loads(self.alice.get("/tour/state/").content)["changes"], {"risk": 1})

    def test_archives_go_into_the_space(self):
        text = gzip.decompress(b"".join(self.alice.get("/data/archive/").streaming_content))
        upload = SimpleUploadedFile("a.jsonl.gz", gzip.compress(text), content_type="application/gzip")
        self.alice.post("/data/import/", {"archive": upload, "mode": "replace"})
        self.assertEqual(Dataset.objects.count(), 2)                      # the permanent one stays
        self.assertEqual(Dataset.objects.exclude(pk=self.dataset.pk).get().owner,
                         self.alice.cookies[demo.COOKIE].value)
        self.assertEqual(self.names(self.bob), [self.dataset.name])

    def test_pages_say_what_the_demo_does(self):
        page = self.alice.get("/data/")
        self.assertContains(page, "This is a demo")
        self.assertContains(page, ">permanent<")
        self.assertContains(page, "Generate a data set")
        self.assertContains(page, 'action="/data/import/"')
        self.assertNotContains(page, "Delete data set</button>")           # not for the permanent one
        self.assertContains(self.alice.get("/parameters/risk/"), "This is a demo")


class NormalInstallationTest(CohortTestCase):
    def test_no_spaces_without_demo(self):
        client = browser()
        response = client.get("/data/")
        self.assertNotIn(demo.COOKIE, response.cookies)
        self.assertNotContains(response, "This is a demo")
        self.assertContains(response, "Delete data set</button>")
        self.assertEqual(demo.visitor(), "")
