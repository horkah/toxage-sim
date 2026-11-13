"""Weekly hazards of adverse events.

The hazard of an event type in a week is
    target hazard of the regimen x time weight of the week x patient multiplier
    x dose effect x calibration factor.
"""
import math
from statistics import NormalDist

ILD = "interstitial_lung_disease"
CV = "cardiovascular_event"
# Event types with risk factors of their own. The general patient factor, the
# dose and the supportive measures of a risk-adapted start do not act on them.
OWN_FACTORS = (ILD, CV)


def time_weights(shape, weeks, params):
    """Share of the cumulative hazard that falls into each week.

    The shares of the first weeks, up to the calibration window, sum to 1.
    Later weeks continue the same shape.
    """
    s = params["hazards"]["shapes"]
    window = params["simulation"]["calibration_weeks"]
    if shape == "early":
        raw = [math.exp(-w / s["early"]["decay_weeks"]) for w in range(weeks)]
    elif shape == "mid":
        raw = [(w + 1) * math.exp(-(w + 1) / s["mid"]["peak_weeks"]) for w in range(weeks)]
    elif shape == "cumulative":
        raw = [min(w + 1, s["cumulative"]["plateau_weeks"]) for w in range(weeks)]
    elif shape == "constant":
        raw = [1.0] * weeks
    elif shape == "ild":
        o = params["hazards"]["ild"]["onset_days"]
        dist = NormalDist(math.log(o["median"]), o["sigma"])
        cdf = [0.0] + [dist.cdf(math.log(7 * (w + 1))) for w in range(weeks)]
        raw = [cdf[w + 1] - cdf[w] for w in range(weeks)]
    else:
        raise ValueError(shape)
    total = sum(raw[:window])
    return [r / total for r in raw]


def target_probabilities(regimen, params):
    """Share of trial patients with at least one event, per event type.

    'other' is set so that the event types together give the overall rate of
    severe toxicity, if they were independent.
    """
    targets = dict(regimen["severe_event_rates"])
    if regimen["cardiovascular_event_rate"] is not None:
        # The published rate holds for the weeks of the trial.
        share = params["simulation"]["calibration_weeks"] / params["hazards"]["cardiovascular"]["rate_window_weeks"]
        targets[CV] = 1 - (1 - regimen["cardiovascular_event_rate"]) ** share
    none = 1.0
    for p in targets.values():
        none *= 1 - p
    targets["other"] = max(0.0, 1 - (1 - regimen["severe_toxicity_rate"]) / none)
    if regimen["ild_rate"] is not None:
        share = params["hazards"]["ild"]["onset_days"]["share_within_52_weeks"]
        targets[ILD] = regimen["ild_rate"] * share
    return targets


def multipliers(patient, latent, params):
    """Hazard multiplier of one patient for every event type."""
    hz = params["hazards"]
    general = general_multiplier(patient, latent, params)
    pretreated = patient["prior_therapy_lines"] >= params["population"]["pretreated_from_lines"]
    sp = hz["specific"]

    result = {name: general for name in hz["event_types"]}
    for name in ("neutropenia", "febrile_neutropenia"):
        m = sp[name]
        result[name] *= (m["reference_neutrophils"] / patient["neutrophils_10e9_l"]) ** m["baseline_neutrophils_exponent"]
        if pretreated:
            result[name] *= m["pretreated"]
        if patient["gcsf_prophylaxis"]:
            result[name] *= m["gcsf"]
    m = sp["anaemia"]
    result["anaemia"] *= math.exp(m["log_hazard_ratio_per_g_dl_below_12_5"] * (12.5 - patient["haemoglobin_g_dl"]))
    if patient["renal_function"] == "moderate_severe_decrease":
        result["anaemia"] *= m["renal_moderate_severe"]
    m = sp["thrombocytopenia"]
    result["thrombocytopenia"] *= (m["reference_platelets"] / patient["platelets_10e9_l"]) ** m["baseline_platelets_exponent"]
    if pretreated:
        result["thrombocytopenia"] *= m["pretreated"]
    if patient["age_years"] >= 70:
        result["diarrhoea"] *= sp["diarrhoea"]["age_70_or_older"]
    if patient["diabetes"]:
        result["peripheral_neuropathy"] *= sp["peripheral_neuropathy"]["diabetes"]
    if patient["cardiovascular_disease"]:
        result["hypertension"] *= sp["hypertension"]["cardiovascular_disease"]

    hr = hz["ild"]["hazard_ratios"]
    ild = 1.0
    if patient["age_years"] < 65:
        ild *= hr["age_below_65"]
    if patient["lung_comorbidity"]:
        ild *= hr["lung_comorbidity"]
    if patient["renal_function"] == "mild_decrease":
        ild *= hr["renal_mild_decrease"]
    elif patient["renal_function"] == "moderate_severe_decrease":
        ild *= hr["renal_moderate_severe_decrease"]
    if patient["years_since_diagnosis"] > 4:
        ild *= hr["more_than_4_years_since_diagnosis"]
    if patient["spo2_percent"] < 95:
        ild *= hr["spo2_below_95"]
    result[ILD] = ild
    result[CV] = cardiovascular_multiplier(patient, latent, params)
    return result


