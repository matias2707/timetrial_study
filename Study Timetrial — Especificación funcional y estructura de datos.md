# Study Timetrial — Especificación funcional y estructura de datos

## 1. Propósito

**Study Timetrial** es una aplicación de escritorio para medir el tiempo que un estudiante dedica a ejercicios de una materia y registrar cada intento de forma estructurada.

El programa permite:

- seleccionar una ubicación lógica dentro de una materia;
- cronometrar el tiempo efectivo de resolución;
- cronometrar períodos de descanso;
- acumular múltiples períodos de descanso;
- registrar múltiples intentos del mismo ejercicio;
- indicar si un intento fue completado o no;
- navegar rápidamente entre ejercicios, incisos y secciones;
- visualizar, editar, reiniciar y eliminar registros;
- guardar toda la información en un archivo local legible nuevamente por el programa.

La aplicación estará diseñada para uso personal y local, sin necesidad de servidor ni base de datos.

---

# 2. Terminología

El programa utilizará cuatro niveles lógicos:

```text
REGISTRO / MATERIA
└── SECCIÓN
    └── EJERCICIO
        └── INCISO
            └── INTENTO
```

### Registro / Materia

Es el archivo completo correspondiente a una materia.

Ejemplo:

```text
Algebra.json
```

El registro contiene todos los datos de la materia:

```text
Algebra
├── Guía 1
├── Guía 2
├── Guía 3
├── Parcial 1
├── Final 1
└── ...
```

Solamente puede existir **un registro abierto simultáneamente**.

---

## 3. Sección

"Sección" es el nombre genérico del primer nivel.

Una sección puede representar:

- Guía
- Parcial
- Final
- otro tipo definido por el usuario

Ejemplos:

```text
Guía 1
Guía 2
Parcial 1
Parcial 2
Final 1
```

Por defecto, el tipo será:

```text
Guía
```

y su numeración comenzará en:

```text
1
```

La aplicación **no necesita conocer previamente cuántas secciones existen**.

Tampoco necesita conocer cuántos ejercicios tiene una sección.

---

# 4. Ejercicio

Un ejercicio tiene:

```text
número natural > 0
```

Ejemplos:

```text
Ejercicio 1
Ejercicio 2
Ejercicio 17
Ejercicio 125
```

No existen restricciones respecto del número máximo.

El programa no necesita conocer previamente qué ejercicios existen.

Por lo tanto, puede existir directamente:

```text
Ejercicio 37
```

aunque jamás se haya registrado el 1 al 36.

---

# 5. Inciso

Un ejercicio puede:

### No tener inciso

Internamente:

```text
inciso = null
```

Nunca se visualiza como `0`.

La interfaz mostrará simplemente:

```text
Guía 1 - Ejercicio 3
```

y no:

```text
Guía 1 - Ejercicio 3 - Inciso 0
```

### Tener inciso

Los incisos son:

```text
1, 2, 3, 4, 5, ...
```

Nunca existe el inciso 0.

El programa no necesita saber cuántos incisos tiene el ejercicio.

Por ejemplo:

```text
Ejercicio 2
 ├── Inciso 1
 ├── Inciso 2
 ├── Inciso 3
 └── Inciso 4
```

El programa permite continuar indefinidamente:

```text
Siguiente inciso
→ 5
→ 6
→ 7
→ ...
```

aunque conceptualmente el estudiante pueda no necesitarlos.

---

# 6. Intento

Cada vez que se guarda una ejecución de un ejercicio se crea un **intento independiente**.

Por ejemplo:

```text
Guía 1 - Ejercicio 5

Intento 1 → 00:08:32:450
Intento 2 → 00:07:51:210
Intento 3 → 00:06:59:875
```

Los intentos se almacenan como registros independientes.

No es necesario que el número de intento sea visible para el usuario.

El agrupamiento se determina mediante:

```text
Sección + Ejercicio + Inciso
```

Por lo tanto, si existen dos registros:

```text
Guía 1 - Ejercicio 5 - Inciso 2
Guía 1 - Ejercicio 5 - Inciso 2
```

