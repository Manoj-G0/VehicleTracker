"""Health and readiness endpoints."""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.services.vehicle_service import VehicleService

router = APIRouter()


@router.get(
    "/health",
    summary="Application health",
    description="Liveness always succeeds. Readiness includes a PostgreSQL ping.",
)
async def health(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    ready = False
    try:
        ready = await VehicleService(db).health()
    except Exception:  # noqa: BLE001
        ready = False

    payload = {
        "status": "ok" if ready else "degraded",
        "service": settings.app_name,
        "environment": settings.app_env,
        "ready": ready,
    }
    code = status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=code, content=payload)
