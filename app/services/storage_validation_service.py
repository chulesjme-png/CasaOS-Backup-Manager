import os

from app.models.storage_resource import StorageResource


class StorageValidationService:
    """
    Servicio encargado de validar el estado real de los recursos
    de almacenamiento detectados.

    Comprueba:

    - existencia del recurso
    - permisos de lectura
    - tamaño aproximado
    - errores encontrados

    No decide si un recurso debe incluirse en backup.
    Esa responsabilidad pertenece a StorageResolverService.
    """

    def validate(
        self,
        resources: list[StorageResource],
    ) -> list[StorageResource]:

        validated_resources = []

        for resource in resources:

            if not resource.backup_candidate:
                validated_resources.append(resource)
                continue

            self._validate_resource(resource)

            validated_resources.append(resource)

        return validated_resources


    def _validate_resource(
        self,
        resource: StorageResource,
    ):

        path = (
            resource.validation_path
            or resource.source
        )


        if not path:

            resource.validation_errors.append(
                "Ruta de validación vacía"
            )

            return


        if not os.path.exists(path):

            resource.exists = False

            resource.validation_errors.append(
                "Ruta inexistente"
            )

            return


        resource.exists = True


        if os.access(
            path,
            os.R_OK,
        ):

            resource.readable = True

        else:

            resource.readable = False

            resource.validation_errors.append(
                "Permiso insuficiente de lectura"
            )


        try:

            resource.size = self._calculate_size(
                path
            )

        except Exception as error:

            resource.validation_errors.append(
                f"Error calculando tamaño: {error}"
            )


    def _calculate_size(
        self,
        path: str,
    ) -> int:

        total_size = 0


        if os.path.isfile(path):

            return os.path.getsize(path)


        for root, _, files in os.walk(path):

            for filename in files:

                filepath = os.path.join(
                    root,
                    filename,
                )

                try:

                    total_size += os.path.getsize(
                        filepath
                    )

                except OSError:

                    continue


        return total_size