"""
Modelo que representa una solicitud de ejecución
de backup preparada.

Une un BackupManifest con la referencia
al backend seleccionado, la operación solicitada
y su configuración.

No ejecuta operaciones.
No contiene lógica de selección.
"""

from app.models.backup_manifest import BackupManifest
from app.models.backend_configuration import BackendConfiguration
from app.models.backup_operation import BackupOperationType


class BackupExecutionRequest:
    """
    Solicitud preparada para un backend.
    """

    def __init__(
        self,
        manifest: BackupManifest,
        backend_name: str,
        operation: BackupOperationType = BackupOperationType.RUN_BACKUP,
        backend_configuration: BackendConfiguration = None,
    ):
        self.manifest = manifest
        self.backend_name = backend_name
        self.operation = operation

        if backend_configuration is None:
            backend_configuration = BackendConfiguration(
                backend_name=backend_name
            )

        self.backend_configuration = backend_configuration