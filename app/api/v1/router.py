import os
import shutil
import platform
import subprocess
import urllib.request
import json
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database.connection import get_db, SessionLocal
from app.core.config import config_manager
from app.schemas.execution import ExecutionCreate
from app.services.execution_history_service import ExecutionHistoryService
from app.services.background_worker_service import BackgroundWorkerService
from app.models.execution import ExecutionRecordModel

router = APIRouter()


@router.get("/apps", response_model=List[str])
def get_apps():
    app_data_path = Path("/DATA/AppData")
    if not app_data_path.exists() or not app_data_path.is_dir():
        return []
    apps = [
        entry.name
        for entry in app_data_path.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    ]
    return sorted(apps)


@router.get("/system/info")
def get_system_info():
    mem_bytes = (
        os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        if hasattr(os, "sysconf")
        else 0
    )
    return {
        "processor": platform.processor() or platform.machine(),
        "architecture": platform.architecture()[0],
        "system": platform.system(),
        "release": platform.release(),
        "total_memory_gb": round(mem_bytes / (1024**3), 2),
    }


@router.get("/system/docker")
def get_docker_containers():
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}|{{.Status}}|{{.Image}}"],
            capture_output=True,
            text=True,
            check=True,
        )
        containers = []
        for line in result.stdout.strip().split("\n"):
            if line:
                parts = line.split("|")
                containers.append(
                    {
                        "name": parts[0],
                        "status": parts[1] if len(parts) > 1 else "",
                        "image": parts[2] if len(parts) > 2 else "",
                    }
                )
        return containers
    except Exception:
        return []


@router.get("/system/disks")
def get_disks():
    disks = []
    media_path = Path("/media")
    data_path = Path("/DATA")
    paths_to_check = [data_path]
    if media_path.exists():
        paths_to_check.extend([p for p in media_path.iterdir() if p.is_dir()])

    for p in paths_to_check:
        try:
            usage = shutil.disk_usage(p)
            disks.append(
                {
                    "path": str(p),
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent_used": round((usage.used / usage.total) * 100, 1),
                }
            )
        except Exception:
            continue
    return disks


@router.get("/config")
def get_config():
    return config_manager.config


@router.post("/config")
def update_config(config_data: dict):
    return config_manager.save_config(config_data)


@router.post("/config/test-telegram")
def test_telegram():
    cfg = config_manager.config
    if not cfg.telegram_enabled or not cfg.telegram_bot_token or not cfg.telegram_chat_id:
        raise HTTPException(
            status_code=400,
            detail="Telegram no está configurado o habilitado.",
        )

    url = f"https://api.telegram.org/bot{cfg.telegram_bot_token}/sendMessage"
    payload = json.dumps(
        {
            "chat_id": cfg.telegram_chat_id,
            "text": "🧪 Mensaje de prueba desde CasaOS Backup Manager.",
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                return {
                    "status": "ok",
                    "message": "Mensaje de prueba enviado correctamente.",
                }
            raise HTTPException(
                status_code=400, detail="Error en la respuesta de Telegram."
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error enviando mensaje: {str(e)}"
        )


@router.post("/backups/run-app/{app_name}")
def run_app_backup(
    app_name: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    history_service = ExecutionHistoryService(db)
    exec_data = ExecutionCreate(
        app_name=app_name,
        backend_type="tar",
        destination_path=config_manager.config.selected_target_disk or "/DATA/Backups",
    )
    record = history_service.create_execution(exec_data)

    background_tasks.add_task(
        BackgroundWorkerService.run_backup_job_async,
        record.id,
        SessionLocal,
    )
    return record


@router.delete("/executions")
def clear_executions(db: Session = Depends(get_db)):
    db.query(ExecutionRecordModel).delete()
    db.commit()
    return {"status": "ok", "message": "Historial de ejecuciones vaciado."}