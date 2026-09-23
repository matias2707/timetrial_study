# Especificación Técnica: Contratos de Persistencia y Esquemas de Datos

**Identificador:** `DATA-SPEC-001`  
**Capa de Referencia:** `domain/models.py` / `infrastructure/storage_service.py`  
**Estado:** Invariante / Esquema Versión 1  

---

## 1. Propósito
Definir la estructura de datos canónica, contratos de serialización/deserialización y garantías de compatibilidad hacia atrás para el almacenamiento de registros de estudio (`Record`), intentos individuales (`TimerItem`), secciones del planificador (`PlannedSection`) e hitos académicos (`PlannerSchedule`).

---

## 2. Esquema JSON Canónico (Versión 1)

```json
{
  "schema_version": 1,
  "application": "Study Timetrial",
  "record_name": "string",
  "created_at": "YYYY-MM-DDTHH:MM:SS",
  "updated_at": "YYYY-MM-DDTHH:MM:SS",
  "items": [
    {
      "id": "uuid-v4-string",
      "section_type": "string",
      "section_number": 1,
      "exercise": 1,
      "inciso": 1,
      "exercise_time_ms": 142000,
      "break_time_ms": 15000,
      "completed": true,
      "comment": "string",
      "created_at": "YYYY-MM-DDTHH:MM:SS"
    }
  ],
  "planner_sections": [
    {
      "section_type": "string",
      "section_number": 1,
      "title": "string",
      "total_exercises": 10,
      "exercise_configs": { "1": 3, "4": 2 },
      "exercise_tags": { "1.1": ["tag-redo"] },
      "exercise_notes": { "1": "Notas en Markdown..." }
    }
  ],
  "tags": [
    {
      "id": "tag-redo",
      "name": "Rehacer",
      "color": "#ef4444"
    }
  ],
  "planner_schedule": {
    "period_type": "Cuatrimestral",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "milestones": [
      {
        "name": "Primer Parcial",
        "date": "YYYY-MM-DD",
        "type": "parcial",
        "color": "#ef4444",
        "icon": "🎯"
      }
    ]
  }
}
```

---

## 3. Invariantes de Dominio y Normalización

1. **Identificadores UUID:** Cada `TimerItem` debe tener un `id` único. Si al deserializar no existe o es nulo, se genera uno nuevo (`uuid.uuid4()`).
2. **Normalización de Inciso:**
   * `inciso = None` representa explícitamente "Sin inciso".
   * El valor numérico legado `0` se normaliza automáticamente a `None`.
3. **Tiempos no negativos:** `exercise_time_ms >= 0` y `break_time_ms >= 0`.
4. **Tolerancia a campos ausentes:** Si un archivo JSON antiguo no contiene `planner_sections`, `tags` o `planner_schedule`, el parser los inicializa con listas o valores vacíos por defecto sin lanzar excepción.
5. **Persistencia Atómica:** La escritura en disco debe realizarse primero en un archivo temporal o con volcado limpio para evitar corrupciones ante cierres forzados.

---

## 4. Pipeline Transitorio de Migraciones (Fase Alfa)

Durante el ciclo de desarrollo alfa del proyecto, se dispone del módulo `infrastructure/compatibility/migrations.py`:

* **Objetivo:** Proporcionar actualización progresiva de estructuras JSON locales que hayan cambiado entre iteraciones alfa.
* **Naturaleza Transitoria:** Este subsistema está confinado en `infrastructure/compatibility/` y será completamente retirado antes de la versión 1.0 estable sin alterar los modelos puros de dominio.
* **Flujo de Migración:**
  1. Si un archivo JSON no posee `schema_version` (formato v0), `upgrade_v0_to_v1()` normaliza la raíz y los campos mínimos de sesión.
  2. Si se detecta desactualización, se genera una copia de seguridad automática (`.bak`) antes de sobrescribir el archivo.
  3. `StorageService.read()` aplica la conversión en memoria de forma transparente para evitar rupturas de carga.
