"""User repository for authentication and admin management."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.password_reset import PasswordResetVerification
from app.models.registration_verification import RegistrationVerification
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

    async def get_registration_verification(self, email: str) -> RegistrationVerification | None:
        normalized = email.strip().lower()
        return await self.session.scalar(
            select(RegistrationVerification).where(
                func.lower(RegistrationVerification.email) == normalized,
                RegistrationVerification.is_active.is_(True),
            )
        )

    async def create_registration_verification(
        self,
        *,
        username: str,
        email: str,
        password_hash: str,
        otp_hash: str,
        expires_at,
    ) -> RegistrationVerification:
        item = RegistrationVerification(
            username=username.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
            otp_hash=otp_hash,
            expires_at=expires_at,
            attempt_count=0,
            last_requested_at=datetime.now(timezone.utc),
            is_active=True,
        )
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def update_registration_verification(
        self,
        verification: RegistrationVerification,
        *,
        otp_hash: str | None = None,
        expires_at=None,
        attempt_count: int | None = None,
        last_requested_at=None,
    ) -> RegistrationVerification:
        if otp_hash is not None:
            verification.otp_hash = otp_hash
        if expires_at is not None:
            verification.expires_at = expires_at
        if attempt_count is not None:
            verification.attempt_count = attempt_count
        if last_requested_at is not None:
            verification.last_requested_at = last_requested_at
        await self.session.flush()
        return verification

    async def get_password_reset_verification(self, user_id: int) -> PasswordResetVerification | None:
        return await self.session.scalar(
            select(PasswordResetVerification).where(
                PasswordResetVerification.user_id == user_id,
                PasswordResetVerification.is_active.is_(True),
            )
        )

    async def create_password_reset_verification(
        self,
        *,
        user_id: int,
        otp_hash: str,
        expires_at,
    ) -> PasswordResetVerification:
        item = PasswordResetVerification(
            user_id=user_id,
            otp_hash=otp_hash,
            expires_at=expires_at,
            attempt_count=0,
            last_requested_at=datetime.now(timezone.utc),
            is_active=True,
        )
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def update_password_reset_verification(
        self,
        verification: PasswordResetVerification,
        *,
        otp_hash: str | None = None,
        expires_at=None,
        attempt_count: int | None = None,
        last_requested_at=None,
        clear_verified_at: bool = False,
    ) -> PasswordResetVerification:
        if otp_hash is not None:
            verification.otp_hash = otp_hash
        if expires_at is not None:
            verification.expires_at = expires_at
        if attempt_count is not None:
            verification.attempt_count = attempt_count
        if last_requested_at is not None:
            verification.last_requested_at = last_requested_at
        if clear_verified_at:
            verification.verified_at = None
        await self.session.flush()
        return verification

    async def revoke_refresh_tokens(self, user_id: int) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )

    async def list_users(self) -> list[User]:
        stmt = self._active().order_by(User.username)
        return list((await self.session.scalars(stmt)).all())

    async def create(
        self,
        payload: UserCreate,
        password_hash: str,
        allow_access: bool | None = None,
        is_active: bool | None = None,
    ) -> User:
        user = User(
            username=payload.username.strip(),
            email=payload.email.strip().lower(),
            password_hash=password_hash,
            role=payload.role.upper(),
            allow_access=payload.allow_access if allow_access is None else allow_access,
            is_active=payload.is_active if is_active is None else is_active,
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
