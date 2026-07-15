from __future__ import annotations

from app.services.disk_service import DiskService
from app.services.docker_service import DockerService
from app.services.app_discovery_service import AppDiscoveryService


docker_service = DockerService()
disk_service = DiskService()
app_service = AppDiscoveryService()


def get_docker_status():
    """
    Devuelve el estado general del motor Docker.
    """
    return docker_service.get_status()


def get_disk_usage():
    """
    Devuelve la información de uso del disco.
    """
    return disk_service.get_usage()


def get_services_status():
    """
    Devuelve automáticamente todos los contenedores Docker.
    """
    return docker_service.list_containers()


def get_applications():
    """
    Devuelve todas las aplicaciones Docker Compose detectadas.
    """
    return app_service.list_applications()