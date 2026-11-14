"""Chart data over time and across scenarios.

The functions return chart specs like those of charts.py, which
static/explorer/charts.js draws. Two scenarios can be shown together: the
selected one (class "sa") and a comparison (class "sb", dashed).
"""
import math

from .charts import _empty, _r, mean, nice_max, rate
from .survival import (MONTH, YEAR, at_risk, complete_until, cumulative_incidence, had_event, kaplan_meier,
                       median, overall_survival, paired, restricted_mean, restricted_times, sampled,
                       severe_free_survival, value_at)

OS_HORIZON = 5 * YEAR

ILD = "interstitial_lung_disease"
CV = "cardiovascular_event"
CLASSES = ("sa", "sb")
LEAD_BINS = [(0, 6), (7, 13), (14, 27), (28, 55), (56, None)]
GRADE_GROUPS = [("grade 1", "g1", (1,)), ("grade 2", "g2", (2,)), ("grade 3–4", "g3", (3, 4)), ("grade 5", "g5", (5,))]
EVENT_NAMES = {ILD: "lung toxicity", CV: "cardiovascular event"}
# Events with a monitoring component of their own, shown by grade per scenario: (chart id, type, title).
GRADED_EVENTS = [("iv-lung", ILD, "Lung toxicity by grade"), ("iv-heart", CV, "Cardiovascular events by grade")]


def event_name(kind):
    """Readable name of an event type."""
    return EVENT_NAMES.get(kind, kind.replace("_", " "))


# Survival and time to event --------------------------------------------------

# Reasons for the end of therapy, in the order of the chart: (cause, label, class).
END_REASONS = [("toxicity", "toxicity", "end-tox"), ("progression", "progression", "end-prog"),
               ("completed", "completed as planned", "end-done"), ("death", "death", "end-death"),
               ("lost_to_follow_up", "lost to follow-up", "end-lost")]


def _axis(end_day):
    """Unit, label and ticks of a time axis that reaches end_day: years beyond
    three years, months below. The last tick is at or after end_day."""
    if end_day > 3 * YEAR:
        unit, label, step = YEAR, "years after therapy start", 1 if end_day <= 10.5 * YEAR else 2
    else:
        unit, label, step = MONTH, "months after therapy start", 3 if end_day <= 24.5 * MONTH else 6
    top = math.ceil(end_day / unit / step - 0.02) * step
    return unit, label, list(range(0, top + 1, step))


def time_to_event(title, named, curve, end_day, y_label, falling, patient_day=None, note=None):
    """Curves of one endpoint for the selected scenario and the comparison, with
    the number at risk below. named is [(scenario title, records)]; curve(records)
    gives the steps; patient_day marks the selected patient's event."""
    if not named or not all(records for _, records in named):
        return _empty("line", title)
    unit, label, ticks = _axis(end_day)
    series, risk_rows = [], []
    for (name, records), cls in zip(named, CLASSES):
        points = [[_r(t / unit, 3), _r(v)] for t, v in sampled(curve(records), end_day)]
        series.append({"name": name, "cls": cls, "dash": cls == "sb", "step": True, "points": points})
        risk_rows.append({"name": name, "cls": cls, "dash": cls == "sb",
                          "values": [at_risk(records, min(t * unit, end_day)) for t in ticks]})
    top = 1.0 if falling else nice_max(max(p[1] for s in series for p in s["points"]) or 0.01)
    spec = {
        "type": "line", "title": title, "series": series,
        "x": {"label": label, "format": "num", "min": 0, "max": ticks[-1], "ticks": ticks},
        "y": {"label": y_label, "format": "pct", "min": 0, "max": top},
        "at_risk": {"rows": risk_rows},
        "marker": ({"x": _r(patient_day / unit, 3), "label": f"patient, day {patient_day}"}
                   if patient_day is not None and patient_day <= end_day else None),
    }
    if note:
        spec["note"] = note
    return spec


