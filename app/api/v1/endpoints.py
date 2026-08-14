import os
import logging
from typing import List, Dict, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
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

# --- MODELOS PYDANTIC PARA VALIDACIÓN DE ENTRADA ---

class ScheduleUpdateRequest(BaseModel):
    schedule_frequency: str = Field(..., description="Frecuencia: 'daily', 'weekly', 'monthly'")
    schedule_time: str = Field(..., description="Hora en formato HH:MM (ej. '03:00')")

class RestoreRequest(BaseModel):
    backup_file: str = Field(..., description="Nombre o ruta del archivo de copia a restaurar")
    target_app: Optional[str] = Field("all", description="Nombre de la app específica o 'all' para todo el sistema")

class NotificationSettings(BaseModel):
    telegram_enabled: bool
    telegram_bot_token: Optional[str] = ""
    telegram_chat_id: Optional[str] = ""
    webhook_enabled: bool
    webhook_url: Optional[str] = ""


# --- ENDPOINTS DE CONFIGURACIÓN Y ESTADO ---

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


# --- ENDPOINTS MODAL: NOTIFICACIONES (TELEGRAM / WEBHOOK) ---

@router.post("/notifications/settings")
async def save_notification_settings(settings: NotificationSettings):
    """Guarda la configuración de notificaciones recibida desde la UI y la persiste en config.json."""
    try:
        data = settings.model_dump() if hasattr(settings, 'model_dump') else settings.dict()
        
        # 1. Guardar cada valor en el gestor de configuración
        for key, value in data.items():
            config_manager.update_key(key, value)
            
        # Forzar guardado persistente en disco (config.json) si el método existe
        if hasattr(config_manager, "save_config"):
            config_manager.save_config()
            
        # 2. Actualizar el servicio activo en memoria
        notification_service.update_config(config_manager.config)
        
        return {"status": "ok", "message": "Configuración guardada correctamente"}
    except Exception as e:
        logger.error(f"Error guardando notificaciones: {e}")
        raise HTTPException(status_code=500, detail=f"Error al guardar datos: {str(e)}")

