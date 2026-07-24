# CONTRIBUTING

## Introducción

Gracias por contribuir a CasaOS Backup Manager.

Este proyecto sigue una arquitectura modular basada en Clean Architecture y está diseñado para ser mantenible, extensible e independiente del motor de backup utilizado.

Antes de realizar cualquier modificación es recomendable leer la documentación disponible en la carpeta `docs/`.

---

# Filosofía del proyecto

CasaOS Backup Manager **no es un frontend para Duplicati**.

El objetivo es desarrollar un **Backup Engine profesional**, capaz de trabajar con múltiples motores de backup mediante una arquitectura desacoplada.

Duplicati es únicamente el primer backend implementado.

La arquitectura está preparada para soportar:

- Duplicati
- Restic
- Borg
- Rsync
- Kopia
- Futuros motores de backup

---

# Principios de desarrollo

Todo el código debe respetar los siguientes principios:

- Clean Architecture.
- SOLID.
- Single Responsibility Principle.
- Separation of Concerns.
- Código legible.
- Tipado completo.
- Bajo acoplamiento.
- Alta cohesión.

---

# Responsabilidades

Cada componente debe tener una única responsabilidad.

Ejemplos:

- Los **Services** contienen la lógica de negocio.
- Los **Models** representan únicamente datos del dominio.
- Los **Connectors** encapsulan la comunicación con sistemas externos.
- Los **Backends** implementan la integración con un motor de backup.
- Los **Routers** únicamente exponen la API.

---

# Organización del código

No mezclar responsabilidades.

Ejemplos de dependencias permitidas:

```
Router
    │
    ▼
Service
    │
    ▼
Core
    │
    ▼
Connector
```

No deben existir dependencias en sentido contrario.

---

# Desarrollo de nuevos servicios

Cada nuevo servicio debe:

- Tener una única responsabilidad.
- Ser reutilizable.
- Ser fácilmente testeable.
- Evitar dependencias innecesarias.
- Utilizar modelos del dominio como interfaz.

---

# Desarrollo de nuevos modelos

Los modelos deben:

- Contener únicamente datos.
- Estar completamente tipados.
- No acceder a Docker.
- No acceder a HTTP.
- No contener lógica de infraestructura.

---

# Desarrollo de nuevos backends

Todo backend debe implementar el contrato definido por `BackupBackend`.

El Backup Engine nunca debe conocer detalles específicos del backend.

Toda comunicación con APIs externas debe realizarse mediante un Connector.

---

# Pruebas

Toda nueva funcionalidad debe incorporar pruebas unitarias.

Antes de finalizar un sprint deben ejecutarse, como mínimo:

```bash
docker compose down

docker compose up -d --build

docker compose exec casaos-backup-manager python -m pytest -v
```

No deben incorporarse cambios con pruebas fallando.

---

# Commits

Los commits deben realizarse únicamente cuando:

- El proyecto compila correctamente.
- Todos los tests finalizan con éxito.
- La documentación correspondiente ha sido actualizada.

Los mensajes de commit deben describir claramente el contenido del sprint.

Ejemplo:

```
Entrega v0.5.0-alpha6 - Infraestructura del Backup Engine
```

---

# Documentación

Toda funcionalidad nueva debe reflejarse en la documentación correspondiente.

Evitar documentos excesivamente grandes.

La documentación se divide por áreas:

- README.md
- ARCHITECTURE.md
- ROADMAP.md
- CHANGELOG.md
- docs/BACKUP_ENGINE.md
- docs/BACKEND_DEVELOPMENT.md
- docs/DOMAIN_MODELS.md
- docs/PROJECT_STRUCTURE.md
- docs/CONTRIBUTING.md

---

# Objetivo

El objetivo del proyecto es construir un Backup Engine modular, mantenible e independiente del motor de backup, preparado para evolucionar durante los próximos años sin comprometer la arquitectura ni la calidad del código.