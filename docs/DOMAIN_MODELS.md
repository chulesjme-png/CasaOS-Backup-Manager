# DOMAIN MODELS

## Introducción

Los modelos de dominio representan las entidades principales utilizadas por el Backup Engine.

Son objetos simples que contienen datos y definen el contrato entre los distintos servicios del sistema.

Los modelos no contienen lógica de infraestructura ni dependencias externas.

---

# Principios

Todos los modelos siguen las siguientes reglas:

- Responsabilidad única.
- Tipado completo.
- Sin acceso a Docker.
- Sin acceso a HTTP.
- Sin lógica de ejecución.
- Independientes del backend.

---

# Modelos implementados

## Application

Representa una aplicación detectada en CasaOS.

Información típica:

- Nombre
- Contenedor Docker
- Estado
- Recursos asociados

---

## ApplicationProfile

Describe toda la información necesaria para realizar una copia de seguridad de una aplicación.

Incluye:

- Información de la aplicación
- Recursos de almacenamiento
- Configuración del backup

---

## StorageResource

Representa un recurso físico utilizado por una aplicación.

Puede corresponder a:

- Bind Mount
- Volume
- Directorio
- Archivo

Durante la validación incorpora información adicional como:

- Existencia
- Permisos de lectura
- Tamaño
- Estado de validación
- Errores detectados

---

## BackupPlan

Resultado del proceso de planificación.

Define qué recursos deben incluirse en una copia de seguridad.

---

## BackupJob

Representa un trabajo de backup preparado para ser ejecutado.

Contiene toda la información necesaria para que un backend pueda realizar la operación.

---

## BackupExecutionRequest

Modelo utilizado para iniciar una ejecución.

Contiene:

- Aplicación objetivo
- Backend seleccionado
- Opciones de ejecución

Es el punto de entrada del Backup Engine.

---

## BackupManifest

Describe de forma independiente del backend el contenido de una operación de backup.

Su objetivo es desacoplar la planificación de la ejecución.

---

## BackupResult

Modelo común devuelto por todos los backends.

Incluye, entre otros:

- Resultado de la operación
- Backend utilizado
- Aplicación
- Hora de inicio
- Hora de finalización
- Bytes procesados
- Advertencias
- Errores
- Metadatos adicionales

Todos los motores de backup deben devolver este modelo.

---

## BackendConfiguration

Representa la configuración necesaria para inicializar un backend.

Incluye:

- Nombre del backend
- Estado (habilitado o deshabilitado)
- Parámetros de configuración
- Metadatos

El Backup Engine nunca accede directamente a archivos de configuración; siempre utiliza este modelo.

---

# Relaciones entre modelos

```
Application
        │
        ▼
ApplicationProfile
        │
        ▼
StorageResource
        │
        ▼
BackupPlan
        │
        ▼
BackupJob
        │
        ▼
BackupExecutionRequest
        │
        ▼
BackupManifest
        │
        ▼
BackupResult
```

---

# Evolución prevista

Durante los próximos sprints se incorporarán nuevos modelos relacionados con la ejecución real de los backends, entre ellos:

- DuplicatiCapabilities
- BackupDefinition
- BackendJob
- ProgressInfo
- RestoreRequest
- RestoreResult

Estos modelos ampliarán el dominio sin modificar los contratos existentes, manteniendo la compatibilidad con los componentes ya implementados.