# CHANGELOG

## v0.4.0-alpha4

### Added

* Incorporada la primera versión completa de **Storage Intelligence**.
* Añadido el campo `validation_status` al modelo `StorageResource`.
* Definidos los estados de validación:

  * `unknown`
  * `ready`
  * `missing`
  * `unreadable`
  * `empty`
  * `error`

### Changed

* `StorageValidationService` pasa a ser el único responsable de validar el estado de los recursos de almacenamiento.
* La validación utiliza `validation_path` como ruta principal de comprobación, manteniendo compatibilidad con `source` cuando es necesario.
* La validación se ha convertido en un proceso idempotente, reinicializando el estado del recurso antes de cada comprobación.
* `BackupPlannerService` utiliza `validation_status` para construir los planes de copia.
* `BackupJobBuilderService` consume directamente la información generada por el planificador, evitando duplicar reglas de negocio.
* El cálculo de `estimated_size` se realiza únicamente sobre los recursos preparados para copia.

### Fixed

* Diferenciación entre recursos inexistentes, inaccesibles, vacíos y preparados para copia.
* Eliminada la acumulación de errores de validación entre ejecuciones consecutivas.
* Recuperada la compatibilidad completa con Python 3.9 sustituyendo el uso de `match/case` por estructuras `if/elif`.
* Validado el funcionamiento mediante:

  * `docker compose down`
  * `docker compose build --no-cache`
  * `docker compose up`
* Confirmado el arranque correcto del Dashboard y del servicio FastAPI.

### Architecture

Se consolida definitivamente el flujo principal del Backup Engine:

```text
Docker Engine
        │
        ▼
AppDiscoveryService
        │
        ▼
ApplicationProfileService
        │
        ▼
StorageResolverService
        │
        ▼
StorageValidationService
        │
        ▼
BackupPlannerService
        │
        ▼
BackupPlan
        │
        ▼
BackupJobBuilderService
        │
        ▼
BackupJob
```

La inteligencia de validación reside exclusivamente en `StorageValidationService`. Los servicios posteriores consumen el resultado de la validación sin reinterpretar reglas de negocio.

---

## v0.4.0-alpha1

### Added

* Iniciada la fase de desarrollo del Backup Engine.
* Añadida la documentación base del proyecto:

  * `ROADMAP.md`
  * `ARCHITECTURE.md`
* Definido el concepto de `BackupJob` como trabajo de copia resuelto.

### Changed

* Separada conceptualmente la planificación (`BackupPlan`) de la preparación de ejecución (`BackupJob`).
* Definida la independencia del núcleo del Backup Engine respecto a los motores de ejecución:

  * Duplicati
  * Restic
  * Borg
  * Rsync
* Preparada la separación entre resolución de almacenamiento y lógica del motor de backup.

### Fixed

* Detectada una corrupción del dominio `models` provocada por la sobrescritura accidental de varios modelos Python con plantillas HTML.
* Restaurados completamente los modelos:

  * `Application`
  * `Container`
  * `ApplicationProfile`
  * `BackupPlan`
* Verificados todos los imports del dominio antes de la reparación para asegurar que no existían implementaciones alternativas.
* Recuperada la coherencia entre los modelos del dominio y los servicios que los utilizan.
* Validada la reparación mediante:

  * `docker compose down`
  * `docker compose build --no-cache`
  * `docker compose up`
* Confirmado el arranque correcto de la aplicación sin errores de importación ni de sintaxis.

### Architecture

* Consolidada la evolución del flujo principal:

```text
Docker
    │
    ▼
Application Discovery
    │
    ▼
Application
    │
    ▼
ApplicationProfile
    │
    ▼
BackupPlan
    │
    ▼
BackupJob
    │
    ▼
Execution Backend
```
