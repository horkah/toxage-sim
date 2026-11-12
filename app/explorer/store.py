"""Writes generated data into the database."""
from django.db import transaction

from engine import generate as engine
from schema import toxage_schema

from . import cohort
from .models import Course, Dataset, Patient

KEYS = ("scenario_id", "patient_id")


def _strip(record):
    return {k: v for k, v in record.items() if k not in KEYS}


def _group(records):
    found = {}
    for r in records:
        found.setdefault((r["scenario_id"], r["patient_id"]), []).append(_strip(r))
    return found


def columns(rows):
    """Observation records of one course as one list per field."""
    names = [f for f in toxage_schema.fields("observation") if f not in KEYS]
    return {name: [r[name] for r in rows] for name in names}


def generate(n, seed, scenarios=None, replace=False):
    """Generate a data set with the engine and store it. Returns the Dataset."""
    data = engine.generate(n, seed, scenarios)
    events, alerts, observations = (_group(data[t]) for t in ("event", "alert", "observation"))
    with transaction.atomic():
        if replace:
            Dataset.objects.all().delete()
        dataset = Dataset.objects.create(metadata=data["metadata"], scenarios=data["scenario"])
        Patient.objects.bulk_create(
            [Patient(dataset=dataset, patient_id=b["patient_id"], baseline=b) for b in data["baseline"]],
            batch_size=500)
        keys = dict(dataset.patients.values_list("patient_id", "pk"))
        Course.objects.bulk_create((
            Course(
                patient_id=keys[o["patient_id"]],
                scenario_id=o["scenario_id"],
                outcome=_strip(o),
                events=events.get((o["scenario_id"], o["patient_id"]), []),
                alerts=alerts.get((o["scenario_id"], o["patient_id"]), []),
                observations=columns(observations.get((o["scenario_id"], o["patient_id"]), [])),
            )
            for o in data["outcome"]), batch_size=200)
    cohort.clear_cache()
    return dataset
