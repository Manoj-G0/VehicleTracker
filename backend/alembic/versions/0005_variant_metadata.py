"""Add variant metadata columns for equations and emissions data.

Revision ID: 0005_variant_metadata
Revises: 0004_vehicle_bands_and_otp
Create Date: 2026-09-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_variant_metadata"
down_revision: Union[str, Sequence[str], None] = "0004_vehicle_bands_and_otp"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("variants", sa.Column("equation", sa.String(length=1024), nullable=True))
    op.add_column("variants", sa.Column("cycle_energy_demand", sa.String(length=255), nullable=True))
    op.add_column("variants", sa.Column("co2", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("variants", "co2")
    op.drop_column("variants", "cycle_energy_demand")
    op.drop_column("variants", "equation")
