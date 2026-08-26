import os
import shutil
import subprocess
import psutil
from typing import List, Dict, Any

class DiskService:
    def __init__(self):
        pass

    def _get_label_from_lsblk(self, device_path: str) -> str:
        """
        Intenta obtener la etiqueta real (LABEL) del dispositivo mediante lsblk.
        """
        try:
            cmd = ["lsblk", "-no", "LABEL,MODEL", device_path]
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
            if output:
                lines = output.splitlines()
                first_line = lines[0].strip()
                # Si hay LABEL lo usamos, si no, probamos con el modelo del disco
                parts = first_line.split()
                if parts:
                    return " ".join(parts)
        except Exception:
            pass
        return ""

    def get_disks(self) -> List[Dict[str, Any]]:
        """
        Obtiene únicamente los discos/particiones externos reales montados,
        obteniendo el nombre formateado de CasaOS y descartando carpetas del sistema.
        """
        raw_partitions = psutil.disk_partitions(all=True)
        
        # 1. Normalizar rutas removiendo prefijos de mapeo contenedor
        clean_mounts = []
        for part in raw_partitions:
            m = part.mountpoint
            if m.startswith("/host"):
                m = m[5:] or "/"
            clean_mounts.append((m, part))

        all_paths = [m[0] for m in clean_mounts]

        disks = []
        for clean_mountpoint, part in clean_mounts:
            # Descartar rutas base del sistema e intermedias conocidas
            if clean_mountpoint in ["/", "/proc", "/sys", "/dev", "/DATA", "/media", "/media/devmon", "/media/pichules", "/mnt"]:
                continue

            # Filtrar carpetas intermedias (si existe otro punto de montaje dentro de esta ruta)
            normalized_path = clean_mountpoint.rstrip("/") + "/"
            is_parent = any(
                other != clean_mountpoint and (other + "/").startswith(normalized_path)
                for other in all_paths
            )
            if is_parent:
                continue

            # Ruta física accesible dentro del contenedor
            target_path = part.mountpoint
            if os.path.exists("/host") and not part.mountpoint.startswith("/host"):
                container_mapped_path = f"/host{part.mountpoint}"
                if os.path.exists(container_mapped_path):
                    target_path = container_mapped_path

            try:
                usage = shutil.disk_usage(target_path)
                
                # Intentar obtener la etiqueta legible del disco (ej: USB3.0, HUH728080ALE601, etc.)
                label = self._get_label_from_lsblk(part.device)
                
                # Si no tiene etiqueta de disco, acortamos la UUID mostrando solo los primeros 8 caracteres
                folder_name = clean_mountpoint.split("/")[-1]
                if not label:
                    if len(folder_name) > 15 and "-" in folder_name:
                        label = f"Disco ({folder_name[:8]}...)"
                    else:
                        label = folder_name

                disks.append({
                    "device": part.device,
                    "mount": clean_mountpoint,
                    "mountpoint": clean_mountpoint,
                    "name": label,
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