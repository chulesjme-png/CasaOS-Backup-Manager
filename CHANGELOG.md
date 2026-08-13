# Changelog

Historial de cambios de CasaOS Backup Manager.

---

# v0.5.0-beta1 - Audit Log, Real-Time WebSockets & Storage Volume Fixes

Fecha: 13/08/2026

## Added

* **Módulo de Historial y Auditoría:**
  * Sistema de registro de auditoría con almacenamiento en base de datos SQLite (`history.db`).
  * Persistencia de las últimas 50 operaciones (respaldos y restauraciones) detallando fecha, objetivo, estado (Éxito/Fallo) y duración exacta en segundos.
  * Nueva vista modal en la interfaz web para consultar el historial de ejecuciones y botón dedicado para limpiar registros.
* **Comunicaciones en Tiempo Real (WebSockets):**
  * Canal WebSocket dedicado (`/api/v1/ws/progress`) para transmisión instantánea del progreso de respaldos (porcentajes y logs).
  * Notificaciones flotantes y barras de progreso fluidas en el panel sin necesidad de recargar la página.
* **Database Hooks en Caliente:**
  * Sistema de pre-procesamiento para bases de datos SQLite (e.g., Sonarr, Plex, Radarr).
  * Generación segura de volcados SQL (`.backup_dump.sql`) antes de comprimir la aplicación para garantizar consistencia sin detener los contenedores.

## Fixed

* **Propagación de Montajes en Docker:**
  * Solucionado el problema crítico donde los backups en unidades USB/externas (`/media`) quedaban atrapados en la capa virtual del contenedor.
  * Añadida propagación de volúmenes `:rshared` y modo `privileged: true` en `docker-compose.yml` para acceso nativo y dinámico al almacenamiento físico.
* **Permisos de Archivos y Visibilidad SMB/Finder:**
  * Corrección de generación de archivos `.tar.gz` para asegurar visibilidad en red local y clientes SMB (macOS Finder).

---

# v0.5.0-alpha7 - Brand Identity, Dashboard UI & Backup Engine Integration

Fecha: 07/08/2026

## Added

* **Identidad visual e interfaz de usuario:**
  * Integración del logo oficial horizontal (`logo-horizontal.svg`) en la cabecera principal del panel.
  * Dashboard unificado con visión general del sistema, perfiles de aplicaciones generados y tablas detalladas de contenedores y rutas de almacenamiento.
  * Pestañas interactivas para telemetría de hardware (Raspberry Pi 5), Docker Engine y almacenamiento externo montado.
  * Componentes de notificación Toast en tiempo real para interacción con la interfaz.
* **Backup Engine & API REST:**
  * Conexión completa del flujo del `Backup Engine` con el backend real de Duplicati.
  * Implementación de los endpoints de la API para ejecución (`/api/v1/executions/run`) y cancelación (`/api/v1/executions/cancel`).
  * Creación del sistema de persistencia y base de datos local (`app/database/`).
  * Registro centralizado de backends mediante `BackendRegistry`.
  * Cobertura de pruebas completa alcanzando **57 tests en verde** (incluyendo pruebas de routers, servicios y clientes de Duplicati).

## Fixed

* Corrección del enrutamiento de archivos estáticos en plantillas Jinja2/FastAPI para evitar errores `NoMatchFound` al cargar recursos gráficos.
* Corrección de tipos en mayúsculas/minúsculas para el modelo de cancelación (`BackupOperationType.CANCEL`).

---

# v0.5.0-alpha6 - Duplicati REST Integration Validation

Fecha: 28/07/2026

## Added

* Validación de comunicación real con servidor Duplicati mediante API REST.
* Autenticación, lectura de backups y creación de trabajos remotos.