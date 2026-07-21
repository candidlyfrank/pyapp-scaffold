from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]


def read(path: str) -> str:
    return (ROOT / path).read_text()


def test_frontend_is_integrated_and_hardened():
    base = yaml.safe_load(read("docker-compose.yml"))
    dev = yaml.safe_load(read("docker-compose.dev.yml"))
    staging = yaml.safe_load(read("docker-compose.staging.yml"))
    prod = yaml.safe_load(read("docker-compose.prod.yml"))

    frontend = base["services"]["frontend"]
    assert frontend["build"] == {
        "context": "./src/frontend",
        "dockerfile": "Dockerfile",
        "target": "development",
    }
    assert frontend["environment"]["DJANGO_INTERNAL_URL"] == "http://django:8090"
    assert frontend["expose"] == ["3000"]
    assert "frontend" in base["services"]["caddy"]["depends_on"]

    assert dev["services"]["frontend"]["build"]["target"] == "development"
    assert "3000:3000" in dev["services"]["frontend"]["ports"]
    assert "./src/frontend:/app" in dev["services"]["frontend"]["volumes"]
    assert "/app/node_modules" in dev["services"]["frontend"]["volumes"]
    assert "/app/.next" in dev["services"]["frontend"]["volumes"]

    assert staging["services"]["frontend"]["build"]["target"] == "production"
    production_frontend = prod["services"]["frontend"]
    assert production_frontend["build"]["target"] == "production"
    assert production_frontend["image"] == "${FRONTEND_IMAGE:-pyapp-scaffold-frontend:local}"
    assert production_frontend["read_only"] is True
    assert production_frontend["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in production_frontend["security_opt"]
    assert "/tmp" in production_frontend["tmpfs"]  # noqa: S108
    assert "ports" not in staging["services"]["frontend"]
    assert "ports" not in production_frontend


def test_caddy_routes_django_prefixes_before_frontend_fallback():
    for path in [
        "config/caddy/Caddyfile.dev",
        "config/caddy/Caddyfile.staging",
        "config/caddy/Caddyfile.prod",
    ]:
        caddyfile = read(path)
        positions = [
            caddyfile.index(f"handle {prefix}*")
            for prefix in ["/api/", "/admin/", "/static/", "/media/"]
        ]
        frontend_position = caddyfile.index("reverse_proxy frontend:3000")
        assert positions == sorted(positions)
        assert all(position < frontend_position for position in positions)
        assert "handle_path /api/" not in caddyfile


def test_django_internal_url_is_never_public_frontend_configuration():
    checked = [
        "docker-compose.yml",
        "docker-compose.dev.yml",
        "docker-compose.staging.yml",
        "docker-compose.prod.yml",
        ".env.dev",
        ".env.staging.example",
        ".env.prod.example",
    ]
    combined = "\n".join(read(path) for path in checked)
    assert "NEXT_PUBLIC_DJANGO_INTERNAL_URL" not in combined


def test_frontend_uses_npm_with_a_buildkit_cache():
    dockerfile = read("src/frontend/Dockerfile")
    package = read("src/frontend/package.json")
    dev_compose = read("docker-compose.dev.yml")

    assert "--mount=type=cache,id=npm,target=/root/.npm" in dockerfile
    assert "npm ci --fetch-timeout=300000" in dockerfile
    assert 'CMD ["npm", "run", "dev"]' in dockerfile
    assert "COPY package.json package-lock.json ./" in dockerfile
    assert 'command: ["npm", "run", "dev"]' in dev_compose
    assert "npm" not in dockerfile
    assert "packageManager" not in package
    assert (ROOT / "src/frontend/package-lock.json").exists()
