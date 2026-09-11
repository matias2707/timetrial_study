# Operación y validación

**Fecha de revisión:** 2026-09-11  
**Estado:** vigente para la implementación actual

## Requisitos

- Windows, macOS o Linux con Python 3.10 o superior compatible con PySide6.
- Dependencias definidas en `requirements.txt`:
  - `PySide6>=6.8`
  - `qtawesome>=1.3.0`

## Instalación y ejecución

Desde la raíz del proyecto en la terminal:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Al iniciar por primera vez o sin argumento, la aplicación ofrece crear un archivo nuevo o abrir un registro reciente. Si se continúa, crea o asocia automáticamente un registro local `StudyTimetrial_YYYYMMDD.json`. Desde el menú superior **Archivo** se puede crear otro archivo, abrir uno existente, guardar como, renombrar o cerrar el registro actual.

## Validación automática

### 1. Ejecución de la suite de pruebas unitarias

La suite cubre servicios de aplicación, persistencia, lógica de planificación, agregaciones estadísticas, consultas de registros, formateadores y componentes de interfaz (usando modo `offscreen` sin abrir ventanas interactivas):

```powershell
python -m unittest discover -s tests -v
```

### 2. Comprobación de sintaxis y compilación

Verifica que todos los módulos de presentación, aplicación, dominio e infraestructura compilen sin errores de sintaxis:

```powershell
python -m py_compile main.py presentation/main_window.py presentation/weekly_chart_widget.py presentation/planner_widget.py presentation/planner_dialogs.py presentation/inciso_dialog.py presentation/excel_filter_popup.py presentation/flow_layout.py presentation/presentation_dialogs.py presentation/presentation_formatters.py presentation/theme.py application/application_service.py application/planner_service.py application/statistics_service.py application/record_query.py domain/models.py domain/timer_service.py infrastructure/storage_service.py
```

## Protocolo de validación manual de interfaz

Tras introducir modificaciones en la interfaz o controladores, ejecutar `python main.py` y seguir la lista de verificación:

### Vista Cronómetro:
1. **Flujo de sesión:** Iniciar una sesión (`Espacio`), alternar a receso, reanudar y finalizar como completo (`Enter`). Confirmar sonido de éxito.
2. **Sesión incompleta:** Iniciar otra sesión y marcarla como incompleta (`Esc`). Confirmar registro en la tabla.
3. **Bloqueo de controles:** Comprobar que los campos de sección, ejercicio e inciso se bloquean durante la sesión y se reactivan al finalizar.
4. **Navegación:** Probar botones de avance y retroceso (inciso, ejercicio, sección). Verificar que se guarden los intentos activos.
5. **Comentario en curso:** Preparar un comentario antes de finalizar y verificar que aparezca adjunto en la tabla de registros.

### Vista Registros:
6. **Filtros emergentes:** Abrir el popup de filtro de una cabecera de columna, desmarcar valores y confirmar que la tabla y el conteo se actualizan. Probar el botón para limpiar todos los filtros.
7. **Ordenamiento jerárquico:** Hacer clic en las cabeceras para alternar orden ascendente y descendente en varias columnas simultáneas.
8. **Edición manual:** Probar agregar un item manual, editar un intento existente, reiniciar contadores y eliminar un registro.

### Vista Estadísticas:
9. **Visualización y métricas:** Acceder a la pestaña y verificar que las tarjetas de KPIs muestren los totales correctos y que el gráfico de barras semanal pinte las columnas proporcionales al tiempo estudiado.

### Vista Planificador:
10. **Gestión de secciones:** Crear una sección planificada (`Guía 1`, 10 ejercicios, con incisos en el ejercicio 1).
11. **Carga rápida:** Hacer clic en un ejercicio del planificador y confirmar que transfiera la ubicación al cronómetro.
12. **Límites de navegación:** Intentar navegar más allá del total de ejercicios configurados en la sección activa y comprobar el diálogo de advertencia de límites.

### Configuración y Temas:
13. **Modo Claro / Modo Oscuro:** Alternar el tema desde el menú superior **Configuración > Temas** y verificar el contraste visual y repintado de estilos.
14. **Control de audio:** Conmutar la opción de silenciar sonidos y verificar que los efectos sonoros respeten el estado.
15. **Confirmación al salir:** Iniciar una sesión e intentar cerrar la ventana (`Alt+F4`); comprobar que el diálogo pregunte si guardar o descartar.

## Diagnóstico y directrices de soporte

- Los errores de esquema o JSON malformado se deben tratar como problemas del archivo externo, sin improvisar migraciones que corrompan datos existentes.
- La ruta activa y la lista de recientes son administradas exclusivamente por `infrastructure/storage_service.py`.
- La lógica de casos de uso y cálculo de métricas debe permanecer desacoplada de `QApplication` para garantizar su cobertura en pruebas automatizadas.
