from django.test import SimpleTestCase, TestCase

from explorer import params
from explorer.models import Setting


class HelperTest(SimpleTestCase):
    def test_leaves_and_notes(self):
        data = {"a": {"b": 1, "basis": "x", "c": {"d": [1, 2]}}, "e": True}
        self.assertEqual(list(params.leaves(data)),
                         [(("a", "b"), 1), (("a", "basis"), "x"), (("a", "c", "d"), [1, 2]), (("e",), True)])
        self.assertTrue(params.is_note(("a", "basis")))
        self.assertFalse(params.is_note(("a", "b")))

    def test_apply_changes_a_copy(self):
        data = {"a": {"b": 1}, "e": True}
        changed = params.apply(data, {"a/b": 2, "a/gone": 5, "x/y": 1})
        self.assertEqual(changed, {"a": {"b": 2}, "e": True})
        self.assertEqual(data["a"]["b"], 1)

    def test_parse_keeps_the_type_of_the_default(self):
        self.assertEqual(params.parse(" 2 ", 1), 2)
        self.assertIsInstance(params.parse("2", 1), int)
        self.assertEqual(params.parse("2.5", 1), 2.5)
        self.assertEqual(params.parse("0.5", 0.3), 0.5)
        self.assertIs(params.parse("false", True), False)
        self.assertEqual(params.parse(" early ", "mid"), "early")
        self.assertEqual(params.parse("[1, 3]", [1, 2]), [1, 3])
        self.assertIsNone(params.parse("null", None))
        for text, default in (("x", 1), ("nan", 1.0), ("yes", True), ("{}", [1]), ("[1,", [1])):
            with self.assertRaises(ValueError):
                params.parse(text, default)

    def test_show(self):
        self.assertEqual([params.show(v) for v in (True, 1.5, "a", [1, 2], None)],
                         ["true", "1.5", "a", "[1, 2]", "null"])

    def test_sources_exist_and_have_values(self):
        for source in params.SOURCES.values():
            self.assertTrue(list(params.leaves(source.default())), source.key)
        self.assertIn("nalirifox", params.SOURCES["regimens"].default())


class StoreTest(TestCase):
    PATH = "hazards/dose_exponent/value"

    def test_whole_numbers_refuse_fractions(self):
        self.assertTrue(params.is_whole("parameters", "simulation/weeks"))
        self.assertTrue(params.is_whole("regimens", "olaparib/lab_interval_weeks"))       # * for any regimen
        self.assertTrue(params.is_whole("interventions", "consequences/intensive_care/4/days"))
        self.assertFalse(params.is_whole("interventions", "costs/hospital_day"))           # cents allowed
        self.assertFalse(params.is_whole("regimens", "olaparib"))
        with self.assertRaisesMessage(ValueError, "must be a whole number"):
            params.parse("2.5", 520, whole=True)
        self.assertEqual(params.parse("104.0", 520, whole=True), 104)
        self.assertIsInstance(params.parse("104.0", 520, whole=True), int)
        self.assertEqual(params.parse("812.5", 800), 812.5)
        errors = params.save("parameters", {"simulation/weeks": "60.5"})
        self.assertEqual(errors, {"simulation/weeks": "must be a whole number"})
        self.assertEqual(params.changes("parameters"), {})

    def test_the_list_of_whole_numbers_is_no_parameter(self):
        for key in params.SOURCES:
            paths = [params.SEP.join(p) for g in params.form(key) for p in [r["path"].split(params.SEP) for r in g["rows"]]]
            self.assertNotIn("whole_numbers", paths)
        rows = {r["path"]: r for g in params.form("parameters") for r in g["rows"]}
        self.assertTrue(rows["simulation/weeks"]["whole"])
        self.assertFalse(rows["survival/frailty_log_hazard_ratio"]["whole"])

    def test_save_stores_only_changes(self):
        errors = params.save("parameters", {self.PATH: "3", "simulation/weeks": "520", "unknown/path": "1"})
        self.assertEqual(errors, {})
        self.assertEqual(params.changes("parameters"), {self.PATH: 3})
        self.assertEqual(params.effective("parameters")["hazards"]["dose_exponent"]["value"], 3)
        self.assertEqual(params.all_changes(), {"parameters": {self.PATH: 3}})

    def test_default_value_removes_the_change(self):
        params.save("parameters", {self.PATH: "3"})
        params.save("parameters", {self.PATH: "2.0"})
        self.assertEqual(params.changes("parameters"), {})
        self.assertFalse(Setting.objects.exists())

    def test_errors_are_reported_and_other_values_saved(self):
        errors = params.save("parameters", {self.PATH: "abc", "simulation/weeks": "104"})
        self.assertEqual(list(errors), [self.PATH])
        self.assertEqual(params.changes("parameters"), {"simulation/weeks": 104})

    def test_notes_cannot_be_changed(self):
        params.save("parameters", {"simulation/basis": "x"})
        self.assertEqual(params.changes("parameters"), {})

    def test_reset(self):
        params.save("parameters", {self.PATH: "3", "simulation/weeks": "104"})
        params.save("risk", {"ild/window_days": "365"})
        params.reset("parameters", self.PATH)
        self.assertEqual(params.changes("parameters"), {"simulation/weeks": 104})
        params.reset("parameters")
        self.assertEqual(params.all_changes(), {"risk": {"ild/window_days": 365}})
        params.reset()
        self.assertEqual(params.all_changes(), {})

    def test_form(self):
        params.save("parameters", {self.PATH: "3"})
        groups = {g["anchor"]: g for g in params.form("parameters", errors={"simulation/weeks": "bad"})}
        row = next(r for r in groups["group-hazards"]["rows"] if r["path"] == self.PATH)
        self.assertEqual((row["value"], row["default"], row["changed"], row["kind"]), ("3.0", "2.0", True, "number"))
        self.assertEqual(row["anchor"], "param-" + self.PATH.replace("/", "--"))
        self.assertEqual((groups["group-hazards"]["changed"], groups["group-hazards"]["title"]), (1, "Hazards"))
        weeks = next(r for r in groups["group-simulation"]["rows"] if r["path"] == "simulation/weeks")
        self.assertEqual(weeks["error"], "bad")
        self.assertFalse(any(r["path"].endswith("/basis") for g in groups.values() for r in g["rows"]))

    def test_engine_config(self):
        params.save("regimens", {"olaparib/severe_toxicity_rate": "0.6"})
        params.save("interventions", {"risk_adapted_start/share_flagged": "0.5"})
        config = params.engine_config()
        self.assertEqual(config["regimens"]["olaparib"]["severe_toxicity_rate"], 0.6)
        self.assertEqual(config["interventions"]["risk_adapted_start"]["share_flagged"], 0.5)
        self.assertIn("nalirifox", config["calibration"])
        self.assertTrue(params.needs_calibration(params.all_changes()))
        self.assertFalse(params.needs_calibration({"interventions": {"a": 1}, "risk": {"b": 2}}))
