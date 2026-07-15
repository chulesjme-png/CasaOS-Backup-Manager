"""
Centraliza la creación del cliente Docker.

Toda la aplicación debe obtener el cliente Docker a través de esta clase.
De esta forma, en el futuro podremos sustituir la conexión local por una
conexión remota (SSH, TCP/TLS, etc.) sin modificar los servicios.
"""

from __future__ import annotations

import docker
from docker.client import DockerClient


class DockerClientFactory:
    """
    Fábrica encargada de crear clientes Docker.
    """

    @staticmethod
    def get_client() -> DockerClient | None:
        """
        Devuelve un cliente Docker conectado.

        Si la conexión falla devuelve None.
        """

        try:
            client = docker.from_env()
            client.ping()
            return client

        except Exception:
            return None