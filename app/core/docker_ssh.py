"""
Conector para Docker remoto mediante SSH.

Actualmente esta clase prepara la infraestructura necesaria para soportar
conexiones SSH en futuras entregas sin modificar el comportamiento de la
aplicación.
"""

from __future__ import annotations

from docker.client import DockerClient

from app.core.host import HostConfig


class SSHDockerConnector:
    """
    Conector para Docker remoto mediante SSH.
    """

    def __init__(self, host: HostConfig):
        self.host = host

    def get_client(self) -> DockerClient:
        """
        Devuelve un cliente Docker remoto.

        La implementación real se incorporará en la siguiente entrega.
        """

        raise NotImplementedError(
            "La conexión SSH se implementará en la Entrega 4.3.3."
        )