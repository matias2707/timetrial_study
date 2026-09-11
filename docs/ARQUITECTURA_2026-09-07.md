# Arquitectura de Study Timetrial

**Fecha de revisión:** 2026-09-11  
**Estado:** vigente para la implementación actual

Este documento describe la estructura que debe preservarse durante cambios
incrementales. Si una modificación cambia una responsabilidad o un contrato,
debe actualizarse este documento y la prueba correspondiente.

## Objetivo

Mantener una aplicación de escritorio modular, comprobable y sin dependencia de
PySide6 en la lógica que puede probarse sin una ventana. La interfaz traduce
eventos y gestiona el estado visual; la aplicación coordina casos de uso, consultas
y planificaciones; el dominio define reglas, modelos y entidades; la infraestructura
gestiona la persistencia en archivos JSON locales.

## Capas y dependencias

```mermaid
flowchart TD
    subgraph UI [Capa de Presentación - presentation/]
        MW[MainWindow - main_window.py]
        PW[PlannerWidget - planner_widget.py]
        WC[WeeklyChartWidget - weekly_chart_widget.py]
        EF[ExcelFilterPopup - excel_filter_popup.py]
        ID[IncisoDialog - inciso_dialog.py]
        PD[PresentationDialogs - presentation_dialogs.py]
        PF[Formatters - presentation_formatters.py]
        TH[Theme & Estilos - theme.py]
    end

    subgraph APP [Capa de Aplicación - application/]
        AS[StudyApplicationService - application_service.py]
        PS[PlannerService - planner_service.py]
        SS[StatisticsService - statistics_service.py]
        RQ[RecordQuery - record_query.py]
    end

    subgraph DOMAIN [Capa de Dominio - domain/]
        MD[Models - models.py\nRecord, TimerItem, PlannedSection]
        TS[TimerService - timer_service.py\nTimerMode, TimerService]
    end

    subgraph INFRA [Capa de Infraestructura - infrastructure/]
        ST[StorageService - storage_service.py]
        RF[RecentFilesManager]
    end

    JSON[(Archivos JSON locales)]

    UI --> APP
    UI --> DOMAIN
    APP --> DOMAIN
    APP --> INFRA
    INFRA --> DOMAIN
    INFRA --> JSON
```

### Detalle de módulos por capa

- **Presentación (`presentation/`):**
  - `main_window.py`: Coordina la ventana principal, toolbar superior, pestañas (Cronómetro, Registros, Estadísticas, Planificador), navegación de ejercicios, audio y ciclo de vida de archivos.
  - `weekly_chart_widget.py`: Renderiza el gráfico semanal con `QPainter` en alta resolución antialiasing, adaptado a modo claro y oscuro.
  - `planner_widget.py`: Visualiza la cuadrícula de planificación con tarjetas (`PlannedSectionCard`), grupos de ejercicios e incisos, barra de progreso y diálogo de carga de ejercicio.
  - `planner_dialogs.py`: Diálogos modales para alta, edición y configuración de secciones planificadas.
  - `excel_filter_popup.py`: Popup interactivo estilo Excel para filtrado por valores únicos y ordenamiento jerárquico por columna.
  - `inciso_dialog.py`: Diálogo modal para detección y resolución guiada de desfasajes de incisos (gap resolution).
  - `flow_layout.py`: Distribución adaptativa de elementos que ajusta filas y columnas automáticamente al redimensionar.
  - `presentation_dialogs.py`: Diálogos Qt para alta/edición manual de registros e importación selectiva desde otros archivos JSON.
  - `presentation_formatters.py`: Adaptadores para representar tiempos (`format_milliseconds`, `format_hh_mm`, `format_hh_mm_ss`, `timer_markup`).
  - `theme.py`: Generador central de hojas de estilo QSS para Modo Claro y Modo Oscuro, temas de diálogos y estilos dinámicos del cronómetro.
  - `media/`: Efectos de audio en formato WAV para inicio y finalización de ejercicios.
  - `main.py`: Punto de entrada que inicializa `QApplication` y levanta `MainWindow`.

