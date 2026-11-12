"""Course of one patient over time in weekly steps.

Each week the patient can have an adverse event, a change of the therapy,
the end of the therapy or death. Events change the therapy, and the therapy
changes the hazard of later events.
"""
import math

from hazards import ILD


def _draw(rng, probabilities):
    keys = [k for k in probabilities if k != "basis"]
    return rng.choices(keys, weights=[probabilities[k] for k in keys])[0]


def simulate(rng, patient, latent, regimen, params, hazard_rows):
    """Return the course of one patient as a dictionary."""
    weeks = params["simulation"]["weeks"]
    hz = params["hazards"]
    act = params["actions"]
    levels = act["dose_levels"]
    gamma = hz["dose_exponent"]["value"]
    smoothing = params["measurements"]["exposure_smoothing"]

    dose = patient["starting_dose_level"]
    stopped, end_day, end_reason = False, None, "ongoing"
    interrupted_until = 0
    exposure = 0.0
    death_day = None
    events, states = [], []
    ild = None  # {"onset_day", "diagnosis_day", "grade", "recognised"}
    last_day = 0  # day of the latest recorded event, so that later ones do not precede it

    p_stop = 1 - 0.5 ** (1 / regimen["median_treatment_weeks"])
    sv = params["survival"]
    h_death = math.log(2) / (regimen["median_survival_months"] * 4.345)
    h_death *= math.exp(sv["frailty_log_hazard_ratio"] * latent["frailty"])
    if patient["ecog"] >= 2:
        h_death *= sv["hazard_ratio_ecog_2"]
    p_death = 1 - math.exp(-h_death)

    def stop(day, reason):
        nonlocal stopped, end_day, end_reason
        if not stopped:
            stopped, end_day, end_reason = True, day, reason

    def apply(action, week, day):
        nonlocal dose, interrupted_until
        if stopped:
            return "none"
        if action == "dose_reduction":
            lower = [x for x in levels if x < dose - 1e-9]
            if lower:
                dose = lower[0]
            else:
                action = "discontinuation"
        if action == "interruption":
            low, high = act["interruption_weeks"]
            interrupted_until = week + 1 + rng.randint(low, high)
        if action == "discontinuation":
            stop(day, "toxicity")
        return action

    for week in range(weeks):
        first_day = 7 * week + 1

        if ild and not ild["recognised"] and ild["diagnosis_day"] <= first_day + 6:
            ild["recognised"] = True
            day = last_day = max(ild["diagnosis_day"], last_day, first_day)
            ild["diagnosis_day"] = day
            wanted = act["ild"]["grade_1"] if ild["grade"] == 1 else act["ild"]["grade_2_or_higher"]
            action = apply(wanted, week, day)
            events.append({"patient_id": patient["patient_id"], "event_type": ILD, "grade": ild["grade"],
                           "onset_day": ild["onset_day"], "day": day, "action": action})
            if ild["grade"] == 5:
                death_day = day
                stop(day, "toxicity")

        status = "stopped" if stopped else "interrupted" if week < interrupted_until else "on_treatment"
        week_dose = dose

        if status == "on_treatment" and death_day is None:
            effect = dose ** gamma
            total, parts = 0.0, []
            for event_type, coefficient, weights in hazard_rows:
                if event_type == ILD and ild:
                    continue
                h = coefficient * weights[week] * effect
                if h > 0:
                    total += h
                    parts.append((event_type, h))
            if total > 0 and rng.random() < 1 - math.exp(-total):
                event_type = rng.choices([t for t, _ in parts], weights=[h for _, h in parts])[0]
                day = max(first_day + rng.randrange(7), last_day)
                if event_type == ILD:
                    grade = int(_draw(rng, hz["ild"]["grade_probabilities"]))
                    d = hz["ild"]["recognition_delay"]
                    if rng.random() < d["probability_delayed"]:
                        delay = round(rng.lognormvariate(math.log(d["median_days"]), d["sigma"]))
                    else:
                        delay = rng.randint(0, d["maximum_days_if_prompt"])
                    ild = {"onset_day": day, "diagnosis_day": day + delay, "grade": grade, "recognised": False}
                else:
                    grades = hz["grade_probabilities"].get(event_type, hz["grade_probabilities"]["default"])
                    grade = int(_draw(rng, grades))
                    wanted = _draw(rng, act["probabilities"].get(event_type, act["probabilities"]["default"]))
                    action = "none" if grade == 5 else apply(wanted, week, day)
                    last_day = day
                    events.append({"patient_id": patient["patient_id"], "event_type": event_type, "grade": grade,
                                   "onset_day": day, "day": day, "action": action})
                    if grade == 5:
                        death_day = day
                        stop(day, "toxicity")

        exposure = (1 - smoothing) * exposure + smoothing * (week_dose if status == "on_treatment" else 0.0)
        states.append((status, None if status == "stopped" else week_dose, exposure))

        if death_day is None and rng.random() < p_death:
            death_day = max(first_day + rng.randrange(7), last_day)
            stop(death_day, "death")
        if death_day is not None:
            break
        if not stopped:
            maximum = regimen["max_treatment_weeks"]
            if maximum is not None and week + 1 >= maximum:
                stop(first_day + 6, "completed")
            elif rng.random() < p_stop:
                stop(first_day + 6, "progression")

    if ild and not ild["recognised"]:
        ild["diagnosis_day"] = None
    follow_up = death_day if death_day is not None else 7 * weeks
    return {"states": states, "events": events, "ild": ild, "end_day": end_day, "end_reason": end_reason,
            "death_day": death_day, "follow_up_days": follow_up}


def outcome(patient, course):
    """Return the outcome record of one patient."""
    severe = [e["day"] for e in course["events"] if e["grade"] >= 3 and e["day"] <= 90]
    ild = course["ild"]
    return {
        "patient_id": patient["patient_id"],
        "follow_up_days": course["follow_up_days"],
        "severe_toxicity_90d": bool(severe),
        "severe_toxicity_day": min(severe) if severe else None,
        "ild": ild is not None,
        "ild_onset_day": ild["onset_day"] if ild else None,
        "ild_diagnosis_day": ild["diagnosis_day"] if ild else None,
        "ild_grade": ild["grade"] if ild else None,
        "treatment_end_day": course["end_day"],
        "treatment_end_reason": course["end_reason"],
        "death_day": course["death_day"],
    }
