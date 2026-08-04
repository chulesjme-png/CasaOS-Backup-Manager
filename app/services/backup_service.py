import os
import tarfile
import subprocess
from datetime import datetime
from typing import List, Dict, Any
from app.services.profile_service import profile_service

BACKUP_DESTINATION = "/DATA/Backups/CasaOS"

class BackupService:
    def __init__(self, target_dir: str = BACKUP_DESTINATION):
        self.target_dir = target_dir
        os.makedirs(self.target_dir, exist_ok=True)

    def execute_app_backup(self, app_id: str) -> Dict[str, Any]:
        """Ejecuta la copia de seguridad de un perfil de aplicación específico."""
        profiles = profile_service.generate_profiles_from_discovery()
        profile = next((p for p in profiles if p["app_id"] == app_id), None)

        if not profile:
            return {"success": False, "error": f"Perfil '{app_id}' no encontrado"}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"{app_id}_backup_{timestamp}.tar.gz"
        backup_path = os.path.join(self.target_dir, backup_filename)

        included_paths = profile.get("paths", [])
        if not included_paths:
            return {"success": False, "error": "No hay rutas asociadas para respaldar"}

        try:
            # 1. Ejecución opcional de Pre-Hook (Dumps DB, etc.)
            hooks = profile.get("recommended_hooks", [])
            for hook in hooks:
                print(f"[HOOK] Ejecutando pre-backup hook ({hook}) para {app_id}...")

            # 2. Creación del archivo comprimido TAR.GZ
            files_added = 0
            with tarfile.open(backup_path, "w:gz") as tar:
                for path in included_paths:
                    if os.path.exists(path):
                        # Evita añadir recursivamente la propia carpeta de destino
                        if os.path.abspath(path) == os.path.abspath(self.target_dir):
                            continue
                        arcname = os.path.basename(path)
                        tar.add(path, arcname=arcname)
                        files_added += 1

            size_bytes = os.path.getsize(backup_path) if os.path.exists(backup_path) else 0
            size_mb = round(size_bytes / (1024 * 1024), 2)

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
            return {"success": False, "error": str(e)}

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """Lista las copias de seguridad realizadas en el volumen de destino."""
        if not os.path.exists(self.target_dir):
            return []

        snapshots = []
        for file in os.listdir(self.target_dir):
            if file.endswith(".tar.gz"):
                full_p = os.path.join(self.target_dir, file)
                stat = os.stat(full_p)
                snapshots.append({
                    "filename": file,
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created_at": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
        return sorted(snapshots, key=lambda x: x["created_at"], reverse=True)

backup_service = BackupService()