from dataclasses import dataclass


@dataclass
class Container:
    """
    Representa un contenedor Docker dentro del dominio de la
    aplicación.

    Este modelo abstrae la información relevante de un
    contenedor sin depender directamente del SDK de Docker.

    Será utilizado progresivamente por los servicios de
    descubrimiento, planificación y ejecución de copias
    de seguridad.
    """

    container_id: str

    name: str

    image: str

    status: str

    service: str

    project: str