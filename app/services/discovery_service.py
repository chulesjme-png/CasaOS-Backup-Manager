import os
import logging
import docker

logger = logging.getLogger("casaos_backup_manager")

class DiscoveryService:
    """Servicio para descubrir únicamente aplicaciones e instancias activas instaladas en CasaOS."""

    APPDATA_PATH = "/DATA/AppData"
    DB_HOOKS = {"immich", "nextcloud", "mariadb", "mysql", "postgres", "vaultwarden", "plex"}

    def scan_apps(self) -> list:
        """
        Escanea y devuelve ÚNICAMENTE las aplicaciones/contenedores que están instalados y activos en Docker.
        Evita listar carpetas de configuraciones antiguas o carpetas genéricas de AppData.
        """
        apps = []
        installed_apps = {}

        try:
            client = docker.from_env()
            # Obtenemos todos los contenedores (running, stopped, etc.)
            containers = client.containers.list(all=True)

            for container in containers:
                name = container.name.strip('/')
                
                # Ignorar contenedores del sistema base de CasaOS si fuera necesario o mostrarlos
                # Extraemos el nombre de la app (CasaOS suele poner casaos.app.name o el nombre del contenedor)
                app_name = container.labels.get("casaos.app.name") or name
                
                # Buscar si existe su carpeta de AppData
                app_path = os.path.join(self.APPDATA_PATH, app_name)
                if not os.path.exists(app_path):
                    # Probar con el nombre del contenedor tal cual
                    app_path = os.path.join(self.APPDATA_PATH, name)
                    if not os.path.exists(app_path):
                        app_path = f"/DATA/AppData/{app_name}"

                app_name_lower = app_name.lower()
                has_db_hook = any(db in app_name_lower for db in self.DB_HOOKS)

                installed_apps[app_name] = {
                    "name": app_name,
                    "container_name": name,
                    "path": app_path,
                    "has_db_hook": has_db_hook,
                    "status": container.status
                }

            # Convertir a lista ordenada por nombre
            apps = sorted(list(installed_apps.values()), key=lambda x: x["name"].lower())

        except Exception as e:
            logger.error(f"Error escaneando contenedores Docker: {e}")

        logger.info(f"Escaneo completado: {len(apps)} contenedores/aplicaciones detectadas.")
        return apps

discovery_service = DiscoveryService()