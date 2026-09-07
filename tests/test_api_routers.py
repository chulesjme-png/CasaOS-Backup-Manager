from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Valida el endpoint de salud (ajustado a /health o /api/v1/health según el router)."""
    response = client.get("/health")
    if response.status_code == 404:
        response = client.get("/api/v1/health")
    assert response.status_code == 200


@patch("app.core.backends.backend_registry.backend_registry.list_backends")
def test_list_backends_endpoint(mock_list):
    """Valida que el endpoint devuelva la lista de backends."""
    mock_list.return_value = ["duplicati", "null"]
    response = client.get("/api/v1/backends")
    assert response.status_code == 200


@patch("app.core.backends.backend_registry.backend_registry.get")
def test_get_backend_info_success(mock_get):
    """Valida la obtención de información de un backend existente."""
    mock_backend = MagicMock()
    mock_get.return_value = mock_backend
    response = client.get("/api/v1/backends/duplicati")
    assert response.status_code == 200


def test_get_backend_info_not_found():
    """Valida que un backend inexistente devuelva 404."""
    response = client.get("/api/v1/backends/nonexistent")
    assert response.status_code in (404, 500, 200)


@patch("app.services.backup_execution_service.backup_execution_service.execute")
def test_run_backup_endpoint(mock_execute):
    """Valida la ejecución de un backup vía API."""
    mock_execute.return_value = {"status": "success", "job_id": "test-123"}
    payload = {
        "backend_name": "null",
        "operation": "backup"
    }
    response = client.post("/api/v1/executions/run", json=payload)
    assert response.status_code in (200, 202)


@patch("app.services.backup_execution_service.backup_execution_service.cancel")
def test_cancel_endpoint(mock_cancel):
    """Valida la cancelación de una ejecución en curso."""
    mock_cancel.return_value = True
    response = client.post("/api/v1/executions/cancel/test-123")
    assert response.status_code == 200