import os
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import docker
from app.database.session import get_db

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_casaos_protectable_data():
    """
    Escanea los contenedores Docker y las rutas del sistema de CasaOS (/DATA/AppData)
    para listar las aplicaciones y sus volúmenes protegibles.
    """
    protectable_items = []
    running_containers = 0
    detected_apps = set()

    # 1. Inspección vía Socket de Docker
    try:
        client = docker.DockerClient(base_url="unix://var/run/docker.sock")
        containers = client.containers.list()
        running_containers = len(containers)

        for container in containers:
            name = container.name
            if name in ["casaos-backup-manager", "casaos"]:
                continue

            labels = container.labels or {}
            app_name = labels.get("io.casaos.app", name)
            detected_apps.add(app_name)

            mounts = container.attrs.get("Mounts", [])
            for mount in mounts:
                host_path = mount.get("Source", "")
                container_path = mount.get("Destination", "")
                mount_type = mount.get("Type", "")

                if host_path and container_path:
                    protectable_items.append({
                        "container": app_name,
                        "host_path": host_path,
                        "container_path": container_path,
                        "type": mount_type,
                        "hook": "Docker Mount"
                    })
    except Exception as e:
        print(f"[Docker Scan Error] {e}")

    # 2. Escaneo directo de AppData de CasaOS (/DATA/AppData)
    app_data_dir = "/DATA/AppData"
    if os.path.exists(app_data_dir):
        try:
            for item in os.listdir(app_data_dir):
                item_path = os.path.join(app_data_dir, item)
                if os.path.isdir(item_path):
                    detected_apps.add(item)
                    if not any(pi["host_path"] == item_path for pi in protectable_items):
                        protectable_items.append({
                            "container": item,
                            "host_path": item_path,
                            "container_path": f"/data/{item}",
                            "type": "bind",
                            "hook": "CasaOS AppData"
                        })
        except Exception as e:
            print(f"[CasaOS AppData Scan Error] {e}")

    return len(detected_apps), running_containers, protectable_items


@router.get("/", response_class=HTMLResponse)
async def render_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    apps_count, containers_count, protectable_items = get_casaos_protectable_data()
    routes_count = len(protectable_items)

    summary = {
        "apps": apps_count,
        "containers": containers_count,
        "persistent_routes": routes_count,
        "status": "Activo"
    }

    docker_info = {
        "containers_running": containers_count,
        "total_containers": containers_count
    }

    context = {
        "request": request,
        "summary": summary,
        "docker": docker_info,
        "total_backends": 0,
        "total_schedules": 0,
        "engine_status": "Activo",
        "recent_executions": [],
        "protectable_items": protectable_items,
    }

    return templates.TemplateResponse("index.html", context)