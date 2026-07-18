import json
import subprocess
from pathlib import Path

import psutil

from app.models.storage import StorageDevice


class StorageService:
    """
    Servicio de detección y clasificación
    de almacenamiento.

    Preparado para Backup Engine.
    """

    def get_storage_devices(self):

        devices = []

        physical_devices = self._get_block_devices()

        partitions = psutil.disk_partitions(
            all=False
        )

        for partition in partitions:

            try:

                usage = psutil.disk_usage(
                    partition.mountpoint
                )

            except (
                PermissionError,
                FileNotFoundError
            ):

                continue

            info = self._find_device_info(
                partition.device,
                physical_devices
            )

            device_type = self._detect_type(
                info,
                partition.mountpoint
            )

            backup_supported = (
                device_type
                in [
                    "USB",
                    "NAS",
                    "Local"
                ]
            )

            status = self._get_status(
                usage,
                backup_supported
            )

            storage = StorageDevice(

                name=self._get_name(
                    info,
                    partition.mountpoint
                ),

                device=partition.device,

                model=(info.get("model") or "").strip(),

                serial=info.get("serial") or "",

                transport=info.get("tran") or "",

                mount_point=partition.mountpoint,

                filesystem=partition.fstype,

                total=usage.total,

                used=usage.used,

                free=usage.free,

                percent=usage.percent,

                device_type=device_type,

                removable=(info.get("tran") or "") == "usb",

                available=True,

                backup_supported=backup_supported,

                status=status,

                description=self._description(
                    device_type,
                    backup_supported
                )

            )

            devices.append(storage)

        return sorted(
            devices,
            key=lambda x: x.mount_point
        )

    def _get_block_devices(self):

        try:

            result = subprocess.run(

                [
                    "lsblk",
                    "-J",
                    "-o",
                    "NAME,MODEL,SERIAL,TRAN"
                ],

                capture_output=True,

                text=True,

                check=True
            )

            return json.loads(
                result.stdout
            ).get(
                "blockdevices",
                []
            )

        except Exception:

            return []

    def _find_device_info(
        self,
        device,
        devices
    ):

        name = Path(device).name

        for item in devices:

            if item.get(
                "name"
            ) == name:

                return item

            for child in item.get(
                "children",
                []
            ):

                if child.get(
                    "name"
                ) == name:

                    return item

        return {}

    def _detect_type(
        self,
        info,
        mount
    ):

        if (info.get("tran") or "") == "usb":

            return "USB"

        if mount == "/":

            return "Sistema"

        if (info.get("tran") or "") == "nvme":

            return "Sistema"

        return "Local"

    def _get_name(
        self,
        info,
        mount
    ):

        model = (info.get("model") or "").strip()

        if model:

            return model

        if mount == "/":

            return "Sistema"

        return Path(
            mount
        ).name

    def _get_status(
        self,
        usage,
        backup_supported
    ):

        if not backup_supported:

            return "No recomendado"

        if usage.percent >= 90:

            return "Sin espacio"

        return "Disponible"

    def _description(
        self,
        device_type,
        supported
    ):

        if device_type == "USB":

            return "Destino USB para copias"

        if device_type == "NAS":

            return "Almacenamiento remoto"

        if device_type == "Sistema":

            return "Disco principal del servidor"

        if supported:

            return "Destino local"

        return "No disponible para backup"