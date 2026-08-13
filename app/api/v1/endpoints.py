import os
import logging
from typing import List, Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, Field

from app.core.config import config_manager, AppConfig
from app.services.disk_service import disk_service
from app.services.discovery_service import discovery_service
from app.services.duplicati_service import duplicati_service
from app.services.scheduler_service import scheduler_service

logger = logging.getLogger("casaos-backup")
router = APIRouter()

# --- MODELOS PYDANTIC PARA VALIDACIÓN DE ENTRADA ---

class ScheduleUpdateRequest(BaseModel):
    schedule_frequency: str = Field(..., description="Frecuencia: 'daily', 'weekly', 'monthly'")
    schedule_time: str = Field(..., description="Hora en formato HH:MM (ej. '03:00')")

class RestoreRequest(BaseModel):
    backup_file: str = Field(..., description="Nombre o ruta del archivo de copia a restaurar")
    target_app: Optional[str] = Field("all", description="Nombre de la app específica o 'all' para todo el sistema")


# --- ENDPOINTS DE CONFIGURACIÓN Y ESTADO ---

@router.get("/config", response_model=AppConfig)
def get_config():
    return config_manager.config

@router.post("/config", response_model=AppConfig)
def update_config(payload: Dict[str, str]):
    for key, value in payload.items():
        config_manager.update_key(key, value)
    
    # Si la actualización afectó la programación, recargamos el scheduler
    if "schedule_frequency" in payload or "schedule_time" in payload:
        scheduler_service.reload_schedule()
        
    return config_manager.config

@router.get("/disks")
def get_disks():
    return disk_service.get_system_disks()

@router.get("/apps")
def get_apps():
    return discovery_service.scan_apps()


# --- ENDPOINTS MODAL 1: PROGRAMACIÓN DE COPIAS ---

@router.get("/schedules")
def get_schedule():
    config = config_manager.config
    return {
        "schedule_frequency": config.schedule_frequency,
        "schedule_time": config.schedule_time
    }

@router.post("/schedules")
def update_schedule(payload: ScheduleUpdateRequest):
    try:
        config_manager.update_key("schedule_frequency", payload.schedule_frequency)
        config_manager.update_key("schedule_time", payload.schedule_time)
        
        # Aplicar la nueva programación en tiempo real
        scheduler_service.reload_schedule()
        
        return {
            "status": "success",
            "message": "Programación actualizada y sincronizada correctamente",
            "schedule_frequency": payload.schedule_frequency,
            "schedule_time": payload.schedule_time
        }
    except Exception as e:
        logger.error(f"Error actualizando la programación: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- ENDPOINTS MODAL 2: RESTAURACIÓN Y EXPLORACIÓN ---

@router.get("/backups/list")
def list_available_backups():
    """Explora recursivamente el disco destino en busca de archivos de copia de seguridad."""
    target_disk = config_manager.config.selected_target_disk
    if not target_disk or not os.path.exists(target_disk):
        return {"target_disk": target_disk, "backups": []}

    backups = []
    try:
        # Exploración recursiva para detectar backups dentro de subdirectorios
        for root, _, files in os.walk(target_disk):
            for file in files:
                if file.endswith(".tar.gz") or file.endswith(".zip") or "backup" in file.lower():
                    file_path = os.path.join(root, file)
                    stats = os.stat(file_path)
                    rel_path = os.path.relpath(file_path, target_disk)
                    backups.append({
                        "filename": rel_path,
                        "path": file_path,
                        "size_mb": round(stats.st_size / (1024 * 1024), 2),
                        "created_at": stats.st_mtime
                    })
    except Exception as e:
        logger.error(f"Error listando archivos de backup en {target_disk}: {e}")

    return {
        "target_disk": target_disk,
        "backups": backups
    }

@router.post("/backups/restore")
async def restore_backup(payload: RestoreRequest):
    """Ejecuta el proceso de restauración real delegando al servicio."""
    if not payload.backup_file:
        raise HTTPException(status_code=400, detail="Debe especificar un archivo de copia de seguridad.")
    
    try:
        success = await duplicati_service.restore_backup(payload.backup_file, payload.target_app or "all")
        if success:
            return {
                "status": "success",
                "message": f"Restauración completada con éxito para '{payload.backup_file}'."
            }
        else:
            raise HTTPException(status_code=500, detail="Ocurrió un error al procesar el archivo de restauración.")
    except Exception as e:
        logger.error(f"Error en restauración: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- ENDPOINTS DE EJECUCIÓN MANUAL ---

@router.post("/backups/run-app/{app_name}")
async def run_app_backup(app_name: str):
    apps = discovery_service.scan_apps()
    app = next((a for a in apps if a["name"] == app_name), None)
    if not app:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")

    success = await duplicati_service.run_app_backup(app["name"], app["path"])
    return {"status": "success" if success else "failed", "app": app_name}

@router.post("/backups/run-full")
async def run_full_backup():
    success = await duplicati_service.run_full_disaster_recovery()
    return {"status": "success" if success else "failed"}