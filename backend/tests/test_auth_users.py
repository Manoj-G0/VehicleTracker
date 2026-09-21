"""Authentication and user-management tests."""

from tests.conftest import sample_vehicle_payload


async def _create_admin(client):
    return await client.post(
        "/api/v1/users",
        json={
            "username": "admin",
            "email": "admin@example.com",
            "password": "StrongPass123!",
            "role": "ADMIN",
            "allow_access": True,
            "is_active": True,
        },
    )


async def test_login_success_for_active_admin(client):
    await _create_admin(client)
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "StrongPass123!"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "ADMIN"


async def test_login_rejects_disabled_user(client):
    await client.post(
        "/api/v1/users",
        json={
            "username": "blocked",
            "email": "blocked@example.com",
            "password": "StrongPass123!",
            "role": "USER",
            "allow_access": False,
            "is_active": True,
        },
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "blocked", "password": "StrongPass123!"},
    )
    assert response.status_code == 401


async def test_user_cannot_create_vehicle_without_admin(client):
    await client.post(
        "/api/v1/users",
        json={
            "username": "regular",
            "email": "regular@example.com",
            "password": "StrongPass123!",
            "role": "USER",
            "allow_access": True,
            "is_active": True,
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "regular", "password": "StrongPass123!"},
    )
    token = login.json()["access_token"]
    response = await client.post(
        "/api/v1/vehicles",
        json=sample_vehicle_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_admin_can_create_vehicle_with_jwt(client):
    await _create_admin(client)
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "StrongPass123!"},
    )
    token = login.json()["access_token"]
    response = await client.post(
        "/api/v1/vehicles",
        json=sample_vehicle_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
