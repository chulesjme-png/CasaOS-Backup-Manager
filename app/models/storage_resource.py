from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StorageResource:
    """
    Representa un recurso de almacenamiento detectado en una
    aplicación Docker.

    Mantiene la ruta original del host y la ruta utilizada
    para validación dentro del contexto disponible.
    """

    application: str

    source: str

    destination: str

    storage_type: str

    backup_candidate: bool = True

    ignore_reason: Optional[str] = None

    # Ruta utilizada para validar el recurso.
    #
    # En entornos Docker normalmente será la ruta interna
    # del contenedor (destination).
    validation_path: Optional[str] = None

    # Estado de validación

    exists: bool = False

    readable: bool = False

    size: int = 0

    validation_errors: list[str] = field(
        default_factory=list
    )

    # Estado resumido de la validación.
    #
    # Valores posibles:
    #   - unknown
    #   - ready
    #   - missing
    #   - unreadable
    #   - empty
    #   - error
    validation_status: str = "unknown"