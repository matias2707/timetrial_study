# Especificación Técnica: Métricas de Progreso y Estados de Ejercicios

**Identificador:** `PLAN-SPEC-002`  
**Capa de Referencia:** `application/planner_service.py` / `application/statistics_service.py`  
**Estado:** Invariante / Producción  

---

## 1. Propósito
Definir las fórmulas de agregación, cálculo de estados atómicos (`completed`, `failed`, `pending`), ponderación fraccionaria por incisos y analítica global de la materia.

---

## 2. Estados de un Nodo de Ejercicio (`ExerciseNodeStatus`)

Para cada ejercicio (o inciso individual):
* **`completed`:** Existe al menos un intento con `completed == True`.
* **`failed`:** Existen únicamente intentos con `completed == False` (ningún éxito registrado aún).
* **`pending`:** No registra ningún intento en el historial.

### Ejercicios Compuestos (con Incisos):
Si un ejercicio posee $N$ incisos ($N \ge 1$):
* El ejercicio padre es `completed` únicamente si **todos** sus incisos están completados.
* El ejercicio padre es `failed` si al menos un inciso está fallado y ninguno está completado, o si se intentaron incisos pero no se completaron todos.
* **Ponderación Fraccionaria (`completed_weight`):**
  $$\text{completed\_weight} = \sum_{k=1}^N \frac{\text{inciso}_k.\text{is\_completed}}{N}$$

---

## 3. Métricas de Sección Planificada (`PlannedSectionStatus`)

* **Unidades Totales (`total_units`):** Suma de ejercicios simples + suma de todos los incisos de ejercicios compuestos.
* **Unidades Completadas (`completed_units`):** Cantidad de hojas (ejercicios simples o incisos) completadas con éxito.
* **Porcentaje de Completitud:**
  $$\% \text{ Avance} = \frac{\text{completed\_weight}}{\text{total\_exercises}} \times 100$$
* **Tiempos Netos:**
  * $\text{total\_exercise\_time\_ms} = \sum \text{exercise\_time\_ms de todos los intentos}$
  * $\text{total\_break\_time\_ms} = \sum \text{break\_time\_ms de todos los intentos}$

---

## 4. Métricas Diarias y Cronológicas (`compute_today_summary_metrics`)

* Filtra registros cuya fecha ISO coincida con la fecha local de hoy (`YYYY-MM-DD`).
* Calcula:
  1. Tiempo total de estudio invertido hoy.
  2. Tiempo total de descanso tomado hoy.
  3. Total de ejercicios/intentos completados vs fallados hoy.
  4. Distribución horaria (cubetas de 24 horas para renderizar en gráficos de barras o histogramas).