se interpretan naturalmente como dos intentos del mismo ejercicio/inciso.

---

# 7. Estados de la aplicación

La aplicación tendrá cuatro estados principales:

```text
ESPERA
PLAY
RECESO
REGISTROS
```

### ESPERA

No existe ningún cronómetro activo.

El usuario puede seleccionar/modificar:

```text
Sección
Número de sección
Ejercicio
Inciso
```

Valores iniciales:

```text
Sección = Guía
Número de sección = 1
Ejercicio = 1
Inciso = null
```

En pantalla se mostraría algo como:

```text
Guía 1 - Ejercicio 1
```

o:

```text
Guía 1 - Ejercicio 1 - Inciso 1
```

dependiendo del valor del inciso.

---

# 8. Estado PLAY

Al presionar:

```text
PLAY
```

comienza a correr el tiempo de ejercicio.

La ubicación seleccionada queda bloqueada visualmente y pasa a ser solamente informativa.

Ejemplo:

```text
Guía 2 - Ejercicio 7 - Inciso 3
```

Mientras el tiempo está corriendo:

- sección no editable;
- ejercicio no editable;
- inciso no editable;
- botón Registros deshabilitado.

El cronómetro de ejercicio comienza a acumular tiempo.

---

# 9. Estado RECESO

Al presionar:

```text
RECESO
```

se produce una alternancia:

```text
TIEMPO DE EJERCICIO → pausado
TIEMPO DE RECESO    → activo
```

Mientras el receso está activo:

```text
Ejercicio: 00:17:32:421
Receso:    00:02:18:503
```

El tiempo de ejercicio no avanza.

El tiempo de receso sí avanza.

---

## 9.1. Reanudar

Al presionar:

```text
PLAY
```

se produce:

```text
TIEMPO DE RECESO    → pausado
TIEMPO DE EJERCICIO → continúa
```

No se pierde ningún tiempo.

---

## 9.2. Múltiples recesos

Pueden existir tantos recesos como el usuario quiera:

```text
Ejercicio
  ↓
Receso
  ↓
Ejercicio
  ↓
Receso
  ↓
Ejercicio
  ↓
Receso
  ↓
Ejercicio
```

No se guardan como períodos independientes.

Solamente interesa el acumulado:

```text
receso_total = receso_1 + receso_2 + receso_3 + ...
```

Ejemplo:

```text
Receso 1 = 00:02:15:000
Receso 2 = 00:01:30:000
Receso 3 = 00:00:45:000

Total = 00:04:30:000
```

---

# 10. Precisión temporal

Internamente los tiempos se almacenarán en **milisegundos**.

Ejemplo:

```text
1250345 ms
```

se visualiza como:

```text
00:20:50:345
```

Formato:

```text
HH:MM:SS:SSS
```

Los milisegundos serán utilizados internamente aunque inicialmente la información visible podría ser suficiente en resoluciones menores.

Esta decisión permite cambiar posteriormente la forma de visualización sin modificar la estructura de almacenamiento.

---

# 11. Reiniciar

El botón:

```text
REINICIAR
```

reinicia el intento actualmente en curso.

Resultado:

```text
Tiempo de ejercicio = 00:00:00:000
Tiempo de receso    = 00:00:00:000
```

No genera ningún registro.

No modifica registros existentes.

No agrega información al archivo.

Por lo tanto:

```text
Antes:
Ejercicio 3
Tiempo = 00:12:34

REINICIAR

Después:
Ejercicio 3
Tiempo = 00:00:00
```

Es como comenzar nuevamente el mismo intento sin haber guardado el anterior.

Si había un receso activo, también se cancela.

---

# 12. Reintentar

El botón:

```text
REINTENTAR
```

significa:

> guardar el intento actual y comenzar inmediatamente otro intento del mismo ejercicio/inciso.

Primero se guarda:

```text
Tiempo actual
Receso acumulado
Sección
Ejercicio
Inciso
Completado = false
```

Luego:

```text
Tiempo de ejercicio = 00:00:00:000
Tiempo de receso    = 00:00:00:000
```

