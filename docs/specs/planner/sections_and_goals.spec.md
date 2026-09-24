# Especificación Técnica: Secciones Planificadas, Metas y Límites de Navegación

**Identificador:** `PLAN-SPEC-001`  
**Capa de Referencia:** `domain/models.py` / `application/planner_service.py`  
**Estado:** Invariante / Producción  

---

## 1. Propósito
Definir la estructura de una sección académica de estudio (`PlannedSection`), su configuración de ejercicios e incisos, y el mecanismo de verificación de límites de navegación para evitar intentos fuera de rango.

---

## 2. Modelo de Sección Planificada (`PlannedSection`)

* `section_type: str`: Categoría temática (ej. `"Guía"`, `"Práctica"`).
* `section_number: int`: Número de la sección ($\ge 1$).
* `title: str`: Título descriptivo (ej. `"Álgebra Lineal - Matrices"`).
* `total_exercises: int`: Total de ejercicios declarados en la sección.
* `exercise_configs: dict[str, int]`: Mapeo `"<ejercicio>": <cantidad_incisos>`. Si un ejercicio no figura en el diccionario o su valor es `0`, carece de incisos.
* `exercise_tags: dict[str, list[str]]`: Mapeo de ejercicio o ejercicio.inciso (`"1"` o `"1.1"`) a lista de IDs de etiquetas.
* `exercise_notes: dict[str, str]`: Apuntes de estudio en Markdown asociados a cada nodo.

---

## 3. Sincronización Automática con Registros (`sync_planner_with_records`)

1. Si un usuario registra un intento para un ejercicio que excede `total_exercises` o con incisos superiores a los configurados, **el sistema no bloquea el registro**.
2. Al recalcular el planificador:
   * Si la sección no existía en `record.planner_sections`, se autogenera una sección con los ejercicios observados.
   * Si el ejercicio observado excede `total_exercises`, se expande `total_exercises = max_exercise_observado`.
   * Si se observan incisos para un ejercicio configurado con 0, se actualiza `exercise_configs[str(ej)] = max_inciso_observado`.

---

## 4. Control de Límites de Navegación (`check_navigation_boundary`)

Cuando el usuario navega desde el cronómetro (botones o atajos):
* Si `exercise > total_exercises`: Se emite un aviso de límite de sección excedido (`BoundaryExceeded`).
* Si `inciso > exercise_configs.get(str(exercise), 0)`: Se emite aviso de inciso fuera de rango.
* La acción permite al usuario decidir si desea expandir la sección o cancelar la navegación.

---

## 5. Visualización de Marcadores (Bookmarks) en la Pestaña Cronómetro

1. **Ubicación e Integración Visual:**
   * En la pestaña del Cronómetro (`HomeViewWidget`), el recuadro principal de ubicación (`"Guía N · Ejercicio M..."`) refleja de manera inmediata los marcadores asignados (`exercise_tags`).
   * El texto descriptivo del ejercicio se presenta centrado horizontal y verticalmente dentro del recuadro.
   * Cada marcador se dibuja como un ícono de bookmark (`fa5s.bookmark`) colgando en la parte superior derecha (`y=2px`), idéntico al comportamiento visual de las celdas del planificador, con el color asignado en el catálogo (`tag.color`) y contorno para asegurar alto contraste visual sobre temas claros y oscuros.
2. **Contrato de Dimensionamiento Fijo:**
   * El recuadro posee un tamaño fijo estándar (`340px` de ancho $\times$ `50px` de alto).
   * En caso de que los bookmarks asignados o la extensión del texto del ejercicio superen el espacio disponible, el recuadro se agranda a un tamaño fijo superior (`440px` o `520px`), garantizando estabilidad visual fija sin fluctuaciones por caracteres individuales y asegurando que el texto centrado no solape con las cintas de marcador.
3. **Información Contextual y Accesibilidad:**
   * El `toolTip` del recuadro incorpora la lista legible de los nombres de los marcadores asignados (`Marcadores: <Nombre 1>, <Nombre 2>...`).
   * La interacción mediante clic en el recuadro abre el cuadro modal de detalle para edición de marcadores y apuntes.

---

## 6. Gestión del Catálogo de Marcadores (`TagManagerDialog`)

1. **Persistencia Inmediata en Edición en Celda (`itemChanged`):**
   * La tabla del catálogo de marcadores permite editar el nombre de cualquier etiqueta escribiendo directamente en la celda o mediante doble clic.
   * El evento `itemChanged` detecta el cambio de texto, valida que no esté vacío y sincroniza de forma inmediata la actualización en `application_service.update_tag_definition(tag_id, new_name, color)` y en disco.
   * Si el usuario deja la celda en blanco, el sistema revierte automáticamente al nombre original para evitar etiquetas anónimas.
2. **Modal y Acciones de Edición:**
   * El botón de edición en la columna de acciones permite renombrar mediante un único clic abriendo el diálogo de texto `QInputDialog`.
   * El doble clic sobre la columna de color abre directamente el selector de color `QColorDialog`.
   * Los cambios en nombres y colores se reflejan en tiempo real en los filtros del planificador, la lista de selección de marcadores y el recuadro del cronómetro.


