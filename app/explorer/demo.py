"""Demo installation: every visitor works in a space of their own.

With settings.DEMO the data sets and parameter changes stored by the operator
are permanent: everyone sees them, nobody can delete or change them. A visitor
may still do everything the app offers: generate data sets within the limit of
the database, delete them, change parameters, import archives, run the
tutorial and the demo. All of it goes into the visitor's own space, which only
that browser sees, and which is emptied

- when the visitor reloads the page (the browser marks a reload with
  Cache-Control: max-age=0; a link or a new tab is no reload), and
- after settings.DEMO_IDLE_MINUTES without a request of that browser.

A browser is known by a session cookie. In a normal installation there is no
visitor: everything is permanent and shared, as stored.

Data sets of a space carry its id in Dataset.owner; parameter changes of a space
are stored as Setting "<file>@<id>" (params.py), the time of its last request
as Setting "visitor@<id>".
"""
import secrets
import time
from contextvars import ContextVar

from django.conf import settings
from django.db import transaction

from .models import Dataset, Setting

COOKIE = "toxage_visitor"
SEEN = "visitor@"
_current = ContextVar("visitor", default="")
_last_sweep = [0.0]


def visitor():
    """Id of the visitor of this request, "" outside a demo installation."""
    return _current.get()


def setting_key(key):
    """Key of a stored parameter file in the space of this request."""
    return f"{key}@{visitor()}" if visitor() else key


def visible(queryset=None):
    """The data sets this request may see: the permanent ones and its own."""
    queryset = Dataset.objects.all() if queryset is None else queryset
    return queryset.filter(owner__in=["", visitor()]) if visitor() else queryset


def removable(dataset):
    """True if this request may delete the data set or change it: always in a normal
    installation, only the visitor's own ones in a demo installation."""
    return not settings.DEMO or (bool(visitor()) and dataset.owner == visitor())


def empty(owner):
    """Remove everything of a visitor's space: data sets and parameter changes."""
    if not owner:
        return
    with transaction.atomic():
        Dataset.objects.filter(owner=owner).delete()
        Setting.objects.filter(pk__endswith=f"@{owner}").exclude(pk=SEEN + owner).delete()


def _forget(owner):
    """Empty a space and remove its record of activity."""
    empty(owner)
    Setting.objects.filter(pk=SEEN + owner).delete()


def sweep(now=None):
    """Empty the spaces without a request for settings.DEMO_IDLE_MINUTES. Runs at most
    once a minute."""
    now = time.time() if now is None else now
    if now - _last_sweep[0] < 60:
        return
    _last_sweep[0] = now
    limit = now - settings.DEMO_IDLE_MINUTES * 60
    for row in Setting.objects.filter(pk__startswith=SEEN):
        if row.value.get("at", 0) < limit:
            _forget(row.pk[len(SEEN):])
    # Data sets of spaces without a record (e.g. after a restart during a request).
    known = {k[len(SEEN):] for k in Setting.objects.filter(pk__startswith=SEEN).values_list("pk", flat=True)}
    for owner in set(Dataset.objects.exclude(owner="").values_list("owner", flat=True)) - known:
        _forget(owner)


def _seen(owner, now):
    """Note a request of the visitor; written at most every 30 seconds."""
    row = Setting.objects.filter(pk=SEEN + owner).first()
    if row is None or now - row.value.get("at", 0) > 30:
        Setting.objects.update_or_create(pk=SEEN + owner, defaults={"value": {"at": now}})


def is_reload(request):
    """True for a reload of a page by the user: a page request (not one of the page
    script, which sends X-Toxage-Fetch) that the browser marks as reload."""
    return (request.method == "GET" and request.headers.get("X-Toxage-Fetch") != "1"
            and request.headers.get("Sec-Fetch-Dest", "document") == "document"
            and "max-age=0" in request.headers.get("Cache-Control", "")
            and not request.path.startswith(("/static/", "/tour/")))


class VisitorMiddleware:
    """Give each browser of a demo installation its space, empty it on a reload of
    the page, and empty the spaces of idle visitors."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.DEMO or request.path.startswith("/static/"):
            return self.get_response(request)
        owner = request.COOKIES.get(COOKIE, "")
        fresh = not (len(owner) == 16 and all(c in "0123456789abcdef" for c in owner))
        if fresh:
            owner = secrets.token_hex(8)
        now = time.time()
        sweep(now)
        if not fresh and is_reload(request):
            empty(owner)
        _seen(owner, now)
        token = _current.set(owner)
        try:
            response = self.get_response(request)
        finally:
            _current.reset(token)
        if fresh:
            response.set_cookie(COOKIE, owner, samesite="Lax", httponly=True, secure=request.is_secure())
        return response


def context(request):
    """Template variables: demo (bool), the idle minutes."""
    return {"demo": settings.DEMO, "demo_idle_minutes": settings.DEMO_IDLE_MINUTES}
