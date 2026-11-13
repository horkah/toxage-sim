import math

from django.test import SimpleTestCase

from explorer import charts
from explorer.cohort import Field, fields

from .helpers import CohortTestCase

FIELDS = {f.name: f for f in fields()}


class HelperTest(SimpleTestCase):
    def test_nice_step(self):
        self.assertEqual(charts.nice_step(10, 10), 1)
        self.assertEqual(charts.nice_step(0.9, 10), 0.1)
        self.assertEqual(charts.nice_step(23, 10), 2.5)
        self.assertEqual(charts.nice_step(40, 10), 5)
        self.assertEqual(charts.nice_step(0, 5), 1)

    def test_nice_max(self):
        self.assertAlmostEqual(charts.nice_max(0.83), 1.0)
        self.assertAlmostEqual(charts.nice_max(0.27), 0.3)
        self.assertAlmostEqual(charts.nice_max(0.2), 0.2)

    def test_rate_mean_percentile(self):
        self.assertEqual(charts.rate([{"e": True}, {"e": False}], "e"), 0.5)
        self.assertIsNone(charts.rate([], "e"))
        self.assertEqual(charts.mean([1, None, 3]), 2)
        self.assertIsNone(charts.mean([None]))
        self.assertEqual(charts.percentile([1, 2, 3, 4], 3), 62.5)
        self.assertIsNone(charts.percentile([], 3))
        self.assertIsNone(charts.percentile([1], None))


class GroupingTest(SimpleTestCase):
    def test_choice(self):
        labels, key, links = charts.grouping(FIELDS["renal_function"], [])
        self.assertEqual(labels[2], "moderate severe decrease")
        self.assertEqual(key("mild_decrease"), 1)
        self.assertEqual(links[0], {"renal_function": ["normal"]})

    def test_bool(self):
        labels, key, links = charts.grouping(FIELDS["lung_comorbidity"], [])
        self.assertEqual((labels, key(True), key(None)), (["no", "yes"], 1, None))
        self.assertEqual(links[1], {"lung_comorbidity": "true"})

    def test_small_integer_range_with_missing_values(self):
        labels, key, links = charts.grouping(FIELDS["ga_impaired_domains"], [])
        self.assertEqual(labels, [str(i) for i in range(8)] + ["not recorded"])
        self.assertEqual((key(3), key(None)), (3, 8))
        self.assertEqual(links[3], {"ga_impaired_domains_min": 3, "ga_impaired_domains_max": 3})
        self.assertIsNone(links[-1])

    def test_integer_bins(self):
        rows = [{"age_years": a} for a in range(40, 80)]
        labels, key, links = charts.grouping(FIELDS["age_years"], rows)
        self.assertEqual(labels[0], "40–44")
        self.assertEqual(key(43), 0)
        self.assertEqual(links[0], {"age_years_min": 40, "age_years_max": 44})

    def test_integer_bins_stop_at_schema_maximum(self):
        rows = [{"spo2_percent": v} for v in range(85, 101)]
        labels, _, links = charts.grouping(FIELDS["spo2_percent"], rows)
        self.assertEqual(labels[-1], "100")
        self.assertEqual(links[-1], {"spo2_percent_min": 100})

    def test_long_tail_goes_to_open_bin(self):
        rows = [{"years_since_diagnosis": v / 10} for v in range(100)] + [
            {"years_since_diagnosis": 50.0}]
        labels, key, links = charts.grouping(FIELDS["years_since_diagnosis"], rows)
        self.assertTrue(labels[-1].startswith("≥"))
        self.assertEqual(key(50.0), len(labels) - 1)
        self.assertEqual(key(0.0), 0)
        self.assertIsNone(links[0])

    def test_number_without_values(self):
        labels, key, _ = charts.grouping(FIELDS["years_since_diagnosis"], [])
        self.assertEqual(len(labels), 1)
        self.assertEqual(key(0), 0)

    def test_grouped_drops_empty_groups_but_keeps_the_patient(self):
        field = FIELDS["ecog"]
        rows = [{"ecog": 0}, {"ecog": 0}, {"ecog": 2}]
        groups, mine = charts.grouped(rows, field, {"ecog": 4})
        self.assertEqual([g[0] for g in groups], ["0", "2", "4"])
        self.assertEqual([len(g[1]) for g in groups], [2, 1, 0])
        self.assertEqual(mine, 2)
        self.assertIsNone(charts.grouped(rows, field)[1])

    def test_field_without_schema_bounds(self):
        field = Field("x", "X", "baseline", "number", integer=True)
        labels, key, _ = charts.grouping(field, [{"x": 1}, {"x": 9}])
        self.assertEqual(key(9), len(labels) - 1)


