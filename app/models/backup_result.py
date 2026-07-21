from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class BackupResult:
    """
    Resultado común devuelto por cualquier backend de backup.

    Este modelo representa el resultado final de una ejecución de backup,
    independientemente del motor utilizado (Duplicati, Restic, Borg, Rsync,
    etc.).

    Todos los backends deberán devolver una instancia de BackupResult para
    garantizar una interfaz uniforme dentro del Backup Engine.
    """

    success: bool

    backend: str

    application: str

    started_at: datetime

    finished_at: datetime

    bytes_processed: int = 0

    warnings: List[str] = field(default_factory=list)

    errors: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)