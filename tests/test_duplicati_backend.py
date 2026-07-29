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

from app.models.backup_execution_request import (
    BackupExecutionRequest,
)

from app.models.backup_manifest import (
    BackupManifest,
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