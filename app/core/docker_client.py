"""
Centraliza la creación del cliente Docker.

La factoría selecciona automáticamente el conector adecuado en función
de la configuración del Host.
"""

from __future__ import annotations

from docker.client import DockerClient

from app.config.settings import DEFAULT_HOST
from app.core.docker_local import LocalDockerConnector


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
            connector = LocalDockerConnector()
            return connector.get_client()

        if DEFAULT_HOST.is_ssh:
            raise NotImplementedError(
                "La conexión SSH se implementará en la Entrega 4.3.2."
            )

        if DEFAULT_HOST.is_tcp:
            raise NotImplementedError(
                "La conexión TCP/TLS se implementará en una entrega futura."
            )

        return None