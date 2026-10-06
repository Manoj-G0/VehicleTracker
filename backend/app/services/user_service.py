"""User service with secure hashing and role checks."""

from __future__ import annotations

import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import status

from app.core.config import get_settings
from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    AuthToken,
    PasswordChange,
    ResetPasswordRequest,
    ResetPasswordVerifyRequest,
    TokenPair,
    UserCreate,
    UserRead,
    UserRegistration,
    UserUpdate,
    VerifyRegistrationRequest,
)
from app.services.email_service import EmailService
from app.services.otp_service import OTPService


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

    @staticmethod
    def _normalise_email(email: str) -> str:
        return email.strip().lower()

    async def _send_registration_otp(self, username: str, email: str, password_hash: str) -> None:
        otp = OTPService.generate_otp()
        expires_at = OTPService.create_expires_at()
        existing = await self.repository.get_registration_verification(email)
        if existing is not None:
            await self.repository.update_registration_verification(
                existing,
                otp_hash=OTPService.hash_otp(otp),
                expires_at=expires_at,
                attempt_count=0,
                last_requested_at=datetime.now(timezone.utc),
            )
            await asyncio.to_thread(EmailService.send_otp_email, email, otp, purpose="registration")
            return
        await self.repository.create_registration_verification(
            username=username,
            email=email,
            password_hash=password_hash,
            otp_hash=OTPService.hash_otp(otp),
            expires_at=expires_at,
        )
        await asyncio.to_thread(EmailService.send_otp_email, email, otp, purpose="registration")

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

    async def register(self, payload: UserRegistration) -> dict[str, str | int]:
        username = payload.username.strip()
        email = self._normalise_email(payload.email)
        if await self.repository.get_by_username(username):
            raise ConflictError("A user with this username already exists", field="username")
        if await self.repository.get_by_email(email):
            raise ConflictError("A user with this email already exists", field="email")
        if await self.repository.get_registration_verification(email):
            raise ConflictError("A user with this email already exists", field="email")
        password_hash = self._hash_password(payload.password)
        await self._send_registration_otp(username, email, password_hash)
        return {
            "status": "otp_sent",
            "message": "Verification code sent to your email.",
            "resend_after_seconds": get_settings().otp_resend_cooldown_seconds,
        }

    async def verify_registration(self, payload: VerifyRegistrationRequest) -> UserRead:
        email = self._normalise_email(payload.email)
        verification = await self.repository.get_registration_verification(email)
        if verification is None:
            raise AppError("Registration request not found or expired", status_code=status.HTTP_400_BAD_REQUEST)
        if OTPService.is_expired(verification.expires_at):
            raise AppError("OTP expired. Please request a new one.", status_code=status.HTTP_400_BAD_REQUEST)
        if verification.username.strip().lower() != payload.username.strip().lower():
            raise AppError("Registration details do not match the request", status_code=status.HTTP_400_BAD_REQUEST)
        if verification.attempt_count >= get_settings().otp_max_attempts:
            raise AppError("Too many failed attempts. Please request a new OTP.", status_code=status.HTTP_400_BAD_REQUEST)
        if verification.otp_hash != OTPService.hash_otp(payload.otp):
            await self.repository.update_registration_verification(verification, attempt_count=(verification.attempt_count + 1))
            raise AppError("Invalid OTP", status_code=status.HTTP_400_BAD_REQUEST)

        role = "ADMIN" if email.lower() == get_settings().admin_email.lower() else "USER"
        user = await self.repository.get_by_email(email)
        if user is None:
            user = await self.repository.create(
                UserCreate(username=verification.username, email=email, password="TempPass123!", role=role),
                verification.password_hash,
                allow_access=True,
                is_active=True,
            )
        else:
            user.username = verification.username
            user.role = role
            user.password_hash = verification.password_hash
            user.allow_access = True
            user.is_active = True
            await self.session.flush()
        verification.is_active = False
        await self.session.flush()
        return UserRead.model_validate(user)

    async def resend_registration_otp(self, email: str) -> dict[str, str | int]:
        normalized = self._normalise_email(email)
        verification = await self.repository.get_registration_verification(normalized)
        if verification is None:
            raise NotFoundError("No pending registration found for this email")
        if verification.last_requested_at and datetime.now(timezone.utc) < verification.last_requested_at + timedelta(seconds=get_settings().otp_resend_cooldown_seconds):
            raise AppError("Please wait before requesting another OTP.", status_code=status.HTTP_429_TOO_MANY_REQUESTS)
        otp = OTPService.generate_otp()
        verification.otp_hash = OTPService.hash_otp(otp)
        verification.expires_at = OTPService.create_expires_at()
        verification.attempt_count = 0
        verification.last_requested_at = datetime.now(timezone.utc)
        await asyncio.to_thread(EmailService.send_otp_email, normalized, otp, purpose="registration")
        return {
            "status": "otp_sent",
            "message": "Verification code resent.",
            "resend_after_seconds": get_settings().otp_resend_cooldown_seconds,
        }

    async def forgot_password(self, email: str) -> dict[str, str | int]:
        normalized = self._normalise_email(email)
        user = await self.repository.get_by_email(normalized)
        if user is None:
            raise NotFoundError("No account found for this email")
        otp = OTPService.generate_otp()
        expires_at = OTPService.create_expires_at()
        existing = await self.repository.get_password_reset_verification(user.id)
        if existing is not None:
            now = datetime.now(timezone.utc)
            if existing.last_requested_at and now < existing.last_requested_at + timedelta(seconds=get_settings().otp_resend_cooldown_seconds):
                raise AppError("Please wait for the resend timer to finish before requesting another code.", status_code=status.HTTP_429_TOO_MANY_REQUESTS)
            await self.repository.update_password_reset_verification(
                existing,
                otp_hash=OTPService.hash_otp(otp),
                expires_at=expires_at,
                attempt_count=0,
                last_requested_at=now,
                clear_verified_at=True,
            )
        else:
            await self.repository.create_password_reset_verification(user_id=user.id, otp_hash=OTPService.hash_otp(otp), expires_at=expires_at)
        await asyncio.to_thread(EmailService.send_otp_email, normalized, otp, purpose="password reset")
        return {
            "status": "otp_sent",
            "message": "Password reset code sent to your email.",
            "resend_after_seconds": get_settings().otp_resend_cooldown_seconds,
        }

    async def verify_password_reset(self, payload: ResetPasswordVerifyRequest) -> dict[str, str]:
        user = await self.repository.get_by_email(self._normalise_email(payload.email))
        if user is None:
            raise NotFoundError("No account found for this email")
        verification = await self.repository.get_password_reset_verification(user.id)
        if verification is None:
            raise AppError("No password reset request found", status_code=status.HTTP_400_BAD_REQUEST)
        if verification.attempt_count >= get_settings().otp_max_attempts:
            raise AppError("Too many failed attempts. Please request a new OTP.", status_code=status.HTTP_400_BAD_REQUEST)
        if OTPService.is_expired(verification.expires_at):
            raise AppError("OTP expired. Please request a new one.", status_code=status.HTTP_400_BAD_REQUEST)
        if verification.otp_hash != OTPService.hash_otp(payload.otp):
            await self.repository.update_password_reset_verification(verification, attempt_count=(verification.attempt_count + 1))
            raise AppError("Invalid OTP", status_code=status.HTTP_400_BAD_REQUEST)

        verification.verified_at = datetime.now(timezone.utc)
        token_seed = f"{user.id}:{user.email.lower()}:{verification.expires_at.isoformat()}"
        token = f"{user.id}:{user.email.lower()}:{hashlib.sha256(token_seed.encode('utf-8')).hexdigest()}"
        await self.session.flush()
        return {"status": "verified", "token": token, "message": "OTP verified."}

    async def reset_password(self, payload: ResetPasswordRequest) -> dict[str, str]:
        parts = payload.token.split(":")
        if len(parts) != 3 or not parts[0].isdigit():
            raise AppError("Invalid reset token", status_code=status.HTTP_400_BAD_REQUEST)

        user_id = int(parts[0])
        email = parts[1].lower()
        user = await self.repository.get_by_id(user_id)
        if user is None or user.email.lower() != email:
            raise AppError("Invalid reset token", status_code=status.HTTP_400_BAD_REQUEST)

        reset_verification = await self.repository.get_password_reset_verification(user.id)
        if reset_verification is None or reset_verification.verified_at is None:
            raise AppError("Password reset is not verified. Please complete OTP verification first.", status_code=status.HTTP_400_BAD_REQUEST)
        if OTPService.is_expired(reset_verification.expires_at):
            raise AppError("OTP expired. Please request a new one.", status_code=status.HTTP_400_BAD_REQUEST)

        expected_seed = f"{user.id}:{user.email.lower()}:{reset_verification.expires_at.isoformat()}"
        expected_token = f"{user.id}:{user.email.lower()}:{hashlib.sha256(expected_seed.encode('utf-8')).hexdigest()}"
        if payload.token != expected_token:
            raise AppError("Invalid reset token", status_code=status.HTTP_400_BAD_REQUEST)

        if not payload.new_password or payload.new_password != payload.confirm_password:
            raise AppError("New password and confirmation must match", status_code=status.HTTP_400_BAD_REQUEST)

        user.password_hash = self._hash_password(payload.new_password)
        await self.repository.revoke_refresh_tokens(user.id)
        reset_verification.is_active = False
        await self.session.flush()
        return {"status": "updated", "message": "Password updated successfully."}

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

    async def delete_user(self, user_id: int, current_user_id: int | None = None) -> None:
        if current_user_id is not None and user_id == current_user_id:
            raise AppError("You cannot delete your own account.", status_code=status.HTTP_400_BAD_REQUEST)
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
        if payload.new_password == payload.current_password:
            raise AppError("New password must be different from the current password.", status_code=status.HTTP_400_BAD_REQUEST)
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
