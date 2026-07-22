"""
Modelo que representa una solicitud de ejecución
de backup preparada.

Une un BackupManifest con la referencia
al backend seleccionado y su configuración.

No ejecuta operaciones.
No contiene lógica de selección.
"""

from app.models.backup_manifest import BackupManifest
from app.models.backend_configuration import BackendConfiguration


class BackupExecutionRequest:
    """
    Solicitud preparada para un backend.
    """

    def __init__(
        self,
        manifest: BackupManifest,
        backend_name: str,
        backend_configuration: BackendConfiguration = None,
    ):
        self.manifest = manifest
        self.backend_name = backend_name

        if backend_configuration is None:
            backend_configuration = BackendConfiguration(
                backend_name=backend_name
            )

        self.backend_configuration = backend_configuration