import subprocess
import logging
import re
import os

logger = logging.getLogger(__name__)

class DuplicatiEngine:
    @staticmethod
    def run_cli_backup(source_path: str, destination_path: str, backup_name: str, progress_callback=None) -> bool:
        """
        Invoca la herramienta Duplicati CLI para realizar una copia incremental.
        """
        # Crear subdirectorio específico en el disco externo
        target_dir = os.path.join(destination_path, "CasaOS_Backups", backup_name)
        os.makedirs(target_dir, exist_ok=True)

        # Comando Duplicati CLI sintaxis estándar
        # URL de destino formato file://
        dest_url = f"file://{target_dir}"

        cmd = [
            "duplicati-cli", "backup",
            dest_url,
            source_path,
            "--passphrase=CasaOSBackupManagerSecureKey",
            "--no-encryption=false",
            "--compression-module=zip"
        ]

        logger.info(f"🚀 Iniciando Duplicati CLI: Source={source_path} -> Dest={dest_url}")

        try:
            # Ejecutar proceso capturando salida en tiempo real para parsear el progreso %
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in process.stdout:
                # Buscar patrones de porcentaje tipo "15.40%" o "Processing..."
                match = re.search(r'(\d{1,3}\.\d{1,2})%', line)
                if match and progress_callback:
                    pct = float(match.group(1))
                    progress_callback(int(pct))

            process.wait()

            if process.returncode == 0:
                logger.info(f"✅ Duplicati CLI completó la copia de {backup_name} con éxito.")
                if progress_callback:
                    progress_callback(100)
                return True
            else:
                logger.error(f"❌ Duplicati CLI terminó con código de error {process.returncode}")
                return False

        except FileNotFoundError:
            logger.warning("⚠️ 'duplicati-cli' no se encuentra instalado en el PATH del sistema host. Se requerirá fallback.")
            return False
        except Exception as e:
            logger.error(f"❌ Error ejecutando Duplicati CLI: {e}")
            return False