# Study Timetrial

Aplicación de escritorio local desarrollada en Python y PySide6 para cronometrar ejercicios de estudio, registrar intentos, analizar estadísticas de rendimiento y planificar guías de estudio completas en archivos JSON.

## Características principales

- **Cronómetro de alta precisión:** Reloj digital monotónico con tiempos netos de ejercicio y descanso, navegación rápida entre incisos/ejercicios/secciones, atajos de teclado y notas inmediatas.
- **Tabla de Registros analítica:** Filtros interactivos emergentes estilo Excel, ordenamiento múltiple jerárquico, reordenamiento de columnas, búsqueda global, KPI cards y badges de estado.
- **Panel de Estadísticas:** Resumen de métricas acumuladas, gráfico semanal de dedicación renderizado en alta resolución antialiasing y análisis desagregado por sección.
- **Planificador de estudio:** Estructuración previa de guías académicas con ejercicios simples y compuestos (incisos), pesos ponderados de completitud (`completed_weight`) y carga directa al cronómetro con verificación de límites.
- **Resolución de desfasaje de incisos:** Pausa automática del cronómetro y diálogo modal inteligente ante detección de intentos previos sin clasificar.
- **Temas y Audio:** Soporte instantáneo para **Modo Claro** y **Modo Oscuro**, y notificaciones sonoras con opción de silencio.
- **Persistencia local y segura:** Archivos JSON atómicos y portables (esquema versión `1`), sin dependencia de servicios en la nube ni bases de datos externas.

## Inicio rápido

En PowerShell o terminal, desde la raíz del proyecto:

```powershell
python -m pip install -r requirements.txt
python main.py
```

La primera ejecución crea un registro local automático `StudyTimetrial_YYYYMMDD.json` o permite elegir un archivo nuevo o reciente.

## Estructura del proyecto

- `main.py`: Punto de entrada que inicializa `QApplication` y levanta la ventana principal.
- `presentation/`: Interfaz visual en PySide6:
  - `main_window.py`: Ventana principal, navegación, barras de herramientas y coordinación.
  - `weekly_chart_widget.py`: Gráfico semanal de barras personalizado renderizado con `QPainter`.
  - `planner_widget.py` y `planner_dialogs.py`: Interfaz y diálogos del Planificador.
  - `excel_filter_popup.py`: Menú de filtro y ordenamiento avanzado tipo Excel.
  - `inciso_dialog.py`: Diálogo modal de resolución guiada de desfasajes de incisos.
  - `theme.py`: Definición y generación de estilos para Modo Claro y Oscuro.
  - `presentation_dialogs.py` y `presentation_formatters.py`: Diálogos y adaptadores de tiempo.
- `application/`: Casos de uso desacoplados de bibliotecas gráficas:
  - `application_service.py`: Fachada principal de coordinación (`StudyApplicationService`).
  - `planner_service.py`: Lógica de análisis de avance, pesos y límites del planificador.
  - `statistics_service.py`: Procesamiento analítico y agregaciones temporales.
  - `record_query.py`: Filtrado multicriterio y ordenamiento jerárquico de registros.
- `domain/`: Reglas de negocio y entidades fundamentales:
  - `models.py`: Entidades `TimerItem`, `PlannedSection` y `Record`.
  - `timer_service.py`: Reloj monotónico de precisión con modos `WAITING`, `PLAY` y `BREAK`.
- `infrastructure/`:
  - `storage_service.py`: Persistencia JSON y gestión del índice de archivos recientes.
- `tests/`: 11 suites de pruebas unitarias automatizadas.
- `docs/`: Documentación técnica y funcional normativa.

## Documentación

Consulta el [índice documental completo](docs/README.md):

- [Arquitectura del sistema](docs/ARQUITECTURA_2026-09-07.md)
- [Especificación funcional y modelo de datos](docs/Study%20Timetrial%20%E2%80%94%20Especificaci%C3%B3n%20funcional%20y%20estructura%20de%20datos.md)
- [Contrato de persistencia JSON](docs/CONTRATO_JSON.md)
- [Guía de operación y validación](docs/OPERACION_Y_VALIDACION.md)

## Pruebas automatizadas

Para ejecutar la suite completa de 73 pruebas unitarias:

```powershell
python -m unittest discover -s tests -v
```
