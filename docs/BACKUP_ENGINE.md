# BACKUP ENGINE

## Introducción

El **Backup Engine** es el núcleo de CasaOS Backup Manager.

Su responsabilidad es coordinar todo el proceso de ejecución de una copia de seguridad sin depender de ningún backend concreto.

El motor nunca interactúa directamente con Duplicati, Restic, Borg o cualquier otro sistema de backup. Toda esa responsabilidad está delegada en la capa de Backends.

---

# Objetivos

El Backup Engine ha sido diseñado para:

- Ser independiente del backend.
- Permitir múltiples motores de backup.
- Mantener una arquitectura desacoplada.
- Facilitar la incorporación de nuevos backends.
- Centralizar la lógica de ejecución.

---

# Flujo de ejecución

```
BackupExecutionRequest
        │
        ▼
BackupExecutionService
        │
        ▼
BackupManifestBuilderService
        │
        ▼
BackupRunnerService
        │
        ▼
BackendFactory
        │
        ▼
BackupBackend
        │
        ▼
BackupResult
```

Cada componente tiene una única responsabilidad y desconoce la implementación interna del siguiente nivel.

---

# Componentes

## BackupExecutionService

Punto de entrada del motor.

Responsabilidades:

- recibir la solicitud de ejecución;
- validar la petición;
- coordinar el flujo del Backup Engine.

---

## BackupManifestBuilderService

Genera un `BackupManifest` a partir de la información recibida.

El manifiesto contiene toda la información necesaria para ejecutar el backup independientemente del backend seleccionado.

---

## BackupRunnerService

Responsable de ejecutar un backup.

Funciones:

- obtener el backend adecuado;
- delegar la ejecución;
- devolver un `BackupResult`.

No contiene lógica específica de ningún backend.

---

## BackendFactory

Selecciona la implementación adecuada del backend.

Ejemplos:

- NullBackend
- DuplicatiBackend

En el futuro:

- ResticBackend
- BorgBackend
- RsyncBackend
- KopiaBackend

---

## BackupBackend

Interfaz común implementada por todos los motores de backup.

Todos los backends deben devolver un objeto `BackupResult`.

---

# Principios de diseño

El Backup Engine sigue los principios de:

- Clean Architecture
- SOLID
- Single Responsibility
- Dependency Inversion

La lógica del dominio nunca depende de implementaciones concretas.

---

# Estado actual

Actualmente el flujo está completamente implementado.

La ejecución del backend Duplicati funciona en modo simulación utilizando el `DuplicatiClient`.

No se crean todavía trabajos reales de backup.

---

# Próximo paso

El siguiente bloque del desarrollo será **Duplicati Capability Detection**.

Este componente permitirá detectar automáticamente las capacidades del servidor Duplicati antes de iniciar cualquier operación.