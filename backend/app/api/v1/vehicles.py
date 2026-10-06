"""Vehicle CRUD and search APIs."""

from io import BytesIO

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, require_admin, require_importer, require_viewer
from app.db.session import get_db
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleFilterParams,
    VehiclePage,
    VehicleRead,
    VehicleUpdate,
)
from app.schemas.variant import VariantCreate, VariantPage, VariantRead
from app.services.vehicle_service import VehicleService

router = APIRouter()


def get_vehicle_service(db: AsyncSession = Depends(get_db)) -> VehicleService:
    return VehicleService(db)


@router.get(
    "/vehicles",
    response_model=VehiclePage,
    summary="List vehicles",
    description=(
        "Returns paginated base-model records. Populated filters are combined with AND. "
        "Text matching uses case-insensitive partial matching. The variant_name filter uses "
        "EXISTS so parent rows are not duplicated. OB ID is not unique and may match many vehicles."
    ),
)
async def list_vehicles(
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=None, ge=1),
    base_model_name: str | None = Query(default=None),
    rlf_id: str | None = Query(default=None),
    rm_id: str | None = Query(default=None),
    ip_id: str | None = Query(default=None),
    rm_rlf_band: str | None = Query(default=None),
    ip_band: str | None = Query(default=None),
    evap_id: str | None = Query(default=None),
    pr_id: str | None = Query(default=None),
    df_id: str | None = Query(default=None),
    ob_id: str | None = Query(default=None),
    er_id: str | None = Query(default=None),
    pems_id: str | None = Query(default=None),
    variant_name: str | None = Query(default=None),
    service: VehicleService = Depends(get_vehicle_service),
    settings: Settings = Depends(get_settings),
    _: CurrentUser = Depends(require_viewer),
) -> VehiclePage:
    filters = VehicleFilterParams(
        base_model_name=base_model_name,
        rlf_id=rlf_id,
        rm_id=rm_id,
        ip_id=ip_id,
        rm_rlf_band=rm_rlf_band,
        ip_band=ip_band,
        evap_id=evap_id,
        pr_id=pr_id,
        df_id=df_id,
        ob_id=ob_id,
        er_id=er_id,
        pems_id=pems_id,
        variant_name=variant_name,
    )
    size = page_size or settings.default_page_size
    return await service.list_vehicles(filters, page, size, settings.max_page_size)


@router.get(
    "/vehicles/export",
    summary="Export filtered vehicles to Excel",
)
async def export_vehicles(
    base_model_name: str | None = Query(default=None),
    rlf_id: str | None = Query(default=None),
    rm_id: str | None = Query(default=None),
    ip_id: str | None = Query(default=None),
    rm_rlf_band: str | None = Query(default=None),
    ip_band: str | None = Query(default=None),
    evap_id: str | None = Query(default=None),
    pr_id: str | None = Query(default=None),
    df_id: str | None = Query(default=None),
    ob_id: str | None = Query(default=None),
    er_id: str | None = Query(default=None),
    pems_id: str | None = Query(default=None),
    variant_name: str | None = Query(default=None),
    service: VehicleService = Depends(get_vehicle_service),
    _: CurrentUser = Depends(require_viewer),
) -> StreamingResponse:
    filters = VehicleFilterParams(
        base_model_name=base_model_name,
        rlf_id=rlf_id,
        rm_id=rm_id,
        ip_id=ip_id,
        rm_rlf_band=rm_rlf_band,
        ip_band=ip_band,
        evap_id=evap_id,
        pr_id=pr_id,
        df_id=df_id,
        ob_id=ob_id,
        er_id=er_id,
        pems_id=pems_id,
        variant_name=variant_name,
    )
    workbook = await service.export_vehicles(filters)
    return StreamingResponse(
        BytesIO(workbook),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=vehicles.xlsx"},
    )


@router.get(
    "/vehicles/{vehicle_id}",
    response_model=VehicleRead,
    summary="Get vehicle detail",
    responses={404: {"description": "Vehicle not found"}},
)
async def get_vehicle(
    vehicle_id: int,
    service: VehicleService = Depends(get_vehicle_service),
    _: CurrentUser = Depends(require_viewer),
) -> VehicleRead:
    return await service.get_vehicle(vehicle_id)


@router.get("/vehicles/{vehicle_id}/variants", response_model=VariantPage, summary="List vehicle variants")
async def list_variants(
    vehicle_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int | None = Query(default=20, ge=1),
    service: VehicleService = Depends(get_vehicle_service),
    settings: Settings = Depends(get_settings),
    _: CurrentUser = Depends(require_viewer),
) -> VariantPage:
    return await service.list_variants(vehicle_id, page, page_size or 20, settings.max_page_size)


@router.post("/vehicles/{vehicle_id}/variants", response_model=VariantRead, status_code=status.HTTP_201_CREATED)
async def create_variant(
    vehicle_id: int,
    payload: VariantCreate,
    service: VehicleService = Depends(get_vehicle_service),
    _: CurrentUser = Depends(require_importer),
) -> VariantRead:
    return await service.create_variant(vehicle_id, payload)


@router.put("/vehicles/{vehicle_id}/variants/{variant_id}", response_model=VariantRead)
async def update_variant(
    vehicle_id: int,
    variant_id: int,
    payload: VariantCreate,
    service: VehicleService = Depends(get_vehicle_service),
    _: CurrentUser = Depends(require_importer),
) -> VariantRead:
    return await service.update_variant(vehicle_id, variant_id, payload)


@router.delete("/vehicles/{vehicle_id}/variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variant(
    vehicle_id: int,
    variant_id: int,
    service: VehicleService = Depends(get_vehicle_service),
    _: CurrentUser = Depends(require_importer),
) -> Response:
    await service.delete_variant(vehicle_id, variant_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/vehicles",
    response_model=VehicleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create vehicle",
    responses={409: {"description": "Duplicate base model"}, 422: {"description": "Validation error"}},
)
async def create_vehicle(
    payload: VehicleCreate,
    service: VehicleService = Depends(get_vehicle_service),
    _: CurrentUser = Depends(require_importer),
) -> VehicleRead:
    return await service.create_vehicle(payload)


@router.put(
    "/vehicles/{vehicle_id}",
    response_model=VehicleRead,
    summary="Update vehicle and variant set",
    responses={404: {"description": "Vehicle not found"}, 409: {"description": "Duplicate base model"}},
)
async def update_vehicle(
    vehicle_id: int,
    payload: VehicleUpdate,
    service: VehicleService = Depends(get_vehicle_service),
    _: CurrentUser = Depends(require_importer),
) -> VehicleRead:
    return await service.update_vehicle(vehicle_id, payload)


@router.delete(
    "/vehicles/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete vehicle",
    description="Marks the vehicle as deleted. Records are retained and excluded from search.",
    responses={404: {"description": "Vehicle not found"}},
)
async def delete_vehicle(
    vehicle_id: int,
    service: VehicleService = Depends(get_vehicle_service),
    _: CurrentUser = Depends(require_admin),
) -> Response:
    await service.delete_vehicle(vehicle_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
