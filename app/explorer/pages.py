"""Pages next to the explorer: data sets, archive, parameters, reference."""
from functools import wraps

from django.conf import settings
from django.http import Http404, HttpResponseForbidden, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from schema import toxage_schema

from . import archive, cohort, docs, params, store
from .models import Dataset

PAGE = 50
MAX_PATIENTS = 20000


def changes_data(view):
    """Views that change data or parameters are closed in read-only mode."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        """The view itself, or 403 in read-only mode."""
        if settings.READ_ONLY:
            return HttpResponseForbidden("The app runs in read-only mode.")
        return view(request, *args, **kwargs)
    return wrapped


def fetched(request):
    """True for requests of the page script, which swaps the page in place
    and needs no redirect after a change."""
    return request.headers.get("X-Toxage-Fetch") == "1"


def _int(text, default, low, high):
    """A whole number from a form or query value, limited to [low, high]; default if
    it is not a number."""
    try:
        return max(low, min(high, int(text)))
    except (TypeError, ValueError):
        return default


# Data sets -----------------------------------------------------------------------

def _changed_list(changes):
    """Changed parameters of a data set: [(source, path label, value, anchor)]."""
    found = []
    for key, changed in changes.items():
        source = params.SOURCES.get(key)
        for path, value in changed.items():
            found.append((source.title if source else key, key, path.replace(params.SEP, " › ").replace("_", " "),
                          params.show(value), params.anchor(path)))
    return found


def data(request, message=None, error=None, posted=None):
    """Page Data: stored data sets, the form to generate one, the archive. message
    and error come from an import."""
    store.mark_interrupted()
    datasets = list(Dataset.objects.all())
    active = cohort.active(request)
    changed = params.all_changes()
    size = store.used_bytes()
    for d in datasets:
        d.record_counts = [(s["scenario_id"], s["title"], d.metadata.get("records", {}).get(s["scenario_id"], {}))
                           for s in d.scenarios]
        d.changed_list = _changed_list(d.settings)
        d.changed = len(d.changed_list)
    return render(request, "explorer/data.html", {
        "section": "data",
        "datasets": datasets,
        "ready_count": sum(d.ready for d in datasets),
        "active": active,
        "running": any(d.status == Dataset.RUNNING for d in datasets),
        "scenarios": params.effective("interventions")["scenarios"],
        "changed": [(params.SOURCES[k].title, k, len(v)) for k, v in changed.items() if k in params.ENGINE],
        "needs_calibration": params.needs_calibration(changed),
        "size_mb": None if size is None else size / 1e6,
        "limit_mb": settings.DISK_LIMIT_MB,
        "free_bytes": None if size is None else max(0, store.limit_bytes() - size),
        "course_bytes": store.BYTES_PER_COURSE,
        "max_patients": MAX_PATIENTS,
        "read_only": settings.READ_ONLY,
        "message": message,
        "error": error,
        # The form keeps what was entered when a data set was refused.
        "form": {"name": posted.get("name", ""), "n": posted.get("n", "1500"), "seed": posted.get("seed", "1"),
                 "scenarios": posted.getlist("scenarios")} if posted
                else {"name": "", "n": "1500", "seed": "1", "scenarios": None},
    })


@require_POST
@changes_data
def data_generate(request):
    """Start generating a data set from the form; the page then follows the progress."""
    n = _int(request.POST.get("n"), 1500, 3, MAX_PATIENTS)
    seed = _int(request.POST.get("seed"), 1, 0, 2**31 - 1)
    try:
        store.generate(n, seed, request.POST.getlist("scenarios"), request.POST.get("name", ""),
                       recalibrate=request.POST.get("recalibrate") == "yes")
    except (store.Busy, store.TooLarge) as refused:
        return _data_page(request, error=str(refused), posted=request.POST)
    return redirect("data")


@require_POST
@changes_data
def data_delete(request):
    """Delete one data set, one scenario of it, or all data sets."""
    if request.POST.get("all") == "yes":
        store.delete_all()
        return redirect("data")
    dataset = get_object_or_404(Dataset, pk=_int(request.POST.get("dataset"), 0, 0, 2**31))
    scenario_id = request.POST.get("scenario")
    if scenario_id:
        store.delete_scenario(dataset, scenario_id)
    else:
        store.delete_dataset(dataset)
    return redirect("data")


@require_POST
def data_use(request):
    """Choose the data set that the explorer shows."""
    dataset = get_object_or_404(Dataset, pk=_int(request.POST.get("dataset"), 0, 0, 2**31), status=Dataset.READY)
    response = redirect("explorer")
    response.set_cookie(cohort.DATASET_COOKIE, str(dataset.pk), max_age=365 * 86400, samesite="Lax")
    return response


# Archive -------------------------------------------------------------------------

def archive_export(request, pk=None):
    """The whole app, or one data set, as an archive file that can be imported later."""
    dataset = get_object_or_404(Dataset, pk=pk, status=Dataset.READY) if pk is not None else None
    response = StreamingHttpResponse(archive.gzipped(archive.lines([dataset] if dataset else None)),
                                     content_type="application/gzip")
    response["Content-Disposition"] = f'attachment; filename="{archive.filename(dataset)}"'
    return response


def _data_page(request, **kwargs):
    """The data page as the answer to a form; it can be loaded again at /data/."""
    response = data(request, **kwargs)
    response["X-Toxage-Location"] = reverse("data")
    return response


@require_POST
@changes_data
def archive_import(request):
    """Import an uploaded archive, adding its data sets or replacing everything;
    errors are shown on the page."""
    upload = request.FILES.get("archive")
    if upload is None:
        return _data_page(request, error="Please choose an archive file.")
    replace = request.POST.get("mode") == "replace"
    try:
        result = archive.load(upload, replace=replace)
    except archive.ArchiveError as problem:
        return _data_page(request, error=f"The archive was not imported. {problem}")
    text = (f"Imported {result['datasets']} data set{'s' if result['datasets'] != 1 else ''} "
            f"with {result['patients']} patients")
    text += " and the parameter changes of the archive." if result["parameters"] else "."
    if fetched(request):
        return _data_page(request, message=text)
    return redirect("data")


def _table(request):
    """The table of the records page from the query, baseline if unknown."""
    table = request.GET.get("table")
    return table if table in store.TABLES else "baseline"


def records(request, pk):
    """Records of one table of a data set, page by page."""
    dataset = get_object_or_404(Dataset, pk=pk, status=Dataset.READY)
    table = _table(request)
    scenario = cohort.scenario(dataset, request.GET.get("scenario"))
    patient_id = cohort.normalise_id(request.GET.get("patient"))
    page = _int(request.GET.get("page"), 1, 1, 10**9)
    known = None if patient_id else store.count(dataset, table, scenario["scenario_id"])
    if known is not None:
        # A page beyond the end shows the last page instead of reading every record.
        page = min(page, max(1, -(-known // PAGE)))
    spec = toxage_schema.load(table)["properties"]
    fields = [(name, spec[name].get("title", name), spec[name].get("unit", "")) for name in spec]
    found, more = [], False
    for i, record in enumerate(store.records(dataset, table, scenario["scenario_id"], patient_id or None)):
        if i >= page * PAGE:
            more = True
            break
        if i >= (page - 1) * PAGE:
            found.append([cohort.display(record.get(name)) for name, _, _ in fields])
    total = known
    names = [name for name, _, _ in fields]
    return render(request, "explorer/records.html", {
        "patient_col": names.index("patient_id") if "patient_id" in names else -1,
        "scenario_col": names.index("scenario_id") if "scenario_id" in names else -1,
        "section": "data",
        "dataset": dataset, "table": table, "tables": store.TABLES, "scenario": scenario,
        "scenarios": dataset.scenarios, "patient_id": patient_id, "fields": fields, "rows": found,
        "page": page, "more": more, "total": total, "first": (page - 1) * PAGE + 1,
        "last": (page - 1) * PAGE + len(found),
        "by_scenario": table not in ("scenario", "baseline"),
        "by_patient": table != "scenario",
        "description": toxage_schema.load(table)["description"],
    })


def export(request, pk, table):
    """One table of a data set as CSV file, in the format of the central schema."""
    dataset = get_object_or_404(Dataset, pk=pk, status=Dataset.READY)
    if table not in store.TABLES:
        raise Http404
    wanted = request.GET.get("scenario")
    ids = [wanted] if wanted in cohort.scenario_ids(dataset) else cohort.scenario_ids(dataset)
    response = StreamingHttpResponse(store.csv_lines(dataset, table, ids), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="toxage-{dataset.pk}-{table}.csv"'
    return response


# Parameters ----------------------------------------------------------------------

def _source(key):
    """The parameter source of a key, 404 if unknown."""
    if key not in params.SOURCES:
        raise Http404
    return params.SOURCES[key]


def parameters(request, key="parameters"):
    """Page of one parameter file: shows the values, saves changes and resets them."""
    source = _source(key)
    posted, errors, saved = None, {}, False
    if request.method == "POST":
        if settings.READ_ONLY:
            return HttpResponseForbidden("The app runs in read-only mode.")
        action = request.POST.get("action", "save")
        if action == "reset_all":
            params.reset()
        elif action == "reset_source":
            params.reset(key)
        elif action.startswith("reset:"):
            params.reset(key, action[len("reset:"):])
        else:
            posted = {k[2:]: v for k, v in request.POST.items() if k.startswith("p:")}
            errors = params.save(key, posted)
        cohort.clear_cache()
        if not errors and not fetched(request):
            return redirect(f"{reverse('parameters', args=[key])}?saved=1")
        saved = not errors
    changed = params.all_changes()
    return render(request, "explorer/parameters.html", {
        "section": "parameters",
        "source": source,
        "sources": [(s, len(changed.get(s.key, {}))) for s in params.SOURCES.values()],
        "groups": params.form(key, posted, errors),
        "errors": errors,
        "saved": saved or request.GET.get("saved") == "1",
        "changed_here": len(changed.get(key, {})),
        "changed_total": sum(len(v) for v in changed.values()),
        "is_engine": key in params.ENGINE,
        "read_only": settings.READ_ONLY,
    })


# Reference: schema and documents -------------------------------------------------

def _reference(request, template, **context):
    """Render a page of the reference section with its side bar: schema tables and
    documents."""
    return render(request, template, {
        "section": "reference",
        "groups": docs.groups(),
        "tables": [(name, toxage_schema.load(name)["title"]) for name in toxage_schema.TABLES],
        "dataset": cohort.active(request),
        **context,
    })


def schema(request):
    """Page Data schema: every table and field of the central schema with type,
    values, unit and meaning."""
    tables = []
    for name in toxage_schema.TABLES:
        spec = toxage_schema.load(name)
        fields = []
        for key, f in spec["properties"].items():
            types = f.get("type", "string")
            types = " or ".join(types) if isinstance(types, list) else types
            if "enum" in f:
                values = ", ".join(str(v).replace("_", " ") for v in f["enum"] if v is not None)
            elif "minimum" in f and "maximum" in f:
                values = f"{f['minimum']} to {f['maximum']}"
            elif "minimum" in f:
                values = f"{f['minimum']} or more"
            else:
                values = ""
            fields.append({"name": key, "title": f.get("title", key), "type": types, "values": values,
                           "unit": f.get("unit", ""), "description": f.get("description", "")})
        tables.append({"name": name, "title": spec["title"], "version": spec["version"],
                       "description": spec["description"], "fields": fields,
                       "records": name in store.TABLES})
    return _reference(request, "explorer/schema.html", schema_tables=tables, page="schema")


def documents(request, key=None):
    """Reference overview without key, else one document rendered from Markdown with
    its headings."""
    if key is None:
        return _reference(request, "explorer/documents.html", page="index")
    if key not in docs.DOCUMENTS:
        raise Http404
    document = docs.DOCUMENTS[key]
    html, headings = docs.page(document)
    return _reference(request, "explorer/document.html", document=document, html=html, page=key,
                      headings=[h for h in headings if h[0] == 2])
