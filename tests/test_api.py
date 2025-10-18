"""Tests for API endpoints."""
import pytest
from httpx import AsyncClient
from api.app import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data['service'] == 'Skadi'
        assert 'version' in data


@pytest.mark.asyncio
async def test_health_endpoint():
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()['status'] == 'healthy'


@pytest.mark.asyncio
async def test_telemetry_ingestion():
    """Test telemetry ingestion."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        telemetry_data = {
            "samples": [{
                "ts": "2025-10-18T23:11:00Z",
                "rack_id": "R-C-07",
                "inlet_c": 24.8,
                "outlet_c": 36.2,
                "pdu_kw": 8.6,
                "gpu_energy_j": 45250,
                "tokens_ps": 9800,
                "latency_p95_ms": 180,
                "fan_rpm_pct": 62,
                "pump_rpm_pct": 55,
                "queue_depth": 42
            }]
        }
        
        response = await client.post("/telemetry", json=telemetry_data)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert data['ingested'] == 1


@pytest.mark.asyncio
async def test_state_overview():
    """Test state overview endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/state/overview")
        assert response.status_code == 200
        # May return no_data if no telemetry ingested yet


@pytest.mark.asyncio
async def test_mode_control():
    """Test mode control endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Get current mode
        response = await client.get("/mode")
        assert response.status_code == 200
        
        # Set mode
        response = await client.post("/mode", json={"mode": "advisory"})
        assert response.status_code == 200
        assert response.json()['new_mode'] == 'advisory'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