y continúa en:

```text
misma sección
mismo ejercicio
mismo inciso
```

Ejemplo:

```text
Guía 1 - Ejercicio 8 - Inciso 2

Intento anterior:
Tiempo = 00:10:32
Completado = false

REINTENTAR

Nuevo intento:
Tiempo = 00:00:00
Completado = false
```

---

# 13. Siguiente Inciso

El botón:

```text
SIGUIENTE INCISO
```

guarda el intento actual y avanza al siguiente inciso del mismo ejercicio.

Antes de avanzar:

```text
se guarda el tiempo
se guarda el receso
se guarda completado = true
```

Luego:

```text
inciso = inciso + 1
```

### Caso especial: ejercicio sin inciso

Si actualmente:

```text
inciso = null
```

y se presiona:

```text
SIGUIENTE INCISO
```

el resultado será:

```text
inciso = 1
```

Por lo tanto:

```text
Guía 1 - Ejercicio 4
```

pasa a:

```text
Guía 1 - Ejercicio 4 - Inciso 1
```

Esto permite convertir funcionalmente un ejercicio sin inciso en uno con inciso.

---

# 14. Siguiente Ejercicio

El botón:

```text
SIGUIENTE EJERCICIO
```

guarda el intento actual:

```text
completado = true
```

y avanza:

```text
ejercicio = ejercicio + 1
```

El inciso se reinicia a:

```text
null
```

porque el programa no sabe si el nuevo ejercicio tendrá incisos.

Ejemplo:

```text
Guía 1 - Ejercicio 4 - Inciso 3
```

→ Siguiente ejercicio →

```text
Guía 1 - Ejercicio 5
```

Si el Ejercicio 5 tiene incisos, el usuario podrá pasar a:

```text
Inciso 1
```

mediante la interfaz o mediante `Siguiente inciso`.

El programa nunca necesita conocer de antemano la estructura del ejercicio.

---

# 15. Siguiente Sección

El botón conceptualmente denominado:

```text
SIGUIENTE G
```

será tratado internamente como:

```text
SIGUIENTE SECCIÓN
```

porque una materia puede tener:

```text
Guías
Parciales
Finales
```

en el mismo nivel jerárquico.

El botón:

1. guarda el intento actual;
2. marca el intento como completado;
3. incrementa la sección;
4. reinicia ejercicio a `1`;
5. establece inciso en `null`.

Ejemplo:

```text
Guía 3 - Ejercicio 8 - Inciso 2
```

→ Siguiente sección →

```text
Guía 4 - Ejercicio 1
```

El tipo de sección se conserva por defecto.

La posibilidad de cambiar de:

```text
Guía
```

a:

```text
Parcial
```

se realiza mediante la configuración de la sección.

---

# 16. Detener

El botón:

```text
DETENER
```

finaliza la ejecución actual y guarda el intento.

El registro generado tendrá:

```text
completado = false
```

porque detener la aplicación no implica que el ejercicio haya sido completado.

Después:

```text
PLAY → ESPERA
```

La información seleccionada puede volver a modificarse.

El registro generado permanece guardado.

---

# 17. Regla general de completado

El campo:

```text
completado : boolean
```

representa si ese intento particular se considera terminado.

Se utilizará:

| Acción | Guarda registro | Completado |
|---|---:|---:|
| Siguiente inciso | Sí | `true` |
| Siguiente ejercicio | Sí | `true` |
| Siguiente sección | Sí | `true` |
| Reintentar | Sí | `false` |
| Detener | Sí | `false` |
| Reiniciar | No | — |

Esto permite distinguir, por ejemplo:

```text
Intento 1 → 12:42 → false
Intento 2 → 10:18 → false
Intento 3 → 09:54 → true
```

---

# 18. Guardado automático de los intentos

Cada vez que una acción genera un registro:

```text
Siguiente inciso
Siguiente ejercicio
Siguiente sección
Reintentar
Detener
```

la información se escribe automáticamente en el archivo activo.

El programa reutiliza el mismo archivo mientras ese registro permanezca abierto.

Por ejemplo:

