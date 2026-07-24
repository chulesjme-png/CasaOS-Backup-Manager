"""
Contrato base para cualquier backend de backup.
"""

from abc import ABC, abstractmethod

from app.models.backup_execution_request import (
    BackupExecutionRequest,
)

from app.models.backup_result import (
    BackupResult,
)

from app.models.backend_capabilities import (
    BackendCapabilities,
)


class BackupBackend(ABC):
    """
    Contrato común para cualquier backend de backup.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Nombre único del backend.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def capabilities(self) -> BackendCapabilities:
        """
        Capacidades declaradas por el backend.
        """
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        request: BackupExecutionRequest,
    ) -> BackupResult:
        """
        Ejecuta un backup y devuelve un resultado normalizado.
        """
        raise NotImplementedError