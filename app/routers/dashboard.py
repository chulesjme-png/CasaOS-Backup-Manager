from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.config.template import templates
from app.utils.template import build_context

from app.core.services import (
    get_docker_status,
    get_disk_usage,
    get_services_status,
    get_applications,
)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    context = build_context(
        request,
        docker=get_docker_status(),
        disk=get_disk_usage(),
        services=get_services_status(),
        applications=get_applications(),
    )

    return templates.TemplateResponse(
        "index.html",
        context,
    )