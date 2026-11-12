from django.http import QueryDict
from django.test import SimpleTestCase

import toxage_risk
from explorer import filters


class FilterTest(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.models = toxage_risk.load()
        cls.specs = filters.specs(cls.models)

    def parse(self, text):
        return filters.parse(QueryDict(text), self.specs)

    def test_specs_cover_schema_and_models(self):
        keys = {f.key for f in self.specs}
        self.assertIn("regimen", keys)
        self.assertIn("ild_grade", keys)
        self.assertIn("risk_severe90", keys)
        self.assertNotIn("patient_id", keys)
        risk = next(f for f in self.specs if f.key == "risk_ild")
        self.assertEqual((risk.group, risk.scale, risk.unit), ("Risk", 100, "%"))

    def test_parse_choice_keeps_only_allowed_values(self):
        self.assertEqual(self.parse("sex=male&sex=other"), {"sex": {"male"}})
        self.assertEqual(self.parse("sex=other"), {})

    def test_parse_bool(self):
        self.assertEqual(self.parse("ild=true"), {"ild": True})
        self.assertEqual(self.parse("ild=false"), {"ild": False})
        self.assertEqual(self.parse("ild=maybe"), {})

    def test_parse_range_and_scale(self):
        self.assertEqual(self.parse("age_years_min=60"), {"age_years": (60.0, None)})
        self.assertEqual(self.parse("risk_ild_max=20"), {"risk_ild": (None, 0.2)})

    def test_parse_ignores_bad_numbers(self):
        self.assertEqual(self.parse("age_years_min=abc&age_years_max=nan&ecog_min="), {})

    def test_matches(self):
        row = {"sex": "male", "ild": False, "age_years": 70, "ga_impaired_domains": None}
        self.assertTrue(filters.matches(row, {"sex": {"male"}, "ild": False,
                                              "age_years": (70, 70)}))
        self.assertFalse(filters.matches(row, {"sex": {"female"}}))
        self.assertFalse(filters.matches(row, {"ild": True}))
        self.assertFalse(filters.matches(row, {"age_years": (71, None)}))
        self.assertFalse(filters.matches(row, {"age_years": (None, 69)}))
        self.assertFalse(filters.matches(row, {"ga_impaired_domains": (0, None)}))

    def test_apply(self):
        rows = [{"ecog": 0}, {"ecog": 2}]
        self.assertEqual(filters.apply(rows, {"ecog": (1, None)}), [{"ecog": 2}])
        self.assertEqual(filters.apply(rows, {}), rows)

    def test_form_groups_and_state(self):
        query = QueryDict("sex=male&age_years_min=50&ild=true")
        groups = filters.form(self.specs, query, filters.parse(query, self.specs))
        self.assertEqual([g["name"] for g in groups], ["Patient", "Outcome", "Risk"])
        patient = {e["spec"].key: e for e in groups[0]["entries"]}
        self.assertEqual(patient["sex"]["selected"], {"male"})
        self.assertEqual(patient["age_years"]["min"], "50")
        self.assertTrue(patient["sex"]["active"])
        self.assertFalse(patient["ecog"]["active"])
        self.assertTrue(groups[1]["active"])
        self.assertFalse(groups[2]["active"])
        self.assertEqual({e["spec"].key: e for e in groups[1]["entries"]}["ild"]["value"], "true")