```text
Algebra.json
```

puede recibir:

```text
Intento 1
Intento 2
Intento 3
Intento 4
...
```

sin necesidad de pulsar manualmente "Guardar" después de cada ejercicio.

---

# 19. Archivo automático

Si el usuario todavía no ha elegido un archivo definitivo, el programa generará automáticamente un archivo local de trabajo.

Ese archivo será el almacenamiento persistente del registro activo.

El nombre inicial puede ser generado automáticamente, por ejemplo:

```text
StudyTimetrial_20260902.json
```

Posteriormente el usuario puede convertirlo en:

```text
Algebra.json
```

El programa utilizará el mismo archivo hasta que el usuario lo cierre manualmente desde Registros.

---

# 20. Pérdida de un intento en curso

Existe una distinción importante:

### Datos ya registrados

Ya fueron escritos en el archivo.

Por lo tanto, no se pierden al cerrar el programa.

### Intento actualmente corriendo

Todavía no es un registro definitivo.

Si la aplicación termina inesperadamente, por ejemplo:

```text
crash
apagado
proceso terminado
```

el intento actualmente en ejecución puede perderse.

Los intentos anteriores permanecen guardados.

---

# 21. Cierre mediante X

Cuando el usuario presiona la X de la ventana y existe un intento en ejecución, el programa mostrará:

```text
Hay un intento en curso.

¿Desea guardar la información antes de salir?
```

Opciones:

```text
Guardar y salir
Salir sin guardar
Cancelar
```

### Guardar y salir

Guarda el intento actual como:

```text
completado = false
```

porque cerrar la aplicación tampoco demuestra que el ejercicio haya sido completado.

### Salir sin guardar

Descarta solamente el intento actualmente en ejecución.

Los registros anteriores no se modifican.

### Cancelar

La aplicación continúa funcionando.

---

# 22. Pantalla Registros

La pantalla Registros representa el contenido persistente de la materia.

Header recomendado:

```text
[Abrir registro] [Guardar registro] [Renombrar] [Cerrar registro]
```

Y en el cuerpo:

```text
[Agregar item]
```

---

# 23. Visualización de los registros

Cada intento aparecerá individualmente.

Formato conceptual:

```text
Sección - Ejercicio - Inciso - Receso - Tiempo - Completado - Editar - Reset - Eliminar
```

Ejemplo:

```text
Guía 1 - E1 -      - 00:01:32:120 - 00:08:31:442 - Sí
Guía 1 - E1 - I1   - 00:00:44:500 - 00:04:12:231 - No
Guía 1 - E1 - I1   - 00:00:20:000 - 00:03:51:882 - Sí
Guía 1 - E2 -      - 00:02:10:450 - 00:09:12:734 - Sí
```

Los intentos del mismo ejercicio/inciso aparecen uno debajo del otro.

---

# 24. Orden de los registros

El orden recomendado será:

```text
Sección
    ↓
Ejercicio
    ↓
Inciso
    ↓
Intentos
```

Dentro de un mismo ejercicio/inciso, los intentos se muestran en el orden en que fueron creados.

Esto hace que:

```text
Guía 1 - Ejercicio 4 - Inciso 2
```

aparezca como un bloque:

```text
Intento A
Intento B
Intento C
```

aunque los intentos hayan sido generados en diferentes momentos.

---

# 25. Editar

Al presionar:

```text
EDITAR
```

la fila pasa a modo edición.

Los campos editables serán:

```text
Sección / tipo
Número de sección
Ejercicio
Inciso
Receso
Tiempo
Completado
```

El usuario podrá editar una celda individual.

Ejemplo:

```text
doble click → Ejercicio
```

permite introducir un nuevo número.

Al presionar:

```text
ENTER
```

se valida el valor.

Si es correcto:

```text
Registro modificado correctamente.
```

El cambio se escribe inmediatamente en el archivo.

Si es incorrecto:

```text
Valor inválido.
```

y el dato anterior se conserva.

---

# 26. Reglas de validación

### Sección

El número debe ser:

```text
natural > 0
```

### Ejercicio

Debe ser:

