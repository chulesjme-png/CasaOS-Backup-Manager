"""
Contrato base para los motores de backup.

BackupBackend define la interfaz que todos los futuros
motores de ejecución deberán implementar.

Ejemplos futuros:

- Duplicati
- Restic
- Borg
- Rsync

Este módulo NO ejecuta backups.
Únicamente define el contrato interno del Backup Engine.
"""

from abc import ABC, abstractmethod

from app.models.backup_manifest import BackupManifest


class BackupBackend(ABC):
    """
    Clase abstracta base para cualquier backend de backup.

    Un backend concreto debe implementar este contrato
    sin modificar el núcleo del Backup Engine.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Nombre identificativo del backend.
        """
        pass

    @abstractmethod
    def supports(self, manifest: BackupManifest) -> bool:
        """
        Indica si el backend puede trabajar con el manifiesto recibido.

        Cada backend podrá decidir sus propias capacidades.
        """
        pass

    @abstractmethod
    def execute(self, manifest: BackupManifest) -> None:
        """
        Ejecuta un backup utilizando el manifiesto.

        La implementación real pertenece al backend concreto.
        """
        pass

    @abstractmethod
    def verify(self, manifest: BackupManifest) -> bool:
        """
        Verifica el estado del backup generado.

        La lógica depende del motor utilizado.
        """
        pass

    @abstractmethod
    def restore(self, manifest: BackupManifest) -> None:
        """
        Restaura información utilizando el manifiesto.

        La implementación dependerá del backend.
        """
        pass