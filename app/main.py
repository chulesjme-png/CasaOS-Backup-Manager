from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config.settings import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
)

from app.config.template import templates
from app.routers.dashboard import router as dashboard_router


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

app.include_router(dashboard_router)