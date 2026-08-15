import os
import logging
import subprocess
import asyncio
from datetime import datetime
from app.core.config import config_manager
from app.services.backup_engine_service import backup_engine_service

logger = logging.getLogger("casaos-backup")

class DuplicatiService:
    def __init__(self):
        pass

    def get_target_disk(self) -> str:
        """Obtiene la ruta del disco de destino configurado, con fallback si está vacío."""
        target_disk = config_manager.config.selected_target_disk
        
        # Fallback inteligente si no hay nada guardado en la configuración
        if not target_disk:
            default_disk = "/media/pichules/08604ab9-10b8-46bc-a6f2-a19f3adfc6fa"
            if os.path.exists(default_disk):
                logger.warning(f"[DuplicatiService] Sin disco en config. Usando ruta por defecto: {default_disk}")
                return default_disk
            raise ValueError("No se ha seleccionado ningún disco de destino en la configuración.")
            
        return target_disk

    def run_app_backup(self, app_name: str, app_path: str) -> bool:
        """Realiza la copia de seguridad de una aplicación específica."""
        try:
            target_disk = self.get_target_disk()
            dest_dir = os.path.join(target_disk, "Backups", "Apps", app_name)
            os.makedirs(dest_dir, exist_ok=True)

            logger.info(f"Iniciando respaldo de {app_name} en {dest_dir}...")

            # Marca de tiempo para mantener historial de respaldos
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            tar_file = os.path.join(dest_dir, f"{app_name}_backup_{timestamp}.tar.gz")
            
            cmd = ["tar", "-czf", tar_file, "-C", app_path, "."]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Respaldo de {app_name} completado con éxito: {os.path.basename(tar_file)}")
                
                # 🧹 Aplicar política de retención automática (máximo 3 copias)
                try:
                    backup_engine_service.apply_retention_policy(
                        target_dir=dest_dir,
                        prefix=app_name,
                        max_copies=3
                    )
                except Exception as ret_err:
                    logger.warning(f"[DuplicatiService] Error aplicando retención para {app_name}: {ret_err}")

                return True
            else:
                logger.error(f"Error al empaquetar {app_name}: {result.stderr}")
                return False

        except ValueError as ve:
            logger.error(f"[DuplicatiService] Error de configuración: {ve}")
            return False
        except Exception as e:
            logger.error(f"[DuplicatiService] Error inesperado respaldando {app_name}: {e}")
            return False

    def run_full_disaster_recovery(self) -> bool:
        """Realiza la copia de seguridad completa del sistema (Disaster Recovery)."""
        try:
            target_disk = self.get_target_disk()
            dest_dir = os.path.join(target_disk, "Backups", "DisasterRecovery")
            os.makedirs(dest_dir, exist_ok=True)

            logger.info(f"Iniciando Disaster Recovery en {dest_dir}...")

            # 1. Crear nombre de archivo con marca de tiempo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            tar_file = os.path.join(dest_dir, f"disaster_recovery_{timestamp}.tar.gz")
            
            # 2. Comando tar para resguardar las rutas críticas de CasaOS
            # (Puedes añadir o quitar rutas si lo necesitas)
            cmd = [
                "tar", "-czf", tar_file, 
                "/DATA/AppData",     # Datos de los contenedores
                "/var/lib/casaos",   # Base de datos y estado de CasaOS
                "/etc/casaos"        # Configuraciones de CasaOS
            ]
            
            # 3. Ejecutar la compresión (esto bloqueará/tardará según el tamaño)
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # NOTA: tar suele devolver '1' si un archivo cambió mientras se leía (común en logs/dbs activas).
            # Por tanto, consideramos éxito el código 0 (perfecto) y el 1 (warning tolerado).
            if result.returncode in [0, 1]:
                logger.info(f"Disaster Recovery completado con éxito: {os.path.basename(tar_file)}")
                
                # 4. Limpieza: Mantener solo las últimas 2 copias del sistema completo (para no saturar disco)
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
                logger.error(f"Error al empaquetar Disaster Recovery: {result.stderr}")
                return False

        except ValueError as ve:
            logger.error(f"[DuplicatiService] Error de configuración: {ve}")
            return False
        except Exception as e:
            logger.error(f"[DuplicatiService] Error inesperado en Disaster Recovery: {e}")
            return False

duplicati_service = DuplicatiService()