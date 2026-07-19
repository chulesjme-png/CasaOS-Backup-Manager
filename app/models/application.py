from dataclasses import dataclass


@dataclass
class Application:
    """
    Representa una aplicación descubierta en el host.

    Actualmente una aplicación corresponde a un proyecto
    Docker Compose detectado por AppDiscoveryService.

    Este modelo constituye el contrato del dominio entre
    el descubrimiento de aplicaciones y el resto del
    Backup Engine.

    En futuras versiones podrá incorporar información
    adicional como:

    - mounts
    - volumes
    - networks
    - labels
    - compose_file
    - compose_version
    """

    name: str

    containers: int

    status: str