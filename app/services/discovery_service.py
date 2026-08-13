import os
from pathlib import Path
from typing import List, Dict

APPDATA_DIR = Path("/DATA/AppData")

# Mapeo automático de hooks de BD según el nombre de la app o sus archivos internos
DB_HOOK_KEYWORDS = {
    "mariadb": "MariaDB Dump Hook",
    "mysql": "MySQL Dump Hook",
    "postgres": "PostgreSQL Dump Hook",
    "postgresql": "PostgreSQL Dump Hook",
    "nextcloud": "DB Sync Hook",
    "immich": "Postgres Dump Hook"
}

class DiscoveryService:
    def scan_apps(self) -> List[Dict[str, any]]:
        apps = []
        if not APPDATA_DIR.exists():
            return apps

        for entry in sorted(APPDATA_DIR.iterdir()):
            if entry.is_dir():
                app_name = entry.name
                app_path = str(entry)
                
                # Chequear si requiere Hook DB
                has_db_hook = False
                hook_type = None
                
                app_lower = app_name.lower()
                for key, hook in DB_HOOK_KEYWORDS.items():
                    if key in app_lower:
                        has_db_hook = True
                        hook_type = hook
                        break

                apps.append({
                    "name": app_name,
                    "path": app_path,
                    "has_db_hook": has_db_hook,
                    "hook_type": hook_type
                })

        return apps

discovery_service = DiscoveryService()