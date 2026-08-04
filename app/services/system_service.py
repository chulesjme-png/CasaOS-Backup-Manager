def get_real_protectable_data() -> list:
    """Inspecciona los montajes de los contenedores Docker mediante la API local."""
    import urllib3
    import json
    import os

    socket_path = "/var/run/docker.sock"
    if not os.path.exists(socket_path):
        return []

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

    try:
        pool = UnixHTTPConnectionPool(socket_path)
        res = pool.request('GET', '/containers/json?all=true')
        if res.status != 200:
            return []
        
        containers = json.loads(res.data.decode('utf-8'))
        protectable_items = []

        for container in containers:
            names = container.get('Names', ['/desconocido'])
            c_name = names[0].lstrip('/') if names else 'desconocido'
            c_image = container.get('Image', 'unknown')
            c_status = container.get('State', 'unknown')

            # Detectar bases de datos
            name_lower, img_lower = c_name.lower(), c_image.lower()
            is_db, db_type, hook = False, None, None
            if "postgres" in img_lower or "postgres" in name_lower:
                is_db, db_type, hook = True, "postgresql", "pg_dumpall"
            elif "mariadb" in img_lower or "mysql" in img_lower or "mariadb" in name_lower or "mysql" in name_lower:
                is_db, db_type, hook = True, "mysql_mariadb", "mysqldump_all"
            elif "redis" in img_lower or "redis" in name_lower:
                is_db, db_type, hook = True, "redis", "redis_bgsave"

            mounts = container.get('Mounts', [])
            for mount in mounts:
                source = mount.get('Source', '')
                destination = mount.get('Destination', '')
                mount_type = mount.get('Type', 'bind')
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
                    "is_db": is_db,
                    "db_type": db_type,
                    "recommended_hook": hook
                })

        return protectable_items
    except Exception as e:
        print(f"[ERROR] Error al inspeccionar datos protegibles: {e}")
        return []