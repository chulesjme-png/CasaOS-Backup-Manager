# CasaOS Backup Manager - Roadmap

## Estado actual

Versión:

v0.4.0-alpha1

Fase:

Inicio del Backup Engine


---

# Objetivo del proyecto

CasaOS Backup Manager tiene como objetivo construir un sistema profesional de copias de seguridad para entornos CasaOS.

La aplicación debe ser capaz de:

1. Detectar aplicaciones instaladas.
2. Analizar sus recursos.
3. Crear perfiles de backup.
4. Generar planes de copia.
5. Resolver trabajos de backup.
6. Ejecutar copias mediante diferentes backends.
7. Restaurar aplicaciones completas.


---

# Arquitectura actual

Flujo principal:

Docker

↓

Application Discovery

↓

Application Profile

↓

Backup Plan

↓

Backup Job

↓

Execution Backend


Backends previstos:

- Duplicati
- Restic
- Borg
- Rsync


---

# Versiones

## v0.1.x

Estado:

Infraestructura base.

Incluye:

- FastAPI.
- Docker integration.
- Dashboard inicial.
- Arquitectura modular.


---

## v0.2.x

Estado:

Descubrimiento y análisis.

Incluye:

- detección de aplicaciones;
- servicios Docker;
- análisis inicial de almacenamiento.


---

## v0.3.x

Estado:

Dashboard estabilizado.

Incluye:

- ApplicationProfile.
- BackupPlan.
- StorageResource.
- BackupPlannerService.
- Dashboard coherente con los nuevos modelos.


---

## v0.4.x

Estado:

Desarrollo del Backup Engine.

Objetivos:

- BackupJob.
- StorageResolver.
- BackupEngineService.
- resolución de recursos.
- preparación para ejecución.


---

# Próximos sprints


## v0.4.0-alpha1

Objetivo:

Crear la primera capa del Backup Engine.

Pendiente:

- BackupJob.
- StorageResolverService.
- BackupEngineService.


## v0.4.x

Objetivos:

- detección de rutas inexistentes;
- exclusiones automáticas;
- cálculo de tamaños;
- resolución de dependencias.


## v0.5.x

Objetivos:

- motor de ejecución;
- integración con backends.


## v0.6.x

Objetivos:

- restauración;
- recuperación completa.


---

# Principios del proyecto

## Independencia del backend

El núcleo del proyecto no dependerá de una herramienta concreta de backup.


## Clean Architecture

Los modelos representan datos.

Los servicios contienen lógica.

Los backends ejecutan acciones.


## Evolución incremental

No se rediseña la aplicación.

Cada versión añade capacidades sobre la arquitectura existente.