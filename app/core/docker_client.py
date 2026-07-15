"""
Centraliza la creación del cliente Docker.

La factoría selecciona automáticamente el conector adecuado en función
de la configuración del Host.
"""

from __future__ import annotations

from docker.client import DockerClient

from app.config.settings import DEFAULT_HOST
from app.core.docker_local import LocalDockerConnector
from app.core.docker_ssh import SSHDockerConnector


class DockerClientFactory:
    """
    Fábrica encargada de crear clientes Docker.
    """

    @staticmethod
    def get_client() -> DockerClient | None:
        """
        Devuelve un cliente Docker según la configuración del Host.
        """

        if DEFAULT_HOST.is_local:
            return LocalDockerConnector().get_client()

        if DEFAULT_HOST.is_ssh:
            return SSHDockerConnector(DEFAULT_HOST).get_client()

        if DEFAULT_HOST.is_tcp:
            raise NotImplementedError(
                "La conexión TCP/TLS se implementará en una entrega futura."
            )

        return None