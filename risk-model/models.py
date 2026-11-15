"""Risk models for candidates 1 to 5.

Candidate 1: any adverse event of grade 3 to 5 within 90 days (logistic model).
Candidate 2: interstitial lung disease or pneumonitis (proportional hazards).
Candidate 3: severe or febrile neutropenia within 90 days (logistic model).
Candidate 4: severe diarrhoea within 90 days (logistic model).
Candidate 5: major cardiovascular events under androgen deprivation
(proportional hazards, with an effect that depends on the type of therapy).

All models take one baseline record (schema/baseline.schema.json) and need
only the Python standard library.
"""
import itertools
import json
import math
from pathlib import Path
from statistics import NormalDist

MODEL_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = MODEL_DIR / "config" / "models.json"


def load_config(path=DEFAULT_CONFIG):
    """The model configuration from a JSON file, by default the literature
    configuration."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _logit(p):
    """Log-odds of a probability."""
    return math.log(p / (1 - p))


def _sigmoid(x):
    """Logistic function: probability of a log-odds value."""
    return 1 / (1 + math.exp(-x))


def category(risk, thresholds):
    """Risk category (low, intermediate, high) by the thresholds of a model."""
    if risk >= thresholds["high_from"]:
        return "high"
    if risk >= thresholds["intermediate_from"]:
        return "intermediate"
    return "low"


# Candidate 1 ----------------------------------------------------------------

def severe_toxicity_terms(patient, cfg):
    """Return the factors of candidate 1 that apply to the patient.

    Each term is (factor, value shown to the user, odds ratio applied).
    """
    m = cfg["severe_toxicity_90d"]
    odds = m["odds_ratios"]
    ref_age = m["reference_patient"]["age_years"]
    age = patient["age_years"]
    terms = [(
        "age",
        f"{age} years (reference {ref_age})",
        odds["per_10_years_of_age"]["value"] ** ((age - ref_age) / 10),
    )]
    if patient["ecog"] >= 2:
        terms.append(("ecog", f"ECOG {patient['ecog']}", odds["ecog_2_or_higher"]["value"]))
    domains = patient["ga_impaired_domains"]
    if domains:
        terms.append((
            "geriatric_assessment",
            f"{domains} impaired domain(s)",
            odds["per_impaired_ga_domain"]["value"] ** domains,
        ))
    ref = m["reference_patient"]
    hb = patient["haemoglobin_g_dl"]
    terms.append((
        "haemoglobin",
        f"{hb:g} g/dl (reference {ref['haemoglobin_g_dl']:g})",
        odds["per_g_dl_haemoglobin_below_reference"]["value"] ** (ref["haemoglobin_g_dl"] - hb),
    ))
    albumin = patient["albumin_g_l"]
    terms.append((
        "albumin",
        f"{albumin:g} g/l (reference {ref['albumin_g_l']:g})",
        odds["per_10_g_l_albumin_below_reference"]["value"] ** ((ref["albumin_g_l"] - albumin) / 10),
    ))
    if patient["starting_dose_level"] < m["thresholds"]["reduced_starting_dose_below"]:
        terms.append(("reduced_starting_dose", f"starting dose level {patient['starting_dose_level']:g}",
                      odds["reduced_starting_dose"]["value"]))
    return terms


def severe_toxicity_risk(patient, cfg):
    """Probability of severe toxicity within 90 days: regimen rate on the log-odds
    scale plus the patient's terms."""
    m = cfg["severe_toxicity_90d"]
    x = _logit(m["regimen_rates"][patient["regimen"]]["rate"])
    for _, _, ratio in severe_toxicity_terms(patient, cfg):
        x += math.log(ratio)
    return _sigmoid(x)


# Candidate 2 ----------------------------------------------------------------

# Risk factors of candidate 2, in the order of the configuration. The cut-offs
# of age, years since diagnosis and oxygen saturation are parameters
# (ild/thresholds); the published ones are 65 years, 4 years and 95%.
ILD_FACTORS = ("younger_age", "lung_comorbidity", "renal_mild_decrease",
               "renal_moderate_severe_decrease", "long_since_diagnosis", "low_spo2")


