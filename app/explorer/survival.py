"""Time-to-event endpoints and their comparison between scenarios.

Every endpoint counts from therapy start. A patient without the event is
censored at the end of follow-up: death for endpoints that death does not
end, otherwise the end of the simulated period. Curves:

- Kaplan-Meier for endpoints in which death is part of the event (overall
  survival, survival without severe toxicity, time on therapy).
- Aalen-Johansen cumulative incidence for events that death or another event
  can prevent (first severe adverse event, end of therapy for toxicity, lung
  toxicity, cardiovascular events). 1 - Kaplan-Meier would count the patients
  who died as if they could still have the event and overestimate it.

Comparison: the scenarios hold the same patients with the same random
draws, so they are compared pair by pair, not with tests for independent
groups such as the log-rank test. Every patient is followed until death or
the end of the simulated period, so up to that end each patient's time and
status are known. A restricted mean (mean time without the event up to a
horizon) and the share with the event at a time are then means of
per-patient values, and their difference between two scenarios is the mean
of the per-patient differences; its 95% confidence interval comes from the
spread of these differences.
"""
import math
from bisect import bisect_right
from dataclasses import dataclass

YEAR, MONTH = 365.25, 30.44
Z95 = 1.959964


@dataclass(frozen=True)
class Record:
    """One patient for one endpoint: time in days and what happened then. cause
    None means censored (no event up to that time)."""
    patient_id: str
    time: float
    cause: str | None


# Estimators ------------------------------------------------------------------

def _grouped(records):
    """[(time, {cause: n}, censored n)] in time order."""
    by_time = {}
    for r in records:
        counts = by_time.setdefault(r.time, [{}, 0])
        if r.cause is None:
            counts[1] += 1
        else:
            counts[0][r.cause] = counts[0].get(r.cause, 0) + 1
    return [(t, *by_time[t]) for t in sorted(by_time)]


def kaplan_meier(records):
    """Share without any event over time, as steps [(time, share)] starting at
    (0, 1). Each step holds from its time on."""
    steps, at_risk, share = [(0.0, 1.0)], len(records), 1.0
    for t, causes, censored in _grouped(records):
        events = sum(causes.values())
        if events and at_risk:
            share *= 1 - events / at_risk
            steps.append((t, share))
        at_risk -= events + censored
    return steps


def cumulative_incidence(records, cause):
    """Aalen-Johansen estimate of the share with an event of the given cause,
    with all other causes competing, as steps [(time, share)] from (0, 0)."""
    steps, at_risk, alive, total = [(0.0, 0.0)], len(records), 1.0, 0.0
    for t, causes, censored in _grouped(records):
        events = sum(causes.values())
        if events and at_risk:
            mine = causes.get(cause, 0)
            if mine:
                total += alive * mine / at_risk
                steps.append((t, total))
            alive *= 1 - events / at_risk
        at_risk -= events + censored
    return steps


def value_at(steps, time):
    """Value of a step curve at a time."""
    return steps[bisect_right([s[0] for s in steps], time) - 1][1]


def restricted_mean(steps, horizon):
    """Area under a falling step curve up to horizon: the mean time without the event."""
    area = 0.0
    for (t, v), nxt in zip(steps, steps[1:] + [(horizon, None)]):
        if t >= horizon:
            break
        area += v * (min(nxt[0], horizon) - t)
    return area


def median(steps):
    """First time at which a falling curve reaches 0.5 or less; None if it does not."""
    return next((t for t, v in steps if v <= 0.5), None)


def at_risk(records, time):
    """Number of patients still under observation and without event at a time."""
    return sum(r.time >= time for r in records)


def sampled(steps, end, most=400):
    """A step curve as chart points up to end: its own steps, or the values on an
    even grid if it has more than most of them."""
    inner = [s for s in steps if s[0] <= end]
    if len(inner) > most:
        inner = [(end * i / most, value_at(steps, end * i / most)) for i in range(most + 1)]
    return inner + [(end, inner[-1][1])]


