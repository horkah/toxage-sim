"""Baseline characteristics of synthetic patients.

Each patient has a latent frailty that is not part of the data. It drives
several observed characteristics and, later, the toxicity and survival
hazards. This links the observed data to the outcomes without a direct
causal effect of every single variable.
"""
import math

TUMOURS = ("pancreas", "prostate", "breast")


def _clip(value, low, high):
    """The value limited to [low, high]."""
    return max(low, min(high, value))


def _sigmoid(x):
    """Logistic function: maps a log-odds value to a probability."""
    return 1 / (1 + math.exp(-x))


def _choice(rng, probabilities):
    """One key of a {key: probability} mapping, drawn with these weights."""
    keys = list(probabilities)
    return rng.choices(keys, weights=[probabilities[k] for k in keys])[0]


def _lognormal(rng, median, sigma):
    """A draw from a log-normal distribution with the given median."""
    return rng.lognormvariate(math.log(median), sigma)


def _regimen(rng, subgroup, frailty, age, bilirubin, lung_problem, params):
    """The regimen of a patient: chosen by subgroup, frailty, age, bilirubin and lung
    problems as in the parameters."""
    c = params["treatment_choice"]
    if subgroup == "pancreas_metastatic":
        m = c["pancreas_nalirifox"]
        x = m["intercept"] + m["frailty_slope"] * frailty + m["per_year_above_65"] * (age - 65)
        if bilirubin > 1.5:
            x += m["bilirubin_above_1_5_shift"]
        return "nalirifox" if rng.random() < _sigmoid(x) else "gemcitabine_nab_paclitaxel"
    if subgroup == "breast_her2_low":
        m = c["breast_her2_low_trastuzumab_deruxtecan"]
        p = m["probability_with_lung_problem"] if lung_problem else m["probability"]
        return "trastuzumab_deruxtecan" if rng.random() < p else "chemotherapy_single_agent"
    if subgroup == "breast_triple_negative":
        return "pembrolizumab_chemotherapy"
    return _choice(rng, c[subgroup])


def _cardiovascular(rng, tumour, age, diabetes, cvd, params):
    """Cardiovascular history and risk factors, and the type of androgen
    deprivation for patients with prostate cancer."""
    p = params["population"]
    prior = cvd and rng.random() < p["prior_cardiovascular_event"]["probability_with_cardiovascular_disease"]
    h = p["arterial_hypertension"]
    hypertension = rng.random() < _sigmoid(
        h["intercept"] + h["per_year_above_65"] * (age - 65) + h["diabetes_shift"] * diabetes
        + h["cardiovascular_disease_shift"] * cvd
    )
    b = p["systolic_bp_mmhg"]
    pressure = b["mean"] + b["hypertension_shift"] * hypertension + b["per_year_above_65"] * (age - 65) + rng.gauss(0, b["sd"])
    smoking = _choice(rng, p["smoking_status"].get(tumour, p["smoking_status"]["default"]))
    adt = None
    if tumour == "prostate":
        a = params["treatment_choice"]["adt_antagonist"]
        chance = a["probability_with_prior_cardiovascular_event"] if prior else a["probability"]
        adt = "gnrh_antagonist" if rng.random() < chance else "gnrh_agonist"
    return {
        "adt_type": adt,
        "prior_cardiovascular_event": prior,
        "arterial_hypertension": hypertension,
        "systolic_bp_mmhg": round(_clip(pressure, b["minimum"], b["maximum"])),
        "smoking_status": smoking,
    }


