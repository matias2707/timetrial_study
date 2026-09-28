# Especificación Técnica — Franja de Actividad Diaria y Aguja Temporal 24 Horas

**Módulo:** `presentation/today_activity_strip_widget.py`, `application/statistics_service.py`  
**Fecha:** 2026-09-26  
**Estado:** Activo / Producción (TASK-014 / Enhancements)

---

## 1. Propósito Funcional

El widget **Actividad de Hoy** (`TodayActivityStripWidget`) proporciona al estudiante una visualización continua y de alto impacto sobre el ritmo y volumen de estudio distribuido a lo largo de las 24 horas de la jornada actual (de 00:00 a 24:00 hs).

El componente combina dos dimensiones críticas:
1. **Heatmap de Intensidad Horaria:** 24 celdas rectangulares independientes con 5 niveles de color que reflejan el tiempo de estudio neto acumulado y la cantidad de intentos realizados en cada bloque horario.
2. **Aguja / Cursor Vertical de Tiempo Real:** Un indicador lineal animado que atraviesa verticalmente los rectángulos horarios, desplazándose suavemente desde el inicio del día (00:00:00, extremo izquierdo del primer rectángulo) hasta el final del día (23:59:59 / 24:00:00, extremo derecho del último rectángulo), permitiendo al usuario observar con precisión visual el avance del tiempo y comparar su momento actual con las franjas ya estudiadas.

---

## 2. Contratos y Algoritmos de Posicionamiento

### 2.1. Fracción Diaria y Coordenada Continua

Para cualquier instante temporal $T = (H, M, S, \mu s)$:

1. **Fracción del Día:**
   $$\text{progreso} = \frac{H \times 3600 + M \times 60 + S + \frac{\mu s}{1\,000\,000}}{86400} \in [0.0, 1.0]$$

2. **Interpolación Geométrica Continua por Rectángulo:**
   Para garantizar una alineación exacta de $0.0\text{ px}$ de error con los bordes de cada celda y un paso suave y sin saltos a través de las separaciones de $3\text{ px}$ entre celdas:

   - **Fracción dentro de la hora actual:**
     $$f_h = \frac{M \times 60 + S + \frac{\mu s}{1\,000\,000}}{3600.0} \in [0.0, 1.0)$$

   - **Posición horizontal $X(T)$:**
     - Para horas $H \in [0, 22]$:
       $$X(T) = X_{\text{celda}[H]} + f_h \times \left( X_{\text{celda}[H+1]} - X_{\text{celda}[H]} \right)$$
     - Para la hora $H = 23$ (última hora del día):
       $$X(T) = X_{\text{celda}[23]} + f_h \times \text{ancho}_{\text{celda}[23]}$$

### 2.2. Continuidad y Puntos Notables

- **00:00:00 (Inicio de jornada):** Coincide con el borde izquierdo exacto de la celda 0 (`X = cell[0].x`).
- **06:00:00 (Madrugada):** Coincide con el borde izquierdo de la celda 6 (`X = cell[6].x`).
- **12:00:00 (Mediodía):** Coincide con el centro del strip y borde izquierdo de la celda 12 (`X = cell[12].x`).
- **18:00:00 (Tarde):** Coincide con el borde izquierdo de la celda 18 (`X = cell[18].x`).
- **23:00:00 (Noche):** Coincide con el borde izquierdo de la celda 23 (`X = cell[23].x`).
- **23:59:59 (Fin de jornada):** Coincide con el borde derecho de la celda 23 (`X = cell[23].x + cell[23].width`).
- **Transición entre horas:** Al completarse una hora ($f_h \to 1.0$), la aguja atraviesa naturalmente el espacio intercelular y arriba exactamente a la siguiente celda sin discontinuidades visuales.

### 2.3. Resolución de Intervalo de Sesión y Reglas de Causalidad Anti-Spill

El cálculo de franjas horarias (`compute_today_timeline_buckets` y `get_24h_hourly_distribution`) delega en `resolve_item_time_interval` para determinar con precisión matemática el inicio y fin de cada sesión `[item_start, item_end]` a partir de `item.created_at` y `total_duration_ms`:

1. **Esquema de Creación Dual y Retrocompatibilidad:**
   - **Items Estándar (Modernos):** Creados mediante `StudyApplicationService.finish_item` con `session_started_at`. Su atributo `created_at` (`dt`) refleja el **inicio real** de la sesión, y la finalización real se calcula como `dt + dur`.
   - **Items Legados (Completion-Stamped):** Archivos históricos o registros manuales donde `created_at` (`dt`) se estampó al **finalizar** la sesión, habiendo iniciado en `dt - dur`.
   - **Sesiones Prolongadas (hasta 6 horas o más):** Durante sesiones de estudio extensas, el temporizador de alta resolución (`time.perf_counter`) y el reloj de pared (`datetime.now()`) pueden acumular leves derivas (10 a 30 segundos). La heurística no debe confundir esta pequeña deriva con un registro legado.

