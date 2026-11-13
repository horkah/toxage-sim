"""Archive of the app's data: export to one file and import it again later.

An archive is a gzip-compressed text file with one JSON object per line
(JSON Lines). The lines in order:

  {"type": "archive", "format": "toxage-sim-archive", "format_version": 1, ...}
  {"type": "parameters", "changes": {source: {path: value}}}     whole-app archives only
  {"type": "dataset", "ref": 3, "name": ..., "n": ..., ...}
  {"type": "patient", "dataset": 3, "patient_id": ..., "baseline": {...},
   "courses": [{"scenario_id": ..., "outcome": {...}, "events": [...],
                "alerts": [...], "observations": {...}}]}
  ...
  {"type": "end", "datasets": 1, "patients": 1500}

The last line shows that the file is complete. Records keep the layout of the
central schema, so an archive can also be read without the app. Uncompressed
files with the same lines are accepted on import, too.
"""
import gzip
import io
import json
import zlib
from datetime import datetime, timezone

from django.db import transaction
from django.utils.dateparse import parse_datetime

from schema import toxage_schema
from toxage_app.version import BUILD, VERSION

from . import cohort, params, store
from .models import Course, Dataset, Patient, Setting

FORMAT = "toxage-sim-archive"
FORMAT_VERSION = 1
BATCH = 300


class ArchiveError(ValueError):
    """The file is not an archive of this app, or it is damaged."""


