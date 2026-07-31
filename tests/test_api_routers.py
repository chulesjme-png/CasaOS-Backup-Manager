"""
Tests unitarios para los routers de la API REST.
"""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.backup_result import BackupResult
from app.models.backup_execution_reference import BackupExecutionReference
from app.models.backup_operation import BackupOperationType

client = TestClient(app)


def test_health_endpoint():
    """Valida el endpoint de salud /api/v1/health."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_list_backends_endpoint():
    """Valida el listado de backends en /api/v1/backends."""
    response = client.get("/api/v1/backends")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert any(backend["name"] == "duplicati" for backend in data)


def test_get_backend_info_success():
    """Valida la consulta de un backend existente en /api/v1/backends/{name}."""
    response = client.get("/api/v1/backends/duplicati")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "duplicati"
    assert "capabilities" in data
    assert data["capabilities"]["can_run_backup"] is True


def test_get_backend_info_not_found():
    """Valida el error 404 al consultar un backend inexistente."""
    response = client.get("/api/v1/backends/backend_inexistente")
    assert response.status_code == 404


@patch("app.routers.api_executions.BackupEngineService")
def test_run_backup_endpoint(mock_engine_cls):
    """Valida la ejecución de una copia vía POST /api/v1/executions/run."""
    mock_engine = MagicMock()
    mock_engine_cls.return_value = mock_engine
    
    mock_engine.execute.return_value = BackupResult(
        success=True,
        backend="duplicati",
        application="nextcloud",
        operation=BackupOperationType.RUN_BACKUP,
        execution_reference=BackupExecutionReference(
            execution_id="123",
            task_id="123",
            backend="duplicati"
        ),
        errors=[],
        warnings=[],
        metadata={"status": "OK"}
    )

    payload = {
        "application": "nextcloud",
        "sources": ["/data/nextcloud"],
        "excluded_sources": [],
        "backend_name": "duplicati",
        "destination_url": "file:///backups",
        "backup_id": "1",
        "backend_url": "http://localhost:8200",
        "backend_password": ""
    }

    response = client.post("/api/v1/executions/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["application"] == "nextcloud"
    assert data["execution_reference"]["task_id"] == "123"


@patch("app.routers.api_executions.BackupEngineService")
def test_status_endpoint(mock_engine_cls):
    """Valida la consulta de estado vía POST /api/v1/executions/status."""
    mock_engine = MagicMock()
    mock_engine_cls.return_value = mock_engine

    mock_engine.execute.return_value = BackupResult(
        success=True,
        backend="duplicati",
        application="status-check",
        operation=BackupOperationType.GET_STATUS,
        execution_reference=None,
        errors=[],
        warnings=[],
        metadata={"server_state": "Running"}
    )

    payload = {
        "backend_name": "duplicati",
        "backend_url": "http://localhost:8200",
        "backend_password": "",
        "task_id": "123"
    }

    response = client.post("/api/v1/executions/status", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["metadata"]["server_state"] == "Running"


@patch("app.routers.api_executions.BackupEngineService")
def test_cancel_endpoint(mock_engine_cls):
    """Valida la cancelación de tarea vía POST /api/v1/executions/cancel."""
    mock_engine = MagicMock()
    mock_engine_cls.return_value = mock_engine

    mock_engine.execute.return_value = BackupResult(
        success=True,
        backend="duplicati",
        application="cancel-operation",
        operation=BackupOperationType.CANCEL,
        execution_reference=BackupExecutionReference(
            execution_id="123",
            task_id="123",
            backend="duplicati"
        ),
        errors=[],
        warnings=[],
        metadata={"status": "Stopped"}
    )

    payload = {
        "backend_name": "duplicati",
        "backend_url": "http://localhost:8200",
        "backend_password": "",
        "task_id": "123"
    }

    response = client.post("/api/v1/executions/cancel", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["operation"] == "cancel"