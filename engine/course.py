"""Course of one patient over time in weekly steps, under one scenario.

Each week the patient can have a new adverse event, a change of the therapy,
the end of the therapy or death. An adverse event starts mild and worsens
until it is recognised. Usual care recognises it at a fixed later day;
monitoring can recognise it earlier, at a lower grade.

All random decisions use the fixed numbers of draws.py, keyed by purpose and
week. Two scenarios therefore give the same course for a patient until an
intervention changes something.
"""
import math

from hazards import CV, ILD, OWN_FACTORS
import interventions


def _stage(episode, day):
    """Grade that an unrecognised event has reached on a day."""
    grade = episode["grade"]
    span = episode["routine_day"] - episode["onset_day"]
    if grade <= 1 or span <= 0 or day >= episode["routine_day"]:
        return grade
    return min(grade, 1 + int((grade - 1) * (day - episode["onset_day"]) / span))


def simulate(draws, latent, regimen, params, iv, plan, hazard_rows, weeks=None):
    """Return the course of one patient as a dictionary.

    plan comes from interventions.plan() and holds the patient record as the
    scenario adapts it. hazard_rows come from HazardTable.for_patient().
    """
    patient = plan["patient"]
    pid = patient["patient_id"]
    weeks = params["simulation"]["weeks"] if weeks is None else weeks
    hz, act, sim = params["hazards"], params["actions"], params["simulation"]
    levels = act["dose_levels"]
    gamma = hz["dose_exponent"]["value"]
    smoothing = params["measurements"]["exposure_smoothing"]
    part, cons = iv["participation"], iv["consequences"]
    perfect = plan["perfect"]
    sources = plan["sources"]
    after_stop = part["monitoring_weeks_after_stop"]
    obs_after_stop = sim["observation_weeks_after_stop"]

    dose = patient["starting_dose_level"]
    stopped, end_day, end_reason, stop_week = False, None, "ongoing", None
    interrupted_until = 0
    exposure = 0.0
    death_day, toxic_death = None, False
    lost = dropped = False
    events, alerts, states, pending = [], [], [], []
    ild = cv = None
    last_day = 0
    report_weeks = {s: 0 for s in sources}
    report_weekday = int(draws.u("report_weekday") * 7)

    stop_base = 1 - 0.5 ** (1 / regimen["median_treatment_weeks"])
    dose_step_ratio = iv["efficacy"]["progression_hazard_ratio_per_dose_step"]
    sv = params["survival"]
    h_death = math.log(2) / (regimen["median_survival_months"] * 4.345)
    h_death *= math.exp(sv["frailty_log_hazard_ratio"] * latent["frailty"])
    if patient["ecog"] >= 2:
        h_death *= sv["hazard_ratio_ecog_2"]
    p_death = 1 - math.exp(-h_death)

    def stop(day, reason, week):
        """End the therapy on a day for a reason, once; later calls keep the first
        end."""
        nonlocal stopped, end_day, end_reason, stop_week
        if not stopped:
            stopped, end_day, end_reason, stop_week = True, day, reason, week

    def apply(action, week, day):
        """Carry out an action on the dose after an event and return what was
        actually done: a dose reduction below the lowest level becomes a
        discontinuation."""
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
            interrupted_until = week + 1 + low + int(draws.u("interruption", week) * (high - low + 1))
        if action == "discontinuation":
            stop(day, "toxicity", week)
        return action

    def recognise(episode, day, by, week, first_day):
        """Record an event: its grade, what is done, and what it costs."""
        nonlocal death_day, toxic_death, last_day
        kind, key = episode["event_type"], episode["week"]
        day = last_day = max(day, last_day, first_day)
        grade = episode["grade"]
        if by == "monitoring":
            halt = iv["early_treatment"]["halt_probability"]
            if perfect or draws.u(f"halt:{kind}", key) < halt.get(kind, halt["default"]):
                grade = episode["stage"]
        if grade == 5:
            action = "none"
        elif kind == ILD:
            action = apply(act["ild"]["grade_1"] if grade == 1 else act["ild"]["grade_2_or_higher"], week, day)
        elif grade >= 3:
            wanted = draws.pick(f"action:{kind}", act["probabilities"].get(kind, act["probabilities"]["default"]), key)
            action = apply(wanted, week, day)
        else:
            action = apply(draws.pick(f"early_action:{kind}", iv["early_treatment"]["actions_below_grade_3"], key), week, day)

        hospital = cons["hospital_probability"].get(kind, cons["hospital_probability"]["default"])
        in_hospital = draws.u(f"hospital:{kind}", key) < hospital[str(grade)]
        hospital_days = icu_days = 0
        if in_hospital:
            hospital_days = max(1, round(cons["hospital_days_mean"][str(grade)] * (0.5 + draws.u(f"stay:{kind}", key))))
            icu = cons["intensive_care"].get(str(grade))
            if icu and draws.u(f"icu:{kind}", key) < icu["probability"]:
                icu_days = icu["days"]
        events.append({
            "scenario_id": plan["scenario_id"], "patient_id": pid, "event_type": kind, "grade": grade,
            "onset_day": episode["onset_day"], "day": day, "detected_by": by,
            "usual_care_day": episode["routine_day"], "usual_care_grade": episode["grade"],
            "action": action, "hospital_days": hospital_days, "icu_days": icu_days,
            "unplanned_visit": grade >= 2 and not in_hospital,
        })
        if kind == ILD:
            ild.update(diagnosis_day=day, grade=grade, recognised=True)
        if kind == CV:
            cv.update(diagnosis_day=day, grade=grade, recognised=True)
        if grade == 5:
            death_day, toxic_death = day, True
            stop(day, "toxicity", week)

    for week in range(weeks):
        first_day = 7 * week + 1

        # After the end of therapy and of the observation period only death remains.
        if stopped and not pending and week > stop_week + max(after_stop, obs_after_stop):
            if draws.u("death", week) < p_death:
                death_day = first_day + int(draws.u("death_day", week) * 7)
                break
            continue

        # 1. Monitoring: reports of this week, alerts, early recognition.
        monitored = bool(sources) and not lost and not dropped and (
            not stopped or week <= stop_week + after_stop)
        if monitored and not perfect:
            rate = part["dropout_per_week"]["first_8_weeks" if week < 8 else "later"]
            if draws.u("dropout", week) < rate:
                dropped = monitored = False
        if monitored and (perfect or draws.u("adherence", week) < plan["adherence"]):
            report_day = first_day + report_weekday
            for source in sources:
                report_weeks[source] += 1
                alerted = False
                for episode in list(pending):
                    if not episode["onset_day"] <= report_day < episode["routine_day"]:
                        continue
                    stage = _stage(episode, report_day)
                    chance = interventions.sensitivity(source, episode["event_type"], stage, iv, perfect)
                    if draws.u(f"detect:{source}:{episode['event_type']}", week) >= chance:
                        continue
                    alerted = True
                    attended = draws.u("attend", week) < plan["attendance"]
                    acted = attended and draws.u("act", week) < plan["action"]
                    alerts.append({"scenario_id": plan["scenario_id"], "patient_id": pid, "day": report_day,
                                   "source": source, "true_alert": True, "event_type": episode["event_type"],
                                   "attended": attended, "acted": acted})
                    if acted:
                        episode["stage"] = stage
                        pending.remove(episode)
                        recognise(episode, report_day + 1, "monitoring", week, first_day)
                if not alerted and not perfect and (
                        draws.u(f"false:{source}", week) < iv["detection"][source]["false_alerts_per_report"]):
                    alerts.append({"scenario_id": plan["scenario_id"], "patient_id": pid, "day": report_day,
                                   "source": source, "true_alert": False, "event_type": None,
                                   "attended": draws.u("attend", week) < plan["attendance"], "acted": False})

        # 2. Usual care recognises events that have reached their day.
        for episode in sorted(pending, key=lambda e: e["routine_day"]):
            if episode["routine_day"] <= first_day + 6 and death_day is None:
                pending.remove(episode)
                if not lost or episode["grade"] >= 4:
                    recognise(episode, episode["routine_day"], "routine", week, first_day)

        status = "stopped" if stopped else "interrupted" if week < interrupted_until else "on_treatment"
        week_dose = dose

        # 3. New events start.
        if status == "on_treatment" and death_day is None:
            effect = dose ** gamma
            for kind, coefficient, weights in hazard_rows:
                h = coefficient * weights[week] * (1.0 if kind == CV else effect)
                if h <= 0 or (kind == ILD and ild) or (kind == CV and cv) or (
                        any(e["event_type"] == kind for e in pending)):
                    continue
                if draws.u(f"start:{kind}", week) >= 1 - math.exp(-h):
                    continue
                onset = first_day + int(draws.u(f"day:{kind}", week) * 7)
                if kind == ILD:
                    grade = int(draws.pick("grade:ild", hz["ild"]["grade_probabilities"], week))
                    d = hz["ild"]["recognition_delay"]
                    if draws.u("ild_delayed", week) < d["probability_delayed"]:
                        delay = round(math.exp(math.log(d["median_days"]) + d["sigma"] * draws.normal("ild_delay", week)))
                    else:
                        delay = int(draws.u("ild_delay", week) * (d["maximum_days_if_prompt"] + 1))
                    ild = {"onset_day": onset, "diagnosis_day": None, "grade": grade, "recognised": False}
                elif kind == CV:
                    grade = int(draws.pick("grade:cv", hz["grade_probabilities"][CV], week))
                    w = hz["cardiovascular"]["warning_phase"]
                    delay = 0
                    if draws.u("cv_warned", week) < w["probability"]:
                        delay = max(1, round(math.exp(
                            math.log(w["median_days"]) + w["sigma"] * draws.normal("cv_warning", week))))
                    cv = {"onset_day": onset, "diagnosis_day": None, "grade": grade, "recognised": False}
                else:
                    grades = hz["grade_probabilities"].get(kind, hz["grade_probabilities"]["default"])
                    grade = int(draws.pick(f"grade:{kind}", grades, week))
                    delay = (grade - 1) * iv["natural_course"]["stage_days"][kind]
                episode = {"event_type": kind, "grade": grade, "onset_day": onset,
                           "routine_day": onset + delay, "week": week, "stage": 1}
                seen_by = [s for s in sources if interventions.sensitivity(s, kind, 1, iv, True) > 0]
                # An event without a warning phase cannot be seen in advance.
                sudden = kind == CV and delay == 0
                if perfect and seen_by and not sudden:
                    alerts.append({"scenario_id": plan["scenario_id"], "patient_id": pid, "day": onset,
                                   "source": seen_by[0], "true_alert": True, "event_type": kind,
                                   "attended": True, "acted": True})
                    recognise(episode, onset + 1, "monitoring", week, first_day)
                elif delay == 0:
                    recognise(episode, onset, "routine", week, first_day)
                else:
                    pending.append(episode)

        exposure = (1 - smoothing) * exposure + smoothing * (week_dose if status == "on_treatment" else 0.0)
        if not stopped or stop_week is None or week <= stop_week + obs_after_stop:
            states.append((status, None if status == "stopped" else week_dose, exposure))

        # 4. Death, loss to follow-up, end of therapy.
        if death_day is None and draws.u("death", week) < p_death:
            # A random day of the week, but not before the last recognised event.
            death_day = max(first_day + int(draws.u("death_day", week) * 7), last_day)
            stop(death_day, "death", week)
        if death_day is not None:
            break
        if not stopped:
            maximum = regimen["max_treatment_weeks"]
            p_stop = stop_base * dose_step_ratio ** levels.index(dose) if dose in levels else stop_base
            if draws.u("lost", week) < iv["loss_to_follow_up"]["per_week_on_therapy"]:
                lost = True
                stop(first_day + 6, "lost_to_follow_up", week)
            elif maximum is not None and week + 1 >= maximum:
                stop(first_day + 6, "completed", week)
            elif draws.u("stop", week) < p_stop:
                stop(first_day + 6, "progression", week)

    follow_up = death_day if death_day is not None else 7 * weeks
    return {"states": states, "events": events, "alerts": alerts, "ild": ild, "cv": cv, "end_day": end_day,
            "end_reason": end_reason, "death_day": death_day, "toxic_death": toxic_death,
            "follow_up_days": follow_up, "report_weeks": report_weeks, "plan": plan}


