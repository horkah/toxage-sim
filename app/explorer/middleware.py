""""Gates and launch parameters of the app.

Nothing of the app is shown before the user accepted the disclaimer and licence
terms; the acceptance is a cookie with the version of the terms. The exception is
?demo=1, which accepts the terms for the session so a kiosk can run the demo
unattended. After the gate, LaunchMiddleware turns the launch parameters of a
URL (?ui= and ?demo=) into the cookie and the browser trigger that hold the
choice, so the parameters do not linger in links and forms.
"""
from urllib.parse import urlencode

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

from . import ui


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
        ?next= to the disclaimer. ?demo=1 accepts the terms for the session, so a
        kiosk can start the demo without a click on the disclaimer."""
        disclaimer = reverse("disclaimer")
        open_paths = (disclaimer, "/" + settings.STATIC_URL.lstrip("/"))
        if accepted(request) or request.path.startswith(open_paths):
            return self.get_response(request)
        # ?demo=1 starts the demo in the browser (tour.js). Visitors who call it
        # are taken to know the terms, and may be at a kiosk without a keyboard
        # or mouse to click through the disclaimer, so it is accepted for them
        # for the session. The cookie lets the demo's later requests through too.
        if request.GET.get("demo") == "1":
            response = self.get_response(request)
            response.set_cookie(settings.DISCLAIMER_COOKIE, settings.DISCLAIMER_VERSION,
                                samesite="Lax", httponly=True, secure=request.is_secure())
            return response
        return redirect(f"{disclaimer}?{urlencode({'next': request.get_full_path()})}")


class LaunchMiddleware:
    """Turn the launch parameters of a URL into what holds the choice.

    ?ui=advanced|simple selects the view on a SIMPLE_UI installation and goes
    into the cookie (toxage_ui) that the Settings toggle also writes; the
    parameter is dropped from the URL with a redirect, so it does not turn up in
    links and forms. ?demo=1 starts the demo in the browser (tour.js); the
    parameter is kept out of the query string the views build on, for the same
    reason, and the browser keeps it long enough to start the demo.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ui_param = request.GET.get("ui")
        if request.method == "GET" and ui_param is not None:
            query = request.GET.copy()
            del query["ui"]
            target = request.path + (("?" + query.urlencode()) if query else "")
            response = redirect(target)
            if settings.SIMPLE_UI and ui_param == "advanced":
                response.set_cookie(ui.COOKIE, "advanced", max_age=31536000,
                                     samesite="Lax", httponly=True, secure=request.is_secure())
            elif settings.SIMPLE_UI and ui_param == "simple":
                response.delete_cookie(ui.COOKIE, samesite="Lax")
            return response
        # ?demo=1 is read in the browser (tour.js); kept out of links and forms.
        if "demo" in request.GET:
            request.GET = request.GET.copy()
            del request.GET["demo"]
        return self.get_response(request)
