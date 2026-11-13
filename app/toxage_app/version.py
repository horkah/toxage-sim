"""Version and build of the app, shown on the about page and in the footer.

The version is the one of pyproject.toml and changes with a release. The
build changes with every build of the app:

  TOXAGE_BUILD   environment variable, if set, shown as it is
  BUILD          file in the repository root, written by the Dockerfile:
                 the moment of the build in seconds since 1970, and the commit
  git            moment and short hash of the last commit, in a working copy
  "dev"          otherwise

A moment is stored as a plain number of seconds and shown in the time zone
of the server (zone.py), e.g. "20261113.2245 (abc1234)".
"""
import os
import subprocess
import tomllib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .zone import local_zone

REPO = Path(__file__).resolve().parents[2]


def _version():
    try:
        with open(REPO / "pyproject.toml", "rb") as f:
            return tomllib.load(f)["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "0"


def stamp(text, zone=None):
    """ "1763070300 abc1234" -> "20251113.2245 (abc1234)" in the server's zone.
    Text in another form, e.g. from an older build, is shown as it is."""
    parts = text.split()
    if not parts or not parts[0].isdigit() or len(parts) > 2:
        return text
    moment = datetime.fromtimestamp(int(parts[0]), ZoneInfo(zone or local_zone()))
    return f"{moment:%Y%m%d.%H%M}" + (f" ({parts[1]})" if len(parts) == 2 else "")


def _git():
    try:
        out = subprocess.run(["git", "-C", str(REPO), "log", "-1", "--format=%ct %h"],
                             capture_output=True, text=True, timeout=3, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return stamp(out) if out else None


def _build():
    if os.environ.get("TOXAGE_BUILD"):
        return os.environ["TOXAGE_BUILD"].strip()
    try:
        text = (REPO / "BUILD").read_text(encoding="utf-8").strip()
        if text:
            return stamp(text)
    except OSError:
        pass
    return _git() or "dev"


VERSION = _version()
BUILD = _build()
