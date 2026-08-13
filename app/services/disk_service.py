import os
import shutil
import psutil
from typing import List, Dict

class DiskService:
    @staticmethod
    def bytes_to_gb(b: int) -> float:
        return round(b / (1024 ** 3), 1)

    def get_system_disks(self) -> List[Dict[str, str]]:
        disks = []
        seen_paths = set()

        # Puntos de montaje habituales en CasaOS / Debian
        candidate_mounts = ["/DATA", "/media", "/mnt", "/"]

        # Escaneo de particiones activas en el sistema
        for partition in psutil.disk_partitions(all=False):
            mountpoint = partition.mountpoint
            
            # Filtrar solo montajes relevantes para almacenamiento
            if any(mountpoint.startswith(prefix) for prefix in candidate_mounts):
                if mountpoint in seen_paths or "docker" in mountpoint:
                    continue
                
                try:
                    usage = shutil.disk_usage(mountpoint)
                    free_gb = self.bytes_to_gb(usage.free)
                    total_gb = self.bytes_to_gb(usage.total)
                    
                    # Generar etiqueta amigable
                    disk_name = os.path.basename(mountpoint) or "Sistema Base"
                    label = f"Disco: {disk_name} ({mountpoint})"
                    
                    disks.append({
                        "name": label,
                        "path": mountpoint,
                        "free": f"{free_gb} GB",
                        "total": f"{total_gb} GB",
                        "free_bytes": usage.free,
                        "total_bytes": usage.total
                    })
                    seen_paths.add(mountpoint)
                except PermissionError:
                    continue

        return disks

disk_service = DiskService()