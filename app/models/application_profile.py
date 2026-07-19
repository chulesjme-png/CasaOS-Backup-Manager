from dataclasses import dataclass, field

from app.models.storage_resource import StorageResource


@dataclass
class ApplicationProfile:
    """
    Perfil de backup asociado a una aplicación.

    Describe la configuración necesaria para construir
    un BackupPlan a partir de los recursos detectados.
    """

    name: str

    application: str

    description: str

    enabled: bool = True

    resources: list[StorageResource] = field(default_factory=list)

    tags: list[str] = field(default_factory=list)