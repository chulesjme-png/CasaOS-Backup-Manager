"""
Backend de prueba para validar el contrato BackupBackend.

No realiza operaciones reales de backup.

Su finalidad es comprobar que el Backup Engine
puede trabajar contra cualquier implementación
del contrato de backend.
"""

from app.core.backends.backup_backend import BackupBackend
from app.models.backup_manifest import BackupManifest


class NullBackupBackend(BackupBackend):
    """
    Implementación vacía del contrato de backend.

    Utilizada únicamente para pruebas internas.
    """

    @property
    def name(self) -> str:
        return "null"

    def supports(self, manifest: BackupManifest) -> bool:
        """
        El backend nulo acepta cualquier manifiesto.
        """
        return True

    def execute(self, manifest: BackupManifest) -> None:
        """
        No realiza ninguna operación.
        """
        return None

    def verify(self, manifest: BackupManifest) -> bool:
        """
        Siempre devuelve válido.
        """
        return True

    def restore(self, manifest: BackupManifest) -> None:
        """
        No realiza restauraciones.
        """
        return None