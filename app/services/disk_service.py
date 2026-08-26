import os
import shutil
import subprocess
import psutil
from typing import List, Dict, Any

class DiskService:
    def __init__(self):
        pass

    def _get_device_label(self, device_path: str, mountpoint: str) -> str:
        """
        Obtiene el nombre del disco buscando etiquetas del sistema o acortando el UUID.
        """
        folder_name = mountpoint.split("/")[-1] if "/" in mountpoint else mountpoint

        # 1. Intentar obtener etiqueta por udevadm (si está disponible)
        if device_path and device_path != "none" and os.path.exists(device_path):
            try:
                cmd = ["udevadm", "info", "--query=property", "--name=" + device_path]
                output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
                for line in output.splitlines():
                    if line.startswith("ID_FS_LABEL=") or line.startswith("ID_MODEL="):
                        val = line.split("=", 1)[1].strip()
                        if val:
                            return val.replace("_", " ")
            except Exception:
                pass

        # 2. Si es un UUID largo (ej: 08604ab9-10b8-46bc-a6f2...), lo acortamos de forma limpia
        if len(folder_name) > 16 and "-" in folder_name:
            return f"Disco {folder_name[:8]}"

        return folder_name or mountpoint

    def get_disks(self) -> List[Dict[str, Any]]:
        raw_partitions = psutil.disk_partitions(all=True)

        # Detectar cuál es el dispositivo físico raíz ("/") para ignorar todas sus carpetas
        root_device = None
        for p in raw_partitions:
            if p.mountpoint in ["/", "/host"]:
                root_device = p.device
                break

        # Carpetas base del sistema que NUNCA deben mostrarse
        BLACK_LIST_PATHS = {
            "/", "/host", "/DATA", "/media", "/media/devmon", 
            "/media/pichules", "/mnt", "/run/media", "/proc", "/sys", "/dev"
        }

        disks = []
        for part in raw_partitions:
            m = part.mountpoint
            
            # Normalizar ruta montada vía host
            clean_mount = m[5:] if m.startswith("/host") else m
            clean_mount = clean_mount or "/"

            # FILTRO 1: Ignorar carpetas negras explícitas
            if clean_mount in BLACK_LIST_PATHS:
                continue

            # FILTRO 2: Ignorar cualquier montaje que pertenezca al disco del sistema raíz
            if root_device and part.device == root_device:
                continue

            # Ruta real accesible dentro del contenedor
            target_path = part.mountpoint
            if os.path.exists("/host") and not part.mountpoint.startswith("/host"):
                mapped = f"/host{part.mountpoint}"
                if os.path.exists(mapped):
                    target_path = mapped

            try:
                usage = shutil.disk_usage(target_path)
                
                # Descartar particiones virtuales o vacías de 0 bytes
                if usage.total == 0:
                    continue

                display_name = self._get_device_label(part.device, clean_mount)

                disks.append({
                    "device": part.device,
                    "mount": clean_mount,
                    "mountpoint": clean_mount,
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