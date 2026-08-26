import os
import json
import glob
import tarfile
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from app.services.profile_service import profile_service
from app.services.backup_engine_service import backup_engine_service

CONFIG_FILE = "/data/settings.json"
DEFAULT_BACKUP_DESTINATION = "/DATA/Backups/CasaOS"

def get_current_backup_target() -> str:
    """Lee el destino de copia guardado en la configuración o retorna el valor por defecto."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                target = data.get("target_path")
                if target:
                    return target
        except Exception as e:
            print(f"[WARNING] Error al leer {CONFIG_FILE}: {e}")
    return DEFAULT_BACKUP_DESTINATION


class BackupService:
    def __init__(self, target_dir: str = None):
        self._custom_target_dir = target_dir

    @property
    def target_dir(self) -> str:
        """Obtiene dinámicamente la ruta de destino activa."""
        path = self._custom_target_dir or get_current_backup_target()
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            print(f"[WARNING] No se pudo crear el directorio de backups '{path}': {e}")
        return path

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024 * 1024:
            return f"{round(size_bytes / 1024, 1)} KB"
        return f"{round(size_bytes / (1024 * 1024), 2)} MB"

    def _format_date(self, timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    def _collect_file_list(self, paths: List[str], active_target: str):
        """Escanea las rutas objetivo y genera una lista detallada con sus tamaños para calcular el progreso."""
        file_list = []
        total_bytes = 0

        abs_target = os.path.abspath(active_target)

        for path in paths:
            if not os.path.exists(path):
                continue

            abs_path = os.path.abspath(path)
            if abs_path == abs_target or abs_path.startswith(abs_target + os.sep):
                continue

            if os.path.isfile(path):
                try:
                    sz = os.path.getsize(path)
                    total_bytes += sz
                    file_list.append((path, os.path.basename(path), sz))
                except (OSError, FileNotFoundError):
                    pass
            elif os.path.isdir(path):
                parent_dir = os.path.dirname(path)
                for root, _, files in os.walk(path):
                    for f in files:
                        full_f = os.path.join(root, f)
                        abs_full_f = os.path.abspath(full_f)
                        if abs_full_f == abs_target or abs_full_f.startswith(abs_target + os.sep):
                            continue
                        try:
                            sz = os.path.getsize(full_f)
                            total_bytes += sz
                            rel_p = os.path.relpath(full_f, start=parent_dir)
                            file_list.append((full_f, rel_p, sz))
                        except (OSError, FileNotFoundError):
                            pass

        return file_list, total_bytes if total_bytes > 0 else 1

    def execute_app_backup(self, app_id: str, progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict[str, Any]:
        """Ejecuta la copia de seguridad de un perfil de aplicación específico con progreso en tiempo real."""
        if progress_callback:
            progress_callback(2, f"Iniciando respaldo de {app_id}...")

        profiles = profile_service.generate_profiles_from_discovery()
        profile = next((p for p in profiles if p["app_id"] == app_id), None)

        if not profile:
            return {"success": False, "error": f"Perfil '{app_id}' no encontrado"}

        active_target = self.target_dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{app_id}_backup_{timestamp}.tar.gz"
        backup_path = os.path.join(active_target, backup_filename)

        included_paths = profile.get("paths", [])
        if not included_paths:
            return {"success": False, "error": "No hay rutas asociadas para respaldar"}

        try:
            # 1. Ejecución opcional de Pre-Hook (Dumps DB, etc.)
            hooks = profile.get("recommended_hooks", [])
            for hook in hooks:
                if progress_callback:
                    progress_callback(5, f"Ejecutando pre-hook ({hook})...")
                print(f"[HOOK] Ejecutando pre-backup hook ({hook}) para {app_id}...")

            # 2. Escaneo previo para cálculo de progreso
            if progress_callback:
                progress_callback(8, "Calculando volumen de datos...")
            
            file_list, total_bytes = self._collect_file_list(included_paths, active_target)

            # 3. Creación del archivo comprimido TAR.GZ con reporte continuo
            files_added = 0
            processed_bytes = 0

            with tarfile.open(backup_path, "w:gz") as tar:
                for full_f, arcname, sz in file_list:
                    if os.path.exists(full_f):
                        tar.add(full_f, arcname=arcname, recursive=False)
                        processed_bytes += sz
                        files_added += 1

                        if progress_callback:
                            pct = 10 + int((processed_bytes / total_bytes) * 80)
                            pct = min(pct, 92)
                            mb_proc = processed_bytes / (1024 * 1024)
                            progress_callback(pct, f"Empaquetando datos ({mb_proc:.1f} MB)...")

            if progress_callback:
                progress_callback(94, "Verificando archivo comprimido...")

            size_bytes = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0
            size_mb = round(size_bytes / (1024 * 1024), 2)

            # 4. Aplicar Política de Retención Automática (Máximo 3 copias)
            if progress_callback:
                progress_callback(97, "Aplicando políticas de retención...")
            try:
                backup_engine_service.apply_retention_policy(
                    target_dir=active_target,
                    prefix=app_id,
                    max_copies=3
                )
            except Exception as ret_err:
                print(f"[WARNING] Error aplicando retención para {app_id}: {ret_err}")

            if progress_callback:
                progress_callback(100, "Copia de seguridad completada con éxito")

            return {
                "success": True,
                "app_id": app_id,
                "backup_file": backup_filename,
                "full_path": backup_path,
                "size_mb": size_mb,
                "timestamp": timestamp,
                "files_added": files_added
            }

        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Error en copia de seguridad: {str(e)}")
            return {"success": False, "error": str(e)}

    def execute_disaster_recovery(self, progress_callback: Optional[Callable[[int, str], None]] = None) -> Dict[str, Any]:
        """Ejecuta un respaldo completo de Disaster Recovery (/DATA/AppData) con barra de progreso fluida."""
        if progress_callback:
            progress_callback(2, "Iniciando Disaster Recovery...")

        active_target = self.target_dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"disaster_recovery_{timestamp}.tar.gz"
        backup_path = os.path.join(active_target, backup_filename)

        source_paths = ["/DATA/AppData"]

        try:
            if progress_callback:
                progress_callback(8, "Escaneando archivos del sistema...")

            file_list, total_bytes = self._collect_file_list(source_paths, active_target)

            files_added = 0
            processed_bytes = 0

            with tarfile.open(backup_path, "w:gz") as tar:
                for full_f, arcname, sz in file_list:
                    if os.path.exists(full_f):
                        tar.add(full_f, arcname=arcname, recursive=False)
                        processed_bytes += sz
                        files_added += 1

                        if progress_callback:
                            pct = 10 + int((processed_bytes / total_bytes) * 82)
                            pct = min(pct, 95)
                            mb_proc = processed_bytes / (1024 * 1024)
                            progress_callback(pct, f"Empaquetando datos y configuraciones ({mb_proc:.1f} MB)...")

            size_bytes = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0
            size_mb = round(size_bytes / (1024 * 1024), 2)

            # Aplicar retención también para Disaster Recovery
            try:
                backup_engine_service.apply_retention_policy(
                    target_dir=active_target,
                    prefix="disaster_recovery",
                    max_copies=3
                )
            except Exception as ret_err:
                print(f"[WARNING] Error aplicando retención en Disaster Recovery: {ret_err}")

            if progress_callback:
                progress_callback(100, "Disaster Recovery completado con éxito")

            return {
                "success": True,
                "backup_file": backup_filename,
                "full_path": backup_path,
                "size_mb": size_mb,
                "timestamp": timestamp,
                "files_added": files_added
            }

        except Exception as e:
            if progress_callback:
                progress_callback(0, f"Error en Disaster Recovery: {str(e)}")
            return {"success": False, "error": str(e)}

    def list_snapshots(self, max_keep_per_app: int = 3) -> List[Dict[str, Any]]:
        """
        Lista las copias de seguridad activas en el directorio destino.
        Elimina automáticamente del disco las copias que superen max_keep_per_app por aplicación.
        """
        return self.get_available_backups(target_dir=self.target_dir, max_keep_per_app=max_keep_per_app)

    def get_available_backups(self, target_dir: str = None, max_keep_per_app: int = 3) -> List[Dict[str, Any]]:
        """
        Escanea el directorio de backups, borra físicamente del disco las copias
        obsoletas (más de 3 por app) y retorna solo las 3 más recientes de cada una.
        """
        active_target = target_dir or self.target_dir
        if not active_target or not os.path.exists(active_target):
            return []

        pattern = os.path.join(active_target, "*.tar.gz")
        all_files = glob.glob(pattern)

        app_groups: Dict[str, List[str]] = {}

        for filepath in all_files:
            filename = os.path.basename(filepath)
            
            if "_backup_" in filename:
                app_name = filename.split("_backup_")[0]
            elif filename.startswith("disaster_recovery_") or filename.startswith("full_system_"):
                app_name = "Disaster Recovery"
            else:
                app_name = "Otros"

            if app_name not in app_groups:
                app_groups[app_name] = []
            app_groups[app_name].append(filepath)

        valid_backups = []

        for app_name, files in app_groups.items():
            # Ordenar por fecha de modificación (la más reciente primero)
            files.sort(key=lambda f: os.path.getmtime(f), reverse=True)

            to_keep = files[:max_keep_per_app]
            to_delete = files[max_keep_per_app:]

            # Eliminar archivos obsoletos físicamente del disco
            for old_file in to_delete:
                try:
                    os.remove(old_file)
                    print(f"[RETENTION] Copia obsoleta eliminada del disco: {old_file}")
                except Exception as e:
                    print(f"[ERROR] No se pudo eliminar copia obsoleta {old_file}: {e}")

            # Procesar únicamente las copias conservadas
            for filepath in to_keep:
                try:
                    stat = os.stat(filepath)
                    filename = os.path.basename(filepath)
                    
                    display_app = app_name.capitalize() if app_name not in ("Disaster Recovery", "Otros") else app_name

                    valid_backups.append({
                        "filename": filename,
                        "filepath": filepath,
                        "full_path": filepath,
                        "app": display_app,
                        "app_id": app_name,
                        "size": stat.st_size,
                        "size_mb": round(stat.st_size / (1024 * 1024), 2),
                        "size_formatted": self._format_size(stat.st_size),
                        "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        "mtime": stat.st_mtime
                    })
                except Exception as e:
                    print(f"[ERROR] Error al leer metadatos de {filepath}: {e}")
                    continue

        valid_backups.sort(key=lambda x: x["mtime"], reverse=True)
        return valid_backups

backup_service = BackupService()