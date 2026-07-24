"""
Modelo que representa las capacidades de un backend de backup.

Cada backend informa de las capacidades que soporta para que el
Backup Engine pueda adaptar su comportamiento sin conocer detalles
de implementación.

El modelo es deliberadamente simple y libre de lógica de negocio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BackendCapabilities:
    """
    Capacidades detectadas para un backend.
    """

    backend: str

    version: str = "unknown"

    api_available: bool = False

    can_create_jobs: bool = False

    can_run_backup: bool = False

    can_cancel_backup: bool = False

    can_restore: bool = False

    supports_encryption: bool = False

    supports_compression: bool = False

    supports_retention: bool = False

    supports_scheduling: bool = False

    metadata: dict[str, Any] = field(default_factory=dict)