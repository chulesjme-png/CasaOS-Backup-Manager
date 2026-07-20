"""
Pruebas del BackupManifestBuilderService.

Valida la transformación:

BackupJob
    ↓
BackupManifest
"""

from app.models.backup_job import BackupJob
from app.services.backup_manifest_builder_service import (
    BackupManifestBuilderService,
)


def test_backup_manifest_builder_creates_manifest():

    job = BackupJob(
        application="test-app",
        sources=[],
        excluded_sources=[],
        warnings=[
            "test warning"
        ],
        estimated_size=1024,
        metadata={
            "test": True
        },
    )

    service = BackupManifestBuilderService()

    manifest = service.build(job)

    assert manifest.application == "test-app"

    assert manifest.estimated_size == 1024

    assert manifest.warnings == [
        "test warning"
    ]

    assert manifest.metadata == {
        "test": True
    }