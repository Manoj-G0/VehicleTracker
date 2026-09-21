"""User repository for authentication and admin management."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.models.refresh_token import RefreshToken


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _active(self) -> Select[tuple[User]]:
        return select(User)

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.scalar(self._active().where(User.id == user_id))

    async def get_by_username(self, username: str) -> User | None:
        normalized = username.strip()
        return await self.session.scalar(self._active().where(func.lower(User.username) == normalized.lower()))

    async def get_by_email(self, email: str) -> User | None:
        normalized = email.strip().lower()
        return await self.session.scalar(self._active().where(func.lower(User.email) == normalized))

    async def list_users(self) -> list[User]:
        stmt = self._active().order_by(User.username)
        return list((await self.session.scalars(stmt)).all())

    async def create(self, payload: UserCreate, password_hash: str, allow_access: bool | None = None) -> User:
        user = User(
            username=payload.username.strip(),
            email=payload.email.strip().lower(),
            password_hash=password_hash,
            role=payload.role.upper(),
            allow_access=payload.allow_access if allow_access is None else allow_access,
            is_active=payload.is_active,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def create_refresh_token(self, user_id: int, token_hash: str, expires_at) -> RefreshToken:
        token = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_refresh_token(self, token_hash: str) -> RefreshToken | None:
        return await self.session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    async def revoke_refresh_tokens(self, user_id: int) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )

    async def update(self, user: User, payload: UserUpdate, password_hash: str | None = None) -> User:
        if payload.username is not None:
            user.username = payload.username.strip()
        if payload.email is not None:
            user.email = payload.email.strip().lower()
        if payload.role is not None:
            user.role = payload.role.upper()
        if payload.allow_access is not None:
            user.allow_access = payload.allow_access
        if payload.is_active is not None:
            user.is_active = payload.is_active
        if password_hash is not None:
            user.password_hash = password_hash
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.session.delete(user)
        await self.session.flush()
