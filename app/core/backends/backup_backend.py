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

from app.models.backup_operation import (
    BackupOperationType,
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


    def supports_operation(
        self,
        operation: BackupOperationType,
    ) -> bool:
        """
        Indica si el backend soporta
        una operación concreta.
        """

        capabilities = self.capabilities

        mapping = {
            BackupOperationType.CREATE_JOB:
                capabilities.can_create_jobs,

            BackupOperationType.RUN_BACKUP:
                capabilities.can_run_backup,

            BackupOperationType.GET_STATUS:
                capabilities.can_get_status,

            BackupOperationType.CANCEL:
                capabilities.can_cancel_backup,

            BackupOperationType.RESTORE:
                capabilities.can_restore,

            BackupOperationType.VERIFY:
                capabilities.can_verify,
        }

        return mapping.get(
            operation,
            False,
        )


    @abstractmethod
    def execute(
        self,
        request: BackupExecutionRequest,
    ) -> BackupResult:
        """
        Ejecuta una operación y devuelve
        un resultado normalizado.
        """
        raise NotImplementedError