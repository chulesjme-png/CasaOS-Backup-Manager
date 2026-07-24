# BACKEND DEVELOPMENT

## Introducción

CasaOS Backup Manager ha sido diseñado para soportar múltiples motores de backup.

El Backup Engine nunca depende de una implementación concreta. Toda la interacción con un motor de backup se realiza a través de la capa de Backends.

Actualmente el primer backend implementado es **Duplicati**, pero la arquitectura permite incorporar nuevos motores sin modificar el dominio.

---

# Arquitectura

```
BackupRunnerService
        │
        ▼
BackendFactory
        │
        ▼
BackupBackend
   ├── NullBackupBackend
   └── DuplicatiBackend
        │
        ▼
DuplicatiClient
        │
        ▼
Duplicati API
```

Cada nivel tiene una única responsabilidad.

---

# BackupBackend

`BackupBackend` define el contrato común que deben implementar todos los motores de backup.

Todo backend debe ser capaz de:

- comprobar disponibilidad;
- ejecutar una solicitud de backup;
- devolver un objeto `BackupResult`.

El Backup Engine nunca conoce la implementación concreta utilizada.

---

# BackendFactory

`BackendFactory` es responsable de seleccionar la implementación adecuada para cada solicitud.

Actualmente soporta:

- NullBackupBackend
- DuplicatiBackend

En futuras versiones se añadirán:

- ResticBackend
- BorgBackend
- RsyncBackend
- KopiaBackend

---

# BackendRegistry

Centraliza el registro de los backends disponibles.

Sus responsabilidades son:

- registrar implementaciones;
- localizar un backend por nombre;
- desacoplar el motor de la creación de instancias.

---

# BackendConfigurationService

Proporciona la configuración necesaria para cada backend.

Actualmente devuelve la configuración por defecto para Duplicati:

- URL
- Usuario
- Contraseña
- Verificación SSL
- Timeout

Para motores desconocidos devuelve una configuración deshabilitada.

---

# DuplicatiBackend

`DuplicatiBackend` implementa la interfaz `BackupBackend`.

Actualmente funciona en modo simulación.

El flujo de trabajo es:

```
BackupExecutionRequest
        │
        ▼
BackendConfigurationService
        │
        ▼
DuplicatiClient
        │
        ▼
BackupResult
```

No crea todavía trabajos reales de backup.

---

# DuplicatiClient

Toda la comunicación HTTP con Duplicati está encapsulada en este componente.

Actualmente implementa:

- `_request()`
- `_get()`
- `ping()`
- `get_server_state()`
- `get_version()`

Ningún otro componente del proyecto realiza peticiones HTTP directamente.

---

# Principios de diseño

Los Backends deben cumplir las siguientes reglas:

- No contienen lógica de negocio del Backup Engine.
- No construyen URLs fuera del Connector.
- No utilizan directamente bibliotecas HTTP.
- No conocen otros backends.
- Devuelven siempre un `BackupResult`.

---

# Estado actual

La infraestructura de backends está completamente operativa.

Duplicati actúa como primera implementación de referencia.

La ejecución real de copias de seguridad se incorporará en los próximos sprints, comenzando con la detección automática de capacidades del servidor.