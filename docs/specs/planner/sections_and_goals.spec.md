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
