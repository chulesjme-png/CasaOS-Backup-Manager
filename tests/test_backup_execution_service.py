"""
Pruebas del BackupExecutionService.

Valida la transformación:

BackupManifest
        ↓
BackupExecutionRequest
"""

from app.models.backup_manifest import BackupManifest
from app.services.backup_execution_service import (
    BackupExecutionService,
)


def test_backup_execution_service_creates_request():

    manifest = BackupManifest(
        application="test-app",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=4096,
        metadata={
            "environment": "test"
        },
    )

    service = BackupExecutionService()

    request = service.prepare(
        manifest,
        "null",
    )

    assert request.manifest == manifest

    assert request.backend_name == "null"