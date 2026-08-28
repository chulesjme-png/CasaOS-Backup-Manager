"""
Backend Duplicati.

Primera integración real con el servidor Duplicati.

Responsabilidades:

- Implementar el contrato BackupBackend.
- Consumir BackendConfiguration.
- Consumir BackupConfiguration.
- Construir trabajos internos de Duplicati.
- Construir payloads REST para Duplicati.
- Comunicarse con Duplicati mediante DuplicatiClient.
- Transformar la respuesta en BackupResult.

No contiene lógica HTTP.
No conoce Docker.
No conoce CasaOS.

La comunicación externa está delegada en:
app.connectors.duplicati.DuplicatiClient
"""

from datetime import datetime
from typing import Optional

from app.connectors.duplicati.duplicati_client import (
    DuplicatiClient,
)
from app.connectors.duplicati.duplicati_payload_builder import (
    DuplicatiPayloadBuilder,
)
from app.connectors.duplicati.duplicati_response_mapper import (
    DuplicatiResponseMapper,
)
from app.connectors.exceptions import (
    ConnectorError,
)
from app.core.backends.backup_backend import (
    BackupBackend,
)
from app.models.backend_capabilities import (
    BackendCapabilities,
)
from app.models.backup_execution_request import (
    BackupExecutionRequest,
)
from app.models.backup_execution_reference import (
    BackupExecutionReference,
)
from app.models.backup_operation import (
    BackupOperationType,
)
from app.models.backup_resource_type import (
    BackupResourceType,
)
from app.models.backup_result import (
    BackupResult,
)
from app.services.duplicati_job_builder import (
    DuplicatiJobBuilder,
)


