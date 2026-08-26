import os
import shutil
import subprocess
from typing import List, Dict, Any

class DiskService:
    def __init__(self):
        pass

    def _get_device_label(self, device_path: str, mountpoint: str) -> str:
        folder_name = mountpoint.split("/")[-1] if "/" in mountpoint else mountpoint

        if device_path and device_path.startswith("/dev/"):
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

        if len(folder_name) > 16 and "-" in folder_name:
            return f"Disco {folder_name[:8]}"

        return folder_name or mountpoint

    def get_disks(self) -> List[Dict[str, Any]]:
        mounts_source = "/host/proc/mounts" if os.path.exists("/host/proc/mounts") else "/proc/mounts"
        
        if not os.path.exists(mounts_source):
            return []

        VALID_PREFIXES = ("/media/pichules/", "/mnt/", "/run/media/")

        disks = []
        seen_mounts = set()

        with open(mounts_source, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 3:
                    continue

                device, mountpoint, fstype = parts[0], parts[1], parts[2]

                # Filtro estricto: Debe comenzar con uno de los prefijos válidos
                if not any(mountpoint.startswith(prefix) for prefix in VALID_PREFIXES):
                    continue

                # Evitar mostrar directorios de montaje raíz (como /media/pichules directamente)
                if mountpoint in ("/media/pichules", "/mnt", "/run/media"):
                    continue

                if mountpoint in seen_mounts:
                    continue
                seen_mounts.add(mountpoint)

                target_path = f"/host{mountpoint}" if os.path.exists(f"/host{mountpoint}") else mountpoint

                try:
                    usage = shutil.disk_usage(target_path)
                    
                    if usage.total == 0:
                        continue

                    display_name = self._get_device_label(device, mountpoint)

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