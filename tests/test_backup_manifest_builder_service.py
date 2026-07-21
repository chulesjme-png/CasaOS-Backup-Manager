"""
Pruebas del BackupManifestBuilderService.

Valida la transformación:

BackupJob
    ↓
BackupManifest
"""

from app.models.application import Application
from app.models.application_profile import ApplicationProfile
from app.models.backup_job import BackupJob
from app.services.backup_manifest_builder_service import (
    BackupManifestBuilderService,
)


def test_backup_manifest_builder_creates_manifest():

    application = Application(
        name="test-app",
        containers=1,
        status="running",
    )

    profile = ApplicationProfile(
        name="default",
        application="test-app",
        description="Perfil de pruebas",
    )

    job = BackupJob(
        application=application,
        profile=profile,
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
        "test": True,
        "generated_from": "BackupJob",
    }