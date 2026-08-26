from fastapi import APIRouter, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException
from typing import List, Dict, Any
import time

from app.services.disk_service import disk_service
from app.services.docker_service import docker_service
from app.services.app_discovery_service import app_discovery_service
from app.services.backup_engine_service import backup_engine_service
from app.services.audit_service import audit_service
from app.core.config import config_service
from app.core.ws_manager import ws_manager
from app.schemas.config import ConfigSchema

router = APIRouter()

@router.get("/system/disks")
async def get_disks():
    """
    Retorna la lista de discos montados marcando cuál es el disco seleccionado en la configuración.
    """
    config = config_service.load_config()
    selected_disk = config.get("selected_target_disk", "/DATA")
    
    disks = disk_service.get_disks()
    
    # Marcar el disco activo persistido
    for disk in disks:
        disk["is_selected"] = (disk["mountpoint"] == selected_disk)
        
    return disks

@router.get("/system/docker")
async def get_docker_status():
    return docker_service.get_system_status()

@router.get("/apps")
async def get_applications():
    return app_discovery_service.discover_apps()

@router.post("/config")
async def update_config(payload: ConfigSchema):
    config_service.save_config(payload.dict())
    return {"status": "success", "config": payload.dict()}

@router.get("/config")
async def get_config():
    return config_service.load_config()

@router.post("/backup/full")
async def run_full_backup(background_tasks: BackgroundTasks):
    job_id = f"backup_{int(time.time())}"
    
    async def task_wrapper():
        start_time = time.perf_counter()
        try:
            result = await backup_engine_service.create_full_backup()
            duration = round(time.perf_counter() - start_time, 2)
            audit_service.log_execution(job_id=job_id, status="SUCCESS", duration=duration, details=result)
            await ws_manager.broadcast({"type": "BACKUP_FINISHED", "status": "SUCCESS", "job_id": job_id})
        except Exception as e:
            duration = round(time.perf_counter() - start_time, 2)
            audit_service.log_execution(job_id=job_id, status="FAILED", duration=duration, error=str(e))
            await ws_manager.broadcast({"type": "BACKUP_FINISHED", "status": "FAILED", "error": str(e)})

    background_tasks.add_task(task_wrapper)
    return {"status": "started", "job_id": job_id}

@router.get("/backups")
async def list_backups():
    config = config_service.load_config()
    target_disk = config.get("selected_target_disk", "/DATA")
    return backup_engine_service.list_available_backups(target_disk=target_disk)

@router.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)