"""Variant child records belonging to a base vehicle model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.vehicle import Vehicle


class Variant(TimestampMixin, Base):
    __tablename__ = "variants"
    __table_args__ = (
        UniqueConstraint("vehicle_id", "variant_name", name="uq_variants_vehicle_id_variant_name"),
        Index("ix_variants_name", "variant_name"),
        Index("ix_variants_vehicle_id", "vehicle_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("vehicles.id", ondelete="CASCADE"),
        nullable=False,
    )
    variant_name: Mapped[str] = mapped_column(String(512), nullable=False)

    vehicle: Mapped[Vehicle] = relationship(back_populates="variants")
