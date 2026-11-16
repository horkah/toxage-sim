"""Tests of the engine. Run with: python3 -m unittest discover engine/tests"""
import copy
import json
import random
import sys
import unittest
from collections import Counter
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_DIR.parent))
sys.path.insert(0, str(ENGINE_DIR))

from schema import toxage_schema  # noqa: E402
import generate  # noqa: E402
import hazards  # noqa: E402
import uncertainty  # noqa: E402
from draws import Draws  # noqa: E402

USUAL = generate.USUAL_CARE


def by_patient(records, scenario_id):
    found = {}
    for r in generate.of_scenario(records, scenario_id):
        found.setdefault(r["patient_id"], []).append(r)
    return found


def without(record, *keys):
    return {k: v for k, v in record.items() if k not in keys}


class DrawsTest(unittest.TestCase):
    def test_numbers_are_fixed_and_differ_by_purpose_week_and_patient(self):
        d = Draws(1, 5)
        self.assertEqual(d.u("death", 3), Draws(1, 5).u("death", 3))
        values = {d.u("death", 3), d.u("death", 4), d.u("stop", 3), Draws(1, 6).u("death", 3),
                  Draws(2, 5).u("death", 3)}
        self.assertEqual(len(values), 5)

    def test_numbers_are_uniform(self):
        values = [Draws(3, i).u("x", i % 7) for i in range(20000)]
        self.assertTrue(all(0 <= v < 1 for v in values))
        self.assertAlmostEqual(sum(values) / len(values), 0.5, delta=0.01)
        self.assertAlmostEqual(sum(v < 0.1 for v in values) / len(values), 0.1, delta=0.01)

    def test_pick_follows_probabilities(self):
        picks = Counter(Draws(4, i).pick("p", {"a": 0.2, "b": 0.8, "basis": "x"}) for i in range(5000))
        self.assertEqual(set(picks), {"a", "b"})
        self.assertAlmostEqual(picks["a"] / 5000, 0.2, delta=0.02)


class EngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.regimens, cls.params = generate.load_config()
        cls.iv = generate.load_interventions()
        cls.config = generate.default_config()
        cls.data = generate.generate(3000, seed=7, validate=False)
        cls.baseline = {p["patient_id"]: p for p in cls.data["baseline"]}
        cls.scenarios = [s["scenario_id"] for s in cls.data["scenario"]]
        cls.outcome = {s: {o["patient_id"]: o for o in generate.of_scenario(cls.data["outcome"], s)}
                       for s in cls.scenarios}
        cls.events = {s: by_patient(cls.data["event"], s) for s in cls.scenarios}
        cls.alerts = {s: by_patient(cls.data["alert"], s) for s in cls.scenarios}
        cls.observations = {s: by_patient(cls.data["observation"], s) for s in cls.scenarios}

    def rate(self, field, test, scenario=USUAL):
        ids = [i for i, p in self.baseline.items() if test(p)]
        return sum(bool(self.outcome[scenario][i][field]) for i in ids) / len(ids)

    def total(self, field, scenario):
        return sum(o[field] for o in self.outcome[scenario].values())

    # Structure -------------------------------------------------------------

    def test_records_follow_schema(self):
        small = generate.generate(300, seed=2)
        for table in generate.TABLES:
            self.assertTrue(small[table], table)

    def test_config_matches_schema(self):
        self.assertEqual(set(self.regimens), set(toxage_schema.allowed_values("baseline", "regimen")))
        types = set(self.params["hazards"]["event_types"]) | {hazards.ILD}
        # Major bleeding has no rate of a regimen: it comes with thromboprophylaxis.
        self.assertEqual(types | {hazards.BLEEDING}, set(toxage_schema.allowed_values("event", "event_type")))
        for regimen in self.regimens.values():
            self.assertLessEqual(set(regimen["severe_event_rates"]), types)
        self.assertIn(USUAL, self.iv["scenarios"])
        self.assertEqual(self.iv["scenarios"][USUAL]["components"], [])

    def test_tumour_types_follow_their_shares(self):
        counts = Counter(p["tumour_type"] for p in self.data["baseline"])
        shares = self.params["population"]["tumour_shares"]
        for tumour in ("pancreas", "prostate", "breast"):
            self.assertAlmostEqual(counts[tumour] / 3000, shares[tumour], delta=0.001)
        # Also in a small cohort and in the first patients of a large one.
        first = Counter(p["tumour_type"] for p in self.data["baseline"][:20])
        self.assertEqual(first, Counter(pancreas=5, prostate=8, breast=7))

    def test_selection_limits_the_cohort(self):
        config = copy.deepcopy(self.config)
        config["selection"] = {"tumour_types": ["pancreas", "breast"], "subgroups": None,
                               "regimens": ["nalirifox", "trastuzumab_deruxtecan", "sacituzumab_govitecan", "olaparib"]}
        data = generate.generate(600, 4, [USUAL], config=config)
        regimens = Counter(p["regimen"] for p in data["baseline"])
        # Olaparib belongs to prostate cancer, which is not chosen.
        self.assertEqual(set(regimens), {"nalirifox", "trastuzumab_deruxtecan", "sacituzumab_govitecan"})
        tumours = Counter(p["tumour_type"] for p in data["baseline"])
        self.assertAlmostEqual(tumours["pancreas"] / 600, 0.25 / 0.60, delta=0.01)      # the shares keep their proportions
        self.assertEqual(data["metadata"]["selection"], config["selection"])
        # Subgroups without a chosen regimen drop out.
        self.assertNotIn("breast_triple_negative", {p["subgroup"] for p in data["baseline"]})
        config["selection"] = {"tumour_types": ["prostate"], "regimens": ["nalirifox"]}
        with self.assertRaises(ValueError):
            generate.generate(30, 1, [USUAL], config=config)
        # No selection and a selection of everything give the same patients.
        everything = copy.deepcopy(self.config)
        everything["selection"] = {"tumour_types": ["pancreas", "prostate", "breast"], "subgroups": None, "regimens": None}
        self.assertEqual(generate.generate(90, 3, [USUAL], config=everything)["baseline"],
                         generate.generate(90, 3, [USUAL], config=self.config)["baseline"])

    def test_regimen_fits_subgroup(self):
        for p in self.data["baseline"]:
            self.assertEqual(self.regimens[p["regimen"]]["subgroup"], p["subgroup"])

    def test_same_seed_gives_same_data(self):
        self.assertEqual(generate.generate(90, seed=3), generate.generate(90, seed=3))
        self.assertNotEqual(generate.generate(90, seed=3)["outcome"], generate.generate(90, seed=4)["outcome"])

    def test_validator_finds_errors(self):
        record = dict(self.data["baseline"][0], ecog=9, regimen="unknown")
        del record["sex"]
        self.assertEqual(len(toxage_schema.errors("baseline", record)), 3)

    def test_every_scenario_has_one_outcome_per_patient(self):
        for s in self.scenarios:
            self.assertEqual(set(self.outcome[s]), set(self.baseline))

    # Usual care against the literature ---------------------------------------

    def test_calibration_is_close_to_literature(self):
        with open(ENGINE_DIR / "config" / "calibration.json", encoding="utf-8") as f:
            check = json.load(f)["check"]
        for regimen, types in check.items():
            for event_type, v in types.items():
                self.assertAlmostEqual(v["realised"], v["target"], delta=0.03, msg=f"{regimen} {event_type}")

    def test_frail_patients_have_more_severe_toxicity(self):
        fit = self.rate("severe_toxicity_90d", lambda p: p["ecog"] == 0)
        frail = self.rate("severe_toxicity_90d", lambda p: p["ecog"] == 2)
        self.assertGreater(frail, fit + 0.05)

    def test_older_patients_with_impairments_are_close_to_gap70(self):
        rate = self.rate("severe_toxicity_90d",
                         lambda p: p["age_years"] >= 70 and (p["ga_impaired_domains"] or 0) >= 1)
        self.assertAlmostEqual(rate, 0.71, delta=0.07)

    def test_lung_toxicity(self):
        tdxd = [i for i, p in self.baseline.items() if p["regimen"] == "trastuzumab_deruxtecan"]
        first_year = sum(self.outcome[USUAL][i]["ild"] and self.outcome[USUAL][i]["ild_onset_day"] <= 364
                         for i in tdxd) / len(tdxd)
        self.assertAlmostEqual(first_year, 0.105, delta=0.04)
        self.assertEqual(self.rate("ild", lambda p: p["regimen"] == "nalirifox"), 0)

    def test_cardiovascular_events_follow_hero(self):
        # Shore et al. (2020): 6.2% in 48 weeks under a GnRH agonist, death from any cause
        # included; 61.5% of such events are cardiovascular (Lopes et al., 2021). More
        # after an earlier event.
        def first_year(test):
            ids = [i for i, p in self.baseline.items() if p["adt_type"] is not None and test(p)]
            hits = sum(self.outcome[USUAL][i]["cv_event"] and self.outcome[USUAL][i]["cv_event_day"] <= 336
                       for i in ids)
            return hits / len(ids)
        agonist = lambda p: p["adt_type"] == "gnrh_agonist"
        self.assertAlmostEqual(first_year(agonist), 0.062 * 0.615, delta=0.025)
        self.assertGreater(first_year(lambda p: agonist(p) and p["prior_cardiovascular_event"]),
                           first_year(lambda p: agonist(p) and not p["prior_cardiovascular_event"]))
        self.assertEqual(self.rate("cv_event", lambda p: p["tumour_type"] != "prostate"), 0)

    def test_cardiovascular_history_of_the_patients(self):
        men = [p for p in self.data["baseline"] if p["tumour_type"] == "prostate"]
        share = lambda test: sum(test(p) for p in men) / len(men)
        self.assertAlmostEqual(share(lambda p: p["prior_cardiovascular_event"]), 0.139, delta=0.04)
        self.assertTrue(0.05 < share(lambda p: p["adt_type"] == "gnrh_antagonist") < 0.35)
        for p in self.data["baseline"]:
            self.assertEqual(p["adt_type"] is not None, p["tumour_type"] == "prostate")
            if p["prior_cardiovascular_event"]:
                self.assertTrue(p["cardiovascular_disease"])

    def test_laboratory_values_and_medication_follow_the_literature(self):
        # Lyman et al. (2011): 13.5% with AST above 35 U/l, 19.5% with alkaline
        # phosphatase above 120 U/l, 12.8% with white cells below 5, 14.4% on
        # immunosuppressive medication.
        patients = self.data["baseline"]
        share = lambda test, group=patients: sum(test(p) for p in group) / len(group)
        self.assertAlmostEqual(share(lambda p: p["ast_u_l"] > 35), 0.135, delta=0.06)
        self.assertAlmostEqual(share(lambda p: p["alkaline_phosphatase_u_l"] > 120), 0.195, delta=0.08)
        self.assertAlmostEqual(share(lambda p: p["white_cells_10e9_l"] < 5), 0.128, delta=0.08)
        self.assertAlmostEqual(share(lambda p: p["ugt1a1_28_homozygous"]), 0.10, delta=0.03)
        for p in patients:
            self.assertGreater(p["white_cells_10e9_l"], p["neutrophils_10e9_l"])
            if p["regimen"] == "adt_docetaxel_abiraterone":
                self.assertTrue(p["immunosuppressive_medication"])
        others = [p for p in patients if p["regimen"] != "adt_docetaxel_abiraterone"]
        self.assertAlmostEqual(share(lambda p: p["immunosuppressive_medication"], others), 0.144, delta=0.04)

    def test_neutropenia_follows_the_published_risk_factors(self):
        regimens, params = self.config["regimens"], self.config["parameters"]
        patient = dict(next(p for p in self.data["baseline"] if p["regimen"] == "nalirifox"),
                       gcsf_prophylaxis=False, ugt1a1_28_homozygous=False, prior_therapy_lines=0)
        latent = {"frailty": 0.0}
        value = lambda **changes: hazards.multipliers(
            dict(patient, **changes), latent, params, regimens["nalirifox"])["neutropenia"]
        self.assertAlmostEqual(value(gcsf_prophylaxis=True) / value(), 0.26)
        self.assertAlmostEqual(value(prior_therapy_lines=1) / value(), 1.925)
        self.assertAlmostEqual(value(ugt1a1_28_homozygous=True) / value(), 2.0)
        self.assertAlmostEqual(value(white_cells_10e9_l=patient["white_cells_10e9_l"] + 1) / value(), 0.93)
        # The genotype counts only with irinotecan, the lung factors only with trastuzumab deruxtecan.
        other = lambda **changes: hazards.multipliers(
            dict(patient, **changes), latent, params, regimens["gemcitabine_nab_paclitaxel"])
        self.assertAlmostEqual(other(ugt1a1_28_homozygous=True)["diarrhoea"], other()["diarrhoea"])
        self.assertEqual(other(lung_comorbidity=True, spo2_percent=90)[hazards.ILD], 1.0)
        tdxd = hazards.multipliers(dict(patient, lung_comorbidity=True), latent, params, regimens["trastuzumab_deruxtecan"])
        self.assertGreater(tdxd[hazards.ILD], 1.7)

    def test_severe_neutropenia_and_diarrhoea_follow_the_regimens(self):
        rate = lambda field, regimen: self.rate(field, lambda p: p["regimen"] == regimen)
        self.assertGreater(rate("severe_neutropenia_90d", "gemcitabine_nab_paclitaxel"),
                           rate("severe_neutropenia_90d", "nalirifox"))
        self.assertGreater(rate("severe_diarrhoea_90d", "nalirifox"),
                           rate("severe_diarrhoea_90d", "gemcitabine_nab_paclitaxel") + 0.05)
        self.assertEqual(rate("severe_diarrhoea_90d", "olaparib"), 0)
        self.assertEqual(rate("severe_neutropenia_90d", "olaparib"), 0)

    def test_khorana_score_and_venous_thromboembolism(self):
        # Key et al. (2020): 2 points for pancreatic cancer; 10.2% symptomatic events
        # within three months of chemotherapy without prophylaxis.
        for p in self.data["baseline"]:
            points = 2 * (p["tumour_type"] == "pancreas") + (p["platelets_10e9_l"] >= 350) + (
                p["haemoglobin_g_dl"] < 10) + (p["white_cells_10e9_l"] > 11) + (p["bmi"] >= 35)
            self.assertEqual(p["khorana_score"], points)
            if p["thromboprophylaxis"]:
                self.assertGreaterEqual(p["khorana_score"], 2)
        pancreas = lambda p: p["tumour_type"] == "pancreas"
        self.assertAlmostEqual(self.rate("vte", lambda p: pancreas(p) and not p["thromboprophylaxis"]), 0.102, delta=0.04)
        self.assertEqual(self.rate("vte", lambda p: p["tumour_type"] == "breast"), 0)
        for s in self.scenarios:
            for pid, o in self.outcome[s].items():
                days = [e["day"] for e in self.events[s].get(pid, []) if e["event_type"] == hazards.VTE]
                self.assertEqual(o["vte"], bool(days))
                self.assertEqual(o["vte_day"], min(days) if days else None)
                bleeding = any(e["event_type"] == hazards.BLEEDING for e in self.events[s].get(pid, []))
                self.assertEqual(o["major_bleeding"], bleeding)
                if bleeding:
                    self.assertTrue(self.baseline[pid]["thromboprophylaxis"] or s != USUAL)

    def test_thromboprophylaxis_prevents_thrombosis_and_causes_bleeding(self):
        # Everybody with a Khorana score of 2 or more gets prophylaxis, against nobody.
        rates = {}
        for probability in (0.0, 1.0):
            config = copy.deepcopy(self.config)
            config["parameters"]["treatment_choice"]["thromboprophylaxis"]["probability"] = probability
            data = generate.generate(3000, 9, [USUAL], validate=False, config=config)
            ids = {p["patient_id"] for p in data["baseline"] if p["tumour_type"] == "pancreas"}
            rows = [o for o in data["outcome"] if o["patient_id"] in ids]
            rates[probability] = (sum(o["vte"] for o in rows) / len(rows),
                                  sum(o["major_bleeding"] for o in rows) / len(rows))
        # Hazard ratio 0.41; 1.7 percentage points more major bleeding within 180 days.
        self.assertAlmostEqual(rates[1.0][0] / rates[0.0][0], 0.41, delta=0.17)
        self.assertEqual(rates[0.0][1], 0)
        self.assertAlmostEqual(rates[1.0][1], 0.017, delta=0.012)

    def test_false_alerts_make_the_team_act_less_often(self):
        # With a strong fatigue, fewer true alerts are acted on than without any.
        acted = {}
        for ratio in (1.0, 0.3):
            config = copy.deepcopy(self.config)
            config["interventions"]["participation"]["alert_fatigue"]["action_ratio_per_earlier_false_alert"] = ratio
            data = generate.generate(600, 5, ["symptom_monitoring"], config=config)
            true = [a for a in data["alert"] if a["true_alert"] and a["attended"]]
            acted[ratio] = sum(a["acted"] for a in true) / len(true)
        self.assertGreater(acted[1.0], acted[0.3] + 0.1)

    def test_quality_of_life_follows_the_published_utilities(self):
        # Lloyd et al. (2006): 0.715 on treatment, 0.272 less with progressive disease.
        q = self.config["interventions"]["quality_of_life"]
        self.assertEqual(q["base"]["breast"], 0.715)
        self.assertEqual(q["after_therapy_decrement"], 0.272)
        for o in self.outcome[USUAL].values():
            years = o["follow_up_days"] / 365.25
            self.assertLessEqual(o["qaly"], 0.95 * years + 1e-6)

    def test_lung_toxicity_is_often_recognised_late(self):
        # A cohort of its own: the 3000 patients of the class have only about 35
        # diagnosed lung events, too few for a share (standard error 8 points).
        # 9000 patients give about 100 (standard error 5 points).
        data = generate.generate(9000, seed=7, scenarios=[USUAL], validate=False)
        gaps = [o["ild_diagnosis_day"] - o["ild_onset_day"] for o in data["outcome"]
                if o["ild"] and o["ild_diagnosis_day"] is not None]
        self.assertGreater(len(gaps), 80)
        self.assertAlmostEqual(sum(g > 7 for g in gaps) / len(gaps), 0.53, delta=0.2)    # Powell et al.: 53%

    def test_usual_care_has_no_intervention(self):
        self.assertEqual(self.alerts[USUAL], {})
        for o in self.outcome[USUAL].values():
            self.assertEqual((o["cost_intervention"], o["alerts"], o["participating"], o["high_risk_flag"]),
                             (0, 0, False, False))
        for events in self.events[USUAL].values():
            for e in events:
                self.assertEqual((e["detected_by"], e["day"] >= e["usual_care_day"], e["grade"]),
                                 ("routine", True, e["usual_care_grade"]))

    # Course over time -----------------------------------------------------------

    def test_follow_up_runs_until_death_or_ten_years(self):
        horizon = 7 * self.params["simulation"]["weeks"]
        self.assertEqual(horizon, 3640)
        days = [o["follow_up_days"] for o in self.outcome[USUAL].values()]
        self.assertEqual(max(days), horizon)
        self.assertGreater(sum(d > 364 for d in days) / len(days), 0.4)
        for o in self.outcome[USUAL].values():
            if o["death_day"] is None:
                self.assertEqual(o["follow_up_days"], horizon)
            else:
                self.assertEqual(o["follow_up_days"], o["death_day"])

    def test_outcome_agrees_with_events_and_alerts(self):
        for s in self.scenarios:
            for pid, o in self.outcome[s].items():
                events = self.events[s].get(pid, [])
                alerts = self.alerts[s].get(pid, [])
                days = [e["day"] for e in events if e["grade"] >= 3 and e["day"] <= 90]
                self.assertEqual(o["severe_toxicity_90d"], bool(days))
                self.assertEqual(o["severe_toxicity_day"], min(days) if days else None)
                for field, types in (("severe_neutropenia", ("neutropenia", "febrile_neutropenia")),
                                     ("severe_diarrhoea", ("diarrhoea",))):
                    days = [e["day"] for e in events
                            if e["event_type"] in types and e["grade"] >= 3 and e["day"] <= 90]
                    self.assertEqual(o[f"{field}_90d"], bool(days))
                    self.assertEqual(o[f"{field}_day"], min(days) if days else None)
                self.assertEqual(o["ild"], o["ild_onset_day"] is not None)
                heart = [e for e in events if e["event_type"] == hazards.CV]
                self.assertLessEqual(len(heart), 1)
                self.assertEqual(o["cv_event"], any(e["grade"] >= 3 for e in heart))
                self.assertEqual(o["cv_event"], o["cv_event_day"] is not None)
                self.assertEqual(o["cv_event_1y"], o["cv_event"] and o["cv_event_day"] <= 364)
                self.assertEqual(o["cv_grade"], heart[0]["grade"] if heart else None)
                if heart:
                    self.assertEqual(o["cv_onset_day"], heart[0]["onset_day"])
                self.assertEqual(o["treatment_end_reason"] == "ongoing", o["treatment_end_day"] is None)
                self.assertEqual(o["hospital_days"], sum(e["hospital_days"] for e in events))
                self.assertEqual(o["alerts"], len(alerts))
                self.assertEqual(o["false_alerts"], sum(not a["true_alert"] for a in alerts))
                self.assertEqual(o["death_from_toxicity"], any(e["grade"] == 5 for e in events))
                if o["death_from_toxicity"]:
                    self.assertIsNotNone(o["death_day"])
                self.assertLessEqual(o["qaly"], o["follow_up_days"] / 365.25)

    def test_course_is_consistent(self):
        for s in self.scenarios:
            for pid, rows in self.observations[s].items():
                o = self.outcome[s][pid]
                self.assertEqual([r["week"] for r in rows], list(range(len(rows))))
                self.assertLessEqual(rows[-1]["day"], o["follow_up_days"])
                doses = [r["dose_level"] for r in rows if r["dose_level"] is not None]
                self.assertEqual(doses, sorted(doses, reverse=True))
                stopped = [r["treatment_status"] == "stopped" for r in rows]
                self.assertEqual(stopped, sorted(stopped))
                for e in self.events[s].get(pid, []):
                    self.assertLessEqual(e["onset_day"], e["day"])
                    self.assertLessEqual(e["day"], o["follow_up_days"])
                    self.assertLessEqual(e["icu_days"], e["hospital_days"] + e["icu_days"])

    def test_lab_values_show_severe_events(self):
        for pid, events in self.events[USUAL].items():
            weeks = {r["week"]: r for r in self.observations[USUAL][pid]}
            for e in events:
                row = weeks.get((e["day"] - 1) // 7)
                if row is None:
                    continue
                if e["event_type"] == "neutropenia":
                    self.assertLess(row["neutrophils_10e9_l"], 1.0)
                if e["event_type"] == "anaemia":
                    self.assertLess(row["haemoglobin_g_dl"], 8.05)

    def test_oxygen_saturation_falls_before_diagnosis(self):
        changes = []
        for pid, o in self.outcome[USUAL].items():
            if o["ild_diagnosis_day"] is None or o["ild_grade"] < 2:
                continue
            if o["ild_diagnosis_day"] - o["ild_onset_day"] < 21:
                continue
            for r in self.observations[USUAL][pid]:
                if o["ild_onset_day"] + 14 <= r["day"] <= o["ild_diagnosis_day"] and r["spo2_percent"] is not None:
                    changes.append(r["spo2_percent"] - self.baseline[pid]["spo2_percent"])
        self.assertLess(sum(changes) / len(changes), -1.5)

    def test_blood_pressure_and_chest_pain_rise_in_the_warning_phase(self):
        pressure, pain, quiet = [], [], []
        for pid, o in self.outcome[USUAL].items():
            rows = self.observations[USUAL][pid]
            if self.baseline[pid]["adt_type"] is not None and o["cv_onset_day"] is None:
                quiet += [r["pro_chest_pain"] for r in rows[1:] if r["pro_chest_pain"] is not None]
            if not o["cv_event"] or o["cv_event_day"] - o["cv_onset_day"] < 7:
                continue
            for r in rows:
                if o["cv_onset_day"] <= r["day"] + 6 and r["day"] <= o["cv_event_day"]:
                    if r["systolic_bp_mmhg"] is not None:
                        pressure.append(r["systolic_bp_mmhg"] - self.baseline[pid]["systolic_bp_mmhg"])
                    if r["pro_chest_pain"] is not None:
                        pain.append(r["pro_chest_pain"])
        self.assertGreater(sum(pressure) / len(pressure), 8)
        self.assertGreater(sum(pain) / len(pain), sum(quiet) / len(quiet) + 1)

    # Scenarios ----------------------------------------------------------------------

    def test_usual_care_does_not_depend_on_other_scenarios(self):
        alone = generate.generate(150, seed=9, scenarios=[USUAL], validate=False)
        full = generate.generate(150, seed=9, scenarios=[USUAL, "combined"], validate=False)
        for table in ("observation", "event", "outcome"):
            self.assertEqual(alone[table], generate.of_scenario(full[table], USUAL), table)

    def test_patients_outside_an_intervention_have_the_same_course(self):
        scenario = "lung_monitoring"
        outside = [i for i, o in self.outcome[scenario].items() if not o["participating"]]
        self.assertGreater(len(outside), 2000)
        for pid in outside:
            self.assertEqual(without(self.outcome[scenario][pid], "scenario_id"),
                             without(self.outcome[USUAL][pid], "scenario_id"))
            self.assertEqual([without(r, "scenario_id") for r in self.observations[scenario].get(pid, [])],
                             [without(r, "scenario_id") for r in self.observations[USUAL].get(pid, [])])
            self.assertEqual([without(e, "scenario_id") for e in self.events[scenario].get(pid, [])],
                             [without(e, "scenario_id") for e in self.events[USUAL].get(pid, [])])

    def test_monitoring_recognises_earlier_and_at_a_lower_grade(self):
        found = 0
        for s in self.scenarios:
            for events in self.events[s].values():
                for e in events:
                    self.assertLessEqual(e["grade"], e["usual_care_grade"])
                    if e["detected_by"] == "monitoring":
                        found += 1
                        self.assertLess(e["day"], e["usual_care_day"] + 7)
        self.assertGreater(found, 100)

    def test_alerts_are_consistent(self):
        for s in self.scenarios:
            for alerts in self.alerts[s].values():
                for a in alerts:
                    self.assertTrue(a["attended"] or not a["acted"])
                    self.assertEqual(a["true_alert"], a["event_type"] is not None)
                    if not a["true_alert"]:
                        self.assertFalse(a["acted"])

    def test_lung_monitoring_is_limited_to_its_regimen(self):
        for pid, o in self.outcome["lung_monitoring"].items():
            if o["participating"]:
                self.assertEqual(self.baseline[pid]["regimen"], "trastuzumab_deruxtecan")
        sources = {a["source"] for alerts in self.alerts["lung_monitoring"].values() for a in alerts}
        self.assertEqual(sources, {"lung_monitoring"})

    def test_lung_monitoring_lowers_the_grade_of_lung_toxicity(self):
        # Monitoring also records events that usual care never recognises, because the
        # patient dies or the follow-up ends first. The mean grade shows the effect.
        def grades(s):
            return [e["grade"] for events in self.events[s].values() for e in events
                    if e["event_type"] == hazards.ILD]
        mean = lambda values: sum(values) / len(values)
        self.assertLess(mean(grades("lung_monitoring")), mean(grades(USUAL)))
        severe = lambda s: sum(g >= 3 for g in grades(s))
        self.assertLessEqual(severe("lung_monitoring"), severe(USUAL))

    def test_lung_monitoring_reads_the_measurements(self):
        s = "lung_monitoring"
        true = [a for alerts in self.alerts[s].values() for a in alerts if a["true_alert"]]
        false = [a for alerts in self.alerts[s].values() for a in alerts if not a["true_alert"]]
        self.assertTrue(true)
        self.assertTrue(false)
        for a in true + false:
            # The detection model alerts only on a report with an oxygen saturation,
            # and that saturation is in the observation table.
            week = (a["day"] - 1) // 7
            row = self.observations[s][a["patient_id"]][week]
            self.assertIsNotNone(row["spo2_percent"])
            self.assertLess(row["spo2_percent"], self.baseline[a["patient_id"]]["spo2_percent"])
        # The observations of usual care are the ones the detection model would read.
        self.assertEqual([without(o, "scenario_id") for o in self.observations[USUAL]["P000001"]][:3],
                         [without(o, "scenario_id") for o in self.observations[s]["P000001"]][:3])

    def test_lung_monitoring_can_use_the_stand_in(self):
        config = copy.deepcopy(self.config)
        config["interventions"]["detection"]["lung_monitoring"]["detector"] = "stand_in"
        data = generate.generate(900, 5, ["lung_monitoring"], config=config)
        self.assertTrue(any(a["source"] == "lung_monitoring" for a in data["alert"]))

    def test_cardiovascular_monitoring_is_limited_to_androgen_deprivation(self):
        s = "cardiovascular_monitoring"
        for pid, o in self.outcome[s].items():
            if o["participating"]:
                self.assertEqual(self.baseline[pid]["tumour_type"], "prostate")
        sources = {a["source"] for alerts in self.alerts[s].values() for a in alerts}
        self.assertEqual(sources, {"cardiovascular_monitoring"})
        seen = {a["event_type"] for alerts in self.alerts[s].values() for a in alerts if a["true_alert"]}
        self.assertEqual(seen, {hazards.CV, "hypertension"})

    def test_cardiovascular_monitoring_prevents_events_with_a_warning_phase(self):
        s = "cardiovascular_monitoring"
        self.assertLess(self.total("cv_event", s), self.total("cv_event", USUAL))
        for pid, o in self.outcome[s].items():
            usual = self.outcome[USUAL][pid]
            if usual["cv_event"] and not o["cv_event"] and o["cv_grade"] is not None:
                # Averted: the warning phase was treated before the major event.
                self.assertLess(o["cv_grade"], 3)
                self.assertGreater(usual["cv_event_day"], usual["cv_onset_day"])
        # Sudden events stay, also with perfect detection.
        sudden = [i for i, o in self.outcome[USUAL].items()
                  if o["cv_event"] and o["cv_event_day"] == o["cv_onset_day"]]
        self.assertTrue(sudden)
        self.assertGreater(self.total("cv_event", "perfect_detection"), 0)
        self.assertLess(self.total("cv_event", "perfect_detection"), self.total("cv_event", s))

    def test_risk_adapted_start_flags_the_given_share_and_lowers_toxicity(self):
        s = "risk_adapted_start"
        flagged = [i for i, o in self.outcome[s].items() if o["high_risk_flag"]]
        self.assertAlmostEqual(len(flagged) / len(self.baseline),
                               self.iv["risk_adapted_start"]["share_flagged"], delta=0.01)
        taking_part = [i for i in flagged if self.outcome[s][i]["participating"]]
        self.assertTrue(0.5 < len(taking_part) / len(flagged) < 0.95)
        before = sum(self.outcome[USUAL][i]["severe_toxicity_90d"] for i in taking_part)
        after = sum(self.outcome[s][i]["severe_toxicity_90d"] for i in taking_part)
        self.assertLess(after, 0.92 * before)
        self.assertTrue(all(not self.outcome[s][i]["participating"]
                            for i in self.baseline if i not in flagged))

    def test_model_guided_start_uses_the_risk_models(self):
        s, stand_in = "model_guided_start", "risk_adapted_start"
        flagged = {i for i, o in self.outcome[s].items() if o["high_risk_flag"]}
        self.assertAlmostEqual(len(flagged) / len(self.baseline), 0.3, delta=0.02)
        # The flag follows the model for severe toxicity, not the stand-in.
        scorer = generate.risk_models.Scorer()
        risk = {i: scorer.score(p)["severe_toxicity_90d_risk"] for i, p in self.baseline.items()}
        self.assertGreater(min(risk[i] for i in flagged), max(risk[i] for i in risk if i not in flagged) - 1e-12)
        self.assertNotEqual(flagged, {i for i, o in self.outcome[stand_in].items() if o["high_risk_flag"]})
        self.assertLess(self.rate("severe_toxicity_90d", lambda p: True, s),
                        self.rate("severe_toxicity_90d", lambda p: True, USUAL))
        # Patients who are not flagged or do not take part have the course of usual care.
        for i, o in self.outcome[s].items():
            if not (o["high_risk_flag"] and o["participating"]):
                self.assertEqual(without(o, "scenario_id", "high_risk_flag", "cost_intervention"),
                                 without(self.outcome[USUAL][i], "scenario_id", "high_risk_flag", "cost_intervention"))

    def test_scenarios_order_by_effect(self):
        events = {s: sum(e["grade"] >= 3 for ev in self.events[s].values() for e in ev) for s in self.scenarios}
        self.assertLess(events["symptom_monitoring"], events[USUAL])
        self.assertLess(events["risk_adapted_start"], events[USUAL])
        self.assertLess(events["combined"], min(events["symptom_monitoring"], events["risk_adapted_start"]))
        self.assertLess(self.total("hospital_days", "combined"), self.total("hospital_days", USUAL))
        self.assertGreater(self.total("qaly", "combined"), self.total("qaly", USUAL))
        self.assertGreater(self.total("cost_intervention", "combined"), 0)

    def test_perfect_detection_is_the_upper_limit(self):
        s = "perfect_detection"
        self.assertTrue(all(o["participating"] for o in self.outcome[s].values()))
        # Only events without notice can still be fatal: a cardiovascular event
        # without a warning phase, or a major bleeding.
        sudden = (hazards.CV, hazards.BLEEDING)
        fatal = [e for events in self.events[s].values() for e in events if e["grade"] == 5]
        self.assertTrue(all(e["event_type"] in sudden and e["onset_day"] == e["usual_care_day"] for e in fatal))
        self.assertLess(self.total("death_from_toxicity", s), self.total("death_from_toxicity", "combined"))
        self.assertEqual(self.total("false_alerts", s), 0)
        severe = [e for ev in self.events[s].values() for e in ev if e["grade"] >= 3]
        self.assertTrue(all(e["event_type"] in sudden for e in severe))
        self.assertGreaterEqual(self.total("qaly", s), self.total("qaly", "combined"))


class UncertaintyTest(unittest.TestCase):
    """Repeated simulation with parameters drawn from their published uncertainty."""

    @classmethod
    def setUpClass(cls):
        cls.config = generate.default_config()
        cls.uncertainty = uncertainty.load_uncertainty()

    def test_every_uncertain_parameter_exists(self):
        for entry in self.uncertainty["ratios"] + self.uncertainty["shares"]:
            for path in entry["paths"]:
                self.assertIsInstance(uncertainty._get(self.config, path), float, path)
        for entry in self.uncertainty["ratios"]:
            low, high = entry["interval"]
            value = uncertainty._get(self.config, entry["paths"][0])
            self.assertTrue(low < value < high, entry["name"])
        for name in self.uncertainty["regimen_patients"]:
            if name != "basis":
                self.assertIn(name, self.config["regimens"])

    def test_draws_follow_the_published_intervals(self):
        rng = random.Random(1)
        values = [uncertainty.draw_config(rng, self.config, self.uncertainty)[1] for _ in range(400)]
        gcsf = sorted(v["Neutropenia: G-CSF"] for v in values)
        self.assertAlmostEqual(gcsf[200], 0.26, delta=0.02)                 # the median is the value
        self.assertAlmostEqual(gcsf[10], 0.18, delta=0.03)                  # 2.5% and 97.5% are the interval
        self.assertAlmostEqual(gcsf[389], 0.37, delta=0.05)
        rate = [v["nalirifox: severe toxicity"] for v in values]
        self.assertAlmostEqual(sum(rate) / len(rate), 0.87, delta=0.01)
        self.assertTrue(all(0.78 < r < 0.94 for r in rate))                 # 370 patients
        # The configuration itself stays as it is, and both neutropenia types get the same value.
        drawn, _ = uncertainty.draw_config(rng, self.config, self.uncertainty)
        self.assertEqual(self.config, generate.default_config())
        specific = drawn["parameters"]["hazards"]["specific"]
        self.assertEqual(specific["neutropenia"]["gcsf"], specific["febrile_neutropenia"]["gcsf"])
        self.assertNotEqual(specific["neutropenia"]["gcsf"], 0.26)

    def test_analysis(self):
        result = uncertainty.analyse(240, 3, seed=2, scenarios=["risk_adapted_start"])
        self.assertEqual(list(result["scenarios"]), [USUAL, "risk_adapted_start"])
        self.assertEqual(len(result["drawn"]), 3)
        for measures in result["scenarios"].values():
            for m in measures.values():
                for part in ("value", "difference"):
                    self.assertLessEqual(m[part]["low"], m[part]["mean"] + 1e-12)
                    self.assertLessEqual(m[part]["mean"], m[part]["high"] + 1e-12)
        usual = result["scenarios"][USUAL]["severe_90d"]
        self.assertEqual(usual["difference"], {"mean": 0.0, "low": 0.0, "high": 0.0})
        self.assertLess(usual["value"]["low"], usual["value"]["high"])       # the draws differ
        self.assertLess(result["scenarios"]["risk_adapted_start"]["severe_90d"]["difference"]["mean"], 0)
        # The same seed gives the same analysis.
        again = uncertainty.analyse(240, 3, seed=2, scenarios=["risk_adapted_start"])
        self.assertEqual(result["scenarios"], again["scenarios"])
        self.assertIn("Severe toxicity, 90 days", uncertainty.report(result))


class ReviewFixesTest(unittest.TestCase):
    """Fixes of the code review (project/code-review-issues.md)."""

    def test_a_share_of_zero_flags_nobody(self):
        import interventions
        iv = generate.load_interventions()
        iv["risk_adapted_start"]["share_flagged"] = 0
        threshold = interventions.flag_threshold([0.1, 0.5, 0.9], iv)
        self.assertFalse(any(score >= threshold for score in (0.1, 0.5, 0.9)))
        iv["risk_adapted_start"]["share_flagged"] = 1 / 3
        self.assertEqual(interventions.flag_threshold([0.1, 0.5, 0.9], iv), 0.9)

    def test_zero_weeks_are_zero_weeks(self):
        import course
        config = generate.default_config()
        regimens, params, iv = config["regimens"], config["parameters"], config["interventions"]
        patients, thresholds = generate.cohort(3, 1, regimens, params, iv)
        table = hazards.HazardTable(regimens, params, config["calibration"])
        result = next(generate.run(patients, thresholds, USUAL, regimens, params, iv, table, weeks=0))[3]
        self.assertEqual(result["states"], [])

if __name__ == "__main__":
    unittest.main()
