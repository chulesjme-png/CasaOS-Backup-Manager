"""
Modelo que representa una solicitud preparada para ejecutar
una operación de backup.

Une:

- Qué copiar (BackupManifest)
- Cómo copiar (BackupConfiguration)
- Qué backend utilizar
- Configuración del backend
- Operación solicitada
- Referencia opcional a una ejecución remota.

No ejecuta operaciones.
No contiene lógica de selección.
"""

from app.models.backup_configuration import (
    BackupConfiguration,
)

from app.models.backup_execution_reference import (
    BackupExecutionReference,
)

from app.models.backup_manifest import (
    BackupManifest,
)

from app.models.backend_configuration import (
    BackendConfiguration,
)

from typing import Optional

from app.models.backup_operation import (
    BackupOperationType,
)


class BackupExecutionRequest:
    """
    Solicitud preparada para un backend.
    """

    def __init__(
        self,
        manifest: BackupManifest,
        backup_configuration: BackupConfiguration,
        backend_name: str,
        operation: BackupOperationType = (
            BackupOperationType.RUN_BACKUP
        ),
        backend_configuration: BackendConfiguration = None,
        execution_reference: (
            Optional[BackupExecutionReference]
        ) = None,
    ) -> None:

        self.manifest = manifest

        self.backup_configuration = (
            backup_configuration
        )

        self.backend_name = backend_name

        self.operation = operation

        self.execution_reference = (
            execution_reference
        )

        if backend_configuration is None:

            backend_configuration = (
                BackendConfiguration(
                    backend_name=backend_name
                )
            )

        self.backend_configuration = (
            backend_configuration
        )