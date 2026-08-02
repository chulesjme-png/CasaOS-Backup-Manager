from fastapi import APIRouter, HTTPException, status
from app.schemas.execution import (
    BackupExecutionApiRequest,
    BackupCancelApiRequest,
    BackupResultResponse,
    BackupConfiguration,
    BackupManifest,
    BackupOperationType,
    BackupResult,
)

# ------------------------------------------------------------------
# CORRECCIÓN AQUÍ: Se importa desde backup_engine_service
# ------------------------------------------------------------------
from app.services.backup_engine_service import BackupEngineService

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


@router.post("/run", response_model=BackupResultResponse)
def run_backup(req: BackupExecutionApiRequest) -> BackupResultResponse:
    """Inicia la ejecución de una copia de seguridad."""
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

    engine = BackupEngineService()
    result: BackupResult = engine.execute(
        backend_name=req.backend_name,
        operation=BackupOperationType.RUN_BACKUP,
        manifest=manifest,
        config=backup_config,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"errors": result.errors, "warnings": result.warnings},
        )

    return BackupResultResponse(
        success=result.success,
        backend=result.backend,
        application=result.application,
        # CORRECCIÓN: Usamos el enum directamente porque result ya no lo tiene
        operation=BackupOperationType.RUN_BACKUP.value,
        execution_reference=(
            result.execution_reference.model_dump()
            if result.execution_reference
            else None
        ),
        errors=result.errors,
        warnings=result.warnings,
        metadata=result.metadata,
    )


@router.post("/cancel", response_model=BackupResultResponse)
def cancel_backup(req: BackupCancelApiRequest) -> BackupResultResponse:
    """Cancela una tarea de copia de seguridad en ejecución."""
    manifest = BackupManifest(application=req.application)
    backup_config = BackupConfiguration(destination_url="")

    engine = BackupEngineService()
    result: BackupResult = engine.execute(
        backend_name=req.backend_name,
        operation=BackupOperationType.CANCEL,
        manifest=manifest,
        config=backup_config,
        execution_reference=req.execution_reference,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"errors": result.errors, "warnings": result.warnings},
        )

    return BackupResultResponse(
        success=result.success,
        backend=result.backend,
        application=result.application,
        # CORRECCIÓN: Usamos el enum directamente
        operation=BackupOperationType.CANCEL.value,
        execution_reference=(
            result.execution_reference.model_dump()
            if result.execution_reference
            else None
        ),
        errors=result.errors,
        warnings=result.warnings,
        metadata=result.metadata,
    )