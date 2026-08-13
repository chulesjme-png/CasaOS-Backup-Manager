import os
import shutil
import logging
import psutil

logger = logging.getLogger("casaos_backup_manager")

class DiskService:
    """Servicio para gestión y análisis de almacenamiento en el Host y CasaOS."""

    # Sistemas de archivos a ignorar
    IGNORED_FSTYPES = {
        'tmpfs', 'devtmpfs', 'devtmpfs', 'sysfs', 'proc', 'overlay',
        'squashfs', 'cgroup', 'pstore', 'bpf', 'tracefs', 'debugfs', 'mqueue', 'devpts'
    }

    # Puntos de montaje virtuales/del contenedor a ignorar
    IGNORED_PATHS = {
        '/etc/resolv.conf', '/etc/hostname', '/etc/hosts',
        '/dev', '/proc', '/sys', '/run'
    }

    def get_system_disks(self) -> list:
        """
        Obtiene la lista de discos y particiones de almacenamiento reales.
        Filtra archivos de sistema, montajes virtuales y duplicados de Docker.
        """
        disks = []
        seen_mounts = set()
        seen_devices = set()

        try:
            partitions = psutil.disk_partitions(all=True)
            for part in partitions:
                mountpoint = part.mountpoint
                device = part.device
                fstype = part.fstype.lower()

                # Ignorar sistemas de archivos sintéticos/temporales
                if fstype in self.IGNORED_FSTYPES:
                    continue

                # Ignorar rutas virtuales explícitas
                if mountpoint in self.IGNORED_PATHS or any(mountpoint.startswith(p + '/') for p in self.IGNORED_PATHS):
                    continue

                # Ignorar archivos individuales montados como volúmenes
                if os.path.isfile(mountpoint):
                    continue

                # Evitar duplicados por dispositivo o punto de montaje
                if mountpoint in seen_mounts:
                    continue
                
                # Ignorar montajes secundarios genéricos si apuntan al mismo sitio
                if mountpoint in ['/media', '/mnt', '/DATA'] and not os.path.ismount(mountpoint):
                    # Si no es un punto de montaje real dedicado, omitirlo para dar preferencia a los subdirectorios
                    pass

                try:
                    usage = shutil.disk_usage(mountpoint)
                    
                    # Convertir bytes a GB
                    total_gb = round(usage.total / (1024 ** 3), 1)
                    used_gb = round(usage.used / (1024 ** 3), 1)
                    free_gb = round(usage.free / (1024 ** 3), 1)
                    percent = round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0

                    # Si el tamaño total es 0 (ej. pseudo-fs no filtrado), omitir
                    if total_gb == 0:
                        continue

                    # Extraer un nombre legible para el disco
                    if mountpoint == '/':
                        name = "Almacenamiento Raíz (/)"
                    elif mountpoint.startswith('/media/'):
                        parts = mountpoint.strip('/').split('/')
                        label = parts[-1] if len(parts) >= 2 else mountpoint
                        name = f"Disco: {label}"
                    else:
                        name = f"Disco ({mountpoint})"

                    # Agregamos solo montajes únicos con espacio significativo
                    disk_info = {
                        "device": device,
                        "mountpoint": mountpoint,
                        "name": f"{name} ({mountpoint})",
                        "label": name,
                        "total_gb": total_gb,
                        "used_gb": used_gb,
                        "free_gb": free_gb,
                        "percent": percent,
                        "fstype": part.fstype
                    }

                    # Evitar duplicar dispositivos montados exactamente con el mismo tamaño y uso
                    dev_key = f"{total_gb}-{used_gb}"
                    if dev_key in seen_devices and mountpoint in ['/DATA', '/media', '/mnt']:
                        continue

                    seen_mounts.add(mountpoint)
                    seen_devices.add(dev_key)
                    disks.append(disk_info)

                except PermissionError:
                    continue
                except Exception as e:
                    logger.warning(f"Error leyendo uso de disco en {mountpoint}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error al obtener particiones del sistema: {e}")

        # Ordenar por tamaño total (de mayor a menor)
        disks.sort(key=lambda x: x['total_gb'], reverse=True)
        return disks

    def get_disk_by_path(self, path: str) -> dict:
        """Obtiene la información de disco correspondiente a una ruta específica."""
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