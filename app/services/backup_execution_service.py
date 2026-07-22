"""
Servicio encargado de preparar solicitudes
de ejecución del Backup Engine.

Transforma:

BackupManifest
        |
        v
BackupExecutionRequest

No ejecuta backups.
No resuelve backends.
No conoce implementaciones concretas.
"""

from typing import Optional

from app.models.backup_manifest import BackupManifest

from app.models.backend_configuration import (
    BackendConfiguration,
)

from app.models.backup_execution_request import (
    BackupExecutionRequest,
)


class BackupExecutionService:
    """
    Servicio de preparación de solicitudes
    de ejecución.
    """

    def prepare(
        self,
        manifest: BackupManifest,
        backend_name: str,
        backend_configuration: Optional[BackendConfiguration] = None,
    ) -> BackupExecutionRequest:
        """
        Construye una solicitud de ejecución
        a partir de un manifiesto.
        """

        return BackupExecutionRequest(
            manifest=manifest,
            backend_name=backend_name,
            backend_configuration=backend_configuration,
        )