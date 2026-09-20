"""Tokens de diseño para temas visuales (Modo Claro y Modo Oscuro) de Study Timetrial."""

from __future__ import annotations

from dataclasses import dataclass

THEME_LIGHT = "light"
THEME_DARK = "dark"


@dataclass(frozen=True)
class ThemeTokens:
    """Conjunto de tokens cromáticos y semánticos para un tema visual."""

    name: str
    is_dark: bool
    mode_comment: str

    # Superficies y fondos base
    bg_app: str
    bg_dialog: str
    bg_surface: str
    bg_surface_alt: str
    bg_card: str
    bg_card_inner: str
    bg_clock_card: str
    bg_tab_bar: str
    bg_tab_active: str
    bg_location_badge: str
    bg_status_badge: str
    bg_input: str
    bg_input_focus: str
    bg_input_disabled: str
    bg_button: str
    bg_button_hover: str
    bg_button_pressed: str
    bg_stepper_pressed: str
    bg_secondary_action: str
    bg_secondary_hover: str

    # Tablas y listas
    bg_table: str
    bg_table_alt: str
    bg_table_header: str
    table_gridline: str
    table_selection_bg: str
    table_selection_fg: str
    bg_list: str
    list_item_hover: str
    list_item_selected_bg: str
    list_item_selected_fg: str

    # Desplegables (ComboBox) y Filtros
    bg_filter_panel: str
    bg_combobox: str
    combobox_fg: str
    combobox_hover_bg: str
    combobox_focus_border: str
    combobox_dropdown_bg: str
    combobox_dropdown_fg: str
    combobox_dropdown_sel_bg: str
    combobox_dropdown_sel_fg: str
    filter_reset_bg: str
    filter_reset_fg: str
    filter_reset_hover_bg: str
    filter_reset_hover_fg: str
    filter_reset_hover_border: str
    sort_dir_btn_bg: str
    sort_dir_btn_fg: str
    sort_dir_btn_hover_bg: str
    sort_dir_btn_hover_border: str

    # Excel Filter Popup
    popup_bg: str
    popup_border: str
    popup_title_fg: str
    popup_btn_bg: str
    popup_btn_fg: str
    popup_btn_border: str
    popup_btn_hover_bg: str
    popup_btn_hover_border: str
    popup_btn_hover_fg: str
    popup_sep: str
    popup_list_bg: str
    popup_list_border: str
    popup_list_hover: str

    # Toolbars y Menús
    bg_toolbar: str
    toolbar_border: str
    toolbar_btn_bg: str
    toolbar_btn_fg: str
    toolbar_btn_border: str
    toolbar_btn_hover_bg: str
    toolbar_btn_hover_border: str
    toolbar_btn_hover_fg: str
    toolbar_btn_pressed: str
    toolbar_primary_bg: str
    toolbar_primary_fg: str
    toolbar_primary_border: str
    toolbar_primary_hover_bg: str
    toolbar_primary_hover_fg: str
    menu_bg: str
    menu_fg: str
    menu_border: str
    menu_item_fg: str
    menu_item_sel_bg: str
    menu_item_sel_fg: str
    menu_item_disabled: str
    menu_separator: str

    # Bordes generales
    border_subtle: str
    border_strong: str
    border_focus: str
    border_disabled: str
    card_border: str
    hero_card_top: str

    # Tipografía / Textos
    text_primary: str
    text_heading: str
    text_secondary: str
    text_muted: str
    text_faint: str
    text_disabled: str
    text_checkbox: str
    text_clock_exercise: str
    text_clock_break: str
    tab_text: str
    tab_text_selected: str

    # Acciones principales del cronómetro (Hero Buttons)
    hero_start_bg: str
    hero_start_fg: str
    hero_start_border: str
    hero_start_hover_bg: str
    hero_start_hover_border: str
    hero_start_hover_fg: str

    hero_pause_bg: str
    hero_pause_fg: str
    hero_pause_border: str
    hero_pause_hover_bg: str
    hero_pause_hover_border: str

    hero_resume_bg: str
    hero_resume_fg: str
    hero_resume_border: str
    hero_resume_hover_bg: str
    hero_resume_hover_border: str

    stop_bg: str
    stop_fg: str
    stop_border: str
    stop_hover_bg: str
    stop_hover_border: str

    complete_bg: str
    complete_fg: str
    complete_border: str
    complete_hover_bg: str

    danger_bg: str
    danger_fg: str
    danger_border: str
    danger_hover_bg: str

    comment_action_bg: str
    comment_action_fg: str
    comment_action_border: str
    comment_action_hover_bg: str
    comment_action_hover_border: str
    comment_action_hover_fg: str

    # Badges de tabla
    badge_completed_bg: str
    badge_completed_fg: str
    badge_completed_border: str

    badge_incomplete_bg: str
    badge_incomplete_fg: str
    badge_incomplete_border: str

    # Barra de progreso y barras de scroll
    progress_bg: str
    progress_border: str
    progress_fg: str
    progress_chunk: str
    scroll_bg: str
    scroll_handle: str
    scroll_handle_hover: str

    # Tooltip
    tooltip_bg: str
    tooltip_fg: str
    tooltip_border: str


