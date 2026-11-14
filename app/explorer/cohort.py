"""The scored cohort: patient records of the newest data set together with
the risks of all registered risk models, and the field descriptions of the
central schema.

A row is the baseline record of a patient, the outcome record of one scenario
and the risks. The rows of a scenario are kept in memory after first use."""
import os
import threading
from collections import OrderedDict
from dataclasses import dataclass

import toxage_risk
from schema import toxage_schema

from . import courses, params
from .models import Course, Dataset

USUAL_CARE = "usual_care"
DATASET_COOKIE = "toxage_dataset"
# Rows and events of the scenarios used last, least recently used out. The
# limit counts patients over all entries: rows take about 5.5 KB and events
# about 1.3 KB per patient and scenario, so 60 000 patients are about 400 MB.
# One data set of 1500 patients under seven scenarios needs 2 x 10 500.
CACHE_PATIENTS = int(os.environ.get("TOXAGE_CACHE_PATIENTS", 60000))
_CACHE = OrderedDict()      # key -> (value, number of patients)
_CACHE_LOCK = threading.Lock()


def _cached(key, size, compute):
    """The value of key from the cache, else compute() it and keep it. The
    oldest entries leave when the cache holds more than CACHE_PATIENTS
    patients; the newest entry always stays, even if it alone is larger."""
    with _CACHE_LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
            return _CACHE[key][0]
    value = compute()       # outside the lock: other requests need not wait
    with _CACHE_LOCK:
        _CACHE[key] = (value, size)
        _CACHE.move_to_end(key)
        total = sum(n for _, n in _CACHE.values())
        while total > CACHE_PATIENTS and len(_CACHE) > 1:
            _, (_, n) = _CACHE.popitem(last=False)
            total -= n
    return value


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
    """Forget the stored rows and events, e.g. after a change of parameters or data."""
    with _CACHE_LOCK:
        _CACHE.clear()


def newest():
    """The newest data set that is ready."""
    return Dataset.objects.filter(status=Dataset.READY).first()


def active(request):
    """The data set that the user works with: the one chosen on the data
    page (kept in a cookie), else the newest."""
    chosen = request.GET.get("dataset") or request.COOKIES.get(DATASET_COOKIE)
    if chosen and str(chosen).isdigit():
        dataset = Dataset.objects.filter(pk=int(chosen), status=Dataset.READY).first()
        if dataset:
            return dataset
    return newest()


def risk_models():
    """The registered risk models with the parameters of the user."""
    return toxage_risk.load(params.effective("risk"))


def scenario_ids(dataset):
    """Ids of the scenarios of a data set, in their order."""
    return [s["scenario_id"] for s in dataset.scenarios]


def scenario(dataset, wanted):
    """The scenario record with the wanted id, or usual care, or the first."""
    by_id = {s["scenario_id"]: s for s in dataset.scenarios}
    return by_id.get(wanted) or by_id.get(USUAL_CARE) or dataset.scenarios[0]


def rows(dataset, scenario_id, models):
    """Baseline, outcome and risks of all patients in one scenario."""
    def compute():
        """Read baseline and outcome of every patient and add the risks."""
        pairs = courses.full_values(Course.objects.filter(patient__dataset=dataset, scenario_id=scenario_id).order_by(
            "patient__patient_id"), dataset, "patient__baseline", "outcome")
        return score([{**b, **o} for b, o in pairs], models)
    return _cached((dataset.pk, scenario_id, "rows"), dataset.n, compute)


def events(dataset, scenario_id):
    """Adverse events of one scenario as {patient_id: [event records]}."""
    return _cached((dataset.pk, scenario_id, "events"), dataset.n, lambda: dict(courses.full_values(
        Course.objects.filter(patient__dataset=dataset, scenario_id=scenario_id), dataset,
        "patient__patient_id", "events")))


def course(dataset, scenario_id, patient_id):
    """Events, alerts and weekly observations of one patient in one scenario, or None."""
    found = courses.full_values(Course.objects.filter(patient__dataset=dataset, patient__patient_id=patient_id,
                                                      scenario_id=scenario_id), dataset,
                                "events", "alerts", "observations").first()
    return dict(zip(("events", "alerts", "observations"), found)) if found else None


def current(scenario_id=USUAL_CARE):
    """Return (dataset, models, rows) of the newest data set, or None."""
    dataset = newest()
    if dataset is None:
        return None
    models = risk_models()
    return dataset, models, rows(dataset, scenario(dataset, scenario_id)["scenario_id"], models)


def normalise_id(text):
    """Turn user input into a patient ID: " 42 " and "p000042" give "P000042"."""
    text = (text or "").strip().upper()
    if text.isdigit():
        return f"P{int(text):06d}"
    return text


def find(rows, patient_id):
    """The row of one patient, or None."""
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