def therapy_end_reasons(name, records, end_day):
    """Cumulative incidence of the end of therapy by reason, for one scenario."""
    title = f"End of therapy by reason: {name}"
    if not records:
        return _empty("line", title)
    unit, label, ticks = _axis(end_day)
    series = [{"name": text, "cls": cls, "step": True,
               "points": [[_r(t / unit, 3), _r(v)] for t, v in sampled(cumulative_incidence(records, cause), end_day)]}
              for cause, text, cls in END_REASONS if any(r.cause == cause for r in records)]
    return {
        "type": "line", "title": title, "series": series,
        "x": {"label": label, "format": "num", "min": 0, "max": ticks[-1], "ticks": ticks},
        "y": {"label": "share of patients", "format": "pct", "min": 0,
              "max": nice_max(max(p[1] for s in series for p in s["points"]) or 0.01)},
        "note": "Each reason against all others; at any time the shares and the share still on therapy add up to 100%.",
    }


def _span(days):
    """A time in words: 90 days, 1 year, 5 years."""
    if days >= YEAR - 1 and abs(days / YEAR - round(days / YEAR)) < 0.01:
        years = round(days / YEAR)
        return f"{years} year{'s' if years != 1 else ''}"
    return f"{round(days)} days"


# Measures of the endpoint table: (endpoint, measure label, kind, records key, days, cause, unit).
# kind: "mean" restricted mean up to days, "free" share without event at days,
# "cif" share with an event of cause by days, "median" median time. {span} in a
# label is replaced by the time, cut to the simulated period.
MEASURES = [
    ("Overall survival", "mean survival within {span} (restricted mean)", "mean", "os", 5 * YEAR, None, "years"),
    ("Overall survival", "alive at {span}", "free", "os", YEAR, None, "pct"),
    ("Overall survival", "median survival", "median", "os", None, None, "years"),
    ("Survival without severe toxicity", "mean time alive without severe event within {span}", "mean", "sfs",
     YEAR, None, "days"),
    ("Survival without severe toxicity", "alive without severe event at {span}", "free", "sfs", YEAR, None, "pct"),
    ("First severe adverse event", "cumulative incidence at {span}", "cif", "severe", 90, "event", "pct"),
    ("First severe adverse event", "cumulative incidence at {span}", "cif", "severe", YEAR, "event", "pct"),
    ("Time on therapy", "median time on therapy", "median", "therapy", None, None, "months"),
    ("End of therapy for toxicity", "cumulative incidence at {span}", "cif", "therapy", YEAR, "toxicity", "pct"),
    ("Lung toxicity, grade 2 or higher", "cumulative incidence at {span}", "cif", "lung", YEAR, "event", "pct"),
    ("Major cardiovascular event", "cumulative incidence at {span}", "cif", "heart", YEAR, "event", "pct"),
]


def _show(value, unit):
    """A value of the endpoint table as text."""
    if value is None:
        return "–"
    if unit == "pct":
        return f"{100 * value:.1f}%"
    if unit == "years":
        return f"{value / YEAR:.2f} years"
    if unit == "months":
        return f"{value / MONTH:.1f} months"
    return f"{value:.1f} days"


def _show_diff(value, unit):
    """A difference of the endpoint table: percentage points for shares, days for times."""
    if unit == "pct":
        return f"{100 * value:+.1f} pts"
    return f"{value:+.1f} days"


def _curve_value(records, kind, days, cause):
    """Value of a measure from the estimated curve (used when follow-up is not complete)."""
    if kind == "cif":
        return value_at(cumulative_incidence(records, cause), days)
    steps = kaplan_meier(records)
    if kind == "free":
        return value_at(steps, days)
    if kind == "median":
        return median(steps)
    return restricted_mean(steps, days)


def _per_patient(records, kind, days, cause):
    """{patient: value} of a measure, valid when follow-up is complete until days."""
    if kind == "mean":
        return restricted_times(records, days)
    if kind == "free":
        return {k: 1 - v for k, v in had_event(records, days).items()}
    return had_event(records, days, cause)


