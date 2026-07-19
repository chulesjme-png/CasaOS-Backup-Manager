from dataclasses import dataclass, field


@dataclass
class ApplicationProfile:
    """
    Perfil de backup de una aplicación.

    Este modelo representa la configuración de backup
    asociada a una aplicación descubierta.

    Un ApplicationProfile describe qué datos deben
    protegerse y servirá como entrada para la generación
    de un BackupPlan.

    En futuras versiones podrá persistirse y editarse
    desde la interfaz web.
    """

    name: str

    application: str

    description: str

    enabled: bool = True

    backup_sources: list[str] = field(default_factory=list)

    tags: list[str] = field(default_factory=list)