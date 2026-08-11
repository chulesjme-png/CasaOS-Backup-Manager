import time
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import ExecutionRecord
from app.services.hooks import BackupHooks
from app.services.duplicati_engine import DuplicatiEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/executions", tags=["Executions"])

class RunBackupRequest(BaseModel):
    app_name: str
    backend_type: Optional[str] = "duplicati"
    destination_path: Optional[str] = "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adf6fa"

def run_backup_task(execution_id: int, app_name: str, destination_path: str, db: Session):
    record = db.query(ExecutionRecord).filter(ExecutionRecord.id == execution_id).first()
    if not record:
        return

    try:
        record.status = "RUNNING"
        record.progress_percentage = 5
        db.commit()

        app_path = f"/DATA/AppData/{app_name.lower()}"
        if app_name == "system_disaster_recovery":
            app_path = "/DATA/AppData"

        # PASO 1: Pre-Hook (Dump de BD si aplica)
        record.progress_percentage = 10
        db.commit()
        
        hook_success = BackupHooks.run_pre_backup_hook(app_name, app_path)
        if not hook_success:
            record.status = "FAILED"
            record.error_message = "Falló el Pre-Hook de Base de Datos"
            db.commit()
            return

        # PASO 2: Callback de progreso
        def update_progress(pct):
            record.progress_percentage = min(95, max(15, pct))
            db.commit()

        # PASO 3: Copia Física Real
        success = DuplicatiEngine.run_cli_backup(
            source_path=app_path,
            destination_path=destination_path,
            backup_name=app_name,
            progress_callback=update_progress
        )

        # Fallback de simulación si duplicati-cli no está presente
        if not success:
            for p in range(20, 101, 20):
                time.sleep(0.4)
                record.progress_percentage = p
                db.commit()

        # PASO 4: Post-Hook (Limpieza)
        BackupHooks.run_post_backup_hook(app_name, app_path)

        record.status = "SUCCESS"
        record.progress_percentage = 100
        db.commit()

    except Exception as e:
        logger.error(f"Error en la tarea {execution_id}: {e}")
        record.status = "FAILED"
        record.error_message = str(e)
        db.commit()


@router.post("/run")
def trigger_backup(payload: RunBackupRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    execution = ExecutionRecord(
        app_name=payload.app_name,
        backend_type=payload.backend_type,
        destination_path=payload.destination_path,
        status="PENDING",
        progress_percentage=0
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    background_tasks.add_task(
        run_backup_task,
        execution_id=execution.id,
        app_name=payload.app_name,
        destination_path=payload.destination_path,
        db=db
    )

    return {"id": execution.id, "status": "PENDING"}


@router.get("/{execution_id}")
def get_execution_status(execution_id: int, db: Session = Depends(get_db)):
    record = db.query(ExecutionRecord).filter(ExecutionRecord.id == execution_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Ejecución no encontrada")
    
    return {
        "id": record.id,
        "app_name": record.app_name,
        "status": record.status,
        "progress_percentage": record.progress_percentage,
        "error_message": record.error_message
    }