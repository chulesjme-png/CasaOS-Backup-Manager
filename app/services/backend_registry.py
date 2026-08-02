"""
Registro central de backends de respaldo disponibles.
"""

from typing import Dict, Type, List, Optional
from app.services.duplicati_service import DuplicatiService


class BackendRegistry:
    """Gestor para registrar e instanciar servicios de almacenamiento."""

    _backends: Dict[str, Type] = {
        "duplicati": DuplicatiService,
    }

    @classmethod
    def list_backends(cls) -> List[dict]:
        """Retorna la lista de backends registrados."""
        return [
            {
                "name": name,
                "enabled": True,
                "description": f"Backend {name}",
                "type": name
            }
            for name in cls._backends.keys()
        ]

    @classmethod
    def get_backend(cls, backend_name: str):
        """Retorna la clase del backend solicitado."""
        backend_cls = cls._backends.get(backend_name.lower())
        if not backend_cls:
            return None
        return backend_cls