@router.post("/notifications/test")
async def test_notification(settings: NotificationSettings):
    """Envía un mensaje de prueba a Telegram o Webhook."""
    try:
        success = await notification_service.send_test_message(
            token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            webhook_url=settings.webhook_url,
            telegram_enabled=settings.telegram_enabled,
            webhook_enabled=settings.webhook_enabled
        )
        if not success:
            raise HTTPException(status_code=400, detail="No se pudo enviar la prueba. Comprueba el Token/Chat ID.")
        return {"status": "ok", "message": "Notificación enviada"}
    except Exception as e:
        logger.error(f"Error enviando prueba de notificación: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    target_disk = config_manager.config.selected_target_disk
    if not target_disk or not os.path.exists(target_disk):
        return {"target_disk": target_disk, "backups": []}

    backups = []
    try:
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
    if not payload.backup_file:
        raise HTTPException(status_code=400, detail="Debe especificar un archivo de copia de seguridad.")
    
    app_target = payload.target_app or "all"
    await ws_manager.broadcast({
        "job_id": f"restore_{app_target}",
        "percentage": 15,
        "message": f"Iniciando restauración de {payload.backup_file}..."
    })

    try:
        success = await duplicati_service.restore_backup(payload.backup_file, app_target)
        if success:
            await ws_manager.broadcast({
                "job_id": f"restore_{app_target}",
                "percentage": 100,
                "message": f"¡Restauración de {payload.backup_file} completada con éxito!"
            })
            await notification_service.send_notification(
                title="Restauración Completada",
                message=f"Se ha restaurado correctamente el respaldo: <b>{payload.backup_file}</b>",
                status="success"
            )
            return {
                "status": "success",
                "message": f"Restauración completada con éxito para '{payload.backup_file}'."
            }
        else:
            await ws_manager.broadcast({
                "job_id": f"restore_{app_target}",
                "percentage": 0,
                "message": f"Error al restaurar {payload.backup_file}."
            })
            raise HTTPException(status_code=500, detail="Ocurrió un error al procesar el archivo de restauración.")
    except Exception as e:
        logger.error(f"Error en restauración: {e}")
        await ws_manager.broadcast({
            "job_id": f"restore_{app_target}",
            "percentage": 0,
            "message": f"Error: {str(e)}"
        })
        await notification_service.send_notification(
            title="Error en Restauración",
            message=f"Falló la restauración de <b>{payload.backup_file}</b>:\n<code>{str(e)}</code>",
            status="error"
        )
        raise HTTPException(status_code=500, detail=str(e))


# --- ENDPOINTS DE EJECUCIÓN MANUAL ---

@router.post("/backups/run-app/{app_name}")
async def run_app_backup(app_name: str):
    apps = discovery_service.scan_apps()
    app = next((a for a in apps if a["name"] == app_name), None)
    if not app:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")

    # 1. Notificar inicio mediante WebSocket
    await ws_manager.broadcast({
        "job_id": f"backup_{app_name}",
        "percentage": 15,
        "message": f"Iniciando resguardo de {app_name}..."
    })

    success = await duplicati_service.run_app_backup(app["name"], app["path"])
    
    if success:
        # 2. Notificar finalización mediante WebSocket
        await ws_manager.broadcast({
            "job_id": f"backup_{app_name}",
            "percentage": 100,
            "message": f"¡Backup de {app_name} completado con éxito!"
        })
        await notification_service.send_notification(
            title=f"Copia Exitosa: {app_name}",
            message=f"La copia de seguridad para la aplicación <b>{app_name}</b> se ha completado correctamente.",
            status="success"
        )
    else:
        # Notificar fallo por WebSocket
        await ws_manager.broadcast({
            "job_id": f"backup_{app_name}",
            "percentage": 0,
            "message": f"Error durante la copia de {app_name}."
        })
        await notification_service.send_notification(
            title=f"Error en Copia: {app_name}",
            message=f"Ocurrió un fallo al respaldar la aplicación <b>{app_name}</b>.",
            status="error"
        )

    return {"status": "success" if success else "failed", "app": app_name}

@router.post("/backups/run-full")
async def run_full_backup():
    # 1. Notificar inicio de Disaster Recovery mediante WebSocket
    await ws_manager.broadcast({
        "job_id": "backup_disaster_recovery",
        "percentage": 15,
        "message": "Iniciando Disaster Recovery completo..."
    })

    success = await duplicati_service.run_full_disaster_recovery()
    
    if success:
        # 2. Notificar finalización por WebSocket
        await ws_manager.broadcast({
            "job_id": "backup_disaster_recovery",
            "percentage": 100,
            "message": "¡Disaster Recovery completado con éxito!"
        })
        await notification_service.send_notification(
            title="Disaster Recovery Completo",
            message="El respaldo integral del sistema CasaOS y /DATA/AppData ha finalizado con éxito.",
            status="success"
        )
    else:
        await ws_manager.broadcast({
            "job_id": "backup_disaster_recovery",
            "percentage": 0,
            "message": "Error durante la ejecución del Disaster Recovery."
        })
        await notification_service.send_notification(
            title="Error en Disaster Recovery",
            message="Falló la copia completa del sistema CasaOS.",
            status="error"
        )

    return {"status": "success" if success else "failed"}


# --- ENDPOINTS HISTORIAL DE EJECUCIÓN (AUDIT LOG) ---

@router.get("/logs")
def get_execution_logs():
    return audit_service.get_logs(limit=50)

@router.delete("/logs")
def clear_execution_logs():
    success = audit_service.clear_logs()
    return {"status": "success" if success else "failed"}


# --- ENDPOINT WEBSOCKET PARA PROGRESO EN TIEMPO REAL ---

@router.websocket("/ws/progress")
async def websocket_progress_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)