"""Add vehicle manufacturer to vehicles.

Revision ID: 0006_vehicle_manufacturer
Revises: 0005_variant_metadata
Create Date: 2026-10-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_vehicle_manufacturer"
down_revision: Union[str, Sequence[str], None] = "0005_variant_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vehicles", sa.Column("vehicle_manufacturer", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("vehicles", "vehicle_manufacturer")
