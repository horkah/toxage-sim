"""Pages next to the explorer: data sets, parameters, schema, documents."""
from functools import wraps

from django.conf import settings
from django.http import Http404, HttpResponseForbidden, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from schema import toxage_schema

from . import cohort, docs, params, store
from .models import Dataset

PAGE = 50
MAX_PATIENTS = 20000


def changes_data(view):
    """Views that change data or parameters are closed in read-only mode."""
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if settings.READ_ONLY:
            return HttpResponseForbidden("The app runs in read-only mode.")
        return view(request, *args, **kwargs)
    return wrapped


def _int(text, default, low, high):
    try:
        return max(low, min(high, int(text)))
    except (TypeError, ValueError):
        return default


# Data sets -----------------------------------------------------------------------

def data(request):
    store.mark_interrupted()
    datasets = list(Dataset.objects.all())
    active = cohort.active(request)
    changed = params.all_changes()
    size = store.database_size()
    for d in datasets:
        d.record_counts = [(s["scenario_id"], s["title"], d.metadata.get("records", {}).get(s["scenario_id"], {}))
                           for s in d.scenarios]
        d.changed = sum(len(v) for v in d.settings.values())
    return render(request, "explorer/data.html", {
        "section": "data",
        "datasets": datasets,
        "active": active,
        "running": any(d.status == Dataset.RUNNING for d in datasets),
        "scenarios": params.effective("interventions")["scenarios"],
        "changed": {params.SOURCES[k].title: len(v) for k, v in changed.items() if k in params.ENGINE},
        "needs_calibration": params.needs_calibration(changed),
        "size_mb": None if size is None else size / 1e6,
        "max_patients": MAX_PATIENTS,
        "read_only": settings.READ_ONLY,
    })


@require_POST
@changes_data
def data_generate(request):
    n = _int(request.POST.get("n"), 1500, 3, MAX_PATIENTS)
    seed = _int(request.POST.get("seed"), 1, 0, 2**31 - 1)
    store.generate(n, seed, request.POST.getlist("scenarios"), request.POST.get("name", ""),
                   recalibrate=request.POST.get("recalibrate") == "yes")
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


def _table(request):
    table = request.GET.get("table")
    return table if table in store.TABLES else "baseline"


def records(request, pk):
    """Records of one table of a data set, page by page."""
    dataset = get_object_or_404(Dataset, pk=pk, status=Dataset.READY)
    table = _table(request)
    scenario = cohort.scenario(dataset, request.GET.get("scenario"))
    patient_id = cohort.normalise_id(request.GET.get("patient"))
    page = _int(request.GET.get("page"), 1, 1, 10**9)
    spec = toxage_schema.load(table)["properties"]
    fields = [(name, spec[name].get("title", name), spec[name].get("unit", "")) for name in spec]
    found, more = [], False
    for i, record in enumerate(store.records(dataset, table, scenario["scenario_id"], patient_id or None)):
        if i >= page * PAGE:
            more = True
            break
        if i >= (page - 1) * PAGE:
            found.append([cohort.display(record.get(name)) for name, _, _ in fields])
    total = None if patient_id else store.count(dataset, table, scenario["scenario_id"])
    return render(request, "explorer/records.html", {
        "section": "data",
        "dataset": dataset, "table": table, "tables": store.TABLES, "scenario": scenario,
        "scenarios": dataset.scenarios, "patient_id": patient_id, "fields": fields, "rows": found,
        "page": page, "more": more, "total": total, "first": (page - 1) * PAGE + 1,
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
    if key not in params.SOURCES:
        raise Http404
    return params.SOURCES[key]


def parameters(request, key="parameters"):
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
        if not errors:
            return redirect(f"{reverse('parameters', args=[key])}?saved=1")
    changed = params.all_changes()
    return render(request, "explorer/parameters.html", {
        "section": "parameters",
        "source": source,
        "sources": [(s, len(changed.get(s.key, {}))) for s in params.SOURCES.values()],
        "groups": params.form(key, posted, errors),
        "errors": errors,
        "saved": request.GET.get("saved") == "1",
        "changed_here": len(changed.get(key, {})),
        "changed_total": sum(len(v) for v in changed.values()),
        "is_engine": key in params.ENGINE,
        "read_only": settings.READ_ONLY,
    })


# Schema and documents ------------------------------------------------------------

def schema(request):
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
                       "description": spec["description"], "fields": fields})
    return render(request, "explorer/schema.html", {
        "section": "schema","tables": tables})


def documents(request, key=None):
    if key is None:
        return render(request, "explorer/documents.html", {
        "section": "documents","groups": docs.groups()})
    if key not in docs.DOCUMENTS:
        raise Http404
    document = docs.DOCUMENTS[key]
    html, headings = docs.page(document)
    return render(request, "explorer/document.html", {
        "section": "documents",
        "document": document, "html": html, "groups": docs.groups(),
        "headings": [h for h in headings if h[0] == 2],
    })
