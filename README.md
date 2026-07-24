# CasaOS Backup Manager

Sistema profesional de copias de seguridad para CasaOS diseñado con una arquitectura modular, independiente del motor de backup y preparada para soportar múltiples backends.

## Estado del proyecto

Versión actual:

**v0.5.0-alpha6**

Estado:

- ✅ Descubrimiento de aplicaciones completado.
- ✅ Storage Intelligence completado.
- ✅ Backup Planning completado.
- ✅ Infraestructura del Backup Engine completada.
- 🔄 Próximo sprint: Duplicati Capability Detection.

---

## Objetivo

CasaOS Backup Manager no pretende ser un frontend para Duplicati.

El objetivo es construir un **Backup Engine** desacoplado capaz de trabajar con distintos motores de backup mediante una arquitectura común.

Actualmente el primer backend implementado es:

- Duplicati

En futuras versiones podrán añadirse:

- Restic
- Borg
- Rsync
- Kopia
- Otros motores compatibles

---

## Arquitectura

El flujo principal del Backup Engine es:

```
DockerService
        │
        ▼
AppDiscoveryService
        │
        ▼
ApplicationProfileService
        │
        ▼
StorageResolverService
        │
        ▼
StorageValidationService
        │
        ▼
BackupPlannerService
        │
        ▼
BackupJobBuilderService
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
```

---

## Documentación

La documentación del proyecto está organizada por módulos.

| Documento | Descripción |
|-----------|-------------|
| `ARCHITECTURE.md` | Visión general de la arquitectura. |
| `ROADMAP.md` | Estado del desarrollo y próximos sprints. |
| `CHANGELOG.md` | Historial de cambios. |
| `docs/BACKUP_ENGINE.md` | Funcionamiento del Backup Engine. |
| `docs/BACKEND_DEVELOPMENT.md` | Desarrollo de Backends y Connectors. |
| `docs/DOMAIN_MODELS.md` | Modelos del dominio. |
| `docs/PROJECT_STRUCTURE.md` | Organización del proyecto. |
| `docs/CONTRIBUTING.md` | Guía para colaboradores. |

---

## Tecnologías

- Python
- FastAPI
- Docker SDK
- Docker Compose
- Jinja2
- HTML
- CSS
- JavaScript

---

## Desarrollo

Para validar el proyecto:

```bash
docker compose down

docker compose up -d --build

docker compose exec casaos-backup-manager python -m pytest -v
```

Todos los cambios deben mantener la arquitectura del proyecto y superar la batería completa de pruebas antes de realizar un commit.

---

## Licencia

Pendiente de definir.