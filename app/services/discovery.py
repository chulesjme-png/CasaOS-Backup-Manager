import os
import json
import urllib3
from typing import List, Dict, Any

class UnixHTTPConnectionPool(urllib3.HTTPConnectionPool):
    def __init__(self, socket_path, timeout=5):
        super().__init__('localhost', timeout=timeout)
        self.socket_path = socket_path

    def _new_conn(self):
        import socket
        conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        conn.settimeout(self.timeout.connect_timeout)
        conn.connect(self.socket_path)
        return conn

class DockerDiscoveryService:
    def __init__(self, socket_path: str = "/var/run/docker.sock"):
        self.socket_path = socket_path

    def _query_docker_api(self, endpoint: str) -> Any:
        """Consulta la API local de Docker mediante el socket Unix directamente."""
        if not os.path.exists(self.socket_path):
            print(f"[ERROR] Socket de Docker no encontrado en {self.socket_path}")
            return None

        try:
            pool = UnixHTTPConnectionPool(self.socket_path)
            response = pool.request('GET', endpoint)
            if response.status == 200:
                return json.loads(response.data.decode('utf-8'))
        except Exception as e:
            print(f"[ERROR] Fallo al consultar API de Docker ({endpoint}): {e}")
        return None

    def is_database_container(self, name: str, image: str) -> Dict[str, Any]:
        """Detecta si un contenedor es una base de datos y define su hook."""
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
        """Inspecciona todos los contenedores y extrae las rutas montadas."""
        containers = self._query_docker_api('/containers/json?all=true')
        if not containers or not isinstance(containers, list):
            return []

        protectable_items = []

        for container in containers:
            # Extraer nombres limpios de contenedor e imagen
            names = container.get('Names', ['/desconocido'])
            c_name = names[0].lstrip('/') if names else 'desconocido'
            c_image = container.get('Image', 'unknown')
            c_status = container.get('State', 'unknown')

            db_info = self.is_database_container(c_name, c_image)
            mounts = container.get('Mounts', [])

            for mount in mounts:
                mount_type = mount.get('Type', 'bind')
                source = mount.get('Source', '')
                destination = mount.get('Destination', '')
                rw = mount.get('RW', True)

                # Descartar montajes del sistema o socket de docker
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

        return protectable_items

discovery_service = DockerDiscoveryService()