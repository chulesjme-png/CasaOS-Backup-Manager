from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.session import get_db

router = APIRouter()

# Ubicación de la carpeta de plantillas (app/templates)
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
    Recopila contadores de destinos, programaciones y estado del sistema.
    """
    total_backends = 0
    total_schedules = 0
    engine_status = "Activo"
    recent_executions: List[Dict[str, Any]] = []
    protectable_items: List[Dict[str, Any]] = []

    # Intento de lectura de métricas de la base de datos con manejo de fallos
    try:
        # Si tienes modelos SQLAlchemy importados, puedes descomentar la lógica:
        # total_backends = db.query(Backend).count()
        # total_schedules = db.query(Schedule).count()
        pass
    except Exception as err:
        print(f"[Dashboard Router] Error al obtener datos de la BD: {err}")

    context = {
        "request": request,
        "total_backends": total_backends,
        "total_schedules": total_schedules,
        "engine_status": engine_status,
        "recent_executions": recent_executions,
        "protectable_items": protectable_items,
    }

    return templates.TemplateResponse("index.html", context)