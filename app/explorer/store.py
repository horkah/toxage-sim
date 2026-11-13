"""Generates data sets with the engine, stores them, reads them back as
records of the central schema, and deletes them.

Generating takes seconds to minutes, so it runs in a thread of the server
process. The Dataset row carries the state and the progress.
"""
import csv
import io
import os
import threading
import traceback

from django.conf import settings
from django.db import connection, transaction

from engine import calibrate
from engine import generate as engine
from schema import toxage_schema

from . import cohort, params
from .models import Course, Dataset, Patient

KEYS = ("scenario_id", "patient_id")
TABLES = ("scenario", "baseline", "outcome", "event", "alert", "observation")
_RUNNING = set()     # data sets that a thread of this process is generating


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


def _counts(data):
    counts = {s["scenario_id"]: {"observation": 0, "event": 0, "alert": 0} for s in data["scenario"]}
    for table in ("observation", "event", "alert"):
        for r in data[table]:
            counts[r["scenario_id"]][table] += 1
    return counts


def _progress(pk, share, message):
    Dataset.objects.filter(pk=pk).update(progress=share, message=message)


def _fill(dataset, scenarios, recalibrate, config):
    """Generate the data of a data set and store them."""
    pk = dataset.pk
    if recalibrate:
        result = calibrate.calibrate(config, write=False, progress=lambda done, total: _progress(
            pk, 0.4 * done / total, f"Calibrating the event rates, round {done} of {total}"))
        config["calibration"] = result["factors"]
    else:
        _progress(pk, 0.4, "Simulating")
    data = engine.generate(dataset.n, dataset.seed, scenarios, validate=False, config=config,
                           progress=lambda done, total: _progress(
                               pk, 0.4 + 0.5 * done / total, f"Simulated {done} of {total} scenarios"))
    for table in ("scenario", "baseline", "event", "alert", "outcome"):
        toxage_schema.validate(table, data[table])
    _progress(pk, 0.9, "Storing")
    events, alerts, observations = (_group(data[t]) for t in ("event", "alert", "observation"))
    with transaction.atomic():
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
        Dataset.objects.filter(pk=pk).update(
            status=Dataset.READY, progress=1, message="", scenarios=data["scenario"],
            metadata={**data["metadata"], "records": _counts(data)}, calibrated=recalibrate)


def _run(dataset, scenarios, recalibrate, config, in_thread):
    try:
        _fill(dataset, scenarios, recalibrate, config)
    except Exception as error:     # the reason is shown to the user on the data page
        traceback.print_exc()
        Dataset.objects.filter(pk=dataset.pk).update(
            status=Dataset.FAILED, message=f"{type(error).__name__}: {error}"[:300])
    finally:
        _RUNNING.discard(dataset.pk)
        cohort.clear_cache()
        if in_thread:
            connection.close()


def generate(n, seed, scenarios=None, name="", recalibrate=None, replace=False, wait=None):
    """Create a data set and fill it with the engine and the current
    parameters. Returns the Dataset at once; it is ready when its status says
    so. With wait=True the call returns after the data set is filled.

    recalibrate=None calibrates the event rates again if parameters that
    affect them differ from the defaults.
    """
    changed = params.all_changes()
    config = params.engine_config(changed)
    scenarios = [s for s in (scenarios or []) if s in config["interventions"]["scenarios"]] or None
    if recalibrate is None:
        recalibrate = params.needs_calibration(changed)
    if replace:
        delete_all()
    dataset = Dataset.objects.create(
        name=name.strip()[:80] or f"{n} patients, seed {seed}", n=n, seed=seed,
        settings={k: v for k, v in changed.items() if k in params.ENGINE}, message="Starting")
    wait = not settings.ASYNC_JOBS if wait is None else wait
    _RUNNING.add(dataset.pk)
    if wait:
        _run(dataset, scenarios, recalibrate, config, False)
        dataset.refresh_from_db()
    else:
        threading.Thread(target=_run, args=(dataset, scenarios, recalibrate, config, True), daemon=True).start()
    return dataset


