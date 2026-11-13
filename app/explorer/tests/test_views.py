from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from explorer.templatetags import explorer_tags

from .helpers import CohortTestCase

COOKIE = settings.DISCLAIMER_COOKIE


class DisclaimerTest(TestCase):
    def test_everything_redirects_to_the_disclaimer(self):
        for url in ("/", "/random/", "/?patient=1"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response["Location"].startswith("/disclaimer/?next="))

    def test_disclaimer_is_shown_without_menu(self):
        response = self.client.get("/disclaimer/")
        self.assertContains(response, "Terms of use")
        self.assertNotContains(response, 'class="menu"')

    def test_accept_for_this_session_only(self):
        response = self.client.post("/disclaimer/", {"accept": "yes", "next": "/?patient=7"})
        self.assertRedirects(response, "/?patient=7", fetch_redirect_response=False)
        cookie = response.cookies[COOKIE]
        self.assertEqual(cookie.value, settings.DISCLAIMER_VERSION)
        self.assertEqual(cookie["max-age"], "")

    def test_accept_and_remember(self):
        response = self.client.post("/disclaimer/", {"accept": "yes", "remember": "yes"})
        self.assertEqual(int(response.cookies[COOKIE]["max-age"]),
                         settings.DISCLAIMER_REMEMBER_DAYS * 86400)

    def test_without_acceptance_the_form_shows_an_error(self):
        response = self.client.post("/disclaimer/", {"remember": "yes"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please accept")
        self.assertNotIn(COOKIE, response.cookies)

    def test_foreign_next_is_ignored(self):
        response = self.client.post("/disclaimer/", {"accept": "yes",
                                                     "next": "https://example.com/"})
        self.assertEqual(response["Location"], reverse("explorer"))

    def test_old_version_asks_again(self):
        self.client.cookies[COOKIE] = "0"
        self.assertEqual(self.client.get("/").status_code, 302)

    def test_revoke(self):
        self.client.cookies[COOKIE] = settings.DISCLAIMER_VERSION
        self.assertEqual(self.client.get(reverse("revoke")).status_code, 405)
        response = self.client.post(reverse("revoke"))
        self.assertRedirects(response, reverse("disclaimer"))
        self.assertEqual(response.cookies[COOKIE].value, "")

    def test_static_files_are_open(self):
        with override_settings(DEBUG=True):
            response = self.client.get("/static/explorer/style.css")
        self.assertNotEqual(response.status_code, 302)


class EmptyExplorerTest(TestCase):
    def setUp(self):
        self.client.cookies[COOKIE] = settings.DISCLAIMER_VERSION

    def test_without_data(self):
        self.assertContains(self.client.get("/"), "No data yet")
        self.assertRedirects(self.client.get("/random/"), "/", fetch_redirect_response=False)


class ExplorerTest(CohortTestCase):
    def setUp(self):
        super().setUp()
        self.client.cookies[COOKIE] = settings.DISCLAIMER_VERSION

    def test_cohort_view(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selection"], self.n)
        self.assertIsNone(response.context["patient"])
        self.assertContains(response, 'id="chart-data"')
        self.assertContains(response, "<tox-chart", count=len(response.context["chart_data"]))

    def test_filters_narrow_the_selection(self):
        response = self.client.get("/?tumour_type=breast&age_years_max=60")
        expected = [r for r in self.rows if r["tumour_type"] == "breast" and r["age_years"] <= 60]
        self.assertEqual(response.context["selection"], len(expected))
        self.assertEqual(response.context["active_count"], 2)

    def test_risk_filter(self):
        response = self.client.get("/?risk_severe90_min=80")
        expected = [r for r in self.rows if r["risk_severe90"] >= 0.8]
        self.assertEqual(response.context["selection"], len(expected))

    def test_patient_view(self):
        response = self.client.get("/?patient=3")
        self.assertEqual(response.context["patient"]["patient_id"], "P000003")
        self.assertTrue(response.context["patient_in_selection"])
        self.assertContains(response, "Patient P000003")
        self.assertContains(response, "Risk factors")

    def test_patient_outside_filter(self):
        row = self.rows[0]
        other = next(t for t in ("pancreas", "prostate", "breast") if t != row["tumour_type"])
        response = self.client.get(f"/?patient={row['patient_id']}&tumour_type={other}")
        self.assertFalse(response.context["patient_in_selection"])
        self.assertContains(response, "outside the current filter")

    def test_unknown_patient(self):
        response = self.client.get("/?patient=X1")
        self.assertIsNone(response.context["patient"])
        self.assertContains(response, "No patient with ID")

    def test_model_choice(self):
        self.assertEqual(self.client.get("/?model=ild").context["focus"].id, "ild")
        self.assertEqual(self.client.get("/?model=none").context["focus"].id, "severe90")

    def test_links_keep_the_state(self):
        context = self.client.get("/?sex=male&patient=5&model=ild").context
        self.assertEqual(context["clear_patient"], "sex=male&model=ild")
        self.assertEqual(context["reset_filters"], "model=ild&patient=P000005")
        self.assertEqual(context["keep"], [("sex", "male"), ("model", "ild")])
        links = dict((m.id, q) for m, q in context["model_links"])
        self.assertEqual(links["severe90"], "sex=male&patient=5&model=severe90")

    def test_scenario_choice(self):
        context = self.client.get("/").context
        self.assertEqual(context["scenario"]["scenario_id"], "usual_care")
        self.assertIsNone(context["compare"])
        context = self.client.get("/?scenario=combined").context
        self.assertEqual(context["scenario"]["scenario_id"], "combined")
        self.assertEqual(context["compare"]["scenario_id"], "usual_care")
        self.assertIsNone(self.client.get("/?scenario=combined&compare=none").context["compare"])
        context = self.client.get("/?scenario=combined&compare=lung_monitoring").context
        self.assertEqual(context["compare"]["scenario_id"], "lung_monitoring")
        self.assertEqual(self.client.get("/?scenario=x").context["scenario"]["scenario_id"], "usual_care")

    def test_filters_use_the_outcome_of_the_scenario(self):
        usual = self.client.get("/?participating=true").context["selection"]
        combined = self.client.get("/?participating=true&scenario=combined").context["selection"]
        self.assertEqual(usual, 0)
        self.assertGreater(combined, 0)

    def test_views(self):
        for view, text in (("risk", "Distribution of predicted risk"), ("characteristics", "by patient characteristics"),
                           ("time", "Cohort over time"), ("interventions", "Scenarios side by side")):
            response = self.client.get(f"/?view={view}&scenario=combined")
            self.assertEqual(response.context["view"], view)
            self.assertContains(response, text)
            self.assertContains(response, "<tox-chart", count=len(response.context["chart_data"]))
        self.assertEqual(self.client.get("/?view=x").context["view"], "risk")

    def test_time_view_of_a_patient(self):
        response = self.client.get("/?view=time&scenario=combined&patient=4")
        self.assertContains(response, "Patient P000004 over time")
        self.assertContains(response, "Adverse events: Combined")
        self.assertContains(response, "Adverse events: Usual care")
        self.assertIn("patient-dose", response.context["chart_data"])
        self.assertIn("time-survival", response.context["chart_data"])

    def test_interventions_view(self):
        response = self.client.get("/?view=interventions&scenario=lung_monitoring&tumour_type=breast")
        self.assertContains(response, "Cost per QALY gained")
        self.assertContains(response, "Early recognition: Lung monitoring")
        table = response.context["sections"][0]["table"]
        self.assertEqual(len(table), 6)
        self.assertEqual(table[0]["n"], response.context["selection"])
        self.assertNotContains(self.client.get("/?view=interventions"), "Early recognition:")

    def test_view_links_keep_the_state(self):
        context = self.client.get("/?sex=male&scenario=combined&view=time").context
        links = {key: query for key, _, query in context["view_links"]}
        self.assertEqual(links["interventions"], "sex=male&scenario=combined&view=interventions")
        self.assertEqual(context["reset_filters"], "view=time&scenario=combined&model=severe90")
        self.assertEqual(context["keep_state"], [("sex", "male"), ("view", "time")])

    def test_random_patient_respects_filters(self):
        for _ in range(5):
            response = self.client.get("/random/?tumour_type=breast")
            self.assertEqual(response.status_code, 302)
            patient_id = response["Location"].split("patient=")[1]
            row = next(r for r in self.rows if r["patient_id"] == patient_id)
            self.assertEqual(row["tumour_type"], "breast")

    def test_random_patient_with_empty_selection(self):
        response = self.client.get("/random/?age_years_min=200&patient=P000001")
        self.assertEqual(response["Location"], "/?age_years_min=200")


class TagTest(TestCase):
    def test_filters(self):
        self.assertEqual(explorer_tags.pct(0.1234), "12.3%")
        self.assertEqual(explorer_tags.pct(0.5, 0), "50%")
        self.assertEqual(explorer_tags.pct(None), "–")
        self.assertEqual(explorer_tags.num(0.6666), "0.67")
        self.assertEqual(explorer_tags.num(None), "–")
        self.assertEqual(explorer_tags.label("lu_psma_617"), "lu psma 617")
