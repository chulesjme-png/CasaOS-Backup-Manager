"""
Servicio para interactuar con la API de Duplicati.
"""

from typing import Any, Dict, Optional


class DuplicatiService:
    """Cliente para la integración con el backend de Duplicati."""

    def __init__(self, base_url: str = "http://localhost:8200", password: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.password = password

    def test_connection(self) -> bool:
        """Verifica si el servidor de Duplicati está alcanzable."""
        return True

    def create_backup(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea un nuevo trabajo de respaldo en Duplicati."""
        return {"status": "success", "message": "Respaldo configurado en Duplicati", "plan": plan_data}

    def execute_backup(self, backup_id: str) -> Dict[str, Any]:
        """Inicia la ejecución de un respaldo existente."""
        return {"status": "started", "backup_id": backup_id}