```text
natural > 0
```

### Inciso

Puede ser:

```text
null
```

o:

```text
natural > 0
```

Nunca:

```text
0
```

### Tiempo

Debe ser:

```text
>= 00:00:00:000
```

### Receso

Debe ser:

```text
>= 00:00:00:000
```

### Completado

Debe ser exclusivamente:

```text
true
false
```

---

# 27. Conversión de ejercicio sin inciso a ejercicio con inciso

Está permitido.

Ejemplo:

```text
Guía 1 - Ejercicio 4
```

puede modificarse a:

```text
Guía 1 - Ejercicio 4 - Inciso 1
```

También puede modificarse posteriormente a:

```text
Guía 1 - Ejercicio 4 - Inciso 2
```

El campo simplemente pasa de:

```text
null
```

a:

```text
1
```

---

# 28. Reset de un registro

El botón:

```text
RESET
```

requiere confirmación.

Diálogo:

```text
¿Está seguro de reiniciar este registro?
```

Si el usuario confirma:

```text
Tiempo  → 00:00:00:000
Receso  → 00:00:00:000
```

El resto de la información permanece igual.

En particular:

```text
Sección
Ejercicio
Inciso
Completado
```

no se modifican.

El registro continúa existiendo.

---

# 29. Eliminar un registro

El botón:

```text
ELIMINAR
```

requiere confirmación.

Diálogo:

```text
¿Está seguro de eliminar este registro?

Esta acción no se puede deshacer.
```

Si se confirma:

```text
registro eliminado
```

y el cambio se guarda inmediatamente en el archivo.

---

# 30. Agregar item

La pantalla Registros tendrá:

```text
AGREGAR ITEM
```

para introducir manualmente un registro.

El formulario permitirá establecer:

```text
Tipo de sección
Número de sección
Ejercicio
Inciso
Tiempo
Receso
Completado
```

Valores iniciales recomendados:

```text
Inciso = null
Tiempo = 00:00:00:000
Receso = 00:00:00:000
Completado = false
```

Al confirmar:

1. se validan los datos;
2. se crea un nuevo registro;
3. se agrega al historial;
4. se guarda inmediatamente en el archivo.

Esto permite cargar manualmente información sin utilizar el cronómetro.

---

# 31. Abrir registro

Al presionar:

```text
ABRIR REGISTRO
```

se abre el explorador de archivos.

El usuario selecciona un archivo compatible, inicialmente:

```text
*.json
```

El programa:

1. abre el archivo;
2. valida su estructura;
3. comprueba su versión;
4. carga los datos;
5. muestra el contenido en Registros.

Si el archivo no es válido, se muestra un error y el registro actual no se modifica.

---

# 32. Un solo registro abierto

Solo puede existir un registro activo simultáneamente.

Si ya existe uno abierto y el usuario intenta abrir otro:

```text
Ya existe un registro abierto.

Cierre el registro actual antes de abrir otro.
```

Esto evita mezclar accidentalmente datos de dos materias.

---

# 33. Cerrar registro

Al presionar:

```text
CERRAR REGISTRO
```

aparece una confirmación:

```text
¿Desea cerrar el registro actual?
```

Si confirma:

```text
registro activo → ninguno
```

El archivo no se elimina.

Simplemente deja de estar abierto en la aplicación.

Posteriormente puede volver a abrirse mediante:

```text
Abrir registro
```

---

# 34. Guardar registro

El botón:

```text
GUARDAR REGISTRO
```

es la operación mediante la cual el usuario puede guardar/exportar el registro en una ubicación elegida.

Si el registro todavía utiliza un archivo interno generado automáticamente:

```text
Guardar registro
```

abre el explorador de archivos para elegir:

```text
ubicación
nombre
```

Ejemplo:

```text
Algebra.json
```

Una vez guardado:

```text
archivo activo = Algebra.json
```

y las siguientes operaciones automáticas utilizarán ese archivo.

---

# 35. Renombrar registro

Se agregará una acción:

```text
RENOMBRAR
```

para permitir cambiar el nombre del archivo sin modificar su contenido.

