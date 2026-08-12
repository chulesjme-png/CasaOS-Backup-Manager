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

# Rutas del sistema a excluir del listado de datos respaldables
SYSTEM_IGNORED_PREFIXES = (
    "/var/run/docker.sock",
    "/etc/localtime",
    "/etc/timezone",
    "/dev/",
    "/sys",
    "/proc",
)


def scan_docker_and_casaos():
    """
    Escanea exhaustivamente los contenedores Docker e inspecciona sus montajes de forma aislada.
    """
    protectable_items: List[Dict[str, Any]] = []
    detected_apps = set()
    running_containers_count = 0

    # 1. Escaneo e inspección vía Docker API
    try:
        client = docker.DockerClient(base_url="unix://var/run/docker.sock")
        containers = client.containers.list(all=True)

        for container in containers:
            try:
                # Contar contenedores en ejecución
                if container.status == "running":
                    running_containers_count += 1

                name = container.name or ""
                if name in ["casaos-backup-manager", "casaos-backup"]:
                    continue

                # Inspección detallada para obtener Labels y Mounts completos
                try:
                    info = client.api.inspect_container(container.id)
                except Exception:
                    info = container.attrs or {}

                config = info.get("Config") or {}
                labels = config.get("Labels") or {}
                if not isinstance(labels, dict):
                    labels = {}

                # Determinar nombre de la aplicación
                app_name = (
                    labels.get("io.casaos.app")
                    or labels.get("com.docker.compose.project")
                    or name
                )
                if app_name:
                    detected_apps.add(app_name)

                # Procesar puntos de montaje
                mounts = info.get("Mounts") or []
                for m in mounts:
                    if not isinstance(m, dict):
                        continue

                    host_path = str(m.get("Source") or "").strip()
                    container_path = str(m.get("Destination") or "").strip()
                    mount_type = str(m.get("Type") or "bind").strip()

                    if not host_path or not container_path:
                        continue

                    # Omitir conectores/archivos del sistema
                    if any(host_path.startswith(prefix) for prefix in SYSTEM_IGNORED_PREFIXES):
                        continue

                    # Evitar duplicados
                    already_added = any(
                        item["container"] == app_name and item["host_path"] == host_path
                        for item in protectable_items
                    )
                    if not already_added:
                        protectable_items.append({
                            "container": app_name,
                            "host_path": host_path,
                            "container_path": container_path,
                            "type": mount_type,
                            "hook": "Docker Mount"
                        })

            except Exception as inner_err:
                print(f"[Docker Scan] Error analizando contenedor {getattr(container, 'name', 'desconocido')}: {inner_err}")

    except Exception as e:
        print(f"[Docker Scan Error] Error al conectar con el socket de Docker: {e}")

    # 2. Escaneo complementario directo en carpetas AppData de CasaOS
    appdata_dirs = ["/DATA/AppData", "/DATA/appdata", "/var/lib/casaos/apps"]
    for base_path in appdata_dirs:
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
                print(f"[Storage Scan Error] Error al leer {base_path}: {e}")

    return len(detected_apps), running_containers_count, protectable_items


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