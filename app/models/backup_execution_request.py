"""
Modelo que representa una solicitud de ejecución
de backup preparada.

Une un BackupManifest con la referencia
al backend seleccionado.

No ejecuta operaciones.
No contiene lógica de selección.
"""

from app.models.backup_manifest import BackupManifest


class BackupExecutionRequest:
    """
    Solicitud preparada para un backend.
    """

    def __init__(
        self,
        manifest: BackupManifest,
        backend_name: str,
    ):
        self.manifest = manifest
        self.backend_name = backend_name