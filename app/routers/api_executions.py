from fastapi import APIRouter, HTTPException, status
from app.schemas.execution import (
    BackupExecutionApiRequest,
    BackupCancelApiRequest,
    BackupResultResponse,
    BackupOperationType,
)

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


@router.post("/run", response_model=BackupResultResponse)
def run_backup(req: BackupExecutionApiRequest) -> BackupResultResponse:
    """Inicia la ejecución de una copia de seguridad."""
    try:
        # AQUÍ: Simulamos una ejecución exitosa de inicio de tarea
        # Puedes adaptar este bloque si tienes un ejecutor real como DuplicatiService
        return BackupResultResponse(
            success=True,
            backend=req.backend_name,
            application=req.application,
            operation=BackupOperationType.RUN_BACKUP.value,
            execution_reference={
                "execution_id": "exec_001",
                "task_id": "task_full_system",
                "backend": req.backend_name,
            },
            errors=[],
            warnings=[],
            metadata={
                "destination_url": req.destination_url,
                "sources": req.sources,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"errors": [str(e)], "warnings": []},
        )


@router.post("/cancel", response_model=BackupResultResponse)
def cancel_backup(req: BackupCancelApiRequest) -> BackupResultResponse:
    """Cancela una tarea de copia de seguridad en ejecución."""
    try:
        return BackupResultResponse(
            success=True,
            backend=req.backend_name,
            application=req.application,
            operation=BackupOperationType.CANCEL.value,
            execution_reference=(
                req.execution_reference.model_dump()
                if req.execution_reference
                else None
            ),
            errors=[],
            warnings=[],
            metadata={},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"errors": [str(e)], "warnings": []},
        )