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