"""
Pruebas del BackendExecutionService.

Valida:

BackupExecutionRequest
        ↓
BackendExecutionService
        ↓
BackendRegistry
        ↓
BackupBackend
"""

from app.services.backend_execution_service import (
    BackendExecutionService,
)

from app.core.backends.backend_factory import (
    BackendFactory,
)

from app.models.backup_execution_request import (
    BackupExecutionRequest,
)

from app.models.backup_manifest import (
    BackupManifest,
)


def test_backend_execution_service_resolves_backend():

    registry = BackendFactory.create_registry()

    service = BackendExecutionService(
        registry
    )

    manifest = BackupManifest(
        application="test-app",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=0,
        metadata={},
    )

    request = BackupExecutionRequest(
        manifest=manifest,
        backend_name="null",
    )

    backend = service.resolve(request)

    assert backend is not None

    assert backend.name == "null"