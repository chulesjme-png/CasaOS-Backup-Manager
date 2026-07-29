"""
Servicio encargado de preparar la ejecución de un BackupPlan.

Flujo:

BackupPlan
    |
    v
BackupJob
    |
    v
BackupManifest
    |
    v
BackupExecutionService
    |
    v
BackupExecutionRequest
    |
    v
BackendExecutionService
"""

from typing import Optional

from app.models.backup_configuration import (
    BackupConfiguration,
)
from app.models.backup_plan import BackupPlan

from app.services.backup_job_builder_service import (
    BackupJobBuilderService,
)
from app.services.backup_engine_service import (
    BackupEngineService,
)
from app.services.backup_execution_service import (
    BackupExecutionService,
)
from app.services.backend_execution_service import (
    BackendExecutionService,
)

from app.core.backends.backend_factory import (
    BackendFactory,
)


class BackupPlanExecutionService:
    """
    Orquestador de preparación de ejecuciones.
    """

    def __init__(
        self,
        backup_job_builder_service: Optional[
            BackupJobBuilderService
        ] = None,
        backup_engine_service: Optional[
            BackupEngineService
        ] = None,
        backup_execution_service: Optional[
            BackupExecutionService
        ] = None,
        backend_execution_service: Optional[
            BackendExecutionService
        ] = None,
    ):

        self.backup_job_builder_service = (
            backup_job_builder_service
            or BackupJobBuilderService()
        )

        self.backup_engine_service = (
            backup_engine_service
            or BackupEngineService()
        )

        self.backup_execution_service = (
            backup_execution_service
            or BackupExecutionService()
        )

        self.backend_execution_service = (
            backend_execution_service
            or BackendExecutionService(
                BackendFactory.create_registry()
            )
        )

    def execute(
        self,
        backup_plan: BackupPlan,
        backup_configuration: BackupConfiguration,
        backend_name: str,
    ):
        """
        Prepara una ejecución de backup.

        No ejecuta todavía el backend.
        """

        backup_job = (
            self.backup_job_builder_service.build(
                backup_plan
            )
        )

        manifest = (
            self.backup_engine_service.prepare(
                backup_job
            )
        )

        execution_request = (
            self.backup_execution_service.prepare(
                manifest=manifest,
                backup_configuration=backup_configuration,
                backend_name=backend_name,
            )
        )

        backend = (
            self.backend_execution_service.resolve(
                execution_request
            )
        )

        return {
            "request": execution_request,
            "backend": backend,
        }