import os
import shutil
import logging
import psutil

logger = logging.getLogger("casaos_backup_manager")

class DiskService:
    """Servicio de detección de discos compatible con entornos Docker y Host."""

    IGNORED_FSTYPES = {
        'tmpfs', 'devtmpfs', 'sysfs', 'proc', 'overlay', 'squashfs', 
        'cgroup', 'pstore', 'bpf', 'tracefs', 'debugfs', 'mqueue', 'devpts', 'ecryptfs'
    }

    IGNORED_PATHS = {
        '/etc/resolv.conf', '/etc/hostname', '/etc/hosts',
        '/dev', '/proc', '/sys', '/run'
    }

    def get_system_disks(self) -> list:
        disks = []
        seen_devices = set()

        try:
            # Inspeccionar particiones montadas en el sistema
            partitions = psutil.disk_partitions(all=True)
            
            for part in partitions:
                mountpoint = part.mountpoint
                device = part.device
                fstype = part.fstype.lower()

                if fstype in self.IGNORED_FSTYPES:
                    continue

                if mountpoint in self.IGNORED_PATHS or any(mountpoint.startswith(p + '/') for p in self.IGNORED_PATHS):
                    continue

                if os.path.isfile(mountpoint):
                    continue

                try:
                    # Deduplicación por ID de dispositivo del Kernel
                    stat_info = os.stat(mountpoint)
                    dev_id = stat_info.st_dev

                    if dev_id in seen_devices:
                        continue

                    usage = shutil.disk_usage(mountpoint)
                    total_gb = round(usage.total / (1024 ** 3), 1)
                    used_gb = round(usage.used / (1024 ** 3), 1)
                    free_gb = round(usage.free / (1024 ** 3), 1)
                    percent = round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0

                    if total_gb == 0:
                        continue

                    # Etiquetado descriptivo
                    if mountpoint == '/':
                        name = "Almacenamiento Raíz (/)"
                    elif mountpoint.startswith('/media/'):
                        parts = mountpoint.strip('/').split('/')
                        label = parts[-1] if len(parts) >= 2 else mountpoint
                        name = f"Disco: {label}"
                    else:
                        name = f"Disco ({mountpoint})"

                    seen_devices.add(dev_id)
                    disks.append({
                        "device": device,
                        "mountpoint": mountpoint,
                        "name": f"{name} ({mountpoint})",
                        "label": name,
                        "total_gb": total_gb,
                        "used_gb": used_gb,
                        "free_gb": free_gb,
                        "percent": percent,
                        "fstype": part.fstype
                    })

                except (PermissionError, FileNotFoundError):
                    continue
                except Exception as e:
                    logger.warning(f"Error analizando {mountpoint}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error al obtener discos del sistema: {e}")

        disks.sort(key=lambda x: x['total_gb'], reverse=True)
        return disks

    def get_disk_by_path(self, path: str) -> dict:
        try:
            usage = shutil.disk_usage(path)
            return {
                "total_gb": round(usage.total / (1024 ** 3), 1),
                "used_gb": round(usage.used / (1024 ** 3), 1),
                "free_gb": round(usage.free / (1024 ** 3), 1),
                "percent": round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error obteniendo uso de disco para {path}: {e}")
            return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0}

disk_service = DiskService()