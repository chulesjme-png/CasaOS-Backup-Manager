from dataclasses import dataclass, field

from app.models.application_profile import ApplicationProfile
from app.models.backup_configuration import BackupConfiguration
from app.models.storage_resource import StorageResource


@dataclass
class BackupPlan:
    """
    Plan de copia generado para una aplicación.

    Representa la definición completa de una copia
    de seguridad preparada para una aplicación.

    Contiene dos bloques claramente diferenciados:

    - Qué copiar.
    - Cómo copiar.

    A partir de este modelo se construirá posteriormente
    un BackupJob para una ejecución concreta.
    """

    application: str

    profile: ApplicationProfile

    enabled: bool = True

    resources: list[StorageResource] = field(
        default_factory=list
    )

    estimated_size: int = 0

    warnings: list[str] = field(
        default_factory=list
    )

    ready: bool = False

    backup_configuration: BackupConfiguration = field(
        default_factory=BackupConfiguration
    )