import random

from django.conf import settings
from django.http import QueryDict
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import charts, cohort, filters
from .middleware import accepted


def _query(query, **changes):
    """A query string with some parameters replaced or removed (None)."""
    query = query.copy()
    for key, value in changes.items():
        query.pop(key, None)
        if value is not None:
            query[key] = value
    return query.urlencode()


def explorer(request):
    data = cohort.current()
    if data is None:
        return render(request, "explorer/empty.html")
    dataset, models, rows = data

    specs = filters.specs(models)
    active = filters.parse(request.GET, specs)
    selection = filters.apply(rows, active)

    focus = next((m for m in models if m.id == request.GET.get("model")), models[0])
    wanted = cohort.normalise_id(request.GET.get("patient"))
    patient = cohort.find(rows, wanted) if wanted else None

    sections = charts.build(selection, patient, focus, models)
    return render(request, "explorer/explorer.html", {
        "dataset": dataset,
        "total": len(rows),
        "selection": len(selection),
        "models": models,
        "focus": focus,
        "summaries": [charts.summary(selection, m) for m in models],
        "filter_form": filters.form(specs, request.GET, active),
        "active_count": len(active),
        "patient": patient,
        "patient_id": wanted,
        "patient_in_selection": patient is not None and any(
            r["patient_id"] == patient["patient_id"] for r in selection),
        "patient_fields": [
            (f, cohort.display(patient[f.name], f.unit)) for f in cohort.fields()
        ] if patient else [],
        "patient_risks": charts.patient_risks(patient, selection, models) if patient else [],
        "sections": sections,
        "chart_data": {cid: spec for s in sections for cid, spec in s["charts"]},
        "keep": [(k, v) for k, values in request.GET.lists() if k != "patient"
                 for v in values],
        "model_links": [(m, _query(request.GET, model=m.id)) for m in models],
        "clear_patient": _query(request.GET, patient=None),
        "reset_filters": _query(QueryDict(), model=focus.id,
                                patient=patient["patient_id"] if patient else None),
    })


def random_patient(request):
    """Select a random patient of the current selection."""
    data = cohort.current()
    if data is None:
        return redirect("explorer")
    _, models, rows = data
    selection = filters.apply(rows, filters.parse(request.GET, filters.specs(models)))
    if not selection:
        return redirect(f"{reverse('explorer')}?{_query(request.GET, patient=None)}")
    chosen = random.choice(selection)["patient_id"]
    return redirect(f"{reverse('explorer')}?{_query(request.GET, patient=chosen)}")


def disclaimer(request):
    target = request.GET.get("next") or request.POST.get("next") or reverse("explorer")
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = reverse("explorer")
    error = False
    if request.method == "POST":
        if request.POST.get("accept") == "yes":
            response = redirect(target)
            remember = request.POST.get("remember") == "yes"
            response.set_cookie(
                settings.DISCLAIMER_COOKIE, settings.DISCLAIMER_VERSION,
                max_age=settings.DISCLAIMER_REMEMBER_DAYS * 86400 if remember else None,
                samesite="Lax", httponly=True, secure=request.is_secure())
            return response
        error = True
    return render(request, "explorer/disclaimer.html", {
        "next": target, "error": error, "accepted": accepted(request),
        "version": settings.DISCLAIMER_VERSION,
    })


@require_POST
def revoke(request):
    """Withdraw the acceptance, so that the disclaimer shows again."""
    response = redirect("disclaimer")
    response.delete_cookie(settings.DISCLAIMER_COOKIE, samesite="Lax")
    return response
