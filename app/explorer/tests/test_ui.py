"""The simple view (ui.py): less shown and offered, the same data."""
from django.conf import settings
from django.test import override_settings

from explorer import ui
from explorer.models import Dataset

from .helpers import CohortTestCase

COOKIE = settings.DISCLAIMER_COOKIE


class NormalViewTest(CohortTestCase):
    """Without TOXAGE_SIMPLE_UI nothing of the simple view shows."""

    def setUp(self):
        super().setUp()
        self.client.cookies[COOKIE] = settings.DISCLAIMER_VERSION

    def test_no_simple_view(self):
        about = self.client.get("/about/")
        self.assertNotContains(about, 'id="simple-view"')
        self.assertNotContains(about, 'data-setting="ui"')
        self.assertContains(about, ">Parameters</a>")
        self.assertEqual(self.client.get("/?view=characteristics").context["view"], "characteristics")


@override_settings(SIMPLE_UI=True, ASYNC_JOBS=False)
class SimpleViewTest(CohortTestCase):
    def setUp(self):
        super().setUp()
        self.client.cookies[COOKIE] = settings.DISCLAIMER_VERSION

    def test_about_and_settings(self):
        about = self.client.get("/about/")
        self.assertContains(about, 'id="simple-view"')
        self.assertContains(about, "Settings › View › Advanced")
        self.assertContains(about, 'data-setting="ui" data-cookie="toxage_ui"')
        self.assertContains(about, 'data-simple="1"')
        self.assertNotContains(about, ">Parameters</a>")
        self.assertEqual(self.client.get("/parameters/risk/").status_code, 200)    # still reachable

    def test_explorer_shows_the_chosen_views_and_charts(self):
        response = self.client.get("/?view=characteristics")
        self.assertEqual(response.context["view"], "risk")                         # not offered: Risk
        self.assertEqual([k for k, _, _ in response.context["view_links"]], list(ui.VIEWS))
        self.assertEqual(set(response.context["chart_data"]), {"risk-hist", "calibration", "incidence"})
        interventions = self.client.get("/?view=interventions&scenario=combined").context
        self.assertTrue(set(interventions["chart_data"]) <= ui.CHARTS)
        self.assertIn("tte-sfs", interventions["chart_data"])
        endpoints = next(s for s in interventions["sections"] if s.get("endpoints"))["endpoints"]
        self.assertEqual([e["endpoint"] for e in endpoints], list(ui.ENDPOINTS))
        self.assertNotContains(self.client.get("/?view=interventions&scenario=combined"),
                               "<th>95% confidence interval</th>")

    def test_few_filters_and_the_others_kept(self):
        response = self.client.get("/?regimen=olaparib")
        keys = {e["spec"].key for g in response.context["filter_form"] for e in g["entries"]}
        self.assertEqual(keys, {"tumour_type", "age_years", "ecog", "risk_severe90"})
        self.assertIn(("regimen", "olaparib"), response.context["kept_filters"])
        self.assertContains(response, '<input type="hidden" name="regimen" value="olaparib">')
        # The filter itself applies as in the full view.
        self.client.cookies[ui.COOKIE] = "advanced"
        full = self.client.get("/?regimen=olaparib")
        self.assertEqual(response.context["selection"], full.context["selection"])

    def test_data_page_and_generating(self):
        page = self.client.get("/data/")
        self.assertNotContains(page, 'name="name"')
        self.assertNotContains(page, 'id="archive"')
        self.assertNotContains(page, "Inspect records")
        self.assertContains(page, "scenarios of the same patients")
        # The short form makes a data set under every scenario.
        form = page.context
        posted = {"n": "6", "seed": "1", "scenarios": [sid for sid, _, _ in form["scenario_choices"]]}
        self.client.post("/data/generate/", posted)
        made = Dataset.objects.exclude(pk=self.dataset.pk).get()
        self.assertEqual(len(made.scenarios), len(form["scenario_choices"]))

    def test_advanced_shows_everything(self):
        self.client.cookies[ui.COOKIE] = "advanced"
        response = self.client.get("/?view=characteristics")
        self.assertEqual(response.context["view"], "characteristics")
        self.assertContains(response, 'data-simple="0"')
        self.assertContains(self.client.get("/data/"), 'id="archive"')
        self.assertContains(self.client.get("/about/"), 'id="simple-view"')     # still explained there
