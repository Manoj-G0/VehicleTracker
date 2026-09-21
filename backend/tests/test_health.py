"""Health endpoint tests."""


async def test_health_returns_ready(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["status"] == "ok"
