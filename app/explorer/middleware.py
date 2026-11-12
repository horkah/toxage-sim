"""Nothing of the app is shown before the user accepted the disclaimer and
licence terms. The acceptance is a cookie with the version of the terms."""
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


def accepted(request):
    return request.COOKIES.get(settings.DISCLAIMER_COOKIE) == settings.DISCLAIMER_VERSION


class DisclaimerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        disclaimer = reverse("disclaimer")
        open_paths = (disclaimer, "/" + settings.STATIC_URL.lstrip("/"))
        if accepted(request) or request.path.startswith(open_paths):
            return self.get_response(request)
        return redirect(f"{disclaimer}?{urlencode({'next': request.get_full_path()})}")
