# Changelog

Historial de cambios de CasaOS Backup Manager.

---

# v0.5.0-alpha6 - Duplicati REST Integration Validation

Fecha: 28/07/2026

## Added

* Validación de comunicación real con servidor Duplicati.
* Autenticación mediante API REST de Duplicati.
* Implementación funcional de `DuplicatiClient`.
* Lectura de backups existentes mediante `/api/v1/backups`.
* Creación de trabajos remotos mediante `/api/v1/backups`.
* Validación del constructor de payloads REST para Duplicati.

---

## Validated

La integración externa de Duplicati queda validada mediante:

```text
CasaOS Backup Manager
        |
        v
DuplicatiBackend
        |
        v
DuplicatiClient
        |
        v
Duplicati REST API
```

Operaciones verificadas:

* `authenticate()`
* `get_backups()`
* `create_job()`

---

# Duplicati API Notes

Durante la integración se identificaron requisitos específicos del contrato REST de Duplicati.

---

## Creación de nuevos backups

El objeto `Backup` debe incluir:

```json
{
    "ID": null
}
```

cuando se crea un nuevo trabajo.

---

## Lista de fuentes

El formato aceptado por Duplicati es:

```json
{
    "Sources": [
        "/ruta/origen"
    ]
}
```

No son válidos formatos alternativos como:

```json
{
    "Sources": [
        {
            "Path": "/ruta/origen"
        }
    ]
}
```

---

# Tests realizados

## Obtener backups existentes

Script:

```text
scripts/test_duplicati_get_backups.py
```

Comando ejecutado:

```bash
docker compose exec casaos-backup-manager python scripts/test_duplicati_get_backups.py
```

Resultado:

* Autenticación correcta.
* Recuperación de backups existentes.
* Lectura de metadata.
* Lectura de programación.
* Lectura de estado remoto.

Backups recuperados:

* CasaOS Completo.
* CasaOS Configuración.
* CasaOS-Test.

---

## Crear backup remoto

Script:

```text
scripts/test_duplicati_create_job.py
```

Comando ejecutado:

```bash
docker compose exec casaos-backup-manager python scripts/test_duplicati_create_job.py
```

Resultado:

```json
{
    "ID": "4",
    "Temporary": false
}
```

El trabajo fue creado correctamente en Duplicati.

---

# Arquitectura actual

La capa connector de Duplicati queda validada:

```text
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

# Responsabilidades

## DuplicatiClient

Responsable de:

* comunicación HTTP.
* autenticación.
* gestión de sesión.
* llamadas REST.
* gestión de errores HTTP.

No conoce:

* Docker.
* CasaOS.
* Backup Engine.
* reglas de negocio.

---

## DuplicatiPayloadBuilder

Responsable de:

* adaptar `DuplicatiJob`.
* construir payload REST.
* traducir modelos internos al contrato externo.

No realiza:

* llamadas HTTP.
* autenticación.
* ejecución.

---

## DuplicatiJob

Modelo interno:

* independiente de REST.
* independiente del transporte HTTP.
* representa una definición de backup Duplicati.

Contiene:

* fuentes.
* destino.
* cifrado.
* compresión.
* retención.
* opciones.
* metadata.

---

# Estado del proyecto

## Completado

* Infraestructura inicial de backends.
* Connector Duplicati.
* Autenticación REST.
* Lectura de backups.
* Creación de backups remotos.
* Validación del payload REST.

---

## Pendiente

* Integración completa desde `DuplicatiBackend`.
* Ejecución remota de backups.
* Monitorización de tareas.
* Sincronización de estados.
* Integración con Backup Engine.
* Visualización avanzada en dashboard.

---

# Historial anterior

## v0.5.0-alpha5

Added:

* Infraestructura inicial de backends.
* Primeros conectores.
* Modelos base para configuración de backend.

---

## v0.5.0-alpha4

Added:

* Pipeline inicial del Backup Engine.
* Validación de recursos de almacenamiento.
* Storage Intelligence inicial.

---

## v0.4.x

Added:

* Resolución de almacenamiento.
* Validación de recursos.
* Servicios de descubrimiento.

---

## v0.3.x

Added:

* Dashboard inicial.
* Visualización del estado interno.
