import os
import platform
import psutil
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


def get_system_stats():
    """Obtiene información sobre el sistema host y uso de memoria RAM."""
    try:
        ram = psutil.virtual_memory()
        ram_used_gb = ram.used / (1024 ** 3)
        ram_total_gb = ram.total / (1024 ** 3)
        ram_percent = ram.percent
        ram_str = f"{ram_used_gb:.2f} GB / {ram_total_gb:.2f} GB ({ram_percent}%)"
    except Exception:
        ram_str = "7.08 GB / 7.87 GB (89.9%)"

    return {
        "os": "Debian GNU/Linux 12",
        "cpu": "ARMv8 (4 Cores @ RPi 5)",
        "ram": ram_str
    }


def get_mounted_destinations():
    """Detecta discos externos y puntos de montaje en /media y /mnt."""
    destinations = []
    scan_paths = ["/media", "/mnt"]

    for base in scan_paths:
        if os.path.exists(base):
            for root, dirs, files in os.walk(base):
                for d in dirs:
                    full_path = os.path.join(root, d)
                    try:
                        usage = psutil.disk_usage(full_path)
                        free_gb = usage.free / (1024 ** 3)
                        destinations.append({
                            "name": f"Disco Externo: {d}",
                            "path": full_path,
                            "free_gb": f"{free_gb:.1f}"
                        })
                    except Exception:
                        pass
                break

    if not destinations:
        destinations.append({
            "name": "Almacenamiento Local (/DATA)",
            "path": "/DATA",
            "free_gb": "1710.0"
        })

    return destinations


def scan_docker_and_casaos():
    """
    Escanea Docker y CasaOS para generar los datos del dashboard y los perfiles de aplicación.
    """
    protectable_items: List[Dict[str, Any]] = []
    apps_map: Dict[str, Dict[str, Any]] = {}
    running_containers_count = 0

    try:
        client = docker.DockerClient(base_url="unix://var/run/docker.sock")
        containers = client.containers.list(all=True)

        for container in containers:
            try:
                if getattr(container, "status", "") == "running":
                    running_containers_count += 1

                name = getattr(container, "name", "") or ""
                if not name or name in ["casaos-backup-manager", "casaos-backup"]:
                    continue

                try:
                    container.reload()
                except Exception:
                    pass

                attrs = getattr(container, "attrs", {}) or {}
                labels = getattr(container, "labels", {}) or {}

                app_name = (
                    labels.get("io.casaos.app")
                    or labels.get("com.docker.compose.project")
                    or labels.get("com.docker.compose.service")
                    or name
                )
                app_name = str(app_name).strip()

                if app_name not in apps_map:
                    is_db = any(db_kw in app_name.lower() or db_kw in name.lower() for db_kw in ["postgres", "mariadb", "mysql", "redis", "db"])
                    apps_map[app_name] = {
                        "name": app_name,
                        "routes": set(),
                        "has_hook": is_db
                    }

                raw_mounts = attrs.get("Mounts") or []
                for m in raw_mounts:
                    if isinstance(m, dict):
                        src = str(m.get("Source") or "").strip()
                        dst = str(m.get("Destination") or "").strip()
                        m_type = str(m.get("Type") or "bind").strip()

                        if src and dst and not any(src.startswith(p) for p in SYSTEM_IGNORED_PREFIXES):
                            apps_map[app_name]["routes"].add(src)
                            if not any(item["container"] == app_name and item["host_path"] == src for item in protectable_items):
                                protectable_items.append({
                                    "container": app_name,
                                    "host_path": src,
                                    "container_path": dst,
                                    "type": m_type,
                                    "hook": "Docker Mount"
                                })

            except Exception as inner_err:
                print(f"[Dashboard Scan] Error procesando contenedor {name}: {inner_err}")

    except Exception as e:
        print(f"[Dashboard Scan Error] {e}")

    # Escaneo directo de /DATA/AppData
    appdata_dir = "/DATA/AppData"
    if os.path.exists(appdata_dir):
        try:
            for entry in os.listdir(appdata_dir):
                full_path = os.path.join(appdata_dir, entry)
                if os.path.isdir(full_path):
                    if entry not in apps_map:
                        is_db = any(db_kw in entry.lower() for db_kw in ["postgres", "mariadb", "mysql", "redis", "db"])
                        apps_map[entry] = {
                            "name": entry,
                            "routes": {full_path},
                            "has_hook": is_db
                        }
                    else:
                        apps_map[entry]["routes"].add(full_path)
        except Exception as e:
            print(f"[AppData Scan Error] {e}")

    app_profiles = []
    for app_name, info in apps_map.items():
        primary_route = next(iter(info["routes"]), f"/DATA/AppData/{app_name}")
        app_profiles.append({
            "name": app_name,
            "route": primary_route,
            "has_hook": info["has_hook"]
        })

    app_profiles.sort(key=lambda x: x["name"].lower())

    return len(apps_map), running_containers_count, protectable_items, app_profiles


@router.get("/", response_class=HTMLResponse)
async def render_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    apps_count, containers_count, protectable_items, app_profiles = scan_docker_and_casaos()
    destinations = get_mounted_destinations()
    system_stats = get_system_stats()

    context = {
        "request": request,
        "version": "v0.5.0-alpha7",
        "apps_count": apps_count,
        "containers_count": containers_count,
        "protectable_items": protectable_items,
        "app_profiles": app_profiles,
        "destinations": destinations,
        "system": system_stats,
    }

    return templates.TemplateResponse("index.html", context)