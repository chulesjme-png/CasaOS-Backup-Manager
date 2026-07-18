# CHANGELOG

## v0.3.0-alpha1

### Added

- Introducido el modelo `ApplicationProfile`.
- Introducido el servicio `ApplicationProfileService`.
- Introducido el modelo `BackupPlan`.
- Introducido el servicio `BackupPlannerService`.
- Nuevo componente `application_profiles.html`.
- Nuevo componente `backup_plans.html`.
- El Dashboard ahora genera perfiles de aplicación automáticamente.
- El Dashboard genera un plan de backup para cada aplicación descubierta.
- Añadidas las variables de configuración:
  - `FEATURE_APPLICATION_PROFILES`
  - `FEATURE_BACKUP_PLANNER`

### Changed

- Actualizada la página principal (`index.html`) para mostrar:
  - Application Profiles
  - Backup Plans
- Refactorizado `DashboardService` para centralizar la generación de perfiles y planes de backup.
- Actualizada la versión de la aplicación a **v0.3.0-alpha1**.

---

## v0.2.0-alpha1

### Added

- Añadido `StorageResource`.
- Añadido el filtrado de mounts del sistema.
- Clasificación de Bind Mount y Docker Volume.
- Tabla de Backup Sources ampliada con Tipo, Backup y Motivo.