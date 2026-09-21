"""Alembic environment. Schema is managed only via migrations."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

from app.core.config import get_settings
from app.db.base import Base
from app.models import ImportJob, Variant, Vehicle  # noqa: F401

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    # Alembic uses a synchronous engine. Convert asyncpg URL if needed.
    url = config.get_main_option("sqlalchemy.url", "")
    if url.startswith("postgresql+asyncpg://"):
        sync_url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        connectable = engine_from_config(
            {**config.get_section(config.config_ini_section, {}), "sqlalchemy.url": sync_url},
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
