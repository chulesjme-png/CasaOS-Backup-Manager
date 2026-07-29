"""
Tests para BackupExecutionRequest.
"""

from app.models.backup_configuration import (
    BackupConfiguration,
)

from app.models.backup_execution_request import (
    BackupExecutionRequest,
)

from app.models.backend_configuration import (
    BackendConfiguration,
)

from app.models.backup_manifest import (
    BackupManifest,
)

from app.models.backup_operation import (
    BackupOperationType,
)


def create_test_manifest():

    return BackupManifest(
        application="test",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=0,
    )


def create_backup_configuration():

    return BackupConfiguration(
        destination_url="file:///backup",
    )


def test_backup_execution_request_creates_default_configuration():

    manifest = create_test_manifest()

    backup_configuration = (
        create_backup_configuration()
    )

    request = BackupExecutionRequest(
        manifest=manifest,
        backup_configuration=backup_configuration,
        backend_name="null",
    )

    assert request.backend_name == "null"

    assert (
        request.backup_configuration
        == backup_configuration
    )

    assert (
        request.backend_configuration.backend_name
        == "null"
    )


def test_backup_execution_request_accepts_configuration():

    manifest = create_test_manifest()

    backup_configuration = (
        create_backup_configuration()
    )

    configuration = BackendConfiguration(
        backend_name="duplicati",
        configuration={
            "destination": "/backup",
        },
    )

    request = BackupExecutionRequest(
        manifest=manifest,
        backup_configuration=backup_configuration,
        backend_name="duplicati",
        backend_configuration=configuration,
    )

    assert (
        request.backup_configuration
        == backup_configuration
    )

    assert (
        request.backend_configuration.backend_name
        == "duplicati"
    )

    assert (
        request.backend_configuration.configuration[
            "destination"
        ]
        == "/backup"
    )


def test_backup_execution_request_default_operation():

    manifest = create_test_manifest()

    backup_configuration = (
        create_backup_configuration()
    )

    request = BackupExecutionRequest(
        manifest=manifest,
        backup_configuration=backup_configuration,
        backend_name="duplicati",
    )

    assert (
        request.operation
        == BackupOperationType.RUN_BACKUP
    )