def endpoint_table(named, horizon):
    """Rows of the endpoint table for the selected scenario and, if given, the
    comparison. named is [(scenario title, {records key: (records, population note)})].
    Times are cut to the simulated period (horizon days)."""
    out = []
    for endpoint, label, kind, key, days, cause, unit in MEASURES:
        found = [parts.get(key) for _, parts in named]
        if not all(f and f[0] for f in found):
            continue
        records = [f[0] for f in found]
        days = min(days, horizon) if days else None
        row = {"endpoint": endpoint, "population": found[0][1], "measure": label.format(span=_span(days or 0)),
               "values": [], "diff": None, "ci": None}
        complete = days is not None and all(complete_until(r, days) for r in records)
        if kind != "median" and complete and len(records) == 2:
            p = paired(*(_per_patient(r, kind, days, cause) for r in records))
            row["values"] = [_show(p.a, unit), _show(p.b, unit)]
            row["diff"] = _show_diff(p.diff, "pct" if unit == "pct" else "days")
            low, high = (_show_diff(v, "pct" if unit == "pct" else "days") for v in (p.low, p.high))
            row["ci"] = f"{low} to {high}"
        else:
            values = [_curve_value(r, kind, days, cause) for r in records]
            row["values"] = [_show(v, unit) for v in values]
            if len(values) == 2 and None not in values and kind != "median":
                row["diff"] = _show_diff(values[0] - values[1], "pct" if unit == "pct" else "days")
        out.append(row)
    for previous, row in zip([None] + out, out):
        row["first"] = previous is None or previous["endpoint"] != row["endpoint"]
    return out


# Scenarios side by side ------------------------------------------------------

def scenario_table(scenarios, rows_of, events_of, ids, usual_care="usual_care"):
    """Key numbers per scenario for the patients with the given ids.
    free_1y is the share alive without severe toxicity at one year, d_os the
    gain in mean survival within five years against usual care, in days.

    rows_of(scenario_id) and events_of(scenario_id) give the rows and the
    events of a scenario. Costs and quality-adjusted life years are also
    given as difference to usual care, where that scenario exists.
    """
    table = []
    for s in scenarios:
        sid = s["scenario_id"]
        rows = [r for r in rows_of(sid) if r["patient_id"] in ids]
        if not rows:
            return []
        events = [e for r in rows for e in events_of(sid).get(r["patient_id"], [])]
        alerts = sum(r["alerts"] for r in rows)
        n = len(rows)
        end = max(r["follow_up_days"] for r in rows)
        table.append({
            "scenario": s, "n": n,
            "participating": rate(rows, "participating"),
            "flagged": rate(rows, "high_risk_flag"),
            "severe_90d": rate(rows, "severe_toxicity_90d"),
            "severe_events": sum(e["grade"] >= 3 for e in events) / n,
            "early": sum(e["detected_by"] == "monitoring" for e in events) / n,
            "cv_events": sum(r["cv_event"] for r in rows),
            "toxic_deaths": sum(r["death_from_toxicity"] for r in rows),
            "hospital_days": mean(r["hospital_days"] for r in rows),
            "alerts": alerts / n,
            "false_share": sum(r["false_alerts"] for r in rows) / alerts if alerts else None,
            "qaly": mean(r["qaly"] for r in rows),
            "cost_care": mean(r["cost_care"] for r in rows),
            "cost_intervention": mean(r["cost_intervention"] for r in rows),
            # Every patient is followed until death or the end of the simulated period.
            "_os": restricted_times(overall_survival(rows), min(OS_HORIZON, end)),
            "free_1y": 1 - mean(had_event(severe_free_survival(rows, events_of(sid)), min(YEAR, end)).values()),
        })
    for t in table:
        t["cost"] = t["cost_care"] + t["cost_intervention"]
    base = next((t for t in table if t["scenario"]["scenario_id"] == usual_care), None)
    for t in table:
        t["d_cost"] = t["d_qaly"] = t["icer"] = t["d_os"] = None
        if base and t is not base:
            t["d_os"] = paired(t["_os"], base["_os"]).diff
            t["d_cost"], t["d_qaly"] = t["cost"] - base["cost"], t["qaly"] - base["qaly"]
            # A cost per QALY is only meaningful for a clear gain at extra cost.
            if t["d_qaly"] >= 0.0005 and t["d_cost"] > 0:
                t["icer"] = t["d_cost"] / t["d_qaly"]
    for t in table:
        del t["_os"]
    return table


