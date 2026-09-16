# Product Backlog y Hoja de Ruta — Study Timetrial

**Fecha de creación:** 2026-09-13  
**Última actualización:** 2026-09-16  
**Estado general:** En desarrollo activo  
**Audiencia / Destino:** Desarrolladores humanos y Agentes Autónomos de IA  

> **Guía operativa para Agentes de IA:** Este documento constituye la fuente única de verdad para la planificación y ejecución de tareas. Cada ítem incluye contexto funcional, puntos de contacto arquitectónicos por archivo y criterios de aceptación verificables mediante tests automatizados.

---

## 1. Convenciones y Estructura

### Tipos de Tarea (Standard Issue Types)
- ✨ **Feature:** Nueva funcionalidad o módulo para el usuario.
- 🐛 **Bugfix:** Corrección de defectos, estados inválidos o fallos en tiempo de ejecución.
- 🔨 **Enhancement:** Evolución, rediseño o ampliación de una característica existente.
- 🧹 **Refactor / Tech Debt:** Mejoras estructurales internas sin alteración del comportamiento externo.

### Estados de Tarea (Workflow Lifecycle)
- `[ ]` **Pendiente (Ready):** Tarea especificada técnicamente y lista para ser tomada por un agente o desarrollador.
- `[/]` **En progreso (In Progress):** Tarea actualmente en desarrollo activo en el workspace.
- `[x]` **Completado (Done):** Código implementado, verificado manualmente y con el 100% de tests unitarios pasando.
- `[-]` **Descartado / Pospuesto (Archived):** Tarea cancelada o postergada formalmente con justificación documentada.

### Niveles de Prioridad
- 🔴 **Alta:** Crítica para la estabilidad, el flujo principal de estudio o la arquitectura base.
- 🟡 **Media:** Mejora relevante de usabilidad, herramientas complementarias o ampliación funcional.
- 🟢 **Baja:** Ajuste cosmético menor, micro-optimización o exploración futura.

### Capas Arquitectónicas del Proyecto
- **`presentation/`**: Interfaz PySide6 (vistas, widgets modulares, diálogos, estilos QSS y tokens de diseño).
- **`application/`**: Orquestación de casos de uso, lógica de sesión y servicios coordinadores (`StudyApplicationService`, `PlannerService`).
- **`domain/`**: Entidades fundamentales (`Record`, `TimerItem`, `PlannedSection`, `TagDefinition`) y lógica de reloj (`TimerService`).
- **`infrastructure/`**: Persistencia atómica de archivos JSON, IO y sistema de archivos (`StorageService`).
- **`tests/`**: Suite de pruebas unitarias automatizadas (`unittest`).

### Reglas de Invarianza para Agentes de IA (AI Guardrails)
1. **Invarianza del contrato JSON:** Respetar la tolerancia a campos opcionales (`docs/CONTRATO_JSON.md`). Nunca renombrar ni eliminar campos del esquema `1` sin migración explícita; los nuevos campos deben tener valores predeterminados seguros (`None`, `[]`, `{}`).
2. **Separación de Capas (SoC):** La capa `presentation` nunca accede directamente a `infrastructure` ni muta `domain` directamente; toda interacción debe pasar por `StudyApplicationService`.
3. **Determinismo del temporizador:** No alterar `time.perf_counter()` en `TimerService` con llamadas bloqueantes en el hilo principal de la UI.
4. **Verificación automatizada obligatoria:** Toda tarea que modifique `domain`, `application` o `infrastructure` debe incluir o actualizar pruebas en `tests/`. El comando de validación obligatorio que debe pasar al 100% es:  
   `python -m unittest discover -s tests -v`

---

## 2. Matriz de Seguimiento Rápido

