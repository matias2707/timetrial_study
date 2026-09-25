# Especificación Técnica — Módulo de Estadísticas y Analítica Temporal

**Módulo:** `presentation/statistics/`, `application/statistics_service.py`  
**Fecha:** 2026-09-25  
**Estado:** Especificación de Rediseño Temporal y Presenter MVP  

---

## 1. Propósito Funcional

El subsistema de estadísticas proporciona al estudiante una plataforma analítica dividida en tres dimensiones temporales estrictas:
1. **🌐 Dimensión General (Visión Global y Evolución):**
   - KPIs macro acumulativos de toda la cursada (tiempo neto total, descansos, racha de días, tasa de avance de la materia).
   - **Gráfico de Evolución Acumulativa:** Proyección temporal del esfuerzo acumulado (horas netas a lo largo de las semanas) y evolución de la curva de aprendizaje (ejercicios completados vs. intentos incompletos/fallados acumulados).
   - **Cronograma de Cursada (`CourseHeatmapWidget`):** Calendario mensual interactivo con hitos de evaluación y volumen de estudio.
   - **Desglose Curricular por Guías:** Resumen de avance, tiempos e intentos por sección.
   - **Ranking de Mayor Esfuerzo:** Clasificación de ejercicios con criterio alternable (por tiempo acumulado, cantidad de reintentos o mejores marcas/récords) y acceso directo al cronómetro.
   - **Distribución Circadiana 24 Horas (`Hourly24hChartWidget`):** Histograma de franjas horarias con cálculo del horario pico de productividad.

2. **📊 Dimensión Semanal (Ritmo de 7 Días y Carga Semanal):**
   - Navegación bidireccional entre semanas (`Semana Anterior`, `Semana Actual`, `Semana Siguiente`).
   - KPIs de la semana: Tiempo neto total, promedio diario sobre días activos, días estudiados (ej. 5/7) y tasa de completitud semanal.
   - **Gráfico Semanal Diario (`WeeklyChartWidget`):** Comparativa visual de los 7 días (Lunes a Domingo) con balance exacto entre estudio y descansos.
   - **Desglose de Ejercicios de la Semana:** Lista agrupada de todos los ejercicios abordados en dicha semana con sus tiempos e intentos.

3. **📅 Dimensión Diaria (Registro Quirúrgico de la Jornada):**
   - Navegación por fechas (`Día Anterior`, `Hoy`, `Día Siguiente` y selección directa).
   - KPIs de la jornada: Tiempo neto, descansos acumulados, conteo de ejercicios y tasa de efectividad (% de intentos completados vs. fallados).
   - **Tabla Cronológica de Intentos del Día:** Registro secuencial de cada sesión realizada (hora inicio/fin, guía, ejercicio, inciso, tiempo neto, receso, estado completado/fallado, notas) y acción de un clic para recargar el ejercicio en el cronómetro.

4. **Acción de Exportación Unificada:** Cabecera con botón directo `[ 📤 Exportar Datos ]` que prepara la integración nativa de TASK-009.

---

## 2. Modelos y Contratos de Datos (DTOs)

Todos los modelos de transporte son inmutables (`@dataclass(frozen=True)`):

