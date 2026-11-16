"""Server side of the tutorial and the demo.

The tour itself runs in the browser (static/explorer/tour.js). The demo
changes parameters and creates data sets. Before it starts, the server keeps
a snapshot of what could change; when the demo ends or is stopped, the server
brings exactly this state back: the stored parameter changes, the set of data
sets, and the data set chosen for the explorer.

Only one demo changes the app at a time. The browser that took the snapshot
holds its token in a cookie. A demo that has not started a new round for
DEMO_MINUTES is taken as abandoned, and the next request brings the state
before it back.

In a demo installation (explorer/demo.py) each visitor works in a space of
their own. There the demo needs no snapshot: it starts every round with an
empty space and empties it again at the end.
"""
import secrets
import time

from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from . import cohort, demo, params, store
from .models import Dataset, Setting

SNAPSHOT = "tour_snapshot"
DEMO_COOKIE = "toxage_demo"
DEMO_MINUTES = 60           # a round of the demo takes about 25 minutes at normal speed


def _snapshot():
    """The stored snapshot as a dictionary, or None."""
    row = Setting.objects.filter(pk=SNAPSHOT).first()
    return row.value if row else None


def _stale(saved):
    """True if the demo of this snapshot has not started a round for DEMO_MINUTES.
    Snapshots of older versions have no time and count as stale."""
    return time.time() - saved.get("taken_at", 0) > DEMO_MINUTES * 60


def _own(request, saved):
    """True if the request comes from the browser that took the snapshot."""
    token = request.COOKIES.get(DEMO_COOKIE)
    return bool(token) and secrets.compare_digest(token, saved.get("token", ""))


def restore_stale():
    """Bring the state before an abandoned demo back. Runs with every page."""
    if settings.DEMO:
        return
    saved = _snapshot()
    if saved is not None and _stale(saved):
        restore_snapshot()


def has_snapshot():
    """True if a demo noted the state of the app and has not restored it yet."""
    return Setting.objects.filter(pk=SNAPSHOT).exists()


def context(request):
    """Values that every page needs: the tour state, the mode, the version."""
    from toxage_app.version import BUILD, VERSION
    restore_stale()
    saved = _snapshot()
    # The note "a demo did not finish" is for the demo's own browser; the demo of
    # someone else is running, and abandoned ones were just restored.
    return {"tour_snapshot": saved is not None and _own(request, saved),
            "app_version": VERSION, "app_build": BUILD, "repository": settings.REPOSITORY_URL,
            "time_zone": settings.TIME_ZONE}


def state(request):
    """What the tour needs to know to wait for results."""
    store.mark_interrupted()
    active = cohort.active(request)
    return JsonResponse({
        "datasets": [{"id": d.pk, "name": d.name, "status": d.status,
                      "scenarios": [s["scenario_id"] for s in d.scenarios]}
                     for d in demo.visible()],
        "active": active.pk if active else None,
        "changes": {key: len(value) for key, value in params.all_changes().items()},
        "snapshot": has_snapshot(),
    })


def take_snapshot(request):
    """Keep the state that a demo could change and return the token of the demo,
    or None if another demo is running. An existing snapshot of the same
    browser or of an abandoned demo is restored first, so that every round
    starts from the state before the demo."""
    saved = _snapshot()
    if saved is not None:
        if not (_stale(saved) or _own(request, saved)):
            return None
        restore_snapshot()
    token = secrets.token_urlsafe(24)
    Setting.objects.create(pk=SNAPSHOT, value={
        "settings": params.all_changes(),
        "datasets": list(Dataset.objects.values_list("pk", flat=True)),
        "cookie": request.COOKIES.get(cohort.DATASET_COOKIE),
        "token": token,
        "taken_at": time.time(),
    })
    return token


def restore_snapshot():
    """Bring the state of the snapshot back. Returns the cookie value of the
    data set that was chosen then, or None; False without a snapshot."""
    snapshot = Setting.objects.filter(pk=SNAPSHOT).first()
    if snapshot is None:
        return False
    saved = snapshot.value
    with transaction.atomic():
        params.reset()
        for key, changed in saved["settings"].items():
            if key in params.SOURCES and changed:
                Setting.objects.create(pk=key, value=changed)
        Dataset.objects.exclude(pk__in=saved["datasets"]).delete()
        snapshot.delete()
    cohort.clear_cache()
    store.compact()
    return saved.get("cookie")


@require_POST
def snapshot(request):
    """POST: note the state before a demo (or a new round) and give this browser
    the demo's token. "taken" is False while another demo is running; this demo
    then leaves out the steps that change something. In a demo installation the
    visitor's space is emptied instead, and the demo may always change things."""
    if settings.DEMO:
        demo.empty(demo.visitor())
        return JsonResponse({"taken": True})
    token = take_snapshot(request)
    response = JsonResponse({"taken": token is not None})
    if token:
        response.set_cookie(DEMO_COOKIE, token, max_age=DEMO_MINUTES * 60, samesite="Lax", httponly=True,
                            secure=request.is_secure())
    return response


@require_POST
def restore(request):
    """POST: bring back the state noted before the demo, and the data set the browser
    had chosen then. Only the demo's own browser may do this, or anyone once the
    demo is abandoned; a running demo of someone else stays. In a demo installation:
    empty the visitor's space."""
    if settings.DEMO:
        demo.empty(demo.visitor())
        response = JsonResponse({"restored": True})
        response.delete_cookie(cohort.DATASET_COOKIE, samesite="Lax")
        return response
    saved = _snapshot()
    if saved is not None and not (_stale(saved) or _own(request, saved)):
        return JsonResponse({"restored": False, "busy": True})
    cookie = restore_snapshot()
    response = JsonResponse({"restored": cookie is not False})
    if cookie is False:
        return response
    if cookie:
        response.set_cookie(cohort.DATASET_COOKIE, cookie, max_age=365 * 86400, samesite="Lax")
    else:
        response.delete_cookie(cohort.DATASET_COOKIE, samesite="Lax")
    response.delete_cookie(DEMO_COOKIE, samesite="Lax")
    return response
