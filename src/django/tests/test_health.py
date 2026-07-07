import importlib

from django.test import Client

from app import settings


def test_health_endpoint_returns_service_metadata():
    response = Client().get("/health/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "django",
        "status": "ok",
        "port": 8090,
    }


def test_root_endpoint_renders_default_django_page():
    response = Client().get("/")

    assert response.status_code == 200
    assert response["content-type"].startswith("text/html")
    content = response.content.decode()
    assert "Django app is running" in content
    assert "Default Django scaffold" in content


def test_static_url_is_configured_for_staticfiles_runserver():
    assert settings.STATIC_URL == "/static/"


def test_csrf_trusted_origins_are_read_from_environment(monkeypatch):
    monkeypatch.setenv("DJANGO_CSRF_TRUSTED_ORIGINS", "https://pyapp.envx, https://admin.envx")
    reloaded_settings = importlib.reload(settings)

    assert reloaded_settings.CSRF_TRUSTED_ORIGINS == ["https://pyapp.envx", "https://admin.envx"]


def test_csrf_trusted_origins_default_to_empty_when_environment_is_missing(monkeypatch):
    monkeypatch.delenv("DJANGO_CSRF_TRUSTED_ORIGINS", raising=False)
    reloaded_settings = importlib.reload(settings)

    assert reloaded_settings.CSRF_TRUSTED_ORIGINS == []


def test_default_django_contrib_stack_is_enabled():
    for app_name in [
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
    ]:
        assert app_name in settings.INSTALLED_APPS


def test_admin_route_is_available():
    response = Client().get("/admin/")

    assert response.status_code == 302
    assert "/admin/login/" in response["location"]