def ild_tests(cfg):
    """Test of every risk factor of candidate 2 on a patient, with the cut-offs
    of the configuration: {factor: function(patient) -> bool}."""
    t = cfg["ild"]["thresholds"]
    return {
        "younger_age": lambda p: p["age_years"] < t["younger_below_age"],
        "lung_comorbidity": lambda p: p["lung_comorbidity"],
        "renal_mild_decrease": lambda p: p["renal_function"] == "mild_decrease",
        "renal_moderate_severe_decrease": lambda p: p["renal_function"] == "moderate_severe_decrease",
        "long_since_diagnosis": lambda p: p["years_since_diagnosis"] > t["long_since_diagnosis_more_than_years"],
        "low_spo2": lambda p: p["spo2_percent"] < t["low_spo2_below_percent"],
    }


def ild_labels(cfg):
    """Readable name of every risk factor of candidate 2, with the cut-offs of
    the configuration, e.g. "age below 65"."""
    t = cfg["ild"]["thresholds"]
    return {
        "younger_age": f"age below {t['younger_below_age']:g}",
        "lung_comorbidity": "lung comorbidity",
        "renal_mild_decrease": "renal function mildly decreased",
        "renal_moderate_severe_decrease": "renal function moderately or severely decreased",
        "long_since_diagnosis": f"more than {t['long_since_diagnosis_more_than_years']:g} years since diagnosis",
        "low_spo2": f"oxygen saturation below {t['low_spo2_below_percent']:g}%",
    }


def ild_applicable(patient, cfg):
    """True if the lung model has a rate for the patient's regimen."""
    return patient["regimen"] in cfg["ild"]["regimen_rates"]


def ild_uses_factors(regimen, cfg):
    """True if the published risk factors apply to the regimen. Other covered
    regimens get their rate for every patient."""
    return cfg["ild"]["regimen_rates"][regimen].get("risk_factors", True)


def ild_terms(patient, cfg):
    """Return the risk factors of candidate 2 that apply to the patient.

    Each term is (factor, label, hazard ratio).
    """
    if not ild_uses_factors(patient["regimen"], cfg):
        return []
    hr, labels = cfg["ild"]["hazard_ratios"], ild_labels(cfg)
    return [
        (name, labels[name], hr[name]["value"])
        for name, test in ild_tests(cfg).items()
        if test(patient)
    ]


def _reference_profiles(ref):
    """All combinations of risk factors with their share in the reference
    population, assuming independent factors. Yields (share, factor names)."""
    renal = [
        (1 - ref["renal_mild_decrease"] - ref["renal_moderate_severe_decrease"], []),
        (ref["renal_mild_decrease"], ["renal_mild_decrease"]),
        (ref["renal_moderate_severe_decrease"], ["renal_moderate_severe_decrease"]),
    ]
    binary = [
        [(1 - ref[name], []), (ref[name], [name])]
        for name in ("younger_age", "lung_comorbidity", "long_since_diagnosis", "low_spo2")
    ]
    for combo in itertools.product(renal, *binary):
        share = math.prod(s for s, _ in combo)
        yield share, [n for _, names in combo for n in names]


def solve_baseline_risk(profiles, target):
    """Risk r0 without risk factors such that the mean risk 1 - (1 - r0)^ratio
    over the profiles [(share, ratio)] equals the target rate.

    The mean risk grows with r0, so a bisection over [0, 1] finds it. The upper
    bound is 1, not the target: with protective factors (ratio below 1) r0 lies
    above the target."""
    low, high = 0.0, 1.0
    for _ in range(60):
        mid = (low + high) / 2
        mean = sum(share * (1 - (1 - mid) ** ratio) for share, ratio in profiles)
        low, high = (mid, high) if mean < target else (low, mid)
    return (low + high) / 2


def ild_baseline_risk(regimen, cfg):
    """Risk r0 of a patient without risk factors on the given regimen.

    A fitted configuration stores r0 directly. Otherwise r0 is chosen so that
    the mean risk in the reference population equals the regimen rate.
    """
    entry = cfg["ild"]["regimen_rates"][regimen]
    if "baseline_risk" in entry:
        return entry["baseline_risk"]
    if not ild_uses_factors(regimen, cfg):
        return entry["rate"]
    hr = cfg["ild"]["hazard_ratios"]
    profiles = [
        (share, math.prod(hr[n]["value"] for n in names))
        for share, names in _reference_profiles(cfg["ild"]["reference_population"])
    ]
    return solve_baseline_risk(profiles, entry["rate"])