def scenario_bars(table, title, series, label, fmt, selected, stacked=False):
    """One bar per scenario. series is [(name, class, key of the table)]."""
    if not table:
        return _empty("bars", title)
    ids = [t["scenario"]["scenario_id"] for t in table]
    return {
        "type": "bars", "horizontal": True, "stacked": stacked, "title": title,
        "categories": [t["scenario"]["title"] for t in table],
        "series": [{"name": name, "cls": cls, "values": [_r(t[key]) for t in table]}
                   for name, cls, key in series],
        "value": {"label": label, "format": fmt},
        "highlight": ids.index(selected) if selected in ids else None,
        "highlight_name": "selected scenario",
        "links": [{"scenario": sid} for sid in ids],
    }


def event_grades(scenarios, events_of, ids, selected, kind, title):
    """Number of events of one type per scenario, by grade at recognition."""
    counts = []
    for s in scenarios:
        grades = [e["grade"] for pid, events in events_of(s["scenario_id"]).items() if pid in ids
                  for e in events if e["event_type"] == kind]
        counts.append([sum(g in members for g in grades) for _, _, members in GRADE_GROUPS])
    if not any(sum(c) for c in counts):
        return _empty("bars", title)
    sids = [s["scenario_id"] for s in scenarios]
    return {
        "type": "bars", "horizontal": True, "stacked": True, "title": title,
        "categories": [s["title"] for s in scenarios],
        "series": [{"name": name, "cls": cls, "values": [c[i] for c in counts]}
                   for i, (name, cls, _) in enumerate(GRADE_GROUPS)],
        "value": {"label": "events", "format": "int"},
        "highlight": sids.index(selected) if selected in sids else None,
        "highlight_name": "selected scenario",
        "links": [{"scenario": sid} for sid in sids],
    }


def monitored(events, ids):
    """Events of the given patients that monitoring recognised."""
    return [e for pid, found in events.items() if pid in ids for e in found
            if e["detected_by"] == "monitoring"]


def lead_time(events, ids):
    """Days by which monitoring recognised events earlier than usual care."""
    title = "Days gained by early recognition"
    gained = [e["usual_care_day"] - e["day"] for e in monitored(events, ids)]
    if not gained:
        return _empty("bars", title)
    labels = [f"{a}–{b}" if b is not None else f"≥ {a}" for a, b in LEAD_BINS]
    values = [sum(g >= a and (b is None or g <= b) for g in gained) for a, b in LEAD_BINS]
    values[0] += sum(g < 0 for g in gained)
    return {
        "type": "bars", "title": title, "categories": labels,
        "series": [{"name": "events recognised through monitoring", "cls": "sa", "values": values}],
        "value": {"label": "events", "format": "int"}, "axis": "days earlier than in usual care",
        "highlight": None,
    }


def grade_shift(events, ids):
    """Grade of the events that monitoring recognised, against the grade they
    would have reached in usual care."""
    title = "Grade of events recognised through monitoring"
    found = monitored(events, ids)
    if not found:
        return _empty("bars", title)
    grades = range(1, 6)
    return {
        "type": "bars", "title": title, "categories": [f"grade {g}" for g in grades],
        "series": [
            {"name": "in usual care", "cls": "sb", "values": [sum(e["usual_care_grade"] == g for e in found) for g in grades]},
            {"name": "with monitoring", "cls": "sa", "values": [sum(e["grade"] == g for e in found) for g in grades]},
        ],
        "value": {"label": "events", "format": "int"}, "highlight": None,
    }


# One patient over time -------------------------------------------------------

def _week(day):
    """Week of a day after therapy start, as used on the x axis (day 1 is week 0)."""
    return _r((day - 1) / 7, 2)


