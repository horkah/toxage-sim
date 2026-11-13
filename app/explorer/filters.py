"""Cohort filters. They are built from the central schema and the registered
risk models, so new fields and new models get a filter without code changes.

A filter is read from the query string:
  choice  field=a&field=b       keep rows whose value is one of them
  bool    field=true|false
  number  field_min=&field_max= bounds included; rows without a value drop out
Risks are entered in percent.
"""
import math
from dataclasses import dataclass

from .cohort import fields, risk_key

GROUPS = {"baseline": "Patient", "outcome": "Outcome"}


@dataclass(frozen=True)
class Filter:
    key: str
    label: str
    group: str
    kind: str
    choices: tuple = ()
    unit: str = ""
    scale: float = 1.0     # factor between the entered value and the stored value


def specs(models):
    found = [
        Filter(f.name, f.label, GROUPS[f.table], f.kind, f.choices, f.unit)
        for f in fields()
    ]
    found += [
        Filter(risk_key(m), m.name, "Risk", "number", unit="%", scale=100)
        for m in models
    ]
    return found


def _number(text):
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def parse(query, filter_specs):
    """Return the active conditions {key: condition} of a QueryDict."""
    active = {}
    for f in filter_specs:
        if f.kind == "choice":
            chosen = {c for c in f.choices if c in query.getlist(f.key)}
            if chosen:
                active[f.key] = chosen
        elif f.kind == "bool":
            if query.get(f.key) in ("true", "false"):
                active[f.key] = query.get(f.key) == "true"
        else:
            low, high = _number(query.get(f"{f.key}_min")), _number(query.get(f"{f.key}_max"))
            if low is not None or high is not None:
                active[f.key] = (
                    None if low is None else low / f.scale,
                    None if high is None else high / f.scale,
                )
    return active


def matches(row, active):
    for key, condition in active.items():
        value = row.get(key)
        if isinstance(condition, set):
            if value not in condition:
                return False
        elif isinstance(condition, bool):
            if value is not condition:
                return False
        else:
            low, high = condition
            if value is None or (low is not None and value < low) or (
                    high is not None and value > high):
                return False
    return True


def apply(rows, active):
    return [r for r in rows if matches(r, active)]


def form(filter_specs, query, active):
    """Filters grouped for the form, in spec order:
    [{"name": group, "entries": [entry], "active": any entry active}]."""
    groups = {}
    for f in filter_specs:
        entry = {"spec": f, "active": f.key in active}
        if f.kind == "choice":
            entry["selected"] = set(query.getlist(f.key))
        elif f.kind == "bool":
            entry["value"] = query.get(f.key, "")
        else:
            entry["min"] = query.get(f"{f.key}_min", "")
            entry["max"] = query.get(f"{f.key}_max", "")
        groups.setdefault(f.group, []).append(entry)
    return [{"name": name, "entries": entries, "active": any(e["active"] for e in entries)}
            for name, entries in groups.items()]


def _bound(value):
    return f"{value:g}"


def chips(filter_specs, query, active):
    """The active filters as short texts, in spec order:
    [{"key", "label", "value", "keys": query keys that hold the filter}]."""
    from .cohort import display
    found = []
    for f in filter_specs:
        if f.key not in active:
            continue
        condition = active[f.key]
        if f.kind == "choice":
            value = ", ".join(display(c) for c in f.choices if c in condition)
            keys = [f.key]
        elif f.kind == "bool":
            value = "yes" if condition else "no"
            keys = [f.key]
        else:
            low, high = (None if b is None else b * f.scale for b in condition)
            unit = f" {f.unit}" if f.unit and f.unit != "%" else f.unit
            if low is not None and high is not None:
                value = _bound(low) if low == high else f"{_bound(low)}–{_bound(high)}"
            elif low is not None:
                value = f"≥ {_bound(low)}"
            else:
                value = f"≤ {_bound(high)}"
            value += unit
            keys = [f"{f.key}_min", f"{f.key}_max"]
        found.append({"key": f.key, "label": f.label, "value": value, "keys": keys})
    return found
