"""
Router principal con telemetría real de la Raspberry Pi, CasaOS y Perfiles de Aplicación.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os
import traceback

from app.services.system_service import (
    get_system_info,
    get_docker_info,
    get_disk_info,
    get_protectable_data
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
        # 1. Telemetría real del host y Docker
        system_raw = get_system_info()
        docker_raw = get_docker_info()
        disk_raw = get_disk_info("/DATA")

        system_raw["api_version"] = docker_raw.get("api_version", "1.43")
        
        engine_data = DynamicData(system_raw)
        docker_data = DynamicData(docker_raw)
        disk_data = DynamicData(disk_raw)

        # 2. Servicios / Contenedores reales detectados
        services_list = [DynamicData(s) for s in docker_raw.get("services_list", [])]

        # 3. Datos protegibles (Rutas y DBs reales)
        protectable_raw = get_protectable_data()
        protectable_list = [DynamicData(item) for item in protectable_raw]

        # 4. Generación dinámica de Perfiles de Aplicación
        profiles_raw = profile_service.generate_profiles_from_discovery()
        profiles_list = [DynamicData(p) for p in profiles_raw]

        # 5. Aplicaciones activas basadas en perfiles
        apps_list = [
            DynamicData({"name": "CasaOS Apps", "containers": len(services_list), "status": "En ejecución", "running": True})
        ]

        # 6. Almacenamiento CasaOS
        destinations_list = [
            DynamicData({
                "id": "dest_1",
                "name": "Almacenamiento CasaOS (/DATA)",
                "mount": "/DATA",
                "mount_point": "/DATA",
                "transport": "Local Storage",
                "path": "/DATA",
                "system": "ext4",
                "total_gb": disk_raw["total_gb"],
                "used_gb": disk_raw["used_gb"],
                "free_gb": disk_raw["free_gb"],
                "use_percent": disk_raw["percent"],
                "status": "Conectado",
            })
        ]

        # 7. Motores de Backup integrados
        backends_list = [
            DynamicData({"id": "duplicati", "name": "Duplicati Engine", "status": "Activo", "available": True}),
            DynamicData({"id": "restic", "name": "Restic Engine", "status": "Listo", "available": True}),
        ]

        # 8. Resumen dinámico
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