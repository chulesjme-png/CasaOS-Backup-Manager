"""
Modelo de configuración de un backup.

Representa la configuración elegida por el usuario para ejecutar
un backup independientemente del backend utilizado.

Complementa a BackupManifest:

- BackupManifest describe QUÉ copiar.
- BackupConfiguration describe CÓMO copiar.

No contiene lógica de negocio.
No conoce implementaciones concretas.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BackupConfiguration:
    """
    Configuración de un trabajo de backup.

    Este modelo contiene únicamente las opciones elegidas por el usuario
    para ejecutar un backup. No incluye información sobre los recursos a
    copiar, ya que esa responsabilidad corresponde a BackupManifest.
    """

    destination_url: str = ""

    description: str = ""

    encryption: Optional[str] = None

    passphrase: Optional[str] = None

    compression: Optional[str] = None

    retention_policy: Optional[str] = None

    schedule: Optional[Dict[str, Any]] = None

    filters: List[Dict[str, Any]] = field(
        default_factory=list
    )

    options: Dict[str, Any] = field(
        default_factory=dict
    )

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    def is_complete(self) -> bool:
        """
        Indica si la configuración contiene la información
        mínima necesaria para ejecutar un backup.
        """

        return bool(self.destination_url)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la configuración en un diccionario serializable.

        No realiza ninguna transformación específica del backend.
        """

        return {
            "destination_url": self.destination_url,
            "description": self.description,
            "encryption": self.encryption,
            "passphrase": self.passphrase,
            "compression": self.compression,
            "retention_policy": self.retention_policy,
            "schedule": self.schedule,
            "filters": list(self.filters),
            "options": dict(self.options),
            "metadata": dict(self.metadata),
        }