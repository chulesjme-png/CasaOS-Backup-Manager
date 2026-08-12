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

SYSTEM_IGNORED_PREFIXES = (
    "/var/run/docker.sock",
    "/etc/localtime",
    "/etc/timezone",
    "/dev",
    "/sys",
    "/proc",
)


def scan_docker_and_casaos():
    """
    Escanea los contenedores Docker activos e inspecciona sus volúmenes y etiquetas.
    """
    protectable_items: List[Dict[str, Any]] = []
    detected_apps = set()
    running_containers_count = 0

    try:
        client = docker.DockerClient(base_url="unix://var/run/docker.sock")
        containers = client.containers.list(all=True)

        for container in containers:
            try:
                status = getattr(container, "status", "unknown")
                if status == "running":
                    running_containers_count += 1

                name = getattr(container, "name", "") or ""
                if not name or name in ["casaos-backup-manager", "casaos-backup"]:
                    continue

                # Cargar metadatos completos del contenedor
                try:
                    container.reload()
                except Exception as reload_err:
                    print(f"[Dashboard] Warning al recargar {name}: {reload_err}")

                attrs = getattr(container, "attrs", {}) or {}
                if not isinstance(attrs, dict):
                    attrs = {}

                # Extraer etiquetas (Labels)
                labels = getattr(container, "labels", {}) or {}
                if not isinstance(labels, dict):
                    config = attrs.get("Config")
                    labels = config.get("Labels") if isinstance(config, dict) else {}
                    if not isinstance(labels, dict):
                        labels = {}

                # Nombre de la aplicación (CasaOS label -> Compose project -> Nombre contenedor)
                app_name = (
                    labels.get("io.casaos.app")
                    or labels.get("com.docker.compose.project")
                    or labels.get("com.docker.compose.service")
                    or name
                )
                app_name = str(app_name).strip()
                if app_name:
                    detected_apps.add(app_name)

                # Extraer Puntos de Montaje (Mounts y Binds)
                mounts_to_process = []

                # Metodo 1: 'Mounts' (Inspección estándar)
                raw_mounts = attrs.get("Mounts")
                if isinstance(raw_mounts, list):
                    for m in raw_mounts:
                        if isinstance(m, dict):
                            src = str(m.get("Source") or "").strip()
                            dst = str(m.get("Destination") or "").strip()
                            m_type = str(m.get("Type") or "bind").strip()
                            if src and dst:
                                mounts_to_process.append((src, dst, m_type))

                # Metodo 2: 'HostConfig.Binds' (Formato host:container)
                host_config = attrs.get("HostConfig")
                if isinstance(host_config, dict):
                    binds = host_config.get("Binds")
                    if isinstance(binds, list):
                        for b in binds:
                            if isinstance(b, str) and ":" in b:
                                parts = b.split(":")
                                if len(parts) >= 2:
                                    src, dst = parts[0].strip(), parts[1].strip()
                                    if src and dst and not any(item[0] == src and item[1] == dst for item in mounts_to_process):
                                        mounts_to_process.append((src, dst, "bind"))

                # Registrar rutas válidas omitiendo archivos del sistema
                for host_path, container_path, mount_type in mounts_to_process:
                    if any(host_path.startswith(prefix) for prefix in SYSTEM_IGNORED_PREFIXES):
                        continue

                    already_exists = any(
                        item["container"] == app_name and item["host_path"] == host_path
                        for item in protectable_items
                    )
                    if not already_exists:
                        protectable_items.append({
                            "container": app_name,
                            "host_path": host_path,
                            "container_path": container_path,
                            "type": mount_type,
                            "hook": "Docker Mount"
                        })

            except Exception as inner_err:
                print(f"[Dashboard] Error procesando contenedor '{getattr(container, 'name', 'desconocido')}': {inner_err}")

    except Exception as e:
        print(f"[Dashboard Error] Error general de Docker SDK: {e}")

    # Escaneo complementario de carpetas de almacenamiento de CasaOS (/DATA/AppData)
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
                print(f"[Dashboard Error] Error leyendo {base_path}: {e}")

    print(f"[Dashboard Scan Result] Apps: {len(detected_apps)} | Running Containers: {running_containers_count} | Protectable Routes: {len(protectable_items)}")

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
        "applications": apps_count,
        "containers": containers_count,
        "persistent_routes": routes_count,
        "routes": routes_count,
        "destinations": 0,
        "schedules": 0,
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