- **Aplicación (`application/`):**
  - `application_service.py`: Fachada principal (`StudyApplicationService`) que expone casos de uso para sesión del cronómetro, navegación, comentarios pendientes, importación, límites de sesión y persistencia.
  - `planner_service.py`: Lógica de análisis de ejercicios planificados (`PlannerService`), cálculo de métricas de completitud ponderadas (`completed_weight`), sincronización de ejercicios no planificados y control de límites.
  - `statistics_service.py`: Cálculos estadísticos globales, distribución por días y por secciones (`DailyStatistic`, `SectionSummary`, `RecordStatistics`).
  - `record_query.py`: Filtrado multicriterio, ordenamiento jerárquico multicomponente y extracción de valores únicos para la vista Registros.

- **Dominio (`domain/`):**
  - `models.py`: Entidades del dominio: `TimerItem` (intento de ejercicio), `PlannedSection` (sección planificada con mapa de incisos) y `Record` (agrupador raíz persistido).
  - `timer_service.py`: Reloj monotónico de precisión milimétrica (`TimerService`) con estados `WAITING`, `PLAY` y `BREAK`, y soporte de pausa temporal sin pérdida de tiempo.

- **Infraestructura (`infrastructure/`):**
  - `storage_service.py`: Encapsula la lectura/escritura JSON atómica de `Record` (`StorageService`) y la gestión de la lista de archivos recientes (`RecentFilesManager`).

- **Pruebas (`tests/`):**
  - 11 suites de pruebas unitarias (`test_application_service.py`, `test_planner_service.py`, `test_statistics_service.py`, `test_record_query.py`, `test_inciso_correction.py`, `test_main_window_records.py`, `test_main_window_planner.py`, `test_theme.py`, etc.) que cubren la aplicación completa sin necesidad de abrir ventanas gráficas interactivas.

## Reglas de diseño

1. La presentación puede importar aplicación y tipos de dominio para adaptar formularios y vistas, pero nunca escribe JSON directamente ni gestiona la persistencia por su cuenta.
2. Ningún módulo de `application/`, `domain/` o `infrastructure/` importa PySide6 ni componentes gráficos de Qt.
3. `domain/` no conoce Qt, widgets, rutas de interfaz ni servicios de almacenamiento.
4. `infrastructure/storage_service.py` es el único módulo responsable de serializar registros y administrar archivos recientes.
5. Las entidades mantienen sus nombres de campos porque forman parte del contrato JSON público local existente.
6. Los nombres nuevos usan `snake_case`, clases `PascalCase` y constantes `UPPER_SNAKE_CASE`.
7. Las dependencias de `StudyApplicationService` se inyectan para permitir dobles en memoria en las pruebas.
8. Los cambios de formato JSON requieren versionado o compatibilidad hacia atrás estricta y su correspondiente prueba.
9. Los widgets muestran estado y emiten acciones; no duplican reglas de negocio ni cálculos matemáticos de métricas.
10. Cada módulo debe tener una breve docstring de responsabilidad y cada función pública debe explicar su contrato.

## Contratos importantes

- El JSON conserva `schema_version: 1`, los campos de `Record`, `TimerItem` y la lista de `planner_sections`; el detalle completo se encuentra en [CONTRATO_JSON.md](CONTRATO_JSON.md).
- Los tiempos se miden con reloj monotónico y se almacenan en milisegundos enteros no negativos.
- `TimerMode` opera estrictamente con `WAITING`, `PLAY` y `BREAK`.
- `StudyApplicationService` es la fachada que usa la interfaz y recibe almacenamiento y cronómetro por inyección de dependencias.

## Validación

La comprobación mínima tras una refactorización o cambio es:

```powershell
python -m unittest discover -s tests -v
python -m py_compile main.py presentation/main_window.py presentation/weekly_chart_widget.py presentation/planner_widget.py presentation/planner_dialogs.py presentation/inciso_dialog.py presentation/excel_filter_popup.py presentation/flow_layout.py presentation/presentation_dialogs.py presentation/presentation_formatters.py presentation/theme.py application/application_service.py application/planner_service.py application/statistics_service.py application/record_query.py domain/models.py domain/timer_service.py infrastructure/storage_service.py
```

No se debe editar manualmente ningún JSON de usuario para resolver un problema de código. Los pasos completos están detallados en [OPERACION_Y_VALIDACION.md](OPERACION_Y_VALIDACION.md).
