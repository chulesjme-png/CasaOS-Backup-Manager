from app.core.backends.null_backup_backend import (
    NullBackupBackend,
)

from app.services.backend_capability_service import (
    BackendCapabilityService,
)


def test_backend_capability_service_discovers_capabilities():

    backend = NullBackupBackend()

    service = BackendCapabilityService()

    capabilities = service.discover(
        backend
    )

    assert capabilities.backend == "null"