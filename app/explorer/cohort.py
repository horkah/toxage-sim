"""The scored cohort: patient records of the newest data set together with
the risks of all registered risk models, and the field descriptions of the
central schema.

A row is the baseline record of a patient, the outcome record of one scenario
and the risks. The rows of a scenario are kept in memory after first use."""
from dataclasses import dataclass

import toxage_risk
from schema import toxage_schema

from .models import Course, Dataset

USUAL_CARE = "usual_care"
_CACHE = {}


@dataclass(frozen=True)
class Field:
    """One field of the central schema, as the app needs it."""
    name: str
    label: str
    table: str
    kind: str              # "choice", "bool" or "number"
    choices: tuple = ()
    unit: str = ""
    nullable: bool = False
    minimum: float = None
    maximum: float = None
    integer: bool = False


# Tables of the central schema with one record per patient, which the app shows.
TABLES = ("baseline", "outcome")


def fields(table=None):
    """Fields of one table, or of all tables that the app shows, in schema
    order. Free text fields such as patient_id are left out."""
    found = []
    for name in TABLES if table is None else (table,):
        for key, spec in toxage_schema.load(name)["properties"].items():
            types = spec.get("type", [])
            types = [types] if isinstance(types, str) else types
            if "enum" in spec:
                kind = "choice"
            elif "boolean" in types:
                kind = "bool"
            elif {"integer", "number"} & set(types):
                kind = "number"
            else:
                continue
            found.append(Field(
                name=key,
                label=spec.get("title", key),
                table=name,
                kind=kind,
                choices=tuple(spec.get("enum", ())),
                unit=spec.get("unit", ""),
                nullable="null" in types,
                minimum=spec.get("minimum"),
                maximum=spec.get("maximum"),
                integer="integer" in types,
            ))
    return found


def risk_key(model):
    """Key of the risk of a model in a row."""
    return f"risk_{model.id}"


def score(records, models):
    """Add the risk of every model to each record."""
    return [{**r, **{risk_key(m): m.risk(r) for m in models}} for r in records]


def clear_cache():
    _CACHE.clear()


def newest():
    return Dataset.objects.order_by("-created", "-pk").first()


def scenario_ids(dataset):
    return [s["scenario_id"] for s in dataset.scenarios]


def scenario(dataset, wanted):
    """The scenario record with the wanted id, or usual care, or the first."""
    by_id = {s["scenario_id"]: s for s in dataset.scenarios}
    return by_id.get(wanted) or by_id.get(USUAL_CARE) or dataset.scenarios[0]


def rows(dataset, scenario_id, models):
    """Baseline, outcome and risks of all patients in one scenario."""
    key = (dataset.pk, scenario_id, "rows")
    if key not in _CACHE:
        pairs = Course.objects.filter(patient__dataset=dataset, scenario_id=scenario_id).order_by(
            "patient__patient_id").values_list("patient__baseline", "outcome")
        _CACHE[key] = score([{**b, **o} for b, o in pairs], models)
    return _CACHE[key]


def events(dataset, scenario_id):
    """Adverse events of one scenario as {patient_id: [event records]}."""
    key = (dataset.pk, scenario_id, "events")
    if key not in _CACHE:
        _CACHE[key] = dict(Course.objects.filter(
            patient__dataset=dataset, scenario_id=scenario_id).values_list("patient__patient_id", "events"))
    return _CACHE[key]


def course(dataset, scenario_id, patient_id):
    """Events, alerts and weekly observations of one patient in one scenario, or None."""
    return Course.objects.filter(patient__dataset=dataset, patient__patient_id=patient_id,
                                 scenario_id=scenario_id).values("events", "alerts", "observations").first()


def current(scenario_id=USUAL_CARE):
    """Return (dataset, models, rows) of the newest data set, or None."""
    dataset = newest()
    if dataset is None:
        return None
    models = toxage_risk.load()
    return dataset, models, rows(dataset, scenario(dataset, scenario_id)["scenario_id"], models)


def normalise_id(text):
    """Turn user input into a patient ID: " 42 " and "p000042" give "P000042"."""
    text = (text or "").strip().upper()
    if text.isdigit():
        return f"P{int(text):06d}"
    return text


def find(rows, patient_id):
    return next((r for r in rows if r["patient_id"] == patient_id), None)


def display(value, unit=""):
    """Readable form of a field value."""
    if value is None:
        return "–"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, str):
        return value.replace("_", " ")
    if isinstance(value, float):
        value = f"{value:.1f}"
    return f"{value} {unit}".strip() if unit and unit != "%" else f"{value}{unit}"
