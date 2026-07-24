# ROADMAP

Estado actual del desarrollo de CasaOS Backup Manager.

---

# Versión actual

**v0.5.0-alpha6**

Estado:

✅ Infraestructura del Backup Engine completada.

---

# Completado

## Fase 1 — Descubrimiento

- DockerService
- AppDiscoveryService
- ApplicationProfileService

Estado:

✅ Completada

---

## Fase 2 — Storage Intelligence

- StorageResolverService
- StorageValidationService

Estado:

✅ Completada

---

## Fase 3 — Backup Planning

- BackupPlannerService
- BackupJobBuilderService

Estado:

✅ Completada

---

## Fase 4 — Backup Engine Infrastructure

Implementado:

- BackupExecutionService
- BackupManifestBuilderService
- BackupRunnerService
- BackendConfigurationService
- BackendFactory
- BackendRegistry
- NullBackend
- DuplicatiBackend
- DuplicatiClient
- BackupResult

Estado:

✅ Completada

---

# Próximo sprint

## Duplicati Capability Detection

Objetivos:

- Crear `DuplicatiCapabilities`.
- Detectar automáticamente las capacidades del servidor.
- Aislar completamente el Backup Engine de la API de Duplicati.
- Preparar la compatibilidad con futuras versiones del backend.

Estado:

🔄 Próximo desarrollo.

---

# Roadmap

Después de completar la detección de capacidades se continuará con:

1. Backup Definition Builder
2. Duplicati Job Builder
3. Backup Launcher
4. Progress Monitor
5. Log Parser
6. Restore Engine
7. Multi-backend Support
8. Scheduler
9. Notification System

---

# Objetivo final

Construir un Backup Engine profesional, independiente del motor de copia de seguridad, donde Duplicati sea únicamente la primera implementación de una arquitectura preparada para soportar múltiples backends (Duplicati, Restic, Borg, Rsync, Kopia y futuros motores).