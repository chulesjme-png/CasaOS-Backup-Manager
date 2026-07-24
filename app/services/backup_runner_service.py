"""
Servicio encargado de orquestar una ejecución
completa del Backup Engine.

Coordina:

BackupJob
    |
    v
BackupManifest
    |
    v
BackupExecutionRequest
    |
    v
Backend
    |
    v
BackupResult

No contiene lógica de backup.
No conoce motores concretos.
Su responsabilidad es coordinar el flujo.
"""

from datetime import datetime
from typing import Optional

from app.models.backup_job import BackupJob

from app.models.backup_operation import (
    BackupOperationType,
)

from app.models.backup_result import BackupResult

from app.services.backup_engine_service import (
    BackupEngineService,
)

from app.services.backup_execution_service import (
    BackupExecutionService,
)

from app.services.backend_execution_service import (
    BackendExecutionService,
)


class BackupRunnerService:
    """
    Orquestador principal de una ejecución
    del Backup Engine.
    """

    def __init__(
        self,
        backend_execution_service: BackendExecutionService,
        engine_service: Optional[BackupEngineService] = None,
        execution_service: Optional[BackupExecutionService] = None,
    ):
        self.engine_service = (
            engine_service
            or BackupEngineService()
        )

        self.execution_service = (
            execution_service
            or BackupExecutionService()
        )

        self.backend_execution_service = (
            backend_execution_service
        )

    def run(
        self,
        backup_job: BackupJob,
        backend_name: str,
        operation: BackupOperationType = (
            BackupOperationType.RUN_BACKUP
        ),
    ) -> BackupResult:
        """
        Ejecuta una operación completa
        del Backup Engine.
        """

        manifest = self.engine_service.prepare(
            backup_job
        )

        request = self.execution_service.prepare(
            manifest=manifest,
            backend_name=backend_name,
            operation=operation,
        )

        backend = (
            self.backend_execution_service.resolve(
                request
            )
        )

        if backend is None:

            raise RuntimeError(
                f"Backend '{backend_name}' no registrado."
            )

        if not backend.supports_operation(
            request.operation
        ):

            now = datetime.utcnow()

            return BackupResult(
                success=False,
                backend=backend.name,
                application=request.manifest.application,
                started_at=now,
                finished_at=now,
                bytes_processed=0,
                warnings=[],
                errors=[
                    (
                        "Backend does not support "
                        f"operation '{request.operation.value}'."
                    )
                ],
                metadata={
                    "operation": request.operation.value,
                },
            )

        return backend.execute(
            request
        )