class DuplicatiBackend(BackupBackend):
    """
    Backend basado en Duplicati.
    """

    @property
    def name(self) -> str:
        return "duplicati"

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            backend=self.name,
            version="unknown",
            api_available=True,
            can_create_jobs=True,
            can_run_backup=True,
            can_get_status=True,
            can_cancel_backup=True,
            can_restore=True,
            can_verify=False,
            supports_encryption=True,
            supports_compression=True,
            supports_retention=True,
            supports_scheduling=True,
            metadata={
                "provider": "Duplicati",
            },
        )

    def execute(
        self,
        request: BackupExecutionRequest,
    ) -> BackupResult:

        operation = request.operation

        if operation == BackupOperationType.CREATE_JOB:
            return self._create_job(request)

        if operation == BackupOperationType.RUN_BACKUP:
            return self._run_backup(request)

        if operation == BackupOperationType.GET_STATUS:
            return self._get_status(request)

        if operation == BackupOperationType.CANCEL:
            return self._cancel(request)

        if operation == BackupOperationType.RESTORE:
            return self._restore(request)

        if operation == BackupOperationType.VERIFY:
            return self._verify(request)

        raise ValueError(
            f"Operación no soportada: {operation}"
        )

    def _create_job(
        self,
        request: BackupExecutionRequest,
    ) -> BackupResult:

        started_at = datetime.utcnow()
        warnings = []
        errors = []
        metadata = {}
        execution_reference: Optional[BackupExecutionReference] = None
        success = False

        try:
            job_builder = DuplicatiJobBuilder()
            job = job_builder.build(
                manifest=request.manifest,
                configuration=request.backup_configuration,
            )

            payload_builder = DuplicatiPayloadBuilder()
            payload = payload_builder.build(job)

            client = self._build_client(request)
            response = client.create_job(payload)

            execution_reference = DuplicatiResponseMapper.from_create_job_response(response)

            metadata = {
                "duplicati_job": job.to_payload(),
                "duplicati_payload": payload,
            }
            success = True

        except ConnectorError as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(str(exc))

        return self._build_result(
            request=request,
            success=success,
            started_at=started_at,
            warnings=warnings,
            errors=errors,
            execution_reference=execution_reference,
            metadata=metadata,
        )

    def _run_backup(
        self,
        request: BackupExecutionRequest,
    ) -> BackupResult:

        started_at = datetime.utcnow()
        warnings = []
        errors = []
        metadata = {}
        execution_reference: Optional[BackupExecutionReference] = request.execution_reference
        success = False

        try:
            backup_id = None

            if execution_reference and execution_reference.resource_id:
                backup_id = execution_reference.resource_id
            elif request.backup_configuration and request.backup_configuration.options:
                backup_id = request.backup_configuration.options.get("backup_id") or request.backup_configuration.options.get("job_id")

            if not backup_id:
                raise ValueError("No se proporcionó backup_id o execution_reference para ejecutar la copia.")

            client = self._build_client(request)
            response = client.run_backup(int(backup_id))

            if isinstance(response, dict):
                task_id = response.get("ID") or response.get("TaskId") or response.get("taskId")
                if task_id:
                    execution_reference = BackupExecutionReference(
                        backend=self.name,
                        resource_type=BackupResourceType.TASK,
                        resource_id=str(task_id),
                        metadata={"raw_reference": response, "execution_id": str(backup_id)},
                    )
                metadata = {"duplicati_run_response": response}

            success = True

        except ConnectorError as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(str(exc))

        return self._build_result(
            request=request,
            success=success,
            started_at=started_at,
            warnings=warnings,
            errors=errors,
            execution_reference=execution_reference,
            metadata=metadata,
        )

    def _get_status(
        self,
        request: BackupExecutionRequest,
    ) -> BackupResult:

        started_at = datetime.utcnow()
        warnings = []
        errors = []
        metadata = {}
        execution_reference: Optional[BackupExecutionReference] = request.execution_reference
        success = False

        try:
            client = self._build_client(request)

            if execution_reference and execution_reference.resource_id:
                task_data = client.get_task(int(execution_reference.resource_id))
                metadata = {
                    "duplicati_task": task_data,
                    "task_id": execution_reference.resource_id,
                }
            else:
                server_state = client.get_server_state()
                metadata = {
                    "duplicati_server_state": server_state,
                    "duplicati_version": server_state.get("Version", "unknown"),
                }

            success = True

        except ConnectorError as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(str(exc))

        return self._build_result(
            request=request,
            success=success,
            started_at=started_at,
            warnings=warnings,
            errors=errors,
            execution_reference=execution_reference,
            metadata=metadata,
        )

    def _cancel(
        self,
        request: BackupExecutionRequest,
    ) -> BackupResult:

        started_at = datetime.utcnow()
        warnings = []
        errors = []
        metadata = {}
        execution_reference: Optional[BackupExecutionReference] = request.execution_reference
        success = False

        try:
            task_id = None

            if execution_reference and execution_reference.resource_id:
                task_id = execution_reference.resource_id
            elif request.backup_configuration and request.backup_configuration.options:
                task_id = request.backup_configuration.options.get("task_id")

            if not task_id:
                raise ValueError("No se proporcionó task_id o execution_reference para cancelar la tarea.")

            client = self._build_client(request)
            client.stop_task(int(task_id))

            metadata = {
                "cancelled_task_id": str(task_id),
                "action": "stop_task",
            }

            success = True

        except ConnectorError as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(str(exc))

        return self._build_result(
            request=request,
            success=success,
            started_at=started_at,
            warnings=warnings,
            errors=errors,
            execution_reference=execution_reference,
            metadata=metadata,
        )

    def _restore(
        self,
        request: BackupExecutionRequest,
    ) -> BackupResult:
        return self._not_implemented(request, "RESTORE")

    def _verify(
        self,
        request: BackupExecutionRequest,
    ) -> BackupResult:
        return self._not_implemented(request, "VERIFY")

    def _build_client(
        self,
        request: BackupExecutionRequest,
    ) -> DuplicatiClient:

        configuration = {}

        if request.backend_configuration:
            configuration = request.backend_configuration.configuration

        url = configuration.get("url")

        if not url:
            raise ConnectorError("Duplicati URL no configurada")

        timeout = configuration.get("timeout", 30)
        password = configuration.get("password", "")

        return DuplicatiClient(
            base_url=url,
            timeout=timeout,
            password=password,
        )

    def _build_result(
        self,
        request: BackupExecutionRequest,
        success: bool,
        started_at: datetime,
        warnings,
        errors,
        metadata,
        execution_reference: Optional[BackupExecutionReference] = None,
    ) -> BackupResult:

        return BackupResult(
            success=success,
            backend=self.name,
            application=request.manifest.application,
            started_at=started_at,
            finished_at=datetime.utcnow(),
            bytes_processed=0,
            warnings=warnings,
            errors=errors,
            execution_reference=execution_reference,
            metadata=metadata,
        )

    def _not_implemented(
        self,
        request: BackupExecutionRequest,
        operation: str,
    ) -> BackupResult:

        return self._build_result(
            request=request,
            success=False,
            started_at=datetime.utcnow(),
            warnings=[],
            errors=[f"Operación {operation} todavía no implementada."],
            metadata={},
        )