def cardiovascular_multiplier(patient, latent, params):
    """Hazard multiplier for a major cardiovascular event under androgen
    deprivation, relative to a man of the reference age on a GnRH agonist
    without risk factors. 1 for patients without androgen deprivation, who
    have no such hazard."""
    if patient["adt_type"] is None:
        return 1.0
    c = params["hazards"]["cardiovascular"]
    hr, other = c["hazard_ratios"], c["other_hazard_ratios"]
    value = 1.0
    if patient["adt_type"] == "gnrh_antagonist":
        value *= hr["antagonist"]
        if patient["prior_cardiovascular_event"]:
            value *= hr["prior_event_with_antagonist"]
    elif patient["prior_cardiovascular_event"]:
        value *= hr["prior_event_with_agonist"]
    if patient["cardiovascular_disease"] and not patient["prior_cardiovascular_event"]:
        value *= other["cardiovascular_disease_without_event"]
    value *= other["per_10_years_of_age"] ** ((patient["age_years"] - other["reference_age"]) / 10)
    if patient["diabetes"]:
        value *= other["diabetes"]
    if patient["arterial_hypertension"]:
        value *= other["arterial_hypertension"]
    if patient["smoking_status"] == "current":
        value *= other["current_smoker"]
    elif patient["smoking_status"] == "former":
        value *= other["former_smoker"]
    if patient["renal_function"] == "moderate_severe_decrease":
        value *= other["renal_moderate_severe_decrease"]
    return value * math.exp(other["frailty_log_hazard_ratio"] * latent["frailty"])


class HazardTable:
    """Target hazards and time weights per regimen, prepared once."""

    def __init__(self, regimens, params, calibration=None):
        self.weeks = params["simulation"]["weeks"]
        window = params["simulation"]["calibration_weeks"]
        self.params = params
        self.calibration = calibration or {}
        types = params["hazards"]["event_types"]
        shapes = {s: time_weights(s, self.weeks, params) for s in ("early", "mid", "cumulative", "constant", "ild")}
        self.targets = {name: target_probabilities(r, params) for name, r in regimens.items()}
        self.rows = {}
        for name, regimen in regimens.items():
            rows = []
            for event_type, p in self.targets[name].items():
                if p <= 0:
                    continue
                if event_type == ILD:
                    # The published onset times were seen in patients still on
                    # treatment. Dividing by the share still on treatment keeps
                    # the observed onset times close to the published ones.
                    on = [0.5 ** (min(w, window) / regimen["median_treatment_weeks"])
                          for w in range(self.weeks)]
                    weights = [w / s for w, s in zip(shapes["ild"], on)]
                    total = sum(weights[:window])
                    weights = [w / total for w in weights]
                else:
                    weights = list(shapes[types[event_type]["shape"]])
                    stop = regimen["chemotherapy_weeks"]
                    if stop is not None and types[event_type]["chemotherapy"]:
                        weights = [w if i < stop else 0.0 for i, w in enumerate(weights)]
                factor = self.calibration.get(name, {}).get(event_type, 1.0)
                rows.append((event_type, -math.log(1 - p) * factor, weights))
            self.rows[name] = rows

    def for_patient(self, patient, latent, general_factor=1.0):
        """Return [(event type, hazard coefficient, weekly weights)] and the
        multipliers. general_factor scales the hazards of all event types
        without risk factors of their own."""
        mult = multipliers(patient, latent, self.params)
        if general_factor != 1.0:
            mult = {t: m if t in OWN_FACTORS else m * general_factor for t, m in mult.items()}
        rows = [(t, h * mult[t], w) for t, h, w in self.rows[patient["regimen"]]]
        return rows, mult


def general_multiplier(patient, latent, params):
    """Patient-related factor that applies to all event types except lung
    toxicity and cardiovascular events: frailty, age and bilirubin."""
    g = params["hazards"]["general"]
    value = math.exp(g["frailty_log_hazard_ratio"] * latent["frailty"])
    value *= g["hazard_ratio_per_10_years_of_age"] ** ((patient["age_years"] - g["reference_age"]) / 10)
    if patient["bilirubin_ratio_uln"] > 1.5:
        value *= g["hazard_ratio_bilirubin_above_1_5"]
    return value