def ild_risk(patient, cfg, baseline_risk=None):
    """Probability of lung toxicity, or None if the model does not apply."""
    if not ild_applicable(patient, cfg):
        return None
    r0 = baseline_risk if baseline_risk is not None else ild_baseline_risk(patient["regimen"], cfg)
    ratio = math.prod(t[2] for t in ild_terms(patient, cfg))
    return 1 - (1 - r0) ** ratio


def ild_onset_share(day, cfg):
    """Share of the lung toxicity events of the time window that have started
    by a day, from the log-normal onset time."""
    m = cfg["ild"]
    onset = NormalDist(math.log(m["onset_days"]["median"]), m["onset_days"]["sigma"])
    if day <= 0:
        return 0.0
    day = min(day, m["window_days"])
    return onset.cdf(math.log(day)) / onset.cdf(math.log(m["window_days"]))


def ild_risk_by_day(patient, day, cfg, baseline_risk=None):
    """Probability of lung toxicity up to a day of the time window, or None if
    the model does not apply."""
    risk = ild_risk(patient, cfg, baseline_risk)
    return None if risk is None else risk * ild_onset_share(day, cfg)


def ild_remaining_risk(patient, day, cfg, baseline_risk=None):
    """Probability of lung toxicity in the rest of the time window for a
    patient who is free of it on the given day, or None if the model does not
    apply."""
    risk = ild_risk(patient, cfg, baseline_risk)
    if risk is None:
        return None
    so_far = risk * ild_onset_share(day, cfg)
    return (risk - so_far) / (1 - so_far)


# Candidates 3 and 4 -----------------------------------------------------------

def _profiles(factors):
    """All combinations of independent yes-or-no factors [(share, ratio)] as
    [(share of the combination, product of its ratios)]."""
    factors = [(s, r) for s, r in factors if s > 0]
    profiles = []
    for combo in itertools.product(*[((1 - share, 1.0), (share, ratio)) for share, ratio in factors]):
        profiles.append((math.prod(s for s, _ in combo), math.prod(r for _, r in combo)))
    return profiles


def solve_reference_risk(profiles, target):
    """Risk of the reference patient such that the mean risk over the
    profiles [(share, odds ratio)] equals the target rate. The mean risk
    grows with the log-odds of the reference patient, so a bisection finds
    it."""
    low, high = -30.0, 30.0
    for _ in range(80):
        mid = (low + high) / 2
        mean = sum(share * _sigmoid(mid + math.log(ratio)) for share, ratio in profiles)
        low, high = (mid, high) if mean < target else (low, mid)
    return _sigmoid((low + high) / 2)


def _odds_risk(reference_risk, terms):
    """Risk from the risk of the reference patient and odds ratio terms."""
    return _sigmoid(_logit(reference_risk) + sum(math.log(ratio) for _, _, ratio in terms))


# Yes-or-no factors of candidate 3: name in the configuration, readable label.
NEUTROPENIA_LABELS = {
    "prior_chemotherapy": "earlier chemotherapy",
    "age_65_or_older": "age 65 or older",
    "ast_above_35": "AST above 35 U/l",
    "alkaline_phosphatase_above_120": "alkaline phosphatase above 120 U/l",
    "bilirubin_above_normal": "bilirubin above normal",
    "egfr": "renal function (eGFR)",
    "white_cells": "white blood cells",
    "immunosuppressive_medication": "immunosuppressive medication",
    "reduced_starting_dose": "reduced starting dose",
    "gcsf_prophylaxis": "G-CSF prophylaxis",
    "ugt1a1_28_homozygous_with_irinotecan": "UGT1A1*28 homozygous, with irinotecan",
}


