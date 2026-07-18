from __future__ import annotations

from typing import Any

from docker.errors import DockerException

from app.core.docker_client import DockerClientFactory


class DockerService:
    """
    Servicio encargado de comunicarse con Docker Engine.
    """

    def __init__(self) -> None:
        self._client = DockerClientFactory.get_client()

    @property
    def client(self):
        """
        Expone el cliente Docker en modo solo lectura.

        Este acceso se mantiene por compatibilidad durante la transición.
        En futuras entregas los servicios dejarán de acceder directamente
        al cliente Docker.
        """
        return self._client

    def is_available(self) -> bool:
        return self._client is not None

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

        if self._client is None:
            default["error"] = "No se pudo conectar con Docker Engine."
            return default

        try:

            containers = self._client.containers.list(all=True)

            running = sum(
                1
                for container in containers
                if container.status == "running"
            )

            stopped = len(containers) - running

            version = self._client.version().get("Version", "-")

            images = len(self._client.images.list())

            volumes = len(self._client.volumes.list())

            networks = len(self._client.networks.list())

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

    def get_engine_info(self) -> dict[str, Any]:
        """
        Devuelve información técnica del motor Docker y del host.

        Este método está pensado para enriquecer el Dashboard con
        información del servidor sin mezclarla con get_status().
        """

        default = {
            "server_version": "-",
            "api_version": "-",
            "operating_system": "-",
            "os_type": "-",
            "architecture": "-",
            "kernel_version": "-",
            "hostname": "-",
            "cpus": 0,
            "memory_gb": 0,
            "docker_root_dir": "-",
            "error": "",
        }

        if self._client is None:
            default["error"] = "No se pudo conectar con Docker Engine."
            return default

        try:

            info = self._client.info()
            version = self._client.version()

            return {
                "server_version": version.get("Version", "-"),
                "api_version": version.get("ApiVersion", "-"),
                "operating_system": info.get("OperatingSystem", "-"),
                "os_type": info.get("OSType", "-"),
                "architecture": info.get("Architecture", "-"),
                "kernel_version": info.get("KernelVersion", "-"),
                "hostname": info.get("Name", "-"),
                "cpus": info.get("NCPU", 0),
                "memory_gb": round(info.get("MemTotal", 0) / 1024**3, 2),
                "docker_root_dir": info.get("DockerRootDir", "-"),
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

        if self._client is None:
            return []

        try:
            containers = []

            for container in self._client.containers.list(all=True):

                image = (
                    container.image.tags[0]
                    if container.image.tags
                    else container.image.short_id
                )

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

    def list_raw_containers(self):
        """
        Devuelve los objetos Container del SDK Docker.

        Este método será el único punto de acceso al cliente Docker para el
        resto de servicios. De esta forma evitamos que conozcan la estructura
        interna del cliente.
        """

        if self._client is None:
            return []

        try:
            return self._client.containers.list(all=True)

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