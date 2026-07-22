"""
Factory para construir el registro inicial
de backends del Backup Engine.

No ejecuta backups.
No decide qué backend utilizar.

Únicamente crea y configura
las implementaciones disponibles.
"""

from app.core.backends.backend_registry import (
    BackendRegistry,
)

from app.core.backends.null_backup_backend import (
    NullBackupBackend,
)

from app.core.backends.duplicati_backend import (
    DuplicatiBackend,
)


class BackendFactory:
    """
    Constructor central del ecosistema de backends.
    """

    @staticmethod
    def create_registry() -> BackendRegistry:
        """
        Crea un registro inicial con los backends disponibles.
        """

        registry = BackendRegistry()

        registry.register(
            NullBackupBackend()
        )

        registry.register(
            DuplicatiBackend()
        )

        return registry