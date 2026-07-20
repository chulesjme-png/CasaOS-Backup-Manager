"""
Servicio encargado de resolver el backend
asociado a una solicitud de ejecución.

No ejecuta backups.
No contiene lógica específica de motores.
"""

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
    Servicio de resolución de backends.
    """

    def __init__(
        self,
        registry: BackendRegistry,
    ):
        self.registry = registry

    def resolve(
        self,
        request: BackupExecutionRequest,
    ) -> BackupBackend | None:
        """
        Obtiene el backend solicitado.
        """

        return self.registry.get(
            request.backend_name
        )