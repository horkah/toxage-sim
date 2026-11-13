"""Server side of the tutorial and the demo.

The tour itself runs in the browser (static/explorer/tour.js). The demo
changes parameters and creates data sets. Before it starts, the server keeps
a snapshot of what could change; when the demo ends or is stopped, the server
brings exactly this state back: the stored parameter changes, the set of data
sets, and the data set chosen for the explorer.
"""
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from . import cohort, params, store
from .models import Dataset, Setting

SNAPSHOT = "tour_snapshot"


def has_snapshot():
    return Setting.objects.filter(pk=SNAPSHOT).exists()


def context(request):
    """Values that every page needs: the tour state, the mode, the version."""
    from toxage_app.version import BUILD, VERSION
    return {"tour_snapshot": has_snapshot(), "read_only": settings.READ_ONLY,
            "app_version": VERSION, "app_build": BUILD, "repository": settings.REPOSITORY_URL,
            "time_zone": settings.TIME_ZONE}


def state(request):
    """What the tour needs to know to wait for results."""
    store.mark_interrupted()
    active = cohort.active(request)
    return JsonResponse({
        "datasets": [{"id": d.pk, "name": d.name, "status": d.status,
                      "scenarios": [s["scenario_id"] for s in d.scenarios]}
                     for d in Dataset.objects.all()],
        "active": active.pk if active else None,
        "changes": {key: len(value) for key, value in params.all_changes().items()},
        "snapshot": has_snapshot(),
        "read_only": settings.READ_ONLY,
    })


def take_snapshot(request):
    """Keep the state that a demo could change. An existing snapshot stays,
    because it holds the state before an earlier, unfinished demo."""
    if has_snapshot():
        return False
    Setting.objects.create(pk=SNAPSHOT, value={
        "settings": params.all_changes(),
        "datasets": list(Dataset.objects.values_list("pk", flat=True)),
        "cookie": request.COOKIES.get(cohort.DATASET_COOKIE),
    })
    return True


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
    if settings.READ_ONLY:
        return JsonResponse({"read_only": True, "taken": False})
    return JsonResponse({"read_only": False, "taken": take_snapshot(request)})


@require_POST
def restore(request):
    cookie = restore_snapshot()
    response = JsonResponse({"restored": cookie is not False})
    if cookie is False:
        return response
    if cookie:
        response.set_cookie(cohort.DATASET_COOKIE, cookie, max_age=365 * 86400, samesite="Lax")
    else:
        response.delete_cookie(cohort.DATASET_COOKIE, samesite="Lax")
    return response
