"""User service with secure hashing and role checks."""

from __future__ import annotations

import bcrypt
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import status

from app.core.config import get_settings
from app.core.exceptions import AppError, ConflictError, NotFoundError, ValidationAppError
from app.repositories.user_repository import UserRepository
from app.schemas.user import AuthToken, PasswordChange, TokenPair, UserCreate, UserRead, UserRegistration, UserUpdate
from app.models.user import User


class UserService:
    def __init__(self, session):
        self.session = session
        self.repository = UserRepository(session)

    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    @staticmethod
    def _create_token(user: User) -> str:
        settings = get_settings()
        payload = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
            "allow_access": user.allow_access,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @staticmethod
    def _hash_refresh_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    async def _issue_token_pair(self, user: User) -> TokenPair:
        settings = get_settings()
        raw_refresh = secrets.token_urlsafe(48)
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        await self.repository.create_refresh_token(user.id, self._hash_refresh_token(raw_refresh), expires_at)
        return TokenPair(
            access_token=self._create_token(user),
            refresh_token=raw_refresh,
            user=UserRead.model_validate(user),
        )

    async def login(self, username: str, password: str) -> TokenPair:
        user = await self.repository.get_by_username(username)
        if user is None:
            raise AppError("Invalid username or password", status_code=status.HTTP_401_UNAUTHORIZED)
        if not user.allow_access or not user.is_active:
            raise AppError("Your account does not currently have access to the application. Please contact an administrator.", status_code=status.HTTP_401_UNAUTHORIZED)
        if not self._verify_password(password, user.password_hash):
            raise AppError("Invalid username or password", status_code=status.HTTP_401_UNAUTHORIZED)
        pair = await self._issue_token_pair(user)
        return TokenPair.model_validate(pair)

    async def register(self, payload: UserRegistration) -> UserRead:
        if await self.repository.get_by_username(payload.username):
            raise ConflictError("A user with this username already exists", field="username")
        if await self.repository.get_by_email(payload.email):
            raise ConflictError("A user with this email already exists", field="email")
        user = await self.repository.create(
            UserCreate(username=payload.username, email=payload.email, password=payload.password),
            self._hash_password(payload.password),
            allow_access=False,
        )
        return UserRead.model_validate(user)

    async def create_user(self, payload: UserCreate) -> UserRead:
        if await self.repository.get_by_username(payload.username):
            raise ConflictError("A user with this username already exists", field="username")
        if await self.repository.get_by_email(payload.email):
            raise ConflictError("A user with this email already exists", field="email")
        password = payload.password or get_settings().default_user_password
        password_hash = self._hash_password(password)
        user = await self.repository.create(payload, password_hash)
        return UserRead.model_validate(user)

    async def list_users(self) -> list[UserRead]:
        users = await self.repository.list_users()
        return [UserRead.model_validate(user) for user in users]

    async def get_user(self, user_id: int) -> UserRead:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return UserRead.model_validate(user)

    async def update_user(self, user_id: int, payload: UserUpdate) -> UserRead:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        if payload.username is not None and payload.username.strip() != user.username:
            existing = await self.repository.get_by_username(payload.username)
            if existing and existing.id != user.id:
                raise ConflictError("A user with this username already exists", field="username")
        if payload.email is not None and payload.email.strip().lower() != user.email.lower():
            existing = await self.repository.get_by_email(payload.email)
            if existing and existing.id != user.id:
                raise ConflictError("A user with this email already exists", field="email")
        password_hash = None
        if payload.password is not None:
            password_hash = self._hash_password(payload.password)
        updated = await self.repository.update(user, payload, password_hash)
        if payload.allow_access is False:
            await self.repository.revoke_refresh_tokens(user.id)
        return UserRead.model_validate(updated)

    async def delete_user(self, user_id: int) -> None:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        await self.repository.delete(user)

    async def get_profile(self, user_id: int) -> UserRead:
        return await self.get_user(user_id)

    async def change_password(self, user_id: int, payload: PasswordChange) -> None:
        user = await self.repository.get_by_id(user_id)
        if user is None or not self._verify_password(payload.current_password, user.password_hash):
            raise AppError("Current password is incorrect", status_code=status.HTTP_400_BAD_REQUEST)
        user.password_hash = self._hash_password(payload.new_password)
        await self.repository.revoke_refresh_tokens(user.id)
        await self.session.flush()

    async def refresh(self, raw_token: str) -> TokenPair:
        token = await self.repository.get_refresh_token(self._hash_refresh_token(raw_token))
        now = datetime.now(timezone.utc)
        if token is None or token.revoked_at is not None or token.expires_at <= now:
            raise AppError("Invalid or expired refresh token", status_code=status.HTTP_401_UNAUTHORIZED)
        user = await self.repository.get_by_id(token.user_id)
        if user is None or not user.is_active or not user.allow_access:
            raise AppError("Your account does not currently have access to the application", status_code=status.HTTP_401_UNAUTHORIZED)
        token.revoked_at = now
        await self.session.flush()
        return await self._issue_token_pair(user)

    async def logout(self, raw_token: str) -> None:
        token = await self.repository.get_refresh_token(self._hash_refresh_token(raw_token))
        if token is not None and token.revoked_at is None:
            token.revoked_at = datetime.now(timezone.utc)
            await self.session.flush()
