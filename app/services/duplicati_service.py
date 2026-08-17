import os
import shutil
import logging
import subprocess
from datetime import datetime
from typing import Optional, List
from app.core.config import config_manager
from app.services.backup_engine_service import backup_engine_service

logger = logging.getLogger("casaos-backup")

class DuplicatiService:
    def __init__(self):
        self.current_process: Optional[subprocess.Popen] = None
        self._is_cancelled: bool = False

    def get_target_disk(self) -> str:
        """Obtiene la ruta del disco de destino configurado, con fallback si está vacío."""
        target_disk = config_manager.config.selected_target_disk
        
        if not target_disk:
            default_disk = "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adfc6fa"
            if os.path.exists(default_disk):
                logger.warning(f"[DuplicatiService] Sin disco en config. Usando ruta por defecto: {default_disk}")
                return default_disk
            raise ValueError("No se ha seleccionado ningún disco de destino en la configuración.")
            
        return target_disk

    def _get_dir_size(self, paths: List[str]) -> int:
        """Calcula el tamaño total acumulado en bytes de las rutas dadas."""
        total_size = 0
        for path in paths:
            if not os.path.exists(path):
                continue
            if os.path.isfile(path):
                total_size += os.path.getsize(path)
            else:
                for root, _, files in os.walk(path):
                    for f in files:
                        fp = os.path.join(root, f)
                        if os.path.exists(fp) and not os.path.islink(fp):
                            try:
                                total_size += os.path.getsize(fp)
                            except Exception:
                                pass
        return total_size

    def cancel_current_backup(self) -> bool:
        """Cancela inmediatamente el proceso de empaquetado en ejecución."""
        self._is_cancelled = True
        if self.current_process and self.current_process.poll() is None:
            try:
                logger.info("[DuplicatiService] Cancelando proceso de copia activo...")
                self.current_process.terminate()
                self.current_process.wait(timeout=5)
            except Exception:
                if self.current_process.poll() is None:
                    self.current_process.kill()
            logger.info("[DuplicatiService] Proceso cancelado correctamente.")
            return True
        return False

    def run_full_disaster_recovery(self) -> bool:
        """Realiza la copia de seguridad completa del sistema (Disaster Recovery)."""
        self._is_cancelled = False
        tmp_file = None
        
        try:
            target_disk = self.get_target_disk()
            dest_dir = os.path.join(target_disk, "Backups", "DisasterRecovery")
            os.makedirs(dest_dir, exist_ok=True)

            source_paths = ["/DATA/AppData", "/var/lib/casaos", "/etc/casaos"]
            existing_sources = [p for p in source_paths if os.path.exists(p)]

            if not existing_sources:
                raise ValueError("Ninguna de las rutas origen de Disaster Recovery existe.")

            # 1. Pre-flight Check: Verificación de espacio disponible + 20% de margen
            required_bytes = int(self._get_dir_size(existing_sources) * 1.2)
            stat = shutil.disk_usage(dest_dir)
            if stat.free < required_bytes:
                free_gb = round(stat.free / (1024**3), 2)
                req_gb = round(required_bytes / (1024**3), 2)
                raise RuntimeError(
                    f"Espacio insuficiente en disco. Libre: {free_gb} GB | Requerido estimado: {req_gb} GB"
                )

            logger.info(f"Iniciando Disaster Recovery en {dest_dir}...")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_tar = os.path.join(dest_dir, f"disaster_recovery_{timestamp}.tar.gz")
            tmp_file = f"{final_tar}.tmp"

            # 2. Comando tar con escritura atómica (.tmp) y flags tolerantes
            cmd = [
                "tar",
                "--warning=no-file-changed",
                "--ignore-failed-read",
                "--exclude=*.log",
                "--exclude=*.tmp",
                "--exclude=*.sock",
                "-czf", tmp_file
            ] + existing_sources

            self.current_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            _, stderr = self.current_process.communicate()
            return_code = self.current_process.returncode

            if self._is_cancelled:
                logger.warning("[DuplicatiService] Operación abortada por el usuario.")
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
                return False

            if return_code in [0, 1]:
                # 3. Test de integridad del archivo generado
                verify_cmd = ["tar", "-tzf", tmp_file]
                verify_res = subprocess.run(verify_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

                if verify_res.returncode != 0:
                    raise RuntimeError("La prueba de integridad del paquete generado ha fallado.")

                # Renombrado atómico a archivo final
                os.rename(tmp_file, final_tar)
                logger.info(f"Disaster Recovery completado y verificado: {os.path.basename(final_tar)}")

                try:
                    backup_engine_service.apply_retention_policy(
                        target_dir=dest_dir,
                        prefix="disaster_recovery",
                        max_copies=2
                    )
                except Exception as ret_err:
                    logger.warning(f"[DuplicatiService] Error aplicando retención en DR: {ret_err}")

                return True
            else:
                raise RuntimeError(f"Error en comando tar: {stderr}")

        except Exception as e:
            logger.error(f"[DuplicatiService] Error en Disaster Recovery: {e}")
            if tmp_file and os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass
            return False
        finally:
            self.current_process = None

    def run_app_backup(self, app_name: str, app_path: str) -> bool:
        """Realiza la copia de seguridad de una aplicación específica."""
        self._is_cancelled = False
        tmp_file = None
        try:
            target_disk = self.get_target_disk()
            dest_dir = os.path.join(target_disk, "Backups", "Apps", app_name)
            os.makedirs(dest_dir, exist_ok=True)

            if not os.path.exists(app_path):
                raise ValueError(f"La ruta de la app no existe: {app_path}")

            # Pre-flight Check para App
            required_bytes = int(self._get_dir_size([app_path]) * 1.2)
            stat = shutil.disk_usage(dest_dir)
            if stat.free < required_bytes:
                raise RuntimeError("Espacio insuficiente en disco para el respaldo de la app.")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_tar = os.path.join(dest_dir, f"{app_name}_backup_{timestamp}.tar.gz")
            tmp_file = f"{final_tar}.tmp"

            cmd = [
                "tar", "--warning=no-file-changed", "--ignore-failed-read",
                "-czf", tmp_file, "-C", app_path, "."
            ]

            self.current_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            _, stderr = self.current_process.communicate()

            if self._is_cancelled:
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
                return False

            if self.current_process.returncode in [0, 1]:
                os.rename(tmp_file, final_tar)
                try:
                    backup_engine_service.apply_retention_policy(
                        target_dir=dest_dir, prefix=app_name, max_copies=3
                    )
                except Exception as ret_err:
                    logger.warning(f"[DuplicatiService] Error retención app {app_name}: {ret_err}")
                return True
            else:
                raise RuntimeError(f"Error empaquetando {app_name}: {stderr}")

        except Exception as e:
            logger.error(f"[DuplicatiService] Error respaldando {app_name}: {e}")
            if tmp_file and os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass
            return False
        finally:
            self.current_process = None

duplicati_service = DuplicatiService()