"""The time zone of the server, in which the app shows all times.

  TZ              environment variable, e.g. Europe/Berlin (docker-compose.yml sets it)
  /etc/timezone   the configured zone on Debian and Ubuntu
  /etc/localtime  the zone the system link points to
  UTC             otherwise
"""
import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _valid(name):
    name = (name or "").strip().lstrip(":")
    if not name:
        return None
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None
    return name


def local_zone(environ=os.environ, etc=Path("/etc")):
    """Name of the time zone of the server, e.g. "Europe/Berlin"."""
    found = _valid(environ.get("TZ"))
    if found:
        return found
    try:
        found = _valid((etc / "timezone").read_text(encoding="utf-8"))
    except OSError:
        found = None
    if found:
        return found
    try:
        target = os.readlink(etc / "localtime")
    except OSError:
        target = ""
    if "zoneinfo/" in target:
        found = _valid(target.split("zoneinfo/", 1)[1])
    return found or "UTC"
