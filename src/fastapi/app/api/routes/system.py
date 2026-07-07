from typing import Any

from fastapi import APIRouter, Request, Response

from app.core.config import settings

router = APIRouter()


def service_metadata(status: str = "ok") -> dict[str, Any]:
    return {
        "service": settings.service_name,
        "status": status,
        "port": settings.port,
    }


@router.get("/")
async def root() -> dict[str, Any]:
    return {
        **service_metadata(),
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
    }


@router.get("/health")
async def health() -> dict[str, Any]:
    return service_metadata()


@router.get("/ready")
async def ready(request: Request) -> dict[str, Any]:
    is_ready = bool(getattr(request.app.state, "ready", False))
    status = "ready" if is_ready else "starting"
    return service_metadata(status=status)


@router.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)