def neutropenia_tests(regimen, cfg):
    """Test of every yes-or-no factor of candidate 3 on a patient, with the
    cut-offs of the configuration: {factor: function(patient) -> bool}."""
    m = cfg["neutropenia"]
    t = m["thresholds"]
    irinotecan = m["regimen_rates"][regimen].get("irinotecan", False)
    return {
        "prior_chemotherapy": lambda p: p["prior_therapy_lines"] >= t["prior_chemotherapy_from_lines"],
        "age_65_or_older": lambda p: p["age_years"] >= t["older_from_age"],
        "ast_above_35": lambda p: p["ast_u_l"] > t["ast_above_u_l"],
        "alkaline_phosphatase_above_120": lambda p: p["alkaline_phosphatase_u_l"] > t["alkaline_phosphatase_above_u_l"],
        "bilirubin_above_normal": lambda p: p["bilirubin_ratio_uln"] > t["bilirubin_above_ratio_uln"],
        "immunosuppressive_medication": lambda p: p["immunosuppressive_medication"],
        "reduced_starting_dose": lambda p: p["starting_dose_level"] < t["reduced_starting_dose_below"],
        "gcsf_prophylaxis": lambda p: p["gcsf_prophylaxis"],
        "ugt1a1_28_homozygous_with_irinotecan": lambda p: irinotecan and p["ugt1a1_28_homozygous"],
    }


def neutropenia_applicable(patient, cfg):
    """True if the neutropenia model has a rate for the patient's regimen."""
    return patient["regimen"] in cfg["neutropenia"]["regimen_rates"]


def neutropenia_terms(patient, cfg):
    """Return the factors of candidate 3 for the patient as (factor, label,
    odds ratio). Renal function and white cells are always listed."""
    m = cfg["neutropenia"]
    odds, ref = m["odds_ratios"], m["reference_patient"]
    terms = [(name, NEUTROPENIA_LABELS[name], odds[name]["value"])
             for name, test in neutropenia_tests(patient["regimen"], cfg).items() if test(patient)]
    egfr, white = patient["egfr_ml_min"], patient["white_cells_10e9_l"]
    terms.append(("egfr", f"eGFR {egfr:g} ml/min (reference {ref['egfr_ml_min']:g})",
                  odds["per_ml_min_of_egfr"]["value"] ** (egfr - ref["egfr_ml_min"])))
    terms.append(("white_cells", f"white cells {white:g} (reference {ref['white_cells_10e9_l']:g})",
                  odds["per_10e9_l_of_white_cells"]["value"] ** (white - ref["white_cells_10e9_l"])))
    return terms


def neutropenia_reference_risk(regimen, cfg):
    """Risk of the reference patient on the regimen: none of the yes-or-no
    factors, reference renal function and white cells.

    A fitted configuration stores it directly. Otherwise it is chosen so that
    the mean risk in the reference population equals the regimen rate.
    """
    m = cfg["neutropenia"]
    entry = m["regimen_rates"][regimen]
    if "reference_risk" in entry:
        return entry["reference_risk"]
    odds, ref = m["odds_ratios"], m["reference_population"]
    shares = {
        "prior_chemotherapy": entry["prior_chemotherapy_share"],
        "age_65_or_older": entry["age_65_or_older_share"],
        "gcsf_prophylaxis": entry["gcsf_share"],
        "ast_above_35": ref["ast_above_35"],
        "alkaline_phosphatase_above_120": ref["alkaline_phosphatase_above_120"],
        "bilirubin_above_normal": ref["bilirubin_above_normal"],
        "immunosuppressive_medication": 1.0 if entry.get("corticosteroid") else ref["immunosuppressive_medication"],
        "ugt1a1_28_homozygous_with_irinotecan":
            ref["ugt1a1_28_homozygous_with_irinotecan"] if entry.get("irinotecan") else 0.0,
    }
    return solve_reference_risk(_profiles([(s, odds[n]["value"]) for n, s in shares.items()]), entry["rate"])


def neutropenia_risk(patient, cfg, reference_risk=None):
    """Probability of severe or febrile neutropenia within the time window,
    or None if the model does not apply."""
    if not neutropenia_applicable(patient, cfg):
        return None
    r0 = reference_risk if reference_risk is not None else neutropenia_reference_risk(patient["regimen"], cfg)
    return _odds_risk(r0, neutropenia_terms(patient, cfg))


# Factors of candidate 4: name in the configuration, readable label.
DIARRHOEA_LABELS = {
    "age_70_or_older": "age 70 or older",
    "ecog_2_or_higher": "ECOG 2 or higher",
    "low_albumin": "low albumin",
    "ugt1a1_28_homozygous_with_irinotecan": "UGT1A1*28 homozygous, with irinotecan",
}


