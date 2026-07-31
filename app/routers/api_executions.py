"""
Router de API para disparar ejecuciones, consultar estados y cancelar tareas.
"""

from fastapi import APIRouter, HTTPException, status

from app.models.backend_configuration import BackendConfiguration
from app.models.backup_configuration import BackupConfiguration
from app.models.backup_execution_reference import BackupExecutionReference
from app.models.backup_execution_request import BackupExecutionRequest
from app.models.backup_manifest import BackupManifest
from app.models.backup_operation import BackupOperationType
from app.schemas.execution import (
    BackupExecutionApiRequest,
    BackupResultResponse,
    BackupTaskCancelApiRequest,
    BackupTaskStatusApiRequest,
)
from app.services.backup_engine_service import BackupEngineService

router = APIRouter(
    prefix="/api/v1/executions",
    tags=["Executions"],
)


@router.post("/run", response_model=BackupResultResponse)
def run_backup(req: BackupExecutionApiRequest) -> BackupResultResponse:
    """
    Inicia la ejecución de una copia de seguridad.
    """
    manifest = BackupManifest(
        application=req.application,
        sources=req.sources,
        excluded_sources=req.excluded_sources,
        warnings=[],
        estimated_size=0,
    )

    params = {}
    if req.backup_id:
        params["backup_id"] = req.backup_id

    backup_config = BackupConfiguration(
        destination_url=req.destination_url,
        parameters=params,
    )

    backend_config = BackendConfiguration(
        backend_name=req.backend_name,
        configuration={
            "url": req.backend_url,
            "password": req.backend_password,
        },
    )

    exec_request = BackupExecutionRequest(
        manifest=manifest,
        backup_configuration=backup_config,
        backend_name=req.backend_name,
        operation=BackupOperationType.RUN_BACKUP,
        backend_configuration=backend_config,
    )

    engine = BackupEngineService()
    result = engine.execute(exec_request)

    return BackupResultResponse(
        success=result.success,
        backend=result.backend,
        application=result.application,
        operation=result.operation.value,
        execution_reference=(
            {
                "execution_id": result.execution_reference.execution_id,
                "task_id": result.execution_reference.task_id,
                "backend": result.execution_reference.backend,
            }
            if result.execution_reference
            else None
        ),
        errors=result.errors,
        warnings=result.warnings,
        metadata=result.metadata,
    )


@router.post("/status", response_model=BackupResultResponse)
def get_status(req: BackupTaskStatusApiRequest) -> BackupResultResponse:
    """
    Consulta el estado de una tarea activa o del estado general del servidor backend.
    """
    manifest = BackupManifest(
        application="status-check",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=0,
    )

    backend_config = BackendConfiguration(
        backend_name=req.backend_name,
        configuration={
            "url": req.backend_url,
            "password": req.backend_password,
        },
    )

    exec_ref = None
    if req.task_id:
        exec_ref = BackupExecutionReference(
            execution_id=req.task_id,
            task_id=req.task_id,
            backend=req.backend_name,
        )

    exec_request = BackupExecutionRequest(
        manifest=manifest,
        backup_configuration=BackupConfiguration(destination_url=""),
        backend_name=req.backend_name,
        operation=BackupOperationType.GET_STATUS,
        backend_configuration=backend_config,
        execution_reference=exec_ref,
    )

    engine = BackupEngineService()
    result = engine.execute(exec_request)

    return BackupResultResponse(
        success=result.success,
        backend=result.backend,
        application=result.application,
        operation=result.operation.value,
        execution_reference=(
            {
                "execution_id": result.execution_reference.execution_id,
                "task_id": result.execution_reference.task_id,
                "backend": result.execution_reference.backend,
            }
            if result.execution_reference
            else None
        ),
        errors=result.errors,
        warnings=result.warnings,
        metadata=result.metadata,
    )


@router.post("/cancel", response_model=BackupResultResponse)
def cancel_task(req: BackupTaskCancelApiRequest) -> BackupResultResponse:
    """
    Solicita la cancelación de una tarea en curso por su task_id.
    """
    manifest = BackupManifest(
        application="cancel-operation",
        sources=[],
        excluded_sources=[],
        warnings=[],
        estimated_size=0,
    )

    backend_config = BackendConfiguration(
        backend_name=req.backend_name,
        configuration={
            "url": req.backend_url,
            "password": req.backend_password,
        },
    )

    exec_ref = BackupExecutionReference(
        execution_id=req.task_id,
        task_id=req.task_id,
        backend=req.backend_name,
    )

    exec_request = BackupExecutionRequest(
        manifest=manifest,
        backup_configuration=BackupConfiguration(destination_url=""),
        backend_name=req.backend_name,
        operation=BackupOperationType.CANCEL,
        backend_configuration=backend_config,
        execution_reference=exec_ref,
    )

    engine = BackupEngineService()
    result = engine.execute(exec_request)

    return BackupResultResponse(
        success=result.success,
        backend=result.backend,
        application=result.application,
        operation=result.operation.value,
        execution_reference=(
            {
                "execution_id": result.execution_reference.execution_id,
                "task_id": result.execution_reference.task_id,
                "backend": result.execution_reference.backend,
            }
            if result.execution_reference
            else None
        ),
        errors=result.errors,
        warnings=result.warnings,
        metadata=result.metadata,
    )