```python
@dataclass(frozen=True)
class DailyAttemptLogEntry:
    item_id: str
    timestamp: str  # ISO string
    start_time_str: str  # HH:MM
    section_display: str  # ej: "Guía 1" o "TP 2"
    section_type: str
    section_number: int
    exercise: int
    inciso: int | None
    exercise_time_ms: int
    break_time_ms: int
    completed: bool
    notes: str = ""

@dataclass(frozen=True)
class DailyStatsSummary:
    target_date: str  # YYYY-MM-DD
    display_date: str  # ej: "Jueves, 25 de Septiembre"
    is_today: bool
    total_exercise_time_ms: int
    total_break_time_ms: int
    attempts: list[DailyAttemptLogEntry]
    completed_count: int
    failed_count: int
    focus_ratio: float  # 0.0 a 1.0 (tiempo_estudio / (tiempo_estudio + tiempo_receso))

@dataclass(frozen=True)
class WeeklyDaySummary:
    date_str: str  # YYYY-MM-DD
    day_name: str  # Lun, Mar, Mié...
    exercise_time_ms: int
    break_time_ms: int
    completed_count: int
    failed_count: int

@dataclass(frozen=True)
class WeeklyExerciseItem:
    section_type: str
    section_number: int
    exercise: int
    inciso: int | None
    section_display: str
    total_exercise_time_ms: int
    attempts_count: int
    is_completed: bool

@dataclass(frozen=True)
class WeeklyStatsSummary:
    week_start_str: str  # YYYY-MM-DD
    week_end_str: str    # YYYY-MM-DD
    display_range: str   # ej: "18 Sep - 24 Sep 2026"
    is_current_week: bool
    total_exercise_time_ms: int
    total_break_time_ms: int
    active_days_count: int
    days: list[WeeklyDaySummary]
    exercises: list[WeeklyExerciseItem]
    completed_count: int
    failed_count: int

@dataclass(frozen=True)
class CumulativePoint:
    date_str: str
    cumulative_exercise_time_ms: int
    cumulative_completed: int
    cumulative_failed: int

@dataclass(frozen=True)
class CumulativeEvolutionData:
    points: list[CumulativePoint]
    total_study_time_ms: int
    total_completed: int
    total_failed: int

@dataclass(frozen=True)
class GeneralStatsSummary:
    record_name: str
    total_attempts: int
    total_exercise_time_ms: int
    total_break_time_ms: int
    avg_exercise_time_ms: int
    avg_break_time_ms: int
    longest_exercise_time_ms: int
    longest_exercise_name: str
    completed_unique_exercises: int
    total_unique_exercises: int
    completion_percentage: float
    has_planner: bool
    planned_completed_display: str
    planned_total_units: int
    planned_completion_percentage: float
    streak_days: int
    total_days_studied: int
    peak_productivity_hour: str  # ej: "16:00 - 18:00"
    focus_ratio: float
    cumulative_evolution: CumulativeEvolutionData
```

---

## 3. Contratos de Interfaz (MVP / Passive View)

### Protocolo de Vista (`presentation/statistics/interfaces.py`)
```python
class IStatisticsView(Protocol):
    def set_empty_state(self, is_empty: bool) -> None: ...
    def render_general_tab(self, summary: GeneralStatsSummary, top_effort: list[Any], sections_summary: list[Any], heatmap_data: Any, hourly_data: Any) -> None: ...
    def render_weekly_tab(self, summary: WeeklyStatsSummary) -> None: ...
    def render_daily_tab(self, summary: DailyStatsSummary) -> None: ...
    def set_active_subtab(self, index: int) -> None: ...
```

### Eventos de Usuario Gestionados por el Presenter
- `on_tab_changed(index: int)`: Conmuta entre General (0), Semanal (1) y Diario (2).
- `on_navigate_week(direction: int)`: -1 (anterior), 0 (actual), +1 (siguiente).
- `on_navigate_day(direction: int)`: -1 (anterior), 0 (hoy), +1 (siguiente) o fecha fija.
- `on_change_top_effort_sort(criteria: str)`: "time", "retries", "pb".
- `on_load_exercise_requested(section_type, section_number, exercise, inciso)`: Emite señal para recargar en el cronómetro principal.
- `on_configure_schedule_requested()`: Abre diálogo de hitos de examen.
- `on_export_requested()`: Dispara diálogo de exportación.

---

## 4. Reglas de Negocio y Algoritmos Analíticos

1. **Racha de Días (Streak):**
   - Un día se considera "activo" si contiene al menos 1 intento completado o no nulo en `items`.
   - Se evalúa de manera contigua retrospectiva desde hoy (o ayer si hoy aún no se registra estudio).
2. **Curva de Evolución Acumulativa:**
   - Agrupa intentos por fecha cronológica ascendente.
   - Acumula progresivamente:
     $$\text{Tiempo Acumulado}(d) = \sum_{t \le d} \text{tiempo}(t)$$
     $$\text{Completados Acumulados}(d) = \sum_{t \le d, \text{ok}} 1$$
     $$\text{Fallados Acumulados}(d) = \sum_{t \le d, \text{no ok}} 1$$
3. **Determinismo Semanal:**
   - Semana normalizada de Lunes (0) a Domingo (6).
   - Soporta navegación infinita hacia atrás/adelante sin excepciones si no hay registros en la semana (muestra KPIs en cero de forma amigable).
4. **Respeto a `AGENTS.md`:**
   - Cero imports de `PySide6` o `Qt` en `presentation/statistics/statistics_presenter.py`.
   - Tokens de tema centralizados desde `get_theme_tokens()`.
