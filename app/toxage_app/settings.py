"""Settings of the toxage-sim app. Only Django itself is needed."""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent
for path in (REPO_DIR, REPO_DIR / "risk-model"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

DEBUG = os.environ.get("TOXAGE_DEBUG", "1") == "1"
# Folder for the database and the secret key. In the container this is the
# volume /data, so both survive a new container.
DATA_DIR = Path(os.environ.get("TOXAGE_DATA_DIR", BASE_DIR))


def _secret_key():
    """The key from the environment, else one that is created once and kept
    in the data folder."""
    key = os.environ.get("TOXAGE_SECRET_KEY")
    if key:
        return key
    path = DATA_DIR / "secret_key"
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        from django.core.management.utils import get_random_secret_key
        key = get_random_secret_key()
        try:
            path.write_text(key)
            path.chmod(0o600)
        except OSError:
            pass    # read-only folder: the key lasts for this process
        return key


SECRET_KEY = _secret_key()
ALLOWED_HOSTS = os.environ.get("TOXAGE_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("TOXAGE_CSRF_TRUSTED_ORIGINS", "").split(",") if o]

INSTALLED_APPS = ["django.contrib.staticfiles", "explorer"]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "explorer.middleware.DisclaimerMiddleware",
]

ROOT_URLCONF = "toxage_app.urls"
WSGI_APPLICATION = "toxage_app.wsgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": ["django.template.context_processors.request",
                                       "explorer.tour.context"]},
}]

# SQLite in one file. Write-ahead logging lets pages be read while a data set
# is being stored, and keeps the number of disk writes low.
DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": os.environ.get("TOXAGE_DB", DATA_DIR / "db.sqlite3"),
    "OPTIONS": {
        "timeout": 30,
        "transaction_mode": "IMMEDIATE",
        "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
    },
}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_TZ = True
STATIC_URL = "static/"

# Disclaimer and licence terms. Raising the version asks every user again.
DISCLAIMER_VERSION = "1"
DISCLAIMER_COOKIE = "toxage_disclaimer"
DISCLAIMER_REMEMBER_DAYS = 365

# Data sets are generated in a thread of the server process. Tests switch
# this off, so that generating finishes within the call.
ASYNC_JOBS = True
# With TOXAGE_READ_ONLY=1 the app shows data and parameters but changes nothing.
READ_ONLY = os.environ.get("TOXAGE_READ_ONLY", "0") == "1"
