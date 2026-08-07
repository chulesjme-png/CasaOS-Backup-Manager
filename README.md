# CasaOS Backup Manager

Gestor profesional de backups para CasaOS basado en arquitectura modular y Clean Architecture.

---

# Descripción

CasaOS Backup Manager es una plataforma de gestión de copias de seguridad diseñada para entornos CasaOS.

Su objetivo es proporcionar una capa inteligente entre las aplicaciones desplegadas en CasaOS, el sistema de archivos del host y diferentes motores de backup.

No es un simple script de copias; el sistema:

* Descubre aplicaciones y contenedores automáticamente.
* Analiza y valida rutas de almacenamiento persistente.
* Genera perfiles de aplicación y planes de resguardo.
* Construye trabajos de copia parametrizados.
* Delega la ejecución en backends especializados.
* Proporciona un dashboard visual con telemetría e identidad integrada.

---

# Arquitectura

El proyecto utiliza Clean Architecture dividiendo responsabilidades de forma desacoplada.

Flujo principal:

Docker Engine / Host System
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
BackupBackend (BackendRegistry)
      |
      v
Motor de backup externo (Duplicati / Restic)
      |
      v
UI Dashboard (FastAPI / Jinja2 / Bootstrap)

---

# Estado actual

**Versión:** `v0.5.0-alpha7`

**Estado:** 
Motor principal, interfaz de usuario con identidad de marca, registro de backends y API unificada completamente funcionales. 
Cobertura de pruebas sólida con **57 tests unitarios y de integración pasando al 100%**.

Actualmente el sistema permite la monitorización visual completa desde la web e interactuar con operaciones a través de la API REST delegadas en backends reales como Duplicati.

Capacidades verificadas y testeadas:

* Detección de backends y capacidades de motor.
* Identificación automática de contenedores y volúmenes de CasaOS.
* Visualización en panel Web con métricas en tiempo real.
* Consulta de copias existentes y estado de ejecución.
* **Ejecución de copias de seguridad (Run).**
* **Cancelación de copias en curso (Cancel).**

---

# Características implementadas

## Interfaz de Usuario e Identidad Visual

Estado: Completado e integrado.

Funciones:

* **Branding e Identidad:** Incorporación del logo oficial horizontal en el panel de control.
* **Header de Estado General:** Resumen rápido de SO, motores activos, apps detectadas y almacenamiento `/DATA` protegido.
* **Selector Dinámico de Destino:** Menú desplegable para alternar destinos de resguardo (Discos externos, NAS, SSD, USB).
* **Control Disaster Recovery:** Módulo para lanzar copias completas del sistema de la Raspberry Pi.
* **Perfiles de Aplicación:** Lista de perfiles detectados con accesos directos para ejecución individual.
* **Pestañas de Telemetría Dinámicas:** Monitoreo del sistema host (Debian/Raspberry Pi 5), Docker Daemon y almacenamiento montado.
* **Inspector Detallado:** Tablas colapsables para auditar contenedores Docker activos y rutas de datos protegibles (`/DATA/AppData` y *bind mounts*).

## Telemetría de Hardware (Raspberry Pi 5)

Estado: Completado y optimizado.

Funciones:

* Extracción directa de métricas de CPU, arquitectura (`aarch64`), versión de kernel y almacenamiento.
* Métrica de Memoria RAM en formato estructurado `Usado / Total (%)`.
* Resiliencia en Plantillas (Jinja2) mediante filtros `default(..., true)` para garantizar disponibilidad de datos en pantalla.

## Descubrimiento Docker & Storage Intelligence

Estado: Completado.

Funciones:

* Detección automática de contenedores activos e identificación de perfiles CasaOS.
* Resolución de rutas físicas en el host y validación de accesibilidad de almacenamiento.

## Backup Engine & API REST

Estado: Completado.

Implementado:

* `BackupPlan` & `BackupJob`.
* `BackendRegistry` modular para inyección de conectores.
* Endpoints de salud (`/health`), descubrimiento (`/backends`) y ejecución (`/executions/run` y `/executions/cancel`).
* Persistencia local en base de datos SQLite/FastAPI.

---

# Backends

La arquitectura permite integrar diferentes motores mediante conectores:

* **Duplicati Engine** (✅ Completamente funcional).
* **Restic Engine** (🔌 Preparado para integración).
* **Borg / Rsync** (📋 Planificados).

---

# Tecnologías

* **Backend:** Python 3.9 / FastAPI / Pydantic / Uvicorn.
* **Frontend:** HTML5 / Jinja2 / Bootstrap 5 / Vanilla JavaScript.
* **Infraestructura:** Docker / Docker Compose / Linux ARM64 (Debian GNU/Linux 12 - Raspberry Pi 5).
* **Integraciones:** Docker SDK / Duplicati REST API.
* **Testing:** Pytest / Unittest.mock (**57 tests pasando**).

---

# Estructura del proyecto

```text
CasaOS-Backup-Manager/
├── app/
│   ├── api/
│   ├── connectors/
│   ├── core/
│   ├── database/
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── static/
│   │   └── img/
│   │       └── logo-horizontal.svg
│   └── templates/
│       ├── base.html
│       ├── index.html
│       └── components/
├── docs/
├── scripts/
├── tests/
├── docker-compose.yml
├── Dockerfile
├── README.md
├── CHANGELOG.md
└── ROADMAP.md