# CasaOS Backup Manager

Gestor profesional de backups para CasaOS basado en arquitectura modular y Clean Architecture.

---

# Descripción

CasaOS Backup Manager es una plataforma de gestión de copias de seguridad diseñada para entornos CasaOS.

Su objetivo es proporcionar una capa inteligente entre las aplicaciones desplegadas en CasaOS y diferentes motores de backup.

No es un script de copias.

El sistema:

* descubre aplicaciones.
* analiza almacenamiento.
* genera planes de backup.
* construye trabajos.
* delega ejecución en backends especializados.
* monitoriza estados.
* proporciona una interfaz visual.

---

# Arquitectura

El proyecto utiliza Clean Architecture.

Flujo principal:

```text
Docker Engine
      |
      v
AppDiscoveryService
      |
      v
ApplicationProfileService
      |
      v
ApplicationProfile
      |
      v
StorageResolverService
      |
      v
StorageResource
      |
      v
StorageValidationService
      |
      v
BackupPlannerService
      |
      v
BackupPlan
      |
      v
BackupJobBuilderService
      |
      v
BackupJob
      |
      v
BackupBackend
      |
      v
Motor de backup externo