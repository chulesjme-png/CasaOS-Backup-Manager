"""
Configuración global de CasaOS Backup Manager.

Este módulo centraliza todos los parámetros generales de la aplicación.
Ningún otro archivo debe contener valores "hardcodeados" relacionados con
el nombre de la aplicación, versión, host o puerto.
"""

from __future__ import annotations

from app.core.host import HostConfig

# -----------------------------------------------------------------------------
# Aplicación
# -----------------------------------------------------------------------------

APP_NAME: str = "CasaOS Backup Manager"
APP_VERSION: str = "0.1.0-alpha4"
APP_DESCRIPTION: str = (
    "Professional backup manager for CasaOS Docker applications."
)

# -----------------------------------------------------------------------------
# Servidor Web
# -----------------------------------------------------------------------------

HOST: str = "0.0.0.0"
PORT: int = 8088

DEBUG: bool = True

# -----------------------------------------------------------------------------
# Docker
# -----------------------------------------------------------------------------

DEFAULT_HOST = HostConfig(
    name="Local Docker",
    connection="local",
)

# -----------------------------------------------------------------------------
# Interfaz
# -----------------------------------------------------------------------------

DEFAULT_LANGUAGE: str = "es"

# -----------------------------------------------------------------------------
# Logging (se utilizará en próximas entregas)
# -----------------------------------------------------------------------------

LOG_LEVEL: str = "INFO"