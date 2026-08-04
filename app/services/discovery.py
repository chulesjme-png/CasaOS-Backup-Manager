import docker
from typing import List, Dict, Any

class DockerDiscoveryService:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            self.client = None
            print(f"[ERROR] No se pudo conectar con el socket de Docker: {e}")

    def is_database_container(self, name: str, image: str) -> Dict[str, Any]:
        """Detecta si un contenedor es una base de datos y define su hook de backup."""
        name_lower = name.lower()
        image_lower = image.lower()

        if "postgres" in image_lower or "postgres" in name_lower:
            return {"is_db": True, "type": "postgresql", "hook": "pg_dumpall"}
        elif "mariadb" in image_lower or "mysql" in image_lower or "mariadb" in name_lower or "mysql" in name_lower:
            return {"is_db": True, "type": "mysql_mariadb", "hook": "mysqldump_all"}
        elif "redis" in image_lower or "redis" in name_lower:
            return {"is_db": True, "type": "redis", "hook": "redis_bgsave"}
        elif "mongodb" in image_lower or "mongo" in name_lower:
            return {"is_db": True, "type": "mongodb", "hook": "mongodump"}
        
        return {"is_db": False, "type": None, "hook": None}

    def inspect_protectable_data(self) -> List[Dict[str, Any]]:
        """Inspecciona los contenedores y extrae sus montajes y rutas persistentes."""
        if not self.client:
            return []

        protectable_items = []

        try:
            containers = self.client.containers.list(all=True)
            
            for container in containers:
                c_name = container.name
                c_image = container.image.tags[0] if container.image.tags else container.image.short_id
                c_status = container.status
                
                db_info = self.is_database_container(c_name, c_image)
                mounts = container.attrs.get('Mounts', [])
                
                for mount in mounts:
                    mount_type = mount.get('Type')
                    source = mount.get('Source', '')
                    destination = mount.get('Destination', '')
                    rw = mount.get('RW', True)

                    if not source or source == '/var/run/docker.sock' or source.startswith('/proc') or source.startswith('/sys'):
                        continue

                    is_casaos_data = source.startswith('/DATA') or '/AppData/' in source

                    protectable_items.append({
                        "container_name": c_name,
                        "image": c_image,
                        "container_status": c_status,
                        "mount_type": mount_type,
                        "host_path": source,
                        "container_path": destination,
                        "read_only": not rw,
                        "is_casaos_data": is_casaos_data,
                        "is_db": db_info["is_db"],
                        "db_type": db_info["type"],
                        "recommended_hook": db_info["hook"]
                    })

        except Exception as e:
            print(f"[ERROR] Error durante la inspección de Docker: {e}")

        return protectable_items

discovery_service = DockerDiscoveryService()