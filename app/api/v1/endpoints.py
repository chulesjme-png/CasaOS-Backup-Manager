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


# --- HELPER DE AUDITORÍA Y HISTORIAL ---

def _record_audit_log(job_type: str, target: str, status: str, duration: str):
    """
    Registra de forma segura un evento de backup en audit_service.
    """
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    log_entry = {
        "timestamp": now_str,
        "type": job_type,
        "target": target,
        "status": status,
        "duration": duration
    }
    
    recorded = False
    candidate_methods = ["add_log", "log_event", "record_log", "log_action", "create_log", "add_entry"]

    for method_name in candidate_methods:
        if hasattr(audit_service, method_name):
            method = getattr(audit_service, method_name)
            if callable(method):
                try:
                    try:
                        method(log_entry)
                    except TypeError:
                        method(job_type, target, status, duration)
                    recorded = True
                    logger.info(f"[Audit] Evento registrado vía {method_name}: {target} ({status})")
                    break
                except Exception as e:
                    logger.warning(f"[Audit] Error al ejecutar {method_name}: {e}")

    if not recorded and hasattr(audit_service, "logs") and isinstance(audit_service.logs, list):
        audit_service.logs.append(log_entry)
        recorded = True
        logger.info(f"[Audit] Evento añadido directamente a audit_service.logs: {target}")

    if not recorded:
        if not hasattr(audit_service, "_runtime_logs"):
            setattr(audit_service, "_runtime_logs", [])
        getattr(audit_service, "_runtime_logs").append(log_entry)
        logger.info(f"[Audit] Evento guardado en _runtime_logs del sistema: {target}")


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
        elif hasattr(config_manager.config, "dict"):
            cfg_dict = config_manager.config.dict()
        else:
            cfg_dict = dict(config_manager.config)

        try:
            notification_service.update_config(cfg_dict)
        except Exception:
            notification_service.update_config(config_manager.config)
        
        logger.info("[Backend] Configuración de notificaciones guardada con éxito.")
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


# --- TAREAS DE RESPALDO (ASÍNCRONAS CON HISTORIAL) ---

async def task_run_app_backup(app_name: str, app_path: str):
    start_time = time.time()
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
            message=f"La aplicación <b>{app_name}</b> se ha respaldado con éxito en {duration_str}.",
            status="success"
        )
        _record_audit_log(job_type="Backup App", target=app_name, status="success", duration=duration_str)
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
        _record_audit_log(job_type="Backup App", target=app_name, status="failed", duration=duration_str)

@router.post("/backups/run-app/{app_name}")
async def run_app_backup(app_name: str, background_tasks: BackgroundTasks):
    apps = discovery_service.scan_apps()
    app = next((a for a in apps if a["name"] == app_name), None)
    if not app:
        raise HTTPException(status_code=404, detail="Aplicación no encontrada")

    background_tasks.add_task(task_run_app_backup, app["name"], app["path"])
    return {"status": "started", "message": f"Copia de {app_name} iniciada en segundo plano."}

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
        "message": "Empaquetando datos y configuraciones..."
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
            message=f"El respaldo integral del sistema se completó correctamente en {duration_str}.",
            status="success"
        )
        _record_audit_log(job_type="Disaster Recovery", target="Sistema Completo", status="success", duration=duration_str)
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
        _record_audit_log(job_type="Disaster Recovery", target="Sistema Completo", status="failed", duration=duration_str)

@router.post("/backups/run-full")
async def run_full_backup(background_tasks: BackgroundTasks):
    background_tasks.add_task(task_run_full_backup)
    return {"status": "started", "message": "Disaster recovery iniciado en segundo plano."}


