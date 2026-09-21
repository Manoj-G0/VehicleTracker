"""Variant request/response schemas."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VariantCreate(BaseModel):
    variant_name: str = Field(..., min_length=1, max_length=512)

    @field_validator("variant_name")
    @classmethod
    def _trim(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Variant name is required")
        return trimmed


class VariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    variant_name: str


class VariantPage(BaseModel):
    items: list[VariantRead]
    page: int
    page_size: int
    total: int
    total_pages: int
