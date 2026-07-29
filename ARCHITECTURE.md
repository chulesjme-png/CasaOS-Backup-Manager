# CasaOS Backup Manager - Architecture

Documento de arquitectura técnica del proyecto.

Fecha actualización: 28/07/2026

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
      +----------------+
      |                |
      v                v
Duplicati        Restic/Borg/Rsync
Backend          Backend
```

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

```
BackupBackend
      |
      |
      +----------------+
      |                |
      v                v
DuplicatiBackend   ResticBackend
```

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

VALIDADA

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

# 7. DuplicatiClient

Ubicación:

```
app/connectors/duplicati/
```

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

```
authenticate()

get_backups()

create_job()
```

---

# 8. DuplicatiPayloadBuilder

Responsabilidad:

Adaptar modelos internos al formato REST esperado por Duplicati.

Entrada:

```
DuplicatiJob
```

Salida:

```
REST Payload
```

No realiza:

* HTTP.
* autenticación.
* ejecución.

---

# 9. DuplicatiJob

Modelo interno de trabajo Duplicati.

Características:

* independiente de REST.
* independiente del transporte.
* representa una definición de backup.

Contiene:

* nombre.
* fuentes.
* destino.
* cifrado.
* compresión.
* retención.
* opciones.
* metadata.

---

# 10. Estado actual del desarrollo

Versión:

```
v0.5.0-alpha6
```

Estado:

Integración inicial real con Duplicati validada.

Completado:

* arquitectura Clean Architecture.
* dashboard inicial.
* descubrimiento Docker.
* Storage Intelligence inicial.
* Backup Engine inicial.
* infraestructura de backends.
* connector Duplicati.
* autenticación REST.
* lectura de backups.
* creación de trabajos remotos.

Pendiente:

* integración completa DuplicatiBackend con Backup Engine.
* ejecución remota de backups.
* seguimiento de tareas.
* monitorización de estados.
* sincronización de resultados.
* integración final con dashboard.

---

# 11. Tecnologías utilizadas

Backend:

* Python 3.9
* FastAPI
* Jinja2
* Docker SDK

Infraestructura:

* Docker
* Docker Compose

Motores externos:

* Duplicati REST API

Testing:

* pytest

---

# 12. Reglas de desarrollo

Mantener:

* Clean Architecture.
* Responsabilidad única.
* Servicios desacoplados.
* Cambios completos de archivos.
* Validación mediante Docker Compose.
* Commit Git después de cada sprint funcional.

Comandos estándar:

```
docker compose down

docker compose build

docker compose up -d

docker compose exec casaos-backup-manager pytest
```

---

# 13. Próxima fase

La siguiente fase consiste en conectar la integración Duplicati ya validada con el flujo real del Backup Engine.

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
Backup remoto ejecutado
```

Después:

* capturar ejecución.
* consultar progreso.
* almacenar estado.
* mostrar resultados en dashboard.
