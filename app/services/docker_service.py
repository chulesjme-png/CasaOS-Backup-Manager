from __future__ import annotations

from typing import Any

import docker
from docker.errors import DockerException


class DockerService:
    """
    Servicio encargado de comunicarse con Docker Engine.
    """

    def __init__(self) -> None:
        self.client = self._connect()

    def _connect(self):
        """
        Intenta conectar con Docker Engine.
        """
        try:
            client = docker.from_env()
            client.ping()
            return client

        except Exception:
            return None

    def is_available(self) -> bool:
        return self.client is not None

    def get_status(self) -> dict[str, Any]:
        """
        Devuelve información general del estado de Docker.
        """

        default = {
            "available": False,
            "engine_version": "-",
            "containers_running": 0,
            "containers_stopped": 0,
            "images": 0,
            "volumes": 0,
            "networks": 0,
            "error": "",
        }

        if self.client is None:
            default["error"] = "No se pudo conectar con Docker Engine."
            return default

        try:

            containers = self.client.containers.list(all=True)

            running = sum(
                1
                for container in containers
                if container.status == "running"
            )

            stopped = len(containers) - running

            version = self.client.version().get("Version", "-")

            images = len(self.client.images.list())

            # Compatible con docker-sdk 7.x
            volumes = len(self.client.volumes.list())

            networks = len(self.client.networks.list())

            return {
                "available": True,
                "engine_version": version,
                "containers_running": running,
                "containers_stopped": stopped,
                "images": images,
                "volumes": volumes,
                "networks": networks,
                "error": "",
            }

        except DockerException as e:

            default["error"] = str(e)
            return default

        except Exception as e:

            default["error"] = str(e)
            return default

    def list_containers(self) -> list[dict[str, Any]]:
        """
        Devuelve la lista de contenedores Docker normalizada para la aplicación.
        """

        if self.client is None:
            return []

        try:
            containers = []

            for container in self.client.containers.list(all=True):

                image = container.image.tags[0] if container.image.tags else container.image.short_id

                containers.append(
                    {
                        "id": container.short_id,
                        "name": container.name,
                        "image": image,
                        "status": container.status,
                        "running": container.status == "running",
                        "icon": self._get_container_icon(image),
                        "color": self._get_status_color(container.status),
                    }
                )

            containers.sort(
                key=lambda c: (
                    not c["running"],
                    c["name"].lower(),
                )
            )

            return containers

        except DockerException:
            return []

        except Exception:
            return []

    def _get_status_color(self, status: str) -> str:
        """
        Traduce el estado de Docker a un color de la interfaz.
        """

        status = status.lower()

        if status == "running":
            return "success"

        if status in ("paused", "restarting"):
            return "warning"

        if status in ("dead", "removing"):
            return "danger"

        return "secondary"

    def _get_container_icon(self, image: str) -> str:
        """
        Devuelve un icono lógico según la imagen Docker.
        """

        image = image.lower()

        if "duplicati" in image:
            return "database"

        if "postgres" in image:
            return "database"

        if "mariadb" in image:
            return "database"

        if "mysql" in image:
            return "database"

        if "redis" in image:
            return "database"

        if "immich" in image:
            return "image"

        if "nextcloud" in image:
            return "cloud"

        if "nginx" in image:
            return "globe"

        if "traefik" in image:
            return "globe"

        if "jellyfin" in image:
            return "film"

        if "plex" in image:
            return "film"

        if "navidrome" in image:
            return "music"

        if "adguard" in image:
            return "shield"

        if "vaultwarden" in image:
            return "lock"

        if "homeassistant" in image:
            return "house"

        return "cube"