"""Scenarios and what they mean for one patient.

A scenario is a set of intervention components. plan() turns a scenario into
the settings of one patient: whether the patient takes part, how the start of
therapy is adapted, and which events monitoring can detect.
"""
import math

from hazards import general_multiplier

COMPONENTS = ("risk_adapted_start", "symptom_monitoring", "lung_monitoring")
SOURCES = ("lung_monitoring", "symptom_report")   # order of priority for an alert


def _sigmoid(x):
    return 1 / (1 + math.exp(-x))


def predictor_score(patient, latent, draws, params, iv, perfect=False):
    """Stand-in for a risk model at therapy start: the true patient-related
    risk on the log scale plus noise. A real risk model can take its place."""
    signal = math.log(general_multiplier(patient, latent, params))
    if perfect:
        return signal
    return signal + iv["risk_adapted_start"]["predictor_noise_sd"] * draws.normal("predictor")


def flag_threshold(scores, iv):
    """Score from which a patient counts as high risk: the given share of the
    cohort is flagged."""
    share = iv["risk_adapted_start"]["share_flagged"]
    ordered = sorted(scores)
    return ordered[min(len(ordered) - 1, int((1 - share) * len(ordered)))]


def plan(patient, latent, regimen, draws, scenario, params, iv, score, threshold):
    """Return the settings of one patient in one scenario."""
    perfect = scenario["perfect"]
    components = set(scenario["components"])
    part = iv["participation"]

    up = part["uptake"]
    uptake = _sigmoid(up["intercept"] + up["frailty_slope"] * latent["frailty"]
                      + up["per_10_years_above_65"] * (patient["age_years"] - 65) / 10)
    takes_part = perfect or draws.u("uptake") < uptake
    ad = part["adherence"]
    adherence = 1.0 if perfect else min(ad["maximum"], max(
        ad["minimum"], ad["base"] + ad["frailty_slope"] * latent["frailty"]))

    result = {
        "perfect": perfect,
        "high_risk": False,
        "participating": False,
        "patient": patient,
        "general_factor": 1.0,
        "sources": [],
        "adherence": adherence,
        "risk_assessed": "risk_adapted_start" in components,
        "attendance": 1.0 if perfect else part["attendance_after_alert"],
        "action": 1.0 if perfect else part["action_after_attended_alert"],
    }

    ras = iv["risk_adapted_start"]
    if "risk_adapted_start" in components and score >= threshold:
        result["high_risk"] = True
        if takes_part:
            result["participating"] = True
            adapted = dict(patient)
            if patient["starting_dose_level"] > ras["reduced_level"] and (
                    draws.u("adapted_dose") < ras["reduced_start_probability"]):
                adapted["starting_dose_level"] = ras["reduced_level"]
            wants_gcsf = regimen["severe_event_rates"].get("neutropenia", 0) >= ras["gcsf_from_neutropenia_rate"]
            if wants_gcsf and not patient["gcsf_prophylaxis"] and (
                    draws.u("adapted_gcsf") < ras["gcsf_probability"]):
                adapted["gcsf_prophylaxis"] = True
            result["patient"] = adapted
            result["general_factor"] = ras["supportive_hazard_ratio"]
            if ras["closer_monitoring"]:
                result["sources"].append("symptom_report")

    if "symptom_monitoring" in components and takes_part:
        result["participating"] = True
        if "symptom_report" not in result["sources"]:
            result["sources"].append("symptom_report")
    lung = iv["detection"]["lung_monitoring"]
    if "lung_monitoring" in components and patient["regimen"] in lung["regimens"] and takes_part:
        result["participating"] = True
        result["sources"].append("lung_monitoring")
    result["sources"].sort(key=SOURCES.index)
    return result


def sensitivity(source, event_type, stage, iv, perfect=False):
    """Probability that one report of a source gives an alert for an event in
    the given stage."""
    d = iv["detection"][source]
    if source == "lung_monitoring":
        if event_type not in d["event_types"]:
            return 0.0
        share = 1.0
    else:
        share = d["detectability"].get(event_type, 0.0)
        if share <= 0:
            return 0.0
    if perfect:
        return 1.0
    return share * d["stage_sensitivity"][str(min(stage, 3))]
