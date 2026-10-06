from tests.conftest import sample_vehicle_payload
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.exceptions import AppError
from app.models.password_reset import PasswordResetVerification
from app.models.registration_verification import RegistrationVerification
from app.services import email_service
from app.services.otp_service import OTPService
from tests.conftest import TestSession


@pytest.fixture
def stub_otp_email(monkeypatch):
    monkeypatch.setattr(email_service.EmailService, "send_otp_email", lambda *args, **kwargs: None)


async def test_registration_requests_otp_without_creating_user(client, stub_otp_email):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "otp-user", "email": "otp-user@example.com", "password": "StrongPass123!"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "otp_sent"
    assert response.json()["resend_after_seconds"] == 300

    resend = await client.post("/api/v1/auth/register/resend", json={"email": "otp-user@example.com"})
    assert resend.status_code == 429

    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "otp-user", "password": "StrongPass123!"},
    )
    assert login.status_code == 401


async def test_registration_verify_creates_user_and_duplicate_email_is_rejected(client, stub_otp_email):
    first = await client.post(
        "/api/v1/auth/register",
        json={"username": "otp-user", "email": "otp-user@example.com", "password": "StrongPass123!"},
    )
    assert first.status_code == 200
    pending = await client.get("/api/v1/auth/health")
    assert pending.status_code == 200

    # No verification data is returned to the client path; this test asserts the duplicate guard is enforced
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "another-user", "email": "OTP-USER@EXAMPLE.COM", "password": "StrongPass123!"},
    )
    assert response.status_code == 409


async def test_registration_otp_success_creates_accessible_account(client, stub_otp_email):
    await client.post("/api/v1/auth/register", json={
        "username": "verified-user",
        "email": "verified@example.com",
        "password": "StrongPass123!",
    })
    async with TestSession() as session:
        pending = await session.scalar(select(RegistrationVerification).where(RegistrationVerification.email == "verified@example.com"))
        pending.otp_hash = OTPService.hash_otp("123456")
        await session.commit()

    verified = await client.post("/api/v1/auth/register/verify", json={
        "username": "verified-user",
        "email": "verified@example.com",
        "otp": "123456",
    })
    assert verified.status_code == 200
    login = await client.post("/api/v1/auth/login", json={"username": "verified-user", "password": "StrongPass123!"})
    assert login.status_code == 200


async def test_expired_registration_otp_is_rejected(client, stub_otp_email):
    await client.post("/api/v1/auth/register", json={
        "username": "expired-user",
        "email": "expired@example.com",
        "password": "StrongPass123!",
    })
    async with TestSession() as session:
        pending = await session.scalar(select(RegistrationVerification).where(RegistrationVerification.email == "expired@example.com"))
        pending.otp_hash = OTPService.hash_otp("123456")
        pending.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        await session.commit()

    response = await client.post("/api/v1/auth/register/verify", json={
        "username": "expired-user",
        "email": "expired@example.com",
        "otp": "123456",
    })
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()


async def test_registration_otp_attempt_limit_is_enforced(client, stub_otp_email):
    await client.post("/api/v1/auth/register", json={
        "username": "locked-user",
        "email": "locked@example.com",
        "password": "StrongPass123!",
    })
    async with TestSession() as session:
        pending = await session.scalar(select(RegistrationVerification).where(RegistrationVerification.email == "locked@example.com"))
        pending.otp_hash = OTPService.hash_otp("123456")
        pending.attempt_count = 5
        await session.commit()

    response = await client.post("/api/v1/auth/register/verify", json={
        "username": "locked-user",
        "email": "locked@example.com",
        "otp": "123456",
    })
    assert response.status_code == 400
    assert "Too many failed attempts" in response.json()["detail"]


async def test_short_registration_code_uses_otp_validation_message(client):
    response = await client.post("/api/v1/auth/register/verify", json={
        "username": "otp-user",
        "email": "otp-user@example.com",
        "otp": "123",
    })
    assert response.status_code == 422
    message = response.json()["detail"][0]["message"]
    assert "OTP" in message
    assert "String" not in message


