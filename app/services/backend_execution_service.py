"""
Servicio encargado de resolver el backend
asociado a una solicitud de ejecución.

No ejecuta backups.
No contiene lógica específica de motores.
"""

from typing import Optional

from app.models.backup_execution_request import (
    BackupExecutionRequest,
)

from app.core.backends.backend_registry import (
    BackendRegistry,
)

from app.core.backends.backup_backend import (
    BackupBackend,
)


class BackendExecutionService:
    """
    Servicio encargado de resolver el backend
    correspondiente a una solicitud de ejecución.
    """

    def __init__(
        self,
        registry: BackendRegistry,
    ):
        self.registry = registry

    def resolve(
        self,
        request: BackupExecutionRequest,
    ) -> Optional[BackupBackend]:
        """
        Devuelve la implementación del backend solicitada
        por la petición de ejecución.
        """

        return self.registry.get(
            request.backend_name
        )