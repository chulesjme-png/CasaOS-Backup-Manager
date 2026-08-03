"""
Servicio optimizado para Raspberry Pi / CasaOS.
Obtiene telemetría real del host leyendo directamente /host/proc y el socket de Docker.
"""

import os
import shutil
import psutil
import docker


def get_real_system_info():
    """Obtiene métricas reales de hardware del host (Raspberry Pi)."""
    model_name = "Raspberry Pi (ARM)"
    
    # Lectura del procesador desde /host/proc/cpuinfo
    proc_cpu = "/host/proc/cpuinfo" if os.path.exists("/host/proc/cpuinfo") else "/proc/cpuinfo"
    cpus_count = 0
    
    if os.path.exists(proc_cpu):
        try:
            with open(proc_cpu, "r") as f:
                for line in f:
                    if "processor" in line:
                        cpus_count += 1
                    if "Model" in line or "Hardware" in line or "model name" in line:
                        model_name = line.split(":")[1].strip()
        except Exception:
            pass

    # Si no contó procesadores en cpuinfo, usamos psutil
    if cpus_count == 0:
        cpus_count = psutil.cpu_count(logical=True) or 4

    # Lectura de memoria real desde /host/proc/meminfo
    total_ram_gb = 0
    proc_mem = "/host/proc/meminfo" if os.path.exists("/host/proc/meminfo") else "/proc/meminfo"
    if os.path.exists(proc_mem):
        try:
            with open(proc_mem, "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        # MemTotal está en kB
                        kb_total = int(line.split(":")[1].replace("kB", "").strip())
                        total_ram_gb = round(kb_total / (1024 * 1024), 2)
                        break
        except Exception:
            pass

    if total_ram_gb == 0:
        total_ram_gb = round(psutil.virtual_memory().total / (1024 ** 3), 2)

    # Nombre del Kernel real del Host
    kernel = os.uname().release
    if os.path.exists("/host/proc/sys/kernel/osrelease"):
        try:
            with open("/host/proc/sys/kernel/osrelease", "r") as f:
                kernel = f.read().strip()
        except Exception:
            pass

    return {
        "operating_system": f"CasaOS ({model_name})",
        "architecture": os.uname().machine,
        "kernel_version": kernel,
        "cpus": cpus_count,
        "memory_gb": total_ram_gb,
        "hostname": "raspberrypi",
    }


def get_real_docker_info():
    """Obtiene información y lista de contenedores reales desde el Docker socket."""
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
            "hostname": version_info.get("Components", [{}])[0].get("Details", {}).get("KernelVersion", "raspberrypi"),
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
            "hostname": "raspberrypi",
            "containers_running": 0,
            "containers_stopped": 0,
            "images": 0,
            "volumes": 0,
            "networks": 0,
            "services_list": []
        }


def get_real_disk_info(path="/DATA"):
    """Obtiene uso real del disco mapeado de CasaOS."""
    # Buscar una ruta válida montada en el contenedor
    target_path = "/"
    for test_path in [path, "/mnt", "/DATA"]:
        if os.path.exists(test_path):
            try:
                stat = shutil.disk_usage(test_path)
                if stat.total > 0:
                    target_path = test_path
                    break
            except Exception:
                continue

    total, used, free = shutil.disk_usage(target_path)
    percent = round((used / total) * 100, 1) if total > 0 else 0
    
    return {
        "total_gb": round(total / (1024 ** 3), 1),
        "used_gb": round(used / (1024 ** 3), 1),
        "free_gb": round(free / (1024 ** 3), 1),
        "percent": percent
    }