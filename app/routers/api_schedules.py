from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
import json
import os

router = APIRouter(prefix="/api/v1/schedules", tags=["schedules"])

CONFIG_FILE = "app/config/schedules_config.json"


class ScheduleTask(BaseModel):
    id: str
    name: str
    target_app: str  # 'all', 'disaster_recovery', o app_id específico
    backend: str     # 'duplicati' o 'restic'
    frequency: str   # 'daily', 'weekly', 'monthly'
    time: str        # Formato 'HH:MM', ej: '03:00'
    days_of_week: Optional[List[int]] = [1] # 0 = Lunes, 6 = Domingo
    retention_days: int = 30
    enabled: bool = True
    notify_webhook: Optional[str] = ""


def load_schedules() -> List[dict]:
    if not os.path.exists(CONFIG_FILE):
        default_data = [
            {
                "id": "sched_full_daily",
                "name": "Copia Completa de Seguridad",
                "target_app": "disaster_recovery",
                "backend": "duplicati",
                "frequency": "daily",
                "time": "03:00",
                "days_of_week": [0, 1, 2, 3, 4, 5, 6],
                "retention_days": 30,
                "enabled": True,
                "notify_webhook": ""
            },
            {
                "id": "sched_apps_weekly",
                "name": "Respaldo Semanal de Datos (/DATA/AppData)",
                "target_app": "all",
                "backend": "duplicati",
                "frequency": "weekly",
                "time": "04:30",
                "days_of_week": [6],
                "retention_days": 60,
                "enabled": True,
                "notify_webhook": ""
            }
        ]
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(default_data, f, indent=4)
        return default_data

    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_schedules(data: List[dict]):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


@router.get("/")
def get_all_schedules():
    """Obtiene el listado de tareas programadas actualmente."""
    return {"schedules": load_schedules()}


@router.post("/save")
def save_schedule(task: ScheduleTask):
    """Crea o actualiza una tarea programada."""
    schedules = load_schedules()
    updated = False

    for i, s in enumerate(schedules):
        if s["id"] == task.id:
            schedules[i] = task.dict()
            updated = True
            break

    if not updated:
        schedules.append(task.dict())

    save_schedules(schedules)
    return {"success": True, "message": f"Tarea '{task.name}' guardada correctamente."}


@router.post("/toggle/{task_id}")
def toggle_schedule(task_id: str):
    """Activa o desactiva una tarea programada por su ID."""
    schedules = load_schedules()
    for s in schedules:
        if s["id"] == task_id:
            s["enabled"] = not s["enabled"]
            save_schedules(schedules)
            state = "activada" if s["enabled"] else "desactivada"
            return {"success": True, "message": f"Tarea '{s['name']}' {state}."}

    raise HTTPException(status_code=404, detail="Tarea programada no encontrada")