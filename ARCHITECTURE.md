# ARCHITECTURE

## Introducción

CasaOS Backup Manager está diseñado siguiendo los principios de **Clean Architecture**, con una estructura modular y desacoplada que permite integrar distintos motores de backup sin modificar el núcleo del sistema.

La arquitectura está organizada en capas, donde cada componente tiene una única responsabilidad y las dependencias fluyen siempre en la misma dirección.

---

# Arquitectura general

```
Docker Engine
        │
        ▼
DockerService
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
BackupJobBuilderService
        │
        ▼
BackupExecutionService
        │
        ▼
BackupManifestBuilderService
        │
        ▼
BackupRunnerService
        │
        ▼
BackendFactory
        │
        ▼
BackupBackend
   ├── NullBackupBackend
   └── DuplicatiBackend
        │
        ▼
Connector
        │
        ▼
Motor de Backup
```

---

# Capas del sistema

## Descubrimiento

Responsable de detectar las aplicaciones instaladas y obtener la información necesaria para construir un perfil de backup.

Componentes principales:

- DockerService
- AppDiscoveryService
- ApplicationProfileService

---

## Storage Intelligence

Analiza y valida todos los recursos de almacenamiento asociados a una aplicación.

Componentes:

- StorageResolverService
- StorageValidationService

---

## Planificación

Genera un plan de backup independiente del backend que finalmente realizará la copia.

Componentes:

- BackupPlannerService
- BackupJobBuilderService

---

## Backup Engine

Coordina la ejecución completa del proceso de backup.

Componentes:

- BackupExecutionService
- BackupManifestBuilderService
- BackupRunnerService

---

## Backends

Implementan la integración con un motor de backup concreto.

Actualmente:

- NullBackupBackend
- DuplicatiBackend

En el futuro:

- ResticBackend
- BorgBackend
- RsyncBackend
- KopiaBackend

---

## Connectors

Encapsulan toda la comunicación con sistemas externos.

Actualmente:

- DuplicatiClient

Los Connectors son el único punto autorizado para realizar llamadas HTTP o interactuar con APIs externas.

---

# Principios arquitectónicos

La arquitectura del proyecto sigue las siguientes reglas:

- Clean Architecture.
- SOLID.
- Single Responsibility Principle.
- Dependency Inversion.
- Bajo acoplamiento.
- Alta cohesión.

Cada componente debe tener una única responsabilidad claramente definida.

---

# Dirección de las dependencias

Las dependencias siempre fluyen en una única dirección:

```
Routers
        │
        ▼
Services
        │
        ▼
Core
        │
        ▼
Connectors
```

Los modelos del dominio son compartidos entre las distintas capas y permanecen independientes de la infraestructura.

---

# Evolución

La arquitectura ha sido diseñada para permitir la incorporación de nuevos motores de backup sin modificar el dominio del proyecto.

Los próximos desarrollos comenzarán con la detección automática de capacidades del backend (**Duplicati Capability Detection**), seguida de la implementación de la ejecución real de copias de seguridad.