# Changelog

Historial de cambios de CasaOS Backup Manager.

---

# v0.5.0-alpha7 - Backup Engine & Execution Integration

Fecha: 02/08/2026

## Added

* Conexión completa del flujo del `Backup Engine` con el backend real de Duplicati.
* Implementación de los endpoints de la API para ejecución (`/api/v1/executions/run`) y cancelación (`/api/v1/executions/cancel`).
* Creación del sistema de persistencia y base de datos local (`app/database/`).
* Registro centralizado de backends mediante `BackendRegistry`.
* Cobertura de pruebas completa alcanzando **57 tests en verde** (incluyendo pruebas de routers, servicios y clientes de Duplicati).

## Fixed

* Corrección de tipos en mayúsculas/minúsculas para el modelo de cancelación (`BackupOperationType.CANCEL`).

---

# v0.5.0-alpha6 - Duplicati REST Integration Validation

Fecha: 28/07/2026

## Added

* Validación de comunicación real con servidor Duplicati mediante API REST.
* Autenticación, lectura de backups y creación de trabajos remotos.
