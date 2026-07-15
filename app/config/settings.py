"""
Configuración global de CasaOS Backup Manager.

Este módulo centraliza todos los parámetros generales de la aplicación.
Ningún otro archivo debe contener valores "hardcodeados" relacionados con
el nombre de la aplicación, versión, host o puerto.
"""

from __future__ import annotations

# -----------------------------------------------------------------------------
# Aplicación
# -----------------------------------------------------------------------------

APP_NAME: str = "CasaOS Backup Manager"
APP_VERSION: str = "0.1.0-alpha3"
APP_DESCRIPTION: str = (
    "Professional backup manager for CasaOS Docker applications."
)

# -----------------------------------------------------------------------------
# Servidor
# -----------------------------------------------------------------------------

HOST: str = "0.0.0.0"
PORT: int = 8088

DEBUG: bool = True

# -----------------------------------------------------------------------------
# Docker
# -----------------------------------------------------------------------------

DOCKER_SOCKET: str = "/var/run/docker.sock"

# -----------------------------------------------------------------------------
# Interfaz
# -----------------------------------------------------------------------------

DEFAULT_LANGUAGE: str = "es"

# -----------------------------------------------------------------------------
# Logging (se utilizará en la siguiente entrega)
# -----------------------------------------------------------------------------

LOG_LEVEL: str = "INFO"