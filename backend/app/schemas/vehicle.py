"""Vehicle request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.variant import VariantCreate, VariantRead
from app.utils.normalization import normalize_identifier


class VehicleFilterParams(BaseModel):
    base_model_name: str | None = None
    rlf_id: str | None = None
    rm_id: str | None = None
    ip_id: str | None = None
    evap_id: str | None = None
    pr_id: str | None = None
    df_id: str | None = None
    ob_id: str | None = None
    er_id: str | None = None
    pems_id: str | None = None
    variant_name: str | None = None

    @field_validator(
        "base_model_name",
        "rlf_id",
        "rm_id",
        "ip_id",
        "evap_id",
        "pr_id",
        "df_id",
        "ob_id",
        "er_id",
        "pems_id",
        "variant_name",
        mode="before",
    )
    @classmethod
    def _empty_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = str(value).strip()
        return trimmed or None


class VehicleBase(BaseModel):
    base_model_name: str = Field(..., min_length=1, max_length=512)
    rlf_id: str | None = Field(default=None, max_length=255)
    rm_id: str | None = Field(default=None, max_length=255)
    ip_id: str | None = Field(default=None, max_length=255)
    evap_id: str | None = Field(default=None, max_length=255)
    pr_id: str | None = Field(default=None, max_length=255)
    df_id: str | None = Field(default=None, max_length=255)
    ob_id: str | None = Field(default=None, max_length=255)
    er_id: str | None = Field(default=None, max_length=255)
    pems_id: str | None = Field(default=None, max_length=255)

    @field_validator("base_model_name")
    @classmethod
    def _trim_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Base model name is required")
        return trimmed

    @field_validator(
        "rlf_id",
        "rm_id",
        "ip_id",
        "evap_id",
        "pr_id",
        "df_id",
        "ob_id",
        "er_id",
        "pems_id",
        mode="before",
    )
    @classmethod
    def _normalize_ids(cls, value: str | None) -> str | None:
        return normalize_identifier(value)


class VehicleCreate(VehicleBase):
    variants: list[VariantCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_variants(self) -> "VehicleCreate":
        names = [item.variant_name.lower() for item in self.variants]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate variants for the same vehicle are not allowed")
        return self


class VehicleUpdate(VehicleCreate):
    pass


class VehicleListItem(VehicleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    variant_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class VehicleRead(VehicleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    variants: list[VariantRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class VehiclePage(BaseModel):
    items: list[VehicleListItem]
    page: int
    page_size: int
    total: int
    total_pages: int
