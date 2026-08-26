import os
import shutil
import subprocess
import psutil
from typing import List, Dict, Any

class DiskService:
    def __init__(self):
        pass

    def _clean_disk_label(self, mountpoint: str, device: str) -> str:
        """
        Genera un nombre amigable para el disco evitando UUIDs extremadamente largos.
        """
        folder_name = mountpoint.split("/")[-1] if "/" in mountpoint else mountpoint

        # Intentar obtener la etiqueta con lsblk si está disponible el dispositivo
        if device and device != "none":
            try:
                cmd = ["lsblk", "-no", "LABEL", device]
                label = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
                if label:
                    return label
            except Exception:
                pass

        # Si el nombre es un UUID largo (ej: 08604ab9-10b8-46bc...), lo acortamos a algo limpio
        if len(folder_name) > 16 and "-" in folder_name:
            return f"Disco ({folder_name[:8]}...)"

        return folder_name or mountpoint

    def get_disks(self) -> List[Dict[str, Any]]:
        raw_partitions = psutil.disk_partitions(all=True)
        
        # Lista estricta de rutas base/intermedias a descartar por completo
        EXCLUDED_EXACT_PATHS = {
            "/", "/proc", "/sys", "/dev", "/DATA", 
            "/media", "/media/devmon", "/media/pichules", "/mnt", "/run/media"
        }

        clean_mounts = []
        for part in raw_partitions:
            m = part.mountpoint
            if m.startswith("/host"):
                m = m[5:] or "/"
            clean_mounts.append((m, part))

        all_paths = [m[0] for m in clean_mounts]
        disks = []

        for clean_mountpoint, part in clean_mounts:
            # 1. Ignorar carpetas del sistema e intermedias directas
            if clean_mountpoint in EXCLUDED_EXACT_PATHS:
                continue

            # 2. Descartar carpetas intermedias (si existe subdirectorio montado)
            normalized_path = clean_mountpoint.rstrip("/") + "/"
            is_parent = any(
                other != clean_mountpoint and (other + "/").startswith(normalized_path)
                for other in all_paths
            )
            if is_parent:
                continue

            # Mapeo de volumen dentro del contenedor Docker
            target_path = part.mountpoint
            if os.path.exists("/host") and not part.mountpoint.startswith("/host"):
                container_mapped_path = f"/host{part.mountpoint}"
                if os.path.exists(container_mapped_path):
                    target_path = container_mapped_path

            try:
                usage = shutil.disk_usage(target_path)
                display_name = self._clean_disk_label(clean_mountpoint, part.device)

                disks.append({
                    "device": part.device,
                    "mount": clean_mountpoint,
                    "mountpoint": clean_mountpoint,
                    "name": display_name,
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