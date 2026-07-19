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

        Devuelve información de cada aplicación incluyendo
        los recursos de almacenamiento detectados.
        """

        containers = self.docker.list_raw_containers()

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
                container.status == "running"
                for container in project_containers
            )

            mounts = []

            for container in project_containers:

                for mount in container.attrs.get(
                    "Mounts",
                    [],
                ):

                    mounts.append(
                        {
                            "source": mount.get("Source", ""),
                            "destination": mount.get("Destination", ""),
                            "type": mount.get("Type", "bind"),
                        }
                    )

            applications.append(
                {
                    "name": project,
                    "containers": len(project_containers),
                    "status": "running" if running else "stopped",
                    "mounts": mounts,
                }
            )

        applications.sort(
            key=lambda app: app["name"].lower()
        )

        return applications