"""
Pruebas del BackupExecutionService.

Valida la transformación:

BackupManifest
        ↓
BackupExecutionRequest
"""

from app.models.backup_configuration import (
    BackupConfiguration,
)

from app.models.backup_manifest import BackupManifest

from app.models.backup_operation import (
    BackupOperationType,
)

from app.services.backup_execution_service import (
    BackupExecutionService,
)


def create_backup_configuration():

    return BackupConfiguration(
        destination_url="file:///backup",
    )


def test_backup_execution_service_creates_request():

    manifest = BackupManifest(
        application="test-app",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=4096,
        metadata={
            "environment": "test",
        },
    )

    backup_configuration = (
        create_backup_configuration()
    )

    service = BackupExecutionService()

    request = service.prepare(
        manifest=manifest,
        backup_configuration=backup_configuration,
        backend_name="null",
    )

    assert request.manifest == manifest

    assert (
        request.backup_configuration
        == backup_configuration
    )

    assert request.backend_name == "null"

    assert (
        request.operation
        == BackupOperationType.RUN_BACKUP
    )


def test_backup_execution_service_accepts_operation():

    manifest = BackupManifest(
        application="test-app",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=4096,
        metadata={
            "environment": "test",
        },
    )

    backup_configuration = (
        create_backup_configuration()
    )

    service = BackupExecutionService()

    request = service.prepare(
        manifest=manifest,
        backup_configuration=backup_configuration,
        backend_name="null",
        operation=BackupOperationType.VERIFY,
    )

    assert (
        request.backup_configuration
        == backup_configuration
    )

    assert (
        request.operation
        == BackupOperationType.VERIFY
    )