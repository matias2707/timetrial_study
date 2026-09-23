# Documentación de Study Timetrial

**Fecha de revisión:** 2026-09-23  
**Estado:** Vigente — Arquitectura Reestructurada (MVP, Theming JSON, Audio Dedicado y Specs de Migración)

## Cómo usar esta documentación

La documentación técnica, operativa y funcional de **Study Timetrial** está organizada de forma modular en las siguientes especificaciones complementarias:

### 1. Gobernanza y Estándares de Ingeniería
* [Directivas Maestras para Agentes (AGENTS.md)](../AGENTS.md): Normas contractuales innegociables para agentes de IA y desarrolladores, protocolo de no-regresión y el **algoritmo de 7 fases para la planificación de nuevas secciones o apartados**.
* [Guía de Desarrollo y Codificación](GUIA_DE_DESARROLLO_Y_CODIFICACION.md): Convenciones de Clean Code, tipado estricto con `typing`, normas de nombres y estructura de capas.

### 2. Árbol de Especificaciones Técnicas para Migración Futura
* [Índice de Especificaciones (docs/specs/)](specs/README.md): Especificaciones funcionales y de contratos desacopladas al 100% de la interfaz gráfica y de PySide6, preparadas para migrar el sistema hacia cualquier stack (Web SPA, Tauri, Flutter, etc.):
  * **Núcleo:** [Motor de Cronómetro](specs/core/timer_engine.spec.md), [Ciclo de Vida de Sesión](specs/core/session_lifecycle.spec.md), [Resolución de Incisos](specs/core/inciso_resolution.spec.md).
  * **Datos:** [Contratos de Persistencia JSON v1](specs/data/persistence_contracts.spec.md), [Consulta y Filtrado estilo Excel](specs/data/query_and_filtering.spec.md).
  * **Planificador:** [Secciones y Metas](specs/planner/sections_and_goals.spec.md), [Métricas de Progreso](specs/planner/progress_metrics.spec.md).
  * **Audio:** [Mezclador Ambiental y Efectos](specs/audio/ambient_and_effects.spec.md).
  * **Estilos:** [Tokens y Plantillas Cromáticas](specs/themes/color_tokens.spec.md).

### 3. Arquitectura y Operación del Sistema
* [Arquitectura General](ARQUITECTURA_2026-09-07.md): Capas de diseño (Presentación MVP, Aplicación, Dominio, Infraestructura), diagrama Mermaid, responsabilidades de cada módulo y reglas de diseño.
* [Arquitectura de Presentación](ARQUITECTURA_PRESENTACION.md): Descomposición modular de la interfaz gráfica en Presenters y Vistas Pasivas (`IHomeView`, `IPlannerView`, `IRecordsView`).
* [Motor de Temas Dinámico](../data/themes/): Carga de paletas desde archivos `.json` en `data/themes/` con fallback seguro y detección automática de temas de usuario.
* [Operación y Validación](OPERACION_Y_VALIDACION.md): Requisitos de entorno, ejecución de tests unitarios, compilación de sintaxis y protocolo de validación manual.
* [Product Backlog y Hoja de Ruta](../BACKLOG.md): Hoja de ruta del proyecto y backlog categorizado.

---

## Convenciones de Estado

- **Implementado:** Comportamiento y módulos verificados en el código activo del proyecto con cobertura de pruebas.
- **Contrato:** Reglas invariantes que deben respetarse rigurosamente al realizar refactorizaciones o extensiones futuras.
- **Pendiente:** Mejoras o nuevas características no contempladas en el alcance de la versión actual.
