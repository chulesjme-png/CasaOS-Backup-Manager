from dataclasses import dataclass


@dataclass
class BackupSource:
    """
    Representa un origen de datos
    que puede ser incluido en un backup.

    Será utilizado por:
    - Backup Discovery
    - Backup Engine
    - Restore Engine
    """


    name: str

    application: str

    source_type: str

    path: str

    container: str

    size: int

    enabled: bool

    description: str
