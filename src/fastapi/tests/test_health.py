from fastapi.testclient import TestClient

from app.main import app


def test_root_endpoint_returns_default_scaffold_metadata():
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "fastapi",
        "status": "ok",
        "port": 8099,
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
    }


def test_health_endpoint_returns_service_metadata():
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "fastapi",
        "status": "ok",
        "port": 8099,
    }


def test_ready_endpoint_reports_lifespan_state():
    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "service": "fastapi",
        "status": "ready",
        "port": 8099,
    }


def test_docs_and_openapi_are_available():
    client = TestClient(app)

    docs_response = client.get("/docs")
    openapi_response = client.get("/openapi.json")

    assert docs_response.status_code == 200
    assert "text/html" in docs_response.headers["content-type"]
    assert openapi_response.status_code == 200
    assert openapi_response.json()["info"]["title"] == "FastAPI Scaffold"


def test_favicon_endpoint_returns_no_content():
    response = TestClient(app).get("/favicon.ico")

    assert response.status_code == 204
