import os
import shutil
import psutil
from typing import List, Dict, Any

class DiskService:
    def __init__(self):
        pass

    def get_disks(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de discos y particiones montadas reales en el Host.
        Filtra puntos de montaje intermedios (/media, /mnt, /media/user) y
        deja únicamente los discos físicos de almacenamiento real.
        """
        mounts_path = "/host/proc/mounts" if os.path.exists("/host/proc/mounts") else "/proc/mounts"
        disks = []
        seen_mounts = set()

        if not os.path.exists(mounts_path):
            # Fallback psutil
            for part in psutil.disk_partitions(all=False):
                if part.mountpoint in seen_mounts:
                    continue
                seen_mounts.add(part.mountpoint)
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks.append({
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent
                    })
                except PermissionError:
                    continue
            return disks

        # Rutas intermedias que NO son discos finales y deben ignorarse
        ignored_exact_mounts = {"/", "/media", "/mnt", "/devmon", "/media/devmon", "/media/pichules"}

        with open(mounts_path, "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 3:
                    continue
                
                device, mountpoint, fstype = parts[0], parts[1], parts[2]

                # Filtrar solo dispositivos reales o rutas de datos/medios
                if device.startswith("/dev/") or mountpoint.startswith(("/media", "/mnt", "/DATA")):
                    # Excluir sistemas virtuales, duplicados o carpetas intermedias
                    if mountpoint in seen_mounts or fstype in ("tmpfs", "devtmpfs", "squashfs", "overlay", "proc", "sysfs"):
                        continue

                    if mountpoint in ignored_exact_mounts and mountpoint != "/DATA":
                        continue

                    # Determinar si es un disco real (ejemplo: /DATA o subcarpetas directas de /media/pichules/...)
                    # Si está en /media/pichules/xxx o /media/xxx, validamos que no sea la carpeta padre pichules
                    target_path = mountpoint
                    if os.path.exists("/host") and not mountpoint.startswith("/host"):
                        container_mapped_path = f"/host{mountpoint}"
                        if os.path.exists(container_mapped_path):
                            target_path = container_mapped_path

                    try:
                        usage = shutil.disk_usage(target_path)
                        seen_mounts.add(mountpoint)
                        
                        # Extraer un nombre amigable para el selector UI
                        display_name = mountpoint
                        if "/" in mountpoint:
                            parts_path = [p for p in mountpoint.split("/") if p]
                            if len(parts_path) >= 1:
                                display_name = parts_path[-1]

                        disks.append({
                            "device": device,
                            "mountpoint": mountpoint,
                            "name": display_name,
                            "fstype": fstype,
                            "total": usage.total,
                            "used": usage.used,
                            "free": usage.free,
                            "percent": round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0
                        })
                    except (PermissionError, FileNotFoundError, OSError):
                        continue

        return disks

disk_service = DiskService()