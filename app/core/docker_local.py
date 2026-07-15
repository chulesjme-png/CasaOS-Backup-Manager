"""
Conector para Docker Engine local.

Esta clase encapsula toda la lógica necesaria para establecer una conexión
con el Docker Engine local utilizando el SDK oficial de Docker.
"""

from __future__ import annotations

import docker
from docker.client import DockerClient


class LocalDockerConnector:
    """
    Gestiona la conexión con el Docker Engine local.
    """

    def get_client(self) -> DockerClient | None:
        """
        Devuelve un cliente Docker conectado al Docker Engine local.

        Si la conexión falla devuelve None.
        """

        try:
            client = docker.from_env()
            client.ping()
            return client

        except Exception:
            return None