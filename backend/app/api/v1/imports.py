"""Excel preview and import APIs."""

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import CurrentUser, require_importer
from app.db.session import get_db
from app.schemas.imports import ImportMode, ImportPreviewResponse, ImportResultResponse
from app.services.import_service import ImportService

router = APIRouter()


def get_import_service(db: AsyncSession = Depends(get_db)) -> ImportService:
    return ImportService(db)


@router.post(
    "/imports/vehicles/preview",
    response_model=ImportPreviewResponse,
    summary="Preview Excel import",
    description="Validates an .xlsx workbook and reports counts without modifying the database.",
    responses={400: {"description": "Invalid file"}, 413: {"description": "File too large"}},
)
async def preview_import(
    file: UploadFile = File(...),
    service: ImportService = Depends(get_import_service),
    settings: Settings = Depends(get_settings),
    _: CurrentUser = Depends(require_importer),
) -> ImportPreviewResponse:
    content = await file.read()
    return await service.preview(content, file.filename or "upload.xlsx", settings.excel_max_file_size_bytes)


@router.post(
    "/imports/vehicles",
    response_model=ImportResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Commit Excel import",
    description="Transactionally upserts (default) or replaces vehicles from a validated workbook.",
    responses={400: {"description": "Validation failure"}, 413: {"description": "File too large"}},
)
async def commit_import(
    file: UploadFile = File(...),
    mode: ImportMode = Form(default=ImportMode.UPSERT),
    service: ImportService = Depends(get_import_service),
    settings: Settings = Depends(get_settings),
    user: CurrentUser = Depends(require_importer),
) -> ImportResultResponse:
    content = await file.read()
    return await service.import_workbook(
        content,
        file.filename or "upload.xlsx",
        settings.excel_max_file_size_bytes,
        mode,
        user,
    )
