# Especificación Técnica — Módulo de Exportación de Datos (CSV / Excel)

**Módulo:** `infrastructure/export_service.py`, `application/application_service.py`, `presentation/export_dialog.py`  
**Fecha:** 2026-09-25  
**Estado:** Especificación Técnica Aprobada (TASK-009)  

---

## 1. Propósito Funcional

El subsistema de exportación permite a los estudiantes volcar el historial de estudio y el análisis consolidado de la cursada a archivos tabulares estándar (`.csv`) compatibles al 100% con Microsoft Excel, Google Sheets, Calc y scripts de análisis en Python/R.

El módulo resuelve dos necesidades principales:
1. **Auditoría e Historial Detallado (Nivel Intento):** Cada registro de tiempo realizado se exporta como una fila con su marca temporal, ubicación curricular precisa, tiempos netos y de receso, estado de finalización, etiquetas de color asignadas y notas/apuntes.
2. **Reporte Resumen Consolidado (Nivel Guía / Ejercicio):** Agrupación curricular que consolida el esfuerzo por cada ejercicio e inciso planificado: total de intentos, tasa de éxito (% completado), tiempo total neto, tiempo promedio, mejor marca personal (*Personal Best*), etiquetas y apuntes actuales.

---

## 2. Compatibilidad y Estándar de Formato

### 2.1 RFC 4180 y Escape Seguro
- El archivo se genera siguiendo estrictamente las especificaciones de RFC 4180:
  - Campos con caracteres delimitadores, comillas dobles o saltos de línea se delimitan obligatoriamente entre comillas dobles (`"..."`).
  - Las comillas dobles dentro de textos se escapan duplicándolas (`""`).
  - Los saltos de línea multilínea en las notas se preservan fielmente sin alterar la estructura tabular.

### 2.2 Codificación y Compatibilidad con Microsoft Excel
- **Encoding `utf-8-sig` (UTF-8 con BOM `\xef\xbb\xbf`):** Garantiza que Microsoft Excel en Windows abra el archivo directamente con doble clic detectando automáticamente la codificación de caracteres, preservando tildes, caracteres especiales (`°`, `#`, `✓`, `✗`) y signos de puntuación sin requerir el asistente de importación manual.
- **Delimitadores soportados:**
  - `;` (Punto y coma - **Recomendado por defecto para entornos en español/latinoamericano**): Permite que Excel separe las columnas de inmediato en sistemas con coma decimal.
  - `,` (Coma - Estándar internacional): Para scripts en R/Pandas o sistemas en inglés.

---

## 3. Contratos de Entrada y Salida (DTOs e Interfaces)

### 3.1 DTOs en `infrastructure/export_service.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

@dataclass(frozen=True)
class ExportOptions:
    file_path: Path
    delimiter: str = ";"
    report_type: str = "detailed"  # "detailed" | "summary"
    include_notes: bool = True
    include_tags: bool = True

@dataclass(frozen=True)
class ExportResult:
    success: bool
    rows_exported: int
    file_path: Path
    error_message: str | None = None
