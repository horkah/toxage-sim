"""Chart data of the explorer.

Every function returns a plain dict (a chart spec) that static/explorer/charts.js
draws. Three chart types exist:

  bars     categories with one or more series, grouped or stacked
  line     series of (x, y) points, optionally as steps
  scatter  points (x, y, class, patient id)

Values in 0..1 with format "pct" are shown in percent. "highlight" marks the
selected patient. "links" holds per category the query parameters that a click
on it sets, which narrows the filter to that category.
"""
import math

import toxage_risk

from .cohort import display, fields, risk_key

EVENT_CLASSES = [{"name": "no event", "cls": "none"}, {"name": "event", "cls": "event"}]


def nice_step(span, count):
    """A round step (1, 2, 2.5 or 5 times a power of ten) that splits span
    into about count parts."""
    raw = span / count if span > 0 else 1
    magnitude = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * magnitude * (1 + 1e-9):
            return m * magnitude
    return 10 * magnitude


def nice_max(value, count=5):
    """Smallest multiple of a round step that is at least value."""
    step = nice_step(value, count)
    return max(step, math.ceil(value / step - 1e-9) * step)


def rate(rows, key):
    """Share of rows where key is true, None without rows."""
    return sum(bool(r[key]) for r in rows) / len(rows) if rows else None


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def percentile(values, value):
    """Percent of values below value, ties counting half."""
    values = [v for v in values if v is not None]
    if not values or value is None:
        return None
    below = sum(v < value for v in values)
    equal = sum(v == value for v in values)
    return 100 * (below + equal / 2) / len(values)


def _pct(x):
    return float(f"{100 * x:.6g}")


def _r(x, digits=4):
    return None if x is None else round(x, digits)


