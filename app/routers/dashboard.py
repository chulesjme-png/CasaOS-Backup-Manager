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

# Rutas del sistema a ignorar en el listado de datos protegibles
SYSTEM_IGNORED_PATHS = {
    "/var/run/docker.sock",
    "/etc/localtime",
    "/etc/timezone",
    "/dev/urandom",
    "/sys",
    "/proc"
}


def scan_docker_and_casaos():
    """
    Escanea exhaustivamente los contenedores Docker y el sistema de archivos de CasaOS
    para identificar aplicaciones, volúmenes y rutas persistentes protegibles.
    """
    protectable_items: List[Dict[str, Any]] = []
    detected_apps = set()
    running_containers = 0

    # 1. Escaneo vía Docker SDK
    try:
        client = docker.DockerClient(base_url="unix://var/run/docker.sock")
        containers = client.containers.list(all=True)
        running_containers = len([c for c in containers if c.status == "running"])

        for container in containers:
            name = container.name
            if name == "casaos-backup-manager":
                continue

            labels = container.labels or {}
            # Nombre de la aplicación (Label CasaOS -> Proyecto Compose -> Nombre Contenedor)
            app_name = (
                labels.get("io.casaos.app") 
                or labels.get("com.docker.compose.project") 
                or name
            )
            detected_apps.add(app_name)

            # Extracción flexible de montajes (Soporta atributo de SDK y diccionario raw)
            raw_mounts = getattr(container, "mounts", []) or container.attrs.get("Mounts", [])

            for mount in raw_mounts:
                if isinstance(mount, dict):
                    host_path = mount.get("Source", "")
                    container_path = mount.get("Destination", "")
                    mount_type = mount.get("Type", "bind")
                else:
                    host_path = getattr(mount, "source", "")
                    container_path = getattr(mount, "destination", "")
                    mount_type = getattr(mount, "type", "bind")

                if host_path and container_path:
                    # Descartar conectores de sistema
                    if any(host_path.startswith(path) for path in SYSTEM_IGNORED_PATHS):
                        continue

                    # Evitar duplicados exactos
                    if not any(item["container"] == app_name and item["host_path"] == host_path for item in protectable_items):
                        protectable_items.append({
                            "container": app_name,
                            "host_path": host_path,
                            "container_path": container_path,
                            "type": mount_type,
                            "hook": "Docker Mount"
                        })

    except Exception as e:
        print(f"[Docker Scan Error] Error escaneando Docker: {e}")

    # 2. Escaneo complementario de carpetas AppData en disco (/DATA/AppData)
    appdata_paths = ["/DATA/AppData", "/DATA/appdata", "/var/lib/casaos/apps"]
    for base_path in appdata_paths:
        if os.path.exists(base_path) and os.path.isdir(base_path):
            try:
                for entry in os.listdir(base_path):
                    full_path = os.path.join(base_path, entry)
                    if os.path.isdir(full_path):
                        detected_apps.add(entry)
                        if not any(item["host_path"] == full_path for item in protectable_items):
                            protectable_items.append({
                                "container": entry,
                                "host_path": full_path,
                                "container_path": f"/data/{entry}",
                                "type": "bind",
                                "hook": "CasaOS Storage"
                            })
            except Exception as e:
                print(f"[Storage Scan Error] Error leyendo {base_path}: {e}")

    return len(detected_apps), running_containers, protectable_items


@router.get("/", response_class=HTMLResponse)
async def render_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    apps_count, containers_count, protectable_items = scan_docker_and_casaos()
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