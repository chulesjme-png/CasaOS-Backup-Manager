from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.config.template import templates
from app.services.dashboard_service import DashboardService
from app.utils.template import build_context


router = APIRouter()

dashboard_service = DashboardService()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):

    context = build_context(
        request,
        **dashboard_service.get_dashboard_data(),
    )

    return templates.TemplateResponse(
        "index.html",
        context,
    )