"""The name of the app as the user sees it.

The project and everything under the hood is called toxage-sim. A demo
installation (settings.DEMO, explorer/demo.py) shows itself as toxage-sim-demo. Templates
get the name as app_name for plain text and app_name_tail for the coloured
part next to the logo (template explorer/brand_name.html).
"""
from django.conf import settings

BASE = "toxage"


def tail():
    """The coloured part of the name: -sim, or -sim-demo in a demo installation."""
    return "-sim-demo" if settings.DEMO else "-sim"


def name():
    """The full name, e.g. toxage-sim-demo."""
    return BASE + tail()


def context(request):
    """Template variables app_name and app_name_tail."""
    return {"app_name": name(), "app_name_tail": tail()}
