from typing import List, Optional, Tuple

from app.models.backup import BackupSource
from app.models.storage_resource import StorageResource
from app.services.docker_service import DockerService


class BackupDiscoveryService:
    IGNORE_PATHS = {
        "/etc/hosts",
        "/etc/hostname",
        "/etc/resolv.conf",
        "/proc",
        "/sys",
        "/dev",
        "/run",
        "/tmp",
    }

    def __init__(self):
        self.docker_service = DockerService()

    def _should_ignore_mount(
        self,
        source: str,
        destination: str,
    ) -> Tuple[bool, Optional[str]]:
        if destination in self.IGNORE_PATHS:
            return True, "Sistema"

        if "docker.sock" in source or "docker.sock" in destination:
            return True, "Docker Socket"

        return False, None

    def _classify_mount(self, mount_type: str) -> str:
        if mount_type == "bind":
            return "Bind Mount"

        if mount_type == "volume":
            return "Docker Volume"

        return mount_type or "unknown"

    def discover_sources(self) -> List[BackupSource]:
        sources = []

        for container in self.docker_service.list_raw_containers():
            app = (container.labels or {}).get(
                "com.docker.compose.project",
                "standalone",
            )

            for mount in container.attrs.get("Mounts", []):
                source = mount.get("Source")

                if not source:
                    continue

                destination = mount.get("Destination", "")
                mount_type = mount.get("Type", "unknown")

                ignored, reason = self._should_ignore_mount(
                    source,
                    destination,
                )

                resource = StorageResource(
                    app,
                    source,
                    destination,
                    self._classify_mount(mount_type),
                    not ignored,
                    reason,
                )

                sources.append(
                    BackupSource(
                        name=f"{container.name}{destination}",
                        application=app,
                        source_type=resource.storage_type,
                        path=source,
                        container=container.name,
                        size=0,
                        enabled=resource.backup_candidate,
                        description=reason or "Backup Candidate",
                    )
                )

        return sources