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
