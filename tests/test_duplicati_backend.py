"""
Pruebas del DuplicatiBackend.

Valida:

BackupExecutionRequest
        ↓
DuplicatiBackend
        ↓
DuplicatiClient
        ↓
BackupResult
"""

from unittest.mock import patch

from app.connectors.exceptions import (
    DuplicatiConnectionError,
)

from app.core.backends.duplicati_backend import (
    DuplicatiBackend,
)

from app.models.backend_configuration import (
    BackendConfiguration,
)

from app.models.backup_configuration import (
    BackupConfiguration,
)

from app.models.backup_execution_reference import (
    BackupExecutionReference,
)

from app.models.backup_execution_request import (
    BackupExecutionRequest,
)

from app.models.backup_manifest import (
    BackupManifest,
)

from app.models.backup_operation import (
    BackupOperationType,
)


@patch(
    "app.core.backends.duplicati_backend.DuplicatiClient"
)
def test_duplicati_backend_executes(
    mock_client,
):
    """
    Comprueba que DuplicatiBackend utiliza
    DuplicatiClient correctamente.
    """

    mock_client_instance = mock_client.return_value

    mock_client_instance.get_server_state.return_value = {
        "Version": "2.0.8.1",
        "MachineName": "Duplicati",
    }

    manifest = BackupManifest(
        application="test-app",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=0,
    )

    backup_configuration = BackupConfiguration(
        destination_url="file:///backups",
    )

    configuration = BackendConfiguration(
        backend_name="duplicati",
        configuration={
            "url": "http://192.168.1.10:8200",
            "timeout": 10,
            "password": "",
        },
    )

    request = BackupExecutionRequest(
        manifest=manifest,
        backup_configuration=backup_configuration,
        backend_name="duplicati",
        backend_configuration=configuration,
    )

    backend = DuplicatiBackend()

    result = backend.execute(
        request
    )

    assert result.success is True
    assert result.backend == "duplicati"
    assert result.application == "test-app"

    assert (
        result.metadata["duplicati_version"]
        == "2.0.8.1"
    )

    assert (
        result.metadata["duplicati_server_state"][
            "MachineName"
        ]
        == "Duplicati"
    )

    mock_client.assert_called_once_with(
        base_url="http://192.168.1.10:8200",
        timeout=10,
        password="",
    )

    mock_client_instance.get_server_state.assert_called_once()


@patch(
    "app.core.backends.duplicati_backend.DuplicatiClient"
)
def test_duplicati_backend_connection_failure(
    mock_client,
):
    """
    Comprueba que un fallo de comunicación con Duplicati
    se transforma en un BackupResult fallido.
    """

    mock_client_instance = mock_client.return_value

    mock_client_instance.get_server_state.side_effect = (
        DuplicatiConnectionError(
            "Servidor Duplicati no disponible"
        )
    )

    manifest = BackupManifest(
        application="test-app",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=0,
    )

    backup_configuration = BackupConfiguration(
        destination_url="file:///backups",
    )

    configuration = BackendConfiguration(
        backend_name="duplicati",
        configuration={
            "url": "http://192.168.1.10:8200",
            "timeout": 10,
            "password": "",
        },
    )

    request = BackupExecutionRequest(
        manifest=manifest,
        backup_configuration=backup_configuration,
        backend_name="duplicati",
        backend_configuration=configuration,
    )

    backend = DuplicatiBackend()

    result = backend.execute(
        request
    )

    assert result.success is False
    assert result.backend == "duplicati"
    assert result.application == "test-app"

    assert len(result.errors) == 1

    assert (
        "Servidor Duplicati no disponible"
        in result.errors[0]
    )


@patch(
    "app.core.backends.duplicati_backend.DuplicatiClient"
)
def test_duplicati_backend_run_backup_success(
    mock_client,
):
    """
    Comprueba la ejecución de RUN_BACKUP y extracción
    de la referencia de tarea.
    """

    mock_client_instance = mock_client.return_value
    mock_client_instance.run_backup.return_value = {
        "ID": 42,
        "Status": "Running",
    }

    manifest = BackupManifest(
        application="test-app",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=0,
    )

    backup_configuration = BackupConfiguration(
        destination_url="file:///backups",
        parameters={"backup_id": "1"},
    )

    configuration = BackendConfiguration(
        backend_name="duplicati",
        configuration={"url": "http://192.168.1.10:8200"},
    )

    request = BackupExecutionRequest(
        manifest=manifest,
        backup_configuration=backup_configuration,
        backend_name="duplicati",
        operation=BackupOperationType.RUN_BACKUP,
        backend_configuration=configuration,
    )

    backend = DuplicatiBackend()
    result = backend.execute(request)

    assert result.success is True
    assert result.execution_reference is not None
    assert result.execution_reference.execution_id == "1"
    assert result.execution_reference.task_id == "42"
    mock_client_instance.run_backup.assert_called_once_with(1)


@patch(
    "app.core.backends.duplicati_backend.DuplicatiClient"
)
def test_duplicati_backend_get_status_with_task_id(
    mock_client,
):
    """
    Comprueba que GET_STATUS consulta la tarea específica si
    se provee execution_reference con task_id.
    """

    mock_client_instance = mock_client.return_value
    mock_client_instance.get_task.return_value = {
        "ID": 42,
        "State": "Completed",
    }

    manifest = BackupManifest(
        application="test-app",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=0,
    )

    exec_ref = BackupExecutionReference(
        execution_id="1",
        task_id="42",
        backend="duplicati",
    )

    configuration = BackendConfiguration(
        backend_name="duplicati",
        configuration={"url": "http://192.168.1.10:8200"},
    )

    request = BackupExecutionRequest(
        manifest=manifest,
        backup_configuration=BackupConfiguration(destination_url="file:///backups"),
        backend_name="duplicati",
        operation=BackupOperationType.GET_STATUS,
        backend_configuration=configuration,
        execution_reference=exec_ref,
    )

    backend = DuplicatiBackend()
    result = backend.execute(request)

    assert result.success is True
    assert result.metadata["task_id"] == "42"
    assert result.metadata["duplicati_task"]["State"] == "Completed"
    mock_client_instance.get_task.assert_called_once_with(42)


@patch(
    "app.core.backends.duplicati_backend.DuplicatiClient"
)
def test_duplicati_backend_cancel_success(
    mock_client,
):
    """
    Comprueba la cancelación exitosa de una tarea activa.
    """

    mock_client_instance = mock_client.return_value

    manifest = BackupManifest(
        application="test-app",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=0,
    )

    exec_ref = BackupExecutionReference(
        execution_id="1",
        task_id="42",
        backend="duplicati",
    )

    configuration = BackendConfiguration(
        backend_name="duplicati",
        configuration={"url": "http://192.168.1.10:8200"},
    )

    request = BackupExecutionRequest(
        manifest=manifest,
        backup_configuration=BackupConfiguration(destination_url="file:///backups"),
        backend_name="duplicati",
        operation=BackupOperationType.CANCEL,
        backend_configuration=configuration,
        execution_reference=exec_ref,
    )

    backend = DuplicatiBackend()
    result = backend.execute(request)

    assert result.success is True
    assert result.metadata["cancelled_task_id"] == "42"
    mock_client_instance.stop_task.assert_called_once_with(42)