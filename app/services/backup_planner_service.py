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

            ready = True

            if not any(
                resource.backup_candidate
                for resource in resources
            ):

                warnings.append(
                    "No se han detectado recursos válidos para respaldar."
                )

                ready = False

            estimated_size = 0

            for resource in resources:

                if not resource.backup_candidate:
                    continue

                status = resource.validation_status

                if status == "ready":

                    estimated_size += resource.size

                elif status == "empty":

                    warnings.append(
                        f"{resource.source}: recurso vacío."
                    )

                elif status == "missing":

                    warnings.append(
                        f"{resource.source}: ruta inexistente."
                    )

                    ready = False

                elif status == "unreadable":

                    warnings.append(
                        f"{resource.source}: permiso insuficiente de lectura."
                    )

                    ready = False

                elif status == "error":

                    warnings.append(
                        f"{resource.source}: error durante la validación."
                    )

                    ready = False

                elif status == "unknown":

                    warnings.append(
                        f"{resource.source}: recurso sin validar."
                    )

                    ready = False

                for error in resource.validation_errors:

                    warning = (
                        f"{resource.source}: {error}"
                    )

                    if warning not in warnings:
                        warnings.append(warning)

            plans.append(
                BackupPlan(
                    application=profile.application,
                    profile=profile,
                    enabled=profile.enabled,
                    resources=resources,
                    estimated_size=estimated_size,
                    warnings=warnings,
                    ready=ready,
                )
            )

        plans.sort(
            key=lambda plan: plan.application.lower()
        )

        return plans