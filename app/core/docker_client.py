"""
Centraliza la creación del cliente Docker.

Toda la aplicación debe obtener el cliente Docker a través de esta clase.
La decisión de cómo conectar (local, SSH, TCP/TLS...) se toma en función
de la configuración del Host.
"""

from __future__ import annotations

import docker
from docker.client import DockerClient

from app.config.settings import DEFAULT_HOST


class DockerClientFactory:
    """
    Fábrica encargada de crear clientes Docker.
    """

    @staticmethod
    def get_client() -> DockerClient | None:
        """
        Devuelve un cliente Docker según la configuración del Host.

        Actualmente solo está implementada la conexión local.
        La infraestructura queda preparada para incorporar SSH y TCP/TLS
        sin modificar el resto de la aplicación.
        """

        if DEFAULT_HOST.is_local:
            return DockerClientFactory._create_local_client()

        if DEFAULT_HOST.is_ssh:
            raise NotImplementedError(
                "La conexión SSH se implementará en la Entrega 4.3."
            )

        if DEFAULT_HOST.is_tcp:
            raise NotImplementedError(
                "La conexión TCP/TLS se implementará en una entrega futura."
            )

        return None

    @staticmethod
    def _create_local_client() -> DockerClient | None:
        """
        Crea un cliente Docker conectado al Docker Engine local.
        """

        try:
            client = docker.from_env()
            client.ping()
            return client

        except Exception:
            return None