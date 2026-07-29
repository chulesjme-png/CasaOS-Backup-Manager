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

from app.models.backup_configuration import (
    BackupConfiguration,
)
from app.models.backup_execution_reference import (
    BackupExecutionReference,
)
from app.models.backup_execution_request import (
    BackupExecutionRequest,
)
from app.models.backup_manifest import (
    BackupManifest,
)
from app.models.backend_configuration import (
    BackendConfiguration,
)
from app.models.backup_operation import (
    BackupOperationType,
)


class BackupExecutionService:
    """
    Servicio de preparación de solicitudes
    de ejecución.
    """

    def prepare(
        self,
        manifest: BackupManifest,
        backup_configuration: BackupConfiguration,
        backend_name: str,
        operation: BackupOperationType = (
            BackupOperationType.RUN_BACKUP
        ),
        backend_configuration: Optional[
            BackendConfiguration
        ] = None,
        execution_reference: Optional[
            BackupExecutionReference
        ] = None,
    ) -> BackupExecutionRequest:
        """
        Construye una solicitud de ejecución
        a partir de un manifiesto.
        """

        return BackupExecutionRequest(
            manifest=manifest,
            backup_configuration=backup_configuration,
            backend_name=backend_name,
            operation=operation,
            backend_configuration=backend_configuration,
            execution_reference=execution_reference,
        )