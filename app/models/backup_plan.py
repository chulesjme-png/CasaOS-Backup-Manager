from dataclasses import dataclass, field

from app.models.application_profile import ApplicationProfile
from app.models.storage_resource import StorageResource


@dataclass
class BackupPlan:
    """
    Plan de copia generado para una aplicación.

    Representa el resultado de transformar un
    ApplicationProfile en un plan preparado para
    construir posteriormente un BackupJob.
    """

    application: str

    profile: ApplicationProfile

    enabled: bool = True

    resources: list[StorageResource] = field(default_factory=list)

    estimated_size: int = 0

    warnings: list[str] = field(default_factory=list)

    ready: bool = False