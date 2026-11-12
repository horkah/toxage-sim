import random

from django.conf import settings
from django.http import QueryDict
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

import toxage_risk

from . import charts, cohort, filters, timeline
from .middleware import accepted

VIEWS = [("risk", "Risk"), ("characteristics", "Patient characteristics"),
         ("time", "Course over time"), ("interventions", "Interventions")]
# Query parameters that are not filters.
STATE = ("patient", "model", "view", "scenario", "compare")


def _query(query, **changes):
    """A query string with some parameters replaced or removed (None)."""
    query = query.copy()
    for key, value in changes.items():
        query.pop(key, None)
        if value is not None:
            query[key] = value
    return query.urlencode()


def _load(request):
    """Data set, risk models, selected and comparison scenario, rows of the
    selected scenario; None without data."""
    dataset = cohort.newest()
    if dataset is None:
        return None
    models = toxage_risk.load()
    scenario = cohort.scenario(dataset, request.GET.get("scenario"))
    others = [s for s in dataset.scenarios if s["scenario_id"] != scenario["scenario_id"]]
    wanted = request.GET.get("compare")
    compare = next((s for s in others if s["scenario_id"] == wanted), None)
    if compare is None and wanted != "none" and scenario["scenario_id"] != cohort.USUAL_CARE:
        compare = next((s for s in others if s["scenario_id"] == cohort.USUAL_CARE), None)
    return dataset, models, scenario, compare, cohort.rows(dataset, scenario["scenario_id"], models)


def _time_sections(dataset, shown, ids, patient, models):
    """Sections of the view 'Course over time'. shown is the selected
    scenario and, if any, the comparison."""
    horizon = 7 * dataset.metadata["weeks"]
    named_rows = [(s["title"], [r for r in cohort.rows(dataset, s["scenario_id"], models)
                                if r["patient_id"] in ids]) for s in shown]
    named_days = [(s["title"], timeline.first_severe_days(
        cohort.events(dataset, s["scenario_id"]), ids)) for s in shown]
    sections = []
    if patient:
        courses = [(s["title"], cohort.course(dataset, s["scenario_id"], patient["patient_id"])) for s in shown]
        sections.append({
            "title": f"Patient {patient['patient_id']} over time",
            "note": "Weekly values while on therapy and shortly after. Vertical lines mark adverse events, "
                    "alerts and the end of therapy in the selected scenario; hover for details.",
            "charts": timeline.patient_charts(courses, patient),
            "events": [(name, timeline.event_rows(c)) for name, c in courses],
        })
    sections.append({
        "title": "Cohort over time",
        "note": "Share of the selected patients over the time since therapy start.",
        "charts": [
            ("time-severe", timeline.severe_incidence(named_days, horizon)),
            ("time-therapy", timeline.on_therapy(named_rows, horizon)),
            ("time-survival", timeline.survival(named_rows, horizon)),
        ],
    })
    return sections


def _intervention_sections(dataset, scenario, ids, models):
    """Sections of the view 'Interventions': all scenarios side by side."""
    sid = scenario["scenario_id"]
    events_of = lambda s: cohort.events(dataset, s)
    table = timeline.scenario_table(
        dataset.scenarios, lambda s: cohort.rows(dataset, s, models), events_of, ids)
    bars = timeline.scenario_bars
    sections = [{
        "title": "Scenarios side by side",
        "note": "The same patients under every scenario. Click a bar to select a scenario. "
                "Costs are placeholder values without the cancer drugs.",
        "table": table,
        "charts": [
            ("iv-severe", bars(table, "Severe toxicity within 90 days", [("patients", "sa", "severe_90d")],
                               "share of patients", "pct", sid)),
            ("iv-events", bars(table, "Severe adverse events", [("events", "sa", "severe_events")],
                               "events per patient", "num", sid)),
            ("iv-hospital", bars(table, "Hospital days", [("days", "sa", "hospital_days")],
                                 "days per patient", "num", sid)),
            ("iv-qaly", bars(table, "Quality-adjusted life years", [("QALY", "sa", "qaly")],
                             "years per patient", "num", sid)),
            ("iv-cost", bars(table, "Costs", [("care", "sb", "cost_care"), ("intervention", "sa", "cost_intervention")],
                             "euros per patient", "int", sid, stacked=True)),
            ("iv-lung", timeline.lung_grades(dataset.scenarios, events_of, ids, sid)),
        ],
    }]
    if sid != cohort.USUAL_CARE:
        sections.append({
            "title": f"Early recognition: {scenario['title']}",
            "note": "Adverse events that monitoring recognised before usual care would have.",
            "charts": [
                ("iv-lead", timeline.lead_time(events_of(sid), ids)),
                ("iv-grade", timeline.grade_shift(events_of(sid), ids)),
            ],
        })
    return sections


def explorer(request):
    data = _load(request)
    if data is None:
        return render(request, "explorer/empty.html")
    dataset, models, scenario, compare, rows = data
    shown = [scenario] + ([compare] if compare else [])

    specs = filters.specs(models)
    active = filters.parse(request.GET, specs)
    selection = filters.apply(rows, active)
    ids = {r["patient_id"] for r in selection}

    focus = next((m for m in models if m.id == request.GET.get("model")), models[0])
    view = request.GET.get("view") if request.GET.get("view") in dict(VIEWS) else "risk"
    wanted = cohort.normalise_id(request.GET.get("patient"))
    patient = cohort.find(rows, wanted) if wanted else None

    if view == "time":
        sections = _time_sections(dataset, shown, ids, patient, models)
    elif view == "interventions":
        sections = _intervention_sections(dataset, scenario, ids, models)
    else:
        built = charts.build(selection, patient, focus, models)
        sections = built[-1:] if view == "characteristics" else built[:-1]
    return render(request, "explorer/explorer.html", {
        "dataset": dataset,
        "total": len(rows),
        "selection": len(selection),
        "models": models,
        "focus": focus,
        "view": view,
        "scenario": scenario,
        "compare": compare,
        "scenarios": dataset.scenarios,
        "summaries": [charts.summary(selection, m) for m in models],
        "filter_form": filters.form(specs, request.GET, active),
        "active_count": len(active),
        "patient": patient,
        "patient_id": wanted,
        "patient_in_selection": patient is not None and patient["patient_id"] in ids,
        "patient_fields": [
            (f, cohort.display(patient[f.name], f.unit)) for f in cohort.fields()
        ] if patient else [],
        "patient_risks": charts.patient_risks(patient, selection, models) if patient else [],
        "sections": sections,
        "chart_data": {cid: spec for s in sections for cid, spec in s["charts"]},
        "keep": [(k, v) for k, values in request.GET.lists() if k != "patient"
                 for v in values],
        "keep_state": [(k, v) for k, values in request.GET.lists()
                       if k not in ("scenario", "compare") for v in values],
        "model_links": [(m, _query(request.GET, model=m.id)) for m in models],
        "view_links": [(key, label, _query(request.GET, view=key)) for key, label in VIEWS],
        "clear_patient": _query(request.GET, patient=None),
        "reset_filters": _query(
            QueryDict(), **{k: request.GET.get(k) for k in STATE if k not in ("patient", "model")},
            model=focus.id, patient=patient["patient_id"] if patient else None),
    })


def random_patient(request):
    """Select a random patient of the current selection."""
    data = _load(request)
    if data is None:
        return redirect("explorer")
    _, models, _, _, rows = data
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