def diarrhoea_tests(regimen, cfg):
    """Test of every factor of candidate 4 on a patient, with the cut-offs of
    the configuration: {factor: function(patient) -> bool}."""
    m = cfg["diarrhoea"]
    t = m["thresholds"]
    irinotecan = m["regimen_rates"][regimen].get("irinotecan", False)
    return {
        "age_70_or_older": lambda p: p["age_years"] >= t["older_from_age"],
        "ecog_2_or_higher": lambda p: p["ecog"] >= 2,
        "low_albumin": lambda p: p["albumin_g_l"] < t["low_albumin_below_g_l"],
        "ugt1a1_28_homozygous_with_irinotecan": lambda p: irinotecan and p["ugt1a1_28_homozygous"],
    }


def diarrhoea_applicable(patient, cfg):
    """True if the diarrhoea model has a rate for the patient's regimen."""
    return patient["regimen"] in cfg["diarrhoea"]["regimen_rates"]


def diarrhoea_terms(patient, cfg):
    """Return the factors of candidate 4 that apply to the patient as
    (factor, label, odds ratio)."""
    odds = cfg["diarrhoea"]["odds_ratios"]
    return [(name, DIARRHOEA_LABELS[name], odds[name]["value"])
            for name, test in diarrhoea_tests(patient["regimen"], cfg).items() if test(patient)]


def diarrhoea_reference_risk(regimen, cfg):
    """Risk of a patient without any factor on the regimen. A fitted
    configuration stores it directly. Otherwise it is chosen so that the mean
    risk in the reference population equals the regimen rate."""
    m = cfg["diarrhoea"]
    entry = m["regimen_rates"][regimen]
    if "reference_risk" in entry:
        return entry["reference_risk"]
    odds, ref = m["odds_ratios"], m["reference_population"]
    factors = [(ref[name] if name != "ugt1a1_28_homozygous_with_irinotecan" or entry.get("irinotecan") else 0.0,
                odds[name]["value"]) for name in DIARRHOEA_LABELS]
    return solve_reference_risk(_profiles(factors), entry["rate"])


def diarrhoea_risk(patient, cfg, reference_risk=None):
    """Probability of severe diarrhoea within the time window, or None if the
    model does not apply."""
    if not diarrhoea_applicable(patient, cfg):
        return None
    r0 = reference_risk if reference_risk is not None else diarrhoea_reference_risk(patient["regimen"], cfg)
    return _odds_risk(r0, diarrhoea_terms(patient, cfg))


# Candidate 5 ----------------------------------------------------------------

# Yes-or-no risk factors of candidate 5 next to the earlier cardiovascular
# event and age: name in the configuration, test on a patient.
CV_FACTORS = {
    "diabetes": lambda p: p["diabetes"],
    "arterial_hypertension": lambda p: p["arterial_hypertension"],
    "current_smoker": lambda p: p["smoking_status"] == "current",
    "former_smoker": lambda p: p["smoking_status"] == "former",
    "renal_moderate_severe_decrease": lambda p: p["renal_function"] == "moderate_severe_decrease",
    "cardiovascular_disease_without_event": lambda p: p["cardiovascular_disease"] and not p["prior_cardiovascular_event"],
}

CV_LABELS = {
    "prior_cardiovascular_event": "earlier myocardial infarction or stroke",
    "cv_age": "age",
    "diabetes": "diabetes",
    "arterial_hypertension": "arterial hypertension",
    "current_smoker": "current smoker",
    "former_smoker": "former smoker",
    "renal_moderate_severe_decrease": "renal function moderately or severely decreased",
    "cardiovascular_disease_without_event": "cardiovascular disease without an earlier event",
}

ADT_LABELS = {"gnrh_agonist": "GnRH agonist", "gnrh_antagonist": "GnRH antagonist"}


def cv_applicable(patient, cfg):
    """True if the patient has a type of androgen deprivation that the cardiovascular
    model covers."""
    return patient.get("adt_type") in cfg["cardiovascular"]["adt_rates"]


