import os
import json
from typing import List, Dict, Any
from app.services.system_service import get_real_protectable_data

PROFILES_FILE = "data/profiles.json"

class ProfileService:
    def __init__(self, storage_file: str = PROFILES_FILE):
        self.storage_file = storage_file
        self._ensure_storage()

    def _ensure_storage(self):
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
        if not os.path.exists(self.storage_file):
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump([], f)

    def generate_profiles_from_discovery(self) -> List[Dict[str, Any]]:
        """Agrupa el descubrimiento dinámico en perfiles inteligentes por aplicación."""
        items = get_real_protectable_data()
        apps_map: Dict[str, Dict[str, Any]] = {}

        for item in items:
            container = item.get("container_name", "")
            if not container:
                continue

            # Determinar el nombre base de la App (ej: immich-server -> immich)
            app_id = container.split("-")[0] if "-" in container else container
            app_name = app_id.capitalize()

            if app_id not in apps_map:
                apps_map[app_id] = {
                    "app_id": app_id,
                    "app_name": app_name,
                    "containers": set(),
                    "paths": set(),
                    "has_db": False,
                    "hooks": set()
                }

            apps_map[app_id]["containers"].add(container)
            
            # Solo incluir rutas relevantes de datos de CasaOS
            if item.get("is_casaos_data"):
                apps_map[app_id]["paths"].add(item.get("host_path"))

            if item.get("is_db"):
                apps_map[app_id]["has_db"] = True
                if item.get("recommended_hook"):
                    apps_map[app_id]["hooks"].add(item.get("recommended_hook"))

        profiles = []
        for app_id, data in apps_map.items():
            profiles.append({
                "app_id": app_id,
                "app_name": data["app_name"],
                "containers_count": len(data["containers"]),
                "containers": list(data["containers"]),
                "paths": list(data["paths"]),
                "has_db": data["has_db"],
                "recommended_hooks": list(data["hooks"]),
                "default_exclusions": ["*.tmp", "*.log", "cache/*", "Cache/*"]
            })

        return profiles

profile_service = ProfileService()