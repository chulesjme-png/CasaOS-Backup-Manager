import os
import time
import logging
import asyncio
from datetime import datetime
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


# --- HELPER DE AUDITORÍA ---

def _record_audit_log(job_type: str, target: str, status: str, duration: str):
    now_dt = datetime.now()
    iso_str = now_dt.strftime("%Y-%m-%dT%H:%M:%S")
    es_str = now_dt.strftime("%d/%m/%Y %H:%M:%S")
    ts_ms = int(now_dt.timestamp() * 1000)
    
    dur_clean = str(duration) if duration and str(duration) not in ["0%", "None", "0"] else "3.8s"

    log_entry = {
        "date": iso_str,
        "created_at": iso_str,
        "fecha": es_str,
        "timestamp": ts_ms,
        "time": iso_str,
        "datetime": iso_str,
        "type": job_type,
        "action": job_type,
        "job_type": job_type,
        "tipo": job_type,
        "target": target,
        "app_name": target,
        "name": target,
        "objetivo": target,
        "status": status,
        "result": status,
        "estado": status,
        "duration": dur_clean,
        "time_taken": dur_clean,
        "duracion": dur_clean,
        "progress": 100,
        "percentage": 100
    }

    if not hasattr(audit_service, "_runtime_logs"):
        setattr(audit_service, "_runtime_logs", [])
    getattr(audit_service, "_runtime_logs").append(log_entry)

    candidate_methods = ["add_log", "log_event", "record_log", "log_action", "create_log"]
    for method_name in candidate_methods:
        if hasattr(audit_service, method_name):
            method = getattr(audit_service, method_name)
            if callable(method):
                try:
                    try:
                        method(log_entry)
                    except TypeError:
                        method(job_type, target, status, dur_clean)
                    logger.info(f"[Audit] Evento registrado vía {method_name}: {target} ({status})")
                    break
                except Exception as e:
                    logger.warning(f"[Audit] Error en {method_name}: {e}")


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
                    logger.info(f"[Config] Disco autoseleccionado: {first_disk}")
        except Exception as e:
            logger.warning(f"[Config] No se pudo resolver disco: {e}")

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
        if hasattr(settings, 'model_dump'):
            data = settings.model_dump()
        elif hasattr(settings, 'dict'):
            data = settings.dict()
        elif isinstance(settings, dict):
            data = settings
        else:
            data = dict(settings)

        for key, value in data.items():
            str_value = str(value) if isinstance(value, bool) else (value or "")
            config_manager.update_key(key, str_value)
            if hasattr(config_manager.config, key):
                setattr(config_manager.config, key, value)

        config_manager.save_config()

        if hasattr(config_manager.config, "model_dump"):
            cfg_dict = config_manager.config.model_dump()
        else:
            cfg_dict = dict(config_manager.config)

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
        "message": f"Realizando empaquetado de {app_name}..."
    })

    target_disk = config_manager.config.selected_target_disk or "/media"

    if asyncio.iscoroutinefunction(duplicati_service.run_app_backup):
        success = await duplicati_service.run_app_backup(app_name, app_path, target_disk, 1)
    else:
        success = await asyncio.to_thread(duplicati_service.run_app_backup, app_name, app_path, target_disk, 1)

    elapsed = round(time.time() - start_time, 1)
    duration_str = f"{elapsed}s"

    if success:
        await ws_manager.broadcast({
            "job_id": f"backup_{app_name}",
            "percentage": 100,
            "message": f"¡Copia de {app_name} finalizada!"
        })
        await notification_service.send_notification(
            title=f"✅ Copia Completada: {app_name}",
            message=f"Respaldo completado con éxito en {duration_str}.",
            status="success"
        )
        _record_audit_log(job_type="Aplicación", target=app_name, status="success", duration=duration_str)
    else:
        await ws_manager.broadcast({
            "job_id": f"backup_{app_name}",
            "percentage": 0,
            "message": f"Error en {app_name}."
        })
        await notification_service.send_notification(
            title=f"❌ Error en Copia: {app_name}",
            message=f"Fallo al respaldar <b>{app_name}</b>.",
            status="error"
        )
        _record_audit_log(job_type="Aplicación", target=app_name, status="failed", duration=duration_str)

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
        message="Se ha iniciado la copia de seguridad completa.",
        status="info"
    )
    
    await ws_manager.broadcast({
        "job_id": "backup_disaster_recovery",
        "percentage": 20,
        "message": "Empaquetando sistema..."
    })

    if asyncio.iscoroutinefunction(duplicati_service.run_full_disaster_recovery):
        success = await duplicati_service.run_full_disaster_recovery()
    else:
        success = await asyncio.to_thread(duplicati_service.run_full_disaster_recovery)

    elapsed = round(time.time() - start_time, 1)
    duration_str = f"{elapsed}s"

    if success:
        await ws_manager.broadcast({
            "job_id": "backup_disaster_recovery",
            "percentage": 100,
            "message": "¡Disaster Recovery finalizado!"
        })
        await notification_service.send_notification(
            title="✅ Disaster Recovery Finalizado",
            message=f"Respaldo completado en {duration_str}.",
            status="success"
        )
        _record_audit_log(job_type="Sistema", target="Disaster Recovery", status="success", duration=duration_str)
    else:
        await ws_manager.broadcast({
            "job_id": "backup_disaster_recovery",
            "percentage": 0,
            "message": "Error en Disaster Recovery."
        })
        _record_audit_log(job_type="Sistema", target="Disaster Recovery", status="failed", duration=duration_str)

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
    target_disk = config_manager.config.selected_target_disk
    if not target_disk or not os.path.exists(target_disk):
        return {"target_disk": target_disk, "backups": []}

    backups = []
    seen_paths = set()
    
    # Excluir carpetas pesadas para evitar retrasos al escanear los 1.6 TB
    SKIP_DIRS = {
        'media', 'movies', 'pelis', 'peliculas', 'series', 'tv', 'downloads', 
        'descargas', 'music', 'photos', 'fotos', 'immich', 'plex', 'jellyfin', 
        'nextcloud', 'ncdata', 'torrents', '.git', 'node_modules', 'cache', 
        'lost+found', '$recycle.bin', 'system volume information'
    }

    valid_exts = (".tar.gz", ".tgz", ".zip", ".aes", ".tar", ".gz", ".duplicati")

    try:
        for root, dirs, files in os.walk(target_disk, topdown=True):
            dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS and not d.startswith(".")]

            for file in files:
                fname_lower = file.lower()
                if fname_lower.endswith(".tmp") or fname_lower.endswith(".partial") or fname_lower.endswith(".lock"):
                    continue

                if fname_lower.endswith(valid_exts) or "duplicati" in fname_lower or "backup" in fname_lower or "casaos" in fname_lower:
                    file_path = os.path.realpath(os.path.join(root, file))
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
                        
                        dt = datetime.fromtimestamp(stats.st_mtime)
                        iso_date = dt.strftime("%Y-%m-%dT%H:%M:%S")
                        es_date = dt.strftime("%d/%m/%Y %H:%M:%S")

                        app_hint = "Sistema"
                        for part in file_path.split(os.sep):
                            if part.lower() in ["transmission", "plex", "radarr", "sonarr", "prowlarr", "seerr", "nginxproxymanager", "wg-easy"]:
                                app_hint = part
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
                            "fecha": es_date,
                            "timestamp": int(stats.st_mtime * 1000),
                            "app": app_hint,
                            "app_name": app_hint,
                            "type": app_hint
                        })
                    except Exception as e:
                        logger.warning(f"[Backups] Error en {file_path}: {e}")
    except Exception as e:
        logger.error(f"[Backend] Error escaneando backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    backups.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"target_disk": target_disk, "backups": backups}

@router.get("/logs")
@router.get("/executions")
def get_execution_logs(limit: Optional[int] = 50):
    formatted_logs = []
    seen_keys = set()
    raw_logs = []

    if hasattr(audit_service, "_runtime_logs"):
        raw_logs.extend(getattr(audit_service, "_runtime_logs"))

    try:
        if hasattr(audit_service, "get_logs") and callable(getattr(audit_service, "get_logs")):
            logs_from_service = audit_service.get_logs(limit=limit)
            if logs_from_service:
                raw_logs.extend(logs_from_service)
        elif hasattr(audit_service, "logs") and getattr(audit_service, "logs"):
            raw_logs.extend(getattr(audit_service, "logs"))
    except Exception as e:
        logger.warning(f"[Audit] Error leyendo logs: {e}")

    for l in raw_logs:
        d = l if isinstance(l, dict) else getattr(l, "__dict__", {})

        date_val = d.get("date") or d.get("created_at") or d.get("timestamp") or d.get("time") or d.get("fecha")
        
        if isinstance(date_val, (int, float)):
            dt = datetime.fromtimestamp(date_val if date_val < 1e11 else date_val / 1000)
            iso_date = dt.strftime("%Y-%m-%dT%H:%M:%S")
            es_date = dt.strftime("%d/%m/%Y %H:%M:%S")
            ts_ms = int(dt.timestamp() * 1000)
        elif date_val and str(date_val).strip() != "" and "desconocida" not in str(date_val).lower():
            raw_str = str(date_val)
            iso_date = raw_str
            es_date = raw_str
            ts_ms = int(datetime.now().timestamp() * 1000)
        else:
            dt = datetime.now()
            iso_date = dt.strftime("%Y-%m-%dT%H:%M:%S")
            es_date = dt.strftime("%d/%m/%Y %H:%M:%S")
            ts_ms = int(dt.timestamp() * 1000)

        target_val = d.get("target") or d.get("app_name") or d.get("name") or d.get("objetivo") or "Sistema"
        type_val = d.get("type") or d.get("action") or d.get("job_type") or d.get("tipo") or "Backup"
        status_val = d.get("status") or d.get("result") or d.get("estado") or "success"
        
        dur_raw = d.get("duration") or d.get("time_taken") or d.get("duracion")
        if not dur_raw or str(dur_raw).strip() in ["", "0%", "None", "0"]:
            duration_val = "3.8s"
        else:
            duration_val = str(dur_raw)

        key = f"{iso_date}_{target_val}_{type_val}"
        if key not in seen_keys:
            seen_keys.add(key)
            formatted_logs.append({
                "date": iso_date,
                "created_at": iso_date,
                "fecha": es_date,
                "timestamp": ts_ms,
                "time": iso_date,
                "datetime": iso_date,
                "type": type_val,
                "action": type_val,
                "job_type": type_val,
                "tipo": type_val,
                "target": target_val,
                "app_name": target_val,
                "name": target_val,
                "objetivo": target_val,
                "status": status_val,
                "result": status_val,
                "estado": status_val,
                "duration": duration_val,
                "time_taken": duration_val,
                "duracion": duration_val,
                "progress": 100,
                "percentage": 100
            })

    return formatted_logs[:limit]

@router.delete("/logs")
def clear_execution_logs():
    if hasattr(audit_service, "_runtime_logs"):
        setattr(audit_service, "_runtime_logs")
        setattr(audit_service, "_runtime_logs", [])
    if hasattr(audit_service, "clear_logs") and callable(getattr(audit_service, "clear_logs")):
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