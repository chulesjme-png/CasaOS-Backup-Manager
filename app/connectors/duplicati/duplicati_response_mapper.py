"""
Duplicati Response Mapper.

Responsabilidades:

- Adaptar respuestas REST de Duplicati.
- Convertir estructuras REST en modelos del dominio.
- Mantener aislado el Backup Engine de la API REST.

Nunca debe:

- Realizar llamadas HTTP.
- Conocer DuplicatiClient.
- Construir BackupResult.
- Contener lógica de negocio.
"""

from __future__ import annotations

from typing import Any

from app.models.backup_execution_reference import (
    BackupExecutionReference,
)
from app.models.backup_resource_type import (
    BackupResourceType,
)


class DuplicatiResponseMapper:
    """
    Adaptador entre la API REST de Duplicati
    y los modelos del dominio.
    """

    @staticmethod
    def from_create_job_response(
        response: dict[str, Any],
    ) -> BackupExecutionReference:
        """
        Convierte la respuesta REST de creación de un backup
        en una referencia uniforme del dominio.

        Respuesta esperada:

        {
            "ID": "5",
            "Temporary": false
        }
        """

        if "ID" not in response:

            raise ValueError(
                "La respuesta de Duplicati no contiene el campo 'ID'."
            )

        return BackupExecutionReference(
            backend="duplicati",
            resource_type=BackupResourceType.BACKUP,
            resource_id=str(response["ID"]),
            metadata={
                "temporary": response.get(
                    "Temporary",
                    False,
                ),
            },
        )