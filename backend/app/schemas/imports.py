"""Excel import request/response schemas."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ImportMode(StrEnum):
    UPSERT = "upsert"
    REPLACE = "replace"


class ImportIssue(BaseModel):
    row: int | None = None
    field: str | None = None
    message: str


class ImportPreviewResponse(BaseModel):
    file_name: str
    total_rows: int
    base_models_detected: int
    variants_detected: int
    new_vehicles: int
    existing_vehicles: int
    new_variants: int
    duplicate_variants: int
    warnings: list[ImportIssue] = Field(default_factory=list)
    errors: list[ImportIssue] = Field(default_factory=list)
    can_import: bool


class ImportResultResponse(BaseModel):
    file_name: str
    mode: ImportMode
    total_rows: int
    created_vehicles: int
    updated_vehicles: int
    created_variants: int
    skipped_variants: int
    warnings: list[ImportIssue] = Field(default_factory=list)
    errors: list[ImportIssue] = Field(default_factory=list)
    job_id: int | None = None
