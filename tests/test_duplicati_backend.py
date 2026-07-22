"""
Pruebas del DuplicatiBackend.

Valida:

BackupExecutionRequest
        ↓
DuplicatiBackend
        ↓
BackupResult
"""

from app.core.backends.duplicati_backend import (
    DuplicatiBackend,
)

from app.models.backend_configuration import (
    BackendConfiguration,
)

from app.models.backup_execution_request import (
    BackupExecutionRequest,
)

from app.models.backup_manifest import (
    BackupManifest,
)


def test_duplicati_backend_executes():

    manifest = BackupManifest(
        application="test-app",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=0,
    )

    configuration = BackendConfiguration(
        backend_name="duplicati",
        configuration={
            "mode": "simulation"
        },
    )

    request = BackupExecutionRequest(
        manifest=manifest,
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

    assert result.metadata["configuration"]["mode"] == "simulation"