"""Vehicle CRUD tests."""

from tests.conftest import sample_vehicle_payload


async def test_create_valid_vehicle(client):
    response = await client.post("/api/v1/vehicles", json=sample_vehicle_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["base_model_name"].startswith("Kia Sorento")
    assert body["ob_id"] == "OB-123"
    assert len(body["variants"]) == 2


async def test_create_missing_base_model(client):
    payload = sample_vehicle_payload()
    payload["base_model_name"] = ""
    response = await client.post("/api/v1/vehicles", json=payload)
    assert response.status_code == 422
    assert any("base_model_name" in item["field"] for item in response.json()["detail"])


async def test_create_duplicate_base_model(client):
    await client.post("/api/v1/vehicles", json=sample_vehicle_payload())
    response = await client.post("/api/v1/vehicles", json=sample_vehicle_payload())
    assert response.status_code == 409


async def test_create_null_ids(client):
    payload = sample_vehicle_payload(
        rlf_id=None,
        rm_id=None,
        ip_id=None,
        evap_id=None,
        pr_id=None,
        df_id=None,
        ob_id=None,
        er_id=None,
        pems_id=None,
        variants=[{"variant_name": "Base"}],
    )
    payload["base_model_name"] = "Null ID Vehicle"
    response = await client.post("/api/v1/vehicles", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["ip_id"] is None
    assert body["ob_id"] is None


async def test_create_normalizes_placeholder_ids(client):
    payload = sample_vehicle_payload(rlf_id="--", rm_id="N/A", ip_id="null")
    payload["base_model_name"] = "Normalized Vehicle"
    response = await client.post("/api/v1/vehicles", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["rlf_id"] is None
    assert body["rm_id"] is None
    assert body["ip_id"] is None


async def test_get_vehicle_detail(client):
    created = (await client.post("/api/v1/vehicles", json=sample_vehicle_payload())).json()
    response = await client.get(f"/api/v1/vehicles/{created['id']}")
    assert response.status_code == 200
    body = response.json()
    assert len(body["variants"]) == 2
    assert body["pems_id"] == "PEMS-123"


async def test_get_vehicle_not_found(client):
    response = await client.get("/api/v1/vehicles/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Vehicle not found"


async def test_update_vehicle_and_variants(client):
    created = (await client.post("/api/v1/vehicles", json=sample_vehicle_payload())).json()
    payload = sample_vehicle_payload(
        ip_id="IP-999",
        variants=[{"variant_name": "HTX 7"}, {"variant_name": "GT-Line"}],
    )
    response = await client.put(f"/api/v1/vehicles/{created['id']}", json=payload)
    assert response.status_code == 200
    names = {item["variant_name"] for item in response.json()["variants"]}
    assert names == {"HTX 7", "GT-Line"}
    assert response.json()["ip_id"] == "IP-999"


async def test_update_rejects_duplicate_variants(client):
    created = (await client.post("/api/v1/vehicles", json=sample_vehicle_payload())).json()
    payload = sample_vehicle_payload(variants=[{"variant_name": "HTX"}, {"variant_name": "htx"}])
    response = await client.put(f"/api/v1/vehicles/{created['id']}", json=payload)
    assert response.status_code == 422


async def test_delete_vehicle_soft(client):
    created = (await client.post("/api/v1/vehicles", json=sample_vehicle_payload())).json()
    deleted = await client.delete(f"/api/v1/vehicles/{created['id']}")
    assert deleted.status_code == 204
    missing = await client.get(f"/api/v1/vehicles/{created['id']}")
    assert missing.status_code == 404
    listed = await client.get("/api/v1/vehicles")
    assert listed.json()["total"] == 0


async def test_delete_not_found(client):
    response = await client.delete("/api/v1/vehicles/42")
    assert response.status_code == 404


async def test_variant_crud_preserves_metadata(client):
    vehicle = (await client.post("/api/v1/vehicles", json=sample_vehicle_payload(variants=[]))).json()
    path = f"/api/v1/vehicles/{vehicle['id']}/variants"
    created = await client.post(path, json={
        "variant_name": "Long Range",
        "equation": "E = P * t",
        "cycle_energy_demand": "14.2 kWh/100km",
        "co2": "0 g/km",
    })
    assert created.status_code == 201
    variant = created.json()
    assert variant["equation"] == "E = P * t"
    assert variant["cycle_energy_demand"] == "14.2 kWh/100km"
    assert variant["co2"] == "0 g/km"

    updated = await client.put(f"{path}/{variant['id']}", json={
        "variant_name": "Long Range Plus",
        "equation": "E = V * I * t",
        "cycle_energy_demand": "13.8 kWh/100km",
        "co2": "2 g/km",
    })
    assert updated.status_code == 200
    assert updated.json()["variant_name"] == "Long Range Plus"
    assert updated.json()["co2"] == "2 g/km"

    listed = await client.get(path)
    assert listed.json()["items"] == [updated.json()]
    deleted = await client.delete(f"{path}/{variant['id']}")
    assert deleted.status_code == 204
    assert (await client.get(path)).json()["total"] == 0


async def test_variant_crud_rejects_duplicate_name(client):
    vehicle = (await client.post("/api/v1/vehicles", json=sample_vehicle_payload(variants=[]))).json()
    path = f"/api/v1/vehicles/{vehicle['id']}/variants"
    await client.post(path, json={"variant_name": "Standard"})
    duplicate = await client.post(path, json={"variant_name": "standard"})
    assert duplicate.status_code == 409
