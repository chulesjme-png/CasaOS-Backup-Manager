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
* Construye trabajos de copia parametrizados con **DB Hooks** para bases de datos en caliente.
* Notifica el avance en tiempo real mediante **WebSockets**.
* Mantiene un **Historial de Auditoría** en SQLite de las operaciones realizadas.
* Delega la ejecución en backends especializados y respalda en almacenamiento externo físico.
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
ApplicationProfileService (DB Hooks Integration)
      |
      v
StorageResolverService & Propagation (:rshared)
      |
      v
BackupPlannerService
      |
      v
BackupJobBuilderService
      |
      v
BackupBackend / TarGz Engine
      |
      +---> AuditLogService (SQLite history.db)
      +---> WebSocketNotifier (/ws/progress)
      |
      v
UI Dashboard (FastAPI / Jinja2 / WebSockets / Bootstrap 5)

---

# Estado actual

**Versión:** `v0.5.0-beta1`

**Estado:** 
Motor principal, auditoría SQLite, transmisión WebSocket en tiempo real, DB Hooks de consistencia, gestión de volúmenes externos y registro de backends completamente funcionales. 
Cobertura de pruebas sólida con **57 tests unitarios y de integración pasando al 100%**.

Actualmente el sistema permite la monitorización visual completa, la ejecución de respaldos individuales o completos, el seguimiento del porcentaje de avance en directo y la consulta histórica de operaciones.

Capacidades verificadas y testeadas:

* Detección automática de contenedores y volúmenes de CasaOS (`/DATA/AppData`).
* **Database Hooks:** Volcados SQLite en caliente antes del empaquetado para evitar corrupción de datos.
* **Escritura directa en almacenamiento USB/Externo:** Soporte de montajes dinámicos mediante propagación `:rshared` y modo privilegiado.
* **Progreso en Tiempo Real:** Actualizaciones instantáneas vía WebSockets en el panel web.
* **Módulo de Auditoría e Historial:** Registro persistente de ejecuciones en SQLite.
* Visualización en panel Web con métricas en tiempo real.
* **Ejecución y gestión de respaldos por aplicación y Disaster Recovery.**

---

# Características implementadas

## Interfaz de Usuario e Identidad Visual

Estado: Completado e integrado.

Funciones:

* **Branding e Identidad:** Incorporación del logo oficial horizontal en el panel de control.
* **Header de Estado General:** Resumen rápido de SO, motores activos, apps detectadas y almacenamiento `/DATA` protegido.
* **Historial de Ejecuciones (Modal):** Vista detallada del registro de auditoría (Fecha/Hora, Tipo, Aplicación, Estado, Duración) con opción de limpieza de logs.
* **Feedback en Tiempo Real:** Barra de progreso y toasts flotantes alimentados mediante canal WebSocket.
* **Selector Dinámico de Destino:** Menú desplegable para alternar destinos de resguardo (Discos externos en `/media`, `/mnt`, NAS, SSD).
* **Control Disaster Recovery:** Módulo para lanzar copias completas del sistema de la Raspberry Pi.
* **Perfiles de Aplicación:** Lista de perfiles detectados con accesos directos para ejecución individual.
* **Pestañas de Telemetría Dinámicas:** Monitoreo del sistema host (Debian/Raspberry Pi 5), Docker Daemon y almacenamiento montado.

## Telemetría de Hardware (Raspberry Pi 5)

Estado: Completado y optimizado.

Funciones:

* Extracción directa de métricas de CPU, arquitectura (`aarch64`), versión de kernel y almacenamiento.
* Métrica de Memoria RAM en formato estructurado `Usado / Total (%)`.
* Resiliencia en Plantillas (Jinja2) mediante filtros `default(..., true)` para garantizar disponibilidad de datos en pantalla.

## Descubrimiento Docker & DB Hooks Intelligence

Estado: Completado.

Funciones:

* Detección automática de contenedores activos e identificación de perfiles CasaOS.
* Resolución de rutas físicas en el host y propagación de puntos de montaje.
* **DB Hooks:** Detección automática de bases de datos SQLite y ejecución de comandos `sqlite3 .backup` o `.dump` en caliente.

## Backup Engine, WebSockets & Audit System

Estado: Completado.

Implementado:

* `BackupPlan` & `BackupJob`.
* Registro de Auditoría persistente en SQLite (`app/database/history.db`).
* Notificador WebSocket (`/api/v1/ws/progress`).
* Endpoints de salud (`/health`), descubrimiento (`/backends`), logs (`/api/v1/logs`) y ejecución (`/api/v1/backups/run-app/{app_name}`).

---

# Backends y Motores

La arquitectura permite integrar diferentes motores mediante conectores:

* **TAR.GZ Local Engine & DB Hooks** (✅ Completamente funcional y optimizado para `/media`).
* **Duplicati Engine** (✅ Completamente funcional).
* **Restic Engine** (🔌 Preparado para integración).
* **Borg / Rsync** (📋 Planificados).

---

# Tecnologías

* **Backend:** Python 3.11 / FastAPI / Pydantic / Uvicorn / SQLite.
* **Frontend:** HTML5 / Jinja2 / Bootstrap 5 / Vanilla JavaScript / WebSockets API.
* **Infraestructura:** Docker / Docker Compose (`privileged`, `:rshared`) / Linux ARM64 (Debian GNU/Linux 12 - Raspberry Pi 5).
* **Integraciones:** Docker SDK / Duplicati REST API / SQLite3 CLI.
* **Testing:** Pytest / Unittest.mock (**57 tests pasando**).

---

# Estructura del proyecto

```text
CasaOS-Backup-Manager/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       └── websocket.py
│   ├── connectors/
│   ├── core/
│   ├── database/
│   │   └── history.db
│   ├── models/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   │   ├── audit_service.py
│   │   ├── backup_service.py
│   │   └── db_hooks_service.py
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