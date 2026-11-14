"""Nothing of the app is shown before the user accepted the disclaimer and
licence terms. The acceptance is a cookie with the version of the terms."""
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse


def accepted(request):
    """True if the browser holds the cookie of the current version of the terms."""
    return request.COOKIES.get(settings.DISCLAIMER_COOKIE) == settings.DISCLAIMER_VERSION


class DisclaimerMiddleware:
    """Sends every request to the disclaimer until its terms were accepted; static
    files stay open."""
    def __init__(self, get_response):
        """Standard middleware: keep the next handler."""
        self.get_response = get_response

    def __call__(self, request):
        """Let accepted requests and the open paths through, redirect the others with
        ?next= to the disclaimer."""
        disclaimer = reverse("disclaimer")
        open_paths = (disclaimer, "/" + settings.STATIC_URL.lstrip("/"))
        if accepted(request) or request.path.startswith(open_paths):
            return self.get_response(request)
        return redirect(f"{disclaimer}?{urlencode({'next': request.get_full_path()})}")
