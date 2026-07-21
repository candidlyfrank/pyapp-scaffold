from types import SimpleNamespace

from django.test import Client, RequestFactory

from app.views import session_api


def test_session_api_returns_authenticated_user():
    request = RequestFactory().get("/api/session/")
    request.user = SimpleNamespace(is_authenticated=True, username="alice")

    response = session_api(request)

    assert response.status_code == 200
    assert response.content == b'{"authenticated": true, "username": "alice"}'


def test_mutation_requires_csrf_cookie_and_header_pair():
    client = Client(enforce_csrf_checks=True)
    client.get("/api/session/")

    rejected = client.post("/api/example-mutation/")
    accepted = client.post(
        "/api/example-mutation/",
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
    )

    assert rejected.status_code == 403
    assert accepted.status_code == 200
    assert accepted.json() == {"status": "saved"}
