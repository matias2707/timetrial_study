# Contrato de persistencia JSON

**Fecha de revisión:** 2026-09-07  
**Estado:** contrato vigente, esquema `1`

## Archivo de registro

Un registro es un objeto JSON con esta forma:

```json
{
  "schema_version": 1,
  "application": "Study Timetrial",
  "record_name": "Algebra_Demo",
  "created_at": "2026-09-02T16:36:28",
  "updated_at": "2026-09-05T16:25:20",
  "items": []
}
```

### Campos de `Record`

| Campo | Tipo | Regla |
|---|---|---|
| `schema_version` | entero | Debe ser `1`. |
| `application` | texto | Identifica la aplicación. Los archivos emitidos usan `Study Timetrial`; el cargador actual no usa este campo para reconstruir el modelo. |
| `record_name` | texto | Nombre lógico, normalmente el nombre del archivo sin `.json`. |
| `created_at` | texto | Fecha ISO creada al construir el registro. |
| `updated_at` | texto | Fecha ISO actualizada al serializar. |
| `items` | lista | Contiene cero o más `TimerItem`. |

### Campos de `TimerItem`

| Campo | Tipo | Regla |
|---|---|---|
| `id` | texto | UUID. Si falta o es nulo al importar, se genera uno nuevo. |
| `section_type` | texto | Tipo de sección. Es obligatorio. |
| `section_number` | entero | Número de sección desde `1`. Es obligatorio. |
| `exercise` | entero | Número de ejercicio desde `1`. Es obligatorio. |
| `inciso` | entero o `null` | `null` significa sin inciso; `0` legado también se normaliza a `null`. |
| `exercise_time_ms` | entero | Tiempo de ejercicio en milisegundos. Es obligatorio. |
| `break_time_ms` | entero | Receso acumulado en milisegundos. Es obligatorio. |
| `completed` | booleano | Indica si el intento se considera completado. Es obligatorio. |
| `comment` | texto | Comentario opcional; si falta, se carga como texto vacío. |
| `created_at` | texto | Fecha ISO del item; si falta, se genera al cargar. |

Los campos obligatorios ausentes hacen fallar la carga con `ValueError`. Un
archivo con otra versión de esquema o sin una lista `items` no es compatible.

## Archivos auxiliares

`.study_timetrial_recent.json` contiene una lista JSON de rutas a archivos
recientes. Se conservan como máximo diez rutas existentes. Este archivo es un
índice local auxiliar y no forma parte del registro académico.

## Reglas de evolución

1. No renombrar ni eliminar campos de `schema_version: 1` sin una migración.
2. Los nuevos campos deben tener un valor por defecto al cargar archivos
   existentes.
3. Un cambio incompatible debe aumentar `schema_version` y añadir pruebas de
   lectura del esquema anterior.
4. No editar archivos de usuario manualmente como solución a un defecto de
   código.

La implementación de lectura y escritura está centralizada en
`infrastructure/storage_service.py`; los modelos definen la serialización
mediante `to_dict` y `from_dict`.
