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

---

## 7. Ejercicios con Incisos Colapsables y Control de Expansión

1. **Botón General de Contracción / Expansión Global:**
   * Ubicado en la barra superior de acciones (`PlannerWidget`).
   * Permite alternar en bloque el estado de todos los grupos compuestos (`CompositeExerciseGroup`) entre contraídos y expandidos.
   * Dispone de texto e íconos dinámicos (`fa5s.compress-arrows-alt` / `fa5s.expand-arrows-alt`).

2. **Botón Cabecera de Grupo (`[ n ]`):**
   * Se ubica al inicio de cada grupo de incisos y exhibe el número base del ejercicio (ej. `1`).
   * Mantiene idéntica apariencia geométrica y cromática que sus celdas compañeras (`52x48px`, esquinas `6px`, bordes y tipografía acorde a estado y tema).
   * **Interacción no modal:** Al hacer clic, conmuta el estado de expansión del grupo (no abre el diálogo modal de detalle).
   * **Estado Expandido:** Muestra el botón cabecera seguido de sus incisos individuales: `[ n ] [ n.1 ] [ n.2 ] ...`.
   * **Estado Contraído (Comprimido):** Oculta los sub-botones de incisos y únicamente presenta el botón cabecera `[ n ]`.

3. **Jerarquía Estricta de Color (`Gris > Rojo > Verde`):**
   * El color del botón padre `[ n ]` refleja la prioridad absoluta del avance de sus incisos:
     1. **Gris (`STATUS_PENDING`):** Si **al menos uno** de los incisos se encuentra pendiente / no realizado.
     2. **Rojo (`STATUS_FAILED`):** Si **ningún inciso** está pendiente, pero **al menos uno** se encuentra en dificultad / fallado.
     3. **Verde (`STATUS_COMPLETED`):** Únicamente si **todos los incisos** se encuentran aprobados / completados.

4. **Consolidación de Íconos en Modo Comprimido:**
   * Al estar contraído, el botón `[ n ]` dibuja en su superficie los íconos acumulados de sus incisos:
     * **Marcadores (Bookmarks):** Muestra las etiquetas asignadas a cualquiera de sus incisos, deduplicadas por ID.
     * **Notas (Sticky-note):** Dibuja el indicador de notas si al menos uno de sus incisos contiene apuntes.
   * Al expandirse, cada inciso exhibe de forma individual sus propias etiquetas y notas, mientras que el botón cabecera conserva su rol de conmutador visual.

---

## 8. Visualización Multi-Columna Adaptativa (Responsive Grid / Masonry)

1. **Contrato de Ancho Dinámico y Adaptabilidad:**
   * La vista general de tarjetas de secciones en `PlannerWidget` adopta una disposición multi-columna adaptativa gobernada por el cálculo de columnas óptimas en función del ancho del viewport:
     $$N = \max\left(1, \min\left(8, \left\lfloor \frac{W_{\text{viewport}} + 14}{460 + 14} \right\rfloor\right)\right)$$
   * Rango ergonómico por tarjeta: $380\text{px}$ a $600\text{px}$, con ancho preferente de $\approx 460-500\text{px}$.
   * Escalabilidad según resolución de pantalla:
     * **Ventanas compactas (< 850px):** 1 columna (100% ancho).
     * **Laptops estándar (1024 - 1366px):** 2 columnas (~480 - 620px c/u).
     * **Escritorio Full HD (1920px):** 3 a 4 columnas (~440 - 580px c/u).
     * **Monitores 2K / QHD (2560px):** 4 a 5 columnas (~480 - 600px c/u).
     * **UltraWide 21:9 (3440px) y 4K UHD (3840px):** 6 a 7 columnas en paralelo, visualizando hasta 14 secciones completas sin desplazamiento vertical.

2. **Lectura Secuencial en "Z" y Columnas Verticalmente Independientes:**
   * Cada columna está implementada mediante un `QVBoxLayout` independiente con alineación superior (`AlignTop`) y espaciador elástico final (`addStretch()`).
   * Las tarjetas se distribuyen por índice en round-robin: tarjeta $i$ en columna $i \pmod N$.
   * La altura de cada tarjeta ("a lo largo") es estrictamente dinámica según las filas requeridas por su `FlowLayout`. No existen ataduras rígidas de altura entre tarjetas de columnas adyacentes (cero espacios vacíos verticales).

---

## 9. Contracción y Expansión de Secciones (Local y Global)

1. **Contracción / Expansión Individual (`PlannedSectionCard`):**
   * Cada tarjeta dispone de un botón conmutador chevron `[ ▼ / ▶ ]` (`btn_collapse_section`).
   * Al contraerse (`is_collapsed = True`), se oculta la cuadrícula interactiva de ejercicios (`exercises_container`) y el separador divisorio, colapsando la tarjeta a la altura compacta de su cabecera (~46px).
   * La barra de progreso unificada (`SegmentedProgressBar`), el porcentaje y los botones de acción (`Editar` y `Eliminar`) permanecen visibles como resumen ejecutivo.
   * La conmutación propaga inmediatamente la invalidación geométrica (`updateGeometry()`), permitiendo que las tarjetas inferiores en esa misma columna asciendan en tiempo real.

2. **Control Global de Secciones (`btn_toggle_sections`):**
   * Ubicado en la barra superior de acciones (`PlannerWidget`) junto al botón de incisos.
   * Permite alternar en bloque el estado de colapso de todas las secciones planificadas (`"Contraer secciones"` / `"Expandir secciones"`).

3. **Sinergia con la Contracción de Incisos:**
   * La contracción de grupos de ejercicios con incisos (`[ n ]`) reduce el ancho de celda y libera espacio en el `FlowLayout`, reduciendo el número de filas de la sección y disminuyendo su altura dinámica en tiempo real.



