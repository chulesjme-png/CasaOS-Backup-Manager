"""
Pruebas del BackupRunnerService.

Valida el flujo completo:

BackupJob
    ↓
BackupEngineService
    ↓
BackupManifest
    ↓
BackupExecutionRequest
    ↓
Backend
    ↓
BackupResult
"""

from app.models.application import Application
from app.models.application_profile import ApplicationProfile
from app.models.backup_configuration import (
    BackupConfiguration,
)
from app.models.backup_job import BackupJob
from app.models.backup_result import BackupResult

from app.services.backup_runner_service import (
    BackupRunnerService,
)

from app.services.backend_execution_service import (
    BackendExecutionService,
)

from app.core.backends.backend_registry import (
    BackendRegistry,
)

from app.core.backends.null_backup_backend import (
    NullBackupBackend,
)


def test_backup_runner_executes_null_backend():

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
        warnings=[],
        estimated_size=2048,
        metadata={
            "source": "test"
        },
    )

    backup_configuration = BackupConfiguration(
        destination_url="",
        description="Configuración de prueba",
        encryption=None,
        passphrase=None,
        compression=None,
        retention_policy=None,
        schedule=None,
        filters=[],
        options={},
        metadata={
            "source": "test"
        },
    )

    registry = BackendRegistry()

    registry.register(
        NullBackupBackend()
    )

    backend_service = BackendExecutionService(
        registry
    )

    runner = BackupRunnerService(
        backend_execution_service=backend_service
    )

    result = runner.run(
        job,
        backup_configuration,
        "null",
    )

    assert isinstance(
        result,
        BackupResult,
    )

    assert result.success is True

    assert result.backend == "null"

    assert result.application == "test-app"