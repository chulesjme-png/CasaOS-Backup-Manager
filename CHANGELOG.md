# CHANGELOG

## v0.4.0-alpha1

### Added

- Iniciada la fase de desarrollo del Backup Engine.
- Añadida la documentación base del proyecto:
  - `ROADMAP.md`
  - `ARCHITECTURE.md`
- Definido el concepto de `BackupJob` como trabajo de copia resuelto.

### Changed

- Separada conceptualmente la planificación (`BackupPlan`) de la preparación de ejecución (`BackupJob`).
- Definida la independencia del núcleo del Backup Engine respecto a los motores de ejecución:
  - Duplicati
  - Restic
  - Borg
  - Rsync
- Preparada la separación entre resolución de almacenamiento y lógica del motor de backup.

### Fixed

- Detectada una corrupción del dominio `models` provocada por la sobrescritura accidental de varios modelos Python con plantillas HTML.
- Restaurados completamente los modelos:
  - `Application`
  - `Container`
  - `ApplicationProfile`
  - `BackupPlan`
- Verificados todos los imports del dominio antes de la reparación para asegurar que no existían implementaciones alternativas.
- Recuperada la coherencia entre los modelos del dominio y los servicios que los utilizan.
- Validada la reparación mediante:
  - `docker compose down`
  - `docker compose build --no-cache`
  - `docker compose up`
- Confirmado el arranque correcto de la aplicación sin errores de importación ni de sintaxis.

### Architecture

- Consolidada la evolución del flujo principal:

```
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