def cv_terms(patient, cfg):
    """Return the risk factors of candidate 5 that apply to the patient.

    Each term is (factor, label, hazard ratio). Age is always listed.
    """
    m = cfg["cardiovascular"]
    terms = []
    if patient["prior_cardiovascular_event"]:
        adt = patient["adt_type"]
        terms.append(("prior_cardiovascular_event",
                      f"{CV_LABELS['prior_cardiovascular_event']}, under a {ADT_LABELS[adt]}",
                      m["prior_event_hazard_ratios"][adt]["value"]))
    hr = m["hazard_ratios"]
    ref_age = m["reference_patient"]["age_years"]
    age = patient["age_years"]
    terms.append(("cv_age", f"{age} years (reference {ref_age})",
                  hr["per_10_years_of_age"]["value"] ** ((age - ref_age) / 10)))
    terms += [(name, CV_LABELS[name], hr[name]["value"]) for name, test in CV_FACTORS.items() if test(patient)]
    return terms


def cv_reference_rate(adt, cfg):
    """Published rate of the type of androgen deprivation, brought to
    cardiovascular events and from the weeks of the trial to the time window
    of the model."""
    m = cfg["cardiovascular"]
    rate = m["adt_rates"][adt]["rate"] * m.get("cardiovascular_share_of_events", {"value": 1.0})["value"]
    return 1 - (1 - rate) ** (m["window_days"] / m["rate_window_days"])


def cv_baseline_risk(adt, cfg):
    """Risk r0 of a man of the reference age without risk factors on the given
    type of androgen deprivation.

    A fitted configuration stores r0 directly. Otherwise r0 is chosen so that
    the mean risk in the reference population equals the published rate.
    """
    m = cfg["cardiovascular"]
    entry = m["adt_rates"][adt]
    if "baseline_risk" in entry:
        return entry["baseline_risk"]
    ref = m["reference_population"]
    prior = ref["prior_cardiovascular_event"][adt]
    factors = [(prior, m["prior_event_hazard_ratios"][adt]["value"])]
    # Cardiovascular disease without an event and the earlier event exclude each
    # other, as do current and former smoking; with small shares the error of
    # treating them as independent is small.
    factors += [(ref[name], m["hazard_ratios"][name]["value"]) for name in CV_FACTORS]
    return solve_baseline_risk(_profiles(factors), cv_reference_rate(adt, cfg))


def cv_risk(patient, cfg, baseline_risk=None):
    """Probability of a major cardiovascular event within the time window, or
    None if the model does not apply."""
    if not cv_applicable(patient, cfg):
        return None
    r0 = baseline_risk if baseline_risk is not None else cv_baseline_risk(patient["adt_type"], cfg)
    ratio = math.prod(t[2] for t in cv_terms(patient, cfg))
    return 1 - (1 - r0) ** ratio


def cv_risk_on(patient, adt, cfg):
    """Risk of the same man on another type of androgen deprivation."""
    return cv_risk(dict(patient, adt_type=adt), cfg)


# Scores for the app -----------------------------------------------------------

