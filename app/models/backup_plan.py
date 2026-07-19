from __future__ import annotations

from dataclasses import dataclass, field

from app.models.application_profile import ApplicationProfile


@dataclass
class BackupPlan:
    """
    Plan de copia generado para una aplicación.

    Este modelo representa el resultado de procesar un
    ApplicationProfile.

    Su finalidad es describir qué debe respaldarse, sin entrar
    todavía en la resolución física de los recursos ni depender
    de ningún backend de ejecución.
    """

    application: str

    profile: ApplicationProfile

    enabled: bool = True

    sources: list[str] = field(default_factory=list)

    estimated_size: int = 0

    warnings: list[str] = field(default_factory=list)

    ready: bool = False