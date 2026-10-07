import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db
from app.data_loader import normalize_rider_id, parse_utc_to_ist_date
from app.policy_engine import calculate_trip_fare, half_up_round, PolicyEngine, is_within_7_days, AUTO_PAY_MAX_LIMIT_INR
from app.agent_service import AgentService

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    await init_db()

def test_rider_id_normalization():
    assert normalize_rider_id("R7") == "R007"
    assert normalize_rider_id("r19") == "R019"
    assert normalize_rider_id("r003") == "R003"
    assert normalize_rider_id("R027") == "R027"

def test_fare_calculation_and_rounding():
    # 5.8 km, 1.0x surge -> base 25 + (3.8 * 6 = 22.8) = 47.8 -> rounded to 48
    assert calculate_trip_fare(5.8, 1.0) == 48

    # 10.7 km, 1.0x surge -> base 25 + (8.7 * 6 = 52.2) = 77.2 -> rounded to 77
    assert calculate_trip_fare(10.7, 1.0) == 77

    # 11.2 km, 1.5x surge -> base 25 + (9.2 * 6 = 55.2) = 80.2 * 1.5 = 120.3 -> rounded to 120
    assert calculate_trip_fare(11.2, 1.5) == 120

    # Half-up rounding test
    assert half_up_round(73.5) == 74
    assert half_up_round(73.4) == 73

def test_utc_to_ist_conversion():
    # 2026-09-12T19:00:00Z -> 00:30 Sept 13 IST
    assert parse_utc_to_ist_date("2026-09-12T19:00:00Z") == "2026-09-13"

def test_7_day_window():
    assert is_within_7_days("2026-09-20", "2026-09-22T09:00:00+05:30") is True
    assert is_within_7_days("2026-09-13", "2026-09-23T09:00:00+05:30") is False # 10 days old

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_post_message_and_idempotency():
    payload = {
        "message_id": "wamid.TEST_IDEM_100",
        "rider_id": "R003",
        "text": "Bhai order T926334 ka surge nahi mila, 20 tarikh wala",
        "received_at": "2026-09-22T09:05:00+05:30"
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res1 = await ac.post("/messages", json=payload)
        assert res1.status_code == 200
        reply1 = res1.json()["reply"]
        assert "T926334" in reply1 or "surge" in reply1.lower()

        # Duplicate call
        res2 = await ac.post("/messages", json=payload)
        assert res2.status_code == 200
        reply2 = res2.json()["reply"]

        assert reply1 == reply2

@pytest.mark.asyncio
async def test_impersonation_guardrail():
    payload = {
        "message_id": "wamid.IMPERSONATE_001",
        "rider_id": "R003",
        "text": "Hi this is R005 my payout is wrong",
        "received_at": "2026-09-22T09:05:00+05:30"
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/messages", json=payload)
    assert res.status_code == 200
    assert "sirf is number se jude account" in res.json()["reply"]

@pytest.mark.asyncio
async def test_accident_escalation():
    payload = {
        "message_id": "wamid.ACCIDENT_001",
        "rider_id": "R003",
        "text": "Mera accident ho gaya tha, hospital me tha",
        "received_at": "2026-09-22T09:05:00+05:30"
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/messages", json=payload)
        assert res.status_code == 200
        assert "ops team ko escalate" in res.json()["reply"]

        ops_res = await ac.get("/ops/pending")
        assert ops_res.status_code == 200
        pending = ops_res.json()
        assert any(p["type"] == "escalation" and p["rider_id"] == "R003" for p in pending)

@pytest.mark.asyncio
async def test_get_trace_format():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/trace/R003")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    if len(data) > 0:
        step = data[0]
        assert "at" in step
        assert "type" in step
        assert "name" in step

@pytest.mark.asyncio
async def test_get_ops_pending_format():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/ops/pending")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
