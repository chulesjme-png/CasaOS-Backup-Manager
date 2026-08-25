import os
import time
import logging
import asyncio
from datetime import datetime, timezone
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
    if not config_manager.config.selected_target_disk:
        try:
            disks = disk_service.get_system_disks()
            if disks and len(disks) > 0:
                first_disk = disks[0].get("mountpoint") or disks[0].get("path")
                if first_disk:
                    config_manager.update_key("selected_target_disk", first_disk)
        except Exception as e:
            logger.warning(f"[Config] Error seleccionando disco: {e}")

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

# --- NOTIFICACIONES ---

@router.post("/notifications/settings")
async def save_notification_settings(settings: Union[NotificationSettings, Dict]):
    try:
        data = settings.model_dump() if hasattr(settings, 'model_dump') else dict(settings)
        for key, value in data.items():
            str_value = str(value) if isinstance(value, bool) else (value or "")
            config_manager.update_key(key, str_value)
            if hasattr(config_manager.config, key):
                setattr(config_manager.config, key, value)

        config_manager.save_config()
        cfg_dict = config_manager.config.model_dump() if hasattr(config_manager.config, "model_dump") else dict(config_manager.config)
        
        try:
            notification_service.update_config(cfg_dict)
        except Exception:
            pass
        return {"status": "ok", "message": "Configuración guardada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            raise HTTPException(status_code=400, detail="No se pudo entregar el mensaje.")
        return {"status": "ok", "message": "Notificación enviada con éxito."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- TAREAS DE RESPALDO ---

async def task_run_app_backup(app_name: str, app_path: str):
    start_time = time.time()
    await notification_service.send_notification(
        title=f"⏳ Inicio de Copia: {app_name}",
        message=f"Se ha iniciado la copia de seguridad de <b>{app_name}</b>.",
        status="info"
    )
    
    await ws_manager.broadcast({
        "job_id": f"backup_{app_name}",
        "percentage": 25,
        "message": f"Empaquetando datos de {app_name}..."
    })

    target_disk = config_manager.config.selected_target_disk or "/media"

    if asyncio.iscoroutinefunction(duplicati_service.run_app_backup):
        success = await duplicati_service.run_app_backup(app_name, app_path, target_disk, 1)
    else:
        success = await asyncio.to_thread(duplicati_service.run_app_backup, app_name, app_path, target_disk, 1)

    elapsed = round(time.time() - start_time, 1)
    duration_seconds = max(elapsed, 0.5)

    if success:
        await ws_manager.broadcast({
            "job_id": f"backup_{app_name}",
            "percentage": 100,
            "message": f"¡Copia de {app_name} finalizada!"
        })
        await notification_service.send_notification(
            title=f"✅ Copia Completada: {app_name}",
            message=f"Respaldo completado con éxito en {duration_seconds}s.",
            status="success"
        )
        audit_service.log_execution(
            job_type="Backup",
            target_name=app_name,
            status="success",
            duration_seconds=duration_seconds,
            message=f"Copia de {app_name} realizada correctamente"
        )
    else:
        await ws_manager.broadcast({
            "job_id": f"backup_{app_name}",
            "percentage": 0,
            "message": f"Error en respaldo de {app_name}."
        })
        await notification_service.send_notification(
            title=f"❌ Error en Copia: {app_name}",
            message=f"Fallo al respaldar <b>{app_name}</b>.",
            status="error"
        )
        audit_service.log_execution(
            job_type="Backup",
            target_name=app_name,
            status="failed",
            duration_seconds=duration_seconds,
            message=f"Fallo al respaldar {app_name}"
        )

@router.post("/backups/run-app/{app_name}")
async def run_app_backup(app_name: str, background_tasks: BackgroundTasks):
    apps = discovery_service.scan_apps()
    app = next((a for a in apps if a["name"] == app_name), None)
    if not app:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")

    background_tasks.add_task(task_run_app_backup, app["name"], app["path"])
    return {"status": "started", "message": f"Copia de {app_name} iniciada."}

async def task_run_full_backup():
    start_time = time.time()
    await notification_service.send_notification(
        title="⏳ Inicio: Disaster Recovery",
        message="Se ha iniciado la copia de seguridad completa del sistema.",
        status="info"
    )
    
    await ws_manager.broadcast({
        "job_id": "backup_disaster_recovery",
        "percentage": 20,
        "message": "Empaquetando el sistema completo..."
    })

    if asyncio.iscoroutinefunction(duplicati_service.run_full_disaster_recovery):
        success = await duplicati_service.run_full_disaster_recovery()
    else:
        success = await asyncio.to_thread(duplicati_service.run_full_disaster_recovery)

    elapsed = round(time.time() - start_time, 1)
    duration_seconds = max(elapsed, 0.5)

    if success:
        await ws_manager.broadcast({
            "job_id": "backup_disaster_recovery",
            "percentage": 100,
            "message": "¡Disaster Recovery finalizado!"
        })
        await notification_service.send_notification(
            title="✅ Disaster Recovery Finalizado",
            message=f"Respaldo completado en {duration_seconds}s.",
            status="success"
        )
        audit_service.log_execution(
            job_type="Backup",
            target_name="Sistema Completo",
            status="success",
            duration_seconds=duration_seconds,
            message="Disaster Recovery completado"
        )
    else:
        await ws_manager.broadcast({
            "job_id": "backup_disaster_recovery",
            "percentage": 0,
            "message": "Error en Disaster Recovery."
        })
        audit_service.log_execution(
            job_type="Backup",
            target_name="Sistema Completo",
            status="failed",
            duration_seconds=duration_seconds,
            message="Error en Disaster Recovery"
        )

@router.post("/backups/run-full")
async def run_full_backup(background_tasks: BackgroundTasks):
    background_tasks.add_task(task_run_full_backup)
    return {"status": "started", "message": "Disaster recovery iniciado."}

# --- PROGRAMACIÓN, HISTORIAL Y LISTADO DE COPIAS ---

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
    search_paths = []
    target_disk = config_manager.config.selected_target_disk
    
    if target_disk and os.path.exists(target_disk):
        search_paths.append(target_disk)

    for fallback in ["/media", "/mnt", "/DATA"]:
        if os.path.exists(fallback) and fallback not in search_paths:
            search_paths.append(fallback)

    backups = []
    seen_paths = set()
    SKIP_DIRS = {'lost+found', '$recycle.bin', 'node_modules', '.git'}
    VALID_EXTS = (
        ".tar.gz", ".tgz", ".zip", ".aes", ".tar", ".gz", 
        ".duplicati", ".dblock", ".dindex", ".dlist", ".sqlite", ".bak", ".backup"
    )

    for base_path in search_paths:
        try:
            for root, dirs, files in os.walk(base_path, topdown=True, followlinks=True):
                dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]

                for file in files:
                    fname_lower = file.lower()
                    if fname_lower.endswith((".tmp", ".partial", ".lock")):
                        continue

                    is_backup = (
                        fname_lower.endswith(VALID_EXTS) or 
                        any(k in fname_lower for k in ["duplicati", "backup", "casaos", "disaster", "transmission"])
                    )

                    if is_backup:
                        file_path = os.path.join(root, file)
                        if file_path in seen_paths:
                            continue
                        seen_paths.add(file_path)

                        try:
                            stats = os.stat(file_path)
                            size_bytes = stats.st_size
                            if size_bytes == 0:
                                continue

                            size_mb = round(size_bytes / (1024 * 1024), 2)
                            size_str = f"{size_mb} MB" if size_mb >= 0.1 else f"{round(size_bytes / 1024, 2)} KB"
                            
                            dt = datetime.fromtimestamp(stats.st_mtime, timezone.utc)
                            iso_date = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                            display_date = dt.strftime("%Y-%m-%d %H:%M:%S")

                            app_hint = "Sistema"
                            parts = file_path.split(os.sep)
                            for part in parts:
                                p_lower = part.lower()
                                if p_lower in ["transmission", "plex", "radarr", "sonarr", "prowlarr", "seerr", "nginxproxymanager", "wg-easy", "jellyfin", "nextcloud", "immich"]:
                                    app_hint = part
                                    break
                            
                            if app_hint == "Sistema":
                                for known in ["transmission", "plex", "radarr", "sonarr", "prowlarr", "seerr", "nginxproxymanager", "wg-easy", "jellyfin", "nextcloud", "immich"]:
                                    if known in fname_lower:
                                        app_hint = known
                                        break

                            backups.append({
                                "filename": file,
                                "name": file,
                                "path": file_path,
                                "file_path": file_path,
                                "size_mb": size_mb,
                                "size_str": size_str,
                                "size": size_str,
                                "created_at": iso_date,
                                "date": iso_date,
                                "fecha": display_date,
                                "timestamp": int(stats.st_mtime * 1000),
                                "app": app_hint,
                                "app_name": app_hint,
                                "type": app_hint
                            })
                        except Exception as e:
                            logger.warning(f"[Backups] Error al inspeccionar {file_path}: {e}")
        except Exception as e:
            logger.error(f"[Backend] Error escaneando {base_path}: {e}")

    backups.sort(key=lambda x: x["timestamp"], reverse=True)
    return backups

@router.get("/logs")
@router.get("/executions")
def get_execution_logs(limit: Optional[int] = 50):
    return audit_service.get_logs(limit=limit)

@router.delete("/logs")
def clear_execution_logs():
    audit_service.clear_logs()
    return {"status": "success"}

@router.websocket("/ws/progress")
async def websocket_progress_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)