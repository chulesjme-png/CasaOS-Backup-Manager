from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.application import Application
from app.models.application_profile import ApplicationProfile
from app.models.storage_resource import StorageResource


@dataclass
class BackupJob:
    """
    Trabajo de copia completamente resuelto.

    Este modelo representa una ejecución preparada
    por el Backup Engine.

    Contiene únicamente los recursos que deberán ser
    procesados durante la ejecución.

    No almacena la configuración elegida por el usuario.
    Esa responsabilidad pertenece al BackupPlan y será
    transportada posteriormente mediante
    BackupExecutionRequest.
    """

    application: Application

    profile: ApplicationProfile

    ready: bool = False

    sources: list[StorageResource] = field(
        default_factory=list
    )

    excluded_sources: list[StorageResource] = field(
        default_factory=list
    )

    missing_sources: list[StorageResource] = field(
        default_factory=list
    )

    estimated_size: int = 0

    warnings: list[str] = field(
        default_factory=list
    )

    backend: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )