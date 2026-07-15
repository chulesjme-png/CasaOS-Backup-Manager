"""
Definición de un Host Docker.

Un Host representa un servidor Docker al que la aplicación puede
conectarse, independientemente del método de conexión utilizado.

Por el momento únicamente soportaremos el modo local, pero esta clase
queda preparada para futuras conexiones mediante SSH o TCP/TLS.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HostConfig:
    """
    Configuración de un Host Docker.
    """

    name: str
    connection: str
    host: str | None = None
    port: int | None = None
    username: str | None = None

    @property
    def is_local(self) -> bool:
        """
        Indica si el Host corresponde al Docker local.
        """
        return self.connection == "local"

    @property
    def is_ssh(self) -> bool:
        """
        Indica si el Host utiliza SSH.
        """
        return self.connection == "ssh"

    @property
    def is_tcp(self) -> bool:
        """
        Indica si el Host utiliza TCP/TLS.
        """
        return self.connection == "tcp"