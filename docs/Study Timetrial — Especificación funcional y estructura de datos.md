# Especificación funcional de Study Timetrial

**Fecha de revisión:** 2026-09-07  
**Estado:** vigente para la implementación actual

## 1. Propósito y alcance

Study Timetrial es una aplicación de escritorio local para medir sesiones de
estudio por ejercicio y guardar intentos en archivos JSON. No requiere servidor
ni base de datos. Un archivo de registro puede contener múltiples intentos y
solo hay un archivo activo en la sesión de la aplicación.

La interfaz principal tiene dos vistas:

- **Cronómetro:** selección de ubicación, reloj, controles de sesión y navegación.
- **Registros:** consulta y mantenimiento de los intentos guardados.

## 2. Modelo de ubicación

Cada intento se identifica visualmente por:

```text
Tipo de sección + número de sección + ejercicio + inciso opcional
```

Los valores iniciales son `Guía`, sección `1`, ejercicio `1` y sin inciso.

- El tipo de sección es texto libre; por defecto es `Guía`.
- El número de sección y el ejercicio son enteros desde `1`.
- El inciso es `null` cuando no existe. En la interfaz, el valor `0` representa
  "Sin inciso" y nunca se persiste como `0`.
- La aplicación no necesita conocer de antemano qué secciones, ejercicios o
  incisos existen.

## 3. Estados del cronómetro

El servicio de dominio usa exactamente estos estados:

| Estado | Significado |
|---|---|
| `WAITING` | No hay sesión activa. La ubicación se puede editar. |
| `PLAY` | El tiempo de ejercicio está avanzando. |
| `BREAK` | El tiempo de receso está avanzando y el de ejercicio está pausado. |

Los tiempos se miden con un reloj monotónico y se acumulan en milisegundos.
El receso no se guarda como períodos individuales, sino como un único total por
intento.

## 4. Acciones de sesión

| Acción visible | Resultado |
|---|---|
| `INICIAR` | Pasa de `WAITING` a `PLAY`. |
| `RECESO` | Pasa de `PLAY` a `BREAK`. |
| `CONTINUAR` | Pasa de `BREAK` a `PLAY`. |
| `DETENER` | Descarta la sesión actual, borra ambos contadores y vuelve a `WAITING`. |
| `INCOMPLETO` | Guarda el intento con `completed = false` y reinicia el cronómetro. |
| `COMPLETO` | Guarda el intento con `completed = true` y reinicia el cronómetro. |
| `REINICIAR` en registros | Pone en cero los tiempos de un intento ya guardado. |

La ubicación queda bloqueada mientras el estado no sea `WAITING`. Al finalizar
un intento se desbloquea y se conserva la ubicación actual, salvo que una
navegación la cambie.

## 5. Navegación

Las acciones de navegación finalizan el intento activo como completado. Si no
hay sesión activa, solo cambian la ubicación.

- **Siguiente inciso:** desde `null` pasa a `1`; después incrementa en uno.
- **Anterior inciso:** decrementa en uno; desde `1` pasa a `null`; desde `null`
  no realiza cambios.
- **Siguiente ejercicio:** incrementa el ejercicio y establece inciso `null`.
- **Anterior ejercicio:** decrementa el ejercicio si es mayor que `1` y establece
  inciso `null`.
- **Siguiente sección:** incrementa la sección, establece ejercicio `1` e inciso
  `null`.
- **Anterior sección:** decrementa la sección si es mayor que `1`, establece
  ejercicio `1` e inciso `null`.

La navegación no borra intentos existentes.

## 6. Intentos y comentarios

Al finalizar una sesión se crea un `TimerItem` independiente con identificador
UUID, ubicación, tiempos, estado, comentario y fecha de creación. Dos items con
la misma ubicación siguen siendo intentos distintos.

El comentario preparado durante la sesión se recorta con `strip()` y se guarda
con el intento. En la vista Registros también se puede añadir o editar el
comentario de un item ya guardado.

La vista Registros permite además:

- agregar manualmente un intento;
- editar sus campos con validación;
- importar items seleccionados desde otro archivo;
- guardar como y renombrar el archivo activo;
- abrir archivos recientes, hasta diez;
- eliminar items tras confirmación.

## 7. Persistencia

Cada finalización, alta, edición, reset, eliminación o importación guarda el
archivo activo automáticamente. El formato exacto y sus reglas de compatibilidad
están en [CONTRATO_JSON.md](CONTRATO_JSON.md).

Al cerrar la ventana con una sesión activa se solicita confirmación. La opción
de guardar conserva el intento como incompleto; la cancelación mantiene abierta
la aplicación.

## 8. Reglas de compatibilidad

- Los nombres de campos JSON forman parte del contrato público local.
- Los tiempos persistidos son enteros no negativos en milisegundos.
- Los archivos válidos usan `schema_version: 1`.
- Un `inciso` ausente, `null` o legado con valor `0` se interpreta como sin
  inciso.
- Los campos opcionales ausentes (`comment`, `id`, fechas) reciben valores
  compatibles al cargar.

## 9. Fuera de alcance actual

No forman parte de la implementación actual: sincronización remota, usuarios,
autenticación, base de datos, múltiples ventanas de registro, edición de
períodos de receso separados y conocimiento previo de la estructura académica.