def mark_interrupted():
    """A data set that is 'running' without a thread of this process was cut
    off by a restart of the server."""
    Dataset.objects.filter(status=Dataset.RUNNING).exclude(pk__in=_RUNNING).update(
        status=Dataset.FAILED, message="Interrupted by a restart of the app")


# Deleting ---------------------------------------------------------------------

def compact():
    """Give the freed space back to the disk (SQLite keeps it otherwise)."""
    if connection.vendor == "sqlite" and not connection.in_atomic_block:
        with connection.cursor() as cursor:
            cursor.execute("VACUUM")


def delete_dataset(dataset):
    dataset.delete()
    cohort.clear_cache()
    compact()


def delete_scenario(dataset, scenario_id):
    """Delete one scenario of a data set. The last scenario stays."""
    left = [s for s in dataset.scenarios if s["scenario_id"] != scenario_id]
    if not left or len(left) == len(dataset.scenarios):
        return False
    with transaction.atomic():
        Course.objects.filter(patient__dataset=dataset, scenario_id=scenario_id).delete()
        dataset.scenarios = left
        dataset.metadata.get("records", {}).pop(scenario_id, None)
        dataset.metadata["scenarios"] = [s["scenario_id"] for s in left]
        dataset.save(update_fields=["scenarios", "metadata"])
    cohort.clear_cache()
    compact()
    return True


def delete_all():
    Dataset.objects.all().delete()
    cohort.clear_cache()
    compact()


def database_size():
    """Size of the database on disk in bytes, None if it is not a file."""
    name = str(connection.settings_dict["NAME"])
    if connection.vendor != "sqlite" or not os.path.exists(name):
        return None
    return sum(os.path.getsize(name + ext) for ext in ("", "-wal") if os.path.exists(name + ext))


# Reading records ----------------------------------------------------------------

def _courses(dataset, scenario_id, patient_id=None):
    found = Course.objects.filter(patient__dataset=dataset, scenario_id=scenario_id).order_by(
        "patient__patient_id")
    return found.filter(patient__patient_id=patient_id) if patient_id else found


def records(dataset, table, scenario_id=None, patient_id=None):
    """Records of one table of the central schema, as an iterator.

    scenario_id is needed for the tables that depend on the scenario,
    patient_id limits them to one patient.
    """
    if table == "scenario":
        yield from dataset.scenarios
    elif table == "baseline":
        found = dataset.patients.order_by("patient_id")
        if patient_id:
            found = found.filter(patient_id=patient_id)
        yield from found.values_list("baseline", flat=True).iterator()
    elif table == "outcome":
        for pid, outcome in _courses(dataset, scenario_id, patient_id).values_list(
                "patient__patient_id", "outcome").iterator():
            yield {"scenario_id": scenario_id, "patient_id": pid, **outcome}
    elif table in ("event", "alert"):
        for pid, found in _courses(dataset, scenario_id, patient_id).values_list(
                "patient__patient_id", f"{table}s").iterator():
            for r in found:
                yield {"scenario_id": scenario_id, "patient_id": pid, **r}
    elif table == "observation":
        for pid, obs in _courses(dataset, scenario_id, patient_id).values_list(
                "patient__patient_id", "observations").iterator():
            names = list(obs)
            for values in zip(*obs.values()):
                yield {"scenario_id": scenario_id, "patient_id": pid, **dict(zip(names, values))}
    else:
        raise ValueError(table)


def count(dataset, table, scenario_id=None):
    """Number of records of a table, None if unknown."""
    if table == "scenario":
        return len(dataset.scenarios)
    if table in ("baseline", "outcome"):
        return dataset.n
    return dataset.metadata.get("records", {}).get(scenario_id, {}).get(table)


def csv_lines(dataset, table, scenario_ids):
    """The records of a table as lines of a CSV file, for all given scenarios."""
    names = toxage_schema.fields(table)
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    def line(values):
        writer.writerow(values)
        text = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate()
        return text

    yield line(names)
    for scenario_id in scenario_ids if table not in ("scenario", "baseline") else [None]:
        for r in records(dataset, table, scenario_id):
            yield line(["" if r[n] is None else ("true" if r[n] else "false") if isinstance(r[n], bool) else r[n]
                        for n in names])