def markers(course, outcome):
    """Events, alerts, end of therapy and death of one course as chart markers."""
    found = []
    for e in course["events"]:
        via = ", through monitoring" if e["detected_by"] == "monitoring" else ""
        found.append({"x": _week(e["day"]), "cls": "ev",
                      "label": f"{event_name(e['event_type'])}, grade {e['grade']}, day {e['day']}{via}"})
    for a in course["alerts"]:
        kind = event_name(a["event_type"]) if a["true_alert"] else "false alert"
        found.append({"x": _week(a["day"]), "cls": "al", "label": f"alert, day {a['day']}: {kind}"})
    if outcome.get("treatment_end_day") and outcome["treatment_end_reason"] != "death":
        reason = outcome["treatment_end_reason"].replace("_", " ")
        found.append({"x": _week(outcome["treatment_end_day"]), "cls": "end",
                      "label": f"end of therapy, day {outcome['treatment_end_day']}: {reason}"})
    return found


MARKER_LEGEND = [{"name": "adverse event recognised", "cls": "mk-ev"}, {"name": "alert", "cls": "mk-al"},
                 {"name": "end of therapy", "cls": "mk-end"}]

PATIENT_CHARTS = [
    ("dose", "Dose level", "dose_level", "share of the standard dose", "num", True),
    ("neutrophils", "Neutrophils", "neutrophils_10e9_l", "10⁹/l", "num", False),
    ("haemoglobin", "Haemoglobin", "haemoglobin_g_dl", "g/dl", "num", False),
    ("platelets", "Platelets", "platelets_10e9_l", "10⁹/l", "int", False),
    ("spo2", "Oxygen saturation", "spo2_percent", "%", "int", False),
    ("pressure", "Systolic blood pressure", "systolic_bp_mmhg", "mmHg", "int", False),
]
SYMPTOMS = [("pro_fatigue", "fatigue", "t3"), ("pro_diarrhoea", "diarrhoea", "obs"),
            ("pro_cough", "cough", "t1"), ("pro_dyspnoea", "shortness of breath", "pred"),
            ("pro_chest_pain", "chest pain", "t2")]


def _points(observations, field):
    """Points [week, value] of one observation field, without the weeks where it is
    missing."""
    return [[w, v] for w, v in zip(observations["week"], observations[field]) if v is not None]


def patient_charts(named_courses, outcome):
    """Charts of one patient over the weeks of observation: [(id, spec)].

    named_courses is [(scenario title, course)] with the selected scenario
    first; outcome is the outcome of the patient in the selected scenario.
    """
    weeks = max(len(c["observations"]["week"]) for _, c in named_courses)
    if not weeks:
        return []
    x = {"label": "week after therapy start", "format": "int", "min": 0, "max": max(weeks - 1, 4)}
    marks = markers(named_courses[0][1], outcome)
    charts = []
    for cid, title, field, unit, fmt, step in PATIENT_CHARTS:
        series = [{"name": name, "cls": cls, "dash": cls == "sb", "step": step,
                   "points": _points(c["observations"], field)}
                  for (name, c), cls in zip(named_courses, CLASSES)]
        values = [p[1] for s in series for p in s["points"]]
        if not values:
            continue
        low = 0 if field in ("dose_level", "neutrophils_10e9_l", "platelets_10e9_l") else min(values)
        high = max(values) if max(values) > low else low + 1
        charts.append((f"patient-{cid}", {
            "type": "line", "title": title, "series": series, "x": x,
            "y": {"label": unit, "format": fmt, "min": low, "max": high},
            "markers": marks, "marker_legend": MARKER_LEGEND,
        }))
    observations = named_courses[0][1]["observations"]
    charts.append(("patient-symptoms", {
        "type": "line", "title": f"Reported symptoms ({named_courses[0][0]})",
        "series": [{"name": name, "cls": cls, "points": _points(observations, field)}
                   for field, name, cls in SYMPTOMS],
        "x": x, "y": {"label": "0 (none) to 4 (very severe)", "format": "int", "min": 0, "max": 4},
        "markers": marks, "marker_legend": MARKER_LEGEND,
    }))
    return charts


def event_rows(course):
    """Events of one course for a table, in order of recognition."""
    return [{**e, "name": event_name(e["event_type"]), "gained": e["usual_care_day"] - e["day"]}
            for e in sorted(course["events"], key=lambda e: e["day"])]
