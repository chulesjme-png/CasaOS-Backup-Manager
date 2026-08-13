from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.scheduler_service import scheduler_service

router = APIRouter(prefix="/api/v1/scheduler", tags=["Scheduler"])

class ScheduleConfig(BaseModel):
    hour: int
    minute: int

@router.get("/")
def get_scheduler_status():
    """Obtiene las tareas activas en el planificador."""
    return {
        "status": "running" if scheduler_service.is_running else "stopped",
        "jobs": scheduler_service.get_scheduled_jobs()
    }

@router.post("/disaster-recovery")
def update_disaster_recovery_schedule(config: ScheduleConfig):
    """Actualiza la hora del respaldo automático diario."""
    if not (0 <= config.hour <= 23) or not (0 <= config.minute <= 59):
        raise HTTPException(status_code=400, detail="Hora o minuto inválidos.")
    
    scheduler_service.schedule_daily_disaster_recovery(hour=config.hour, minute=config.minute)
    return {"status": "success", "message": f"Respaldo reprogramado a las {config.hour:02d}:{config.minute:02d}"}