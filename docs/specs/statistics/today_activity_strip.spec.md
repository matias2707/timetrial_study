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

1. **Causalidad contra reloj de pared (`now`):** Si `dt + dur > now + 5s`, la sesión no pudo terminar en el futuro respecto a la hora real de consulta; se resuelve como finalizada en `dt` (`item_end = dt`, `item_start = dt - dur`).
2. **Causalidad contra actualización de archivo (`record.updated_at`):** Si `dt + dur > updated_at + 10s`, la sesión no pudo extenderse más allá del momento en que el archivo fue guardado en disco; se resuelve como finalizada en `dt`.
3. **Causalidad secuencial entre intentos:** Si el registro posterior en la misma fecha inicia antes de `dt + dur - 5s`, se descarta el solapamiento imposible resolviendo `item_end = dt`.
4. **Modo Inicio:** Si no se viola ningún principio de causalidad (ej. intentos nuevos con `created_at` grabado al inicio de sesión), se resuelve como `item_start = dt` e `item_end = dt + dur`.

Esta formulación garantiza retrocompatibilidad absoluta con registros históricos grabados al término del ejercicio y previene la fuga o derrame de horas netas a través de la medianoche hacia el día siguiente.

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
