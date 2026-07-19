from __future__ import annotations

from app.services.app_discovery_service import AppDiscoveryService
from app.services.application_profile_service import ApplicationProfileService
from app.services.backup_discovery_service import BackupDiscoveryService
from app.services.backup_job_builder_service import BackupJobBuilderService
from app.services.backup_planner_service import BackupPlannerService
from app.services.disk_service import DiskService
from app.services.docker_service import DockerService
from app.services.storage_service import StorageService


class DashboardService:
    """
    Servicio principal del Dashboard.

    Centraliza toda la información mostrada por la interfaz web.

    El Router únicamente debe comunicarse con este servicio.
    """

    def __init__(self) -> None:

        self.docker_service = DockerService()
        self.disk_service = DiskService()
        self.app_service = AppDiscoveryService()
        self.storage_service = StorageService()
        self.backup_service = BackupDiscoveryService()

        # Arquitectura Backup Engine
        self.application_profile_service = ApplicationProfileService()
        self.backup_planner_service = BackupPlannerService()
        self.backup_job_builder_service = BackupJobBuilderService()

    def get_dashboard_data(self) -> dict:
        """
        Devuelve toda la información necesaria para renderizar
        el Dashboard.
        """

        applications = self.app_service.list_applications()

        application_profiles = (
            self.application_profile_service.build_profiles(applications)
        )

        backup_plans = (
            self.backup_planner_service.build_plans(
                application_profiles
            )
        )

        backup_jobs = [
            self.backup_job_builder_service.build(plan)
            for plan in backup_plans
        ]

        return {

            # Estado general de Docker
            "docker": self.docker_service.get_status(),

            # Información técnica del host
            "engine": self.docker_service.get_engine_info(),

            # Disco principal
            "disk": self.disk_service.get_usage(),

            # Aplicaciones Docker Compose
            "applications": applications,

            # Contenedores Docker
            "services": self.docker_service.list_containers(),

            # Dispositivos de almacenamiento
            "storage": self.storage_service.get_storage_devices(),

            # Compatibilidad temporal v0.x
            "backup_sources": self.backup_service.discover_sources(),

            # Application Profiles
            "application_profiles": application_profiles,

            # Backup Plans
            "backup_plans": backup_plans,

            # Backup Engine
            "backup_jobs": backup_jobs,
        }