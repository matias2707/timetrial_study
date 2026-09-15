# Control de Pendientes y Hoja de Ruta — Study Timetrial

**Fecha de creación:** 2026-09-13  
**Última actualización:** 2026-09-13  
**Estado general:** En desarrollo activo  

---

## 1. Convenciones y Estructura

Para mantener la claridad del ciclo de vida de cada tarea y asegurar la consistencia arquitectónica del proyecto, se utilizan las siguientes convenciones:

### Estados de Tarea
- `[ ]` **Pendiente:** Tarea definida y lista para ser implementada.
- `[/]` **En progreso:** Tarea actualmente en desarrollo activo.
- `[x]` **Completado:** Tarea implementada, validada funcionalmente y con pruebas unitarias pasando.
- `[-]` **Descartado / Pospuesto:** Tarea cancelada o diferida a versiones futuras (con motivo especificado).

### Niveles de Prioridad
- 🔴 **Alta:** Funcionalidad crítica para el flujo principal de estudio o arquitectura base.
- 🟡 **Media:** Mejora relevante de usabilidad, análisis o herramientas complementarias.
- 🟢 **Baja:** Detalle cosmético, micro-optimización o exploración futura.

### Capas Arquitectónicas Afectadas
- **`presentation/`**: Interfaz PySide6 (vistas, widgets, diálogos, estilos QSS, tokens).
- **`application/`**: Servicios de coordinación, orquestación de casos de uso y lógica de sesión.
- **`domain/`**: Entidades fundamentales (`Record`, `TimerItem`, `PlannedSection`) y servicio de reloj (`TimerService`).
- **`infrastructure/`**: Persistencia atómica de archivos JSON, IO y sistema de archivos.
- **`tests/`**: Pruebas unitarias automatizadas.

---

## 2. Matriz de Seguimiento Rápido

