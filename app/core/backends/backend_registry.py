"""
Registro central de backends del Backup Engine.

Gestiona las implementaciones disponibles de BackupBackend.

No ejecuta backups.
No toma decisiones de negocio.
Únicamente mantiene referencias a backends registrados.
"""

from app.core.backends.backup_backend import BackupBackend


class BackendRegistry:
    """
    Registro de backends disponibles.
    """

    def __init__(self):
        self._backends: dict[str, BackupBackend] = {}

    def register(self, backend: BackupBackend) -> None:
        """
        Añade un backend al registro.
        """
        self._backends[backend.name] = backend

    def get(self, name: str) -> BackupBackend | None:
        """
        Obtiene un backend por nombre.
        """
        return self._backends.get(name)

    def available(self) -> list[str]:
        """
        Devuelve los nombres de backends registrados.
        """
        return list(self._backends.keys())