def draw_patient(rng, index, tumour, regimens, params):
    """Return (baseline record, latent values) of one patient."""
    p = params["population"]
    subgroup = _choice(rng, p["subgroup_shares"][tumour])

    age_p = p["age"]
    age = round(rng.gauss(age_p[subgroup]["mean"], age_p[subgroup]["sd"]))
    age = _clip(age, age_p["minimum"], age_p["maximum"])
    if tumour == "prostate":
        sex = "male"
    elif tumour == "breast":
        sex = "female"
    else:
        sex = "male" if rng.random() < p["share_male_pancreas"] else "female"

    fr = p["frailty"]
    frailty = rng.gauss(0, 1) + fr["age_weight_per_10_years"] * (age - 65) / 10 + fr["shift"][tumour]

    low, high = p["ecog_thresholds"]
    score = frailty + rng.gauss(0, 0.7)
    ecog = 0 if score < low else 1 if score < high else 2

    ga_p = p["ga"]
    if age >= ga_p["assessed_from_age"]:
        prob = _sigmoid(ga_p["intercept"] + ga_p["frailty_slope"] * frailty)
        ga = sum(rng.random() < prob for _ in range(7))
    else:
        ga = None

    is_pancreas = tumour == "pancreas"
    a = p["albumin_g_l"]
    albumin = a["mean"] + a["frailty_slope"] * frailty + a["pancreas_shift"] * is_pancreas + rng.gauss(0, a["sd"])
    b = p["bmi"]
    bmi = b["mean"] + b["frailty_slope"] * frailty + b["pancreas_shift"] * is_pancreas + rng.gauss(0, b["sd"])

    d = p["diabetes"]
    diabetes = rng.random() < _sigmoid(
        d["intercept"] + d["per_year_above_65"] * (age - 65) + d["pancreas_shift"] * is_pancreas
    )
    cv = p["cardiovascular_disease"]
    cvd = rng.random() < _sigmoid(
        cv["intercept"] + cv["per_year_above_65"] * (age - 65) + cv["male_shift"] * (sex == "male")
    )
    lung = rng.random() < p["lung_comorbidity_probability"]["value"]

    e = p["egfr_ml_min"]
    egfr = e["mean_at_40"] - e["decline_per_year"] * (age - 40) + e["diabetes_shift"] * diabetes + rng.gauss(0, e["sd"])
    egfr = round(_clip(egfr, e["minimum"], e["maximum"]))
    if egfr >= e["categories"]["normal_from"]:
        renal = "normal"
    elif egfr >= e["categories"]["mild_decrease_from"]:
        renal = "mild_decrease"
    else:
        renal = "moderate_severe_decrease"

    bl = p["bilirubin_ratio_uln"]
    if is_pancreas and rng.random() < bl["pancreas_obstruction_probability"]:
        bilirubin = _lognormal(rng, bl["obstruction_median"], bl["obstruction_sigma"])
    else:
        bilirubin = _lognormal(rng, bl["median"], bl["sigma"])

    s = p["spo2"]
    spo2 = s["mean"] + s["lung_comorbidity_shift"] * lung + s["frailty_slope"] * frailty + rng.gauss(0, s["sd"])
    spo2 = round(_clip(spo2, s["minimum"], 100))

    lines = rng.choice(p["prior_therapy_lines"][subgroup])
    pretreated = lines >= p["pretreated_from_lines"]
    n = p["neutrophils_10e9_l"]
    neutrophils = max(n["minimum"], _lognormal(rng, n["median"], n["sigma"]) * (n["pretreated_factor"] if pretreated else 1))
    h = p["haemoglobin_g_dl"]
    hb = (
        (h["mean_male"] if sex == "male" else h["mean_female"])
        + h["frailty_slope"] * frailty
        + h["pretreated_shift"] * pretreated
        + h["renal_impairment_shift"] * (renal == "moderate_severe_decrease")
        + rng.gauss(0, h["sd"])
    )
    pl = p["platelets_10e9_l"]
    platelets = max(pl["minimum"], _lognormal(rng, pl["median"], pl["sigma"]) * (pl["pretreated_factor"] if pretreated else 1))

    ysd = p["years_since_diagnosis"][subgroup]
    years_since_diagnosis = round(_lognormal(rng, ysd["median"], ysd["sigma"]), 1)
    regimen = _regimen(rng, subgroup, frailty, age, bilirubin, lung or spo2 < 95, params)

    sd = params["treatment_choice"]["starting_dose_reduction"]
    reduced = rng.random() < _sigmoid(
        sd["intercept"] + sd["frailty_slope"] * frailty + sd["per_year_above_70"] * (age - 70)
    )
    gcsf = (
        regimens[regimen]["chemotherapy_weeks"] is not None
        and rng.random() < params["treatment_choice"]["gcsf_probability_with_docetaxel"]
    )

    baseline = {
        "patient_id": f"P{index:06d}",
        "tumour_type": tumour,
        "subgroup": subgroup,
        "regimen": regimen,
        "prior_therapy_lines": lines,
        "starting_dose_level": sd["reduced_level"] if reduced else 1.0,
        "gcsf_prophylaxis": gcsf,
        "age_years": age,
        "sex": sex,
        "ecog": ecog,
        "ga_impaired_domains": ga,
        "bmi": round(_clip(bmi, b["minimum"], b["maximum"]), 1),
        "albumin_g_l": round(_clip(albumin, a["minimum"], a["maximum"]), 1),
        "egfr_ml_min": egfr,
        "renal_function": renal,
        "bilirubin_ratio_uln": round(bilirubin, 2),
        "neutrophils_10e9_l": round(neutrophils, 2),
        "haemoglobin_g_dl": round(_clip(hb, h["minimum"], h["maximum"]), 1),
        "platelets_10e9_l": round(platelets),
        "spo2_percent": spo2,
        "lung_comorbidity": lung,
        "diabetes": diabetes,
        "cardiovascular_disease": cvd,
        "years_since_diagnosis": years_since_diagnosis,
    }
    baseline.update(_cardiovascular(rng, tumour, age, diabetes, cvd, params))
    return baseline, {"frailty": frailty}


def draw_cohort(rng, n, regimens, params):
    """Return n patients, split equally over the three tumour types."""
    patients = []
    for i in range(n):
        patients.append(draw_patient(rng, i + 1, TUMOURS[i % 3], regimens, params))
    return patients
