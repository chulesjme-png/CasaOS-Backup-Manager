# CasaOS Backup Manager - Architecture

Documento de arquitectura técnica del proyecto.

Fecha actualización: 03/08/2026

---

# 1. Objetivo del proyecto

CasaOS Backup Manager es un sistema profesional de gestión de backups diseñado para CasaOS.

El objetivo es proporcionar una capa inteligente entre las aplicaciones desplegadas en CasaOS y los diferentes motores de backup.

El sistema NO es un script de copias.

Es una plataforma de gestión que:

* descubre aplicaciones.
* analiza almacenamiento.
* genera planes de backup.
* construye trabajos.
* delega la ejecución en backends especializados.
* monitoriza estados.
* expone información mediante dashboard.

---

# 2. Principios arquitectónicos

El proyecto sigue Clean Architecture.

Principios principales:

* Separación estricta de responsabilidades.
* Servicios independientes.
* Modelos internos desacoplados de tecnologías externas.
* Los conectores externos adaptan contratos.
* Los backends ejecutan operaciones específicas.
* El dashboard únicamente visualiza información del sistema.

---

# 3. Arquitectura general

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
      +----------------+
      |                |
      v                v
Duplicati        Restic/Borg/Rsync
Backend          Backend

---

# 4. Capas del sistema

## Core

Contiene la lógica principal del sistema.

Responsabilidades:

* planificación de backups.
* resolución de recursos.
* creación de planes.
* construcción de trabajos.

No conoce:

* Docker.
* HTTP.
* APIs externas.

---

## Models

Modelos internos del dominio.

Ejemplos:

* Application
* ApplicationProfile
* StorageResource
* BackupPlan
* BackupJob
* DuplicatiJob

Los modelos representan información del sistema.

No contienen:

* llamadas externas.
* lógica de infraestructura.
* autenticación.

---

## Services

Servicios de aplicación.

Ejemplos:

## AppDiscoveryService

Descubre aplicaciones existentes en CasaOS mediante Docker.

Responsabilidad:

* obtener contenedores.
* identificar aplicaciones.
* crear modelos Application.

---

## StorageResolverService

Analiza recursos de almacenamiento disponibles.

Responsabilidad:

* detectar rutas.
* resolver volúmenes.
* identificar recursos candidatos.

---

## StorageValidationService

Valida recursos encontrados.

Comprueba:

* existencia.
* permisos.
* lectura.
* disponibilidad.

---

## BackupPlannerService

Genera planes de backup.

Responsabilidad:

Transformar:

ApplicationProfile + StorageResource

en:

BackupPlan

---

## BackupJobBuilderService

Construye trabajos ejecutables.

Transforma:

BackupPlan

en:

BackupJob

---

# 5. Arquitectura de Backends

Los backends abstraen motores externos de backup.

Contrato principal:

BackupBackend
      |
      |
      +----------------+
      |                |
      v                v
DuplicatiBackend   ResticBackend

Un backend debe encargarse de:

* traducir trabajos internos.
* comunicarse con el motor externo.
* ejecutar operaciones.
* devolver resultados.

No debe:

* descubrir aplicaciones.
* decidir qué copiar.
* gestionar interfaz gráfica.

---

# 6. Integración Duplicati

Estado:

COMPLETA Y VALIDADA (Conectada al Backup Engine y API)

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

# 7. DuplicatiClient

Ubicación:

app/connectors/duplicati/

Responsabilidad:

Comunicación HTTP con Duplicati.

Funciones principales:

* autenticación.
* gestión de sesión.
* llamadas REST.
* gestión de errores.

No conoce:

* CasaOS.
* Docker.
* Backup Engine.
* reglas de negocio.

Operaciones validadas:

* `authenticate()`
* `get_backups()`
* `create_job()`
* `run_backup()`
* `cancel_task()`

---

# 8. DuplicatiPayloadBuilder

Responsabilidad:

Adaptar modelos internos al formato REST esperado por Duplicati.

Entrada:

DuplicatiJob

Salida:

REST Payload

---

# 9. Infraestructura y Despliegue Docker (ARM64 / Raspberry Pi 5)

Arquitectura de Red y Telemetría:

* Contenedor FastAPI expuesto en puerto de la app `8000` (mapeado al anfitrión en `8088`).
* Acceso directo al socket de Docker (`/var/run/docker.sock`) para el `AppDiscoveryService`.
* Acceso a volúmenes de telemetría de Kernel y procesador (`/proc`, `/sys`) mapeados a `/host/proc` y `/host/sys` para soporte ARM64 nativo en Raspberry Pi 5.
* Acceso de lectura al almacenamiento `/DATA` y `/var/lib/casaos` para análisis del `StorageResolverService`.

---

# 10. Estado actual del desarrollo

Versión:

v0.5.0-alpha7

Estado:

Integración completa entre el Backup Engine, la API REST y el backend de Duplicati validada en hardware real (Raspberry Pi 5) y con **57 tests automatizados en verde**.

Completado:

* arquitectura Clean Architecture.
* descubrimiento Docker y Storage Intelligence.
* Backup Engine completo y conectado.
* infraestructura de backends con `BackendRegistry`.
* ejecución (`/executions/run`) y cancelación (`/executions/cancel`) operativas.
* telemetría del sistema y hardware en tiempo real.

---

# 11. Tecnologías utilizadas

Backend:

* Python 3.9
* FastAPI / Uvicorn
* Pydantic
* SQLite / SQLAlchemy (Persistencia de base de datos)

Despliegue:

* Docker / Docker Compose
* Debian / Linux ARM64 (Raspberry Pi 5)

Testing:

* pytest (57 pruebas unitarias y de integración)

---

# 12. Próxima fase

La siguiente etapa consiste en:

* Integración del Frontend (Dashboard visual).
* Seguimiento visual de ejecuciones e historial.
* Empaquetado definitivo para la tienda de aplicaciones de CasaOS.