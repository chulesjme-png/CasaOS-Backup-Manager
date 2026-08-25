import os
import time
import tarfile
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional, Union
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, Query
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

# --- ENDPOINTS DE SISTEMA ---

@router.get("/system/disks")
@router.get("/disks")
def get_disks():
    return disk_service.get_system_disks()

@router.get("/system/docker")
def get_docker_info():
    return {
        "status": "online",
        "containers_running": True,
        "engine": "Docker Engine"
    }

@router.get("/config", response_model=AppConfig)
def get_config():
    if not config_manager.config.selected_target_disk:
        try:
            disks = disk_service.get_system_disks()
            if disks:
                first_disk = disks[0].get("mountpoint")
                if first_disk:
                    config_manager.update_key("selected_target_disk", first_disk)
                    config_manager.save_config()
        except Exception as e:
            logger.warning(f"[Config] Error al establecer disco por defecto: {e}")
    return config_manager.config

@router.post("/config", response_model=AppConfig)
def update_config(payload: Dict[str, str]):
    for key, value in payload.items():
        config_manager.update_key(key, value)
    config_manager.save_config()
    if "schedule_frequency" in payload or "schedule_time" in payload:
        scheduler_service.reload_schedule()
    return config_manager.config

# --- PROGRAMACIÓN DE COPIAS (SCHEDULER) ---

@router.get("/schedule")
def get_schedule():
    return {
        "schedule_frequency": getattr(config_manager.config, "schedule_frequency", "daily"),
        "schedule_time": getattr(config_manager.config, "schedule_time", "03:00")
    }

@router.post("/schedule")
def update_schedule(req: ScheduleUpdateRequest):
    config_manager.update_key("schedule_frequency", req.schedule_frequency)
    config_manager.update_key("schedule_time", req.schedule_time)
    config_manager.save_config()
    scheduler_service.reload_schedule()
    return {"status": "ok", "message": "Programación actualizada correctamente"}

# --- BACKUPS Y RETENCIÓN ---

def _compress_directory(source_path: str, dest_file: str):
    with tarfile.open(dest_file, "w:gz") as tar:
        tar.add(source_path, arcname=os.path.basename(source_path))

def _prune_old_backups(folder_path: str, max_keep: int = 3):
    """Mantiene únicamente las 3 copias más recientes por aplicación."""
    try:
        if not os.path.exists(folder_path):
            return
        VALID_EXTS = (".tar.gz", ".tgz", ".zip", ".tar", ".gz")
        files = []
        for f in os.listdir(folder_path):
            if f.lower().endswith(VALID_EXTS):
                fp = os.path.join(folder_path, f)
                if os.path.isfile(fp):
                    files.append((fp, os.path.getmtime(fp)))

        # Ordenar por fecha de modificación (más recientes primero)
        files.sort(key=lambda x: x[1], reverse=True)

        # Eliminar las copias sobrantes (mayores al límite)
        if len(files) > max_keep:
            for old_fp, _ in files[max_keep:]:
                try:
                    os.remove(old_fp)
                    logger.info(f"[Prune] Rotación exitosa: eliminado backup antiguo {old_fp}")
                except Exception as err:
                    logger.error(f"[Prune] Error eliminando {old_fp}: {err}")
    except Exception as e:
        logger.error(f"[Prune] Error en proceso de rotación para {folder_path}: {e}")

