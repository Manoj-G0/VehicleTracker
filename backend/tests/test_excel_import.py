"""Excel preview and import tests."""

from io import BytesIO

from openpyxl import Workbook

HEADERS = [
    "BASE VEHICLE MODEL",
    "VARIANT NAME",
    "RLF ID",
    "RM ID",
    "IP ID",
    "EVAP ID",
    "PR ID",
    "DF ID",
    "OB ID",
    "ER ID",
    "PEMS ID",
]


def _workbook(rows: list[list[object]], headers: list[str] | None = None) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.append(headers or HEADERS)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def _file(content: bytes, name: str = "vehicles.xlsx"):
    return {"file": (name, content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}


SAMPLE_ROWS = [
    ["Vehicle A", "Variant A1", "RL-A", "--", "IP-123", "EV-A", "NA", "", "OB-123", None, "PEMS-A"],
    [None, "Variant A2", None, None, None, None, None, None, None, None, None],
    ["", "Variant A3", None, None, None, None, None, None, None, None, None],
    ["Vehicle B", "Variant B1", "RL-B", None, "IP-B", "EV-B", None, None, "OB-123", None, "PEMS-B"],
    [None, "Variant B2", None, None, None, None, None, None, None, None, None],
]


async def test_preview_valid_workbook(client):
    response = await client.post(
        "/api/v1/imports/vehicles/preview",
        files=_file(_workbook(SAMPLE_ROWS)),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["can_import"] is True
    assert body["base_models_detected"] == 2
    assert body["variants_detected"] == 5
    assert body["new_vehicles"] == 2
    assert body["total_rows"] == 5


async def test_preview_does_not_write(client):
    await client.post("/api/v1/imports/vehicles/preview", files=_file(_workbook(SAMPLE_ROWS)))
    listed = await client.get("/api/v1/vehicles")
    assert listed.json()["total"] == 0


async def test_missing_header(client):
    response = await client.post(
        "/api/v1/imports/vehicles/preview",
        files=_file(_workbook(SAMPLE_ROWS, headers=HEADERS[:-1])),
    )
    assert response.status_code == 400
    assert "PEMS ID" in response.json()["detail"][0]["message"]


async def test_blank_base_model_before_definition(client):
    rows = [[None, "Orphan", None, None, None, None, None, None, None, None, None]]
    response = await client.post("/api/v1/imports/vehicles/preview", files=_file(_workbook(rows)))
    body = response.json()
    assert body["can_import"] is False
    assert body["errors"]


async def test_duplicate_variant_warning(client):
    rows = [
        ["Vehicle A", "Same", None, None, None, None, None, None, "OB-1", None, None],
        [None, "Same", None, None, None, None, None, None, None, None, None],
    ]
    response = await client.post("/api/v1/imports/vehicles/preview", files=_file(_workbook(rows)))
    body = response.json()
    assert body["duplicate_variants"] == 1
    assert body["can_import"] is True


async def test_reject_non_xlsx(client):
    response = await client.post(
        "/api/v1/imports/vehicles/preview",
        files={"file": ("vehicles.csv", b"a,b", "text/csv")},
    )
    assert response.status_code == 400


async def test_successful_import_and_normalization(client):
    response = await client.post("/api/v1/imports/vehicles", files=_file(_workbook(SAMPLE_ROWS)))
    assert response.status_code == 200
    body = response.json()
    assert body["created_vehicles"] == 2
    assert body["created_variants"] == 5
    listed = await client.get("/api/v1/vehicles")
    names = {item["base_model_name"] for item in listed.json()["items"]}
    assert names == {"Vehicle A", "Vehicle B"}
    vehicle_a = next(item for item in listed.json()["items"] if item["base_model_name"] == "Vehicle A")
    assert vehicle_a["rlf_id"] == "RL-A"
    assert vehicle_a["rm_id"] is None
    assert vehicle_a["ob_id"] == "OB-123"
    detail = await client.get(f"/api/v1/vehicles/{vehicle_a['id']}")
    assert len(detail.json()["variants"]) == 3


async def test_multiple_ob_id_records_imported(client):
    await client.post("/api/v1/imports/vehicles", files=_file(_workbook(SAMPLE_ROWS)))
    response = await client.get("/api/v1/vehicles", params={"ob_id": "OB-123"})
    assert response.json()["total"] == 2


async def test_upsert_adds_variants(client):
    await client.post("/api/v1/imports/vehicles", files=_file(_workbook(SAMPLE_ROWS)))
    extra = [
        ["Vehicle A", "Variant A1", "RL-A2", None, "IP-123", "EV-A", None, None, "OB-123", None, "PEMS-A"],
        [None, "Variant A4", None, None, None, None, None, None, None, None, None],
    ]
    result = await client.post("/api/v1/imports/vehicles", files=_file(_workbook(extra)))
    assert result.json()["updated_vehicles"] == 1
    assert result.json()["created_variants"] == 1
    listed = await client.get("/api/v1/vehicles")
    vehicle_a = next(item for item in listed.json()["items"] if item["base_model_name"] == "Vehicle A")
    assert vehicle_a["rlf_id"] == "RL-A2"
    detail = await client.get(f"/api/v1/vehicles/{vehicle_a['id']}")
    names = {item["variant_name"] for item in detail.json()["variants"]}
    assert "Variant A4" in names
    assert "Variant A2" in names


async def test_replace_mode_replaces_variants(client):
    await client.post("/api/v1/imports/vehicles", files=_file(_workbook(SAMPLE_ROWS)))
    replacement = [
        ["Vehicle A", "Only One", "RL-A", None, "IP-123", "EV-A", None, None, "OB-123", None, "PEMS-A"],
    ]
    await client.post(
        "/api/v1/imports/vehicles",
        files=_file(_workbook(replacement)),
        data={"mode": "replace"},
    )
    listed = await client.get("/api/v1/vehicles")
    vehicle_a = next(item for item in listed.json()["items"] if item["base_model_name"] == "Vehicle A")
    detail = await client.get(f"/api/v1/vehicles/{vehicle_a['id']}")
    names = [item["variant_name"] for item in detail.json()["variants"]]
    assert names == ["Only One"]


async def test_import_rollback_on_fatal_error(client, monkeypatch):
    from app.services import import_service as module

    async def boom(*_args, **_kwargs):
        raise RuntimeError("forced failure")

    monkeypatch.setattr(module.ImportService, "_create_from_group", boom)
    response = await client.post("/api/v1/imports/vehicles", files=_file(_workbook(SAMPLE_ROWS)))
    assert response.status_code == 500
    listed = await client.get("/api/v1/vehicles")
    assert listed.json()["total"] == 0
