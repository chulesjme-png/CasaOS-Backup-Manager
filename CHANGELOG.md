# CHANGELOG

## v0.6.0-alpha1

### Added

* Incorporado el contrato común de resultados del Backup Engine mediante:

  * `BackupResult`

* Añadido `BackupRunnerService` como orquestador principal del flujo completo de ejecución.

* Adaptado el contrato `BackupBackend` para que todos los motores devuelvan un resultado normalizado mediante `BackupResult`.

* Actualizado `NullBackupBackend` como implementación de referencia del nuevo contrato de ejecución.

* Añadida prueba de integración del pipeline completo:

  * `BackupJob`
  * `BackupManifest`
  * `BackupExecutionRequest`
  * `BackupBackend`
  * `BackupResult`

### Changed

* Separada definitivamente la preparación del backup de la ejecución del backend.

* `BackupRunnerService` centraliza la coordinación entre:

  * `BackupEngineService`
  * `BackupExecutionService`
  * `BackendExecutionService`
  * `BackupBackend`

* Los backends pasan a utilizar un contrato común de resultados independientemente del motor utilizado.

* Consolidada la independencia del Backup Engine respecto a implementaciones concretas:

  * Duplicati
  * Restic
  * Borg
  * Rsync

### Fixed

* Corregido el acceso de `NullBackupBackend` a la información de aplicación utilizando el manifiesto asociado a la solicitud de ejecución.

* Ajustado el flujo interno para mantener la separación de responsabilidades entre:

  * `BackupExecutionRequest`
  * `BackupManifest`
  * `BackupResult`

* Validado el funcionamiento mediante:

  * `docker compose down`
  * `docker compose build --no-cache`
  * `docker compose up -d`
  * `docker compose exec casaos-backup-manager pytest -v`

* Confirmado:

  * Arranque correcto del contenedor.
  * Pipeline completo del Backup Engine operativo.
  * **8/8 pruebas superadas.**

### Architecture

Se completa la capa de ejecución abstracta del Backup Engine:

```text
BackupJob
        │
        ▼
BackupManifestBuilderService
        │
        ▼
BackupManifest
        │
        ▼
BackupExecutionService
        │
        ▼
BackupExecutionRequest
        │
        ▼
BackupRunnerService
        │
        ▼
BackendExecutionService
        │
        ▼
BackupBackend
        │
        ▼
BackupResult
        │
        ▼
Duplicati / Restic / Borg / Rsync