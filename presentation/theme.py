"""Definición y generación de temas visuales (Modo Claro y Modo Oscuro) para Study Timetrial."""

from __future__ import annotations

from presentation.theme_tokens import (
    DARK_TOKENS,
    LIGHT_TOKENS,
    THEME_DARK,
    THEME_LIGHT,
    THEME_TOKENS_MAP,
    ThemeTokens,
)

__all__ = [
    "THEME_LIGHT",
    "THEME_DARK",
    "ThemeTokens",
    "DARK_TOKENS",
    "LIGHT_TOKENS",
    "get_theme_tokens",
    "get_available_themes",
    "get_theme_stylesheet",
    "get_dialog_stylesheet",
    "get_status_pill_style",
    "get_timer_cards_style",
]

from presentation.theming.theme_loader import (
    get_available_themes,
    get_theme_tokens as _get_theme_tokens_dynamic,
)


def get_theme_tokens(theme: str) -> ThemeTokens:
    """Obtiene el conjunto de tokens de diseño correspondiente al nombre del tema."""
    return _get_theme_tokens_dynamic(theme)


def build_stylesheet_from_tokens(t: ThemeTokens) -> str:
    """Construye la hoja de estilos QSS a partir de un conjunto de ThemeTokens."""
    return f"""
        {t.mode_comment}
        QWidget {{
            color: {t.text_primary};
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            font-size: 13px;
        }}
        QMainWindow {{
            background: {t.bg_app};
        }}
        QDialog {{
            background: {t.bg_dialog};
            color: {t.text_primary};
        }}
        QToolTip {{
            background-color: {t.tooltip_bg};
            color: {t.tooltip_fg};
            border: 1px solid {t.tooltip_border};
            border-radius: 6px;
            padding: 5px 8px;
            font-size: 12px;
        }}

        /* Top Toolbar */
        QToolBar#main_toolbar {{
            background: {t.bg_toolbar};
            border-bottom: 1px solid {t.toolbar_border};
            padding: 5px 12px;
            spacing: 8px;
        }}
        QToolButton#file_toolbar_button, QToolButton#view_toolbar_button, QToolButton#config_toolbar_button {{
            background: {t.toolbar_btn_bg};
            color: {t.toolbar_btn_fg};
            border: 1px solid {t.toolbar_btn_border};
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 700;
        }}
        QToolButton#file_toolbar_button:hover, QToolButton#view_toolbar_button:hover, QToolButton#config_toolbar_button:hover {{
            background: {t.toolbar_btn_hover_bg};
            border-color: {t.toolbar_btn_hover_border};
            color: {t.toolbar_btn_hover_fg};
        }}
        QToolButton#file_toolbar_button:pressed, QToolButton#view_toolbar_button:pressed, QToolButton#config_toolbar_button:pressed {{
            background: {t.toolbar_btn_pressed};
        }}

        /* Menus */
        QMenu {{
            background-color: {t.menu_bg};
            color: {t.menu_fg};
            border: 1px solid {t.menu_border};
            border-radius: 8px;
            padding: 6px;
        }}
        QMenu::item {{
            background-color: transparent;
            color: {t.menu_item_fg};
            padding: 7px 26px 7px 14px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }}
        QMenu::item:selected {{
            background-color: {t.menu_item_sel_bg};
            color: {t.menu_item_sel_fg};
        }}
        QMenu::item:disabled {{
            color: {t.menu_item_disabled};
        }}
        QMenu::separator {{
            height: 1px;
            background: {t.menu_separator};
            margin: 4px 8px;
        }}
        QMenu::indicator {{
            width: 16px;
            height: 16px;
            margin-left: 4px;
        }}

        /* Tabs */
        QTabWidget::pane {{
            border: none;
            background: {t.bg_app};
        }}
        QTabBar {{
            background: {t.bg_tab_bar};
            border: none;
        }}
        QTabBar::tab {{
            background: {t.bg_tab_bar};
            color: {t.tab_text};
            padding: 13px 28px;
            border: none;
            font-size: 13px;
            font-weight: 700;
            min-width: 140px;
        }}
        QTabBar::tab:selected {{
            color: {t.tab_text_selected};
            background: {t.bg_tab_active};
            border-bottom: 3px solid {t.tab_text_selected};
        }}
        QTabBar::tab:hover:!selected {{
            color: {t.text_primary};
            background: {t.bg_tab_active};
        }}

        /* Scroll containers */
        QScrollArea#homeScroll, QScrollArea#statsScroll, QScrollArea#ambienceScroll {{
            background: transparent;
            border: none;
        }}
        QScrollArea#homeScroll > QWidget > QWidget,
        QScrollArea#statsScroll > QWidget > QWidget,
        QScrollArea#ambienceScroll > QWidget > QWidget {{
            background: transparent;
        }}
        QWidget#homeContainer, QWidget#statsContainer, QWidget#ambienceContainer {{
            background: transparent;
        }}

        /* Headers & Meta */
        QLabel#brand {{
            color: {t.text_heading};
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.5px;
        }}
        QLabel#eyebrow {{
            color: {t.text_muted};
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 1.2px;
        }}
        QLabel#location_selector_label {{
            color: {t.text_muted};
            font-size: 13px;
            font-weight: 800;
            letter-spacing: 1.2px;
        }}
        QLabel#record_meta {{
            color: {t.text_faint};
            font-size: 12px;
            font-weight: 700;
        }}
        QLabel#location_badge {{
            background: {t.bg_location_badge};
            border: 1.5px solid {t.border_subtle if t.is_dark else t.border_subtle};
            border-radius: 10px;
            color: {t.text_heading};
            font-size: 24px;
            font-weight: 800;
            padding: 8px 16px;
        }}
        QLabel#status {{
            color: {t.text_muted};
            font-size: 13px;
            font-weight: 600;
        }}
        QLabel#status_badge {{
            background: {t.bg_status_badge};
            color: {t.text_disabled if not t.is_dark else t.text_muted};
            border: 1px solid {t.border_strong};
            border-radius: 10px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;
            padding: 5px 12px;
        }}

        /* Cards */
        QFrame#heroCard, QFrame#metricCard, QFrame#sectionCard, QFrame#panelCard, QFrame#kpiCard, QFrame#notesCard {{
            background: {t.bg_card};
            border: 1px solid {t.card_border};
            border-radius: 14px;
        }}
        QFrame#heroCard {{
            border-top: 3px solid {t.hero_card_top};
        }}
        QTextBrowser#notes_browser {{
            background: {t.bg_input};
            border: 1px solid {t.border_subtle};
            border-radius: 8px;
            padding: 8px 12px;
            color: {t.text_primary};
            font-size: 12px;
        }}

        /* Clocks */
        QFrame#exerciseCard, QFrame#breakCard {{
            background: {t.bg_clock_card};
            border: 1px solid {t.border_subtle};
            border-radius: 14px;
        }}
        QLabel#digital_clock_exercise {{
            color: {t.text_clock_exercise};
            font-family: 'Consolas', 'Cascadia Code', 'Segoe UI Mono', monospace;
            font-weight: 800;
        }}
        QLabel#digital_clock_break {{
            color: {t.text_clock_break};
            font-family: 'Consolas', 'Cascadia Code', 'Segoe UI Mono', monospace;
            font-weight: 700;
        }}

        /* Continuation Banner */
        QFrame#continuationBanner {{
            background: {t.bg_card};
            border: 1px solid #f59e0b;
            border-left: 5px solid #f59e0b;
            border-radius: 10px;
        }}
        QLabel#continuation_label {{
            color: {t.text_primary};
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton#continuation_cancel_btn {{
            background: transparent;
            color: #ef4444;
            border: 1px solid #ef4444;
            border-radius: 6px;
            padding: 5px 12px;
            font-size: 12px;
            font-weight: 700;
        }}
        QPushButton#continuation_cancel_btn:hover {{
            background: rgba(239, 68, 68, 0.12);
        }}

        /* Header today card & KPIs */
        QFrame#todayCard {{
            background: {t.bg_card};
            border: 1px solid {t.card_border};
            border-radius: 12px;
        }}
        QLabel#today_label {{
            color: {t.text_muted};
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1px;
        }}
        QLabel#today_value {{
            color: {t.text_heading};
            font-size: 16px;
            font-weight: 800;
            font-family: 'Consolas', monospace;
        }}
        QFrame#kpiCardToday {{
            background: {t.bg_card};
            border: 1px solid {t.card_border};
            border-radius: 10px;
        }}
        QLabel#kpiTodayLabel {{
            color: {t.text_muted};
            font-size: 9px;
            font-weight: 800;
            letter-spacing: 0.8px;
        }}
        QLabel#kpiTodayValue {{
            color: {t.text_heading};
            font-size: 15px;
            font-weight: 800;
            font-family: 'Consolas', monospace;
        }}
        QLabel#personal_best_badge {{
            background: {"#27272a" if t.is_dark else "#fef3c7"};
            color: {"#fde047" if t.is_dark else "#b45309"};
            border: 1px solid {"#854d0e" if t.is_dark else "#fde68a"};
            border-radius: 8px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 800;
            font-family: 'Consolas', monospace;
        }}

        /* KPI Cards in Registros */
        QLabel#kpi_title {{
            color: {t.text_muted};
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1px;
        }}
        QLabel#kpi_value {{
            color: {t.text_heading};
            font-size: 17px;
            font-weight: 800;
            font-family: 'Consolas', monospace;
        }}

        /* Statistics KPI Labels */
        QLabel#stat_hero_value {{
            color: {t.text_heading};
            font-size: 32px;
            font-weight: 800;
            font-family: 'Consolas', monospace;
        }}
        QLabel#stat_sub_value {{
            color: {t.text_muted};
            font-size: 20px;
            font-weight: 700;
            font-family: 'Consolas', monospace;
        }}
        QLabel#stat_sub_text {{
            color: {t.text_muted};
            font-size: 16px;
            font-weight: 700;
        }}

        /* Form Inputs */
        QLineEdit, QSpinBox {{
            background: {t.bg_input};
            border: 1.5px solid {t.border_subtle if t.is_dark else t.border_strong};
            border-radius: 9px;
            padding: 8px 12px;
            min-height: 22px;
            color: {t.text_heading};
            font-size: 13px;
        }}
        QLineEdit:focus, QSpinBox:focus {{
            background: {t.bg_input_focus};
            border: 2px solid {t.border_focus};
            padding: 7px 11px;
        }}
        QLineEdit:disabled, QSpinBox:disabled {{
            background: {t.bg_input_disabled};
            color: {t.text_disabled};
            border-color: {t.border_disabled};
        }}
        QLineEdit#location_selector_input, QSpinBox#location_selector_input {{
            font-size: 16px;
            font-weight: 700;
            min-height: 26px;
            padding: 4px 10px;
        }}
        QLineEdit#location_selector_input:focus, QSpinBox#location_selector_input:focus {{
            padding: 3px 9px;
        }}

        /* Buttons */
        QPushButton {{
            background: {t.bg_button};
            color: {t.toolbar_btn_fg};
            border: 1px solid {t.toolbar_btn_border};
            border-radius: 9px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 700;
        }}
        QPushButton:hover {{
            border-color: {t.border_focus};
            background: {t.bg_button_hover};
            color: {t.toolbar_btn_hover_fg};
        }}
        QPushButton:pressed {{
            background: {t.bg_button_pressed};
        }}

        /* Hero timer action buttons */
        QPushButton#hero_start {{
            background: {t.hero_start_bg};
            color: {t.hero_start_fg};
            border: 1px solid {t.hero_start_border};
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }}
        QPushButton#hero_start:hover {{
            background: {t.hero_start_hover_bg};
            border-color: {t.hero_start_hover_border};
            color: {t.hero_start_hover_fg};
        }}
        QPushButton#hero_pause {{
            background: {t.hero_pause_bg};
            color: {t.hero_pause_fg};
            border: 1.5px solid {t.hero_pause_border};
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }}
        QPushButton#hero_pause:hover {{
            background: {t.hero_pause_hover_bg};
            border-color: {t.hero_pause_hover_border};
        }}
        QPushButton#hero_resume {{
            background: {t.hero_resume_bg};
            color: {t.hero_resume_fg};
            border: 1.5px solid {t.hero_resume_border};
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }}
        QPushButton#hero_resume:hover {{
            background: {t.hero_resume_hover_bg};
            border-color: {t.hero_resume_hover_border};
        }}
        QPushButton#hero_break {{
            background: {t.hero_pause_bg};
            color: {t.hero_pause_fg};
            border: 1.5px solid {t.hero_pause_border};
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }}
        QPushButton#hero_break:hover {{
            background: {t.hero_pause_hover_bg};
            border-color: {t.hero_pause_hover_border};
        }}

        QPushButton#stop {{
            background: {t.stop_bg};
            color: {t.stop_fg};
            border: 1px solid {t.stop_border};
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }}
        QPushButton#stop:hover {{
            background: {t.stop_hover_bg};
            border-color: {t.stop_hover_border};
        }}

        QPushButton#complete {{
            background: {t.complete_bg};
            color: {t.complete_fg};
            border: 1px solid {t.complete_border};
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }}
        QPushButton#complete:hover {{
            background: {t.complete_hover_bg};
        }}

        QPushButton#danger {{
            background: {t.danger_bg};
            color: {t.danger_fg};
            border: 1px solid {t.danger_border};
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }}
        QPushButton#danger:hover {{
            background: {t.danger_hover_bg};
        }}

        QPushButton#comment_action, QPushButton#tags_action {{
            background: {t.comment_action_bg};
            color: {t.comment_action_fg};
            border: 1px solid {t.comment_action_border};
            border-radius: 9px;
            padding: 9px 16px;
            font-size: 12px;
            font-weight: 700;
        }}
        QPushButton#comment_action:hover, QPushButton#tags_action:hover {{
            background: {t.comment_action_hover_bg};
            border-color: {t.comment_action_hover_border};
            color: {t.comment_action_hover_fg};
        }}

        /* Steppers numéricos */
        QPushButton#stepper_button {{
            background: {t.bg_button};
            color: {t.toolbar_btn_fg};
            border: 1px solid {t.toolbar_btn_border};
            border-radius: 8px;
            min-width: 36px;
            max-width: 36px;
            min-height: 36px;
            max-height: 36px;
            padding: 0px;
        }}
        QPushButton#stepper_button:hover {{
            background: {t.bg_button_hover};
            border-color: {t.border_focus};
            color: {t.toolbar_btn_hover_fg};
        }}
        QPushButton#stepper_button:pressed {{
            background: {t.bg_stepper_pressed};
        }}
        QPushButton#stepper_button:disabled {{
            background: {t.bg_input_disabled};
            color: {t.text_disabled};
            border-color: {t.border_disabled};
        }}

        QPushButton#toolbar_primary {{
            background: {t.toolbar_primary_bg};
            color: {t.toolbar_primary_fg};
            border: 1px solid {t.toolbar_primary_border};
            font-weight: 800;
            padding: 8px 16px;
            border-radius: 8px;
        }}
        QPushButton#toolbar_primary:hover {{
            background: {t.toolbar_primary_hover_bg};
            color: {t.toolbar_primary_hover_fg};
        }}

        QPushButton#secondary_action {{
            background: {t.bg_secondary_action};
            color: {t.toolbar_btn_fg if t.is_dark else t.comment_action_fg};
            border: 1px solid {t.toolbar_btn_border};
            border-radius: 8px;
            padding: 8px 14px;
            font-weight: 700;
        }}
        QPushButton#secondary_action:hover {{
            background: {t.bg_secondary_hover};
            border-color: {t.border_focus if t.is_dark else t.text_faint};
            color: {t.toolbar_btn_hover_fg};
        }}

        QPushButton#table_action_icon {{
            background: {t.bg_button if t.is_dark else t.bg_secondary_hover};
            border: 1px solid {t.border_strong if t.is_dark else t.border_subtle};
            border-radius: 6px;
            padding: 4px;
            min-width: 28px;
            min-height: 28px;
        }}
        QPushButton#table_action_icon:hover {{
            background: {t.bg_button_hover if t.is_dark else t.bg_button_pressed};
            border-color: {t.text_faint if t.is_dark else t.border_strong};
        }}

        QPushButton#table_delete_icon {{
            background: {t.stop_bg};
            border: 1px solid {t.stop_border};
            border-radius: 6px;
            padding: 4px;
            min-width: 28px;
            min-height: 28px;
        }}
        QPushButton#table_delete_icon:hover {{
            background: {t.stop_hover_bg};
            border-color: #ef4444;
        }}

        /* Table Badges */
        QLabel#table_badge_completed {{
            background: {t.badge_completed_bg};
            color: {t.badge_completed_fg};
            border: 1px solid {t.badge_completed_border};
            border-radius: 6px;
            padding: 2px 8px;
            font-weight: 700;
            font-size: 11px;
        }}
        QLabel#table_badge_incomplete {{
            background: {t.badge_incomplete_bg};
            color: {t.badge_incomplete_fg};
            border: 1px solid {t.badge_incomplete_border};
            border-radius: 6px;
            padding: 2px 8px;
            font-weight: 700;
            font-size: 11px;
        }}

        /* Table */
        QTableWidget {{
            background: {t.bg_table};
            border: 1px solid {t.border_subtle};
            border-radius: 12px;
            gridline-color: {t.table_gridline};
            alternate-background-color: {t.bg_table_alt};
            selection-background-color: {t.table_selection_bg};
            selection-color: {t.table_selection_fg};
            color: {t.text_primary};
        }}
        QHeaderView::section {{
            background: {t.bg_table_header};
            color: {t.text_muted if t.is_dark else t.text_disabled};
            border: none;
            border-bottom: 1.5px solid {t.border_subtle};
            padding: 10px 8px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;
        }}

        /* Progress Bar */
        QProgressBar {{
            background: {t.progress_bg};
            border: 1px solid {t.progress_border};
            border-radius: 8px;
            text-align: center;
            color: {t.progress_fg};
            font-weight: 700;
            font-size: 11px;
            min-height: 20px;
        }}
        QProgressBar::chunk {{
            background: {t.progress_chunk};
            border-radius: 7px;
        }}

        /* Scrollbars */
        QScrollBar:vertical {{
            background: {t.scroll_bg};
            width: 10px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {t.scroll_handle};
            min-height: 24px;
            border-radius: 5px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {t.scroll_handle_hover};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: {t.scroll_bg};
            height: 10px;
            margin: 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: {t.scroll_handle};
            min-width: 24px;
            border-radius: 5px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {t.scroll_handle_hover};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        /* Sliders (Audio volume & controls) */
        QSlider {{
            background: transparent;
            min-height: 22px;
        }}
        QSlider::groove:horizontal {{
            height: 6px;
            background: {t.bg_card_inner};
            border: 1px solid {t.border_subtle};
            border-radius: 3px;
        }}
        QSlider::sub-page:horizontal {{
            background: {t.toolbar_primary_bg};
            border: 1px solid {t.toolbar_primary_bg};
            border-radius: 3px;
        }}
        QSlider::add-page:horizontal {{
            background: {t.bg_card_inner};
            border: 1px solid {t.border_subtle};
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {t.bg_surface};
            border: 2px solid {t.toolbar_primary_bg};
            width: 14px;
            margin-top: -5px;
            margin-bottom: -5px;
            border-radius: 8px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {t.toolbar_primary_hover_bg};
            border: 2px solid {t.border_focus};
        }}
        QSlider::handle:horizontal:disabled {{
            background: {t.border_disabled};
            border: 2px solid {t.border_disabled};
        }}

        /* Track Card Mute Button */
        QPushButton#trackMuteBtn {{
            background: {t.bg_button};
            border: 1px solid {t.border_subtle};
            border-radius: 6px;
            padding: 4px;
        }}
        QPushButton#trackMuteBtn:hover {{
            background: {t.bg_button_hover};
            border-color: {t.border_focus};
        }}
        QPushButton#trackMuteBtn:pressed {{
            background: {t.bg_button_pressed};
        }}

        /* Dialogs and Lists */
        QListWidget {{
            background: {t.bg_list};
            color: {t.text_heading};
            border: 1px solid {t.border_subtle};
            border-radius: 8px;
        }}
        QListWidget::item {{
            padding: 8px;
            border-radius: 6px;
        }}
        QListWidget::item:hover {{
            background: {t.list_item_hover};
        }}
        QListWidget::item:selected {{
            background: {t.list_item_selected_bg};
            color: {t.list_item_selected_fg};
        }}
        QCheckBox {{
            color: {t.text_checkbox};
        }}

        /* Filters and Sorting Panel */
        QFrame#filter_panel {{
            background: {t.bg_filter_panel};
            border: 1px solid {t.border_subtle};
            border-radius: 10px;
            padding: 6px 12px;
        }}
        QLabel#filter_label {{
            color: {t.text_muted};
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;
        }}
        QComboBox {{
            background: {t.bg_combobox};
            color: {t.combobox_fg};
            border: 1px solid {t.border_subtle if t.is_dark else t.border_strong};
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 12px;
            min-height: 22px;
        }}
        QComboBox:hover {{
            border-color: {t.border_strong if t.is_dark else t.text_muted};
            background: {t.combobox_hover_bg};
        }}
        QComboBox:focus {{
            border-color: {t.combobox_focus_border};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: none;
        }}
        QComboBox QAbstractItemView {{
            background: {t.combobox_dropdown_bg};
            color: {t.combobox_dropdown_fg};
            border: 1px solid {t.border_strong};
            selection-background-color: {t.combobox_dropdown_sel_bg};
            selection-color: {t.combobox_dropdown_sel_fg};
            padding: 4px;
            outline: none;
        }}
        QPushButton#filter_reset_btn {{
            background: {t.filter_reset_bg};
            color: {t.filter_reset_fg};
            border: 1px solid {t.border_strong};
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 700;
        }}
        QPushButton#filter_reset_btn:hover {{
            background: {t.filter_reset_hover_bg};
            color: {t.filter_reset_hover_fg};
            border-color: {t.filter_reset_hover_border};
        }}
        QPushButton#sort_dir_btn {{
            background: {t.sort_dir_btn_bg};
            color: {t.sort_dir_btn_fg};
            border: 1px solid {t.border_strong};
            border-radius: 6px;
            padding: 4px 8px;
            font-weight: 800;
            min-width: 28px;
        }}
        QPushButton#sort_dir_btn:hover {{
            background: {t.sort_dir_btn_hover_bg};
            border-color: {t.sort_dir_btn_hover_border};
        }}

        /* Excel Filter Popup */
        QDialog#excelFilterPopup {{
            background: {t.popup_bg};
            border: 1px solid {t.popup_border};
            border-radius: 10px;
        }}
        QLabel#filter_popup_title {{
            color: {t.popup_title_fg};
            font-size: 13px;
            font-weight: 800;
        }}
        QPushButton#filter_sort_btn {{
            background: {t.popup_btn_bg};
            color: {t.popup_btn_fg};
            border: 1px solid {t.popup_btn_border};
            border-radius: 6px;
            text-align: left;
            padding: 6px 10px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton#filter_sort_btn:hover {{
            background: {t.popup_btn_hover_bg};
            border-color: {t.popup_btn_hover_border};
            color: {t.popup_btn_hover_fg};
        }}
        QFrame#filter_sep {{
            color: {t.popup_sep};
            background-color: {t.popup_sep};
            height: 1px;
            border: none;
        }}
        QListWidget#excelFilterList {{
            background: {t.popup_list_bg};
            color: {t.text_primary};
            border: 1px solid {t.popup_list_border};
            border-radius: 6px;
        }}
        QListWidget#excelFilterList::item {{
            padding: 4px 6px;
            border-radius: 4px;
        }}
        QListWidget#excelFilterList::item:hover {{
            background: {t.popup_list_hover};
        }}
    """


