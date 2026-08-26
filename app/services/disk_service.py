import os
import shutil
import psutil
from typing import List, Dict, Any

class DiskService:
    def __init__(self):
        pass

    def get_disks(self) -> List[Dict[str, Any]]:
        """
        Obtiene únicamente los puntos de montaje reales y finales.
        Filtra recursivamente cualquier carpeta o ruta intermedia.
        """
        raw_partitions = psutil.disk_partitions(all=True)
        
        # 1. Normalizar las rutas limpiando prefijos de Docker si existen
        clean_mounts = []
        for part in raw_partitions:
            m = part.mountpoint
            if m.startswith("/host"):
                m = m[5:] or "/"
            clean_mounts.append((m, part))

        # 2. Extraer todas las rutas de montaje disponibles
        all_paths = [m[0] for m in clean_mounts]

        disks = []
        for clean_mountpoint, part in clean_mounts:
            # Excluir rutas de sistema operativo base
            if clean_mountpoint in ["/", "/proc", "/sys", "/dev"]:
                continue

            # FILTRADO RECURSIVO AVANZADO:
            # Si clean_mountpoint es prefijo de CUALQUIER otra ruta en la lista, es un directorio padre/intermedio.
            normalized_path = clean_mountpoint.rstrip("/") + "/"
            is_parent = any(
                other != clean_mountpoint and (other + "/").startswith(normalized_path)
                for other in all_paths
            )

            if is_parent:
                continue

            # Mapeo dentro del contenedor Docker
            target_path = part.mountpoint
            if os.path.exists("/host") and not part.mountpoint.startswith("/host"):
                container_mapped_path = f"/host{part.mountpoint}"
                if os.path.exists(container_mapped_path):
                    target_path = container_mapped_path

            try:
                usage = shutil.disk_usage(target_path)
                display_name = clean_mountpoint.split("/")[-1] if "/" in clean_mountpoint else clean_mountpoint

                disks.append({
                    "device": part.device,
                    "mount": clean_mountpoint,
                    "mountpoint": clean_mountpoint,
                    "name": display_name or clean_mountpoint,
                    "fstype": part.fstype,
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