import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.scheduler_service import add_cron_job, remove_cron_job
from app.models.execution import ScheduleRecordModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/schedules", tags=["schedules"])


# ------------------------------------------------------------------------------
# SCHEMAS (Pydantic)
# ------------------------------------------------------------------------------

class ScheduleCreate(BaseModel):
    app_name: str
    cron_expression: str  # Ej: "0 2 * * *" (diario a las 02:00 AM)
    destination_path: Optional[str] = "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adf6fa"
    is_active: Optional[bool] = True


class ScheduleResponse(BaseModel):
    id: int
    app_name: str
    cron_expression: str
    destination_path: str
    is_active: bool

    class Config:
        from_attributes = True


# ------------------------------------------------------------------------------
# ENDPOINTS REST API
# ------------------------------------------------------------------------------

@router.get("", response_model=List[ScheduleResponse])
def list_schedules(db: Session = Depends(get_db)):
    """Devuelve el listado de todas las tareas de respaldo programadas."""
    schedules = db.query(ScheduleRecordModel).all()
    return schedules


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(payload: ScheduleCreate, db: Session = Depends(get_db)):
    """Crea una nueva regla de automatización y la registra en el motor APScheduler."""
    schedule = ScheduleRecordModel(
        app_name=payload.app_name,
        cron_expression=payload.cron_expression,
        destination_path=payload.destination_path,
        is_active=payload.is_active
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    # Registrar en el motor cron si está marcado como activo
    if schedule.is_active:
        add_cron_job(
            job_id=str(schedule.id),
            app_name=schedule.app_name,
            cron_expression=schedule.cron_expression,
            destination_path=schedule.destination_path
        )

    return schedule


@router.put("/{schedule_id}/toggle", response_model=ScheduleResponse)
def toggle_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Activa o deshabilita la ejecución automática de una programación existente."""
    schedule = db.query(ScheduleRecordModel).filter(ScheduleRecordModel.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Programación no encontrada")

    schedule.is_active = not schedule.is_active
    db.commit()
    db.refresh(schedule)

    if schedule.is_active:
        add_cron_job(
            job_id=str(schedule.id),
            app_name=schedule.app_name,
            cron_expression=schedule.cron_expression,
            destination_path=schedule.destination_path
        )
    else:
        remove_cron_job(str(schedule.id))

    return schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Elimina una programación de la base de datos y detiene su ejecución en APScheduler."""
    schedule = db.query(ScheduleRecordModel).filter(ScheduleRecordModel.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Programación no encontrada")

    remove_cron_job(str(schedule.id))
    db.delete(schedule)
    db.commit()
    return None