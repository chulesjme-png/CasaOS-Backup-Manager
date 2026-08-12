from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.session import get_db

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
    Renderiza la vista principal del Dashboard (index.html).
    Proporciona los datos requeridos por las plantillas y componentes Jinja2.
    """
    # Estructura requerida por summary_card.html y componentes del dashboard
    summary = {
        "containers": 0,
        "destinations": 0,
        "schedules": 0,
        "size": "0 B",
        "status": "Activo"
    }

    docker_info = {
        "containers_running": 0,
        "total_containers": 0
    }

    total_backends = 0
    total_schedules = 0
    engine_status = "Activo"
    recent_executions: List[Dict[str, Any]] = []
    protectable_items: List[Dict[str, Any]] = []

    try:
        # Lógica futura de lectura desde DB/Docker SDK
        pass
    except Exception as err:
        print(f"[Dashboard Router] Error al consultar métricas: {err}")

    context = {
        "request": request,
        "summary": summary,
        "docker": docker_info,
        "total_backends": total_backends,
        "total_schedules": total_schedules,
        "engine_status": engine_status,
        "recent_executions": recent_executions,
        "protectable_items": protectable_items,
    }

    return templates.TemplateResponse("index.html", context)