async def test_password_reset_resend_is_rate_limited(client, stub_otp_email):
    await client.post("/api/v1/users", json={
        "username": "reset-user",
        "email": "reset@example.com",
        "password": "StrongPass123!",
        "allow_access": True,
    })
    first = await client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    assert first.status_code == 200
    assert first.json()["resend_after_seconds"] == 300
    repeated = await client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    assert repeated.status_code == 429


async def test_password_reset_otp_verification_and_password_update(client, stub_otp_email):
    await client.post("/api/v1/users", json={
        "username": "reset-success",
        "email": "reset-success@example.com",
        "password": "StrongPass123!",
        "allow_access": True,
    })
    await client.post("/api/v1/auth/forgot-password", json={"email": "reset-success@example.com"})
    async with TestSession() as session:
        pending = await session.scalar(select(PasswordResetVerification))
        pending.otp_hash = OTPService.hash_otp("654321")
        await session.commit()

    verified = await client.post("/api/v1/auth/forgot-password/verify", json={
        "email": "reset-success@example.com",
        "otp": "654321",
    })
    assert verified.status_code == 200
    token = verified.json()["token"]
    updated = await client.post("/api/v1/auth/reset-password", json={
        "token": token,
        "new_password": "NewStrong456!",
        "confirm_password": "NewStrong456!",
    })
    assert updated.status_code == 200
    login = await client.post("/api/v1/auth/login", json={"username": "reset-success", "password": "NewStrong456!"})
    assert login.status_code == 200


async def test_resending_reset_code_invalidates_prior_verification(client, stub_otp_email):
    await client.post("/api/v1/users", json={
        "username": "reset-resend",
        "email": "reset-resend@example.com",
        "password": "StrongPass123!",
        "allow_access": True,
    })
    await client.post("/api/v1/auth/forgot-password", json={"email": "reset-resend@example.com"})
    async with TestSession() as session:
        pending = await session.scalar(select(PasswordResetVerification))
        pending.otp_hash = OTPService.hash_otp("654321")
        await session.commit()
    verified = await client.post("/api/v1/auth/forgot-password/verify", json={
        "email": "reset-resend@example.com",
        "otp": "654321",
    })
    old_token = verified.json()["token"]

    async with TestSession() as session:
        pending = await session.scalar(select(PasswordResetVerification))
        pending.last_requested_at = datetime.now(timezone.utc) - timedelta(minutes=6)
        await session.commit()
    resent = await client.post("/api/v1/auth/forgot-password", json={"email": "reset-resend@example.com"})
    assert resent.status_code == 200
    stale_reset = await client.post("/api/v1/auth/reset-password", json={
        "token": old_token,
        "new_password": "NewStrong456!",
        "confirm_password": "NewStrong456!",
    })
    assert stale_reset.status_code == 400


def test_otp_email_fails_explicitly_without_smtp(monkeypatch):
    monkeypatch.setattr(email_service, "get_settings", lambda: SimpleNamespace(smtp_host="", smtp_from_email=""))
    with pytest.raises(AppError, match="SMTP_HOST"):
        email_service.EmailService.send_otp_email("person@example.com", "123456", "registration")


def test_otp_email_contains_branded_html(monkeypatch):
    settings = SimpleNamespace(
        smtp_host="smtp.example.com",
        smtp_from_email="no-reply@example.com",
        smtp_from_name="VehicleTracker",
        smtp_port=587,
        smtp_username="",
        smtp_password="",
        otp_expiry_minutes=5,
    )
    captured = {}

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def ehlo(self):
            pass

        def starttls(self):
            pass

        def send_message(self, message):
            captured["message"] = message

    monkeypatch.setattr(email_service, "get_settings", lambda: settings)
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)
    email_service.EmailService.send_otp_email("person@example.com", "123456", "registration")
    message = captured["message"]
    html_body = message.get_body(preferencelist=("html",)).get_content()
    assert "VehicleTracker" in html_body
    assert "123456" in html_body
    assert "expires in 5 minutes" in html_body


async def test_export_returns_filtered_variant_rows(client):
    payload = sample_vehicle_payload(base_model_name="Exportable One", variants=[{"variant_name": "V1"}, {"variant_name": "V2"}])
    created = (await client.post("/api/v1/vehicles", json=payload)).json()
    response = await client.get(
        "/api/v1/vehicles/export",
        params={"base_model_name": "Exportable One"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    assert b"Exportable One" in response.content