DARK_TOKENS = ThemeTokens(
    name=THEME_DARK,
    is_dark=True,
    mode_comment="/* --- MODO OSCURO (ERGONÓMICO & ANTI-HALACIÓN) --- */",
    # Superficies con elevación por luminancia
    bg_app="#0b0f17",             # Deep slate navy relajante (sin negros absolutos #000000)
    bg_dialog="#1e293b",          # Slate 800 para modales flotantes elevados
    bg_surface="#111827",         # Superficie base elevada
    bg_surface_alt="#0f172a",     # Alternativo para paneles secundarios
    bg_card="#111827",            # Tarjetas contenedoras (Nivel 1)
    bg_card_inner="#162032",      # Contenedores anidados (Nivel 2, sin efecto agujero negro)
    bg_clock_card="#162032",      # Marco de reloj digital: fondo elevado distinguible
    bg_tab_bar="#080c14",         # Barra superior integrada y profunda
    bg_tab_active="#111827",      # Pestaña activa conectada al fondo del contenido
    bg_location_badge="#0f172a",
    bg_status_badge="#1e293b",
    bg_input="#0b0f17",
    bg_input_focus="#162032",
    bg_input_disabled="#111827",
    bg_button="#1e293b",
    bg_button_hover="#283548",
    bg_button_pressed="#172033",
    bg_stepper_pressed="#162032",
    bg_secondary_action="#1e293b",
    bg_secondary_hover="#283548",
    # Tablas y listas
    bg_table="#0f172a",
    bg_table_alt="#111827",
    bg_table_header="#0b0f17",
    table_gridline="#1e293b",
    table_selection_bg="#1e293b",
    table_selection_fg="#f8fafc",
    bg_list="#0b0f17",
    list_item_hover="#1e293b",
    list_item_selected_bg="#1e293b",
    list_item_selected_fg="#34d399",
    # Desplegables y Filtros
    bg_filter_panel="#0e1526",
    bg_combobox="#111827",
    combobox_fg="#e2e8f0",
    combobox_hover_bg="#1a2436",
    combobox_focus_border="#10b981",
    combobox_dropdown_bg="#0f172a",
    combobox_dropdown_fg="#f1f5f9",
    combobox_dropdown_sel_bg="#1e293b",
    combobox_dropdown_sel_fg="#34d399",
    filter_reset_bg="#1e293b",
    filter_reset_fg="#94a3b8",
    filter_reset_hover_bg="#334155",
    filter_reset_hover_fg="#f8fafc",
    filter_reset_hover_border="#64748b",
    sort_dir_btn_bg="#1e293b",
    sort_dir_btn_fg="#34d399",
    sort_dir_btn_hover_bg="#283548",
    sort_dir_btn_hover_border="#10b981",
    # Excel Popup
    popup_bg="#0f172a",
    popup_border="#334155",
    popup_title_fg="#34d399",
    popup_btn_bg="#111827",
    popup_btn_fg="#e2e8f0",
    popup_btn_border="#1e293b",
    popup_btn_hover_bg="#1e293b",
    popup_btn_hover_border="#38bdf8",
    popup_btn_hover_fg="#ffffff",
    popup_sep="#1e293b",
    popup_list_bg="#0b0f17",
    popup_list_border="#1e293b",
    popup_list_hover="#1e293b",
    # Toolbars y Menús
    bg_toolbar="#0e1524",
    toolbar_border="#1e293b",
    toolbar_btn_bg="#1e293b",
    toolbar_btn_fg="#e2e8f0",
    toolbar_btn_border="#334155",
    toolbar_btn_hover_bg="#283548",
    toolbar_btn_hover_border="#10b981",
    toolbar_btn_hover_fg="#ffffff",
    toolbar_btn_pressed="#172033",
    toolbar_primary_bg="#065f46",
    toolbar_primary_fg="#ecfdf5",
    toolbar_primary_border="#059669",
    toolbar_primary_hover_bg="#047857",
    toolbar_primary_hover_fg="#ffffff",
    menu_bg="#0f172a",
    menu_fg="#f1f5f9",
    menu_border="#1e293b",
    menu_item_fg="#e2e8f0",
    menu_item_sel_bg="#1e293b",
    menu_item_sel_fg="#34d399",
    menu_item_disabled="#475569",
    menu_separator="#1e293b",
    # Bordes
    border_subtle="#1e293b",
    border_strong="#334155",
    border_focus="#10b981",
    border_disabled="#1f2937",
    card_border="#1e293b",
    hero_card_top="#10b981",
    # Tipografía (Anti-Halación)
    text_primary="#f1f5f9",       # Blanco roto suave (evita halación)
    text_heading="#f8fafc",
    text_secondary="#cbd5e1",
    text_muted="#94a3b8",
    text_faint="#64748b",
    text_disabled="#475569",
    text_checkbox="#f1f5f9",
    text_clock_exercise="#f1f5f9",
    text_clock_break="#94a3b8",
    tab_text="#94a3b8",
    tab_text_selected="#10b981",
    # Hero timer action buttons
    hero_start_bg="#065f46",
    hero_start_fg="#ecfdf5",
    hero_start_border="#059669",
    hero_start_hover_bg="#047857",
    hero_start_hover_border="#047857",
    hero_start_hover_fg="#ffffff",
    hero_pause_bg="#451a03",
    hero_pause_fg="#fde68a",
    hero_pause_border="#78350f",
    hero_pause_hover_bg="#78350f",
    hero_pause_hover_border="#b45309",
    hero_resume_bg="#064e3b",
    hero_resume_fg="#a7f3d0",
    hero_resume_border="#065f46",
    hero_resume_hover_bg="#065f46",
    hero_resume_hover_border="#10b981",
    stop_bg="#450a0a",
    stop_fg="#fca5a5",
    stop_border="#7f1d1d",
    stop_hover_bg="#7f1d1d",
    stop_hover_border="#991b1b",
    complete_bg="#064e3b",
    complete_fg="#6ee7b7",
    complete_border="#059669",
    complete_hover_bg="#065f46",
    danger_bg="#450a0a",
    danger_fg="#fca5a5",
    danger_border="#7f1d1d",
    danger_hover_bg="#5c1010",
    comment_action_bg="#1e293b",
    comment_action_fg="#e2e8f0",
    comment_action_border="#334155",
    comment_action_hover_bg="#283548",
    comment_action_hover_border="#10b981",
    comment_action_hover_fg="#ffffff",
    # Badges
    badge_completed_bg="#064e3b",
    badge_completed_fg="#6ee7b7",
    badge_completed_border="#059669",
    badge_incomplete_bg="#450a0a",
    badge_incomplete_fg="#fca5a5",
    badge_incomplete_border="#7f1d1d",
    # Progreso y scroll
    progress_bg="#111827",
    progress_border="#1e293b",
    progress_fg="#f8fafc",
    progress_chunk="#10b981",
    scroll_bg="#0b0f17",
    scroll_handle="#1e293b",
    scroll_handle_hover="#334155",
    # Tooltip
    tooltip_bg="#1e293b",
    tooltip_fg="#f8fafc",
    tooltip_border="#334155",
)