def _line(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n"


def lines(datasets=None):
    """The archive as text lines. datasets=None archives the whole app: all
    data sets that are ready and the changed parameters."""
    whole = datasets is None
    datasets = list(Dataset.objects.filter(status=Dataset.READY).order_by("created", "pk")
                    if whole else datasets)
    yield _line({
        "type": "archive", "format": FORMAT, "format_version": FORMAT_VERSION,
        "app_version": VERSION, "build": BUILD, "created": datetime.now(timezone.utc).isoformat(),
        "content": "app" if whole else "datasets",
        "schema_version": {t: toxage_schema.load(t)["version"] for t in toxage_schema.TABLES},
    })
    if whole:
        changes = {k: v for k, v in params.all_changes().items() if k in params.SOURCES}
        yield _line({"type": "parameters", "changes": changes})
    patients = 0
    for d in datasets:
        yield _line({
            "type": "dataset", "ref": d.pk, "name": d.name, "created": d.created.isoformat(),
            "n": d.n, "seed": d.seed, "metadata": d.metadata, "scenarios": d.scenarios,
            "settings": d.settings, "calibrated": d.calibrated,
        })
        courses = {}
        for pid, sid, outcome, events, alerts, obs in Course.objects.filter(patient__dataset=d).values_list(
                "patient_id", "scenario_id", "outcome", "events", "alerts", "observations").iterator():
            courses.setdefault(pid, []).append({"scenario_id": sid, "outcome": outcome, "events": events,
                                                "alerts": alerts, "observations": obs})
        for pk, patient_id, baseline in d.patients.order_by("patient_id").values_list(
                "pk", "patient_id", "baseline").iterator():
            patients += 1
            yield _line({"type": "patient", "dataset": d.pk, "patient_id": patient_id,
                         "baseline": baseline, "courses": courses.get(pk, [])})
    yield _line({"type": "end", "datasets": len(datasets), "patients": patients})


def gzipped(text_lines):
    """Compress text lines to a gzip stream, piece by piece."""
    packer = zlib.compressobj(6, zlib.DEFLATED, 31)
    buffer = []
    size = 0
    for text in text_lines:
        data = text.encode("utf-8")
        buffer.append(data)
        size += len(data)
        if size >= 1 << 18:
            out = packer.compress(b"".join(buffer))
            buffer, size = [], 0
            if out:
                yield out
    yield packer.compress(b"".join(buffer)) + packer.flush()


def filename(dataset=None):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    return f"toxage-sim-{'dataset-%d-' % dataset.pk if dataset else ''}{stamp}.jsonl.gz"


# Import ---------------------------------------------------------------------------------

def _reader(fileobj):
    """Text lines of an uploaded file, compressed or not."""
    head = fileobj.read(2)
    fileobj.seek(0)
    raw = gzip.GzipFile(fileobj=fileobj) if head == b"\x1f\x8b" else fileobj
    return io.TextIOWrapper(raw, encoding="utf-8")


def _records(fileobj):
    try:
        for number, text in enumerate(_reader(fileobj), 1):
            if text.strip():
                try:
                    yield number, json.loads(text)
                except json.JSONDecodeError:
                    raise ArchiveError(f"Line {number} is not valid JSON.") from None
    except (OSError, EOFError, UnicodeDecodeError) as error:
        raise ArchiveError(f"The file cannot be read: {error}") from None


def _check(table, records, where):
    for i, record in enumerate(records):
        found = toxage_schema.errors(table, record)
        if found:
            raise ArchiveError(f"{where}: {table} record does not fit the data schema: {'; '.join(found[:3])}")


class _Importer:
    def __init__(self):
        self.datasets = {}      # ref in the file -> Dataset
        self.patients = []      # pending (Patient, [course dicts])
        self.counts = {"datasets": 0, "patients": 0}

    def dataset(self, rec, number):
        try:
            d = Dataset.objects.create(
                name=str(rec["name"])[:80], n=int(rec["n"]), seed=int(rec["seed"]), status=Dataset.READY,
                progress=1, metadata=rec["metadata"], scenarios=rec["scenarios"],
                settings=rec.get("settings", {}), calibrated=bool(rec.get("calibrated")))
        except (KeyError, TypeError, ValueError) as error:
            raise ArchiveError(f"Line {number}: incomplete data set ({error}).") from None
        created = parse_datetime(str(rec.get("created", "")))
        if created:
            Dataset.objects.filter(pk=d.pk).update(created=created)
        self.datasets[rec.get("ref")] = d
        self.counts["datasets"] += 1

    def patient(self, rec, number):
        d = self.datasets.get(rec.get("dataset"))
        if d is None:
            raise ArchiveError(f"Line {number}: patient of an unknown data set.")
        try:
            baseline, courses = rec["baseline"], rec["courses"]
            outcomes = [{"scenario_id": c["scenario_id"], "patient_id": rec["patient_id"], **c["outcome"]}
                        for c in courses]
        except (KeyError, TypeError) as error:
            raise ArchiveError(f"Line {number}: incomplete patient record ({error}).") from None
        _check("baseline", [baseline], f"Line {number}")
        _check("outcome", outcomes, f"Line {number}")
        self.patients.append((Patient(dataset=d, patient_id=str(rec["patient_id"]), baseline=baseline), courses))
        self.counts["patients"] += 1
        if len(self.patients) >= BATCH:
            self.flush()

    def flush(self):
        if not self.patients:
            return
        created = Patient.objects.bulk_create([p for p, _ in self.patients])
        Course.objects.bulk_create([
            Course(patient=p, scenario_id=c["scenario_id"], outcome=c["outcome"], events=c.get("events", []),
                   alerts=c.get("alerts", []), observations=c.get("observations", {}))
            for p, (_, courses) in zip(created, self.patients) for c in courses])
        self.patients = []


def load(fileobj, replace=False):
    """Import an archive. With replace=True the data sets and parameter
    changes of the app are replaced by those of the archive; otherwise the
    data sets of the archive are added and the parameters stay as they are.
    Returns {"datasets": k, "patients": m, "parameters": bool}.
    Raises ArchiveError and leaves the app unchanged if the file is not a
    complete archive."""
    records = _records(fileobj)
    first = next(records, None)
    if first is None:
        raise ArchiveError("The file is empty.")
    _, header = first
    if not isinstance(header, dict) or header.get("format") != FORMAT:
        raise ArchiveError("The file is not an archive of toxage-sim.")
    if not isinstance(header.get("format_version"), int) or header["format_version"] > FORMAT_VERSION:
        raise ArchiveError(f"The archive has format version {header.get('format_version')}; "
                           f"this app reads up to version {FORMAT_VERSION}. Please update the app.")
    importer = _Importer()
    restored = False
    complete = False
    with transaction.atomic():
        if replace:
            Dataset.objects.all().delete()
            Setting.objects.filter(pk__in=params.SOURCES).delete()
        for number, rec in records:
            kind = rec.get("type") if isinstance(rec, dict) else None
            if complete:
                raise ArchiveError(f"Line {number}: data after the end of the archive.")
            if kind == "dataset":
                importer.flush()
                importer.dataset(rec, number)
            elif kind == "patient":
                importer.patient(rec, number)
            elif kind == "parameters":
                if replace:
                    for key, changed in (rec.get("changes") or {}).items():
                        if key in params.SOURCES and changed:
                            Setting.objects.create(pk=key, value=changed)
                    restored = True
            elif kind == "end":
                importer.flush()
                if (rec.get("datasets"), rec.get("patients")) != (
                        importer.counts["datasets"], importer.counts["patients"]):
                    raise ArchiveError("The archive is damaged: the number of records does not match.")
                complete = True
            else:
                raise ArchiveError(f"Line {number}: unknown record type {kind!r}.")
        if not complete:
            raise ArchiveError("The archive is incomplete: its last line is missing. "
                               "The file may have been cut off during the download.")
        for d in importer.datasets.values():
            if d.patients.count() != d.n:
                raise ArchiveError(f"The data set “{d.name}” has {d.patients.count()} instead of {d.n} patients.")
    cohort.clear_cache()
    store.compact()
    return {**importer.counts, "parameters": restored}