def grouping(field, rows):
    """Categories of a field: (labels, key, links).

    key(value) gives the index of the category of a value, or None if the
    value belongs to no category. Choice and boolean fields have one category
    per value, small integer ranges one per number, other numbers round bins.
    Missing values of a nullable field form the last category.
    """
    name = field.name
    if field.kind == "choice":
        index = {c: i for i, c in enumerate(field.choices)}
        labels = [display(c) for c in field.choices]
        links = [{name: [c]} for c in field.choices]
        key = index.get
    elif field.kind == "bool":
        labels, links = ["no", "yes"], [{name: "false"}, {name: "true"}]
        def key(v): return None if v is None else int(v)
    elif field.integer and field.minimum is not None and field.maximum is not None \
            and field.maximum - field.minimum <= 10:
        low, high = int(field.minimum), int(field.maximum)
        labels = [str(v) for v in range(low, high + 1)]
        links = [{f"{name}_min": v, f"{name}_max": v} for v in range(low, high + 1)]
        def key(v): return None if v is None else int(v) - low
    else:
        present = sorted(r[name] for r in rows if r.get(name) is not None)
        # Bins span the lower 95% of the values; the rest falls into an open
        # top bin, so that a long tail does not squeeze all other bins.
        low = present[0] if present else 0
        high = present[int(0.95 * (len(present) - 1))] if present else 0
        step = nice_step(high - low, 8)
        if field.integer:
            step = max(1, math.ceil(step))
        start = math.floor(low / step) * step
        count = int((high - start) // step) + 1
        starts = [start + i * step for i in range(count)]
        tail = bool(present) and present[-1] >= start + count * step
        ends = [a + step - 1 if field.integer else a + step for a in starts]
        if field.integer and field.maximum is not None:
            ends = [min(e, int(field.maximum)) for e in ends]
        if field.integer:
            labels = [f"{a}–{e}" if e > a else str(a) for a, e in zip(starts, ends)]
            links = [{f"{name}_min": a, f"{name}_max": e} for a, e in zip(starts, ends)]
        else:
            labels = [f"{a:g}–{e:g}" for a, e in zip(starts, ends)]
            links = [None] * count
        if tail:
            top = start + count * step
            labels.append(f"{top:g}" if top == field.maximum else f"≥ {top:g}")
            links.append({f"{name}_min": top} if field.integer else None)
            count += 1

        def key(v):
            if v is None:
                return None
            return min(count - 1, max(0, int((v - start) // step)))
    if field.nullable:
        labels, links = labels + ["not recorded"], links + [None]
        missing, inner = len(labels) - 1, key
        def key(v): return missing if v is None else inner(v)
    return labels, key, links


def grouped(rows, field, patient=None):
    """Non-empty categories as [(label, rows, link)] and the index of the
    patient's category (kept even if empty), or None."""
    labels, key, links = grouping(field, rows)
    buckets = [[] for _ in labels]
    for r in rows:
        i = key(r.get(field.name))
        if i is not None:
            buckets[i].append(r)
    mine = key(patient.get(field.name)) if patient else None
    kept = [i for i, b in enumerate(buckets) if b or i == mine]
    groups = [(labels[i], buckets[i], links[i]) for i in kept]
    return groups, (kept.index(mine) if mine in kept else None)


def _scored(rows, model, patient):
    """Rows for which the model gives a risk, and the patient if it does."""
    key = risk_key(model)
    rows = [r for r in rows if r[key] is not None]
    return rows, (patient if patient and patient[key] is not None else None)


def _empty(chart_type, title):
    return {"type": chart_type, "title": title, "empty": True}


def by_field(rows, field, model, patient=None):
    """Observed rate and mean predicted risk per category of a field."""
    rows, patient = _scored(rows, model, patient)
    if not rows:
        return _empty("bars", field.label)
    groups, highlight = grouped(rows, field, patient)
    key = risk_key(model)
    return {
        "type": "bars",
        "horizontal": True,
        "title": field.label,
        "categories": [g[0] for g in groups],
        "counts": [len(g[1]) for g in groups],
        "series": [
            {"name": "observed", "cls": "obs",
             "values": [_r(rate(g[1], model.outcome)) for g in groups]},
            {"name": "predicted", "cls": "pred",
             "values": [_r(mean(r[key] for r in g[1])) for g in groups]},
        ],
        "value": {"label": "rate", "format": "pct"},
        "highlight": highlight,
        "links": [g[2] for g in groups],
    }


def risk_histogram(rows, model, patient=None):
    """Number of patients per risk band, split by observed outcome."""
    title = "Distribution of predicted risk"
    rows, patient = _scored(rows, model, patient)
    if not rows:
        return _empty("bars", title)
    key = risk_key(model)
    top = max([r[key] for r in rows] + ([patient[key]] if patient else []))
    step = min(nice_step(top, 10), 0.1)
    count = max(1, min(int(math.ceil(top / step - 1e-9)), int(round(1 / step))))
    events, others = [0] * count, [0] * count
    for r in rows:
        i = min(count - 1, int(r[key] // step))
        (events if r[model.outcome] else others)[i] += 1
    bands = [(i * step, (i + 1) * step) for i in range(count)]
    return {
        "type": "bars",
        "stacked": True,
        "title": title,
        "categories": [f"{_pct(a):g}–{_pct(b):g}%" for a, b in bands],
        "series": [
            {"name": "event", "cls": "event", "values": events},
            {"name": "no event", "cls": "none", "values": others},
        ],
        "value": {"label": "patients", "format": "int"},
        "axis": "predicted risk",
        "highlight": min(count - 1, int(patient[key] // step)) if patient else None,
        "links": [{f"{key}_min": _pct(a), f"{key}_max": _pct(b)} for a, b in bands],
    }


def calibration(rows, model, patient=None, groups=10):
    """Observed rate against mean predicted risk in groups of equal size."""
    title = "Calibration"
    rows, patient = _scored(rows, model, patient)
    if not rows:
        return _empty("line", title)
    key = risk_key(model)
    points = toxage_risk.calibration(
        [r[key] for r in rows], [r[model.outcome] for r in rows], groups)
    top = nice_max(max([max(p, o) for p, o, _ in points] + ([patient[key]] if patient else [])))
    return {
        "type": "line",
        "title": title,
        "series": [{"name": f"observed, {len(points)} risk groups", "cls": "obs", "dots": True,
                    "points": [[_r(p), _r(o)] for p, o, _ in points]}],
        "x": {"label": "mean predicted risk", "format": "pct", "min": 0, "max": top},
        "y": {"label": "observed rate", "format": "pct", "min": 0, "max": top},
        "diagonal": True,
        "marker": {"x": _r(patient[key]), "label": "patient"} if patient else None,
    }


def incidence(rows, model, patient=None):
    """Cumulative incidence over the days after therapy start, per risk third."""
    title = "Cumulative incidence by risk group"
    rows, patient = _scored(rows, model, patient)
    if len(rows) < 3:
        return _empty("line", title)
    key = risk_key(model)
    ordered = sorted(rows, key=lambda r: r[key])
    n = len(ordered)
    thirds = [ordered[:n // 3], ordered[n // 3:2 * n // 3], ordered[2 * n // 3:]]
    cuts = [thirds[1][0][key], thirds[2][0][key]]
    names = [f"low (< {_pct(cuts[0]):.3g}%)",
             "middle",
             f"high (≥ {_pct(cuts[1]):.3g}%)"]
    mine = None if patient is None else sum(patient[key] >= c for c in cuts)
    series = []
    for i, (group, name, cls) in enumerate(zip(thirds, names, ("t1", "t2", "t3"))):
        days = sorted(r[model.onset] for r in group if r[model.outcome])
        points, total = [[0, 0]], 0
        for day in sorted(set(days)):
            total += days.count(day)
            points.append([day, _r(total / len(group))])
        points.append([model.window_days, _r(total / len(group))])
        label = f"{name}, patient's group" if i == mine else name
        series.append({"name": label, "cls": cls, "step": True, "points": points})
    top = nice_max(max(s["points"][-1][1] for s in series) or 0.01)
    onset = patient.get(model.onset) if patient else None
    return {
        "type": "line",
        "title": title,
        "series": series,
        "x": {"label": "day after therapy start", "format": "int", "min": 0,
              "max": model.window_days},
        "y": {"label": "share with event", "format": "pct", "min": 0, "max": top},
        "marker": {"x": onset, "label": f"patient, day {onset}"} if onset else None,
    }


def scatter(rows, x, y, outcome, patient=None, title=""):
    """Patients as points; x and y are (key, label, format) triples."""
    (xk, xl, xf), (yk, yl, yf) = x, y
    rows = [r for r in rows if r.get(xk) is not None and r.get(yk) is not None]
    if not rows:
        return _empty("scatter", title)
    shown = patient and patient.get(xk) is not None and patient.get(yk) is not None
    note = None
    if patient and not shown:
        # Say why the selected patient has no point here, instead of leaving it out silently.
        missing = next(label for key, label in ((xk, xl), (yk, yl)) if patient.get(key) is None)
        note = (f"Patient {patient['patient_id']} is not in this chart: the model "
                f"“{missing.removeprefix('risk: ')}” does not apply to this patient."
                if missing.startswith("risk: ") else
                f"Patient {patient['patient_id']} is not in this chart: no value for {missing}.")

    def axis(key, label, fmt):
        values = [r[key] for r in rows] + ([patient[key]] if shown else [])
        if fmt == "pct":
            return {"label": label, "format": fmt, "min": 0, "max": nice_max(max(values))}
        return {"label": label, "format": fmt, "min": min(values), "max": max(values)}

    return {
        "type": "scatter",
        "title": title,
        "points": [[_r(r[xk]), _r(r[yk]), int(bool(r[outcome])), r["patient_id"]] for r in rows],
        "classes": EVENT_CLASSES,
        "x": axis(xk, xl, xf),
        "y": axis(yk, yl, yf),
        "highlight": [_r(patient[xk]), _r(patient[yk]), patient["patient_id"]] if shown else None,
        "note": note,
    }


def summary(rows, model):
    """Key numbers of a model in a set of rows."""
    key = risk_key(model)
    rows = [r for r in rows if r[key] is not None]
    risks, events = [r[key] for r in rows], [r[model.outcome] for r in rows]
    return {
        "model": model,
        "n": len(rows),
        "events": sum(bool(e) for e in events),
        "observed": rate(rows, model.outcome),
        "predicted": mean(risks),
        "auc": toxage_risk.auc(risks, events),
        "brier": toxage_risk.brier(risks, events),
    }


def patient_risks(patient, rows, models):
    """Risk of the patient under every model, compared with the rows."""
    found = []
    for m in models:
        key = risk_key(m)
        risk = patient[key]
        factors = m.factors(patient)
        widest = max([abs(math.log(f.ratio)) for f in factors] + [math.log(2)])
        found.append({
            "model": m,
            "applies": risk is not None,
            "risk": risk,
            "reference": m.reference_risk(patient) if risk is not None else None,
            "percentile": percentile([r[key] for r in rows], risk),
            "observed": patient[m.outcome],
            "onset": patient.get(m.onset),
            "factors": [{
                "label": f.label,
                "ratio": f.ratio,
                "width": round(50 * abs(math.log(f.ratio)) / widest, 1),
                "up": f.ratio > 1,
            } for f in factors],
        })
    return found


def build(rows, patient, focus, models):
    """All chart sections of the explorer: [{title, note, charts: [(id, spec)]}]."""
    key = risk_key(focus)
    risk_axis = (key, f"risk: {focus.name}", "pct")
    sections = [{
        "title": f"Risk: {focus.name}",
        "note": "Predicted risk against the observed outcome. Click a bar to filter "
                "by risk band, a point to select a patient.",
        "charts": [
            ("risk-hist", risk_histogram(rows, focus, patient)),
            ("calibration", calibration(rows, focus, patient)),
            ("incidence", incidence(rows, focus, patient)),
            ("risk-age", scatter(rows, ("age_years", "age (years)", "int"), risk_axis,
                                 focus.outcome, patient, "Predicted risk by age")),
        ],
    }]
    others = [m for m in models if m is not focus]
    if others:
        sections.append({
            "title": "Risk across models",
            "note": f"Each point is a patient for whom both models give a risk. "
                    f"Colour: observed outcome of {focus.name}.",
            "charts": [(f"vs-{m.id}", scatter(
                rows, risk_axis, (risk_key(m), f"risk: {m.name}", "pct"), focus.outcome,
                patient, f"{focus.name} vs. {m.name}")) for m in others],
        })
    sections.append({
        "title": f"{focus.name} by patient characteristics",
        "note": "Observed rate and mean predicted risk per group, with the number of "
                "patients. Click a group to filter by it.",
        "charts": [(f"field-{f.name}", by_field(rows, f, focus, patient))
                   for f in fields("baseline")],
    })
    return sections
