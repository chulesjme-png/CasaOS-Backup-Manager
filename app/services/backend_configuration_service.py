"""
Servicio encargado de resolver la configuración
de un backend de backup.

Actualmente devuelve configuraciones por defecto
para cada backend soportado.

En futuras versiones podrá obtener la configuración desde:

- fichero YAML
- variables de entorno
- secretos
- base de datos
- configuración de CasaOS

Los backends nunca deben conocer el origen
de su configuración.
"""

from app.models.backend_configuration import (
    BackendConfiguration,
)


class BackendConfigurationService:
    """
    Servicio responsable de resolver la configuración
    asociada a un backend.
    """

    def get_configuration(
        self,
        backend_name: str,
    ) -> BackendConfiguration:
        """
        Devuelve la configuración correspondiente
        al backend solicitado.
        """

        if backend_name == "duplicati":
            return BackendConfiguration(
                backend_name="duplicati",
                enabled=True,
                configuration={
                    "url": "http://duplicati:8200",
                    "username": "",
                    "password": "",
                    "verify_ssl": False,
                    "timeout": 30,
                },
                metadata={
                    "display_name": "Duplicati",
                    "version": "default",
                },
            )

        if backend_name == "null":
            return BackendConfiguration(
                backend_name="null",
                enabled=True,
                configuration={},
                metadata={
                    "display_name": "Null Backend",
                },
            )

        return BackendConfiguration(
            backend_name=backend_name,
            enabled=False,
            configuration={},
            metadata={
                "reason": "Backend not registered",
            },
        )