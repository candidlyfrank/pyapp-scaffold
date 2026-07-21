import json
import os
import subprocess
import sys


def load_settings(environment: str) -> dict:
    script = """
import json
from app import settings
print(json.dumps({
    "debug": settings.DEBUG,
    "allowed_hosts": settings.ALLOWED_HOSTS,
    "csrf_trusted_origins": settings.CSRF_TRUSTED_ORIGINS,
    "session_secure": settings.SESSION_COOKIE_SECURE,
    "session_http_only": settings.SESSION_COOKIE_HTTPONLY,
    "session_same_site": settings.SESSION_COOKIE_SAMESITE,
    "csrf_secure": settings.CSRF_COOKIE_SECURE,
    "csrf_same_site": settings.CSRF_COOKIE_SAMESITE,
    "proxy_ssl": settings.SECURE_PROXY_SSL_HEADER,
}))
"""
    env = os.environ.copy()
    env.update(
        {
            "ENV": environment,
            "DEBUG": "0",
            "DJANGO_ALLOWED_HOSTS": "example.com,www.example.com",
            "DJANGO_CSRF_TRUSTED_ORIGINS": "https://example.com",
        }
    )
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(result.stdout)


def test_production_cookie_and_proxy_policy():
    settings = load_settings("production")

    assert settings["debug"] is False
    assert settings["allowed_hosts"] == ["example.com", "www.example.com"]
    assert settings["csrf_trusted_origins"] == ["https://example.com"]
    assert settings["session_secure"] is True
    assert settings["session_http_only"] is True
    assert settings["session_same_site"] == "Lax"
    assert settings["csrf_secure"] is True
    assert settings["csrf_same_site"] == "Lax"
    assert settings["proxy_ssl"] == ["HTTP_X_FORWARDED_PROTO", "https"]


def test_development_cookies_work_with_local_http():
    settings = load_settings("development")

    assert settings["session_secure"] is False
    assert settings["csrf_secure"] is False
