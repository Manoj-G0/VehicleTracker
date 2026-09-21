"""Variant-specific filter tests."""

from tests.conftest import sample_vehicle_payload


async def test_variant_name_partial_match(client):
    await client.post(
        "/api/v1/vehicles",
        json=sample_vehicle_payload(
            base_model_name="Parent One",
            variants=[{"variant_name": "HTX 6"}, {"variant_name": "HTX 7"}],
        ),
    )
    await client.post(
        "/api/v1/vehicles",
        json=sample_vehicle_payload(
            base_model_name="Parent Two",
            variants=[{"variant_name": "Prestige"}],
            ip_id="IP-OTHER",
            ob_id="OB-OTHER",
        ),
    )
    response = await client.get("/api/v1/vehicles", params={"variant_name": "htx"})
    names = [item["base_model_name"] for item in response.json()["items"]]
    assert names == ["Parent One"]
    assert response.json()["items"][0]["variant_count"] == 2
