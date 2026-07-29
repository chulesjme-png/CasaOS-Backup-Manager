"""
Constructor del payload REST para Duplicati.

Responsabilidad:

Traducir el modelo interno DuplicatiJob al formato esperado
por la API REST de Duplicati.

No realiza llamadas HTTP.
No conoce autenticación.
No conoce requests.
No conoce CasaOS.

Pertenece a la capa de conectores porque adapta
el modelo interno al contrato externo de Duplicati.
"""

from typing import Any

from app.models.duplicati_job import DuplicatiJob


class DuplicatiPayloadBuilder:
    """
    Construye payloads compatibles con la API REST de Duplicati.
    """

    def build(
        self,
        job: DuplicatiJob,
    ) -> dict[str, Any]:
        """
        Convierte un DuplicatiJob en un payload REST.
        """

        settings = []

        self._append_setting(
            settings,
            "encryption-module",
            job.encryption,
        )

        self._append_setting(
            settings,
            "passphrase",
            job.passphrase,
        )

        self._append_setting(
            settings,
            "compression-module",
            job.compression,
        )

        self._append_setting(
            settings,
            "retention-policy",
            job.retention_policy,
        )

        for key, value in job.options.items():

            self._append_setting(
                settings,
                key,
                value,
            )

        filters = []

        options = job.metadata.get(
            "filters",
            [],
        )

        if options:

            filters.extend(
                options
            )

        return {
            "Backup": {

                "Name": job.name,

                "Description": (
                    job.description
                ),

                "TargetURL": (
                    job.destination_url
                ),

                "Sources": list(
                    job.source_paths
                ),

                "Settings": settings,

                "Filters": filters,
            },

            "Schedule": (
                job.schedule
                or {}
            ),
        }

    def _append_setting(
        self,
        settings: list[dict[str, Any]],
        name: str,
        value: Any,
    ) -> None:
        """
        Añade una configuración si tiene valor.
        """

        if value is None:
            return

        if value == "":
            return

        settings.append(
            {
                "Name": name,
                "Value": value,
            }
        )