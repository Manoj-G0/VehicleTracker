"""Focused coverage for registration, refresh sessions, access, and variant paging."""

from tests.conftest import sample_vehicle_payload


async def test_registration_starts_without_application_access(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "new-user", "email": "new@example.com", "password": "StrongPass123!"},
    )
    assert response.status_code == 201
    assert response.json()["allow_access"] is False

    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "new-user", "password": "StrongPass123!"},
    )
    assert login.status_code == 401


async def test_refresh_rotates_and_rejects_previous_token(client):
    created = await client.post(
        "/api/v1/users",
        json={"username": "refresh-user", "email": "refresh@example.com", "password": "StrongPass123!", "allow_access": True},
    )
    assert created.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "refresh-user", "password": "StrongPass123!"},
    )
    refresh_token = login.json()["refresh_token"]

    rotated = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != refresh_token

    reused = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reused.status_code == 401


async def test_revoking_access_invalidates_refresh_token(client):
    created = await client.post(
        "/api/v1/users",
        json={"username": "access-user", "email": "access@example.com", "password": "StrongPass123!", "allow_access": True},
    )
    user_id = created.json()["id"]
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "access-user", "password": "StrongPass123!"},
    )
    refresh_token = login.json()["refresh_token"]

    revoked = await client.patch(f"/api/v1/users/{user_id}/access", json={"allow_access": False})
    assert revoked.status_code == 200
    assert revoked.json()["allow_access"] is False

    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 401


async def test_variant_endpoint_pages_results(client):
    payload = sample_vehicle_payload(
        base_model_name="Many Variants",
        variants=[{"variant_name": f"Variant {index:02d}"} for index in range(25)],
    )
    created = await client.post("/api/v1/vehicles", json=payload)
    assert created.status_code == 201
    vehicle_id = created.json()["id"]

    first = await client.get(f"/api/v1/vehicles/{vehicle_id}/variants", params={"page": 1, "page_size": 20})
    assert first.status_code == 200
    assert len(first.json()["items"]) == 20
    assert first.json()["total_pages"] == 2

    second = await client.get(f"/api/v1/vehicles/{vehicle_id}/variants", params={"page": 2, "page_size": 20})
    assert len(second.json()["items"]) == 5
