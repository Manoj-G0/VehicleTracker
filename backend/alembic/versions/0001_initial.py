"""Initial schema: vehicles, variants, import_jobs.

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vehicles",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("base_model_name", sa.String(length=512), nullable=False),
        sa.Column("rlf_id", sa.String(length=255), nullable=True),
        sa.Column("rm_id", sa.String(length=255), nullable=True),
        sa.Column("ip_id", sa.String(length=255), nullable=True),
        sa.Column("rm_rlf_band", sa.String(length=64), nullable=True),
        sa.Column("ip_band", sa.String(length=64), nullable=True),
        sa.Column("evap_id", sa.String(length=255), nullable=True),
        sa.Column("pr_id", sa.String(length=255), nullable=True),
        sa.Column("df_id", sa.String(length=255), nullable=True),
        sa.Column("ob_id", sa.String(length=255), nullable=True),
        sa.Column("er_id", sa.String(length=255), nullable=True),
        sa.Column("pems_id", sa.String(length=255), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_vehicles"),
    )
    op.create_index(
        "uq_vehicles_base_model_name_active",
        "vehicles",
        ["base_model_name"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_vehicles_rlf_id", "vehicles", ["rlf_id"])
    op.create_index("ix_vehicles_rm_id", "vehicles", ["rm_id"])
    op.create_index("ix_vehicles_ip_id", "vehicles", ["ip_id"])
    op.create_index("ix_vehicles_evap_id", "vehicles", ["evap_id"])
    op.create_index("ix_vehicles_pr_id", "vehicles", ["pr_id"])
    op.create_index("ix_vehicles_df_id", "vehicles", ["df_id"])
    op.create_index("ix_vehicles_ob_id", "vehicles", ["ob_id"])
    op.create_index("ix_vehicles_er_id", "vehicles", ["er_id"])
    op.create_index("ix_vehicles_pems_id", "vehicles", ["pems_id"])

    op.create_table(
        "variants",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("vehicle_id", sa.BigInteger(), nullable=False),
        sa.Column("variant_name", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            name="fk_variants_vehicle_id_vehicles",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_variants"),
        sa.UniqueConstraint("vehicle_id", "variant_name", name="uq_variants_vehicle_id_variant_name"),
    )
    op.create_index("ix_variants_name", "variants", ["variant_name"])
    op.create_index("ix_variants_vehicle_id", "variants", ["vehicle_id"])

    op.create_table(
        "import_jobs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_import_jobs"),
    )


def downgrade() -> None:
    op.drop_table("import_jobs")
    op.drop_index("ix_variants_vehicle_id", table_name="variants")
    op.drop_index("ix_variants_name", table_name="variants")
    op.drop_table("variants")
    op.drop_index("ix_vehicles_pems_id", table_name="vehicles")
    op.drop_index("ix_vehicles_er_id", table_name="vehicles")
    op.drop_index("ix_vehicles_ob_id", table_name="vehicles")
    op.drop_index("ix_vehicles_df_id", table_name="vehicles")
    op.drop_index("ix_vehicles_pr_id", table_name="vehicles")
    op.drop_index("ix_vehicles_evap_id", table_name="vehicles")
    op.drop_index("ix_vehicles_ip_id", table_name="vehicles")
    op.drop_index("ix_vehicles_rm_id", table_name="vehicles")
    op.drop_index("ix_vehicles_rlf_id", table_name="vehicles")
    op.drop_index("uq_vehicles_base_model_name_active", table_name="vehicles")
    op.drop_table("vehicles")
