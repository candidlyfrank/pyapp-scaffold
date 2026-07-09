import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", secrets.token_urlsafe(32))
DEBUG = True
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
ROOT_URLCONF = "app.urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "debug_toolbar",
    "playground",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "app.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "django_app",
        "USER": "django_app",
        "PASSWORD": os.getenv("DJANGO_DATABASE_PASSWORD", ""),
        "HOST": "postgres-django",
        "PORT": "5432",
        "CONN_MAX_AGE": 60,
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "dev": {
            "format": "%(levelname)s %(name)s %(message)s",
        },
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "dev",
        },
    },
    "root": {"handlers": ["console"], "level": "DEBUG"},
}

INTERNAL_IPS = [
    "127.0.0.1",
    "172.31.0.1"
]

import ipaddress
def show_debug_toolbar(request):
    if not DEBUG:
        return False

    remote_addr = request.META.get("REMOTE_ADDR")
    if remote_addr in INTERNAL_IPS:
        return True

    try:
        return ipaddress.ip_address(remote_addr).is_private
    except ValueError:
        return False


DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": "app.settings.show_debug_toolbar",
}
