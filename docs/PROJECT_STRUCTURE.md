# PROJECT STRUCTURE

## Introducción

CasaOS Backup Manager sigue una arquitectura modular basada en Clean Architecture.

Cada directorio tiene una responsabilidad claramente definida, evitando dependencias innecesarias y facilitando la evolución del proyecto.

---

# Estructura general

```
app/
├── connectors/
├── core/
├── models/
├── routers/
├── services/
├── static/
├── templates/

config/

docs/

tests/
```

---

# Directorios

## app/

Contiene todo el código fuente de la aplicación.

Es el núcleo funcional del proyecto.

---

## app/connectors/

Responsable de la comunicación con sistemas externos.

Actualmente implementa:

```
connectors/
└── duplicati/
    └── duplicati_client.py
```

Reglas:

- Toda comunicación HTTP se implementa aquí.
- No contiene lógica de negocio.
- No conoce el Backup Engine.

---

## app/core/

Contiene los componentes fundamentales del motor.

Actualmente incluye:

```
core/
└── backends/
    ├── backup_backend.py
    ├── backend_factory.py
    ├── backend_registry.py
    ├── duplicati_backend.py
    └── null_backup_backend.py
```

Responsabilidades:

- Definir el contrato común de los backends.
- Registrar implementaciones.
- Seleccionar el backend adecuado.

---

## app/models/

Contiene todos los modelos de dominio.

Ejemplos:

- Application
- ApplicationProfile
- StorageResource
- BackupPlan
- BackupJob
- BackupManifest
- BackupExecutionRequest
- BackupResult
- BackendConfiguration

Los modelos representan datos del dominio y no contienen lógica de infraestructura.

---

## app/services/

Implementa la lógica de negocio del proyecto.

Servicios principales:

- DockerService
- DiskService
- AppDiscoveryService
- ApplicationProfileService
- StorageResolverService
- StorageValidationService
- BackupPlannerService
- BackupJobBuilderService
- BackupExecutionService
- BackupManifestBuilderService
- BackupRunnerService
- BackendConfigurationService
- BackupEngineService

Cada servicio tiene una única responsabilidad.

---

## app/routers/

Define los endpoints de FastAPI.

Los routers delegan toda la lógica en los servicios.

No contienen lógica de negocio.

---

## app/static/

Recursos estáticos utilizados por la interfaz web.

Ejemplos:

- CSS
- JavaScript
- Imágenes

---

## app/templates/

Plantillas HTML utilizadas por la aplicación.

No contienen lógica del Backup Engine.

---

## config/

Archivos de configuración del proyecto.

Incluye parámetros generales y configuración del entorno.

---

## docs/

Documentación técnica del proyecto.

Cada documento aborda un área específica:

- BACKUP_ENGINE.md
- BACKEND_DEVELOPMENT.md
- DOMAIN_MODELS.md
- PROJECT_STRUCTURE.md
- CONTRIBUTING.md

---

## tests/

Pruebas unitarias del proyecto.

Actualmente cubren:

- Modelos
- Servicios
- Backends
- Connectors
- Motor de ejecución

Todos los nuevos componentes deben incorporar sus correspondientes pruebas.

---

# Dependencias entre capas

La dirección permitida de las dependencias es:

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

Los modelos son compartidos por todas las capas y permanecen independientes de la infraestructura.

---

# Reglas de desarrollo

Durante el desarrollo deben mantenerse las siguientes normas:

- Clean Architecture.
- SOLID.
- Single Responsibility Principle.
- Tipado completo.
- Servicios pequeños y especializados.
- Modelos simples.
- Sin dependencias circulares.
- Sin acceso directo a Docker fuera de `DockerService`.
- Sin acceso directo a HTTP fuera de los Connectors.

---

# Evolución

La estructura del proyecto está preparada para incorporar nuevos backends sin modificar la organización existente.

Las futuras incorporaciones (Restic, Borg, Rsync, Kopia y otros motores) reutilizarán la misma arquitectura, manteniendo el dominio independiente de cualquier implementación concreta.