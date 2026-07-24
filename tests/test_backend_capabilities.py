"""
Tests del sistema de capacidades de backend.

Valida que los backends declaran correctamente
sus capacidades sin que el Engine conozca su implementación.
"""

from app.core.backends.null_backup_backend import (
    NullBackupBackend,
)

from app.core.backends.duplicati_backend import (
    DuplicatiBackend,
)


def test_null_backend_capabilities():
    """
    El backend nulo debe declarar capacidades
    mínimas orientadas a testing.
    """

    backend = NullBackupBackend()

    capabilities = backend.capabilities

    assert capabilities.backend == "null"

    assert capabilities.can_run_backup is True

    assert capabilities.can_restore is False

    assert capabilities.supports_encryption is False



def test_duplicati_backend_capabilities():
    """
    Duplicati debe declarar capacidades
    completas del backend.
    """

    backend = DuplicatiBackend()

    capabilities = backend.capabilities

    assert capabilities.backend == "duplicati"

    assert capabilities.can_create_jobs is True

    assert capabilities.can_run_backup is True

    assert capabilities.can_restore is True

    assert capabilities.supports_encryption is True

    assert capabilities.supports_compression is True

    assert capabilities.supports_scheduling is True