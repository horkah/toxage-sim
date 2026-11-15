"""Weekly observations: therapy status, blood tests, oxygen saturation and
patient-reported symptoms. They are derived from the course of the patient,
so that they carry signals of the events.

The noise of a week comes from a generator that is seeded by patient and
week, so it is the same in every scenario."""
import math
import random

from hazards import CV
from population import clip

LAB_EVENTS = ("neutropenia", "febrile_neutropenia", "anaemia", "thrombocytopenia")
# Rates of severe events that drive the drift of the weekly values (blood
# counts, diarrhoea) for regimens without a published rate of that event: a
# small effect, so that the values still move a little under therapy.
FALLBACK_RATES = {"neutropenia": 0.05, "anaemia": 0.03, "thrombocytopenia": 0.02, "diarrhoea": 0.02}


def _ild_effect(day, ild, rise_per_week, maximum, recovery_per_week):
    """Size of the lung effect on a day: grows from onset, falls after diagnosis."""
    if not ild or day < ild["onset_day"]:
        return 0.0
    peak_day = ild["diagnosis_day"] if ild["diagnosis_day"] is not None else day
    effect = min(maximum, rise_per_week * (min(day, peak_day) - ild["onset_day"] + 7) / 7)
    if day > peak_day and ild["grade"] <= 3:
        effect = max(0.0, effect - recovery_per_week * (day - peak_day) / 7)
    return effect


def _warning_effect(day, cv, rise_per_week, maximum, recovery_per_week):
    """Size of the effect of a cardiovascular warning phase on a day: grows
    from its start until the event is recognised and treated, then falls.
    Events without a warning phase have no effect in advance."""
    if not cv or day < cv["onset_day"]:
        return 0.0
    peak_day = cv["diagnosis_day"] if cv["diagnosis_day"] is not None else day
    if peak_day <= cv["onset_day"]:
        return 0.0
    effect = min(maximum, rise_per_week * (min(day, peak_day) - cv["onset_day"] + 7) / 7)
    if day > peak_day:
        effect = max(0.0, effect - recovery_per_week * (day - peak_day) / 7)
    return effect


def home_values(draws, patient, latent, params, week, ild):
    """Oxygen saturation, cough and breathlessness of one week as the patient
    measures and reports them at home, None where a value is missing. ild is
    the lung toxicity of the patient as far as it has developed, or None.

    The course calls this week by week, so that a detection model can read the
    same values that the observation table holds."""
    m = params["measurements"]
    s_p, y_p = m["spo2"], m["symptoms"]
    day = 7 * week + 1
    spo2 = None
    if week == 0 or draws.u("spo2_missing", week) >= s_p["missing"]:
        maximum = s_p["ild_maximum_drop"][str(ild["grade"])] if ild else 0.0
        drop = _ild_effect(day + 6, ild, s_p["ild_drop_per_week"], maximum, s_p["recovery_per_week"])
        base = patient["spo2_percent"]
        if week > 0:
            base += s_p["noise_sd"] * draws.normal("spo2_noise", week)
        spo2 = round(clip(base - drop, 50, 100))
    cough = dyspnoea = None
    reported = draws.u("symptoms_missing", week) >= y_p["missing"]
    if reported:
        level = lambda x, name: round(clip(x + y_p["noise_sd"] * draws.normal(name, week), 0, 4))
        c = y_p["cough"]
        maximum = c["ild_maximum"][str(ild["grade"])] if ild else 0.0
        lung = _ild_effect(day + 6, ild, c["ild_rise_per_week"], maximum, s_p["recovery_per_week"])
        cough = level(c["base"] + c["lung_comorbidity_shift"] * patient["lung_comorbidity"] + lung, "cough_noise")
        b = y_p["dyspnoea"]
        dyspnoea = level(b["base"] + b["lung_comorbidity_shift"] * patient["lung_comorbidity"]
                         + b["frailty_slope"] * max(0.0, latent["frailty"]) + lung, "dyspnoea_noise")
    return {"spo2_percent": spo2, "pro_cough": cough, "pro_dyspnoea": dyspnoea, "reported": reported}


