"""Version and build of the app, shown on the about page and in the footer.

The version is the one of pyproject.toml and changes with a release. The
build changes with every build of the app:

  TOXAGE_BUILD   environment variable, if set
  BUILD          file in the repository root, written by the Dockerfile
  git            date and short hash of the last commit, in a working copy
  "dev"          otherwise
"""
import os
import subprocess
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _version():
    try:
        with open(REPO / "pyproject.toml", "rb") as f:
            return tomllib.load(f)["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        return "0"


def _git():
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "log", "-1", "--format=%cd %h", "--date=format:%Y%m%d.%H%M"],
            capture_output=True, text=True, timeout=3, check=True).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return None
    return f"{out[0]} ({out[1]})" if len(out) == 2 else None


def _build():
    if os.environ.get("TOXAGE_BUILD"):
        return os.environ["TOXAGE_BUILD"].strip()
    try:
        text = (REPO / "BUILD").read_text(encoding="utf-8").strip()
        if text:
            return text
    except OSError:
        pass
    return _git() or "dev"


VERSION = _version()
BUILD = _build()
