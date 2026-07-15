from __future__ import annotations

from collections import defaultdict

from app.services.docker_service import DockerService


class AppDiscoveryService:
    """
    Descubre automáticamente las aplicaciones Docker Compose
    instaladas en el sistema.
    """

    def __init__(self):
        self.docker = DockerService()

    def list_applications(self):
        """
        Agrupa los contenedores por proyecto Docker Compose.

        Devuelve una lista con la información de cada aplicación.
        """

        containers = self.docker.client.containers.list(all=True)

        projects = defaultdict(list)

        for container in containers:

            project = container.labels.get(
                "com.docker.compose.project",
                "Sin proyecto",
            )

            projects[project].append(container)

        applications = []

        for project, project_containers in projects.items():

            running = all(
                c.status == "running"
                for c in project_containers
            )

            applications.append(
                {
                    "name": project,
                    "containers": len(project_containers),
                    "status": "running" if running else "stopped",
                }
            )

        return sorted(
            applications,
            key=lambda app: app["name"].lower(),
        )