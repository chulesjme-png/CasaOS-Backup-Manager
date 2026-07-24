# CHANGELOG

Todos los cambios relevantes del proyecto se documentan en este archivo.

El formato sigue una variante de Keep a Changelog.

---

## [v0.5.0-alpha6] - Infraestructura del Backup Engine

### Añadido

#### Modelos

- BackupResult
- BackendConfiguration

#### Servicios

- BackupRunnerService
- BackupManifestBuilderService
- BackendConfigurationService

#### Core

- BackendFactory
- BackendRegistry
- DuplicatiBackend

#### Connectors

- DuplicatiClient

#### Funcionalidad

- Nueva infraestructura desacoplada para la ejecución de backends.
- Integración inicial del backend Duplicati en modo simulación.
- Configuración centralizada de backends.
- Pipeline completo de ejecución preparado para múltiples motores de backup.
- Resultado de ejecución unificado mediante `BackupResult`.

### Tests

Se amplía la batería de pruebas unitarias para cubrir:

- DuplicatiClient
- BackendFactory
- BackendRegistry
- BackendConfigurationService
- BackupRunnerService
- DuplicatiBackend

Resultado final:

- **23 tests superados**
- **0 fallos**
- **0 errores**

### Corregido

- Restaurado el endpoint oficial `/api/v1/serverstate`.
- Añadida la importación faltante `patch` en los tests.
- Mejorada la separación entre Backend y Connector para evitar dependencias con la API HTTP.

---

## Próximo sprint

Duplicati Capability Detection

Objetivos:

- Descubrir automáticamente las capacidades del servidor Duplicati.
- Crear el modelo `DuplicatiCapabilities`.
- Incorporar un servicio de detección de capacidades.
- Mantener completamente aislado el Backup Engine de los cambios en la API de Duplicati.