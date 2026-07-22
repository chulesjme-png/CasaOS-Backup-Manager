from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class BackendConfiguration:
    """
    Configuración genérica de un backend de backup.

    Este modelo no conoce ningún backend concreto.
    Cada implementación (Duplicati, Restic, Borg, etc.)
    interpretará su propio contenido.
    """

    backend_name: str

    enabled: bool = True

    configuration: Dict[str, Any] = field(default_factory=dict)

    metadata: Dict[str, Any] = field(default_factory=dict)