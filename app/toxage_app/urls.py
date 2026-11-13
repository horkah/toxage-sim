from django.contrib.staticfiles.views import serve
from django.urls import include, path, re_path


def static(request, path):
    """A static file of the app. "no-cache" makes the browser ask every time
    whether the file changed (an unchanged file costs a short 304 answer).
    Without it browsers keep a file by their own guess, possibly for days,
    and run an old script after a new build."""
    response = serve(request, path, insecure=True)
    response["Cache-Control"] = "no-cache"
    return response


urlpatterns = [
    path("", include("explorer.urls")),
    # The few static files are served by the app itself, also without DEBUG,
    # so that the container needs no second server.
    re_path(r"^static/(?P<path>.*)$", static),
]
