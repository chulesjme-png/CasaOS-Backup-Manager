"""
Router principal con telemetría real de la Raspberry Pi, CasaOS, Perfiles de Aplicación y Restauración.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import traceback

from app.services.system_service import (
    get_real_system_info,
    get_real_docker_info,
    get_real_disk_info,
    get_real_protectable_data
)
from app.services.profile_service import profile_service

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

router = APIRouter(tags=["Dashboard"])
templates = Jinja2Templates(directory=TEMPLATES_DIR)


class DynamicData(dict):
    """Acceso dinámico por atributo o diccionario."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    def __getattr__(self, name):
        if name in self:
            return self[name]
        lower = name.lower()
        for k, v in self.items():
            if k.lower() == lower:
                return v
        return 0 if any(num in lower for num in ["count", "total", "used", "free", "percent", "running", "stopped"]) else ""


@router.get("/", response_class=HTMLResponse)
async def render_dashboard(request: Request):
    try:
        system_raw = get_real_system_info()
        docker_raw = get_real_docker_info()
        disk_raw = get_real_disk_info("/DATA")

        system_raw["api_version"] = docker_raw.get("api_version", "1.43")
        
        engine_data = DynamicData(system_raw)
        docker_data = DynamicData(docker_raw)
        disk_data = DynamicData(disk_raw)

        services_list = [DynamicData(s) for s in docker_raw.get("services_list", [])]

        protectable_raw = get_real_protectable_data()
        protectable_list = [DynamicData(item) for item in protectable_raw]

        profiles_raw = profile_service.generate_profiles_from_discovery()
        profiles_list = [DynamicData(p) for p in profiles_raw]

        apps_list = [
            DynamicData({"name": "CasaOS Apps", "containers": len(services_list), "status": "En ejecución", "running": True})
        ]

        destinations_list = [
            DynamicData({
                "id": "dest_1",
                "name": "Almacenamiento CasaOS (/DATA)",
                "mount": "/DATA",
                "mount_point": "/DATA",
                "transport": "Local Storage",
                "path": "/DATA",
                "system": "ext4",
                "total_gb": disk_raw.get("total_gb", 0),
                "used_gb": disk_raw.get("used_gb", 0),
                "free_gb": disk_raw.get("free_gb", 0),
                "use_percent": disk_raw.get("percent", 0),
                "status": "Conectado",
            })
        ]

        backends_list = [
            DynamicData({"id": "duplicati", "name": "Duplicati Engine", "status": "Activo", "available": True}),
            DynamicData({"id": "restic", "name": "Restic Engine", "status": "Listo", "available": True}),
        ]

        summary_info = DynamicData({
            "applications": len(profiles_list),
            "containers": docker_raw.get("containers_running", 0),
            "routes": len(protectable_list),
            "persistent_routes": len(protectable_list),
        })

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "title": "CasaOS Backup Manager",
                "engine": engine_data,
                "system": engine_data,
                "docker": docker_data,
                "disk": disk_data,
                "disk_info": disk_data,
                "storage": destinations_list,
                "destinations": destinations_list,
                "applications": apps_list,
                "services": services_list,
                "containers": services_list,
                "protectable_data": protectable_list,
                "profiles": profiles_list,
                "backends": backends_list,
                "summary": summary_info,
                "summary_info": summary_info,
            }
        )
    except Exception as e:
        return HTMLResponse(content=f"<pre>{traceback.format_exc()}</pre>", status_code=500)


@router.get("/restore", response_class=HTMLResponse)
async def render_restore(request: Request):
    try:
        profiles_raw = profile_service.generate_profiles_from_discovery()
        profiles_list = [DynamicData(p) for p in profiles_raw]

        return templates.TemplateResponse(
            "restore.html",
            {
                "request": request,
                "title": "Centro de Restauración",
                "profiles": profiles_list,
            }
        )
    except Exception as e:
        return HTMLResponse(content=f"<pre>{traceback.format_exc()}</pre>", status_code=500)