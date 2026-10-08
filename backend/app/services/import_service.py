"""Excel preview and transactional import."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import mark_vehicle_cache_dirty
from app.core.exceptions import AppError, ValidationAppError
from app.core.logging import get_logger
from app.core.security import CurrentUser
from app.models.variant import Variant
from app.repositories.import_repository import ImportRepository
from app.repositories.vehicle_repository import VehicleRepository
from app.schemas.imports import (
    ImportIssue,
    ImportMode,
    ImportPreviewResponse,
    ImportResultResponse,
)
from app.models.vehicle import Vehicle
from app.utils.excel import ParsedVehicle, ParsedWorkbook, ParseIssue, parse_workbook, validate_upload

logger = get_logger(__name__)


class ImportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.vehicles = VehicleRepository(session)
        self.jobs = ImportRepository(session)

    async def preview(self, content: bytes, file_name: str, max_bytes: int) -> ImportPreviewResponse:
        parsed = self._parse(content, file_name, max_bytes)
        existing = await self.vehicles.get_by_names([item.base_model_name for item in parsed.vehicles])

        new_vehicles = 0
        existing_vehicles = 0
        new_variants = 0
        duplicate_variants = 0
        for group in parsed.vehicles:
            current = existing.get(group.base_model_name.lower())
            if current is None:
                new_vehicles += 1
                new_variants += len(group.variants)
            else:
                existing_vehicles += 1
                existing_names = {variant.variant_name.lower() for variant in current.variants}
                new_variants += sum(1 for item in group.variants if item.name.lower() not in existing_names)
            duplicate_variants += len(group.duplicate_variant_names)

        errors = [ImportIssue(row=item.row, field=item.field, message=item.message) for item in parsed.errors]
        warnings = [ImportIssue(row=item.row, field=item.field, message=item.message) for item in parsed.warnings]
        return ImportPreviewResponse(
            file_name=file_name,
            total_rows=parsed.total_rows,
            base_models_detected=len(parsed.vehicles),
            variants_detected=sum(len(item.variants) for item in parsed.vehicles),
            new_vehicles=new_vehicles,
            existing_vehicles=existing_vehicles,
            new_variants=new_variants,
            duplicate_variants=duplicate_variants,
            warnings=warnings,
            errors=errors,
            can_import=len(errors) == 0 and len(parsed.vehicles) > 0,
        )

    async def import_workbook(
        self,
        content: bytes,
        file_name: str,
        max_bytes: int,
        mode: ImportMode,
        user: CurrentUser,
    ) -> ImportResultResponse:
        started = datetime.now(timezone.utc)
        parsed = self._parse(content, file_name, max_bytes)
        if parsed.errors:
            raise ValidationAppError("The workbook contains validation errors and cannot be imported")

        logger.info("excel_import_start", file_name=file_name, mode=mode, total_rows=parsed.total_rows)
        existing = await self.vehicles.get_by_names([item.base_model_name for item in parsed.vehicles])

        created_vehicles = 0
        updated_vehicles = 0
        created_variants = 0
        skipped_variants = sum(len(item.duplicate_variant_names) for item in parsed.vehicles)

        try:
            for group in parsed.vehicles:
                vehicle = existing.get(group.base_model_name.lower())
                if vehicle is None:
                    vehicle = await self._create_from_group(group)
                    existing[group.base_model_name.lower()] = vehicle
                    created_vehicles += 1
                    created_variants += len(group.variants)
                    continue

                updated_vehicles += 1
                vehicle.rlf_id = group.identifiers.get("rlf_id")
                vehicle.rm_id = group.identifiers.get("rm_id")
                vehicle.ip_id = group.identifiers.get("ip_id")
                vehicle.evap_id = group.identifiers.get("evap_id")
                vehicle.pr_id = group.identifiers.get("pr_id")
                vehicle.df_id = group.identifiers.get("df_id")
                vehicle.ob_id = group.identifiers.get("ob_id")
                vehicle.er_id = group.identifiers.get("er_id")
                vehicle.pems_id = group.identifiers.get("pems_id")

                incoming = {item.name.lower(): item for item in group.variants}
                existing_names = {variant.variant_name.lower(): variant for variant in vehicle.variants}

                if mode == ImportMode.REPLACE:
                    for key, variant in list(existing_names.items()):
                        if key not in incoming:
                            vehicle.variants.remove(variant)

                for key, item in incoming.items():
                    existing_variant = existing_names.get(key)
                    if existing_variant is None:
                        vehicle.variants.append(
                            Variant(
                                variant_name=item.name,
                                equation=item.equation,
                                cycle_energy_demand=item.cycle_energy_demand,
                                co2=item.co2,
                            )
                        )
                        created_variants += 1
                    else:
                        if item.equation is not None:
                            existing_variant.equation = item.equation
                        if item.cycle_energy_demand is not None:
                            existing_variant.cycle_energy_demand = item.cycle_energy_demand
                        if item.co2 is not None:
                            existing_variant.co2 = item.co2

            await self.session.flush()
            job = await self.jobs.create_completed(
                file_name=file_name,
                total_rows=parsed.total_rows,
                processed_rows=parsed.total_rows,
                created_records=created_vehicles,
                updated_records=updated_vehicles,
                failed_rows=0,
                created_by=user.username,
                started_at=started,
            )
            mark_vehicle_cache_dirty(self.session)
        except Exception as exc:
            await self.session.rollback()
            logger.error("excel_import_failed", file_name=file_name)
            raise AppError("An unexpected error occurred while importing the workbook.", status_code=500) from exc

        logger.info(
            "excel_import_end",
            file_name=file_name,
            created_vehicles=created_vehicles,
            updated_vehicles=updated_vehicles,
            created_variants=created_variants,
        )
        return ImportResultResponse(
            file_name=file_name,
            mode=mode,
            total_rows=parsed.total_rows,
            created_vehicles=created_vehicles,
            updated_vehicles=updated_vehicles,
            created_variants=created_variants,
            skipped_variants=skipped_variants,
            warnings=[
                ImportIssue(row=item.row, field=item.field, message=item.message) for item in parsed.warnings
            ],
            errors=[],
            job_id=job.id,
        )

    def _parse(self, content: bytes, file_name: str, max_bytes: int) -> ParsedWorkbook:
        validate_upload(file_name, content, max_bytes)
        parsed = parse_workbook(content, file_name)
        if parsed.total_rows == 0 and not parsed.errors:
            parsed.errors.append(
                ParseIssue(row=None, field="file", message="The workbook contains no data rows")
            )
        return parsed

    async def _create_from_group(self, group: ParsedVehicle) -> Vehicle:
        vehicle = Vehicle(
            base_model_name=group.base_model_name,
            rlf_id=group.identifiers.get("rlf_id"),
            rm_id=group.identifiers.get("rm_id"),
            ip_id=group.identifiers.get("ip_id"),
            evap_id=group.identifiers.get("evap_id"),
            pr_id=group.identifiers.get("pr_id"),
            df_id=group.identifiers.get("df_id"),
            ob_id=group.identifiers.get("ob_id"),
            er_id=group.identifiers.get("er_id"),
            pems_id=group.identifiers.get("pems_id"),
            variants=[
                Variant(
                    variant_name=item.name,
                    equation=item.equation,
                    cycle_energy_demand=item.cycle_energy_demand,
                    co2=item.co2,
                )
                for item in group.variants
            ],
        )
        self.session.add(vehicle)
        await self.session.flush()
        return vehicle
