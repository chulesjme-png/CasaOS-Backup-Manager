import docker


def get_docker_status():
    """
    Obtiene información general del motor Docker.
    """

    try:
        client = docker.from_env()

        info = client.info()
        version = client.version()

        containers = client.containers.list(all=True)

        running = len([c for c in containers if c.status == "running"])
        stopped = len(containers) - running

        return {
            "available": True,
            "version": version.get("Version"),
            "running_containers": running,
            "stopped_containers": stopped,
            "images": len(client.images.list()),
            "volumes": len(client.volumes.list().volumes or []),
            "networks": len(client.networks.list()),
        }

    except Exception:

        return {
            "available": False,
            "version": None,
            "running_containers": 0,
            "stopped_containers": 0,
            "images": 0,
            "volumes": 0,
            "networks": 0,
        }