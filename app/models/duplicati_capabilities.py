from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DuplicatiCapabilities:
    """
    Representa las capacidades detectadas de una instalación Duplicati.

    Este modelo no ejecuta acciones.
    Solamente describe qué funcionalidades están disponibles.
    """

    available: bool

    version: Optional[str] = None

    supports_api: bool = False

    supports_cli: bool = False

    errors: List[str] = field(default_factory=list)