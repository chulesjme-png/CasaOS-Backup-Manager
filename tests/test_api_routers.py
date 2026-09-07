from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app, active_jobs

client = TestClient(app)


def test_health_endpoint():
    """Valida el endpoint de comprobación de estado."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    response_v1 = client.get("/api/v1/health")
    assert response_v1.status_code == 200
    assert response_v1.json() == {"status": "ok"}


def test_list_backends_endpoint():
    """Valida que el endpoint devuelva la lista de backends disponibles."""
    response = client.get("/api/v1/backends")
    assert response.status_code == 200
    data = response.json()
    assert "backends" in data
    assert isinstance(data["backends"], list)


def test_get_backend_info_success():
    """Valida la obtención de información de un backend existente."""
    response = client.get("/api/v1/backends/duplicati")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "duplicati"


def test_get_backend_info_not_found():
    """Valida que un backend inexistente devuelva 404."""
    response = client.get("/api/v1/backends/nonexistent")
    assert response.status_code == 404


@patch("app.main.perform_real_backup")
def test_run_backup_endpoint(mock_backup):
    """Valida el inicio de ejecución de un backup vía API."""
    payload = {
        "backend_name": "null",
        "operation": "backup",
        "app_name": "Sistema_Completo"
    }
    response = client.post("/api/v1/executions/run", json=payload)
    assert response.status_code in (200, 202)
    assert response.json()["status"] == "success"
    assert "job_id" in response.json()


def test_cancel_endpoint():
    """Valida la cancelación de un trabajo de ejecución."""
    active_jobs["test-123"] = {"status": "running", "cancelled": False}

    response = client.post("/api/v1/executions/cancel/test-123")
    assert response.status_code == 200
    assert response.json() == {"status": "cancelled"}
    assert active_jobs["test-123"]["cancelled"] is True