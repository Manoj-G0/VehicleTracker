"""JWT authentication and role-based access control."""

from __future__ import annotations

from enum import StrEnum

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.db.session import SessionLocal


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    USER = "USER"


class CurrentUser:
    def __init__(self, id: int, username: str, email: str, role: UserRole, allow_access: bool, is_active: bool) -> None:
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.allow_access = allow_access
        self.is_active = is_active


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if not credentials:
        raise AppError("Authentication required", status_code=status.HTTP_401_UNAUTHORIZED)

    try:
        token = jwt.decode(credentials.credentials, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise AppError("Invalid or expired token", status_code=status.HTTP_401_UNAUTHORIZED) from exc

    user_id = token.get("sub")
    if user_id is None:
        raise AppError("Invalid token payload", status_code=status.HTTP_401_UNAUTHORIZED)

    async with SessionLocal() as session:
        user = await UserRepository(session).get_by_id(int(user_id))
    if user is None:
        raise AppError("User not found", status_code=status.HTTP_401_UNAUTHORIZED)
    if not user.allow_access or not user.is_active:
        raise AppError("Your account does not currently have access to the application. Please contact an administrator.", status_code=status.HTTP_401_UNAUTHORIZED)
    role = UserRole(user.role.upper())
    return CurrentUser(user.id, user.username, user.email, role, user.allow_access, user.is_active)


def require_roles(*allowed: UserRole):
    async def _checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed and user.role != UserRole.ADMIN:
            raise AppError("Insufficient permission", status_code=status.HTTP_403_FORBIDDEN)
        return user

    return _checker


require_authenticated_user = require_roles(UserRole.USER, UserRole.ADMIN)
require_viewer = require_roles(UserRole.USER, UserRole.ADMIN)
require_importer = require_roles(UserRole.ADMIN)
require_admin = require_roles(UserRole.ADMIN)
