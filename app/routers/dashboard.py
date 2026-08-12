from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.session import get_db

try:
    from app.services.docker_service import DockerService
except ImportError:
    DockerService = None

try:
    from app.services.casaos_service import CasaOSService
except ImportError:
    CasaOSService = None

try:
    from app.services.protectable_data_service import ProtectableDataService
except ImportError:
    ProtectableDataService = None

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@router.get("/", response_class=HTMLResponse)
async def render_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Renderiza el Dashboard obteniendo los contenedores y rutas de CasaOS reales.
    """
    containers_count = 0
    apps_count = 0
    routes_count = 0
    protectable_items: List[Dict[str, Any]] = []

    if DockerService:
        try:
            docker_srv = DockerService()
            if hasattr(docker_srv, "get_containers"):
                containers = docker_srv.get_containers()
                containers_count = len(containers)
        except Exception as e:
            print(f"[Dashboard Router] Error al escanear Docker: {e}")

    if ProtectableDataService:
        try:
            prot_srv = ProtectableDataService()
            if hasattr(prot_srv, "get_protectable_data"):
                protectable_items = prot_srv.get_protectable_data()
                routes_count = len(protectable_items)
        except Exception as e:
            print(f"[Dashboard Router] Error al escanear datos protegibles: {e}")
    elif CasaOSService:
        try:
            casa_srv = CasaOSService()
            if hasattr(casa_srv, "get_apps"):
                apps = casa_srv.get_apps()
                apps_count = len(apps)
        except Exception as e:
            print(f"[Dashboard Router] Error al consultar CasaOS: {e}")

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