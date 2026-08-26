import os
import shutil
import psutil
from typing import List, Dict, Any

class DiskService:
    def __init__(self):
        pass

    def get_disks(self) -> List[Dict[str, Any]]:
        """
        Obtiene de forma dinámica todos los discos reales del host.
        Filtra puntos de montaje intermedios (ej. /media, /media/usuario, /mnt)
        sin importar el nombre del usuario o la estructura de carpetas.
        """
        disks = []
        raw_partitions = psutil.disk_partitions(all=True)
        
        # Limpiar y normalizar las rutas devueltas por Docker/Host
        clean_mounts = []
        for part in raw_partitions:
            m = part.mountpoint
            if m.startswith("/host"):
                m = m[5:] or "/"
            clean_mounts.append((m, part))

        # Colección de todas las rutas de montaje activas para detectar intermedias
        all_paths = [m[0] for m in clean_mounts]

        for clean_mountpoint, part in clean_mounts:
            # Excluir la raíz del sistema (/), la virtual /proc, etc.
            if clean_mountpoint in ["/", "/proc", "/sys", "/dev"]:
                continue

            # FILTRO DINÁMICO DE CARPETAS INTERMEDIAS:
            # Si existe otro punto de montaje dentro de esta carpeta, es un directorio intermedio.
            # Ej: /media/pichules es intermedia si existe /media/pichules/DISCO_EXTERNO
            is_parent_folder = any(
                other != clean_mountpoint and other.startswith(clean_mountpoint.rstrip("/") + "/")
                for other in all_paths
            )
            if is_parent_folder:
                continue

            # Mapeo de ruta real dentro del contenedor Docker
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