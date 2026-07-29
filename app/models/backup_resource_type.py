"""
Tipos de recursos remotos gestionados por un backend.

Permite identificar de forma tipada el recurso al que hace
referencia una BackupExecutionReference.

No contiene lógica.
"""

from enum import Enum


class BackupResourceType(str, Enum):
    """
    Tipos de recursos soportados por el dominio.
    """

    BACKUP = "backup"

    TASK = "task"