class ChartTest(CohortTestCase):
    def test_empty_selection(self):
        for spec in (charts.risk_histogram([], self.severe), charts.calibration([], self.severe),
                     charts.incidence([], self.severe),
                     charts.by_field([], FIELDS["sex"], self.severe),
                     charts.scatter([], ("age_years", "", "int"), ("risk_ild", "", "pct"), "ild")):
            self.assertTrue(spec["empty"])

    def test_by_field(self):
        spec = charts.by_field(self.rows, FIELDS["tumour_type"], self.severe, self.rows[0])
        self.assertEqual(sum(spec["counts"]), self.n)
        observed = spec["series"][0]["values"]
        self.assertTrue(all(0 <= v <= 1 for v in observed))
        self.assertEqual(spec["categories"][spec["highlight"]],
                         self.rows[0]["tumour_type"].replace("_", " "))

    def test_by_field_uses_only_rows_with_risk(self):
        spec = charts.by_field(self.rows, FIELDS["sex"], self.ild)
        self.assertEqual(sum(spec["counts"]), len(self.ild_rows))

    def test_patient_without_risk_is_not_highlighted(self):
        outsider = next(r for r in self.rows if r["risk_ild"] is None)
        self.assertIsNone(charts.by_field(self.rows, FIELDS["sex"], self.ild, outsider)["highlight"])
        self.assertIsNone(charts.risk_histogram(self.rows, self.ild, outsider)["highlight"])

    def test_risk_histogram(self):
        patient = self.rows[3]
        spec = charts.risk_histogram(self.rows, self.severe, patient)
        events, others = (s["values"] for s in spec["series"])
        self.assertEqual(sum(events) + sum(others), self.n)
        self.assertEqual(sum(events), sum(r["severe_toxicity_90d"] for r in self.rows))
        low = spec["links"][spec["highlight"]]
        self.assertLessEqual(low["risk_severe90_min"] / 100, patient["risk_severe90"])
        self.assertGreaterEqual(low["risk_severe90_max"] / 100, patient["risk_severe90"])
        self.assertLessEqual(len(spec["categories"]), 10)

    def test_calibration(self):
        spec = charts.calibration(self.rows, self.severe, self.rows[0])
        points = spec["series"][0]["points"]
        self.assertEqual(len(points), 10)
        self.assertEqual(points, sorted(points, key=lambda p: p[0]))
        self.assertEqual(spec["marker"]["x"], round(self.rows[0]["risk_severe90"], 4))
        self.assertGreaterEqual(spec["x"]["max"], max(p[1] for p in points))

    def test_incidence(self):
        patient = max(self.rows, key=lambda r: r["risk_severe90"])
        spec = charts.incidence(self.rows, self.severe, patient)
        self.assertEqual(len(spec["series"]), 3)
        for s in spec["series"]:
            ys = [y for _, y in s["points"]]
            self.assertEqual(ys, sorted(ys))
            self.assertEqual(s["points"][-1][0], 90)
        self.assertIn("patient's group", spec["series"][2]["name"])
        total = sum(r["severe_toxicity_90d"] for r in self.rows)
        thirds = [self.n // 3, 2 * self.n // 3 - self.n // 3, self.n - 2 * self.n // 3]
        events = sum(round(s["points"][-1][1] * k) for s, k in zip(spec["series"], thirds))
        self.assertEqual(events, total)

    def test_incidence_marks_event_day(self):
        patient = next(r for r in self.rows if r["severe_toxicity_90d"])
        spec = charts.incidence(self.rows, self.severe, patient)
        self.assertEqual(spec["marker"]["x"], patient["severe_toxicity_day"])
        patient = next(r for r in self.rows if not r["severe_toxicity_90d"])
        self.assertIsNone(charts.incidence(self.rows, self.severe, patient)["marker"])

    def test_scatter(self):
        x, y = ("age_years", "age", "int"), ("risk_ild", "risk", "pct")
        spec = charts.scatter(self.rows, x, y, "ild", self.ild_rows[0], "t")
        self.assertEqual(len(spec["points"]), len(self.ild_rows))
        self.assertEqual(spec["highlight"][2], self.ild_rows[0]["patient_id"])
        self.assertEqual(spec["y"]["min"], 0)
        self.assertLessEqual(spec["x"]["min"], min(r["age_years"] for r in self.ild_rows))
        outsider = next(r for r in self.rows if r["risk_ild"] is None)
        self.assertIsNone(charts.scatter(self.rows, x, y, "ild", outsider)["highlight"])

    def test_summary(self):
        s = charts.summary(self.rows, self.ild)
        self.assertEqual(s["n"], len(self.ild_rows))
        self.assertEqual(s["events"], sum(r["ild"] for r in self.ild_rows))
        self.assertTrue(0 <= s["predicted"] <= 1)

    def test_patient_risks(self):
        patient = self.ild_rows[0]
        found = {r["model"].id: r for r in charts.patient_risks(patient, self.rows, self.models)}
        self.assertTrue(found["ild"]["applies"])
        self.assertEqual(found["severe90"]["risk"], patient["risk_severe90"])
        for f in found["ild"]["factors"]:
            self.assertTrue(0 <= f["width"] <= 50)
            self.assertEqual(f["up"], f["ratio"] > 1)
        outsider = next(r for r in self.rows if r["risk_ild"] is None)
        info = charts.patient_risks(outsider, self.rows, self.models)[1]
        self.assertFalse(info["applies"])
        self.assertIsNone(info["reference"])

    def test_cardiovascular_model(self):
        self.assertEqual(len(self.cv_rows), sum(r["tumour_type"] == "prostate" for r in self.rows))
        s = charts.summary(self.rows, self.cv)
        self.assertEqual(s["n"], len(self.cv_rows))
        self.assertEqual(s["events"], sum(r["cv_event_1y"] for r in self.cv_rows))
        patient = next(r for r in self.cv_rows if r["prior_cardiovascular_event"])
        found = {r["model"].id: r for r in charts.patient_risks(patient, self.rows, self.models)}
        self.assertTrue(found["cv"]["applies"])
        self.assertFalse(found["ild"]["applies"])
        self.assertGreater(found["cv"]["risk"], found["cv"]["reference"])
        self.assertIn("Earlier myocardial infarction or stroke", [f["label"] for f in found["cv"]["factors"]])
        self.assertTrue(charts.build(self.rows, patient, self.cv, self.models))
        outsider = next(r for r in self.rows if r["risk_cv"] is None)
        self.assertIsNone(charts.risk_histogram(self.rows, self.cv, outsider)["highlight"])

    def test_build(self):
        sections = charts.build(self.rows, None, self.severe, self.models)
        self.assertEqual(len(sections), 3)
        ids = [cid for s in sections for cid, _ in s["charts"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("vs-ild", ids)
        self.assertIn("field-regimen", ids)
        self.assertEqual(len(charts.build(self.rows, None, self.severe, [self.severe])), 2)

    def test_specs_are_json_safe(self):
        import json
        sections = charts.build(self.rows, self.rows[0], self.ild, self.models)
        text = json.dumps([spec for s in sections for _, spec in s["charts"]], allow_nan=False)
        self.assertFalse(math.isnan(len(text)))
