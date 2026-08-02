"""
Servicio optimizado para Raspberry Pi / CasaOS.
Obtiene telemetría real del host y de Docker.
"""

import os
import shutil
import psutil
import docker


def get_real_system_info():
    """Obtiene métricas reales de hardware de la Raspberry Pi."""
    # Si estamos dentro de Docker en la Pi, usamos psutil apuntando al host si es posible,
    # o leemos directamente de /host/proc si está montado.
    
    model_name = "Raspberry Pi (ARM)"
    proc_cpu = "/host/proc/cpuinfo"
    
    try:
        if os.path.exists(proc_cpu):
            with open(proc_cpu, "r") as f:
                for line in f:
                    if "Model" in line or "Hardware" in line:
                        model_name = line.split(":")[1].strip()
                        break
    except Exception:
        pass

    # Forzar arquitectura ARM si estamos en la Pi, o leer la real del sistema
    arch = "aarch64" if os.uname().machine in ["aarch64", "armv7l"] else os.uname().machine
    kernel = os.uname().release

    return {
        "operating_system": f"CasaOS ({model_name})",
        "architecture": arch,
        "kernel_version": kernel,
        "cpus": psutil.cpu_count(logical=True) or 4,
        "memory_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "hostname": "raspberrypi",
    }


def get_real_docker_info():
    """Obtiene contenedores reales del Docker de CasaOS."""
    try:
        client = docker.DockerClient(base_url="unix://var/run/docker.sock")
        containers = client.containers.list(all=True)

        running_count = sum(1 for c in containers if c.status == "running")
        stopped_count = len(containers) - running_count

        services_list = []
        for c in containers:
            image_tag = c.image.tags[0] if c.image.tags else (c.image.id[:12] if c.image.id else "unknown")
            services_list.append({
                "name": c.name,
                "image": image_tag,
                "running": c.status == "running",
                "status": "En ejecución" if c.status == "running" else c.status.capitalize()
            })

        version_info = client.version()
        return {
            "available": True,
            "engine_version": version_info.get("Version", "24.0.2"),
            "api_version": version_info.get("ApiVersion", "1.43"),
            "containers_running": running_count,
            "containers_stopped": stopped_count,
            "images": len(client.images.list()),
            "volumes": len(client.volumes.list()),
            "networks": len(client.networks.list()),
            "services_list": services_list
        }
    except Exception as e:
        return {
            "available": False,
            "error": f"Error conectando a Docker Socket: {str(e)}",
            "engine_version": "N/A",
            "api_version": "N/A",
            "containers_running": 0,
            "containers_stopped": 0,
            "images": 0,
            "volumes": 0,
            "networks": 0,
            "services_list": []
        }


def get_real_disk_info(path="/DATA"):
    """Obtiene uso real del almacenamiento de CasaOS."""
    target_path = path if os.path.exists(path) else "/"
    total, used, free = shutil.disk_usage(target_path)
    percent = round((used / total) * 100, 1)
    return {
        "total_gb": round(total / (1024 ** 3), 1),
        "used_gb": round(used / (1024 ** 3), 1),
        "free_gb": round(free / (1024 ** 3), 1),
        "percent": percent
    }