Ejemplo:

```text
StudyTimetrial_20260902.json
```

→

```text
Algebra.json
```

El nombre visible de la aplicación se actualizará automáticamente:

```text
Study Timetrial - Algebra
```

La extensión `.json` no se mostrará en el título.

---

# 36. Título de la aplicación

El título de la ventana y de Home seguirá el nombre del registro activo.

Ejemplo:

```text
Study Timetrial - Algebra
```

Si se abre:

```text
Fisica.json
```

el título será:

```text
Study Timetrial - Fisica
```

Si no existe ningún registro abierto:

```text
Study Timetrial
```

---

# 37. Estructura de datos

La estructura se mantendrá deliberadamente sencilla.

No se almacenarán ejercicios vacíos ni listas innecesarias de incisos.

Cada intento será un objeto independiente.

La jerarquía se reconstruye a partir de sus campos.

Ejemplo:

```json
{
  "schema_version": 1,
  "application": "Study Timetrial",
  "record_name": "Algebra",
  "created_at": "2026-09-02T12:00:00",
  "updated_at": "2026-09-02T13:20:00",
  "items": [
    {
      "id": "uuid-001",
      "section_type": "Guía",
      "section_number": 1,
      "exercise": 1,
      "inciso": null,
      "exercise_time_ms": 523420,
      "break_time_ms": 82450,
      "completed": true,
      "created_at": "2026-09-02T12:10:15"
    },
    {
      "id": "uuid-002",
      "section_type": "Guía",
      "section_number": 1,
      "exercise": 2,
      "inciso": 1,
      "exercise_time_ms": 311250,
      "break_time_ms": 12000,
      "completed": false,
      "created_at": "2026-09-02T12:20:40"
    },
    {
      "id": "uuid-003",
      "section_type": "Guía",
      "section_number": 1,
      "exercise": 2,
      "inciso": 1,
      "exercise_time_ms": 284900,
      "break_time_ms": 45000,
      "completed": true,
      "created_at": "2026-09-02T12:28:02"
    }
  ]
}
```

---

# 38. Por qué los datos se almacenan como una lista de items

Aunque conceptualmente exista:

```text
Guía
 └── Ejercicio
      └── Inciso
           └── Intento
```

no es necesario almacenar físicamente todos esos niveles como objetos anidados.

Es más simple almacenar:

```text
items[]
```

y que cada item indique su ubicación.

Por ejemplo:

```text
section_type
section_number
exercise
inciso
```

Esto permite:

- ejercicios inexistentes;
- números arbitrarios;
- ejercicios sin inciso;
- conversión de `null` a inciso;
- edición de cualquier campo;
- eliminación sencilla;
- agregar registros manualmente;
- múltiples intentos;
- futuras modificaciones de la estructura.

La jerarquía se mantiene conceptualmente sin obligar al archivo a contener elementos vacíos.

---

# 39. Identificador interno

Cada item tendrá un:

```text
id
```

único.

Preferentemente:

```text
UUID
```

Esto permite distinguir incluso dos registros completamente idénticos.

Por ejemplo:

```text
Guía 1 - E3 - I2 - 00:05:00
Guía 1 - E3 - I2 - 00:05:00
```

aunque sean idénticos visualmente, internamente serán dos items diferentes.

---

# 40. Historial y edición

El campo:

```text
created_at
```

permitirá saber cuándo se creó el registro.

La aplicación puede utilizarlo para mantener el orden de creación de los intentos.

No es necesario mostrarlo inicialmente en la interfaz.

Puede servir posteriormente para:

- estadísticas;
- historial temporal;
- análisis de rendimiento;
- filtros;
- gráficos.

---

# 41. Estados internos del cronómetro

Conceptualmente, la lógica será:

```text
                 ┌─────────────┐
                 │   ESPERA    │
                 └──────┬──────┘
                        │ PLAY
                        ▼
                 ┌─────────────┐
          ┌──────│    PLAY     │
          │      └──────┬──────┘
          │             │ RECESO
          │             ▼
          │      ┌─────────────┐
          └──────│   RECESO    │
             PLAY└─────────────┘
```

