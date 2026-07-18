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

### Architecture

- Consolidada la evolución del flujo principal:
