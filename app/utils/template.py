from __future__ import annotations

from fastapi import Request

from app.config.settings import (
    APP_NAME,
    APP_VERSION,
)


def build_context(
    request: Request,
    **kwargs,
) -> dict:
    """
    Construye el contexto base para todas las plantillas.
    """

    context = {
        "request": request,
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
    }

    context.update(kwargs)

    return context