def get_theme_stylesheet(theme: str) -> str:
    """Genera la hoja de estilos QSS completa para el tema especificado ('light' o 'dark')."""
    tokens = get_theme_tokens(theme)
    return build_stylesheet_from_tokens(tokens)


def get_dialog_stylesheet(theme: str) -> str:
    """Devuelve el estilo para el diálogo de selección inicial según el tema."""
    if theme == THEME_DARK:
        return """
            QDialog { background: #0f172a; }
            QLabel#title { color: #f8fafc; font-size: 22px; font-weight: 800; }
            QLabel#subtitle { color: #94a3b8; font-size: 13px; }
            QLabel#recent_header { color: #cbd5e1; font-size: 13px; font-weight: 700; }
            QLabel#version { color: #64748b; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
            QListWidget { background: #0b0f17; color: #f8fafc; border: 1px solid #1e293b; border-radius: 8px; min-height: 120px; font-size: 12px; }
            QListWidget::item { padding: 6px 8px; border-radius: 6px; }
            QListWidget::item:hover { background: #1e293b; }
            QListWidget::item:selected { background: #1e293b; color: #34d399; font-weight: 700; }
            QCheckBox { color: #cbd5e1; font-size: 12px; font-weight: 500; spacing: 8px; }
            QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #334155; background: #0b0f17; }
            QCheckBox::indicator:checked { background: #10b981; border-color: #10b981; }
            QPushButton { min-height: 38px; min-width: 140px; border-radius: 9px; font-size: 12px; font-weight: 700; }
            QPushButton#primary { background: #10b981; color: #0b0f17; border: 1px solid #10b981; font-weight: 800; }
            QPushButton#primary:hover { background: #059669; }
            QPushButton#secondary { background: #1e293b; color: #f1f5f9; border: 1px solid #334155; }
            QPushButton#secondary:hover { background: #283548; border-color: #10b981; }
            QPushButton#ghost { background: transparent; color: #94a3b8; border: 1px solid #1e293b; }
            QPushButton#ghost:hover { background: #1e293b; color: #f8fafc; }
        """
    return """
        QDialog { background: #f7f4ed; }
        QLabel#title { color: #1c1917; font-size: 22px; font-weight: 800; }
        QLabel#subtitle { color: #78716c; font-size: 13px; }
        QLabel#recent_header { color: #44403c; font-size: 13px; font-weight: 700; }
        QLabel#version { color: #a8a29e; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
        QListWidget { background: #fdfcf7; color: #1c1917; border: 1px solid #e4ded4; border-radius: 8px; min-height: 120px; font-size: 12px; }
        QListWidget::item { padding: 6px 8px; border-radius: 6px; }
        QListWidget::item:hover { background: #f5f1e8; }
        QListWidget::item:selected { background: #f1eadb; color: #047857; font-weight: 700; }
        QCheckBox { color: #44403c; font-size: 12px; font-weight: 500; spacing: 8px; }
        QCheckBox::indicator { width: 16px; height: 16px; border-radius: 4px; border: 1px solid #d5cdbf; background: #fdfcf7; }
        QCheckBox::indicator:checked { background: #059669; border-color: #059669; }
        QPushButton { min-height: 38px; min-width: 140px; border-radius: 9px; font-size: 12px; font-weight: 700; }
        QPushButton#primary { background: #059669; color: #ffffff; border: 1px solid #047857; font-weight: 800; }
        QPushButton#primary:hover { background: #047857; }
        QPushButton#secondary { background: #fdfcf7; color: #292524; border: 1px solid #d5cdbf; }
        QPushButton#secondary:hover { background: #f5f1e8; border-color: #059669; }
        QPushButton#ghost { background: transparent; color: #78716c; border: 1px solid #e4ded4; }
        QPushButton#ghost:hover { background: #ede8dd; }
    """


