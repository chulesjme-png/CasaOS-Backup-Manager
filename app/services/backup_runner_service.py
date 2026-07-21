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

from typing import Optional

from app.models.backup_job import BackupJob
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
    de backup.
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
    ) -> BackupResult:
        """
        Ejecuta un flujo completo de backup.
        """

        # 1. Construcción del manifiesto
        manifest = self.engine_service.prepare(
            backup_job
        )

        # 2. Preparación de la solicitud
        request = self.execution_service.prepare(
            manifest,
            backend_name,
        )

        # 3. Resolución del backend
        backend = (
            self.backend_execution_service.resolve(
                request
            )
        )

        if backend is None:
            raise RuntimeError(
                f"Backend '{backend_name}' no registrado."
            )

        # 4. Ejecución
        return backend.execute(
            request
        )