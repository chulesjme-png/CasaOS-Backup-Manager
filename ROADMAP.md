# CasaOS Backup Manager - Roadmap

Hoja de ruta del desarrollo del proyecto.

Fecha actualización: 28/07/2026

---

# Estado actual

Versión actual:

```
v0.5.0-alpha6
```

Estado:

Integración inicial real con Duplicati validada.

La comunicación con un servidor Duplicati externo está funcionando mediante API REST.

Operaciones verificadas:

* autenticación.
* lectura de backups existentes.
* creación de nuevos trabajos remotos.

---

# Fase 0 - Base del proyecto

Estado:

COMPLETADA

Objetivos:

* estructura inicial del proyecto.
* Dockerización.
* configuración del entorno.
* creación del dashboard inicial.

Completado:

* Dockerfile.
* Docker Compose.
* aplicación FastAPI.
* estructura modular.
* templates iniciales.

---

# Fase 1 - Dashboard y descubrimiento

Estado:

COMPLETADA

Objetivos:

Crear una primera capa visual y descubrir el estado del sistema.

Completado:

* dashboard inicial.
* integración Docker.
* descubrimiento de contenedores.
* visualización de aplicaciones.

Componentes:

* DockerService.
* AppDiscoveryService.
* DashboardService.

---

# Fase 2 - Storage Intelligence

Estado:

COMPLETADA

Objetivo:

Comprender los recursos de almacenamiento disponibles.

Completado:

* detección de rutas.
* resolución de recursos.
* validación de almacenamiento.
* generación de StorageResource.

Componentes:

* StorageResolverService.
* StorageValidationService.
* StorageResource.

---

# Fase 3 - Backup Engine

Estado:

PARCIALMENTE COMPLETADA

Objetivo:

Crear el motor interno de planificación.

Completado:

* BackupPlan.
* BackupJob.
* BackupPlannerService.
* BackupJobBuilderService.

Pendiente:

* conectar planificación con ejecución real.
* selección automática de backend.
* gestión completa del ciclo de vida.

---

# Fase 4 - Backend Infrastructure

Estado:

COMPLETADA

Objetivo:

Crear una arquitectura extensible para diferentes motores.

Completado:

* contrato BackupBackend.
* configuración de backend.
* registro de backends.
* infraestructura inicial.

Backends previstos:

* Duplicati.
* Restic.
* Borg.
* Rsync.

---

# Fase 5 - Duplicati Integration

Estado:

VALIDADA

Versión:

```
v0.5.0-alpha6
```

Objetivo:

Integrar Duplicati como primer backend funcional.

Completado:

## Connector Duplicati

* DuplicatiClient.
* autenticación REST.
* gestión de sesión.
* llamadas API.

## Payload Builder

* construcción de payload REST.
* adaptación DuplicatiJob.
* validación del contrato externo.

## Operaciones validadas

### Obtener backups

Endpoint:

```
GET /api/v1/backups
```

Resultado:

Correcto.

Datos obtenidos:

* nombre.
* ID.
* destino.
* programación.
* metadata.
* estado.

---

### Crear backup

Endpoint:

```
POST /api/v1/backups
```

Resultado:

Correcto.

Trabajo creado:

```
CasaOS-Test
ID: 4
```

---

# Fase 6 - Ejecución de Backups

Estado:

PENDIENTE

Objetivo:

Ejecutar backups desde CasaOS Backup Manager.

Trabajo previsto:

* conectar BackupJob con DuplicatiBackend.
* lanzar ejecuciones remotas.
* capturar respuesta.
* almacenar referencia de ejecución.

Flujo esperado:

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

---

# Fase 7 - Monitorización

Estado:

PENDIENTE

Objetivo:

Controlar ejecuciones activas.

Implementar:

* consulta de estado.
* progreso.
* errores.
* tiempos.
* historial.

Modelo previsto:

```
BackupExecution
```

---

# Fase 8 - Dashboard avanzado

Estado:

PENDIENTE

Objetivo:

Convertir el dashboard en una interfaz completa de gestión.

Funciones previstas:

* listado de backups.
* estado de ejecuciones.
* historial.
* errores.
* acciones manuales.

Principio:

El dashboard no ejecuta lógica.

Solo muestra el estado del sistema.

---

# Fase 9 - Multi Backend

Estado:

PENDIENTE

Objetivo:

Añadir nuevos motores sin modificar el núcleo.

Backends previstos:

## Restic

Características:

* snapshots.
* deduplicación.
* cifrado.

## Borg

Características:

* deduplicación.
* compresión.
* cifrado.

## Rsync

Características:

* sincronización directa.
* simplicidad.

---

# Fase 10 - Release estable

Estado:

PENDIENTE

Objetivo:

Preparar versión estable.

Incluye:

* documentación completa.
* pruebas automatizadas.
* instalación CasaOS.
* configuración inicial.
* sistema de actualización.

---

# Próximo objetivo inmediato

Prioridad:

Integración completa del flujo:

```
Backup Engine

        |

        v

BackupBackend

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

Después:

* ejecutar backup.
* consultar resultado.
* reflejar estado en dashboard.
