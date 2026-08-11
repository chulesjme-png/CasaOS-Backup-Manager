import os
import docker

def get_active_app_profiles():
    """
    Escanea el daemon de Docker del host y valida la existencia real de aplicaciones.
    Filtra carpetas huérfanas en /DATA/AppData que pertenezcan a apps eliminadas.
    """
    active_profiles = []
    
    try:
        # Conexión al daemon de Docker del host
        client = docker.from_env()
        containers = client.containers.list(all=True)
        
        # Extraer nombres de contenedores activos/existentes
        running_container_names = set()
        for container in containers:
            # Limpiar el slash inicial que Docker añade a los nombres
            c_name = container.name.lstrip('/').lower()
            running_container_names.add(c_name)

        appdata_dir = "/DATA/AppData"
        
        if os.path.exists(appdata_dir):
            for entry in os.listdir(appdata_dir):
                full_path = os.path.join(appdata_dir, entry)
                
                if os.path.isdir(full_path):
                    app_name_lower = entry.lower()
                    
                    # Regla de oro: solo incluir si el contenedor existe en Docker
                    # o si es un componente conocido relacionado con un contenedor activo
                    if any(c_name in app_name_lower or app_name_lower in c_name for c_name in running_container_names):
                        profile = {
                            "name": entry.capitalize(),
                            "path": full_path,
                            "hook": "Hook DB" if "immich-server" in app_name_lower or "postgres" in app_name_lower else None
                        }
                        active_profiles.append(profile)

    except Exception as e:
        print(f"Error al escanear contenedores Docker: {e}")
        
    return active_profiles