def observations(draws, latent, regimen, params, course, mult):
    """Return the observation records of one patient in one scenario."""
    plan = course["plan"]
    patient = plan["patient"]
    m = params["measurements"]
    rates = regimen["severe_event_rates"]
    frailty = latent["frailty"]
    ild, cv = course["ild"], course["cv"]
    by_week = {}
    for e in course["events"]:
        by_week.setdefault((e["day"] - 1) // 7, []).append(e)
    stop_week = None if course["end_day"] is None else (course["end_day"] - 1) // 7

    sens_n = math.sqrt(mult["neutropenia"])
    sens_a = math.sqrt(mult["anaemia"])
    sens_t = math.sqrt(mult["thrombocytopenia"])
    n_p, h_p, t_p = m["neutrophils"], m["haemoglobin"], m["platelets"]
    s_p, y_p, b_p = m["spo2"], m["symptoms"], m["blood_pressure"]

    records = []
    for week, (status, dose, exposure) in enumerate(course["states"]):
        day = 7 * week + 1
        rng = random.Random(draws.key("observation", week))
        here = by_week.get(week, [])
        types = {e["event_type"]: e for e in here if e["grade"] >= 3}

        scheduled = week % regimen["lab_interval_weeks"] == 0 and (
            stop_week is None or week <= stop_week + m["labs_weeks_after_stop"]
        )
        neutrophils = haemoglobin = platelets = None
        if scheduled or any(t in types for t in LAB_EVENTS):
            drop = n_p["drop_per_event_rate"] * rates.get("neutropenia", FALLBACK_RATES["neutropenia"]) * sens_n
            neutrophils = patient["neutrophils_10e9_l"] * math.exp(-drop * exposure) * rng.lognormvariate(0, n_p["noise_sigma"])
            event = types.get("neutropenia") or types.get("febrile_neutropenia")
            if event:
                neutrophils = rng.uniform(*n_p["grade_4" if event["grade"] >= 4 else "grade_3"])
            drop = min(h_p["maximum_drop"], h_p["drop_g_dl_per_event_rate"] * rates.get("anaemia", FALLBACK_RATES["anaemia"]) * sens_a)
            haemoglobin = patient["haemoglobin_g_dl"] - drop * exposure + rng.gauss(0, h_p["noise_sd"])
            if "anaemia" in types:
                haemoglobin = rng.uniform(*h_p["event_range"])
            drop = min(t_p["maximum_drop"], t_p["drop_per_event_rate"] * rates.get("thrombocytopenia", FALLBACK_RATES["thrombocytopenia"]) * sens_t)
            platelets = patient["platelets_10e9_l"] * (1 - drop * exposure) * rng.lognormvariate(0, t_p["noise_sigma"])
            event = types.get("thrombocytopenia")
            if event:
                platelets = rng.uniform(*t_p["grade_4" if event["grade"] >= 4 else "grade_3"])
            neutrophils = round(max(0.0, neutrophils), 2)
            haemoglobin = round(max(3.0, haemoglobin), 1)
            platelets = round(max(1.0, platelets))

        home = course["home"][week]
        spo2 = home["spo2_percent"]

        fatigue = diarrhoea = chest_pain = None
        cough, dyspnoea = home["pro_cough"], home["pro_dyspnoea"]
        reported = home["reported"]
        if reported:
            noise = lambda: rng.gauss(0, y_p["noise_sd"])
            level = lambda x: round(clip(x + noise(), 0, 4))
            f = y_p["fatigue"]
            recent = here or by_week.get(week - 1, [])
            severe = any(e["grade"] >= 3 for e in recent)
            fatigue = level(f["base"] + f["frailty_slope"] * frailty + f["exposure_slope"] * exposure
                            + f["severe_event_bump"] * severe)
            d = y_p["diarrhoea"]
            value = d["base"] + d["exposure_slope_per_event_rate"] * rates.get("diarrhoea", FALLBACK_RATES["diarrhoea"]) * exposure
            if "diarrhoea" in types:
                value = d["event_level"]
            elif any(e["event_type"] == "diarrhoea" for e in by_week.get(week + 1, [])):
                value += d["week_before_event_bump"]
            diarrhoea = level(value)

        # Drawn after all other values of the week, so that those stay as they are.
        pressure = None
        if week == 0 or rng.random() >= b_p["missing"]:
            pressure = patient["systolic_bp_mmhg"]
            if week > 0:
                pressure += rng.gauss(0, b_p["noise_sd"])
            pressure += b_p["rise_per_hypertension_rate"] * rates.get("hypertension", 0.0) * exposure
            pressure += _warning_effect(day + 6, cv, b_p["warning_rise_per_week"], b_p["warning_maximum"],
                                        b_p["recovery_per_week"])
            if "hypertension" in types:
                pressure = rng.uniform(*b_p["hypertension_event_range"])
            pressure = round(clip(pressure, 60, 260))
        if reported:
            c = y_p["chest_pain"]
            value = c["base"] + c["cardiovascular_disease_shift"] * patient["cardiovascular_disease"]
            value += _warning_effect(day + 6, cv, c["warning_rise_per_week"], c["warning_maximum"],
                                     c["recovery_per_week"])
            if CV in types:
                value = max(value, c["event_level"])
            chest_pain = round(clip(value + rng.gauss(0, y_p["noise_sd"]), 0, 4))

        records.append({
            "scenario_id": plan["scenario_id"], "patient_id": patient["patient_id"], "week": week, "day": day,
            "treatment_status": status, "dose_level": dose,
            "neutrophils_10e9_l": neutrophils, "haemoglobin_g_dl": haemoglobin, "platelets_10e9_l": platelets,
            "spo2_percent": spo2, "systolic_bp_mmhg": pressure, "pro_fatigue": fatigue, "pro_diarrhoea": diarrhoea,
            "pro_cough": cough, "pro_dyspnoea": dyspnoea, "pro_chest_pain": chest_pain,
        })
    return records
