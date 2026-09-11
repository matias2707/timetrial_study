# Especificación funcional de Study Timetrial

**Fecha de revisión:** 2026-09-11  
**Estado:** vigente para la implementación actual

## 1. Propósito y alcance

Study Timetrial es una aplicación de escritorio local desarrollada en Python y PySide6 para medir, estructurar y analizar sesiones de estudio por ejercicio. Permite registrar intentos de resolución, clasificar resultados, visualizar estadísticas de dedicación y planificar guías de estudio completas en archivos JSON locales sin requerir conexión a internet, servidores ni bases de datos externas.

La interfaz de usuario se compone de cuatro vistas principales en pestañas:

1. **Cronómetro:** Selección de ubicación, reloj digital de alta precisión, controles de sesión, navegación rápida, atajos de teclado y notas inmediatas.
2. **Registros:** Tabla analítica de intentos guardados con filtrado interactivo estilo Excel, ordenamiento jerárquico múltiple, reordenamiento de columnas y acciones rápidas.
3. **Estadísticas:** Panel de métricas acumuladas, gráficos semanales de barras antialiasing, ratios de estudio vs. receso y análisis por sección.
4. **Planificador:** Matriz visual del universo de estudio por secciones y ejercicios, seguimiento de completitud por incisos, pesos ponderados y carga directa al cronómetro.

## 2. Modelo de ubicación

Cada ejercicio o intento se ubica mediante una coordenada académica:

```text
Tipo de sección + Número de sección + Número de ejercicio + Inciso opcional
```

- **Tipo de sección:** Texto descriptivo; por defecto `"Guía"` (también `"Práctica"`, `"Parcial"`, etc.).
- **Número de sección:** Entero positivo desde `1`.
- **Ejercicio:** Entero positivo desde `1`.
- **Inciso:** Entero positivo desde `1` o `null`. En la interfaz se presenta `0` como "Sin inciso", normalizándose internamente a `null`.

## 3. Estados y ciclo de vida del cronómetro

El servicio de temporización utiliza tres modos centrales y un estado auxiliar de pausa:

| Modo | Significado visual | Comportamiento |
|---|---|---|
| `WAITING` | `LISTO PARA COMENZAR` (Gris / Pizarra) | Cronómetros en reposo. Permite modificar libremente la ubicación y crear o planificar secciones. |
| `PLAY` | `SESIÓN EN CURSO` (Verde esmeralda) | El reloj de ejercicio acumula tiempo monotónico. La ubicación permanece bloqueada. |
| `BREAK` | `RECESO EN CURSO` (Ámbar / Naranja) | El reloj de ejercicio se pausa; el reloj de receso acumula tiempo de descanso. |
| *Pausa Temporal* | `PAUSADO` (Azul pizarra) | Se congela el reloj mientras se resuelve un diálogo de confirmación (ej. desfasaje de incisos). |

### Acciones de sesión

- **Iniciar / Alternar sesión (Espacio / Botón central):**
  - Si está en `WAITING`, pasa a `PLAY` (emite sonido de inicio si no está silenciado).
  - Si está en `PLAY`, conmuta a `BREAK`.
  - Si está en `BREAK`, conmuta a `PLAY`.
- **Detener:** Cancela la sesión actual, descarta los tiempos no guardados y regresa a `WAITING`.
- **Completo:** Finaliza la sesión, registra un `TimerItem` con `completed = True`, emite sonido de éxito y vuelve a `WAITING`.
- **Incompleto:** Finaliza la sesión, registra un `TimerItem` con `completed = False` y vuelve a `WAITING`.
- **Comentario:** Permite redactar una anotación que se adjunta al intento al completarlo o marcarlo incompleto.

## 4. Navegación y comprobación de límites

Los controles de navegación permiten avanzar o retroceder de manera fluida entre incisos, ejercicios y secciones:

- **Siguiente Inciso:** Avanza al inciso inmediato superior (`null -> 1`, `1 -> 2`, etc.).
- **Anterior Inciso:** Retrocede al inciso anterior (`2 -> 1`, `1 -> null`).
- **Siguiente Ejercicio:** Incrementa el número de ejercicio y reinicia el inciso a `null`.
- **Anterior Ejercicio:** Decrementa el ejercicio (si es `> 1`) y reinicia el inciso a `null`.
- **Siguiente Sección:** Incrementa la sección, estableciendo ejercicio en `1` e inciso en `null`.
- **Anterior Sección:** Decrementa la sección (si es `> 1`), con ejercicio `1` e inciso `null`.

Si se ejecuta una acción de avance mientras hay una sesión activa en `PLAY` o `BREAK`, la sesión se guarda automáticamente como completada antes de desplazarse.

