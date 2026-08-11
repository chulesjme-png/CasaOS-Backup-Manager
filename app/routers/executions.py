from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database.session import get_db, SessionLocal
from app.schemas.execution import ExecutionCreate, ExecutionResponse, ExecutionUpdate, ExecutionStatus
from app.services.execution_history_service import ExecutionHistoryService
from app.services.background_worker_service import BackgroundWorkerService
from app.services.backup_engine_service import BackupEngineService

router = APIRouter(prefix="/api/v1/executions", tags=["Executions"])


@router.post("/run", response_model=ExecutionResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_execution(
    payload: ExecutionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    backup_engine: BackupEngineService = Depends()
):
    history_service = ExecutionHistoryService(db)
    
    # 1. Crear el registro en la BD en estado PENDING
    record = history_service.create_execution(payload)
    
    # 2. Despachar la tarea a segundo plano
    background_tasks.add_task(
        BackgroundWorkerService.run_backup_job_async,
        execution_id=record.id,
        db_factory=SessionLocal,
        backup_engine_service=backup_engine
    )

    return record


@router.get("/{execution_id}", response_model=ExecutionResponse)
def get_execution_status(execution_id: str, db: Session = Depends(get_db)):
    history_service = ExecutionHistoryService(db)
    record = history_service.get_execution(execution_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ejecución con ID {execution_id} no encontrada."
        )
    return record


@router.get("", response_model=List[ExecutionResponse])
def list_execution_history(limit: int = 20, db: Session = Depends(get_db)):
    history_service = ExecutionHistoryService(db)
    return history_service.list_executions(limit=limit)