# Paired comparison -----------------------------------------------------------

def complete_until(records, horizon):
    """True if every censored patient is followed at least until horizon, so that
    the status of all patients up to horizon is known."""
    return all(r.cause is not None or r.time >= horizon for r in records)


def restricted_times(records, horizon):
    """{patient: time without any event up to horizon}."""
    return {r.patient_id: min(r.time, horizon) for r in records}


def had_event(records, time, cause=None):
    """{patient: 1 if the event (of that cause, or any) came by time, else 0}."""
    return {r.patient_id: int(r.cause is not None and r.time <= time and (cause is None or r.cause == cause))
            for r in records}


@dataclass(frozen=True)
class Paired:
    """Means of a per-patient value under two scenarios and the mean of the
    per-patient differences with its 95% confidence interval."""
    a: float
    b: float
    diff: float
    low: float
    high: float
    n: int


def paired(values_a, values_b):
    """Paired comparison of {patient: value} under scenario a and b, over the
    patients in both. None without patients."""
    ids = sorted(values_a.keys() & values_b.keys())
    n = len(ids)
    if not n:
        return None
    diffs = [values_a[i] - values_b[i] for i in ids]
    mean = sum(diffs) / n
    sd = math.sqrt(sum((d - mean) ** 2 for d in diffs) / (n - 1)) if n > 1 else 0.0
    half = Z95 * sd / math.sqrt(n)
    return Paired(sum(values_a[i] for i in ids) / n, sum(values_b[i] for i in ids) / n,
                  mean, mean - half, mean + half, n)


# Endpoints -------------------------------------------------------------------

def _end(row):
    """Last day of follow-up: death or the end of the simulated period."""
    return row["death_day"] if row["death_day"] is not None else row["follow_up_days"]


def overall_survival(rows):
    """Death from any cause."""
    return [Record(r["patient_id"], _end(r), "death" if r["death_day"] is not None else None) for r in rows]


def first_severe(events):
    """Day on which the first adverse event of grade 3 to 5 was recognised, or None."""
    days = [e["day"] for e in events if e["grade"] >= 3]
    return min(days) if days else None


def severe_free_survival(rows, events_of):
    """First adverse event of grade 3 to 5, or death, whichever comes first."""
    out = []
    for r in rows:
        day = first_severe(events_of.get(r["patient_id"], []))
        if day is not None and (r["death_day"] is None or day <= r["death_day"]):
            out.append(Record(r["patient_id"], day, "severe"))
        elif r["death_day"] is not None:
            out.append(Record(r["patient_id"], r["death_day"], "death"))
        else:
            out.append(Record(r["patient_id"], r["follow_up_days"], None))
    return out


def therapy_end(rows):
    """End of the therapy line, with its reason as cause; ongoing therapy is censored."""
    return [Record(r["patient_id"], r["treatment_end_day"], r["treatment_end_reason"])
            if r["treatment_end_day"] is not None else Record(r["patient_id"], _end(r), None)
            for r in rows]


def specific_event(rows, day_of):
    """An event with death as competing cause; day_of(row) is its day or None."""
    out = []
    for r in rows:
        day = day_of(r)
        if day is not None:
            out.append(Record(r["patient_id"], day, "event"))
        elif r["death_day"] is not None:
            out.append(Record(r["patient_id"], r["death_day"], "death"))
        else:
            out.append(Record(r["patient_id"], r["follow_up_days"], None))
    return out


def lung_toxicity(rows):
    """Lung toxicity of grade 2 or higher, by its day of onset."""
    return specific_event(rows, lambda r: r["ild_onset_day"] if r["ild"] and (r["ild_grade"] or 0) >= 2 else None)


def cardiovascular(rows):
    """Major adverse cardiovascular event."""
    return specific_event(rows, lambda r: r["cv_event_day"] if r["cv_event"] else None)
