import os
import shutil
import psutil
from typing import List, Dict, Any

class DiskService:
    def __init__(self):
        pass

    def get_disks(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de discos y particiones montadas en el Host.
        Lee directamente el /proc del host para evitar el aislamiento de Docker
        y no confundir la partición raíz del contenedor con los discos físicos.
        """
        mounts_path = "/host/proc/mounts" if os.path.exists("/host/proc/mounts") else "/proc/mounts"
        disks = []
        seen_mounts = set()

        if not os.path.exists(mounts_path):
            # Fallback seguro con psutil si no existe proc montado
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

        # Lectura directa desde el punto de montaje real
        with open(mounts_path, "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 3:
                    continue
                
                device, mountpoint, fstype = parts[0], parts[1], parts[2]

                # Filtrar únicamente discos de almacenamiento real en CasaOS / Host Linux
                if device.startswith("/dev/") or mountpoint.startswith(("/media", "/mnt", "/DATA")):
                    # Excluir sistemas de archivos virtuales y duplicados
                    if mountpoint in seen_mounts or fstype in ("tmpfs", "devtmpfs", "squashfs", "overlay"):
                        continue
                    
                    # Comprobar la ruta accesible desde el contenedor
                    target_path = mountpoint
                    if os.path.exists("/host") and not mountpoint.startswith("/host"):
                        container_mapped_path = f"/host{mountpoint}"
                        if os.path.exists(container_mapped_path):
                            target_path = container_mapped_path

                    try:
                        usage = shutil.disk_usage(target_path)
                        seen_mounts.add(mountpoint)
                        
                        disks.append({
                            "device": device,
                            "mountpoint": mountpoint,
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