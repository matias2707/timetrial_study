# Study Timetrial

Aplicación de escritorio local desarrollada en Python y PySide6 para cronometrar ejercicios de estudio, registrar intentos, analizar estadísticas de rendimiento y planificar guías de estudio completas en archivos JSON.

## Características principales

- **Cronómetro de alta precisión:** Reloj digital monotónico con tiempos netos de ejercicio y descanso, controles de sesión y notas inmediatas.
- **Tabla de Registros analítica:** Filtros interactivos emergentes estilo Excel, ordenamiento múltiple jerárquico, reordenamiento de columnas, búsqueda global, KPI cards y badges de estado.
- **Panel de Estadísticas:** Resumen de métricas acumuladas, gráfico semanal de dedicación renderizado en alta resolución antialiasing y análisis desagregado por sección.
- **Planificador de estudio:** Estructuración previa de guías académicas con ejercicios simples y compuestos (incisos), pesos ponderados de completitud (`completed_weight`) y carga directa al cronómetro.
- **Resolución de desfasaje de incisos:** Pausa automática del cronómetro y diálogo modal inteligente ante detección de intentos previos sin clasificar.
- **Temas y Audio:** Soporte instantáneo para **Modo Claro** y **Modo Oscuro**, y notificaciones sonoras con opción de silencio.
- **Icono e identidad visual:** Icono de aplicación en forma de cronómetro con paquete multi-resolución (`app_icon.ico` nativo para Windows y `app_icon.png` en alta definición) y configuración explícita de `AppUserModelID` para anclaje correcto en la barra de tareas.
- **Persistencia local y segura:** Archivos JSON atómicos y portables (esquema versión `1`), sin dependencia de servicios en la nube ni bases de datos externas.

## Inicio rápido

En PowerShell o terminal, desde la raíz del proyecto:

```powershell
python -m pip install -r requirements.txt
python main.py
```

La primera ejecución crea un registro local automático en `data/records/StudyTimetrial_YYYYMMDD.json` o permite elegir un archivo nuevo o reciente.

## Estructura del proyecto

- `main.py`: Punto de entrada que configura el modelo de usuario de Windows (`AppUserModelID`), inicializa `QApplication`, carga el icono oficial y levanta la ventana principal.
- `presentation/`: Interfaz visual modular en PySide6:
  - `main_window.py`: Ventana principal (Lean Shell), orquestador de pestañas y despachador de eventos.
  - `app_toolbar.py`: Barra de herramientas superior desacoplada con menús de Archivo y Configuración.
  - `audio_service.py`: Servicio de audio desacoplado para reproducción de sonidos y control de silenciamiento.
  - `home_view.py`: Vista modular del Cronómetro (`HomeViewWidget`) con relojes digitales y controles de intento.
  - `records_view.py`: Vista modular de Registros (`RecordsViewWidget`) con tabla interactiva y filtros.
  - `statistics_view.py`: Vista modular de Estadísticas (`StatisticsViewWidget`) con métricas agregadas y desglose.
  - `weekly_chart_widget.py`: Gráfico semanal de barras personalizado renderizado con `QPainter`.
  - `planner_widget.py` y `planner_dialogs.py`: Interfaz y diálogos del Planificador.
  - `excel_filter_popup.py`: Menú de filtro y ordenamiento avanzado tipo Excel.
  - `inciso_dialog.py`: Diálogo modal de resolución guiada de desfasajes de incisos.
  - `theme_tokens.py`: Definición tipada de tokens de diseño semánticos (`ThemeTokens`) para Modo Claro y Oscuro.
  - `theme.py`: Motor paramétrico de generación de hojas de estilo QSS a partir de tokens de diseño.
  - `presentation_dialogs.py` y `presentation_formatters.py`: Diálogos y adaptadores de tiempo.
  - `media/`: Efectos de sonido de notificación (`.wav`) e iconos oficiales de la aplicación (`app_icon.ico`, `app_icon.png`, `stopwatch_vector.svg`).
- `application/`: Casos de uso desacoplados de bibliotecas gráficas:
  - `application_service.py`: Fachada principal de coordinación (`StudyApplicationService`).
  - `planner_service.py`: Lógica de análisis de avance, pesos y límites del planificador.
  - `statistics_service.py`: Procesamiento analítico y agregaciones temporales.
  - `record_query.py`: Filtrado multicriterio y ordenamiento jerárquico de registros.
- `domain/`: Reglas de negocio y entidades fundamentales:
  - `models.py`: Entidades `TimerItem`, `PlannedSection` y `Record`.
  - `timer_service.py`: Reloj monotónico de precisión con modos `WAITING`, `PLAY` y `BREAK`.
- `infrastructure/`:
  - `storage_service.py`: Persistencia JSON, resolución de directorios y gestión del índice de archivos recientes.
- `data/`: Almacén estructurado de datos de aplicación (fuera del código fuente):
  - `records/`: Registros de sesiones de estudio diarios (`StudyTimetrial_YYYYMMDD.json`).
  - `samples/`: Datasets de ejemplo y demostración (`Algebra_Demo.json`).
  - `.study_timetrial_recent.json`: Registro de archivos de estudio recientes.
- `tests/`: 12 suites de pruebas unitarias automatizadas.
- `docs/`: Documentación técnica y funcional normativa.

## Documentación

Consulta el [índice documental completo](docs/README.md):

- [Arquitectura general del sistema](docs/ARQUITECTURA_2026-09-07.md)
- [Arquitectura de la capa de presentación](docs/ARQUITECTURA_PRESENTACION.md)
- [Especificación funcional y modelo de datos](docs/Study%20Timetrial%20%E2%80%94%20Especificaci%C3%B3n%20funcional%20y%20estructura%20de%20datos.md)
- [Contrato de persistencia JSON](docs/CONTRATO_JSON.md)
- [Guía de operación y validación](docs/OPERACION_Y_VALIDACION.md)

## Pruebas automatizadas

Para ejecutar la suite completa de 76 pruebas unitarias:

```powershell
python -m unittest discover -s tests -v
```
