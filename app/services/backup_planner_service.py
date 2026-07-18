from typing import List

from app.models.application_profile import ApplicationProfile
from app.models.backup_plan import BackupPlan


class BackupPlannerService:
    """
    Servicio encargado de construir los Backup Plans a partir
    de los Application Profiles.

    Este servicio únicamente transforma perfiles en planes de
    backup. No descubre aplicaciones ni genera perfiles.
    """

    def build_plans(
        self,
        application_profiles: List[ApplicationProfile],
    ) -> List[BackupPlan]:
        """
        Construye los planes de backup a partir de los perfiles
        recibidos.
        """

        plans: List[BackupPlan] = []

        for profile in application_profiles:

            warnings = []

            if not profile.backup_sources:
                warnings.append(
                    "No se han detectado rutas para respaldar."
                )

            plans.append(
                BackupPlan(
                    application=profile.application,
                    profile=profile,
                    enabled=profile.enabled,
                    sources=list(profile.backup_sources),
                    estimated_size=0,
                    warnings=warnings,
                    ready=len(warnings) == 0,
                )
            )

        plans.sort(
            key=lambda plan: plan.application.lower()
        )

        return plans