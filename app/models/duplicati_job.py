"""
Modelo interno de un trabajo de Duplicati.

Representa la definición de un trabajo de backup de Duplicati
independientemente de cómo se comunique con la API HTTP.

Este modelo es construido por DuplicatiJobBuilder y consumido por
DuplicatiBackend.

No contiene lógica de negocio.
No conoce HTTP.
No conoce Docker.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DuplicatiJob:
    """
    Definición de un trabajo de Duplicati.
    """

    name: str

    source_paths: List[str]

    destination_url: str

    description: str = ""

    encryption: Optional[str] = None

    passphrase: Optional[str] = None

    compression: Optional[str] = None

    retention_policy: Optional[str] = None

    schedule: Optional[Dict[str, Any]] = None

    options: Dict[str, Any] = field(
        default_factory=dict
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def to_payload(self) -> Dict[str, Any]:
        """
        Convierte el modelo en una estructura serializable.

        No realiza ninguna transformación específica de API.
        La adaptación final a Duplicati se realizará en la capa
        correspondiente.
        """

        return {
            "name": self.name,

            "source_paths": list(
                self.source_paths
            ),

            "destination_url": (
                self.destination_url
            ),

            "description": (
                self.description
            ),

            "encryption": (
                self.encryption
            ),

            "passphrase": (
                self.passphrase
            ),

            "compression": (
                self.compression
            ),

            "retention_policy": (
                self.retention_policy
            ),

            "schedule": (
                self.schedule
            ),

            "options": dict(
                self.options
            ),

            "metadata": dict(
                self.metadata
            ),
        }