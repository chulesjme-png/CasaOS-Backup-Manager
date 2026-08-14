import os
import logging
import asyncio
from typing import List, Dict, Optional, Union
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.core.config import config_manager, AppConfig
from app.core.ws_manager import ws_manager
from app.services.disk_service import disk_service
from app.services.discovery_service import discovery_service
from app.services.duplicati_service import duplicati_service
from app.services.scheduler_service import scheduler_service
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service

logger = logging.getLogger("casaos-backup")
router = APIRouter()

# --- MODELOS PYDANTIC (DTOs) ---

class ScheduleUpdateRequest(BaseModel):
    schedule_frequency: str = Field(..., description="Frecuencia: 'daily', 'weekly', 'monthly'")
    schedule_time: str = Field(..., description="Hora en formato HH:MM")

class RestoreRequest(BaseModel):
    backup_file: str = Field(...)
    target_app: Optional[str] = Field("all")

class NotificationSettings(BaseModel):
    telegram_enabled: bool
    telegram_bot_token: Optional[str] = ""
    telegram_chat_id: Optional[str] = ""
    webhook_enabled: bool
    webhook_url: Optional[str] = ""


# --- CONFIGURACIÓN & ESTADO ---

@router.get("/config", response_model=AppConfig)
def get_config():
    """
    Devuelve la configuración actual. Si no hay disco seleccionado,
    resuelve automáticamente el primer disco del sistema disponible.
    """
    if not config_manager.config.selected_target_disk:
        try:
            disks = disk_service.get_system_disks()
            if disks and len(disks) > 0:
                first_disk = disks[0].get("mountpoint") or disks[0].get("path")
                if first_disk:
                    config_manager.update_key("selected_target_disk", first_disk)
                    logger.info(f"[Config] Disco autoseleccionado por defecto: {first_disk}")
        except Exception as e:
            logger.warning(f"[Config] No se pudo resolver disco por defecto: {e}")

    return config_manager.config

@router.post("/config", response_model=AppConfig)
def update_config(payload: Dict[str, str]):
    for key, value in payload.items():
        config_manager.update_key(key, value)
    
    if "schedule_frequency" in payload or "schedule_time" in payload:
        scheduler_service.reload_schedule()
        
    return config_manager.config

@router.get("/disks")
def get_disks():
    return disk_service.get_system_disks()

@router.get("/apps")
def get_apps():
    return discovery_service.scan_apps()


# --- NOTIFICACIONES (SINCRO Y MANEJO DE TIPOS SEGURO) ---

@router.post("/notifications/settings")
async def save_notification_settings(settings: Union[NotificationSettings, Dict]):
    """
    Guarda la configuración de notificaciones y sincroniza el servicio 
    de forma compatible con diccionarios y modelos Pydantic.
    """
    try:
        # 1. Normalización del payload entrante
        if hasattr(settings, 'model_dump'):
            data = settings.model_dump()
        elif hasattr(settings, 'dict'):
            data = settings.dict()
        elif isinstance(settings, dict):
            data = settings
        else:
            data = dict(settings)

        # 2. Actualización de valores en ConfigManager
        for key, value in data.items():
            str_value = str(value) if isinstance(value, bool) else (value or "")
            config_manager.update_key(key, str_value)
            if hasattr(config_manager.config, key):
                setattr(config_manager.config, key, value)

        # 3. Persistencia en disco
        config_manager.save_config()

        # 4. Sincronización con notification_service (Soporte seguro Dict vs AppConfig)
        if hasattr(config_manager.config, "model_dump"):
            cfg_dict = config_manager.config.model_dump()
        elif hasattr(config_manager.config, "dict"):
            cfg_dict = config_manager.config.dict()
        else:
            cfg_dict = dict(config_manager.config)

        try:
            notification_service.update_config(cfg_dict)
        except Exception:
            # Fallback en caso de que notification_service espere el objeto AppConfig directamente
            notification_service.update_config(config_manager.config)
        
        logger.info("[Backend] Configuración de notificaciones y alertas guardada con éxito.")
        return {"status": "ok", "message": "Configuración guardada correctamente"}

    except Exception as e:
        logger.error(f"[Backend] Error guardando notificaciones: {e}")
        raise HTTPException(status_code=500, detail=f"Error al guardar datos: {str(e)}")

