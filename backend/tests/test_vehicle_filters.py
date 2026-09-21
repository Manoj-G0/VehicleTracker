"""Filter and pagination tests."""

from tests.conftest import sample_vehicle_payload


async def _seed(client) -> None:
    await client.post(
        "/api/v1/vehicles",
        json=sample_vehicle_payload(
            base_model_name="Vehicle A",
            rlf_id="RL-A",
            rm_id="RM-A",
            ip_id="IP-123",
            evap_id="EV-A",
            pr_id="PR-A",
            df_id="DF-A",
            ob_id="OB-123",
            er_id="ER-A",
            pems_id="PEMS-A",
            variants=[{"variant_name": "HTX 6"}, {"variant_name": "HTX 7"}],
        ),
    )
    await client.post(
        "/api/v1/vehicles",
        json=sample_vehicle_payload(
            base_model_name="Vehicle B",
            rlf_id="RL-B",
            rm_id="RM-B",
            ip_id="IP-999",
            evap_id="EV-B",
            pr_id="PR-B",
            df_id="DF-B",
            ob_id="OB-123",
            er_id="ER-B",
            pems_id="PEMS-B",
            variants=[{"variant_name": "Prestige"}],
        ),
    )
    await client.post(
        "/api/v1/vehicles",
        json=sample_vehicle_payload(
            base_model_name="Vehicle C",
            rlf_id="RL-C",
            rm_id="RM-C",
            ip_id="IP-123",
            evap_id="EV-C",
            pr_id="PR-C",
            df_id="DF-C",
            ob_id="OB-456",
            er_id="ER-C",
            pems_id="PEMS-C",
            variants=[{"variant_name": "GT-Line"}, {"variant_name": "HTX 7"}],
        ),
    )


async def test_no_filters_returns_all(client):
    await _seed(client)
    response = await client.get("/api/v1/vehicles")
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert len(body["items"]) == 3


async def test_each_filter(client):
    await _seed(client)
    cases = {
        "base_model_name": ("Vehicle A", ["Vehicle A"]),
        "rlf_id": ("RL-B", ["Vehicle B"]),
        "rm_id": ("RM-C", ["Vehicle C"]),
        "ip_id": ("IP-999", ["Vehicle B"]),
        "evap_id": ("EV-A", ["Vehicle A"]),
        "pr_id": ("PR-B", ["Vehicle B"]),
        "df_id": ("DF-C", ["Vehicle C"]),
        "ob_id": ("OB-456", ["Vehicle C"]),
        "er_id": ("ER-A", ["Vehicle A"]),
        "pems_id": ("PEMS-B", ["Vehicle B"]),
        "variant_name": ("Prestige", ["Vehicle B"]),
    }
    for field, (value, expected) in cases.items():
        response = await client.get("/api/v1/vehicles", params={field: value})
        names = [item["base_model_name"] for item in response.json()["items"]]
        assert names == expected, field


async def test_ob_id_returns_multiple_vehicles(client):
    await _seed(client)
    response = await client.get("/api/v1/vehicles", params={"ob_id": "OB-123"})
    names = {item["base_model_name"] for item in response.json()["items"]}
    assert names == {"Vehicle A", "Vehicle B"}


async def test_ip_and_ob_intersection(client):
    await _seed(client)
    response = await client.get("/api/v1/vehicles", params={"ip_id": "IP-123", "ob_id": "OB-123"})
    names = [item["base_model_name"] for item in response.json()["items"]]
    assert names == ["Vehicle A"]


async def test_variant_filter_no_duplicate_parents(client):
    await _seed(client)
    response = await client.get("/api/v1/vehicles", params={"variant_name": "HTX 7"})
    names = [item["base_model_name"] for item in response.json()["items"]]
    assert names == ["Vehicle A", "Vehicle C"]


async def test_no_results(client):
    await _seed(client)
    response = await client.get("/api/v1/vehicles", params={"ip_id": "missing"})
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["total_pages"] == 0


async def test_empty_filter_ignored(client):
    await _seed(client)
    response = await client.get("/api/v1/vehicles", params={"ip_id": "  "})
    assert response.json()["total"] == 3


async def test_partial_case_insensitive(client):
    await _seed(client)
    response = await client.get("/api/v1/vehicles", params={"base_model_name": "vehicle a"})
    assert response.json()["items"][0]["base_model_name"] == "Vehicle A"


async def test_pagination(client):
    await _seed(client)
    first = await client.get("/api/v1/vehicles", params={"page": 1, "page_size": 2})
    body = first.json()
    assert body["page_size"] == 2
    assert body["total"] == 3
    assert body["total_pages"] == 2
    assert len(body["items"]) == 2
    second = await client.get("/api/v1/vehicles", params={"page": 2, "page_size": 2})
    assert len(second.json()["items"]) == 1


async def test_page_size_max_rejected(client):
    response = await client.get("/api/v1/vehicles", params={"page_size": 101})
    assert response.status_code == 400
