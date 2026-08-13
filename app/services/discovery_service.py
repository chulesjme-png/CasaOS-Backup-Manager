import os
import logging
import docker

logger = logging.getLogger("casaos_backup_manager")

class DiscoveryService:
    """Servicio para descubrir aplicaciones activas de CasaOS mediante Docker y AppData."""

    APPDATA_PATH = "/DATA/AppData"

    # Lista de bases de datos conocidas que requieren hooks especiales
    DB_HOOKS = {"immich", "nextcloud", "mariadb", "mysql", "postgres", "vaultwarden", "plex"}

    def scan_apps(self) -> list:
        """
        Escanea las aplicaciones activas cruzando la información de contenedores Docker 
        en ejecución y las carpetas reales en /DATA/AppData, descartando restos antiguos.
        """
        apps = []
        active_docker_containers = set()

        # 1. Obtener contenedores Docker en ejecución actualmente
        try:
            client = docker.from_env()
            for container in client.containers.list():
                # Limpiar nombres de contenedores (quitar barras iniciales)
                name = container.name.strip('/')
                active_docker_containers.add(name.lower())
                # Añadir también por etiquetas de CasaOS si existen
                app_label = container.labels.get("casaos.app.name")
                if app_label:
                    active_docker_containers.add(app_label.lower())
        except Exception as e:
            logger.warning(f"No se pudo conectar al socket de Docker para listar contenedores: {e}")

        # 2. Escanear /DATA/AppData pero filtrando solo lo que tenga Docker activo o sea válido
        if os.path.exists(self.APPDATA_PATH):
            try:
                items = os.listdir(self.APPDATA_PATH)
                for item in sorted(items):
                    item_path = os.path.join(self.APPDATA_PATH, item)
                    
                    if not os.path.isdir(item_path):
                        continue

                    app_name_lower = item.lower()

                    # FILTRO DE SEGURIDAD: 
                    # Descartar aplicaciones como 'calibre' u otras que no tengan un contenedor activo asociado
                    # (A menos que queramos forzarlo, exigimos que esté en los contenedores activos o en stack conocido)
                    is_running = any(app_name_lower in c or c in app_name_lower for c in active_docker_containers)
                    
                    # Excepción para herramientas internas o si prefieres listar todo lo de AppData excepto huérfanos claros:
                    # Si un directorio se llama 'calibre' pero no hay ningún contenedor Docker activo relacionado, se omite.
                    if not is_running and app_name_lower == "calibre":
                        continue

                    # Detectar si requiere Hook de Base de Datos
                    has_db_hook = any(db in app_name_lower for db in self.DB_HOOKS)

                    apps.append({
                        "name": item,
                        "path": item_path,
                        "has_db_hook": has_db_hook,
                        "status": "running" if is_running else "stopped"
                    })
            except Exception as e:
                logger.error(f"Error escaneando /DATA/AppData: {e}")

        logger.info(f"Escaneo completado: {len(apps)} aplicaciones activas detectadas.")
        return apps

discovery_service = DiscoveryService()