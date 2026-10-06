"""Vehicle persistence and parameterized filter queries."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.variant import Variant
from app.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleFilterParams, VehicleUpdate
from app.utils.normalization import escape_ilike

FILTER_COLUMNS = {
    "base_model_name": Vehicle.base_model_name,
    "rlf_id": Vehicle.rlf_id,
    "rm_id": Vehicle.rm_id,
    "ip_id": Vehicle.ip_id,
    "rm_rlf_band": Vehicle.rm_rlf_band,
    "ip_band": Vehicle.ip_band,
    "evap_id": Vehicle.evap_id,
    "pr_id": Vehicle.pr_id,
    "df_id": Vehicle.df_id,
    "ob_id": Vehicle.ob_id,
    "er_id": Vehicle.er_id,
    "pems_id": Vehicle.pems_id,
}


class VehicleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _active(self) -> Select[tuple[Vehicle]]:
        return select(Vehicle).where(Vehicle.deleted_at.is_(None))

    def _apply_filters(self, stmt: Select, filters: VehicleFilterParams) -> Select:
        data = filters.model_dump()
        variant_name = data.pop("variant_name")
        for field, column in FILTER_COLUMNS.items():
            value = data.get(field)
            if value:
                stmt = stmt.where(column.ilike(f"%{escape_ilike(value)}%", escape="\\"))
        if variant_name:
            exists_stmt = (
                select(Variant.id)
                .where(Variant.vehicle_id == Vehicle.id)
                .where(Variant.variant_name.ilike(f"%{escape_ilike(variant_name)}%", escape="\\"))
            )
            stmt = stmt.where(exists_stmt.exists())
        return stmt

    async def list_page(
        self,
        filters: VehicleFilterParams,
        page: int,
        page_size: int,
    ) -> tuple[list[tuple[Vehicle, int]], int]:
        variant_count = (
            select(func.count(Variant.id))
            .where(Variant.vehicle_id == Vehicle.id)
            .correlate(Vehicle)
            .scalar_subquery()
            .label("variant_count")
        )
        stmt = self._apply_filters(self._active(), filters).order_by(Vehicle.base_model_name)
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = int(await self.session.scalar(count_stmt) or 0)

        offset = (page - 1) * page_size
        rows = (
            await self.session.execute(
                stmt.add_columns(variant_count).offset(offset).limit(page_size)
            )
        ).all()
        return [(row[0], int(row[1] or 0)) for row in rows], total

    async def get_by_id(self, vehicle_id: int, include_variants: bool = True) -> Vehicle | None:
        stmt = self._active().where(Vehicle.id == vehicle_id)
        if include_variants:
            stmt = stmt.options(selectinload(Vehicle.variants))
        return await self.session.scalar(stmt)

    async def list_variants_page(self, vehicle_id: int, page: int, page_size: int) -> tuple[list[Variant], int]:
        base = select(Variant).where(Variant.vehicle_id == vehicle_id)
        total = int(await self.session.scalar(select(func.count()).select_from(base.subquery())) or 0)
        variants = list((await self.session.scalars(
            base.order_by(Variant.variant_name, Variant.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )).all())
        return variants, total

    async def get_variant_by_name(self, vehicle_id: int, variant_name: str) -> Variant | None:
        return await self.session.scalar(
            select(Variant).where(
                Variant.vehicle_id == vehicle_id,
                func.lower(Variant.variant_name) == variant_name.strip().lower(),
            )
        )

    async def get_variant_by_id(self, vehicle_id: int, variant_id: int) -> Variant | None:
        return await self.session.scalar(
            select(Variant).where(Variant.vehicle_id == vehicle_id, Variant.id == variant_id)
        )

    async def create_variant(self, vehicle_id: int, payload) -> Variant:
        variant = Variant(vehicle_id=vehicle_id, **payload.model_dump())
        self.session.add(variant)
        await self.session.flush()
        await self.session.refresh(variant)
        return variant

    async def update_variant(self, variant: Variant, payload) -> Variant:
        variant.variant_name = payload.variant_name
        variant.equation = payload.equation
        variant.cycle_energy_demand = payload.cycle_energy_demand
        variant.co2 = payload.co2
        await self.session.flush()
        await self.session.refresh(variant)
        return variant

    async def delete_variant(self, variant: Variant) -> None:
        await self.session.delete(variant)
        await self.session.flush()

    async def get_by_name(self, base_model_name: str) -> Vehicle | None:
        stmt = (
            self._active()
            .where(func.lower(Vehicle.base_model_name) == base_model_name.lower())
            .options(selectinload(Vehicle.variants))
        )
        return await self.session.scalar(stmt)

    async def get_by_names(self, names: list[str]) -> dict[str, Vehicle]:
        if not names:
            return {}
        lowered = [name.lower() for name in names]
        stmt = (
            self._active()
            .where(func.lower(Vehicle.base_model_name).in_(lowered))
            .options(selectinload(Vehicle.variants))
        )
        vehicles = list((await self.session.scalars(stmt)).unique().all())
        return {vehicle.base_model_name.lower(): vehicle for vehicle in vehicles}

    async def create(self, payload: VehicleCreate) -> Vehicle:
        vehicle = Vehicle(
            base_model_name=payload.base_model_name,
            rlf_id=payload.rlf_id,
            rm_id=payload.rm_id,
            ip_id=payload.ip_id,
            rm_rlf_band=payload.rm_rlf_band,
            ip_band=payload.ip_band,
            evap_id=payload.evap_id,
            pr_id=payload.pr_id,
            df_id=payload.df_id,
            ob_id=payload.ob_id,
            er_id=payload.er_id,
            pems_id=payload.pems_id,
            variants=[
                Variant(
                    variant_name=item.variant_name,
                    equation=item.equation,
                    cycle_energy_demand=item.cycle_energy_demand,
                    co2=item.co2,
                )
                for item in payload.variants
            ],
        )
        self.session.add(vehicle)
        await self.session.flush()
        await self.session.refresh(vehicle)
        return vehicle

    async def update(self, vehicle: Vehicle, payload: VehicleUpdate) -> Vehicle:
        vehicle.base_model_name = payload.base_model_name
        vehicle.rlf_id = payload.rlf_id
        vehicle.rm_id = payload.rm_id
        vehicle.ip_id = payload.ip_id
        vehicle.rm_rlf_band = payload.rm_rlf_band
        vehicle.ip_band = payload.ip_band
        vehicle.evap_id = payload.evap_id
        vehicle.pr_id = payload.pr_id
        vehicle.df_id = payload.df_id
        vehicle.ob_id = payload.ob_id
        vehicle.er_id = payload.er_id
        vehicle.pems_id = payload.pems_id

        desired = {item.variant_name.lower(): item for item in payload.variants}
        existing_by_lower = {variant.variant_name.lower(): variant for variant in vehicle.variants}

        for key, variant in list(existing_by_lower.items()):
            if key not in desired:
                vehicle.variants.remove(variant)

        for key, item in desired.items():
            existing = existing_by_lower.get(key)
            if existing is None:
                vehicle.variants.append(
                    Variant(
                        variant_name=item.variant_name,
                        equation=item.equation,
                        cycle_energy_demand=item.cycle_energy_demand,
                        co2=item.co2,
                    )
                )
            else:
                existing.variant_name = item.variant_name
                existing.equation = item.equation
                existing.cycle_energy_demand = item.cycle_energy_demand
                existing.co2 = item.co2

        await self.session.flush()
        await self.session.refresh(vehicle)
        return vehicle

    async def export_rows(self, filters: VehicleFilterParams) -> list[Vehicle]:
        stmt = (
            self._apply_filters(self._active(), filters)
            .options(selectinload(Vehicle.variants))
            .order_by(Vehicle.base_model_name, Vehicle.id)
        )
        vehicles = list((await self.session.scalars(stmt)).unique().all())
        return vehicles

    async def soft_delete(self, vehicle: Vehicle) -> None:
        vehicle.deleted_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def ping(self) -> bool:
        result = await self.session.scalar(select(1))
        return result == 1
