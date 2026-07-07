# API

## Django

`GET /`

Returns the default browser-facing Django scaffold page with templates,
middleware, static files, admin, auth, sessions, and messages enabled.

`GET /health/`

```json
{
  "service": "django",
  "status": "ok",
  "port": 8090
}
```

## FastAPI

`GET /`

```json
{
  "service": "fastapi",
  "status": "ok",
  "port": 8099,
  "docs": "/docs",
  "health": "/health",
  "ready": "/ready"
}
```

`GET /health`

```json
{
  "service": "fastapi",
  "status": "ok",
  "port": 8099
}
```

`GET /ready`

```json
{
  "service": "fastapi",
  "status": "ready",
  "port": 8099
}
```

Interactive docs remain available at `/docs`, `/redoc`, and `/openapi.json`.