```

### 3.2 Estructura de Columnas — Historial Detallado de Intentos
1. `Fecha`: `YYYY-MM-DD`
2. `Hora`: `HH:MM:SS`
3. `Fecha y Hora ISO`: `YYYY-MM-DDTHH:MM:SS`
4. `Guia / Seccion`: Nombre/tipo de sección (ej. "Guía", "TP")
5. `Numero Seccion`: Número entero
6. `Ejercicio`: Número de ejercicio
7. `Inciso`: Número de inciso o texto vacío si no posee
8. `Identificador`: Cadena de lectura rápida (ej: `Guía 1 · Ej. 2.1`)
9. `Estado`: `Completado` o `Incompleto`
10. `Tiempo Neto (hh:mm:ss)`: Formateado legible
11. `Tiempo Neto (s)`: Tiempo neto en segundos con decimales
12. `Tiempo Neto (ms)`: Milisegundos enteros
13. `Tiempo Descanso (hh:mm:ss)`: Tiempo de receso legible
14. `Tiempo Descanso (s)`: Receso en segundos
15. `Tiempo Total (hh:mm:ss)`: Suma de estudio + receso
16. `Etiquetas`: Lista de nombres de etiquetas separadas por ` | `
17. `Notas / Apuntes`: Texto de notas del ejercicio en la planificación
18. `Comentario Intento`: Comentario individual registrado en el intento específico

### 3.3 Estructura de Columnas — Resumen Consolidado por Ejercicio
1. `Guia / Seccion`: Tipo de sección
2. `Numero Seccion`: Número
3. `Ejercicio`: Ejercicio
4. `Inciso`: Inciso o vacío
5. `Identificador`: Ej: `Guía 1 · Ej. 2.1`
6. `Estado Resolucion`: `Resuelto`, `Incompleto` o `Sin Intentos`
7. `Total Intentos`: Conteo de intentos
8. `Intentos Completados`: Conteo de éxitos
9. `Intentos Incompletos`: Conteo de fallos/incompletos
10. `Tasa Exito (%)`: Porcentaje con 1 decimal
11. `Tiempo Total Neto (hh:mm:ss)`: Tiempo acumulado
12. `Tiempo Total Neto (s)`: Segundos acumulados
13. `Tiempo Promedio (hh:mm:ss)`: Promedio por intento
14. `Mejor Marca PB (hh:mm:ss)`: Récord personal más veloz
15. `Etiquetas`: Lista de nombres de etiquetas separadas por ` | `
16. `Notas / Apuntes`: Texto completo de la nota de planificación

---

## 4. Orquestación en la Capa de Aplicación (`StudyApplicationService`)

El servicio de aplicación expone:
- `export_items_to_csv(file_path: Path | str, items: Sequence[TimerItem] | None = None, delimiter: str = ";") -> ExportResult`:
  - Si `items` es `None`, exporta todos los registros del archivo en memoria (`self.record.items`).
  - Resuelve las etiquetas asociando los IDs a los nombres legibles mediante `record.tags` y `record.planner_sections`.
  - Resuelve las notas del planificador para cada ejercicio/inciso.
- `export_summary_to_csv(file_path: Path | str, delimiter: str = ";") -> ExportResult`:
  - Recorre las secciones planificadas y ejercicios con intentos, calculando las métricas consolidadas.
  - Invoca la infraestructura de persistencia tabular.

---

## 5. Capa de Presentación: Diálogo `ExportDialog`

### 5.1 Ubicación e Interacciones
- Accesible desde:
  1. Barra de herramientas de Registros (`RecordsViewWidget`): Botón `[ 📤 Exportar ]`.
  2. Menú de aplicación: `Archivo` > `Exportar datos (CSV)...`.
  3. Pestaña de Estadísticas: Botón de cabecera `[ 📤 Exportar Datos ]`.
- Diálogo modal `ExportDialog`:
  - **Selector de Tipo de Reporte:** Radio buttons para `Historial detallado de intentos` o `Resumen consolidado por guía y ejercicios`.
  - **Selector de Alcance:**
    - *Todos los registros*
    - *Solo registros visibles/filtrados* (disponible cuando se invoca desde Registros).
    - *Rango de fechas* (con selectores de fecha `QDateEdit` interactivos).
  - **Selector de Formato:** Delimitador `;` (recomendado para Excel en español) o `,` (estándar).
  - **Selector de Ruta de Guardado:** `QLineEdit` con botón de exploración `[Examinar...]` (`QFileDialog.getSaveFileName`).
  - **Botones de Acción:** `[Cancelar]` y `[ 📤 Exportar ]`.
  - Tras la exportación exitosa, muestra mensaje con botón para `[ Abrir carpeta contenedora ]` (`QDesktopServices.openUrl`).

---

## 6. Manejo Seguro de Excepciones
- Si el archivo destino se encuentra bloqueado por otra aplicación (ej: abierto en Microsoft Excel), se captura `PermissionError` y se informa con un mensaje amigable sugiriendo cerrar el archivo antes de reintentar.
- Manejo atómico y seguro: Si ocurre cualquier fallo durante la escritura, se limpia cualquier archivo parcial incompleto.
