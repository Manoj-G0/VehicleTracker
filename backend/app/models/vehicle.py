"""Vehicle master model. Identifier columns are not unique; OB ID may repeat."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.variant import Variant


class Vehicle(TimestampMixin, Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        Index(
            "uq_vehicles_base_model_name_active",
            "base_model_name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_vehicles_rlf_id", "rlf_id"),
        Index("ix_vehicles_rm_id", "rm_id"),
        Index("ix_vehicles_ip_id", "ip_id"),
        Index("ix_vehicles_evap_id", "evap_id"),
        Index("ix_vehicles_pr_id", "pr_id"),
        Index("ix_vehicles_df_id", "df_id"),
        Index("ix_vehicles_ob_id", "ob_id"),
        Index("ix_vehicles_er_id", "er_id"),
        Index("ix_vehicles_pems_id", "pems_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    base_model_name: Mapped[str] = mapped_column(String(512), nullable=False)
    rlf_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rm_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    evap_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pr_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    df_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ob_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    er_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pems_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    variants: Mapped[list[Variant]] = relationship(
        back_populates="vehicle",
        cascade="all, delete-orphan",
        lazy="noload",
        order_by="Variant.variant_name",
    )