| ID | Tarea | Prioridad | Capas | Estado |
| :--- | :--- | :---: | :--- | :---: |
| [TASK-001](#task-001) | Continuación desde registros (recarga al cronómetro para actualización/sobrescritura) | 🔴 Alta | `presentation`, `application`, `domain`, `tests` | `[ ]` |

---

## 3. Detalle de Pendientes

### TASK-001
#### Implementar continuación desde registros (volver a cargar los tiempos de un registro al cronómetro, para actualizarlo/sobrescribirlo)

- **Prioridad:** 🔴 Alta  
- **Estado:** `[ ] Pendiente`  
- **Capas afectadas:** `presentation/`, `application/`, `domain/`, `tests/`  

##### Descripción funcional
Permitir que el usuario retome un intento previamente guardado desde la pestaña de **Registros**, transfiriendo sus datos al **Cronómetro** de la vista principal. Esto resuelve escenarios donde el usuario pausó su sesión de estudio y guardó el registro temporalmente, registró un intento por error antes de finalizar el ejercicio, o necesita extender el tiempo neto o de descanso de un intento ya existente.

##### Casos de uso y flujo de interacción
1. **Disparo desde Registros:**
   - En la tabla de `RecordsViewWidget`, al hacer clic derecho sobre una fila (menú contextual) o mediante un botón de acción en la barra de herramientas, disponer de la opción **"Continuar intento en el cronómetro"**.
2. **Protección de sesión activa:**
   - Si el cronómetro en `HomeViewWidget` ya cuenta con tiempo acumulado (`exercise_time_ms > 0` o `break_time_ms > 0`) o está en ejecución, mostrar un diálogo de confirmación advirtiendo que el intento actual en pantalla será reemplazado.
3. **Precarga en el Cronómetro:**
   - Navegar automáticamente a la pestaña del Cronómetro (`HomeViewWidget`).
   - Cargar en `TimerService` los tiempos del intento: `exercise_time_ms` y `break_time_ms`.
   - Actualizar los selectores de ubicación: tipo de sección, número de sección, ejercicio e inciso correspondiente al registro.
   - Precargar el campo de notas/comentarios con el texto guardado previamente.
   - Configurar el cronómetro en estado pausado/listo para reanudar (`PLAY` o `BREAK` según corresponda).
4. **Identidad visual del modo edición/continuación:**
   - Mostrar un indicador visual distintivo (badge o barra de aviso contextual) en `HomeViewWidget` señalando que se está en **"Modo continuación: editando intento existente"**, indicando fecha/hora original y un botón para **"Cancelar edición"** (que limpie el cronómetro o vuelva al estado nuevo).
5. **Guardado y resolución de persistencia:**
   - Al presionar **Registrar intento**:
     - **Opción predeterminada (Sobrescribir):** Reemplazar el `TimerItem` original dentro de `record.items` con los nuevos tiempos acumulados y notas actualizadas, conservando o registrando la marca temporal de actualización.
     - **Opción alternativa (Guardar como nuevo):** Permitir bifurcar y registrar como un intento adicional sin alterar el registro histórico previo.

##### Cambios técnicos proyectados por capa
- **`domain/timer_service.py`**:
  - Incorporar método `load_accumulated_times(exercise_ms: int, break_ms: int)` para inicializar tiempos de manera determinista y sincronizar los deltas sin romper la monotonía de `time.perf_counter()`.
- **`application/application_service.py`**:
  - Añadir soporte para seguimiento de `editing_item_id: str | None` o referencia a `editing_item`.
  - Método `load_item_into_session(item: TimerItem)` que configure el temporizador, la ubicación y el comentario pendiente.
  - Método `commit_current_session(overwrite: bool = True)` que decida entre `replace_item` o `add_item`.
- **`presentation/records_view.py`**:
  - Agregar acción en el menú contextual de la tabla: *"Continuar este intento en el cronómetro"*.
  - Emitir señal `resume_item_requested(TimerItem)`.
- **`presentation/main_window.py`**:
  - Conectar la señal de `RecordsViewWidget` con el orquestador principal, coordinar la llamada a `application_service` y cambiar la pestaña activa al índice del cronómetro (`home_view`).
- **`presentation/home_view.py`**:
  - Widget de banner/alerta de continuación ("✏️ Continuando intento existente...").
  - Actualización reactiva de relojes con los tiempos cargados.
  - Gestión de botones de acción rápida para confirmar sobrescritura o descartar.
- **`tests/`**:
  - Pruebas unitarias en `test_application_service.py` y `test_timer_service.py` comprobando la recarga de tiempos, no regresión de cronometraje y sobrescritura de items.

##### Criterios de aceptación
- [ ] La acción está disponible en el menú contextual de la tabla de registros.
- [ ] Al seleccionar la acción, la interfaz cambia al cronómetro con la ubicación, tiempos y notas correctamente precargados.
- [ ] Si hay una sesión con tiempo en curso, se solicita confirmación antes de descartarla.
- [ ] El cronómetro puede reanudar la marcha a partir de los tiempos cargados sumando nuevos lapsos con precisión.
- [ ] Se puede guardar el intento sobrescribiendo el registro existente en el archivo JSON sin duplicarlo.
- [ ] Se puede cancelar el modo edición para regresar a un intento nuevo limpio.
- [ ] La suite de pruebas automatizadas pasa al 100% (`python -m unittest discover -s tests -v`).

---

## 4. Backlog de Futuras Mejoras (Ideas en Evaluación)

### 📊 Registros y Estadísticas
- [ ] Exportación de registros y estadísticas a formatos externos (CSV, Excel `.xlsx`, PDF).
- [ ] Comparativa de rendimiento entre diferentes guías o secciones.
- [ ] Detección de patrones de cansancio según evolución del ratio tiempo neto / tiempo de descanso.

### ⏱️ Cronómetro y Sesión
- [ ] Atajos de teclado globales configurables para iniciar/pausar/descanso desde cualquier vista o ventana secundaria.
- [ ] Temporizador tipo Pomodoro o metas de tiempo por ejercicio con avisos audibles y visuales.

### 🎨 UI / UX y Configuración
- [ ] Personalización avanzada de paleta de colores y selección de fuentes.
- [ ] Opción para configurar el volumen del audio o seleccionar sonidos alternativos de notificación.
