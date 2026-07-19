# CasaOS Backup Manager - Architecture

## Introducción

CasaOS Backup Manager es una aplicación diseñada para crear un sistema profesional de copias de seguridad para entornos CasaOS.

El objetivo principal no es monitorizar contenedores ni mostrar información del sistema.

El objetivo es:

- detectar aplicaciones;
- comprender sus datos importantes;
- generar planes de copia;
- preparar trabajos de backup;
- ejecutar copias mediante diferentes motores;
- permitir restauraciones completas.

---

# Principios arquitectónicos

## Clean Architecture

El proyecto sigue una arquitectura basada en separación de responsabilidades.

Las capas principales son:

```
Routers
        │
        ▼
Services
        │
        ▼
Models
```

Cada servicio tiene una única responsabilidad y el dominio permanece independiente de la interfaz web y de los motores de ejecución.

---

# Flujo principal del Backup Engine

El flujo funcional del proyecto es el siguiente:

```
Docker

    │
    ▼

Application Discovery

    │
    ▼

Application

    │
    ▼

ApplicationProfile

    │
    ▼

BackupPlan

    │
    ▼

StorageResolverService

    │
    ▼

StorageResource

    │
    ▼

BackupEngineService

    │
    ▼

BackupJob

    │
    ▼

Execution Backend

    ├── Duplicati
    ├── Restic
    ├── Borg
    ├── Rsync
    └── futuros backends
```

---

# Responsabilidades

## Application Discovery

Detecta automáticamente las aplicaciones instaladas mediante Docker Compose.

---

## ApplicationProfile

Describe qué datos pertenecen a una aplicación y cuáles son candidatos para formar parte de una copia de seguridad.

---

## BackupPlan

Representa un plan lógico de copia.

No contiene información física del almacenamiento ni depende del backend que ejecutará la copia.

---

## StorageResolverService

Resolverá cada origen definido en un `BackupPlan` y determinará los recursos físicos realmente disponibles.

Será responsable de:

- validar rutas;
- identificar volúmenes;
- identificar bind mounts;
- detectar recursos inexistentes;
- generar objetos `StorageResource`.

---

## StorageResource

Representa un recurso físico de almacenamiento susceptible de formar parte de una copia de seguridad.

---

## BackupEngineService

Transformará los recursos resueltos en un `BackupJob` completamente preparado para su ejecución.

No dependerá de ningún motor concreto.

---

## BackupJob

Representa un trabajo de copia completamente resuelto y listo para ser ejecutado por cualquier backend soportado.

---

## Execution Backend

La ejecución del backup será intercambiable.

Inicialmente se prevén:

- Duplicati
- Restic
- Borg
- Rsync

La arquitectura permitirá incorporar nuevos motores sin modificar el dominio.

---

# Integridad del dominio

Durante el desarrollo de la versión **v0.4.0-alpha1** se detectó una incidencia importante: varios modelos del dominio habían sido sobrescritos accidentalmente con contenido HTML y el error había quedado registrado en el historial de Git.

Los modelos afectados fueron:

- `Application`
- `Container`
- `ApplicationProfile`
- `BackupPlan`

La reparación consistió en reconstruir completamente estos modelos, verificando previamente todos los imports para garantizar que no existían implementaciones alternativas ni dependencias ocultas.

Esta incidencia reafirma uno de los principios fundamentales del proyecto:

- los modelos del dominio únicamente contienen datos del dominio;
- las plantillas HTML únicamente residen en `app/templates`;
- los servicios implementan la lógica de negocio;
- la interfaz web nunca forma parte del dominio.

Toda modificación estructural del dominio debe validarse mediante una compilación completa del proyecto y el arranque satisfactorio de la aplicación.