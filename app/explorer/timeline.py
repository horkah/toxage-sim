"""Chart data over time and across scenarios.

The functions return chart specs like those of charts.py, which
static/explorer/charts.js draws. Two scenarios can be shown together: the
selected one (class "sa") and a comparison (class "sb", dashed).
"""
from bisect import bisect_right

from .charts import _empty, _r, mean, nice_max, rate

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


# Cohort over time ------------------------------------------------------------

def share_curve(days, n, end_day, per, falling=False, steps=120):
    """Share of n patients with an event up to each time, as points [x, share].
    days are the event days, x counts in units of per days. With falling the
    share without the event is given."""
    days = sorted(d for d in days if d is not None)
    points = []
    for i in range(steps + 1):
        day = end_day * i / steps
        share = bisect_right(days, day) / n if n else 0
        points.append([_r(day / per, 3), _r(1 - share if falling else share)])
    return points


def _over_time(title, named, days_of, end_day, per, x_label, y_label, falling=False):
    """One curve per scenario. named is [(scenario title, rows or event days)]."""
    series = []
    for (name, items), cls in zip(named, CLASSES):
        n, days = days_of(items)
        if not n:
            return _empty("line", title)
        series.append({"name": name, "cls": cls, "dash": cls == "sb",
                       "points": share_curve(days, n, end_day, per, falling)})
    top = 1.0 if falling else nice_max(max(p[1] for s in series for p in s["points"]) or 0.01)
    return {
        "type": "line", "title": title, "series": series,
        "x": {"label": x_label, "format": "num", "min": 0, "max": end_day / per},
        "y": {"label": y_label, "format": "pct", "min": 0, "max": top},
    }


def survival(named_rows, horizon_days):
    """Share of patients alive over the years after therapy start."""
    return _over_time(
        "Survival", named_rows, lambda rows: (len(rows), [r["death_day"] for r in rows]),
        horizon_days, 365.25, "years after therapy start", "share alive", falling=True)


def on_therapy(named_rows, horizon_days):
    """Share of patients still on the therapy line over the first years."""
    end = min(horizon_days, 3 * 365)
    return _over_time(
        "On therapy", named_rows, lambda rows: (len(rows), [r["treatment_end_day"] for r in rows]),
        end, 30.44, "months after therapy start", "share on therapy", falling=True)


def first_severe_days(events, ids):
    """Day of the first event of grade 3 to 5 per patient, None without one."""
    days = []
    for pid in ids:
        severe = [e["day"] for e in events.get(pid, []) if e["grade"] >= 3]
        days.append(min(severe) if severe else None)
    return days


def severe_incidence(named_days, horizon_days):
    """Share of patients with a first severe adverse event over time."""
    end = min(horizon_days, 2 * 365)
    return _over_time(
        "First severe adverse event", named_days, lambda days: (len(days), days),
        end, 30.44, "months after therapy start", "share with event")


# Scenarios side by side ------------------------------------------------------

def scenario_table(scenarios, rows_of, events_of, ids, usual_care="usual_care"):
    """Key numbers per scenario for the patients with the given ids.

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
        })
    for t in table:
        t["cost"] = t["cost_care"] + t["cost_intervention"]
    base = next((t for t in table if t["scenario"]["scenario_id"] == usual_care), None)
    for t in table:
        t["d_cost"] = t["d_qaly"] = t["icer"] = None
        if base and t is not base:
            t["d_cost"], t["d_qaly"] = t["cost"] - base["cost"], t["qaly"] - base["qaly"]
            # A cost per QALY is only meaningful for a clear gain at extra cost.
            if t["d_qaly"] >= 0.0005 and t["d_cost"] > 0:
                t["icer"] = t["d_cost"] / t["d_qaly"]
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
