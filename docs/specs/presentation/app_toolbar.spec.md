# Especificación Técnica: Barra de Herramientas Principal (AppToolbar)

**Identificador:** `UI-TOOLBAR-001`  
**Capa de Referencia:** `presentation/app_toolbar.py`  
**Patrón:** Passive View (MVP) / QToolBar  
**Estado:** Invariante / Producción  

---

## 1. Propósito y Filosofía de Diseño

La barra de herramientas (`AppToolbar`) provee acceso ergonómico e inmediato a las operaciones de archivo, historial de edición y utilidades globales de **Study Timetrial**.

Siguiendo las convenciones de diseño UX/UI de software profesional de edición (suites como VS Code, Premiere, Blender o Notepad++), implementa una **distribución compacta en dos niveles (two-tier layout)** compuesta exclusivamente por **botones rectangulares** con texto e icono (`ToolButtonTextBesideIcon`), eliminando botones cuadrados aislados para maximizar la legibilidad y densidad de información:

1. **Nivel 1 (Menús Principales - Fila Superior):**
   - Agrupa los menús desplegables principales alineados a la izquierda: `Archivo`, `Edición` y `Configuración`.
   - Dimensiones reducidas (`min-height: 22px; max-height: 22px; font-size: 11px`) con comportamiento plano y feedback hover sutil.
2. **Nivel 2 (Acciones Rápidas - Fila Inferior):**
   - Dispone las acciones operativas más frecuentes en orden secuencial estandarizado de ciclo de vida de documento:
     - **Gestión de Archivo:** `Nuevo` (`Ctrl+N`), `Abrir` (`Ctrl+O`), `Guardar` (`Ctrl+S`), `Guardar como` (`Ctrl+Shift+S`).
     - **Divisor visual:** Separador vertical de 1px.
     - **Historial de Modificaciones:** `Deshacer` (`Ctrl+Z`), `Rehacer` (`Ctrl+Y`).
   - Dimensiones compactas tipo editor (`min-height: 20px; max-height: 22px; font-size: 11px; padding: 2px 7px`).

---

## 2. Mapa de Componentes y Jerarquía Visual

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Nivel 1: [📁 Archivo ▾] [✏️ Edición ▾] [⚙️ Configuración ▾] ── (Espaciador Flexible) ──  │
│ Nivel 2: [📄 Nuevo] [📂 Abrir] [💾 Guardar] [💾 Guardar como] │ [↩️ Deshacer] [↪️ Rehacer]│
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Componentes de Nivel 1 (Menús Principales)

| Componente | Selector CSS | Función / Comportamiento |
| :--- | :--- | :--- |
| `file_button` | `QToolButton#file_toolbar_button` | Despliega menú Archivo (Nuevo, Abrir, Recientes, Guardar, Guardar como, Exportar, Cerrar). |
| `edit_button` | `QToolButton#edit_toolbar_button` | Despliega menú Edición (Deshacer, Rehacer con etiquetas dinámicas). |
| `config_button` | `QToolButton#config_toolbar_button` | Despliega menú Configuración (Catálogo de skins dinámicos, Pantone, sonidos y auto-apertura). |

### 2.2 Componentes de Nivel 2 (Acciones Rápidas)

| Componente | Selector CSS | Acción / Función | Atajo Teclado |
| :--- | :--- | :--- | :--- |
| `quick_new_button` | `QToolButton#quick_new_button` | Crea un nuevo registro de cronometraje. | `Ctrl+N` |
| `quick_open_button` | `QToolButton#quick_open_button` | Abre el selector de archivos locales (`.json`). | `Ctrl+O` |
| `quick_save_button` | `QToolButton#quick_save_button` | Guardado directo reactivo al estado sucio (`is_dirty`). | `Ctrl+S` |
| `quick_save_as_button` | `QToolButton#quick_save_as_button` | Guarda una copia del registro en una nueva ubicación. | `Ctrl+Shift+S` |
| `sep` | `QFrame#toolbar_row_separator` | Línea divisoria vertical entre ciclo de archivo e historial. | - |
| `quick_undo_button` | `QToolButton#quick_undo_button` | Revierte la última acción registrada en `UndoManager`. | `Ctrl+Z` |
| `quick_redo_button` | `QToolButton#quick_redo_button` | Rehace la última acción deshecha. | `Ctrl+Y` |