def get_status_pill_style(state: str, is_dark: bool) -> str:
    """Devuelve la hoja de estilo QSS para la pastilla visual de estado (status_pill).

    Args:
        state: 'paused', 'play', 'break', o 'waiting' (idle).
        is_dark: True si el tema activo es oscuro.
    """
    if state == "paused":
        if is_dark:
            return "background: #1e293b; color: #f1f5f9; border: 1px solid #475569; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;"
        return "background: #ede8dd; color: #44403c; border: 1px solid #d5cdbf; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;"
    elif state == "play":
        if is_dark:
            return "background: #064e3b; color: #6ee7b7; border: 1px solid #059669; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;"
        return "background: #e7f4ec; color: #047857; border: 1px solid #b6e1c6; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;"
    elif state == "break":
        if is_dark:
            return "background: #451a03; color: #fde68a; border: 1px solid #78350f; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;"
        return "background: #fbf4dc; color: #b45309; border: 1px solid #f2dd9b; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;"
    else:  # waiting / idle
        if is_dark:
            return "background: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;"
        return "background: #ede8dd; color: #57534e; border: 1px solid #d5cdbf; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;"


def get_timer_cards_style(state: str, is_dark: bool) -> tuple[str, str]:
    """Devuelve la tupla de estilos (exercise_card_style, break_card_style) según el estado.

    Args:
        state: 'paused', 'play', 'break', o 'waiting'.
        is_dark: True si el tema activo es oscuro.
    """
    if is_dark:
        card_bg = "#162032"
        card_border = "#1e293b"

        if state == "paused":
            return (
                f"QFrame#exerciseCard {{ background: {card_bg}; border: 1.5px solid #475569; border-radius: 14px; }}",
                f"QFrame#breakCard {{ background: {card_bg}; border: 1.5px solid #475569; border-radius: 14px; }}",
            )
        elif state == "play":
            return (
                f"QFrame#exerciseCard {{ background: #081d16; border: 2px solid #10b981; border-radius: 14px; }}",
                f"QFrame#breakCard {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 14px; }}",
            )
        elif state == "break":
            return (
                f"QFrame#exerciseCard {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 14px; }}",
                f"QFrame#breakCard {{ background: #231805; border: 2px solid #f59e0b; border-radius: 14px; }}",
            )
        else:  # waiting
            return (
                f"QFrame#exerciseCard {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 14px; }}",
                f"QFrame#breakCard {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 14px; }}",
            )
    else:
        card_bg = "#fdfcf7"
        card_border = "#e4ded4"

        if state == "paused":
            return (
                f"QFrame#exerciseCard {{ background: #f5f1e8; border: 1.5px solid #d5cdbf; border-radius: 14px; }}",
                f"QFrame#breakCard {{ background: #f5f1e8; border: 1.5px solid #d5cdbf; border-radius: 14px; }}",
            )
        elif state == "play":
            return (
                f"QFrame#exerciseCard {{ background: #eaf5ee; border: 2px solid #059669; border-radius: 14px; }}",
                f"QFrame#breakCard {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 14px; }}",
            )
        elif state == "break":
            return (
                f"QFrame#exerciseCard {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 14px; }}",
                f"QFrame#breakCard {{ background: #fbf4dc; border: 2px solid #d97706; border-radius: 14px; }}",
            )
        else:  # waiting
            return (
                f"QFrame#exerciseCard {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 14px; }}",
                f"QFrame#breakCard {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 14px; }}",
            )
