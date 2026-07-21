# CasaOS Backup Manager - Roadmap

## Estado actual

**Versión:**

v0.6.0-alpha1

**Fase:**

Backup Engine ejecución abstracta validada

---

# Objetivo del proyecto

CasaOS Backup Manager tiene como objetivo construir un sistema profesional de copias de seguridad para entornos CasaOS.

La aplicación debe ser capaz de:

1. Detectar aplicaciones instaladas.
2. Analizar sus recursos.
3. Crear perfiles de backup.
4. Generar planes de copia.
5. Resolver trabajos de backup.
6. Preparar manifiestos de ejecución.
7. Ejecutar copias mediante diferentes backends.
8. Restaurar aplicaciones completas.

---

# Arquitectura actual

Flujo principal:

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
BackendFactory
        │
        ▼
BackendRegistry
        │
        ▼
BackupBackend
        │
        ▼
BackupResult
        │
        ▼
Duplicati / Restic / Borg / Rsync