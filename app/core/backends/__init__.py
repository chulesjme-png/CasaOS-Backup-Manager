"""
Paquete de contratos y adaptadores del Backup Engine.

Contiene:

- contratos base de backend
- registro de backends
- fábrica de backends
- implementaciones disponibles
"""

from app.core.backends.backup_backend import BackupBackend
from app.core.backends.backend_factory import BackendFactory
from app.core.backends.backend_registry import BackendRegistry
from app.core.backends.null_backup_backend import NullBackupBackend

__all__ = [
    "BackupBackend",
    "BackendFactory",
    "BackendRegistry",
    "NullBackupBackend",
]