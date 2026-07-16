from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_system_endpoint_reports_cpu() -> None:
    response = client.get("/api/system")
    assert response.status_code == 200
    payload = response.json()
    assert payload["api"] == "ready"
    assert payload["device"] == "cpu"
    assert (
        payload["dataset_config"].replace("\\", "/").endswith("datasets/dota_ship/dota_ship.yaml")
    )
    assert payload["model_state"] in {"ready", "missing", "dependency_missing", "error"}