2. **Criterios Matemáticos de Detección:**
   Para un item con duración total $D = \text{dur} = \text{exercise\_time\_ms} + \text{break\_time\_ms}$:
   - **Umbral de proximidad:** $U_{\text{near}} = \max(120\text{ s}, 0.20 \times D)$
   - **Umbral de exceso hacia el futuro:** $U_{\text{excess}} = \max(15\text{ s}, 0.40 \times D)$

   Un item se clasifica como legado (completion-stamped, resolviendo `[dt - dur, dt]`) si y solo si:
   - Su marca `dt` coincide estrechamente con el evento de guardado/consulta $T_{\text{ref}}$ ($|T_{\text{ref}} - dt| \le U_{\text{near}}$).
   - Y proyectar $dt + dur$ generaría una intrusión anómala mayoritaria hacia el futuro $((dt + dur) - T_{\text{ref}} \ge U_{\text{excess}}$).

   Donde $T_{\text{ref}}$ se evalúa secuencialmente contra:
   - `record.updated_at` (guardado en disco).
   - `now_dt` (reloj de pared o referencia temporal inyectada).
   - `next_item.created_at` (siguiente intento en la misma fecha).

3. **Modo Estándar (Start-Stamped):**
   Si no se cumplen simultáneamente ambas condiciones de exceso mayoritario y proximidad, el item se resuelve de forma determinista como `item_start = dt` e `item_end = dt + dur`.

4. **Acotamiento Anti-Spill en Franjas de Hoy:**
   En `compute_today_timeline_buckets`, para la jornada en curso (`is_today = True`):
   - Cualquier hora futura ($h > \text{now.hour}$) queda estrictamente forzada a $0\text{ ms}$ y $0$ intentos.
   - La hora actual ($h = \text{now.hour}$) se acota al tiempo efectivamente transcurrido en dicha hora ($\text{now} - h_{\text{start}}$).
   - Para ejercicios que cruzan la medianoche, las horas pertenecientes a cada jornada se computan exclusivamente dentro de los límites de las 00:00 a las 24:00 hs de la fecha consultada.

---

## 3. Arquitectura Visual y Presentación Pasiva

### 3.1. Estructura de Componentes

```text
TodayActivityStripWidget (QFrame)
├── Cabecera (QHBoxLayout)
│   ├── "ACTIVIDAD DE HOY" (QLabel #eyebrow)
│   └── "HORA ACTUAL: HH:MM" (QLabel #activity_strip_now)
├── Pista de Celdas (ActivityTrackWidget)
│   ├── cells_layout (QHBoxLayout, 24 x QFrame #activity_cell_0..23)
│   └── needle_overlay (TimelineNeedleOverlay, WA_TransparentForMouseEvents)
└── Marcas Horarias (QHBoxLayout)
    └── 00:00, 06:00, 12:00, 18:00, 23:00 (Q而后Labels)
```

### 3.2. Diseño de la Aguja

La aguja está compuesta por:
1. **Halo de Contraste:** Trazo de $3.5\text{ px}$ semitransparente (negro en modo oscuro, blanco translúcido en modo claro) que asegura legibilidad universal sobre fondos inactivos (zinc/slate) o celdas verdes activas.
2. **Glow:** Resplandor de $5\text{ px}$ en color acento celeste/azul.
3. **Línea Central:** Trazo nítido de $2.0\text{ px}$ en `#38bdf8` (modo oscuro) o `#0284c7` (modo claro).
4. **Cabezal Superior (Pointer):** Marcador triangular invertido ($8\text{ px} \times 5\text{ px}$) en la parte superior que apunta directamente a la hora actual.
5. **Terminador Inferior:** Pequeño remate circular ($r = 1.5\text{ px}$) en la base de la pista.

### 3.3. Transparencia de Eventos de Ratón

El overlay de la aguja cuenta con `setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)`. De esta forma:
- La aguja **no intercepta ni bloquea** eventos de cursor.
- Al pasar el ratón por encima de cualquier punto de la pista (incluso directamente sobre la aguja), se activan los tooltips informativos detallados de la celda horaria subyacente.

---

## 4. Dinámica Temporal y Rendimiento

1. **Temporizador Autónomo:** Dispone de un `QTimer` interno a $1000\text{ ms}$ (1 segundo) que actualiza la posición de la aguja incluso cuando el cronómetro principal está detenido.
2. **Sincronización con el Cronómetro:** En `HomeViewWidget.refresh_clock()`, se invoca `refresh_needle()` en cada ciclo de refresco para máxima suavidad cuando la aplicación está en sesión activa.
3. **Cambio Automático de Hora:** Al cruzar la frontera de una nueva hora, se refresca automáticamente el halo de hora actual en las celdas sin requerir recarga manual.
4. **Modo Ahorro:** Si el widget no es visible (`isVisible() == False`), omite operaciones de repintado.

---

## 5. Contrato de Pruebas Unitarias y Determinismo

Para garantizar pruebas unitarias deterministas sin depender del reloj del sistema operativo:
- `strip.set_reference_time(datetime | None)`: Inyecta una fecha/hora arbitraria.
- `strip.current_time`: Expone la hora actual o la de referencia inyectada.
- `strip.needle_progress`: Expone el valor escalar $[0.0, 1.0]$.
- `strip.get_needle_x()`: Expone la coordenada $X$ en píxeles.
- `strip.show_needle`: Permite ocultar o visualizar la aguja mediante flag booleano.
