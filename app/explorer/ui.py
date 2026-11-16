"""The simple view of the app.

With settings.SIMPLE_UI (TOXAGE_SIMPLE_UI=1) the app opens in a simple view
that shows the essence of the data with less to read and to choose: three
views of the explorer with their most telling charts, a few filters, and a
data set made from the number of patients alone. Data, models and
calculations are the same as in the full view; only what is shown and offered
is smaller. A browser can switch to the full view, "Advanced", in the
settings (cookie COOKIE); the tours use the full view while they run.
"""
from django.conf import settings

COOKIE = "toxage_ui"

# Views of the explorer, and the charts shown in them (by id).
VIEWS = ("risk", "time", "interventions")
CHARTS = {
    # Risk: how well the model separates and how well it is calibrated.
    "risk-hist", "calibration", "incidence",
    # One patient over time: dose, blood counts, lung, what the patient reports.
    "patient-dose", "patient-neutrophils", "patient-spo2", "patient-symptoms",
    # Interventions: the outcomes that differ most between the scenarios.
    "iv-severe", "iv-hospital", "iv-cost",
    "tte-sfs", "tte-severe", "tte-toxstop", "tte-os",
    "iv-lead", "iv-grade",
}
# Filters: tumour type, age, performance status, and the risk of the chosen model.
FILTERS = ("tumour_type", "age_years", "ecog")
# Endpoints of the table "Survival and time to event", one measure each.
ENDPOINTS = ("Overall survival", "Survival without severe toxicity", "First severe adverse event",
             "End of therapy for toxicity")


def simple(request):
    """True if this request gets the simple view."""
    return settings.SIMPLE_UI and request.COOKIES.get(COOKIE) != "advanced"


def filter_keys(focus):
    """Keys of the filters of the simple view, with the risk of the chosen model."""
    return set(FILTERS) | {f"risk_{focus.id}"}


def slim(sections):
    """The sections of a view with the charts of the simple view only; sections
    left without charts, table or events go."""
    out = []
    for s in sections:
        charts = [(cid, spec) for cid, spec in s["charts"] if cid in CHARTS]
        if charts or s.get("table") or s.get("events") or s.get("endpoints") or s.get("link"):
            out.append({**s, "charts": charts})
    return out


def context(request):
    """Template variables: simple (this request), simple_ui (the installation offers it)."""
    return {"simple": simple(request), "simple_ui": settings.SIMPLE_UI}
