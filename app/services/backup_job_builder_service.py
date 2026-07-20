from app.models.backup_job import BackupJob
from app.models.backup_plan import BackupPlan


class BackupJobBuilderService:
    """
    Servicio encargado de transformar un BackupPlan en un BackupJob.

    El BackupPlan representa la intención de copia.
    El BackupJob representa un trabajo preparado para ser
    entregado posteriormente a un BackupBackend.

    Este servicio no ejecuta backups y no conoce ningún backend
    concreto (Duplicati, Restic, Borg, Rsync).
    """

    def build(
        self,
        plan: BackupPlan,
    ) -> BackupJob:

        warnings = list(plan.warnings)

        sources = []
        missing_sources = []
        excluded_sources = []

        for resource in plan.resources:

            if not resource.backup_candidate:

                excluded_sources.append(resource)
                continue

            status = resource.validation_status

            if status == "ready":

                sources.append(resource)

            elif status == "empty":

                # Un recurso vacío sigue siendo válido
                sources.append(resource)

            else:

                missing_sources.append(resource)

        ready = (
            plan.enabled
            and plan.ready
            and len(sources) > 0
        )

        return BackupJob(
            application=plan.profile.application,
            profile=plan.profile,
            ready=ready,
            sources=sources,
            excluded_sources=excluded_sources,
            missing_sources=missing_sources,
            estimated_size=plan.estimated_size,
            warnings=warnings,
            metadata={
                "generated_from": "BackupPlan",
                "application": plan.application,
            },
        )