def outcome(latent, course, iv):
    """Return the outcome record of one patient in one scenario."""
    plan = course["plan"]
    patient = plan["patient"]
    events, alerts = course["events"], course["alerts"]
    follow_up = course["follow_up_days"]
    severe = [e["day"] for e in events if e["grade"] >= 3 and e["day"] <= 90]
    ild, cv = course["ild"], course["cv"]
    major = bool(cv and cv["recognised"] and cv["grade"] >= 3)

    costs, cons = iv["costs"], iv["consequences"]
    hospital_days = sum(e["hospital_days"] for e in events)
    icu_days = sum(e["icu_days"] for e in events)
    visits = sum(e["unplanned_visit"] for e in events)
    cost_care = (visits * costs["unplanned_visit"] + hospital_days * costs["hospital_day"]
                 + icu_days * costs["intensive_care_day"])
    cost_intervention = 0.0
    if plan["risk_assessed"]:
        cost_intervention += costs["risk_assessment_per_patient"]
    if plan["participating"]:
        cost_intervention += costs["set_up_per_participant"]
    for source, n in course["report_weeks"].items():
        cost_intervention += n * costs["monitoring_per_week"][source]
    for a in alerts:
        cost_intervention += costs["alert_handling"]
        if a["attended"]:
            cost_care += costs["diagnostics_after_alert"][a["source"]]

    q = iv["quality_of_life"]
    base = min(0.95, max(q["minimum"], q["base"][patient["tumour_type"]] + q["frailty_slope"] * latent["frailty"]))
    on_therapy = min(follow_up, course["end_day"] if course["end_day"] is not None else follow_up)
    quality_days = follow_up * base - on_therapy * q["on_therapy_decrement"]
    for e in events:
        days = cons["event_days"][str(e["grade"])]
        if e["event_type"] in OWN_FACTORS:
            days *= cons["event_days"][f"{e['event_type']}_factor"]
        end = follow_up if e["grade"] == 5 else min(follow_up, e["day"] + days)
        quality_days -= q["event_decrement"][str(e["grade"])] * max(0, end - e["onset_day"])

    return {
        "scenario_id": plan["scenario_id"],
        "patient_id": patient["patient_id"],
        "follow_up_days": follow_up,
        "high_risk_flag": plan["high_risk"],
        "participating": plan["participating"],
        "severe_toxicity_90d": bool(severe),
        "severe_toxicity_day": min(severe) if severe else None,
        "ild": ild is not None,
        "ild_onset_day": ild["onset_day"] if ild else None,
        "ild_diagnosis_day": ild["diagnosis_day"] if ild else None,
        "ild_grade": ild["grade"] if ild else None,
        "cv_event": major,
        "cv_event_1y": major and cv["diagnosis_day"] <= 364,
        "cv_onset_day": cv["onset_day"] if cv else None,
        "cv_event_day": cv["diagnosis_day"] if major else None,
        "cv_grade": cv["grade"] if cv and cv["recognised"] else None,
        "treatment_end_day": course["end_day"],
        "treatment_end_reason": course["end_reason"],
        "death_day": course["death_day"],
        "death_from_toxicity": course["toxic_death"],
        "hospital_days": hospital_days,
        "icu_days": icu_days,
        "unplanned_visits": visits,
        "alerts": len(alerts),
        "false_alerts": sum(not a["true_alert"] for a in alerts),
        "cost_care": round(cost_care, 2),
        "cost_intervention": round(cost_intervention, 2),
        "qaly": round(max(0.0, quality_days) / 365.25, 4),
    }
