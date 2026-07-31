from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config.settings import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
)

from app.config.template import templates
from app.routers.dashboard import router as dashboard_router
from app.routers.api_health import router as health_router
from app.routers.api_backends import router as backends_router
from app.routers.api_executions import router as executions_router


app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
)

app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)

# UI Routers
app.include_router(dashboard_router)

# REST API Routers
app.include_router(health_router)
app.include_router(backends_router)
app.include_router(executions_router)