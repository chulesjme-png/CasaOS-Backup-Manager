"""
Pruebas del BackupEngineService.

Valida el flujo:

BackupJob
    ↓
BackupEngineService
    ↓
BackupManifest
"""

from app.models.backup_job import BackupJob
from app.services.backup_engine_service import (
    BackupEngineService,
)


def test_backup_engine_prepares_manifest():

    job = BackupJob(
        application="test-app",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=2048,
        metadata={
            "source": "test"
        },
    )

    engine = BackupEngineService()

    manifest = engine.prepare(job)

    assert manifest.application == "test-app"

    assert manifest.estimated_size == 2048

    assert manifest.metadata == {
        "source": "test"
    }