class Scorer:
    """All models with one configuration. Writes the scores of a patient as
    one record of schema/risk_score. The interface for single models, as the
    app uses it, is in toxage_risk.py."""

    def __init__(self, cfg=None):
        """Prepare the baseline risks r0 of all regimens and types of androgen
        deprivation once."""
        self.cfg = cfg or load_config()
        self.ild_r0 = {r: ild_baseline_risk(r, self.cfg) for r in self.cfg["ild"]["regimen_rates"]}
        self.cv_r0 = {a: cv_baseline_risk(a, self.cfg) for a in self.cfg["cardiovascular"]["adt_rates"]}
        self.neutropenia_r0 = {r: neutropenia_reference_risk(r, self.cfg) for r in self.cfg["neutropenia"]["regimen_rates"]}
        self.diarrhoea_r0 = {r: diarrhoea_reference_risk(r, self.cfg) for r in self.cfg["diarrhoea"]["regimen_rates"]}

    def score(self, patient):
        """Return one risk score record."""
        c1 = self.cfg["severe_toxicity_90d"]
        c2 = self.cfg["ild"]
        severe = severe_toxicity_risk(patient, self.cfg)
        record = {
            "patient_id": patient["patient_id"],
            "model_version": self.cfg["version"],
            "severe_toxicity_90d_risk": severe,
            "severe_toxicity_90d_regimen_rate": c1["regimen_rates"][patient["regimen"]]["rate"],
            "severe_toxicity_90d_category": category(severe, c1["categories"]),
            "ild_applicable": ild_applicable(patient, self.cfg),
            "ild_risk": None,
            "ild_grade2plus_risk": None,
            "ild_regimen_rate": None,
            "ild_category": None,
            "neutropenia_applicable": neutropenia_applicable(patient, self.cfg),
            "neutropenia_risk": None,
            "neutropenia_regimen_rate": None,
            "neutropenia_category": None,
            "diarrhoea_applicable": diarrhoea_applicable(patient, self.cfg),
            "diarrhoea_risk": None,
            "diarrhoea_regimen_rate": None,
            "diarrhoea_category": None,
            "cv_applicable": cv_applicable(patient, self.cfg),
            "cv_risk": None,
            "cv_reference_rate": None,
            "cv_category": None,
        }
        if record["cv_applicable"]:
            risk = cv_risk(patient, self.cfg, self.cv_r0[patient["adt_type"]])
            record.update(
                cv_risk=risk,
                cv_reference_rate=cv_reference_rate(patient["adt_type"], self.cfg),
                cv_category=category(risk, self.cfg["cardiovascular"]["categories"]),
            )
        for key, risk_of, r0 in (("neutropenia", neutropenia_risk, self.neutropenia_r0),
                                 ("diarrhoea", diarrhoea_risk, self.diarrhoea_r0)):
            if record[f"{key}_applicable"]:
                risk = risk_of(patient, self.cfg, r0[patient["regimen"]])
                record.update({
                    f"{key}_risk": risk,
                    f"{key}_regimen_rate": self.cfg[key]["regimen_rates"][patient["regimen"]]["rate"],
                    f"{key}_category": category(risk, self.cfg[key]["categories"]),
                })
        if record["ild_applicable"]:
            risk = ild_risk(patient, self.cfg, self.ild_r0[patient["regimen"]])
            record.update(
                ild_risk=risk,
                ild_grade2plus_risk=risk * c2["grade2plus_share"]["value"],
                ild_regimen_rate=c2["regimen_rates"][patient["regimen"]]["rate"],
                ild_category=category(risk, c2["categories"]),
            )
        return record

    def explain(self, patient):
        """Return the factors behind the scores of one patient, for display.

        Candidates 1, 3 and 4 list odds ratios against the reference patient on
        the same regimen, candidates 2 and 5 hazard ratios against a patient
        without risk factors.
        """
        regimen = patient["regimen"]
        c1 = self.cfg["severe_toxicity_90d"]
        out = {
            "severe_toxicity_90d": {
                "start": {
                    "label": "reference patient on this regimen",
                    "risk": c1["regimen_rates"][regimen]["rate"],
                    "source": c1["regimen_rates"][regimen].get("source"),
                },
                "factors": [
                    {"factor": f, "value": v, "odds_ratio": r}
                    for f, v, r in severe_toxicity_terms(patient, self.cfg)
                ],
            },
            "ild": None,
        }
        if ild_applicable(patient, self.cfg):
            out["ild"] = {
                "start": {
                    "label": "patient without risk factors on this regimen",
                    "risk": self.ild_r0[regimen],
                    "source": self.cfg["ild"]["regimen_rates"][regimen].get("source"),
                },
                "factors": [
                    {"factor": f, "value": label, "hazard_ratio": r}
                    for f, label, r in ild_terms(patient, self.cfg)
                ],
            }
        for key, terms, r0 in (("neutropenia", neutropenia_terms, self.neutropenia_r0),
                               ("diarrhoea", diarrhoea_terms, self.diarrhoea_r0)):
            out[key] = None
            if regimen in r0:
                out[key] = {
                    "start": {
                        "label": "reference patient on this regimen",
                        "risk": r0[regimen],
                        "source": self.cfg[key]["regimen_rates"][regimen].get("source"),
                    },
                    "factors": [{"factor": f, "value": label, "odds_ratio": r} for f, label, r in terms(patient, self.cfg)],
                }
        out["cardiovascular"] = None
        if cv_applicable(patient, self.cfg):
            adt = patient["adt_type"]
            out["cardiovascular"] = {
                "start": {
                    "label": f"man of the reference age without risk factors on a {ADT_LABELS[adt]}",
                    "risk": self.cv_r0[adt],
                    "source": self.cfg["cardiovascular"]["adt_rates"][adt].get("source"),
                },
                "factors": [
                    {"factor": f, "value": label, "hazard_ratio": r}
                    for f, label, r in cv_terms(patient, self.cfg)
                ],
            }
        return out
