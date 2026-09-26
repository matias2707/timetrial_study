# Árbol de Especificaciones Técnicas (Blueprint para Migración Futura)

Este directorio contiene las **especificaciones funcionales, operativas y de contratos de datos** de cada subsistema de **Study Timetrial**.

Cada especificación está redactada de forma **completamente agnóstica de la interfaz gráfica y de PySide6**, de manera que cualquier desarrollador o agente de IA pueda implementar o migrar un módulo hacia cualquier stack tecnológico futuro (Web React/Vue/Svelte, Tauri, Flutter, CLI, backend REST/GraphQL) sin necesidad de consultar el código fuente original de Qt.

---

## Estructura Modular Ramificada

```text
docs/specs/
├── README.md                          <- Este índice maestro y mapa funcional
├── core/
│   ├── timer_engine.spec.md           <- Reglas del cronómetro, acumuladores y modos
│   ├── session_lifecycle.spec.md      <- Estados de sesión (espera, estudio, receso, fin)
│   └── inciso_resolution.spec.md      <- Algoritmo de detección y corrección de incisos
├── data/
│   ├── persistence_contracts.spec.md  <- Esquemas JSON versión 1, invariantes y tipos
│   └── query_and_filtering.spec.md    <- Motor de ordenamiento y filtrado estilo Excel
├── planner/
│   ├── sections_and_goals.spec.md     <- Reglas de secciones planificadas y límites
│   └── progress_metrics.spec.md       <- Algoritmos de avance, métricas y analítica
├── audio/
│   └── ambient_and_effects.spec.md    <- Especificación de mezcla ambiental y efectos
├── statistics/
│   ├── statistics_view.spec.md        <- Rediseño analítico temporal (General, Semanal, Diario) y MVP
│   └── today_activity_strip.spec.md   <- Franja de actividad 24h y aguja temporal en tiempo real
├── export/
│   └── export_service.spec.md         <- Exportación estandarizada CSV/Excel (RFC 4180, utf-8-sig)
└── themes/
    ├── color_tokens.spec.md           <- Diccionario de tokens de color requeridos por tema
    └── skins_catalog.spec.md          <- Catálogo ampliado de skins (Pantone, estacionales y selección)
```

---

## Regla de Oro para Agentes y Desarrolladores

* **Autocontención:** Cada archivo `.spec.md` contiene todo el conocimiento necesario para reconstruir o entender su área funcional: modelos de datos, entradas, salidas, reglas de validación y casos de borde.
* **Sincronización Bidireccional:** Todo cambio implementado en el código fuente debe quedar reflejado de inmediato en su especificación correspondiente.
