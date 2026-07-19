from typing import List

from app.models.application_profile import ApplicationProfile
from app.models.backup_plan import BackupPlan

from app.services.storage_validation_service import (
    StorageValidationService,
)


class BackupPlannerService:
    """
    Servicio encargado de construir los Backup Plans a partir
    de los Application Profiles.

    Antes de generar el plan valida los recursos detectados.
    """

    def __init__(self):

        self._storage_validator = (
            StorageValidationService()
        )


    def build_plans(
        self,
        application_profiles: List[ApplicationProfile],
    ) -> List[BackupPlan]:

        plans: List[BackupPlan] = []


        for profile in application_profiles:


            resources = (
                self._storage_validator.validate(
                    profile.resources
                )
            )


            warnings = []


            if not any(
                resource.backup_candidate
                for resource in resources
            ):

                warnings.append(
                    "No se han detectado recursos válidos para respaldar."
                )


            for resource in resources:

                for error in resource.validation_errors:

                    warnings.append(
                        f"{resource.source}: {error}"
                    )


            estimated_size = sum(
                resource.size
                for resource in resources
                if resource.backup_candidate
            )


            plans.append(
                BackupPlan(
                    application=profile.application,
                    profile=profile,
                    enabled=profile.enabled,
                    resources=resources,
                    estimated_size=estimated_size,
                    warnings=warnings,
                    ready=len(warnings) == 0,
                )
            )


        plans.sort(
            key=lambda plan: plan.application.lower()
        )


        return plans