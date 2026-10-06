"""Authentication endpoints for JWT login and token validation."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import CurrentUser, require_authenticated_user
from app.db.session import get_db
from app.schemas.user import (
    EmailOtpRequest,
    PasswordChange,
    RefreshRequest,
    ResetPasswordRequest,
    ResetPasswordVerifyRequest,
    TokenPair,
    UserLogin,
    UserRead,
    UserRegistration,
    VerifyRegistrationRequest,
)
from app.services.user_service import UserService

router = APIRouter()


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


@router.get("/auth/health", summary="Auth readiness")
async def auth_health() -> dict[str, str | bool]:
    return {"status": "ok", "ready": True}


@router.post("/auth/register", status_code=status.HTTP_200_OK)
async def register(payload: UserRegistration, service: UserService = Depends(get_user_service)) -> dict[str, str | int]:
    return await service.register(payload)


@router.post("/auth/register/verify", status_code=status.HTTP_200_OK)
async def verify_registration(
    payload: VerifyRegistrationRequest,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    return await service.verify_registration(payload)


@router.post("/auth/register/resend", status_code=status.HTTP_200_OK)
async def resend_registration_otp(
    payload: EmailOtpRequest,
    service: UserService = Depends(get_user_service),
) -> dict[str, str | int]:
    return await service.resend_registration_otp(payload.email)


@router.post("/auth/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    payload: EmailOtpRequest,
    service: UserService = Depends(get_user_service),
) -> dict[str, str | int]:
    return await service.forgot_password(payload.email)


@router.post("/auth/forgot-password/verify", status_code=status.HTTP_200_OK)
async def verify_forgot_password(
    payload: ResetPasswordVerifyRequest,
    service: UserService = Depends(get_user_service),
) -> dict[str, str]:
    return await service.verify_password_reset(payload)


@router.post("/auth/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    payload: ResetPasswordRequest,
    service: UserService = Depends(get_user_service),
) -> dict[str, str]:
    return await service.reset_password(payload)


@router.post("/auth/login", response_model=TokenPair, status_code=status.HTTP_200_OK)
async def login(payload: UserLogin, service: UserService = Depends(get_user_service)) -> TokenPair:
    return await service.login(payload.username, payload.password)


@router.post("/auth/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, service: UserService = Depends(get_user_service)) -> TokenPair:
    return await service.refresh(payload.refresh_token)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, service: UserService = Depends(get_user_service)) -> None:
    await service.logout(payload.refresh_token)


@router.post("/auth/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChange,
    user: CurrentUser = Depends(require_authenticated_user),
    service: UserService = Depends(get_user_service),
) -> None:
    await service.change_password(user.id, payload)


@router.get("/auth/me", response_model=UserRead)
async def me(user: CurrentUser = Depends(require_authenticated_user)) -> UserRead:
    return UserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        allow_access=user.allow_access,
        is_active=user.is_active,
    )
