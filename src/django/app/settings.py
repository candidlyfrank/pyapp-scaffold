import ipaddress
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", secrets.token_urlsafe(32))
ENV = os.getenv("ENV", "development")
DEBUG = os.getenv("DEBUG", "1" if ENV == "development" else "0") == "1"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = ENV in {"staging", "production"}
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = ENV in {"staging", "production"}
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_FAILURE_VIEW = "app.views.csrf_failure"
ROOT_URLCONF = "app.urls"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "UTC"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DOCUMENT_DATA_ROOT = Path(
    os.getenv("DJANGO_DOCUMENT_DATA_ROOT", str(BASE_DIR / ".data" / "documents"))
)
DOCUMENT_FILES_ROOT = DOCUMENT_DATA_ROOT / "files"
DOCUMENT_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MEDIA_ROOT = DOCUMENT_FILES_ROOT
DOCUMENT_EVENT_CALLBACK = os.getenv("DOCUMENT_EVENT_CALLBACK", "")
DOCUMENT_RAG_REVISION_STATE_READER = os.getenv(
    "DOCUMENT_RAG_REVISION_STATE_READER",
    "",
)
DOCUMENT_RAG_SYNC_COMMAND_SINK = os.getenv("DOCUMENT_RAG_SYNC_COMMAND_SINK", "")
DOCUMENT_OUTBOX_BATCH_SIZE = int(os.getenv("DOCUMENT_OUTBOX_BATCH_SIZE", "50"))
DOCUMENT_OUTBOX_LEASE_SECONDS = int(
    os.getenv("DOCUMENT_OUTBOX_LEASE_SECONDS", "60")
)
DOCUMENT_OUTBOX_MAX_ATTEMPTS = int(
    os.getenv("DOCUMENT_OUTBOX_MAX_ATTEMPTS", "8")
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "debug_toolbar",
    "documents",
    "document_integrations",
    "store",
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
DATABASES["documents"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": DOCUMENT_DATA_ROOT / "metadata.sqlite3",
    "TEST": {"DEPENDENCIES": []},
}
DATABASE_ROUTERS = ["documents.router.DocumentDatabaseRouter"]

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

def show_debug_toolbar(request):
    if not DEBUG:
        return False

    if "PYTEST_CURRENT_TEST" in os.environ:
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
