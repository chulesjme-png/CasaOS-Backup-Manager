"""
Servicio optimizado para Raspberry Pi / CasaOS.
Obtiene telemetría real del host y de Docker.
"""

import os
import shutil
import psutil
import docker


def get_real_system_info():
    """Obtiene métricas reales de hardware del host (Raspberry Pi)."""
    model_name = "Raspberry Pi (ARM)"
    
    # Intentar leer el cpuinfo del host montado en /host/proc
    proc_cpu_paths = ["/host/proc/cpuinfo", "/proc/cpuinfo"]
    for proc_cpu in proc_cpu_paths:
        try:
            if os.path.exists(proc_cpu):
                with open(proc_cpu, "r") as f:
                    for line in f:
                        if "Model" in line or "Hardware" in line or "model name" in line:
                            model_name = line.split(":")[1].strip()
                            break
                if model_name != "Raspberry Pi (ARM)":
                    break
        except Exception:
            pass

    # Detectar arquitectura real de la Raspberry Pi
    try:
        arch = os.uname().machine
    except Exception:
        arch = "aarch64"

    try:
        kernel = os.uname().release
    except Exception:
        kernel = "Linux"

    # Obtener memoria y CPUs reales
    mem = psutil.virtual_memory()
    cpus = psutil.cpu_count(logical=True) or 4

    return {
        "operating_system": f"CasaOS ({model_name})",
        "architecture": arch,
        "kernel_version": kernel,
        "cpus": cpus,
        "memory_gb": round(mem.total / (1024 ** 3), 2),
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