# --- RESTO DE ENDPOINTS & SINCRO HISTORIAL <-> DISCO ---

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
                            size_bytes = stats.st_size

                            # Ignorar archivos totalmente vacíos (0 bytes)
                            if size_bytes == 0:
                                continue

                            # Calcular tamaño formateado adecuadamente (KB o MB)
                            size_mb = round(size_bytes / (1024 * 1024), 2)
                            if size_mb < 0.1:
                                size_kb = round(size_bytes / 1024, 2)
                                size_str = f"{size_kb} KB"
                            else:
                                size_str = f"{size_mb} MB"

                            backups.append({
                                "filename": file,
                                "path": file_path,
                                "size_mb": size_mb,
                                "size_str": size_str,
                                "created_at": stats.st_mtime
                            })
    except Exception as e:
        logger.error(f"[Backend] Error escaneando backups: {e}")
        raise HTTPException(status_code=500, detail=f"Error leyendo almacenamiento: {str(e)}")

    return {"target_disk": target_disk, "backups": backups}

@router.get("/logs")
def get_execution_logs():
    """
    Obtiene los logs de auditoría sin duplicidades 'Sistema'.
    """
    formatted_logs = []
    seen_targets = set()

    # 1. Leer registros explícitos en memoria de audit_service
    raw_logs = []
    try:
        if hasattr(audit_service, "get_logs") and callable(getattr(audit_service, "get_logs")):
            raw_logs = audit_service.get_logs(limit=50)
        elif hasattr(audit_service, "logs") and isinstance(audit_service.logs, list):
            raw_logs = audit_service.logs
        elif hasattr(audit_service, "_runtime_logs") and isinstance(audit_service._runtime_logs, list):
            raw_logs = audit_service._runtime_logs
    except Exception as e:
        logger.warning(f"[Audit] No se pudieron obtener logs en memoria: {e}")

    for l in raw_logs:
        if isinstance(l, dict):
            ts = l.get("timestamp", l.get("time", ""))
            target = l.get("target", l.get("app_name", l.get("name", "")))
            job_type = l.get("type", l.get("action", l.get("job_type", "Backup App")))
            status = l.get("status", l.get("result", "success"))
            duration = str(l.get("duration", l.get("time_taken", "Completado")))
        else:
            ts = getattr(l, "timestamp", "")
            target = getattr(l, "target", getattr(l, "app_name", ""))
            job_type = getattr(l, "type", getattr(l, "action", "Backup App"))
            status = getattr(l, "status", "success")
            duration = str(getattr(l, "duration", "Completado"))

        # Descartar registros vacíos o fantasma con etiqueta 'Sistema'
        if not target or target.strip().lower() in ["sistema", "none", "n/a"]:
            continue

        if isinstance(ts, (int, float)):
            ts_str = datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M:%S")
        else:
            ts_str = str(ts) if ts else datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        key = f"{ts_str}_{target}"
        if key not in seen_targets:
            seen_targets.add(key)
            formatted_logs.append({
                "timestamp": ts_str,
                "type": job_type,
                "target": target,
                "status": status,
                "duration": duration
            })

    # 2. Escanear archivos físicos reales del disco sin generar 'Sistema'
    target_disk = config_manager.config.selected_target_disk
    if target_disk and os.path.exists(target_disk):
        try:
            search_dirs = [os.path.join(target_disk, "Backups", "Apps")]
            for d in search_dirs:
                if not os.path.exists(d):
                    continue
                for root, _, files in os.walk(d):
                    for file in files:
                        if file.endswith(".tar.gz"):
                            file_path = os.path.join(root, file)
                            stats = os.stat(file_path)
                            ts_str = datetime.fromtimestamp(stats.st_mtime).strftime("%d/%m/%Y %H:%M:%S")

                            # Extraer nombre exacto de la aplicación
                            if "_backup" in file:
                                app_target = file.split("_backup")[0]
                            else:
                                app_target = os.path.basename(root)

                            key = f"{ts_str}_{app_target}"
                            if key not in seen_targets and app_target.lower() != "sistema":
                                seen_targets.add(key)
                                formatted_logs.append({
                                    "timestamp": ts_str,
                                    "type": "Backup App",
                                    "target": app_target,
                                    "status": "success",
                                    "duration": "Completado"
                                })
        except Exception as e:
            logger.warning(f"[Audit] Error deduciendo historial desde disco: {e}")

    # Ordenar por fecha decreciente
    formatted_logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return formatted_logs

@router.delete("/logs")
def clear_execution_logs():
    if hasattr(audit_service, "_runtime_logs"):
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