"""Add vehicle band columns and OTP verification tables.

Revision ID: 0004_vehicle_bands_and_otp
Revises: 0003_refresh_tokens
Create Date: 2026-09-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_vehicle_bands_and_otp"
down_revision: Union[str, Sequence[str], None] = "0003_refresh_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns("vehicles")]

    if "rm_rlf_band" not in columns:
        op.add_column("vehicles", sa.Column("rm_rlf_band", sa.String(length=64), nullable=True))
    if "ip_band" not in columns:
        op.add_column("vehicles", sa.Column("ip_band", sa.String(length=64), nullable=True))
    
    op.create_table(
        "registration_verifications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_registration_verifications_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_registration_verifications"),
    )
    op.create_index("ix_registration_verifications_email", "registration_verifications", ["email"])

    op.create_table(
        "password_reset_verifications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("otp_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_password_reset_verifications_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_password_reset_verifications"),
    )


def downgrade() -> None:
    op.drop_table("password_reset_verifications")
    op.drop_index("ix_registration_verifications_email", table_name="registration_verifications")
    op.drop_table("registration_verifications")
    op.drop_column("vehicles", "ip_band")
    op.drop_column("vehicles", "rm_rlf_band")