LIGHT_TOKENS = ThemeTokens(
    name=THEME_LIGHT,
    is_dark=False,
    mode_comment="/* --- MODO CLARO (CÁLIDO PAPEL / HUESO / CREMA) --- */",
    # Superficies tono papel natural y hueso mate descansado
    bg_app="#f7f4ed",             # Lienzo tono papel marfil cálido (sin deslumbramiento)
    bg_dialog="#fdfcf7",          # Tarjeta modal crema / hueso elevada
    bg_surface="#fdfcf7",         # Superficie crema suave
    bg_surface_alt="#f5f1e8",     # Hueso medio para contenedores interiores
    bg_card="#fdfcf7",            # Tarjetas elevadas crema / hueso
    bg_card_inner="#f5f1e8",      # Cajas anidadas tono hueso
    bg_clock_card="#fdfcf7",      # Marco de reloj digital: crema suave integrado
    bg_tab_bar="#ede8dd",         # Barra superior tono papel encuadernado
    bg_tab_active="#fdfcf7",      # Pestaña activa crema conectada a la vista
    bg_location_badge="#f5f1e8",
    bg_status_badge="#ede8dd",
    bg_input="#fdfcf7",
    bg_input_focus="#ffffff",
    bg_input_disabled="#ede8dd",
    bg_button="#fdfcf7",
    bg_button_hover="#f5f1e8",
    bg_button_pressed="#e7e1d5",
    bg_stepper_pressed="#e7e1d5",
    bg_secondary_action="#fdfcf7",
    bg_secondary_hover="#f5f1e8",
    # Tablas y listas
    bg_table="#fdfcf7",
    bg_table_alt="#f9f6ef",
    bg_table_header="#ede8dd",
    table_gridline="#e4ded4",
    table_selection_bg="#f1eadb", # Resaltado pergamino cálido
    table_selection_fg="#1c1917",
    bg_list="#fdfcf7",
    list_item_hover="#f5f1e8",
    list_item_selected_bg="#f1eadb",
    list_item_selected_fg="#047857",
    # Desplegables y Filtros
    bg_filter_panel="#f7f4ed",
    bg_combobox="#fdfcf7",
    combobox_fg="#1c1917",
    combobox_hover_bg="#f5f1e8",
    combobox_focus_border="#059669",
    combobox_dropdown_bg="#fdfcf7",
    combobox_dropdown_fg="#1c1917",
    combobox_dropdown_sel_bg="#e7f4ec",
    combobox_dropdown_sel_fg="#047857",
    filter_reset_bg="#ede8dd",
    filter_reset_fg="#57534e",
    filter_reset_hover_bg="#e2dcce",
    filter_reset_hover_fg="#1c1917",
    filter_reset_hover_border="#d5cdbf",
    sort_dir_btn_bg="#ede8dd",
    sort_dir_btn_fg="#047857",
    sort_dir_btn_hover_bg="#e2dcce",
    sort_dir_btn_hover_border="#059669",
    # Excel Popup
    popup_bg="#fdfcf7",
    popup_border="#d5cdbf",
    popup_title_fg="#1c1917",
    popup_btn_bg="#f7f4ed",
    popup_btn_fg="#44403c",
    popup_btn_border="#d5cdbf",
    popup_btn_hover_bg="#ede8dd",
    popup_btn_hover_border="#0284c7",
    popup_btn_hover_fg="#1c1917",
    popup_sep="#e4ded4",
    popup_list_bg="#fdfcf7",
    popup_list_border="#d5cdbf",
    popup_list_hover="#f5f1e8",
    # Toolbars y Menús
    bg_toolbar="#fdfcf7",
    toolbar_border="#e4ded4",
    toolbar_btn_bg="#fdfcf7",
    toolbar_btn_fg="#292524",
    toolbar_btn_border="#d5cdbf",
    toolbar_btn_hover_bg="#f5f1e8",
    toolbar_btn_hover_border="#059669",
    toolbar_btn_hover_fg="#1c1917",
    toolbar_btn_pressed="#ede8dd",
    toolbar_primary_bg="#059669",
    toolbar_primary_fg="#ffffff",
    toolbar_primary_border="#047857",
    toolbar_primary_hover_bg="#047857",
    toolbar_primary_hover_fg="#ffffff",
    menu_bg="#fdfcf7",
    menu_fg="#1c1917",
    menu_border="#d5cdbf",
    menu_item_fg="#292524",
    menu_item_sel_bg="#e7f4ec",
    menu_item_sel_fg="#047857",
    menu_item_disabled="#a8a29e",
    menu_separator="#e4ded4",
    # Bordes
    border_subtle="#e4ded4",
    border_strong="#d5cdbf",
    border_focus="#059669",
    border_disabled="#e4ded4",
    card_border="#e4ded4",
    hero_card_top="#059669",
    # Tipografía
    text_primary="#1c1917",       # Warm Charcoal / Stone 900 (tinta cálida, contraste 15.6:1)
    text_heading="#1c1917",
    text_secondary="#44403c",     # Stone 700 (contraste 8.5:1)
    text_muted="#78716c",         # Stone 500 (contraste 4.8:1 WCAG AA)
    text_faint="#a8a29e",
    text_disabled="#a8a29e",
    text_checkbox="#1c1917",
    text_clock_exercise="#1c1917",
    text_clock_break="#78716c",
    tab_text="#78716c",
    tab_text_selected="#047857",
    # Hero buttons
    hero_start_bg="#059669",
    hero_start_fg="#ffffff",
    hero_start_border="#047857",
    hero_start_hover_bg="#047857",
    hero_start_hover_border="#047857",
    hero_start_hover_fg="#ffffff",
    hero_pause_bg="#fbf4dc",
    hero_pause_fg="#b45309",
    hero_pause_border="#f2dd9b",
    hero_pause_hover_bg="#f8eec4",
    hero_pause_hover_border="#d97706",
    hero_resume_bg="#e7f4ec",
    hero_resume_fg="#047857",
    hero_resume_border="#b6e1c6",
    hero_resume_hover_bg="#d4ecdc",
    hero_resume_hover_border="#059669",
    stop_bg="#fae9e9",
    stop_fg="#b91c1c",
    stop_border="#f4bcbc",
    stop_hover_bg="#f7dcdc",
    stop_hover_border="#b91c1c",
    complete_bg="#059669",
    complete_fg="#ffffff",
    complete_border="#047857",
    complete_hover_bg="#047857",
    danger_bg="#fae9e9",
    danger_fg="#b91c1c",
    danger_border="#f4bcbc",
    danger_hover_bg="#f7dcdc",
    comment_action_bg="#fdfcf7",
    comment_action_fg="#44403c",
    comment_action_border="#d5cdbf",
    comment_action_hover_bg="#f5f1e8",
    comment_action_hover_border="#059669",
    comment_action_hover_fg="#1c1917",
    # Badges
    badge_completed_bg="#e7f4ec",
    badge_completed_fg="#047857",
    badge_completed_border="#b6e1c6",
    badge_incomplete_bg="#fae9e9",
    badge_incomplete_fg="#b91c1c",
    badge_incomplete_border="#f4bcbc",
    # Progreso y scroll
    progress_bg="#ede8dd",
    progress_border="#d5cdbf",
    progress_fg="#1c1917",
    progress_chunk="#059669",
    scroll_bg="#f7f4ed",
    scroll_handle="#d5cdbf",
    scroll_handle_hover="#b5aca0",
    # Tooltip
    tooltip_bg="#292524",
    tooltip_fg="#fdfcf7",
    tooltip_border="#44403c",
)

THEME_TOKENS_MAP: dict[str, ThemeTokens] = {
    THEME_DARK: DARK_TOKENS,
    THEME_LIGHT: LIGHT_TOKENS,
}