@router.post("/notifications/test")
async def test_notification(settings: NotificationSettings):
    try:
        success = await notification_service.send_test_message(
            token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            webhook_url=settings.webhook_url,
            telegram_enabled=settings.telegram_enabled,
            webhook_enabled=settings.webhook_enabled
        )
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo entregar el mensaje de prueba.")
        return {"status": "ok", "message": "Notificación de prueba enviada con éxito."}
    except Exception as e:
        logger.error(f"[Backend] Error en test de notificación: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- TAREAS DE RESPALDO (ASÍNCRONAS Y NO BLOQUEANTES) ---

async def task_run_app_backup(app_name: str, app_path: str):
    await notification_service.send_notification(
        title=f"⏳ Inicio de Copia: {app_name}",
        message=f"Se ha iniciado la copia de seguridad de la aplicación <b>{app_name}</b>.",
        status="info"
    )
    
    await ws_manager.broadcast({
        "job_id": f"backup_{app_name}",
        "percentage": 25,
        "message": f"Realizando empaquetado de {app_name}..."
    })

    if asyncio.iscoroutinefunction(duplicati_service.run_app_backup):
        success = await duplicati_service.run_app_backup(app_name, app_path)
    else:
        success = await asyncio.to_thread(duplicati_service.run_app_backup, app_name, app_path)

    if success:
        await ws_manager.broadcast({
            "job_id": f"backup_{app_name}",
            "percentage": 100,
            "message": f"¡Copia de {app_name} finalizada!"
        })
        await notification_service.send_notification(
            title=f"✅ Copia Completada: {app_name}",
            message=f"La aplicación <b>{app_name}</b> se ha respaldado con éxito.",
            status="success"
        )
    else:
        await ws_manager.broadcast({
            "job_id": f"backup_{app_name}",
            "percentage": 0,
            "message": f"Error respaldando {app_name}."
        })
        await notification_service.send_notification(
            title=f"❌ Error en Copia: {app_name}",
            message=f"Ocurrió un fallo al respaldar <b>{app_name}</b>.",
            status="error"
        )

@router.post("/backups/run-app/{app_name}")
async def run_app_backup(app_name: str, background_tasks: BackgroundTasks):
    apps = discovery_service.scan_apps()
    app = next((a for a in apps if a["name"] == app_name), None)
    if not app:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")

    background_tasks.add_task(task_run_app_backup, app["name"], app["path"])
    return {"status": "started", "message": f"Copia de {app_name} iniciada en segundo plano."}

async def task_run_full_backup():
    await notification_service.send_notification(
        title="⏳ Inicio: Disaster Recovery",
        message="Se ha iniciado la copia de seguridad completa del sistema.",
        status="info"
    )
    
    await ws_manager.broadcast({
        "job_id": "backup_disaster_recovery",
        "percentage": 20,
        "message": "Empaquetando datos y configuraciones..."
    })

    if asyncio.iscoroutinefunction(duplicati_service.run_full_disaster_recovery):
        success = await duplicati_service.run_full_disaster_recovery()
    else:
        success = await asyncio.to_thread(duplicati_service.run_full_disaster_recovery)

    if success:
        await ws_manager.broadcast({
            "job_id": "backup_disaster_recovery",
            "percentage": 100,
            "message": "¡Disaster Recovery finalizado!"
        })
        await notification_service.send_notification(
            title="✅ Disaster Recovery Finalizado",
            message="El respaldo integral del sistema se completó correctamente.",
            status="success"
        )
    else:
        await ws_manager.broadcast({
            "job_id": "backup_disaster_recovery",
            "percentage": 0,
            "message": "Error en Disaster Recovery."
        })
        await notification_service.send_notification(
            title="❌ Error en Disaster Recovery",
            message="Falló el proceso de copia integral.",
            status="error"
        )

@router.post("/backups/run-full")
async def run_full_backup(background_tasks: BackgroundTasks):
    background_tasks.add_task(task_run_full_backup)
    return {"status": "started", "message": "Disaster recovery iniciado en segundo plano."}


# --- RESTO DE ENDPOINTS ---

@router.get("/schedules")
def get_schedule():
    config = config_manager.config
    return {"schedule_frequency": config.schedule_frequency, "schedule_time": config.schedule_time}

@router.post("/schedules")
def update_schedule(payload: ScheduleUpdateRequest):
    config_manager.update_key("schedule_frequency", payload.schedule_frequency)
    config_manager.update_key("schedule_time", payload.schedule_time)
    scheduler_service.reload_schedule()
    return {"status": "success", "message": "Programación actualizada"}

@router.get("/backups/list")
def list_available_backups():
    target_disk = config_manager.config.selected_target_disk
    if not target_disk:
        return {"target_disk": target_disk, "backups": []}

    backups = []
    try:
        search_dirs = [target_disk]
        sub_backup_dir = os.path.join(target_disk, "casaos-backups")
        if os.path.exists(sub_backup_dir):
            search_dirs.append(sub_backup_dir)

        for d in search_dirs:
            if os.path.exists(d):
                for root, _, files in os.walk(d):
                    for file in files:
                        if file.endswith(".tar.gz") or file.endswith(".zip"):
                            file_path = os.path.join(root, file)
                            stats = os.stat(file_path)
                            backups.append({
                                "filename": file,
                                "path": file_path,
                                "size_mb": round(stats.st_size / (1024 * 1024), 2),
                                "created_at": stats.st_mtime
                            })
    except Exception as e:
        logger.error(f"[Backend] Error escaneando backups: {e}")
        raise HTTPException(status_code=500, detail=f"Error leyendo almacenamiento: {str(e)}")

    return {"target_disk": target_disk, "backups": backups}

@router.get("/logs")
def get_execution_logs():
    logs = audit_service.get_logs(limit=50)
    formatted_logs = []
    for l in logs:
        if isinstance(l, dict):
            formatted_logs.append({
                "timestamp": l.get("timestamp", l.get("time", 0)),
                "type": l.get("type", l.get("action", l.get("job_type", "Backup"))),
                "target": l.get("target", l.get("app_name", l.get("name", "Sistema"))),
                "status": l.get("status", l.get("result", "success")),
                "duration": l.get("duration", l.get("time_taken", "0s"))
            })
        else:
            formatted_logs.append({
                "timestamp": getattr(l, "timestamp", 0),
                "type": getattr(l, "type", "Backup"),
                "target": getattr(l, "target", "Sistema"),
                "status": getattr(l, "status", "success"),
                "duration": getattr(l, "duration", "0s")
            })
    return formatted_logs

@router.delete("/logs")
def clear_execution_logs():
    return {"status": "success" if audit_service.clear_logs() else "failed"}

@router.websocket("/ws/progress")
async def websocket_progress_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)