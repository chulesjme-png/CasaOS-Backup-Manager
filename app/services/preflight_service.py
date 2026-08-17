import shutil
import logging
from pathlib import Path
from typing import Tuple

logger = logging.getLogger("casaos-backup")

class PreflightService:
    """
    Servicio de verificaciones previas antes de ejecutar copias de seguridad.
    """

    @staticmethod
    def check_disk_space(target_path: str, required_bytes_estimate: int = 0, safety_margin_gb: float = 5.0) -> Tuple[bool, str]:
        """
        Verifica si la ruta de destino existe y cuenta con espacio suficiente.
        
        :param target_path: Ruta del directorio o punto de montaje de destino.
        :param required_bytes_estimate: Estimación en bytes del tamaño de la copia.
        :param safety_margin_gb: Margen de seguridad mínimo libre requerido (por defecto 5 GB).
        :return: Tupla (exito: bool, mensaje: str)
        """
        path = Path(target_path)

        # Buscar el punto de montaje o directorio existente más cercano
        while not path.exists() and path != path.parent:
            path = path.parent

        if not path.exists():
            return False, f"La ruta de destino '{target_path}' no existe ni está montada."

        try:
            total, used, free = shutil.disk_usage(path)
            safety_margin_bytes = int(safety_margin_gb * 1024 * 1024 * 1024)
            needed_bytes = required_bytes_estimate + safety_margin_bytes

            free_gb = free / (1024 ** 3)
            needed_gb = needed_bytes / (1024 ** 3)

            if free < needed_bytes:
                error_msg = (
                    f"Espacio insuficiente en '{path}'. "
                    f"Disponible: {free_gb:.2f} GB | Requerido (con margen de {safety_margin_gb}GB): {needed_gb:.2f} GB."
                )
                logger.error(f"❌ [Pre-flight Fail] {error_msg}")
                return False, error_msg

            logger.info(f"✅ [Pre-flight OK] Espacio verificado en '{path}'. Disponible: {free_gb:.2f} GB.")
            return True, f"Espacio suficiente ({free_gb:.2f} GB disponibles)."

        except Exception as e:
            logger.error(f"❌ [Pre-flight Error] Error al verificar espacio en disco: {e}")
            return False, f"Error al verificar espacio en disco: {str(e)}"

preflight_service = PreflightService()