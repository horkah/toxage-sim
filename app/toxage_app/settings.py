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
SECRET_KEY = os.environ.get("TOXAGE_SECRET_KEY", "insecure-key-for-local-demo-only")
ALLOWED_HOSTS = os.environ.get("TOXAGE_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

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
    "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
}]

DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": os.environ.get("TOXAGE_DB", BASE_DIR / "db.sqlite3"),
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
