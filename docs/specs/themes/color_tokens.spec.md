# Especificación Técnica: Diccionario y Tokens Cromáticos (Theme Tokens)

**Identificador:** `THEME-SPEC-001`  
**Capa de Referencia:** `presentation/theme_tokens.py` / `data/themes/`  
**Estado:** Invariante / Producción  

---

## 1. Propósito
Definir el contrato de nombres y semántica de los tokens de color requeridos para cualquier tema visual de **Study Timetrial**. Permite que cualquier archivo de tema en formato JSON declare exclusivamente valores de color y sea interpretado dinámicamente por la aplicación.

---

## 2. Grupos de Tokens Semánticos

Cada tema JSON debe definir las siguientes variables en formato hexadecimal (`#RRGGBB` o `#AARRGGBB`):

### A. Superficies Base y Fondos (`bg_*`)
* `bg_app`: Fondo de la ventana principal.
* `bg_dialog`: Fondo para modales y cuadros de diálogo.
* `bg_surface`, `bg_surface_alt`: Paneles de contenido y tarjetas secundarias.
* `bg_card`, `bg_card_inner`: Contenedores elevados y tarjetas de métricas.
* `bg_clock_card`: Fondo exclusivo de la tarjeta del reloj principal.
* `bg_tab_bar`, `bg_tab_active`: Pestañas de navegación.
* `bg_input`, `bg_input_focus`, `bg_input_disabled`: Cajas de texto, inputs numéricos.
* `bg_button`, `bg_button_hover`, `bg_button_pressed`: Botones estándar.

### B. Tablas y Filtros
* `bg_table`, `bg_table_alt`, `bg_table_header`: Colores de filas, alternancia y cabecera.
* `table_gridline`: Color de las líneas de cuadrícula.
* `table_selection_bg`, `table_selection_fg`: Elementos seleccionados en la tabla.
* `popup_bg`, `popup_border`, `popup_title_fg`: Ventana emergente de filtros Excel.

### C. Textos y Tipografías (`text_*`)
* `text_primary`: Texto principal legible de alto contraste.
* `text_secondary`: Subtítulos y etiquetas descriptivas.
* `text_muted`, `text_faint`: Metadatos, atajos y leyendas secundarias.
* `text_disabled`: Elementos deshabilitados.
* `text_clock_exercise`: Color de los dígitos del cronómetro de estudio.
* `text_clock_break`: Color de los dígitos del contador de receso.

### D. Acciones Semánticas (Hero Buttons & Badges)
* `hero_start_*`: Botón principal de Iniciar sesión.
* `hero_break_*`: Botón de Pausa / Receso.
* `hero_complete_*`: Botón de Finalizar éxito (`Enter`).
* `hero_incomplete_*`: Botón de Finalizar incompleto (`Esc`).
* `status_pill_*`: Píldoras de estado (`completed`, `failed`, `pending`).
* `accent_primary`, `accent_secondary`: Colores de realce de marca.

---

## 3. Formato de Archivo de Tema (`data/themes/<nombre>.json`) y Validación

Los temas se definen como objetos JSON planos validados contra `data/themes/theme.schema.json`:

```json
{
  "$schema": "./theme.schema.json",
  "name": "dark",
  "is_dark": true,
  "mode_comment": "/* Modo Oscuro Ergonómico */",
  "bg_app": "#0b0f17",
  "bg_dialog": "#121824",
  "bg_surface": "#121824",
  "text_primary": "#e2e8f0",
  "text_secondary": "#94a3b8",
  "text_muted": "#64748b",
  "border_subtle": "#1e293b",
  "border_strong": "#334155",
  "toolbar_primary_bg": "#059669",
  "hero_start_bg": "#059669"
}
```

Cualquier archivo `.json` depositado en `data/themes/` (excluyendo `theme.schema.json`) es descubierto y cargado dinámicamente por `presentation/theming/theme_loader.py`.
