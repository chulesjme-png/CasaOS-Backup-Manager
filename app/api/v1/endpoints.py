import os
import logging
import asyncio
from typing import List, Dict, Optional
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

# --- MODELOS PYDANTIC ---

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


# --- NOTIFICACIONES (CORREGIDO) ---

@router.post("/notifications/settings")
async def save_notification_settings(settings: NotificationSettings):
    """Guarda en memoria y escribe permanentemente en disco la configuración."""
    try:
        data = settings.model_dump() if hasattr(settings, 'model_dump') else settings.dict()
        
        # 1. Actualizar valores en config_manager
        for key, value in data.items():
            if hasattr(config_manager.config, key):
                setattr(config_manager.config, key, value)
            config_manager.update_key(key, str(value) if isinstance(value, bool) else (value or ""))

        # 2. Guardar en disco (Pasando explícitamente el diccionario para evitar error .get)
        try:
            config_manager.save_config()
        except TypeError:
            config_data = config_manager.config.model_dump() if hasattr(config_manager.config, 'model_dump') else config_manager.config.dict()
            config_manager.save_config(config_data)

        # 3. Refrescar la configuración en el servicio de notificaciones
        notification_service.update_config(config_manager.config)
        
        logger.info("Configuración de notificaciones guardada exitosamente.")
        return {"status": "ok", "message": "Configuración guardada correctamente"}
    except Exception as e:
        logger.error(f"Error guardando notificaciones: {e}")
        raise HTTPException(status_code=500, detail=f"Error al guardar datos: {str(e)}")

@router.post("/notifications/test")
async def test_notification(settings: NotificationSettings):
    """Envía un mensaje de prueba utilizando los datos enviados."""
    try:
        success = await notification_service.send_test_message(
            token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            webhook_url=settings.webhook_url,
            telegram_enabled=settings.telegram_enabled,
            webhook_enabled=settings.webhook_enabled
        )
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo entregar el mensaje de prueba. Revisa las credenciales.")
        return {"status": "ok", "message": "Notificación de prueba enviada con éxito."}
    except Exception as e:
        logger.error(f"Error en test de notificación: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- TAREAS DE RESPALDO (NO BLOQUEANTES) ---

async def task_run_app_backup(app_name: str, app_path: str):
    """Ejecuta la copia en un hilo separado para NO congelar la UI ni Telegram."""
    # Notificación de INICIO
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

    # Ejecutar proceso en hilo secundario no bloqueante
    if asyncio.iscoroutinefunction(duplicati_service.run_app_backup):
        success = await duplicati_service.run_app_backup(app_name, app_path)
    else:
        success = await asyncio.to_thread(duplicati_service.run_app_backup, app_name, app_path)

    # Notificación y WS de FIN
    if success:
        await ws_manager.broadcast({
            "job_id": f"backup_{app_name}",
            "percentage": 100,
            "message": f"¡Copia de {app_name} finalizada!"
        })
        await notification_service.send_notification(
            title=f"✅ Copia Completada: {app_name}",
            message=f"La aplicación <b>{app_name}</b> se ha respaldado con éxito en el disco.",
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
            message=f"Ocurrió un fallo al respaldar la aplicación <b>{app_name}</b>.",
            status="error"
        )

@router.post("/backups/run-app/{app_name}")
async def run_app_backup(app_name: str, background_tasks: BackgroundTasks):
    apps = discovery_service.scan_apps()
    app = next((a for a in apps if a["name"] == app_name), None)
    if not app:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")

    # Responder de inmediato al navegador y delegar la copia a segundo plano
    background_tasks.add_task(task_run_app_backup, app["name"], app["path"])
    
    return {"status": "started", "message": f"Copia de {app_name} iniciada en segundo plano."}

async def task_run_full_backup():
    await notification_service.send_notification(
        title="⏳ Inicio: Disaster Recovery",
        message="Se ha iniciado la copia de seguridad completa del sistema (Raspberry Pi).",
        status="info"
    )
    
    await ws_manager.broadcast({
        "job_id": "backup_disaster_recovery",
        "percentage": 20,
        "message": "Empaquetando datos y configuraciones del sistema..."
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
    if not target_disk or not os.path.exists(target_disk):
        return {"target_disk": target_disk, "backups": []}

    backups = []
    try:
        for root, _, files in os.walk(target_disk):
            for file in files:
                if file.endswith(".tar.gz") or file.endswith(".zip"):
                    file_path = os.path.join(root, file)
                    stats = os.stat(file_path)
                    backups.append({
                        "filename": os.path.relpath(file_path, target_disk),
                        "path": file_path,
                        "size_mb": round(stats.st_size / (1024 * 1024), 2),
                        "created_at": stats.st_mtime
                    })
    except Exception as e:
        logger.error(f"Error escaneando backups: {e}")

    return {"target_disk": target_disk, "backups": backups}

@router.get("/logs")
def get_execution_logs():
    return audit_service.get_logs(limit=50)

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