### 2.3 Contenedor, Estructura Interna y Prevención de Superposiciones

* `toolbar_container` (`QWidget#toolbar_container`): Widget contenedor interno con un `QVBoxLayout` (márgenes `0, 1, 0, 2`, espaciado `2px`), insertado dentro del `QToolBar` raíz mediante `self.addWidget(...)`. Es el **único elemento visual alojado directamente en el `QToolBar`**, garantizando compatibilidad total con `QMainWindow.addToolBar(...)`.
* `menu_row` (`QWidget#toolbar_menu_row`): `QHBoxLayout` de nivel superior con espaciado de `2px` y `addStretch()` a la derecha que aloja los botones de menú.
* `actions_row` (`QWidget#toolbar_actions_row`): `QHBoxLayout` de nivel inferior con espaciado de `3px` y `addStretch()` a la derecha que aloja las acciones rápidas rectangulares.
* **Registro Limpio de Atajos de Teclado:** Las acciones de documento (`Ctrl+N`, `Ctrl+O`, `Ctrl+S`, `Ctrl+Shift+S`, `Ctrl+W`, `Ctrl+Q`, `Ctrl+Z`, `Ctrl+Y`) se registran en `toolbar_container` (o en `MainWindow`) con `Qt.ShortcutContext.WindowShortcut`. Se prohíbe invocar `self.addAction(...)` sobre el `QToolBar`, ya que Qt crearía botones gráficos anónimos redundantes en el extremo derecho.
* **Aislamiento de Retrocompatibilidad:** Los controles legados (`quick_sound_button`, `quick_theme_button`, `spacer`) se inicializan sin `parent` y en estado oculto (`hide()`), imposibilitando que Qt los pinte en las coordenadas `(0, 0)` sobre el botón `Archivo`.

---

## 3. Contratos de Eventos y Señales

La clase `AppToolbar` opera como una **Passive View pura**. No ejecuta lógica de persistencia, I/O ni altera estados globales; únicamente canaliza eventos de usuario mediante señales Qt hacia el Presenter y la ventana principal:

```python
request_new_record = Signal()
request_open_record = Signal()
request_open_recent = Signal(Path)
request_save = Signal()
request_save_as = Signal()
request_export = Signal()
request_close_record = Signal()
request_close_app = Signal()
request_theme_change = Signal(str)
request_toggle_sound = Signal()
request_toggle_auto_open = Signal(bool)
request_undo = Signal()
request_redo = Signal()
```

---

## 4. Métodos de Actualización Declarativa

* `update_save_action(is_record_open: bool, is_dirty: bool) -> None`:  
  Sincroniza la disponibilidad reactiva de `save_action`, `quick_save_button` y `quick_save_as_button`.
  - Si no hay registro abierto: `quick_save_button` deshabilitado con tooltip `"Guardar (No hay archivo abierto)"`.
  - Si hay registro abierto pero sin cambios: `quick_save_button` deshabilitado con tooltip `"Sin cambios pendientes (Ctrl+S)"`.
  - Si hay registro abierto con cambios: `quick_save_button` habilitado con tooltip `"Guardar cambios pendientes (Ctrl+S)"`.
* `update_undo_redo_actions(can_undo: bool, can_redo: bool, undo_text: str, redo_text: str) -> None`:  
  Habilita/deshabilita `quick_undo_button` y `quick_redo_button`, actualizando dinámicamente sus tooltips descriptivos contextuales.
* `set_record_actions_enabled(enabled: bool) -> None`:  
  Control maestro de activación para todos los controles que exigen un archivo cargado en memoria (`save`, `save_as`, `export`, `close`, `undo`, `redo`).
* `update_sound_action(is_muted: bool) -> None`:  
  Sincroniza el menú de configuración de audio con el icono de estado (volumen alto / silenciado).
* `set_current_theme(theme: str) -> None`:  
  Marca el tema activo en el catálogo y refresca los estados visuales asociados.
* `update_theme_icons(is_dark: bool) -> None`:  
  Sincroniza la totalidad de los iconos de la barra (tanto de menús como de acciones de Nivel 1 y Nivel 2) con los tokens de color del tema activo (`tokens.toolbar_btn_fg`).
* `populate_recent_files(recent_paths: list[Path], on_open_file: Callable, on_select_recent: Callable) -> None`:  
  Reconstruye reactivamente la lista de archivos recientes en el submenú de Archivo.