| ID | Tipo | Tarea | Prioridad | Capas | Dependencias | Estado |
| :--- | :---: | :--- | :---: | :--- | :---: | :---: |
| [TASK-001](#task-001) | 🔨 Enhancement | Continuación desde registros (recarga al cronómetro para sobrescritura) | 🔴 Alta | `presentation`, `application`, `domain`, `tests` | Ninguna | `[x]` |
| [TASK-002](#task-002) | ✨ Feature | Sistema de marcadores y etiquetas para ejercicios en la planificación | 🔴 Alta | `presentation`, `application`, `domain`, `docs`, `tests` | Ninguna | `[ ]` |
| [TASK-003](#task-003) | 🔨 Enhancement | Sistema de notas y apuntes por ejercicio en la planificación (rediseño de comentarios) | 🟡 Media | `presentation`, `application`, `domain`, `docs`, `tests` | `TASK-002` (sugerida) | `[ ]` |
| [TASK-004](#task-004) | ✨ Feature | Pestaña de Ambientación: Mezclador de audio multicanal adaptativo al cronómetro | 🟡 Media | `presentation`, `application`, `infrastructure`, `domain`, `tests` | Ninguna | `[ ]` |
| [TASK-005](#task-005) | 🐛 Bugfix | Gestión de estado sin proyecto activo y prevención de operaciones erráticas al cerrar archivos | 🔴 Alta | `presentation`, `application`, `infrastructure`, `tests` | Ninguna | `[ ]` |

---

## 3. Detalle de Pendientes

### TASK-001
#### Implementar continuación desde registros (volver a cargar los tiempos de un registro al cronómetro, para actualizarlo/sobrescribirlo)

- **Tipo:** 🔨 Enhancement  
- **Prioridad:** 🔴 Alta  
- **Estado:** `[x] Completado`  
- **Capas afectadas:** `presentation/`, `application/`, `domain/`, `tests/`  
- **Dependencias:** Ninguna  

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
- [x] La acción está disponible en el menú contextual de la tabla de registros.
- [x] Al seleccionar la acción, la interfaz cambia al cronómetro con la ubicación, tiempos y notas correctamente precargados.
- [x] Si hay una sesión con tiempo en curso, se solicita confirmación antes de descartarla.
- [x] El cronómetro puede reanudar la marcha a partir de los tiempos cargados sumando nuevos lapsos con precisión.
- [x] Se puede guardar el intento sobrescribiendo el registro existente en el archivo JSON sin duplicarlo.
- [x] Se puede cancelar el modo edición para regresar a un intento nuevo limpio.
- [x] La suite de pruebas automatizadas pasa al 100% (`python -m unittest discover -s tests -v`).

---

### TASK-002
#### Sistema de marcadores y etiquetas para ejercicios en la planificación

- **Tipo:** ✨ Feature  
- **Prioridad:** 🔴 Alta  
- **Estado:** `[ ] Pendiente`  
- **Capas afectadas:** `domain/`, `application/`, `presentation/`, `infrastructure/`, `docs/`, `tests/`  
- **Dependencias:** Ninguna  

##### Descripción funcional
Permitir categorizar, marcar y rastrear ejercicios del universo de estudio mediante un sistema flexible de etiquetas visuales de color (ej. "Rehacer", "Duda para clase", "Consulté respuesta", etc.). Las etiquetas se definen y guardan a nivel del archivo de materia (`Record.tags`), mientras que la asociación de marcas queda ligada directamente a los ejercicios e incisos en la estructura del planificador (`PlannedSection.exercise_tags`), aislándolas del historial de tiempos del cronómetro (`items`). La asignación puede realizarse de forma rápida desde el cronómetro o directamente desde el planificador, visualizándose con una cinta distintiva en la esquina (*ribbon*) de cada casilla y permitiendo filtrado rápido.

##### Casos de uso y flujo de interacción
1. **Asignación rápida desde el Cronómetro (`HomeViewWidget`):**
   - Incorporar un botón **"🏷️ MARCADORES"** (o **"ETIQUETAS"**) junto al botón de comentarios.
   - Al presionarlo, despliega un menú emergente o diálogo compacto con casillas de verificación (checkboxes) de las etiquetas del catálogo actual para asociarlas al ejercicio e inciso activo.
   - Si el ejercicio no estaba contemplado previamente en la planificación, se sincroniza/incorpora automáticamente.
2. **Visualización y equilibrio gráfico en el Planificador (`PlannerWidget`):**
   - Redimensionar sutilmente los botones de ejercicios (`ExerciseCellButton`) de 46×44 px a ~52×48 px para dar espacio a futuras funcionalidades y mantener legibilidad.
   - Renderizar en la esquina superior un indicador tipo **Ribbon** (cinta/triángulo de color). Si el ejercicio posee múltiples marcas, la esquina se segmenta en bandas con sus respectivos colores.
   - El *tooltip* del botón despliega la lista completa de etiquetas con sus nombres y viñetas de color.
3. **Gestión y edición desde el Planificador:**
   - Al hacer clic en un ejercicio, el diálogo de detalle (`ExerciseDetailPopup`) incluye una sección dedicada a **"Marcadores / Etiquetas"** donde se pueden activar o desactivar marcas directamente, sin necesidad de ejecutar el cronómetro.
   - Proporcionar acceso a un diálogo de configuración para **editar el catálogo de etiquetas** de la materia: renombrar (ej. de "Etiqueta 1" a "Duda de clase"), cambiar color (paleta armónica preseleccionada + selector libre `QColorDialog`) o crear nuevas etiquetas.
4. **Filtro rápido en el Planificador:**
   - Incorporar en la barra superior del planificador un selector/filtro rápido: *"Ver todos"*, *"Solo con marcadores"* o filtrar por una etiqueta específica (ej. *"Solo Etiqueta 1"*). Al filtrar, los ejercicios no coincidentes se atenúan visualmente o se ocultan.
5. **Persistencia e independencia de datos:**
   - La estructura JSON persiste en 3 bloques independientes: `items` (tiempos), `planner_sections` (planificación y `exercise_tags`) y `tags` (catálogo de definiciones).
   - 100% retrocompatible: al abrir archivos sin `tags` o `exercise_tags`, se inicializan con valores por defecto sin provocar excepciones ni alterar los tiempos existentes.

##### Cambios técnicos proyectados por capa
- **`domain/models.py`**:
  - Definir dataclass `TagDefinition(id: str, name: str, color: str)` con métodos de serialización `to_dict` y `from_dict`.
  - Añadir campo `tags: list[TagDefinition]` en `Record` (con 4 etiquetas predeterminadas genéricas: Rojo `#ef4444`, Ámbar `#f59e0b`, Azul `#3b82f6`, Púrpura `#a855f7`).
  - Añadir campo `exercise_tags: dict[str, list[str]]` en `PlannedSection` (mapea clave de ejercicio/inciso como `"3"` o `"3.1"` a lista de IDs de etiquetas).
  - Métodos auxiliares en `PlannedSection`: `get_exercise_tags(exercise, inciso)`, `set_exercise_tags(exercise, inciso, tag_ids)`.
- **`docs/CONTRATO_JSON.md`**:
  - Documentar las especificaciones de `TagDefinition`, la sección `tags` en `Record` y `exercise_tags` en `PlannedSection`.
- **`application/planner_service.py` & `application/application_service.py`**:
  - Incorporar soporte de tags en `ExerciseNodeStatus` (`tags: list[TagDefinition]`).
  - Métodos en `StudyApplicationService` y `PlannerService`:
    - `get_tag_catalog() -> list[TagDefinition]`
    - `update_tag_definition(tag_id: str, name: str, color: str)`
    - `add_tag_definition(name: str, color: str) -> TagDefinition`
    - `delete_tag_definition(tag_id: str)`
    - `set_exercise_tags(section_type: str, section_number: int, exercise: int, inciso: int | None, tag_ids: list[str])`
    - `filter_overview_by_tag(overview: PlannerOverview, tag_id: str | None, only_tagged: bool)`
- **`presentation/planner_widget.py`**:
  - Ajustar tamaño base en `ExerciseCellButton` a 52×48 px.
  - Sobrescribir `paintEvent` en `ExerciseCellButton` para dibujar el triángulo/cinta de color (*ribbon*) en la esquina según las etiquetas del nodo.
  - Añadir en la barra superior un `QComboBox` o botones de filtro rápido de etiquetas.
- **`presentation/planner_dialogs.py`**:
  - Enriquecer `ExerciseDetailPopup` con panel interactivo de selección de etiquetas.
  - Diálogo modal `TagManagerDialog` para editar nombres y colores del catálogo.
- **`presentation/home_view.py`**:
  - Añadir botón de acción `tags_button` con ícono `fa5s.tags`.
  - Conectar con diálogo/menú emergente de selección de etiquetas del ejercicio activo.
- **`tests/`**:
  - Pruebas unitarias de serialización/deserialización retrocompatible en `test_planner_models.py`.
  - Pruebas de asignación, consulta y persistencia en `test_planner_service.py` y `test_application_service.py`.
  - Pruebas de filtrado por etiqueta.

##### Criterios de aceptación
- [ ] Los archivos JSON existentes cargan correctamente sin errores asignando etiquetas por defecto.
- [ ] El botón de marcadores en el cronómetro permite asignar/desasignar etiquetas al ejercicio en curso.
- [ ] En el planificador, las celdas de ejercicios muestran la cinta (*ribbon*) con el o los colores correspondientes.
- [ ] El tooltip y el popup de detalle muestran claramente el nombre y color de cada etiqueta.
- [ ] Es posible editar las etiquetas de un ejercicio directamente desde el planificador sin usar el cronómetro.
- [ ] Es posible renombrar, cambiar el color y agregar etiquetas al catálogo de la materia.
- [ ] El filtro de la barra superior permite aislar rápidamente ejercicios marcados o filtrar por una etiqueta específica.
- [ ] La suite completa de pruebas automatizadas pasa al 100% (`python -m unittest discover -s tests -v`).

---

### TASK-003
#### Sistema de notas y apuntes por ejercicio en la planificación (rediseño de comentarios)

- **Tipo:** 🔨 Enhancement  
- **Prioridad:** 🟡 Media  
- **Estado:** `[ ] Pendiente`  
- **Capas afectadas:** `domain/`, `application/`, `presentation/`, `infrastructure/`, `docs/`, `tests/`  
- **Dependencias:** `TASK-002` (sugerida)  

##### Descripción funcional
Reemplazar el esquema de comentarios fragmentados por intento (`TimerItem.comment`) por un sistema de **Notas y Apuntes de Ejercicio** integrado en la planificación (`PlannedSection.exercise_notes`). Cada ejercicio o inciso cuenta con un bloc de notas único, persistente y editable, visible tanto en el cronómetro como en el planificador. Los comentarios históricos en archivos existentes se preservan íntegramente en el historial de tiempos y se importan automáticamente a la planificación de forma no destructiva para no perder ninguna anotación previa.

##### Casos de uso y flujo de interacción
1. **Visualización y detección en el Planificador (`PlannerWidget`):**
   - Si un ejercicio tiene notas o apuntes cargados, su botón (`ExerciseCellButton`) muestra un mini glifo/ícono sutil (📝) en la esquina inferior derecha (opuesta a la cinta *ribbon* de etiquetas).
   - Al pasar el cursor por encima (tooltip), se previsualiza el apunte con un formato claro y legible.
2. **Edición y gestión desde el detalle del ejercicio (`ExerciseDetailPopup`):**
   - Reemplazar la caja rígida de 80 px de solo lectura por un **panel de notas moderno** con área multilínea estilizada (`QPlainTextEdit`).
   - Botón directo para guardar y actualizar la nota sin necesidad de correr un cronómetro ni salir de la vista.
3. **Integración contextual con el Cronómetro (`HomeViewWidget`):**
   - Al seleccionar un ejercicio o inciso en el cronómetro, el botón de notas detecta si el ejercicio ya contiene un apunte previo (cambiando su ícono o estado visual a activo).
   - Al presionarlo, se despliega el bloc de notas flotante donde el usuario puede consultar lo que había anotado antes (ej. advertencias, fórmulas o dudas) y complementarlo mientras resuelve.
4. **Migración automática y preservación histórica:**
   - Compatibilidad hacia atrás total: los archivos previos conservan intacta su lista `items[].comment`.
   - Al abrir un archivo sin `exercise_notes`, el servicio analiza el historial de intentos del ejercicio y precarga automáticamente el último comentario no vacío en la nota de la planificación.

##### Cambios técnicos proyectados por capa
- **`domain/models.py`**:
  - Añadir campo `exercise_notes: dict[str, str] = field(default_factory=dict)` en `PlannedSection` (mapea clave de ejercicio como `"2"` o `"2.3"` a su texto de nota).
  - Métodos auxiliares en `PlannedSection`: `get_note(exercise: int, inciso: int | None) -> str` y `set_note(exercise: int, inciso: int | None, note: str) -> None`.
  - Serialización retrocompatible en `to_dict` y `from_dict`.
- **`docs/CONTRATO_JSON.md`**:
  - Documentar `exercise_notes` dentro de la especificación de `PlannedSection`.
- **`application/planner_service.py` & `application/application_service.py`**:
  - Incorporar en `ExerciseNodeStatus` el campo `note: str` y `has_note: bool`.
  - Implementar lógica de migración inicial: si `exercise_notes` está vacío para un ejercicio pero existen comentarios en `items`, inicializar con el último comentario registrado.
  - Métodos `get_exercise_note(...)` y `set_exercise_note(...)` en `StudyApplicationService`.
- **`presentation/planner_widget.py`**:
  - Dibujar en `ExerciseCellButton.paintEvent` un mini glifo indicador de nota en la esquina inferior cuando `node.has_note` sea verdadero.
  - Formatear el tooltip para incluir la sección de notas con tipografía diferenciada.
- **`presentation/planner_dialogs.py`**:
  - Rediseñar el contenedor de notas en `ExerciseDetailPopup` con editor de texto interactivo y botón de confirmación/guardado.
- **`presentation/home_view.py`**:
  - Conectar el botón de notas para reflejar reactivamente la nota del ejercicio seleccionado en los combos de ubicación.
  - Abrir diálogo/panel de edición de notas que guarde directamente en `exercise_notes`.
- **`tests/`**:
  - Pruebas unitarias de serialización y lectura de `exercise_notes` en `test_planner_models.py`.
  - Pruebas de migración no destructiva de comentarios legados en `test_planner_service.py`.
  - Pruebas de actualización y sincronización de notas en `test_application_service.py`.

##### Criterios de aceptación
- [ ] Los comentarios existentes en registros previos no se borran ni modifican en `items`.
- [ ] Al abrir un archivo antiguo, las notas previas de los ejercicios se precargan automáticamente en el planificador.
- [ ] Los ejercicios con notas muestran un indicador gráfico sutil en su casilla del planificador.
- [ ] Es posible leer la nota completa en el tooltip y editarla directamente en el popup de detalle del ejercicio.
- [ ] El cronómetro muestra si el ejercicio activo ya tiene notas y permite editarlas o consultarlas en tiempo real.
- [ ] La suite de pruebas automatizadas pasa al 100% (`python -m unittest discover -s tests -v`).

---

### TASK-004
#### Pestaña de Ambientación: Mezclador de audio multicanal adaptativo al cronómetro

- **Tipo:** ✨ Feature  
- **Prioridad:** 🟡 Media  
- **Estado:** `[ ] Pendiente`  
- **Capas afectadas:** `presentation/`, `application/`, `infrastructure/`, `domain/`, `tests/`  
- **Dependencias:** Ninguna  

##### Descripción funcional
Incorporar una quinta pestaña a la aplicación denominada **"Ambientación"**, orientada a mejorar la inmersión y concentración durante las sesiones de estudio. La funcionalidad incluye un motor de audio multicanal capaz de combinar de forma simultánea múltiples pistas sonoras (ruido blanco, lluvia, cafetería, música lofi, etc.) almacenadas en una carpeta local dedicada (`data/ambient/`). La mezcla es totalmente adaptativa a los estados del cronómetro (Estudio, Descanso, Main/Espera), aplicando transiciones suaves con modulación de volumen (*fade in*, *fade out* e interpolación) sin cortes bruscos. La configuración y los presets de mezclas son globales para toda la aplicación (`data/ambient_presets.json`) e incorporan medidas de protección contra sobrecarga y archivos dañados.

##### Casos de uso y flujo de interacción
1. **Navegación y quinta pestaña (`AmbienceViewWidget`):**
   - Agregada como 5ta pestaña en la barra superior con ícono temático (`fa5s.headphones`).
   - Botón maestro **"📂 Abrir carpeta de audios"** para abrir el explorador de Windows en la ruta de pistas y arrastrar audios `.mp3`, `.wav`, `.ogg`, `.flac`.
   - Botón **"🔄 Actualizar pistas"** para escanear y refrescar la biblioteca al instante.
2. **Pestañas de Escena / Estado (Configuración independiente por situación):**
   - Selector en la parte superior del mezclador con 3 perfiles:
     - `[ 🟢 Estudio ]`: mezcla activa cuando el cronómetro está en tiempo neto (`PLAY`).
     - `[ 🟡 Descanso ]`: mezcla activa cuando el cronómetro está en receso (`BREAK`).
     - `[ ⚪ Main / Espera ]`: sonido ambiental de fondo o silencio cuando el cronómetro está en reposo o pausado (`IDLE` / `PAUSE`).
   - Cada pista dispone de un control de volumen individual (0% a 100%) para la escena seleccionada.
   - Botón **"Audicionar escena"** para preescuchar cómo suena la combinación del estado seleccionado mientras se ajusta.
3. **Transiciones suaves e interpolación de volumen (*Crossfade* inteligente):**
   - Slider de configuración de tiempo de transición/fade (ajustable de 0.5 a 5.0 segundos).
   - Al cambiar el estado del cronómetro (ej. de Estudio a Descanso):
     - Las pistas presentes en ambos estados (ej. Lluvia al 50% en Estudio y 20% en Descanso) modulan progresivamente su volumen sin detenerse ni reiniciarse.
     - Las pistas que entran realizan un *fade in* progresivo desde 0%.
     - Las pistas que salen realizan un *fade out* progresivo hasta 0% y se pausan.
4. **Gestión de Presets Globales:**
   - Barra de presets con selector desplegable (ej. *"Tormenta de Enfoque"*, *"Café Tranquilo"*, *"Silencio Zen"*).
   - Botones para *"Guardar mezcla actual como preset"*, *"Sobrescribir"* o *"Eliminar"*.
   - Los presets se almacenan en `data/ambient_presets.json` y están disponibles para cualquier materia o sesión.
5. **Protecciones de estabilidad y rendimiento:**
   - **Límite de seguridad:** Máximo de 8 pistas activas simultáneas por escena para prevenir saturación de audio o saturación de decodificadores.
   - **Reproducción bajo demanda:** Las pistas con volumen 0% se detienen por completo (`stop()`) consumiendo 0% de CPU y memoria.
   - **Control de errores defensivo:** Si un archivo está dañado o tiene un formato no soportado, se captura el error y se marca visualmente con advertencia (⚠️), evitando congelamientos o caídas de la aplicación.
   - **Limitador Master:** Control de volumen general que normaliza la salida para evitar saturación (*clipping* acústico).

##### Cambios técnicos proyectados por capa
- **`domain/models.py`**:
  - Modelos dataclass para ambientación:
    - `AmbienceTrackConfig(track_filename: str, volume: float)`
    - `AmbienceStateMix(study: dict[str, float], break_state: dict[str, float], main_state: dict[str, float])`
    - `AmbiencePreset(id: str, name: str, master_volume: float, fade_duration_sec: float, mixes: AmbienceStateMix)`
- **`infrastructure/ambient_storage.py`**:
  - Servicio de persistencia y lectura de presets y configuración global en `data/ambient_presets.json`.
  - Escaneo seguro de archivos compatibles en la carpeta de pistas (`.mp3`, `.wav`, `.ogg`, `.flac`, `.m4a`).
- **`infrastructure/audio_mixer_engine.py` (o extensión de `audio_service.py`):**
  - Motor multicanal basado en instancias de `QMediaPlayer` y `QAudioOutput` de `PySide6.QtMultimedia`.
  - Sistema de interpolación no bloqueante de volumen mediante `QTimer` o `QVariantAnimation` para ejecutar el *fade*.
  - Suscripción y escucha de cambios de estado del cronómetro (`TimerService`).
- **`application/application_service.py`**:
  - Integración del servicio de ambientación con el ciclo de vida del cronómetro (`on_timer_state_changed`).
  - Métodos para guardar/cargar presets y aplicar perfiles de volumen activos.
- **`presentation/ambience_view.py`**:
  - Creación del widget completo `AmbienceViewWidget`:
    - Cabecera con Master Volume, selector de Fade Time, selector y botones de Presets, y botones de carpeta.
    - Barra de selección de escena (`Estudio` / `Descanso` / `Main`).
    - Grid/Lista con scroll de tarjetas de pistas con nombre, barra de volumen individual, botón mute y badge de estado.
- **`presentation/main_window.py`**:
  - Añadir la quinta pestaña a `self.tabs` con su ícono correspondiente.
  - Conectar el cambio de estado del cronómetro con el motor de ambientación.
- **`tests/`**:
  - Pruebas de persistencia y serialización de presets de ambientación.
  - Pruebas de cálculo e interpolación de volumen ante cambios de estado.
  - Pruebas del límite de seguridad de pistas simultáneas.

##### Criterios de aceptación
- [ ] La pestaña "Ambientación" se muestra en la posición 5 de la ventana principal y se abre correctamente.
- [ ] El botón "Abrir carpeta de audios" abre la carpeta local del sistema y "Actualizar pistas" detecta nuevos audios.
- [ ] Es posible configurar volúmenes independientes para cada uno de los 3 estados (Estudio, Descanso, Main).
- [ ] Al iniciar, pausar o pasar a receso en el cronómetro, el audio transiciona suavemente sin cortes abruptos.
- [ ] Las pistas compartidas entre estados ajustan su volumen mediante interpolación sin reiniciarse.
- [ ] Es posible guardar mezclas completas como presets y volver a cargarlas en cualquier momento.
- [ ] La aplicación no supera el límite seguro de pistas activas y maneja archivos corruptos sin cerrarse ni bloquear la UI.
- [ ] La suite de pruebas automatizadas pasa al 100% (`python -m unittest discover -s tests -v`).

---

### TASK-005
#### Gestión de estado sin proyecto activo y prevención de operaciones erráticas al cerrar archivos

- **Tipo:** 🐛 Bugfix  
- **Prioridad:** 🔴 Alta  
- **Estado:** `[ ] Pendiente`  
- **Capas afectadas:** `presentation/`, `application/`, `infrastructure/`, `tests/`  
- **Dependencias:** Ninguna  

##### Descripción funcional
Resolver las inconsistencias de estado y excepciones no controladas (`ValueError: No hay un archivo activo`) provocadas al cerrar el registro actual o intentar operar la aplicación sin un proyecto cargado. Al cerrar un archivo, se desplegará de forma inmediata el diálogo de bienvenida (`WelcomeDialog`) para facilitar la selección o creación de otro proyecto. Si el usuario cancela dicho diálogo, la aplicación pasará a un estado vacío controlado (*Empty State*): se deshabilitarán las acciones operativas dependientes de archivo en la barra de herramientas y vistas, y se mostrará un panel central claro que invite a abrir o crear un proyecto, eliminando cualquier comportamiento impredecible o fallo en tiempo de ejecución.

##### Casos de uso y flujo de interacción
1. **Cierre de archivo con reenganche inmediato:**
   - Al pulsar *"Cerrar archivo"* (`close_record`), tras la confirmación habitual, el sistema desvincula el archivo y abre automáticamente el diálogo de bienvenida (`WelcomeDialog`) con la lista de recientes, opción de nuevo registro y abrir archivo.
2. **Pantalla de Estado Vacío (*Empty State*) al cancelar o arrancar sin proyecto:**
   - Si se cancela el diálogo de bienvenida (o si no se carga ningún archivo), la ventana principal entra en modo *"Sin Proyecto Activo"*:
     - La barra de título muestra: `Study Timetrial — [Sin proyecto activo]`.
     - En las vistas principales se despliega un panel de estado vacío con mensaje amigable: *"Ningún proyecto abierto"* y dos botones prominentes: `[➕ Crear nuevo registro]` y `[📂 Abrir registro]`.
3. **Protección y deshabilitación de controles dependientes:**
   - En la barra de herramientas y menús: *"Cerrar archivo"*, *"Guardar como"* y *"Renombrar"* se deshabilitan (`setEnabled(False)`).
   - En el Cronómetro: los botones `INICIAR`, `COMENTARIO`, `MARCADORES` y selectores de ubicación se bloquean. Si de algún modo se dispara un intento de registro, se solicita primero crear o abrir un archivo en lugar de arrojar excepciones no controladas.
   - En el Planificador y Registros: se bloquean las acciones de mutación ("Nueva sección", "Sincronizar", edición/borrado de items).
4. **Restauración al abrir o crear un proyecto:**
   - En cuanto el usuario abre o crea un registro válido, el estado vacío se oculta de forma fluida y todas las herramientas y vistas vuelven a activarse al 100%.

##### Cambios técnicos proyectados por capa
- **`application/application_service.py`**:
  - Asegurar que `close_record()` resetee el estado de forma atómica y notifique el cambio a la interfaz.
  - Blindar métodos de guardado y mutación: verificar `is_record_open` antes de delegar a `storage.save()`.
- **`presentation/main_window.py`**:
  - Incorporar método `set_empty_project_state(is_empty: bool)` que centralice la habilitación/deshabilitación de acciones en toolbar, menús y vistas.
  - Actualizar `close_record()` para invocar `prompt_initial_record_choice(force=True)` y llamar a `set_empty_project_state(True)` si no se seleccionó ningún archivo.
  - Actualizar `update_title()` para reflejar `[Sin proyecto activo]`.
  - Proteger `finish_item()` y atajos de teclado ante la ausencia de archivo activo.
- **`presentation/empty_state_widget.py` (o componente visual integrado):**
  - Crear un widget reutilizable con iconografía, tipografía clara y botones de acción rápida conectados a `new_record()` y `open_record()`.
- **`presentation/home_view.py` / `presentation/planner_widget.py` / `presentation/records_view.py`**:
  - Implementar soporte para alternar entre vista normal y estado vacío cuando no hay archivo abierto.
- **`tests/`**:
  - Pruebas unitarias comprobando que `close_record()` no deja la aplicación en un estado que provoque `ValueError`.
  - Pruebas simulando intentos de inicio/guardado sin archivo abierto garantizando que no se producen fallos no controlados.

##### Criterios de aceptación
- [ ] Al cerrar un archivo, se despliega automáticamente el diálogo de bienvenida con las opciones de selección.
- [ ] Si se cancela el diálogo de bienvenida, la aplicación pasa a un estado vacío protegido sin errores en consola ni cierres inesperados.
- [ ] La barra de título indica explícitamente `[Sin proyecto activo]`.
- [ ] Las opciones de menú y herramientas que requieren un archivo quedan deshabilitadas visual y funcionalmente.
- [ ] Ninguna interacción puede disparar `ValueError: No hay un archivo activo`.
- [ ] Es posible crear o abrir un registro directamente desde los botones del estado vacío y reanudar el uso normal.
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
