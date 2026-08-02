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

---

# Estado actual

Versión:

v0.5.0-alpha7

Estado:

Motor principal, registro de backends y API unificada completamente funcionales. 
Cobertura de pruebas sólida con **57 tests unitarios y de integración pasando al 100%**.

Actualmente el sistema puede orquestar operaciones a través de la API REST y delegarlas correctamente en backends reales como Duplicati.

Operaciones verificadas y testeadas:

* detección de backends.
* autenticación.
* consulta de capacidades y estado.
* consulta de backups existentes.
* creación de trabajos remotos.
* **ejecución de copias de seguridad (Run).**
* **cancelación de copias en curso (Cancel).**

---

# Características implementadas

## Dashboard inicial

Estado:

Completado.

Funciones:

* visualización del estado interno.
* información del sistema.
* integración con servicios internos.

---

## Descubrimiento Docker

Estado:

Completado.

Funciones:

* detección de contenedores CasaOS.
* identificación de aplicaciones.
* generación de perfiles.

---

## Storage Intelligence

Estado:

Completado.

Funciones:

* detección de almacenamiento.
* resolución de recursos.
* validación de rutas.
* comprobación de accesibilidad.

---

## Backup Engine & API REST

Estado:

Completado.

Implementado:

* BackupPlan & BackupJob.
* BackupPlannerService & BackupJobBuilderService.
* BackendRegistry modular para inyección de conectores.
* Endpoints de estado (`/health`) y descubrimiento (`/backends`).
* Conexión completa con ejecución real (`/executions/run`).
* Sistema de interrupción de tareas (`/executions/cancel`).

---

# Backends

La arquitectura permite integrar diferentes motores.

Backends previstos:

* Duplicati (✅ Funcional).
* Restic.
* Borg.
* Rsync.

---

# Integración Duplicati

Estado:

Completada y Validada.

Arquitectura:

BackupBackend
      |
      v
DuplicatiBackend
      |
      v
DuplicatiJobBuilder
      |
      v
DuplicatiPayloadBuilder
      |
      v
DuplicatiClient
      |
      v
Duplicati REST API

---

# Operaciones Duplicati verificadas

## Autenticación y Estado

Funcionamiento validado mediante API REST y suite de tests.

---

## Obtener backups

Endpoint:

GET /api/v1/backups

Permite obtener ID, nombre, destino, programación, metadata y estado.

---

## Crear, Ejecutar y Cancelar trabajos

Endpoints API unificada:

POST /api/v1/executions/run
POST /api/v1/executions/cancel

Flujo validado de extremo a extremo:
1. El `BackupEngineService` prepara el manifiesto.
2. Se resuelve el backend mediante el `BackendRegistry`.
3. Se invoca el método correspondiente y se recupera el `execution_reference`.
4. El sistema interrumpe la tarea exitosamente usando el modelo de datos en mayúsculas (`{"operation": "CANCEL"}`).

---

# Tecnologías

Backend:

* Python 3.9
* FastAPI
* Jinja2 / Pydantic

Infraestructura:

* Docker
* Docker Compose

Integraciones:

* Docker SDK
* Duplicati REST API

Testing:

* pytest
* unittest.mock

---

# Estructura del proyecto

CasaOS-Backup-Manager/

├── app/
│   ├── api/
│   ├── connectors/
│   ├── core/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   └── templates/
│
├── docs/
├── scripts/
├── tests/
├── docker-compose.yml
├── Dockerfile
├── README.md
├── ARCHITECTURE.md
└── ROADMAP.md

---

# Desarrollo local

Construcción:

docker compose build

Arranque:

docker compose up -d

Parada:

docker compose down

Tests (con salida detallada de errores):

docker compose exec casaos-backup-manager pytest -v --tb=short

---

# Próxima fase

Dado que el motor interno de planificación ya está conectado exitosamente con la ejecución real (Duplicati) y probado al 100%, la siguiente etapa consiste en:

* Integración del Frontend (Interfaz de usuario).
* Seguimiento visual de las ejecuciones e historial.
* Preparación del empaquetado final para la tienda de aplicaciones de CasaOS.

---

# Licencia

Proyecto en desarrollo.
