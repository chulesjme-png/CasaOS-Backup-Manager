from app.models.storage_resource import StorageResource


class StorageResolverService:
    """
    Servicio encargado de resolver los recursos de almacenamiento
    utilizados por una aplicación.

    Convierte los mounts detectados por Docker en StorageResource
    y determina si son candidatos iniciales para backup.

    Este servicio NO valida el estado real del recurso.
    La validación de existencia, permisos y tamaño corresponde
    a StorageValidationService.
    """

    EXCLUDED_PATHS = [
        "/var/run/docker.sock",
        "/proc",
        "/sys",
        "/dev",
    ]

    def resolve(self, application):
        """
        Devuelve la lista de StorageResource asociados
        a una aplicación.
        """

        resources = []

        mounts = application.get("mounts", [])

        for mount in mounts:

            source = mount.get("source", "")
            destination = mount.get("destination", "")

            backup_candidate, reason = (
                self._is_backup_candidate(
                    source,
                    destination,
                )
            )

            resources.append(
                StorageResource(
                    application=application["name"],
                    source=source,
                    destination=destination,
                    storage_type=mount.get(
                        "type",
                        "bind",
                    ),
                    backup_candidate=backup_candidate,
                    ignore_reason=reason,

                    # Ruta accesible desde el contexto
                    # donde se ejecuta el servicio.
                    validation_path=destination,
                )
            )

        return resources

    def _is_backup_candidate(
        self,
        source: str,
        destination: str,
    ):
        """
        Determina si un recurso debe participar en un backup.
        """

        if not source:

            return (
                False,
                "Ruta de origen vacía",
            )

        for excluded in self.EXCLUDED_PATHS:

            if (
                source == excluded
                or destination == excluded
            ):

                return (
                    False,
                    f"Recurso excluido: {excluded}",
                )

        return (
            True,
            None,
        )