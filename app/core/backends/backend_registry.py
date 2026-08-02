"""
Registro central de backends del Backup Engine.

Gestiona las implementaciones disponibles de BackupBackend.

No ejecuta backups.
No toma decisiones de negocio.
Únicamente mantiene referencias a backends registrados.
"""

from typing import Dict, List, Optional

from app.core.backends.backup_backend import BackupBackend


class BackendRegistry:
    """
    Registro de backends disponibles (Patrón Singleton).
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BackendRegistry, cls).__new__(cls)
            cls._instance._backends: Dict[str, BackupBackend] = {}
        return cls._instance

    def register(
        self,
        backend: BackupBackend,
    ) -> None:
        """
        Añade un backend al registro.
        """
        self._backends[backend.name] = backend

    def get(
        self,
        name: str,
    ) -> Optional[BackupBackend]:
        """
        Obtiene un backend por nombre.
        """
        return self._backends.get(name)

    def available(
        self,
    ) -> List[str]:
        """
        Devuelve los nombres de backends registrados.
        """
        return list(self._backends.keys())

    def list_backends(
        self,
    ) -> List[str]:
        """
        Alias para compatibilidad con el router de backends.
        """
        return self.available()