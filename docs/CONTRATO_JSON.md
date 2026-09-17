# Contrato de persistencia JSON

**Fecha de revisión:** 2026-09-11  
**Estado:** contrato vigente, esquema `1`

## Archivo de registro

Un registro es un objeto JSON autosuficiente que contiene tanto el historial de intentos registrados como la configuración del planificador de estudio:

```json
{
  "schema_version": 1,
  "application": "Study Timetrial",
  "record_name": "Algebra_Demo",
  "created_at": "2026-09-02T16:36:28",
  "updated_at": "2026-09-11T16:25:20",
  "items": [
    {
      "id": "c1f7b889-138d-4f36-a36c-949d282f6e91",
      "section_type": "Guía",
      "section_number": 1,
      "exercise": 1,
      "inciso": 1,
      "exercise_time_ms": 142000,
      "break_time_ms": 15000,
      "completed": true,
      "comment": "Completado sin dificultad",
      "created_at": "2026-09-02T16:38:50"
    }
  ],
  "planner_sections": [
    {
      "section_type": "Guía",
      "section_number": 1,
      "title": "Álgebra Lineal - Vectores",
      "total_exercises": 10,
      "exercise_configs": {
        "1": 3,
        "4": 2
      },
      "exercise_tags": {
        "1.1": ["tag-redo"],
        "4": ["tag-doubt", "tag-key"]
      }
    }
  ],
  "tags": [
    {
      "id": "tag-redo",
      "name": "Rehacer",
      "color": "#ef4444"
    },
    {
      "id": "tag-doubt",
      "name": "Duda para clase",
      "color": "#f59e0b"
    },
    {
      "id": "tag-consulted",
      "name": "Consulté respuesta",
      "color": "#3b82f6"
    },
    {
      "id": "tag-key",
      "name": "Clave / Importante",
      "color": "#a855f7"
    }
  ]
}
```

### Campos de `Record`

| Campo | Tipo | Regla |
|---|---|---|
| `schema_version` | entero | Debe ser `1`. |
| `application` | texto | Identifica la aplicación. Los archivos emitidos usan `Study Timetrial`. |
| `record_name` | texto | Nombre lógico, normalmente el nombre del archivo sin extensión `.json`. |
| `created_at` | texto | Fecha y hora en formato ISO 8601 generada al instanciar el registro. |
| `updated_at` | texto | Fecha y hora en formato ISO 8601 actualizada cada vez que se serializa. |
| `items` | lista | Contiene cero o más objetos `TimerItem`. Es obligatorio. |
| `planner_sections` | lista | Contiene cero o más objetos `PlannedSection`. Si falta (archivos legados), se inicializa como lista vacía `[]`. |
| `tags` | lista | Contiene la lista de objetos `TagDefinition` que definen el catálogo de marcadores para la materia. Si falta en el archivo, se inicializa con el catálogo por defecto. |

### Campos de `TimerItem`

| Campo | Tipo | Regla |
|---|---|---|
| `id` | texto | Identificador único UUIDv4. Si falta o es nulo al cargar/importar, se genera uno nuevo. |
| `section_type` | texto | Tipo de sección (ej. `"Guía"`, `"Práctica"`). Es obligatorio. |
| `section_number` | entero | Número de sección desde `1`. Es obligatorio. |
| `exercise` | entero | Número de ejercicio desde `1`. Es obligatorio. |
| `inciso` | entero o `null` | `null` indica ejercicio sin inciso. El valor numérico `0` (legado) se normaliza a `null`. |
| `exercise_time_ms` | entero | Tiempo neto dedicado al ejercicio en milisegundos no negativos. Es obligatorio. |
| `break_time_ms` | entero | Tiempo total de receso acumulado en milisegundos no negativos. Es obligatorio. |
| `completed` | booleano | Indica si el intento concluyó exitosamente (`true`) o de forma incompleta (`false`). Es obligatorio. |
| `comment` | texto | Comentario opcional. Si falta o es nulo, se carga como texto vacío `""`. |
| `created_at` | texto | Fecha y hora ISO 8601 del intento. Si falta, se genera automáticamente al cargar. |

### Campos de `PlannedSection`

| Campo | Tipo | Regla |
|---|---|---|
| `section_type` | texto | Tipo de sección (ej. `"Guía"`). Si falta, toma `"Guía"` por defecto. |
| `section_number` | entero | Número de sección desde `1`. Si falta, toma `1` por defecto. |
| `title` | texto | Título o descripción opcional de la sección (ej. `"Vectores y Matrices"`). |
| `total_exercises` | entero | Cantidad total de ejercicios planificados en la sección (mínimo `1`). |
| `exercise_configs` | objeto | Diccionario clave-valor serializado con claves de texto `"<ejercicio>": <cantidad_incisos>`. Mapea cada ejercicio con su número de incisos correspondientes (0 si no tiene). |
| `exercise_tags` | objeto | Diccionario clave-valor serializado `"<ejercicio>"` o `"<ejercicio>.<inciso>"` mapeado a una lista de identificadores de etiquetas asociadas (ej: `{"1.1": ["tag-redo"]}`). Si falta, se inicializa como `{}`. |

### Campos de `TagDefinition`

| Campo | Tipo | Regla |
|---|---|---|
| `id` | texto | Identificador único de la etiqueta (ej. `"tag-redo"` o UUID corto). |
| `name` | texto | Nombre o texto descriptivo de la etiqueta (ej. `"Rehacer"`, `"Duda para clase"`). |
| `color` | texto | Código hexadecimal de color para renderizar el marcador (ej. `"#ef4444"`). |

## Archivos auxiliares

`.study_timetrial_recent.json` (ubicado preferentemente en `data/.study_timetrial_recent.json` o en la raíz por retrocompatibilidad) contiene una lista JSON con las rutas absolutas a los archivos de registro abiertos recientemente. Se conservan como máximo 10 rutas existentes válidas. Este archivo es un índice local de sesión y no forma parte del registro académico.

## Reglas de evolución y compatibilidad hacia atrás

1. **Invarianza del esquema:** No renombrar ni eliminar campos de `schema_version: 1` sin una migración explícita.
2. **Tolerancia a campos opcionales:** Si un archivo previo no incluye `planner_sections`, `exercise_tags` o `tags`, el método `Record.from_dict` y `PlannedSection.from_dict` los inicializan de forma segura con valores predeterminados sin generar excepciones.
3. **Normalización de incisos:** Los valores legados donde `inciso == 0` o campos ausentes se mapean automáticamente a `None`.
4. **Sincronización no destructiva:** Si un registro contiene intentos de ejercicios que exceden o no están presentes en `planner_sections`, el servicio de aplicación los respeta y los incorpora a la vista del planificador mediante `sync_planner_with_records()`.
5. **Serialización centralizada:** La implementación de lectura, escritura y parseo reside en `domain/models.py` (`to_dict` / `from_dict`) y es coordinada por `infrastructure/storage_service.py`.
