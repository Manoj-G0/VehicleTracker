"""Vehicle business rules."""

from io import BytesIO
from math import ceil
from zipfile import ZIP_STORED, ZipFile

from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleFilterParams,
    VehicleListItem,
    VehiclePage,
    VehicleRead,
    VehicleUpdate,
)
from app.schemas.variant import VariantCreate, VariantPage, VariantRead


class VehicleService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = VehicleRepository(session)

    async def list_vehicles(
        self,
        filters: VehicleFilterParams,
        page: int,
        page_size: int,
        max_page_size: int,
    ) -> VehiclePage:
        if page < 1:
            raise ValidationAppError("page must be greater than or equal to 1", field="page")
        if page_size < 1:
            raise ValidationAppError("page_size must be greater than or equal to 1", field="page_size")
        if page_size > max_page_size:
            raise ValidationAppError(
                f"page_size must not exceed {max_page_size}",
                field="page_size",
            )

        rows, total = await self.repository.list_page(filters, page, page_size)
        items = [
            VehicleListItem.model_validate(vehicle).model_copy(update={"variant_count": count})
            for vehicle, count in rows
        ]
        total_pages = ceil(total / page_size) if total else 0
        return VehiclePage(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        )

    async def get_vehicle(self, vehicle_id: int) -> VehicleRead:
        vehicle = await self.repository.get_by_id(vehicle_id)
        if vehicle is None:
            raise NotFoundError("Vehicle not found")
        return VehicleRead.model_validate(vehicle)

    async def list_variants(self, vehicle_id: int, page: int, page_size: int, max_page_size: int) -> VariantPage:
        if page_size > max_page_size:
            raise ValidationAppError(f"page_size must not exceed {max_page_size}", field="page_size")
        vehicle = await self.repository.get_by_id(vehicle_id, include_variants=False)
        if vehicle is None:
            raise NotFoundError("Vehicle not found")
        variants, total = await self.repository.list_variants_page(vehicle_id, page, page_size)
        return VariantPage(
            items=[VariantRead.model_validate(item) for item in variants],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=ceil(total / page_size) if total else 0,
        )

    async def create_variant(self, vehicle_id: int, payload: VariantCreate) -> VariantRead:
        if await self.repository.get_by_id(vehicle_id, include_variants=False) is None:
            raise NotFoundError("Vehicle not found")
        if await self.repository.get_variant_by_name(vehicle_id, payload.variant_name):
            raise ConflictError("A variant with this name already exists for this vehicle", field="variant_name")
        return VariantRead.model_validate(await self.repository.create_variant(vehicle_id, payload))

    async def update_variant(self, vehicle_id: int, variant_id: int, payload: VariantCreate) -> VariantRead:
        variant = await self.repository.get_variant_by_id(vehicle_id, variant_id)
        if variant is None:
            raise NotFoundError("Variant not found")
        duplicate = await self.repository.get_variant_by_name(vehicle_id, payload.variant_name)
        if duplicate is not None and duplicate.id != variant.id:
            raise ConflictError("A variant with this name already exists for this vehicle", field="variant_name")
        return VariantRead.model_validate(await self.repository.update_variant(variant, payload))

    async def delete_variant(self, vehicle_id: int, variant_id: int) -> None:
        variant = await self.repository.get_variant_by_id(vehicle_id, variant_id)
        if variant is None:
            raise NotFoundError("Variant not found")
        await self.repository.delete_variant(variant)

    async def export_vehicles(self, filters: VehicleFilterParams) -> bytes:
        vehicles = await self.repository.export_rows(filters)
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Vehicles"
        headers = [
            "Base Model Name",
            "RLF ID",
            "RM ID",
            "IP ID",
            "RM/RLF Band",
            "IP Band",
            "EVAP ID",
            "PR ID",
            "DF ID",
            "OB ID",
            "ER ID",
            "PEMS ID",
            "Variant Name",
            "Equation",
            "Cycle Energy Demand",
            "CO2",
        ]
        worksheet.append(headers)

        for vehicle in vehicles:
            base_row = [
                vehicle.base_model_name,
                vehicle.rlf_id,
                vehicle.rm_id,
                vehicle.ip_id,
                vehicle.rm_rlf_band,
                vehicle.ip_band,
                vehicle.evap_id,
                vehicle.pr_id,
                vehicle.df_id,
                vehicle.ob_id,
                vehicle.er_id,
                vehicle.pems_id,
                "",
                "",
                "",
                "",
            ]
            if not vehicle.variants:
                worksheet.append(base_row)
                continue
            for variant in vehicle.variants:
                worksheet.append([
                    vehicle.base_model_name,
                    vehicle.rlf_id,
                    vehicle.rm_id,
                    vehicle.ip_id,
                    vehicle.rm_rlf_band,
                    vehicle.ip_band,
                    vehicle.evap_id,
                    vehicle.pr_id,
                    vehicle.df_id,
                    vehicle.ob_id,
                    vehicle.er_id,
                    vehicle.pems_id,
                    variant.variant_name,
                    variant.equation,
                    variant.cycle_energy_demand,
                    variant.co2,
                ])

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)
        rewritten = BytesIO()
        with ZipFile(buffer, "r") as source:
            with ZipFile(rewritten, mode="w", compression=ZIP_STORED) as target:
                for info in source.infolist():
                    target.writestr(info.filename, source.read(info.filename), compress_type=ZIP_STORED)
        return rewritten.getvalue()

    async def create_vehicle(self, payload: VehicleCreate) -> VehicleRead:
        existing = await self.repository.get_by_name(payload.base_model_name)
        if existing is not None:
            raise ConflictError("A vehicle with this base model name already exists", field="base_model_name")
        vehicle = await self.repository.create(payload)
        return VehicleRead.model_validate(vehicle)

    async def update_vehicle(self, vehicle_id: int, payload: VehicleUpdate) -> VehicleRead:
        vehicle = await self.repository.get_by_id(vehicle_id)
        if vehicle is None:
            raise NotFoundError("Vehicle not found")
        other = await self.repository.get_by_name(payload.base_model_name)
        if other is not None and other.id != vehicle.id:
            raise ConflictError("A vehicle with this base model name already exists", field="base_model_name")
        updated = await self.repository.update(vehicle, payload)
        return VehicleRead.model_validate(updated)

    async def delete_vehicle(self, vehicle_id: int) -> None:
        vehicle = await self.repository.get_by_id(vehicle_id)
        if vehicle is None:
            raise NotFoundError("Vehicle not found")
        await self.repository.soft_delete(vehicle)

    async def health(self) -> bool:
        return await self.repository.ping()