async def task_run_app_backup(app_name: str, app_path: str, target_disk: str):
    start_time = time.perf_counter()
    
    await notification_service.send_notification(
        title=f"⏳ Inicio de Copia: {app_name}",
        message=f"Se ha iniciado la copia de seguridad de <b>{app_name}</b>.",
        status="info"
    )
    await ws_manager.broadcast({"job_id": f"backup_{app_name}", "percentage": 20, "message": f"Empaquetando {app_name}..."})

    backup_folder = os.path.join(target_disk, "Backups", "Apps", app_name)
    os.makedirs(backup_folder, exist_ok=True)

    timestamp_file = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{app_name}_backup_{timestamp_file}.tar.gz"
    full_output_path = os.path.join(backup_folder, output_filename)

    success = False
    try:
        if os.path.exists(app_path):
            await asyncio.to_thread(_compress_directory, app_path, full_output_path)
            success = True
        else:
            logger.error(f"[Backup] La ruta de la aplicación {app_path} no existe.")
    except Exception as e:
        logger.error(f"[Backup] Error en compresión: {e}")

    # Cálculo exacto de duración real final
    elapsed = round(time.perf_counter() - start_time, 2)
    duration_str = f"{elapsed}s"

    if success:
        _prune_old_backups(backup_folder, max_keep=3)
        await ws_manager.broadcast({"job_id": f"backup_{app_name}", "percentage": 100, "message": f"¡Copia de {app_name} finalizada!"})
        await notification_service.send_notification(
            title=f"✅ Copia Completada: {app_name}",
            message=f"Respaldo generado: {output_filename} ({duration_str})",
            status="success"
        )
        audit_service.log_execution("Backup", app_name, "success", duration_str, f"Archivo: {output_filename}")
    else:
        await ws_manager.broadcast({"job_id": f"backup_{app_name}", "percentage": 0, "message": f"Error respaldando {app_name}"})
        await notification_service.send_notification(
            title=f"❌ Error en Copia: {app_name}",
            message=f"No se pudo respaldar <b>{app_name}</b>.",
            status="error"
        )
        audit_service.log_execution("Backup", app_name, "failed", duration_str, "Error en empaquetado")

@router.post("/backups/run-app/{app_name}")
async def run_app_backup(
    app_name: str, 
    background_tasks: BackgroundTasks, 
    target_disk: Optional[str] = Query(None)
):
    # Si el cliente pasa target_disk por Query Parameter, guardarlo y fijarlo
    if target_disk:
        config_manager.update_key("selected_target_disk", target_disk)
        config_manager.save_config()
    else:
        target_disk = config_manager.config.selected_target_disk or "/media"

    apps = discovery_service.scan_apps()
    app = next((a for a in apps if a["name"] == app_name), None)
    if not app:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")

    background_tasks.add_task(task_run_app_backup, app["name"], app["path"], target_disk)
    return {"status": "started", "message": f"Copia de {app_name} iniciada."}

@router.get("/backups/list")
@router.get("/backups")
def list_available_backups():
    backups = []
    VALID_EXTS = (".tar.gz", ".tgz", ".zip", ".tar", ".gz")

    target_disk = config_manager.config.selected_target_disk or "/media"
    disk_uuid = os.path.basename(target_disk.rstrip(os.sep))
    apps_dir = os.path.join(target_disk, "Backups", "Apps")

    if os.path.exists(apps_dir):
        for app_folder in os.listdir(apps_dir):
            full_app_path = os.path.join(apps_dir, app_folder)
            if os.path.isdir(full_app_path):
                # Aplicar política de retención activa al listar
                _prune_old_backups(full_app_path, max_keep=3)
                
                for file in os.listdir(full_app_path):
                    if file.lower().endswith(VALID_EXTS):
                        file_path = os.path.join(full_app_path, file)
                        try:
                            stats = os.stat(file_path)
                            size_mb = round(stats.st_size / (1024 * 1024), 2)
                            ts_ms = int(stats.st_mtime * 1000)
                            dt = datetime.fromtimestamp(stats.st_mtime, timezone.utc)
                            size_display = f"{size_mb} MB" if size_mb >= 1.0 else f"{round(stats.st_size / 1024, 1)} KB"

                            backups.append({
                                "filename": file,
                                "name": file,
                                "title": file,
                                "path": file_path,
                                "file_path": file_path,
                                "disk": disk_uuid,
                                "disk_path": target_disk,
                                "size_mb": size_mb,
                                "size_str": size_display,
                                "size": size_display,
                                "created_at": dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "date": dt.strftime("%Y-%m-%d %H:%M:%S"),
                                "timestamp": ts_ms,
                                "app": app_folder,
                                "app_name": app_folder,
                                "status": "success",
                                "valid": True
                            })
                        except Exception:
                            continue

    backups.sort(key=lambda x: x["timestamp"], reverse=True)
    return backups

@router.get("/apps")
def get_apps():
    return discovery_service.scan_apps()

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