Desde PLAY también existen:

```text
Reiniciar
Reintentar
Siguiente inciso
Siguiente ejercicio
Siguiente sección
Detener
```

Desde RECESO:

```text
PLAY
Reintentar
Siguiente inciso
Siguiente ejercicio
Siguiente sección
Detener
```

En particular:

```text
RECESO + PLAY
```

significa:

```text
terminar receso
reanudar ejercicio
```

---

# 42. Regla fundamental de persistencia

El sistema distinguirá entre:

### Estado temporal

Lo que está ocurriendo ahora:

```text
timer activo
tiempo acumulado actual
receso actual
sección actual
ejercicio actual
inciso actual
```

### Datos persistentes

Lo que ya fue convertido en un intento:

```text
items[]
```

Solo las acciones que generan un registro escriben un nuevo item.

Esto evita que el archivo tenga que modificarse cientos de veces por segundo mientras corre el cronómetro.

---

# 43. Arquitectura recomendada

Para este programa la tecnología recomendada continúa siendo:

```text
Python
    ↓
PySide6 / Qt
    ↓
JSON
```

Estructura aproximada:

```text
StudyTimetrial/
│
├── main.py
│
├── models/
│   ├── record.py
│   └── timer_state.py
│
├── services/
│   ├── timer_service.py
│   └── storage_service.py
│
├── ui/
│   ├── home_window.py
│   ├── records_window.py
│   ├── dialogs/
│   └── widgets/
│
└── data/
```

La lógica del cronómetro debería estar separada de la interfaz.

La interfaz únicamente debería mostrar el estado y enviar acciones.

---

# 44. Decisiones finales adoptadas

Para evitar ambigüedades al comenzar la implementación:

```text
1. No existen límites predefinidos de ejercicios o incisos.

2. Inciso inexistente = null.
   Nunca se almacena 0.

3. Siguiente inciso desde null → inciso 1.

4. Siguiente ejercicio → ejercicio + 1, inciso = null.

5. Siguiente sección → sección + 1, ejercicio = 1, inciso = null.

6. Receso y tiempo de ejercicio son acumuladores independientes.

7. Solo uno corre simultáneamente.

8. Reiniciar no genera registro.

9. Reintentar genera un registro no completado y comienza otro intento.

10. Siguiente inciso/ejercicio/sección genera un registro completado.

11. Detener genera un registro no completado.

12. Reset solamente pone tiempo y receso en cero.

13. Los intentos son registros independientes.

14. Dos intentos pueden ser completamente idénticos.

15. Solo puede existir un registro abierto simultáneamente.

16. Los registros confirmados se guardan automáticamente.

17. El intento actualmente en ejecución es temporal.

18. Al cerrar con X, el usuario puede guardar o descartar el intento actual.

19. El archivo será JSON.

20. Los tiempos se almacenarán en milisegundos.

21. La interfaz utilizará HH:MM:SS:SSS.

22. El nombre del archivo determina el nombre mostrado en el título.

23. El usuario podrá guardar/renombrar el registro.

24. El archivo tendrá una versión de esquema para permitir futuras modificaciones.

25. La edición, eliminación, reset y agregado de items se persisten inmediatamente.
```

---

# 45. Resultado conceptual

La aplicación completa queda reducida a dos grandes operaciones:

```text
HOME
```

para **producir datos mediante un cronómetro**,

y:

```text
REGISTROS
```

para **administrar los datos producidos**.

El flujo normal será:

```text
Seleccionar ubicación
        ↓
PLAY
        ↓
Ejercicio
   ↕
Receso
        ↓
Siguiente / Reintentar / Detener
        ↓
Item guardado automáticamente
        ↓
Siguiente ejercicio/inciso/sección
        ↓
...
        ↓
REGISTROS
        ↓
Editar / Reset / Eliminar / Agregar
        ↓
Guardar / Renombrar / Cerrar
```

Con esta estructura, el proyecto queda suficientemente definido para comenzar la implementación sin tener que tomar decisiones importantes durante el desarrollo.