"""
Servicio encargado de descubrir capacidades de backends.

Este servicio abstrae al Backup Engine de la implementación
concreta de cada backend.

No conoce:
- Docker.
- CasaOS.
- HTTP.
- Backends concretos.

Únicamente trabaja contra el contrato BackupBackend.
"""

from app.core.backends.backup_backend import (
    BackupBackend,
)

from app.models.backend_capabilities import (
    BackendCapabilities,
)


class BackendCapabilityService:
    """
    Servicio de descubrimiento de capacidades.
    """

    def discover(
        self,
        backend: BackupBackend,
    ) -> BackendCapabilities:
        """
        Devuelve las capacidades soportadas por un backend.
        """

        return backend.capabilities