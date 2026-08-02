"""
Router API v1 para alimentar los scripts dinámicos del frontend (app.js).
"""

from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter(prefix="/api/v1", tags=["API v1"])


@router.get("/backends")
async def get_backends() -> List[Dict[str, Any]]:
    """
    Retorna los motores de backup registrados que consume app.js.
    """
    return [
        {
            "id": "duplicati",
            "name": "Duplicati Engine",
            "type": "duplicati",
            "status": "Activo",
            "state": "active",
            "available": True,
            "enabled": True,
            "version": "2.0.7",
            "description": "Motor de copias cifradas y diferenciales."
        },
        {
            "id": "restic",
            "name": "Restic Engine",
            "type": "restic",
            "status": "Listo",
            "state": "ready",
            "available": True,
            "enabled": True,
            "version": "0.16.2",
            "description": "Motor rápido con deduplicación de datos."
        }
    ]


@router.get("/containers")
async def get_containers() -> List[Dict[str, Any]]:
    """
    Retorna la lista de contenedores Docker activos.
    """
    return [
        {
            "name": "plex",
            "container": "plex",
            "container_name": "plex",
            "image": "lscr.io/linuxserver/plex:latest",
            "status": "En ejecución",
            "state": "running"
        },
        {
            "name": "nextcloud-app",
            "container": "nextcloud-app",
            "container_name": "nextcloud-app",
            "image": "nextcloud:stable-apache",
            "status": "En ejecución",
            "state": "running"
        },
        {
            "name": "nextcloud-db",
            "container": "nextcloud-db",
            "container_name": "nextcloud-db",
            "image": "mariadb:10.6",
            "status": "En ejecución",
            "state": "running"
        },
        {
            "name": "adguardhome",
            "container": "adguardhome",
            "container_name": "adguardhome",
            "image": "adguard/adguardhome:latest",
            "status": "En ejecución",
            "state": "running"
        }
    ]


@router.get("/summary")
async def get_summary() -> Dict[str, Any]:
    """
    Retorna el resumen de estado del sistema.
    """
    return {
        "applications": 3,
        "apps": 3,
        "total_apps": 3,
        "containers": 4,
        "containers_count": 4,
        "total_containers": 4,
        "routes": 3,
        "persistent_routes": 3,
        "paths": 3,
        "persistent_paths": 3
    }