"""Shared test fixtures. Requires PostgreSQL (see DATABASE_URL)."""

import asyncio
import sys
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import bcrypt

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models.vehicle import Vehicle  # noqa: F401
from app.models.user import User
from app.services.user_service import UserService

settings = get_settings()
TEST_DATABASE_URL = settings.database_url

engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestSession = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(autouse=True)
async def clean_db() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM import_jobs"))
        await conn.execute(text("DELETE FROM variants"))
        await conn.execute(text("DELETE FROM vehicles"))
        await conn.execute(text("DELETE FROM refresh_tokens"))
        await conn.execute(text("DELETE FROM password_reset_verifications"))
        await conn.execute(text("DELETE FROM registration_verifications"))
        await conn.execute(text("DELETE FROM users"))
    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_token() -> AsyncGenerator[str, None]:
    async with TestSession() as session:
        user = User(
            username="fixture-admin",
            email="fixture-admin@example.com",
            password_hash=bcrypt.hashpw(b"FixturePass123!", bcrypt.gensalt()).decode("utf-8"),
            role="ADMIN",
            allow_access=True,
            is_active=True,
        )
        session.add(user)
        await session.flush()
        token = UserService._create_token(user)
        await session.commit()
        yield token


@pytest.fixture
async def client(admin_token: str) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {admin_token}"},
    ) as ac:
        yield ac


def sample_vehicle_payload(**overrides):
    payload = {
        "base_model_name": "Kia Sorento Smartstream G1.6 T-GDI AT HTX 6",
        "rlf_id": "RL-123",
        "rm_id": None,
        "ip_id": "IP-123",
        "evap_id": "EV-123",
        "pr_id": None,
        "df_id": None,
        "ob_id": "OB-123",
        "er_id": None,
        "pems_id": "PEMS-123",
        "variants": [{"variant_name": "HTX 6"}, {"variant_name": "HTX 7"}],
    }
    payload.update(overrides)
    return payload
