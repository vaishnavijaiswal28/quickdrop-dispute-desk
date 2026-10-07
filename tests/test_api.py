import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    await init_db()

@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "QuickDrop Rider Payout Dispute Desk"
    assert data["status"] == "RUNNING"

@pytest.mark.asyncio
async def test_post_message_and_idempotency():
    payload = {
        "message_id": "wamid.TEST_IDEMPOTENCY_001",
        "rider_id": "R003",
        "text": "Bhai order T926334 ka surge nahi mila, 20 tarikh wala",
        "received_at": "2026-09-22T09:05:00+05:30"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # First call
        response1 = await ac.post("/messages", json=payload)
        assert response1.status_code == 200
        reply1 = response1.json()["reply"]
        assert "T926334" in reply1

        # Second call with identical message_id (Idempotency test)
        response2 = await ac.post("/messages", json=payload)
        assert response2.status_code == 200
        reply2 = response2.json()["reply"]

        # Replies MUST be identical
        assert reply1 == reply2

@pytest.mark.asyncio
async def test_get_trace():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/trace/R003")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

@pytest.mark.asyncio
async def test_get_ops_pending():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/ops/pending")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
