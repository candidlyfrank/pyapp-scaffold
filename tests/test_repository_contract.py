import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_required_make_targets_exist():
    makefile = read("Makefile")
    for target in [
        "lint",
        "restart",
        "restart-django",
        "restart-fastapi",
        "test",
        "test-django",
        "test-fastapi",
        "test-integration",
        "lock-django",
        "lock-fastapi",
        "scan",
        "scan-django",
        "scan-fastapi",
        "compose-check",
        "ci-backend",
        "ci-frontend",
        "ci",
        "act-ci",
        "rollback",
    ]:
        assert f"{target}:" in makefile


def test_compose_overlays_define_expected_services_and_ports():
    base = yaml.safe_load(read("docker-compose.yml"))
    dev = yaml.safe_load(read("docker-compose.dev.yml"))
    prod = yaml.safe_load(read("docker-compose.prod.yml"))

    assert {"django", "fastapi", "caddy", "postgres-django", "postgres-fastapi", "redis"}.issubset(
        set(base["services"])
    )
    assert base["services"]["django"]["build"]["context"] == "./src/django"
    assert base["services"]["django"]["build"]["dockerfile"] == "Dockerfile"
    assert base["services"]["fastapi"]["build"]["context"] == "./src/fastapi"
    assert base["services"]["fastapi"]["build"]["dockerfile"] == "Dockerfile"
    assert "8090:8090" in dev["services"]["django"]["ports"]
    assert "8099:8099" in dev["services"]["fastapi"]["ports"]
    assert "./src/django:/app" in dev["services"]["django"]["volumes"]
    assert "./src/fastapi:/app" in dev["services"]["fastapi"]["volumes"]
    assert dev["services"]["django"]["command"][0] == "/opt/venv/bin/python"
    assert dev["services"]["fastapi"]["command"][0] == "/opt/venv/bin/uvicorn"
    assert "app.main:app" in dev["services"]["fastapi"]["command"]
    assert prod["services"]["django"]["read_only"] is True
    assert prod["services"]["fastapi"]["read_only"] is True
    assert "ALL" in prod["services"]["django"]["cap_drop"]


def test_workflows_delegate_to_shared_make_commands():
    ci = read(".github/workflows/ci.yml")
    publish = read(".github/workflows/publish.yml")
    deploy = read(".github/workflows/deploy.yml")
    rollback = read(".github/workflows/rollback.yml")

    assert "uv sync --locked --group dev --project src/django" in ci
    assert "uv sync --locked --group dev --project src/fastapi" in ci
    assert "make ci-backend" in ci
    assert "actions/setup-node@v4" in ci
    assert "node-version: 22" in ci
    assert "cache-dependency-path: src/frontend/package-lock.json" in ci
    for command in ["npm ci", "npm run lint", "npm test", "npm run build"]:
        assert f"run: {command}" in ci
    assert "context: ./src/django" in publish
    assert "context: ./src/fastapi" in publish
    assert "make compose-check" in deploy
    assert "make rollback" in rollback


def test_api_reference_documents_supported_interfaces():
    api = read("docs/API.md")
    required_interfaces = [
        "GET /api/session/",
        "POST /api/example-mutation/",
        "POST /api/chat",
        "GET /api/documents/",
        "POST /api/documents/",
        "GET /api/documents/{id}/",
        "PATCH /api/documents/{id}/",
        "DELETE /api/documents/{id}/",
        "GET /api/documents/{id}/download/",
        "GET /api/health",
        "POST /chat/api/chat",
        "dispatch_document_outbox",
        "reconcile_document_revisions",
        "X-CSRFToken",
        "207 Multi-Status",
    ]
    for interface in required_interfaces:
        assert interface in api


def test_frontend_production_dependencies_are_audited():
    package = json.loads(read("src/frontend/package.json"))
    ci = read(".github/workflows/ci.yml")
    makefile = read("Makefile")

    assert package["dependencies"]["next"] == "16.2.11"
    assert package["overrides"] == {
        "postcss": "8.5.12",
        "sharp": "0.35.0",
    }
    assert "npm audit --omit=dev --audit-level=high" in ci
    assert "npm audit --omit=dev --audit-level=high" in makefile


def test_document_rag_requirements_baseline_is_tracked_and_linked():
    srs = read("SOFTWARE_REQUIREMENTS_SPECIFICATION.md")
    architecture_index = read("docs/architecture/README.md")
    architecture_guide = read(
        "docs/architecture/document-file-handling-and-rag-readiness.md"
    )

    assert "## 11. Test Requirements" in srs
    assert "frontend verification job" in srs
    assert "production dependency" in srs
    assert "docs/API.md" in srs
    assert "Document file handling and RAG readiness" in architecture_index
    assert "# Document File Handling and RAG Readiness" in architecture_guide


def test_services_are_independent_python_projects():
    root_project = read("pyproject.toml")
    django_project = read("src/django/pyproject.toml")
    fastapi_project = read("src/fastapi/pyproject.toml")

    assert (ROOT / "src/django/app").is_dir()
    assert (ROOT / "src/fastapi/app").is_dir()
    assert not (ROOT / "src/django/django_app").exists()
    assert not (ROOT / "src/fastapi/fastapi_app").exists()
    assert (ROOT / "src/django/uv.lock").exists()
    assert (ROOT / "src/fastapi/uv.lock").exists()
    assert "django>=" not in root_project
    assert "fastapi>=" not in root_project
    assert "django>=" in django_project
    assert "fastapi>=" not in django_project
    assert "fastapi>=" in fastapi_project
    assert "django>=" not in fastapi_project


def test_service_commands_use_app_package_name():
    checked_paths = [
        "src/django/manage.py",
        "src/django/app/asgi.py",
        "src/django/app/settings.py",
        "src/django/app/wsgi.py",
        "src/fastapi/Dockerfile",
        "src/django/Dockerfile",
        "docker-compose.dev.yml",
        "docker-compose.yml",
        "Makefile",
    ]
    combined = "\n".join(read(path) for path in checked_paths)

    assert "django_app.settings" not in combined
    assert "fastapi_app.main:app" not in combined
    assert "app.settings" in combined
    assert "app.main:app" in combined


def test_service_docker_virtualenvs_are_not_hidden_by_dev_mounts():
    django_dockerfile = read("src/django/Dockerfile")
    fastapi_dockerfile = read("src/fastapi/Dockerfile")

    assert "UV_PROJECT_ENVIRONMENT=/opt/venv" in django_dockerfile
    assert "PATH=\"/opt/venv/bin:$PATH\"" in django_dockerfile
    assert 'CMD ["/opt/venv/bin/python"' in django_dockerfile
    assert "UV_PROJECT_ENVIRONMENT=/opt/venv" in fastapi_dockerfile
    assert "PATH=\"/opt/venv/bin:$PATH\"" in fastapi_dockerfile
    assert 'CMD ["/opt/venv/bin/uvicorn"' in fastapi_dockerfile


def test_agent_plans_exist():
    for plan in [
        ".agents/plan/DEVELOPMENT_PLAN.md",
        ".agents/plan/CICD_PLAN.md",
        ".agents/plan/PRODUCTION_PLAN.md",
        ".agents/plan/ORCHESTRATOR_EXECUTION_PLAN.md",
    ]:
        assert (ROOT / plan).exists()
