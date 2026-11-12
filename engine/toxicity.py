"""Simple toxicity models of the engine.

Candidate 1: any adverse event of grade 3 to 5 within 90 days.
Candidate 2: interstitial lung disease or pneumonitis.
"""
import math


def _logit(p):
    return math.log(p / (1 - p))


def _sigmoid(x):
    return 1 / (1 + math.exp(-x))


def severe_toxicity_risk(patient, regimens, params):
    """Probability of a grade 3 to 5 event within the window (logistic model).

    The regimen rate from the literature is the risk of a reference patient:
    reference age, ECOG 0 or 1, no impaired geriatric domain.
    """
    m = params["severe_toxicity"]
    x = _logit(regimens[patient["regimen"]]["severe_toxicity_rate"])
    x += math.log(m["odds_ratio_per_10_years_of_age"]) * (
        patient["age_years"] - m["reference_age"]
    ) / 10
    if patient["ecog"] >= 2:
        x += math.log(m["odds_ratio_ecog_2_or_higher"])
    x += math.log(m["odds_ratio_per_impaired_ga_domain"]) * (
        patient["ga_impaired_domains"] or 0
    )
    return _sigmoid(x)


def ild_hazard_ratio(patient, params):
    """Combined hazard ratio of the baseline risk factors for lung toxicity."""
    hr = params["ild"]["hazard_ratios"]
    ratio = 1.0
    if patient["age_years"] < 65:
        ratio *= hr["age_below_65"]
    if patient["lung_comorbidity"]:
        ratio *= hr["lung_comorbidity"]
    if patient["renal_function"] == "mild_decrease":
        ratio *= hr["renal_mild_decrease"]
    elif patient["renal_function"] == "moderate_severe_decrease":
        ratio *= hr["renal_moderate_severe_decrease"]
    if patient["years_since_diagnosis"] > 4:
        ratio *= hr["more_than_4_years_since_diagnosis"]
    if patient["spo2_percent"] < 95:
        ratio *= hr["spo2_below_95"]
    return ratio


def ild_risk(patient, baseline_risk, params):
    """Probability of lung toxicity within the window (proportional hazards)."""
    return 1 - (1 - baseline_risk) ** ild_hazard_ratio(patient, params)


def calibrate_ild_baseline_risk(patients, target_rate, params):
    """Find the risk of a patient without risk factors, so that the mean risk
    of the given patients equals the rate reported in the literature."""
    if not patients:
        return target_rate
    ratios = [ild_hazard_ratio(p, params) for p in patients]
    low, high = 0.0, target_rate
    for _ in range(60):
        mid = (low + high) / 2
        mean = sum(1 - (1 - mid) ** r for r in ratios) / len(ratios)
        low, high = (mid, high) if mean < target_rate else (low, mid)
    return (low + high) / 2


def draw_outcome(rng, patient, regimens, params, ild_baseline_risks):
    """Return one outcome record that follows schema/outcome.schema.json."""
    tox = params["severe_toxicity"]
    severe = rng.random() < severe_toxicity_risk(patient, regimens, params)
    severe_day = None
    if severe:
        while severe_day is None or severe_day > tox["window_days"]:
            severe_day = 1 + int(rng.expovariate(1 / tox["mean_onset_day"]))

    ild_p = params["ild"]
    baseline_risk = ild_baseline_risks.get(patient["regimen"])
    ild = baseline_risk is not None and rng.random() < ild_risk(
        patient, baseline_risk, params
    )
    onset, grade = None, None
    if ild:
        onset_p = ild_p["onset_days"]
        while onset is None or not 1 <= onset <= ild_p["window_days"]:
            onset = round(
                rng.lognormvariate(math.log(onset_p["median"]), onset_p["sigma"])
            )
        grades = {k: v for k, v in ild_p["grade_probabilities"].items() if k != "basis"}
        grade = int(rng.choices(list(grades), weights=list(grades.values()))[0])

    return {
        "patient_id": patient["patient_id"],
        "severe_toxicity_90d": severe,
        "severe_toxicity_day": severe_day,
        "ild": ild,
        "ild_onset_day": onset,
        "ild_grade": grade,
    }
