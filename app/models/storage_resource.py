from dataclasses import dataclass
from typing import Optional


@dataclass
class StorageResource:
    """
    Representa un recurso de almacenamiento detectado en una
    aplicación Docker.

    Este modelo describe un punto de almacenamiento susceptible
    de formar parte de un Backup Source.
    """

    application: str

    source: str

    destination: str

    storage_type: str

    backup_candidate: bool = True

    ignore_reason: Optional[str] = None