### Control de límites del Planificador
Antes de navegar hacia adelante (`next_*`), el sistema consulta a `PlannerService`:
- Si el ejercicio o inciso resultante excede la cantidad total configurada en la sección planificada activa, se muestra un diálogo de advertencia informando el límite y solicitando confirmación del usuario para continuar o permanecer dentro del rango planificado.

## 5. Detección y resolución de desfasajes de incisos (Inciso Gap Resolution)

Cuando el usuario registra o navega a un ejercicio con inciso (por ejemplo `Ej. 1, Inciso 2`), pero en el registro ya existían intentos previos de ese mismo ejercicio registrados sin inciso (`inciso = null`):

1. El cronómetro entra en pausa temporal para preservar los tiempos exactos.
2. Se abre el diálogo modal `IncisoGapDialog`, que presenta tres opciones:
   - **Promover registros existentes:** Asigna retroactivamente `inciso = 1` a los intentos previos no clasificados.
   - **Personalizar valores:** Permite editar manualmente la ubicación de destino.
   - **Cancelar:** Cancela la operación y reanuda el cronómetro sin alterar los registros.

## 6. Vista de Registros

Permite auditar, filtrar y modificar todos los intentos almacenados:

- **Filtros emergentes estilo Excel:** Menú en cada cabecera con casilla de búsqueda, lista de selección de valores únicos, indicador visual de filtro activo y botón general para limpiar filtros.
- **Ordenamiento jerárquico multicomponente:** Al hacer clic en las cabeceras se alternan órdenes ascendente, descendente o natural, manteniendo la precedencia visual configurada.
- **Reordenamiento de columnas:** Arrastrar y soltar cabeceras para reconfigurar el orden visual de las columnas.
- **Búsqueda global:** Caja de texto con filtrado en tiempo real sobre todas las columnas.
- **KPI Cards superiores:** Conteo total de intentos visibles, tiempo acumulado de ejercicio, tiempo de descanso y tasa de efectividad (%).
- **Acciones en línea por fila:** Botones compactos con tooltips para ver/editar comentarios, modificar datos del intento, reiniciar tiempos a cero o eliminar el registro tras confirmación.

## 7. Vista de Estadísticas

Ofrece visualizaciones analíticas agregadas sin requerir dependencias externas de trazado:

- **Métricas de resumen:** Total de horas estudiadas, promedio por ejercicio, sesión más prolongada, porcentaje de completitud y balance estudio/descanso.
- **Gráfico semanal de dedicación (`WeeklyChartWidget`):** Gráfico de 7 barras diarias renderizado con `QPainter` en alta resolución antialiasing, adaptado dinámicamente al Modo Claro y Modo Oscuro.
- **Resumen por sección:** Tabla desagregada con tiempos acumulados, cantidad de intentos, ejercicios únicos y porcentaje de avance respecto a la planificación.

## 8. Vista del Planificador

Permite configurar la estructura académica previa de guías y materias:

- **Tarjetas de Sección (`PlannedSectionCard`):** Contienen el título, conteo total de ejercicios, barra de progreso porcentual y resumen de completitud.
- **Mapeo de Incisos:** Configuración personalizada de ejercicios compuestos con cantidad variable de incisos (ej. Ejercicio 1 con incisos `a`, `b`, `c`).
- **Ponderación de completitud (`completed_weight`):** Un ejercicio con 4 incisos completados en 2 de ellos suma `0.5` al progreso total de la sección.
- **Código de colores interactivo:**
  - **Verde:** Ejercicio o inciso completado satisfactoriamente.
  - **Rojo:** Ejercicio o inciso con intentos fallidos / incompletos sin resolver.
  - **Gris:** Ejercicio pendiente de resolución.
- **Carga al cronómetro:** Al hacer clic en cualquier ejercicio del planificador, se consulta si se desea transferir esa ubicación directamente a la pestaña Cronómetro.
- **Sincronización automática:** Cualquier intento registrado en el cronómetro que pertenezca a la sección se refleja de inmediato en el planificador.

## 9. Temas y Experiencia de Usuario

- **Selector de temas:** Soporte integrado para **Modo Claro** y **Modo Oscuro** con diseño moderno, alto contraste y paletas HSL afinadas.
- **Notificaciones sonoras:** Efectos de sonido para inicio y finalización de ejercicios, con opción de silenciar (*Mute*) accesible desde el menú superior.
- **Persistencia de preferencias:** El tema seleccionado y el estado de silencio de audio se guardan automáticamente en la configuración local del sistema operativo (`QSettings`).
- **Diseño adaptable:** Distribución responsiva que ajusta los paneles de control y navegación cuando la ventana se redimensiona a anchos reducidos.

## 10. Persistencia y almacenamiento

- Persistencia en archivos JSON atómicos locales con esquema versión `1`.
- Guardado automático tras cada finalización, edición, importación o borrado.
- Menú de archivos recientes con acceso directo a los últimos 10 registros utilizados.
- Diálogo de advertencia ante intentos de cierre con cronómetro en marcha.
