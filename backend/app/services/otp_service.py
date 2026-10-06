from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings


class OTPService:
    @staticmethod
    def generate_otp() -> str:
        return str(secrets.randbelow(900_000) + 100_000)

    @staticmethod
    def hash_otp(otp: str) -> str:
        return hashlib.sha256(otp.encode("utf-8")).hexdigest()

    @staticmethod
    def is_expired(expires_at: datetime) -> bool:
        return datetime.now(timezone.utc) > expires_at

    @staticmethod
    def create_expires_at() -> datetime:
        settings = get_settings()
        return datetime.now(timezone.utc) + timedelta(minutes=settings.otp_expiry_minutes)

    @staticmethod
    def create_resend_deadline() -> datetime:
        settings = get_settings()
        return datetime.now(timezone.utc) + timedelta(seconds=settings.otp_resend_cooldown_seconds)
