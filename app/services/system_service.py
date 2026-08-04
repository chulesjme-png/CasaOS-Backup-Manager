import os
import json
import urllib3
import platform
import psutil

# Socket Unix auxiliar para la API REST nativa de Docker
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


def query_docker_api(endpoint: str):
    """Consulta la API local de Docker vía socket Unix sin dependencias externas."""
    socket_path = "/var/run/docker.sock"
    if not os.path.exists(socket_path):
        return None
    try:
        pool = UnixHTTPConnectionPool(socket_path)
        res = pool.request('GET', endpoint)
        if res.status == 200:
            return json.loads(res.data.decode('utf-8'))
    except Exception as e:
        print(f"[ERROR] Docker API Query ({endpoint}): {e}")
    return None


def get_real_system_info() -> dict:
    """Obtiene la telemetría real del host (Raspberry Pi)."""
    try:
        mem = psutil.virtual_memory()
        uname = platform.uname()
        return {
            "os_name": f"CasaOS ({uname.system} {uname.machine})",
            "architecture": uname.machine,
            "kernel": uname.release,
            "cpu_cores": psutil.cpu_count(logical=True),
            "ram_total_gb": round(mem.total / (1024**3), 2),
            "ram_used_gb": round(mem.used / (1024**3), 2),
            "ram_percent": mem.percent,
            "hostname": uname.node,
        }
    except Exception as e:
        print(f"[ERROR] Telemetría de sistema: {e}")
        return {
            "os_name": "Linux (Raspberry Pi)",
            "architecture": "aarch64",
            "kernel": "Unknown",
            "cpu_cores": 4,
            "ram_total_gb": 8.0,
            "ram_used_gb": 0.0,
            "ram_percent": 0.0,
            "hostname": "raspberrypi",
        }


def get_real_docker_info() -> dict:
    """Obtiene el listado y estado real de los contenedores Docker."""
    containers = query_docker_api('/containers/json?all=true')
    version_info = query_docker_api('/version')

    if not containers or not isinstance(containers, list):
        return {
            "containers_total": 0,
            "containers_running": 0,
            "containers_stopped": 0,
            "api_version": "1.43",
            "services_list": []
        }

    running = 0
    stopped = 0
    services_list = []

    for c in containers:
        state = c.get('State', '')
        is_running = state == 'running'
        if is_running:
            running += 1
        else:
            stopped += 1

        names = c.get('Names', ['/desconocido'])
        name = names[0].lstrip('/') if names else 'desconocido'
        image = c.get('Image', 'unknown')

        services_list.append({
            "name": name,
            "image": image,
            "status": "En ejecución" if is_running else "Detenido",
            "running": is_running
        })

    api_version = version_info.get('ApiVersion', '1.43') if isinstance(version_info, dict) else '1.43'

    return {
        "containers_total": len(containers),
        "containers_running": running,
        "containers_stopped": stopped,
        "api_version": api_version,
        "services_list": services_list
    }


def get_real_disk_info(path="/DATA") -> dict:
    """Obtiene el espacio en disco de la ruta de almacenamiento."""
    try:
        target_path = path if os.path.exists(path) else "/"
        usage = psutil.disk_usage(target_path)
        return {
            "path": target_path,
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "percent": usage.percent
        }
    except Exception as e:
        print(f"[ERROR] Telemetría de disco: {e}")
        return {
            "path": path,
            "total_gb": 0.0,
            "used_gb": 0.0,
            "free_gb": 0.0,
            "percent": 0.0
        }


def get_real_protectable_data() -> list:
    """Inspecciona los montajes de los contenedores para mapear rutas persistentes y bases de datos."""
    containers = query_docker_api('/containers/json?all=true')
    if not containers or not isinstance(containers, list):
        return []

    protectable_items = []

    for container in containers:
        names = container.get('Names', ['/desconocido'])
        c_name = names[0].lstrip('/') if names else 'desconocido'
        c_image = container.get('Image', 'unknown')
        c_status = container.get('State', 'unknown')

        # Detección de bases de datos
        name_lower, img_lower = c_name.lower(), c_image.lower()
        is_db, db_type, hook = False, None, None
        if "postgres" in img_lower or "postgres" in name_lower:
            is_db, db_type, hook = True, "postgresql", "pg_dumpall"
        elif "mariadb" in img_lower or "mysql" in img_lower or "mariadb" in name_lower or "mysql" in name_lower:
            is_db, db_type, hook = True, "mysql_mariadb", "mysqldump_all"
        elif "redis" in img_lower or "redis" in name_lower:
            is_db, db_type, hook = True, "redis", "redis_bgsave"
        elif "mongodb" in img_lower or "mongo" in name_lower:
            is_db, db_type, hook = True, "mongodb", "mongodump"

        mounts = container.get('Mounts', [])
        for mount in mounts:
            source = mount.get('Source', '')
            destination = mount.get('Destination', '')
            mount_type = mount.get('Type', 'bind')
            rw = mount.get('RW', True)

            # Omitir montajes del sistema o socket de docker
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
                "is_db": is_db,
                "db_type": db_type,
                "recommended_hook": hook
            })

    return protectable_items