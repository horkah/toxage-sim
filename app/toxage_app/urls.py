from django.contrib.staticfiles.views import serve
from django.urls import include, path, re_path

urlpatterns = [
    path("", include("explorer.urls")),
    # The few static files are served by the app itself, also without DEBUG,
    # so that the container needs no second server.
    re_path(r"^static/(?P<path>.*)$", serve, {"insecure": True}),
]
