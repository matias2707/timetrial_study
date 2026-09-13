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
    mode_comment="/* --- MODO OSCURO --- */",
    # Superficies
    bg_app="#090d16",
    bg_dialog="#0f172a",
    bg_surface="#0f172a",
    bg_surface_alt="#0d121f",
    bg_card="#0f172a",
    bg_card_inner="#050811",
    bg_clock_card="#050811",
    bg_tab_bar="#030712",
    bg_tab_active="#0d121f",
    bg_location_badge="#111827",
    bg_status_badge="#1e293b",
    bg_input="#090d16",
    bg_input_focus="#0f172a",
    bg_input_disabled="#111827",
    bg_button="#1e293b",
    bg_button_hover="#273549",
    bg_button_pressed="#172033",
    bg_stepper_pressed="#0f172a",
    bg_secondary_action="#1e293b",
    bg_secondary_hover="#273549",
    # Tablas y listas
    bg_table="#0d121f",
    bg_table_alt="#111827",
    bg_table_header="#090d16",
    table_gridline="#1e293b",
    table_selection_bg="#1e293b",
    table_selection_fg="#ffffff",
    bg_list="#090d16",
    list_item_hover="#1e293b",
    list_item_selected_bg="#1e293b",
    list_item_selected_fg="#bef264",
    # Desplegables y Filtros
    bg_filter_panel="#0b1120",
    bg_combobox="#111827",
    combobox_fg="#e2e8f0",
    combobox_hover_bg="#1a2234",
    combobox_focus_border="#bef264",
    combobox_dropdown_bg="#0f172a",
    combobox_dropdown_fg="#f1f5f9",
    combobox_dropdown_sel_bg="#1e293b",
    combobox_dropdown_sel_fg="#bef264",
    filter_reset_bg="#1e293b",
    filter_reset_fg="#94a3b8",
    filter_reset_hover_bg="#334155",
    filter_reset_hover_fg="#f8fafc",
    filter_reset_hover_border="#64748b",
    sort_dir_btn_bg="#1e293b",
    sort_dir_btn_fg="#bef264",
    sort_dir_btn_hover_bg="#273549",
    sort_dir_btn_hover_border="#bef264",
    # Excel Popup
    popup_bg="#0d121f",
    popup_border="#334155",
    popup_title_fg="#bef264",
    popup_btn_bg="#111827",
    popup_btn_fg="#e2e8f0",
    popup_btn_border="#1e293b",
    popup_btn_hover_bg="#1e293b",
    popup_btn_hover_border="#3b82f6",
    popup_btn_hover_fg="#ffffff",
    popup_sep="#1e293b",
    popup_list_bg="#090d16",
    popup_list_border="#1e293b",
    popup_list_hover="#1e293b",
    # Toolbars y Menús
    bg_toolbar="#0d121f",
    toolbar_border="#1e293b",
    toolbar_btn_bg="#1e293b",
    toolbar_btn_fg="#e2e8f0",
    toolbar_btn_border="#334155",
    toolbar_btn_hover_bg="#273549",
    toolbar_btn_hover_border="#a3e635",
    toolbar_btn_hover_fg="#ffffff",
    toolbar_btn_pressed="#172033",
    toolbar_primary_bg="#bef264",
    toolbar_primary_fg="#090d16",
    toolbar_primary_border="#bef264",
    toolbar_primary_hover_bg="#d9f99d",
    toolbar_primary_hover_fg="#000000",
    menu_bg="#0f172a",
    menu_fg="#f1f5f9",
    menu_border="#1e293b",
    menu_item_fg="#e2e8f0",
    menu_item_sel_bg="#1e293b",
    menu_item_sel_fg="#bef264",
    menu_item_disabled="#475569",
    menu_separator="#1e293b",
    # Bordes
    border_subtle="#1e293b",
    border_strong="#334155",
    border_focus="#bef264",
    border_disabled="#1f2937",
    card_border="#1e293b",
    hero_card_top="#bef264",
    # Tipografía
    text_primary="#f1f5f9",
    text_heading="#f8fafc",
    text_secondary="#e2e8f0",
    text_muted="#94a3b8",
    text_faint="#64748b",
    text_disabled="#475569",
    text_checkbox="#f1f5f9",
    text_clock_exercise="#e2e8f0",
    text_clock_break="#94a3b8",
    tab_text="#64748b",
    tab_text_selected="#bef264",
    # Hero buttons
    hero_start_bg="#bef264",
    hero_start_fg="#090d16",
    hero_start_border="#bef264",
    hero_start_hover_bg="#d9f99d",
    hero_start_hover_border="#d9f99d",
    hero_start_hover_fg="#000000",
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
    complete_bg="#059669",
    complete_fg="#ffffff",
    complete_border="#047857",
    complete_hover_bg="#10b981",
    danger_bg="#dc2626",
    danger_fg="#ffffff",
    danger_border="#b91c1c",
    danger_hover_bg="#ef4444",
    comment_action_bg="#1e293b",
    comment_action_fg="#e2e8f0",
    comment_action_border="#334155",
    comment_action_hover_bg="#273549",
    comment_action_hover_border="#bef264",
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
    progress_chunk="#84cc16",
    scroll_bg="#090d16",
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
    mode_comment="/* --- MODO CLARO --- */",
    # Superficies
    bg_app="#f8fafc",
    bg_dialog="#f8fafc",
    bg_surface="#ffffff",
    bg_surface_alt="#ffffff",
    bg_card="#ffffff",
    bg_card_inner="#090d16",  # Light theme still uses dark card for digital clocks!
    bg_clock_card="#090d16",
    bg_tab_bar="#0f172a",
    bg_tab_active="#1e293b",
    bg_location_badge="#f8fafc",
    bg_status_badge="#f1f5f9",
    bg_input="#f8fafc",
    bg_input_focus="#ffffff",
    bg_input_disabled="#f1f5f9",
    bg_button="#ffffff",
    bg_button_hover="#f8fafc",
    bg_button_pressed="#f1f5f9",
    bg_stepper_pressed="#e2e8f0",
    bg_secondary_action="#ffffff",
    bg_secondary_hover="#f8fafc",
    # Tablas y listas
    bg_table="#ffffff",
    bg_table_alt="#f8fafc",
    bg_table_header="#f8fafc",
    table_gridline="#f1f5f9",
    table_selection_bg="#f1f5f9",
    table_selection_fg="#0f172a",
    bg_list="#ffffff",
    list_item_hover="#f1f5f9",
    list_item_selected_bg="#f1f5f9",
    list_item_selected_fg="#0f172a",
    # Desplegables y Filtros
    bg_filter_panel="#f8fafc",
    bg_combobox="#ffffff",
    combobox_fg="#0f172a",
    combobox_hover_bg="#f8fafc",
    combobox_focus_border="#65a30d",
    combobox_dropdown_bg="#ffffff",
    combobox_dropdown_fg="#0f172a",
    combobox_dropdown_sel_bg="#f1f5f9",
    combobox_dropdown_sel_fg="#0f172a",
    filter_reset_bg="#f1f5f9",
    filter_reset_fg="#64748b",
    filter_reset_hover_bg="#e2e8f0",
    filter_reset_hover_fg="#0f172a",
    filter_reset_hover_border="#94a3b8",
    sort_dir_btn_bg="#f1f5f9",
    sort_dir_btn_fg="#4d7c0f",
    sort_dir_btn_hover_bg="#e2e8f0",
    sort_dir_btn_hover_border="#65a30d",
    # Excel Popup
    popup_bg="#ffffff",
    popup_border="#cbd5e1",
    popup_title_fg="#0f172a",
    popup_btn_bg="#f8fafc",
    popup_btn_fg="#334155",
    popup_btn_border="#e2e8f0",
    popup_btn_hover_bg="#f1f5f9",
    popup_btn_hover_border="#3b82f6",
    popup_btn_hover_fg="#0f172a",
    popup_sep="#e2e8f0",
    popup_list_bg="#ffffff",
    popup_list_border="#cbd5e1",
    popup_list_hover="#f1f5f9",
    # Toolbars y Menús
    bg_toolbar="#ffffff",
    toolbar_border="#e2e8f0",
    toolbar_btn_bg="#ffffff",
    toolbar_btn_fg="#1e293b",
    toolbar_btn_border="#cbd5e1",
    toolbar_btn_hover_bg="#f8fafc",
    toolbar_btn_hover_border="#84cc16",
    toolbar_btn_hover_fg="#0f172a",
    toolbar_btn_pressed="#f1f5f9",
    toolbar_primary_bg="#0f172a",
    toolbar_primary_fg="#bef264",
    toolbar_primary_border="#0f172a",
    toolbar_primary_hover_bg="#1e293b",
    toolbar_primary_hover_fg="#d9f99d",
    menu_bg="#ffffff",
    menu_fg="#0f172a",
    menu_border="#e2e8f0",
    menu_item_fg="#1e293b",
    menu_item_sel_bg="#f1f5f9",
    menu_item_sel_fg="#0f172a",
    menu_item_disabled="#94a3b8",
    menu_separator="#e2e8f0",
    # Bordes
    border_subtle="#e2e8f0",
    border_strong="#cbd5e1",
    border_focus="#84cc16",
    border_disabled="#e2e8f0",
    card_border="#e2e8f0",
    hero_card_top="#84cc16",
    # Tipografía
    text_primary="#0f172a",
    text_heading="#0f172a",
    text_secondary="#1e293b",
    text_muted="#64748b",
    text_faint="#94a3b8",
    text_disabled="#94a3b8",
    text_checkbox="#0f172a",
    text_clock_exercise="#e2e8f0",
    text_clock_break="#94a3b8",
    tab_text="#94a3b8",
    tab_text_selected="#bef264",
    # Hero buttons
    hero_start_bg="#0f172a",
    hero_start_fg="#bef264",
    hero_start_border="#0f172a",
    hero_start_hover_bg="#1e293b",
    hero_start_hover_border="#1e293b",
    hero_start_hover_fg="#d9f99d",
    hero_pause_bg="#fffbeb",
    hero_pause_fg="#b45309",
    hero_pause_border="#fde68a",
    hero_pause_hover_bg="#fef3c7",
    hero_pause_hover_border="#f59e0b",
    hero_resume_bg="#ecfdf5",
    hero_resume_fg="#047857",
    hero_resume_border="#a7f3d0",
    hero_resume_hover_bg="#d1fae5",
    hero_resume_hover_border="#10b981",
    stop_bg="#fef2f2",
    stop_fg="#dc2626",
    stop_border="#fecaca",
    stop_hover_bg="#fee2e2",
    stop_hover_border="#ef4444",
    complete_bg="#10b981",
    complete_fg="#ffffff",
    complete_border="#059669",
    complete_hover_bg="#059669",
    danger_bg="#ef4444",
    danger_fg="#ffffff",
    danger_border="#dc2626",
    danger_hover_bg="#dc2626",
    comment_action_bg="#f8fafc",
    comment_action_fg="#334155",
    comment_action_border="#cbd5e1",
    comment_action_hover_bg="#f1f5f9",
    comment_action_hover_border="#94a3b8",
    comment_action_hover_fg="#0f172a",
    # Badges
    badge_completed_bg="#ecfdf5",
    badge_completed_fg="#047857",
    badge_completed_border="#a7f3d0",
    badge_incomplete_bg="#fef2f2",
    badge_incomplete_fg="#b91c1c",
    badge_incomplete_border="#fecaca",
    # Progreso y scroll
    progress_bg="#f1f5f9",
    progress_border="#e2e8f0",
    progress_fg="#0f172a",
    progress_chunk="#84cc16",
    scroll_bg="#f8fafc",
    scroll_handle="#cbd5e1",
    scroll_handle_hover="#94a3b8",
    # Tooltip
    tooltip_bg="#0f172a",
    tooltip_fg="#f8fafc",
    tooltip_border="#334155",
)

THEME_TOKENS_MAP: dict[str, ThemeTokens] = {
    THEME_DARK: DARK_TOKENS,
    THEME_LIGHT: LIGHT_TOKENS,
}
