import os
import shutil
from typing import List, Dict, Any

class DiskService:
    def __init__(self):
        pass

    def _get_disk_labels_map() -> Dict[str, str]:
        """
        Lee /dev/disk/by-label/ del host para mapear /dev/sdX -> Nombre de la etiqueta.
        """
        label_map = {}
        by_label_paths = ["/host/dev/disk/by-label", "/dev/disk/by-label"]
        
        for path in by_label_paths:
            if os.path.exists(path):
                try:
                    for label in os.listdir(path):
                        full_path = os.path.join(path, label)
                        if os.path.islink(full_path):
                            target = os.path.realpath(full_path)
                            if target.startswith("/host"):
                                target = target[5:]
                            clean_label = label.replace("\\x20", " ").replace("_", " ")
                            label_map[target] = clean_label
                except Exception:
                    pass
        return label_map

    def get_disks(self) -> List[Dict[str, Any]]:
        mounts_source = "/host/proc/mounts" if os.path.exists("/host/proc/mounts") else "/proc/mounts"
        
        if not os.path.exists(mounts_source):
            return []

        labels_map = self._get_disk_labels_map()
        disks = []
        seen_mounts = set()
        seen_devices = set()

        # Prefijos de dispositivos de bloques físicos reales (SATA, USB, NVMe, SD)
        PHYSICAL_DEV_PREFIXES = ("/dev/sd", "/dev/nvme", "/dev/mmcblk", "/dev/vd", "/dev/mapper")

        with open(mounts_source, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 3:
                    continue

                device, mountpoint, fstype = parts[0], parts[1], parts[2]

                # 1. Filtro genérico: Solo aceptar dispositivos físicos reales
                if not device.startswith(PHYSICAL_DEV_PREFIXES):
                    continue

                # 2. Ignorar montajes internos del sistema operativo o Docker
                if mountpoint in ("/", "/boot", "/etc", "/var", "/proc", "/sys", "/dev"):
                    continue
                if mountpoint.startswith(("/var/lib/docker", "/proc", "/sys", "/dev", "/run/docker")):
                    continue

                # 3. Solo aceptar puntos de montaje de almacenamiento (/media/..., /mnt/..., /DATA/...)
                if not mountpoint.startswith(("/media", "/mnt", "/run/media", "/DATA")):
                    continue

                # Ignorar carpetas raíz intermedias (/media, /mnt)
                if mountpoint in ("/media", "/mnt", "/run/media"):
                    continue

                if mountpoint in seen_mounts or device in seen_devices:
                    continue

                target_path = f"/host{mountpoint}" if os.path.exists(f"/host{mountpoint}") else mountpoint

                try:
                    usage = shutil.disk_usage(target_path)
                    if usage.total == 0:
                        continue

                    folder_name = mountpoint.split("/")[-1]
                    dev_short = device.split("/")[-1]

                    # Prioridad de nombres: Etiqueta real > Nombre de carpeta simple > Dispositivo
                    if device in labels_map:
                        display_name = labels_map[device]
                    elif not (len(folder_name) > 18 and "-" in folder_name):
                        display_name = folder_name.replace("_", " ")
                    else:
                        display_name = f"Disco USB ({dev_short})"

                    seen_mounts.add(mountpoint)
                    seen_devices.add(device)

                    disks.append({
                        "device": device,
                        "mount": mountpoint,
                        "mountpoint": mountpoint,
                        "name": display_name,
                        "fstype": fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "percent": round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0
                    })
                except (PermissionError, FileNotFoundError, OSError):
                    continue

        return disks

disk_service = DiskService()