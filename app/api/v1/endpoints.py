import os
import time
import tarfile
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
from app.services.scheduler_service import scheduler_service
from app.services.audit_service import audit_service
from app.services.notification_service import notification_service

logger = logging.getLogger("casaos-backup")
router = APIRouter()

class ScheduleUpdateRequest(BaseModel):
    schedule_frequency: str = Field(...)
    schedule_time: str = Field(...)

class NotificationSettings(BaseModel):
    telegram_enabled: bool
    telegram_bot_token: Optional[str] = ""
    telegram_chat_id: Optional[str] = ""
    webhook_enabled: bool
    webhook_url: Optional[str] = ""

@router.get("/config", response_model=AppConfig)
def get_config():
    if not config_manager.config.selected_target_disk:
        try:
            disks = disk_service.get_system_disks()
            if disks:
                first_disk = disks[0].get("mountpoint") or disks[0].get("path")
                if first_disk:
                    config_manager.update_key("selected_target_disk", first_disk)
        except Exception as e:
            logger.warning(f"[Config] Error al seleccionar disco: {e}")
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

@router.post("/notifications/settings")
async def save_notification_settings(settings: Union[NotificationSettings, Dict]):
    data = settings.model_dump() if hasattr(settings, 'model_dump') else dict(settings)
    for key, value in data.items():
        config_manager.update_key(key, str(value) if isinstance(value, bool) else (value or ""))
    config_manager.save_config()
    return {"status": "ok", "message": "Configuración guardada"}

def _compress_directory(source_path: str, dest_file: str):
    with tarfile.open(dest_file, "w:gz") as tar:
        tar.add(source_path, arcname=os.path.basename(source_path))

async def task_run_app_backup(app_name: str, app_path: str):
    start_time = time.time()
    await notification_service.send_notification(
        title=f"⏳ Inicio de Copia: {app_name}",
        message=f"Se ha iniciado la copia de seguridad de <b>{app_name}</b>.",
        status="info"
    )

    await ws_manager.broadcast({"job_id": f"backup_{app_name}", "percentage": 20, "message": f"Empaquetando {app_name}..."})

    target_disk = config_manager.config.selected_target_disk or "/media"
    backup_folder = os.path.join(target_disk, "Backups", "Apps", app_name)
    os.makedirs(backup_folder, exist_ok=True)

    timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{app_name}_backup_{timestamp_file}.tar.gz"
    full_output_path = os.path.join(backup_folder, output_filename)

    try:
        if os.path.exists(app_path):
            await asyncio.to_thread(_compress_directory, app_path, full_output_path)
            success = True
        else:
            logger.error(f"[Backup] La ruta {app_path} no existe.")
            success = False
    except Exception as e:
        logger.error(f"[Backup] Error creando comprimido: {e}")
        success = False

    elapsed = round(time.time() - start_time, 1)

    if success:
        await ws_manager.broadcast({"job_id": f"backup_{app_name}", "percentage": 100, "message": f"¡Copia de {app_name} finalizada!"})
        await notification_service.send_notification(
            title=f"✅ Copia Completada: {app_name}",
            message=f"Respaldo generado en: {output_filename} ({elapsed}s)",
            status="success"
        )
        audit_service.log_execution("Backup", app_name, "success", elapsed, f"Archivo generado: {output_filename}")
    else:
        await ws_manager.broadcast({"job_id": f"backup_{app_name}", "percentage": 0, "message": f"Error respaldando {app_name}"})
        await notification_service.send_notification(
            title=f"❌ Error en Copia: {app_name}",
            message=f"No se pudo respaldar <b>{app_name}</b>.",
            status="error"
        )
        audit_service.log_execution("Backup", app_name, "failed", elapsed, "Error en el empaquetado")

@router.post("/backups/run-app/{app_name}")
async def run_app_backup(app_name: str, background_tasks: BackgroundTasks):
    apps = discovery_service.scan_apps()
    app = next((a for a in apps if a["name"] == app_name), None)
    if not app:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")

    background_tasks.add_task(task_run_app_backup, app["name"], app["path"])
    return {"status": "started", "message": f"Copia de {app_name} iniciada."}

@router.get("/backups/list")
def list_available_backups():
    backups = []
    seen = set()
    VALID_EXTS = (".tar.gz", ".tgz", ".zip", ".aes", ".tar", ".gz")

    target_disk = config_manager.config.selected_target_disk or "/media"
    possible_roots = [
        os.path.join(target_disk, "Backups"),
        target_disk,
        "/media",
        "/mnt"
    ]

    search_dirs = [d for d in possible_roots if d and os.path.exists(d)]

    for s_dir in search_dirs:
        try:
            for root, _, files in os.walk(s_dir, followlinks=True):
                for file in files:
                    if file.lower().endswith(VALID_EXTS):
                        file_path = os.path.join(root, file)
                        if file_path in seen:
                            continue
                        seen.add(file_path)

                        try:
                            stats = os.stat(file_path)
                            size_mb = round(stats.st_size / (1024 * 1024), 2)
                            ts_ms = int(stats.st_mtime * 1000)
                            dt = datetime.fromtimestamp(stats.st_mtime, timezone.utc)

                            path_parts = file_path.split(os.sep)
                            app_hint = "Sistema"
                            for part in path_parts:
                                if part.lower() in ["transmission", "plex", "radarr", "sonarr", "prowlarr", "seerr", "nginxproxymanager", "wg-easy"]:
                                    app_hint = part
                                    break

                            size_display = f"{size_mb} MB" if size_mb >= 1.0 else f"{round(stats.st_size / 1024, 1)} KB"

                            backups.append({
                                "filename": file,
                                "name": file,
                                "path": file_path,
                                "file_path": file_path,
                                "disk": target_disk,
                                "disk_path": target_disk,
                                "target_disk": target_disk,
                                "mountpoint": target_disk,
                                "size_mb": size_mb,
                                "size_str": size_display,
                                "size": size_display,
                                "created_at": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "date": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "fecha": dt.strftime("%Y-%m-%d %H:%M:%S"),
                                "timestamp": ts_ms,
                                "app": app_hint,
                                "app_name": app_hint,
                                "target": app_hint
                            })
                        except Exception:
                            pass
        except Exception as e:
            logger.error(f"[Backups] Error escaneando {s_dir}: {e}")

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