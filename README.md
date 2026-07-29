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

```
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
```

---

# Estado actual

Versión:

```
v0.5.0-alpha6
```

Estado:

Integración inicial real con Duplicati validada.

Actualmente el sistema puede comunicarse con un servidor Duplicati mediante API REST.

Operaciones verificadas:

* autenticación.
* consulta de backups existentes.
* creación de trabajos remotos.

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

## Backup Engine

Estado:

Parcialmente completado.

Implementado:

* BackupPlan.
* BackupJob.
* BackupPlannerService.
* BackupJobBuilderService.

Pendiente:

* conexión completa con ejecución real.
* gestión del ciclo completo del backup.

---

# Backends

La arquitectura permite integrar diferentes motores.

Backends previstos:

* Duplicati.
* Restic.
* Borg.
* Rsync.

---

# Integración Duplicati

Estado:

Validada.

Arquitectura:

```
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
```

---

# Operaciones Duplicati verificadas

## Autenticación

Funcionamiento validado mediante API REST.

---

## Obtener backups

Endpoint:

```
GET /api/v1/backups
```

Permite obtener:

* ID.
* nombre.
* destino.
* programación.
* metadata.
* estado.

Script utilizado:

```
scripts/test_duplicati_get_backups.py
```

Ejecutado con:

```
docker compose exec casaos-backup-manager python scripts/test_duplicati_get_backups.py
```

---

## Crear trabajos

Endpoint:

```
POST /api/v1/backups
```

Validado mediante:

```
scripts/test_duplicati_create_job.py
```

Resultado:

```
{
    "ID": "4",
    "Temporary": false
}
```

---

# Tecnologías

Backend:

* Python 3.9
* FastAPI
* Jinja2

Infraestructura:

* Docker
* Docker Compose

Integraciones:

* Docker SDK
* Duplicati REST API

Testing:

* pytest

---

# Estructura del proyecto

```
CasaOS-Backup-Manager/

├── app/
│   ├── api/
│   ├── connectors/
│   ├── core/
│   ├── models/
│   ├── routers/
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
```

---

# Desarrollo local

Construcción:

```
docker compose build
```

Arranque:

```
docker compose up -d
```

Parada:

```
docker compose down
```

Tests:

```
docker compose exec casaos-backup-manager pytest
```

---

# Próxima fase

La siguiente etapa del proyecto consiste en conectar el motor interno de planificación con la ejecución real.

Objetivo:

```
BackupPlan

    |

    v

BackupJob

    |

    v

DuplicatiBackend

    |

    v

DuplicatiClient

    |

    v

Backup ejecutado
```

Después se añadirá:

* seguimiento de ejecuciones.
* monitorización.
* historial.
* integración visual completa.
* nuevos motores de backup.

---

# Licencia

Proyecto en desarrollo.
