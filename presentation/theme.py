"""Definición y generación de temas visuales (Modo Claro y Modo Oscuro) para Study Timetrial."""

from __future__ import annotations

from typing import Any

THEME_LIGHT = "light"
THEME_DARK = "dark"


def get_theme_stylesheet(theme: str) -> str:
    """Genera la hoja de estilos QSS completa para el tema especificado ('light' o 'dark')."""
    is_dark = (theme == THEME_DARK)

    if is_dark:
        return """
        /* --- MODO OSCURO --- */
        QWidget {
            color: #f1f5f9;
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            font-size: 13px;
        }
        QMainWindow {
            background: #090d16;
        }
        QDialog {
            background: #0f172a;
            color: #f1f5f9;
        }
        QToolTip {
            background-color: #1e293b;
            color: #f8fafc;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 5px 8px;
            font-size: 12px;
        }

        /* Top Toolbar */
        QToolBar#main_toolbar {
            background: #0d121f;
            border-bottom: 1px solid #1e293b;
            padding: 5px 12px;
            spacing: 8px;
        }
        QToolButton#file_toolbar_button, QToolButton#view_toolbar_button, QToolButton#config_toolbar_button {
            background: #1e293b;
            color: #e2e8f0;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 700;
        }
        QToolButton#file_toolbar_button:hover, QToolButton#view_toolbar_button:hover, QToolButton#config_toolbar_button:hover {
            background: #273549;
            border-color: #a3e635;
            color: #ffffff;
        }
        QToolButton#file_toolbar_button:pressed, QToolButton#view_toolbar_button:pressed, QToolButton#config_toolbar_button:pressed {
            background: #172033;
        }

        /* Menus */
        QMenu {
            background-color: #0f172a;
            color: #f1f5f9;
            border: 1px solid #1e293b;
            border-radius: 8px;
            padding: 6px;
        }
        QMenu::item {
            background-color: transparent;
            color: #e2e8f0;
            padding: 7px 26px 7px 14px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }
        QMenu::item:selected {
            background-color: #1e293b;
            color: #bef264;
        }
        QMenu::item:disabled {
            color: #475569;
        }
        QMenu::separator {
            height: 1px;
            background: #1e293b;
            margin: 4px 8px;
        }
        QMenu::indicator {
            width: 16px;
            height: 16px;
            margin-left: 4px;
        }

        /* Tabs */
        QTabWidget::pane {
            border: none;
            background: #090d16;
        }
        QTabBar {
            background: #030712;
            border: none;
        }
        QTabBar::tab {
            background: #030712;
            color: #64748b;
            padding: 13px 28px;
            border: none;
            font-size: 13px;
            font-weight: 700;
            min-width: 140px;
        }
        QTabBar::tab:selected {
            color: #bef264;
            background: #0d121f;
            border-bottom: 3px solid #bef264;
        }
        QTabBar::tab:hover:!selected {
            color: #f1f5f9;
            background: #0d121f;
        }

        /* Scroll containers */
        QScrollArea#homeScroll, QScrollArea#statsScroll {
            background: transparent;
            border: none;
        }
        QWidget#homeContainer, QWidget#statsContainer {
            background: transparent;
        }

        /* Headers & Meta */
        QLabel#brand {
            color: #f8fafc;
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.5px;
        }
        QLabel#eyebrow {
            color: #94a3b8;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 1.2px;
        }
        QLabel#record_meta {
            color: #64748b;
            font-size: 12px;
            font-weight: 700;
        }
        QLabel#location_badge {
            background: #111827;
            border: 1.5px solid #1f2937;
            border-radius: 10px;
            color: #f8fafc;
            font-size: 24px;
            font-weight: 800;
            padding: 8px 16px;
        }
        QLabel#status {
            color: #94a3b8;
            font-size: 13px;
            font-weight: 600;
        }
        QLabel#status_badge {
            background: #1e293b;
            color: #94a3b8;
            border: 1px solid #334155;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;
            padding: 5px 12px;
        }

        /* Cards */
        QFrame#heroCard, QFrame#metricCard, QFrame#sectionCard, QFrame#panelCard, QFrame#kpiCard {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 14px;
        }
        QFrame#heroCard {
            border-top: 3px solid #bef264;
        }

        /* Clocks */
        QFrame#exerciseCard, QFrame#breakCard {
            background: #050811;
            border: 1px solid #1e293b;
            border-radius: 14px;
        }
        QLabel#digital_clock_exercise {
            color: #e2e8f0;
            font-family: 'Consolas', 'Cascadia Code', 'Segoe UI Mono', monospace;
            font-weight: 800;
        }
        QLabel#digital_clock_break {
            color: #94a3b8;
            font-family: 'Consolas', 'Cascadia Code', 'Segoe UI Mono', monospace;
            font-weight: 700;
        }

        /* Header today card */
        QFrame#todayCard {
            background: #0f172a;
            border: 1px solid #1e293b;
            border-radius: 12px;
        }
        QLabel#today_label {
            color: #94a3b8;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1px;
        }
        QLabel#today_value {
            color: #f8fafc;
            font-size: 16px;
            font-weight: 800;
            font-family: 'Consolas', monospace;
        }

        /* KPI Cards in Registros */
        QLabel#kpi_title {
            color: #94a3b8;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1px;
        }
        QLabel#kpi_value {
            color: #f8fafc;
            font-size: 17px;
            font-weight: 800;
            font-family: 'Consolas', monospace;
        }

        /* Statistics KPI Labels */
        QLabel#stat_hero_value {
            color: #f8fafc;
            font-size: 32px;
            font-weight: 800;
            font-family: 'Consolas', monospace;
        }
        QLabel#stat_sub_value {
            color: #94a3b8;
            font-size: 20px;
            font-weight: 700;
            font-family: 'Consolas', monospace;
        }
        QLabel#stat_sub_text {
            color: #94a3b8;
            font-size: 16px;
            font-weight: 700;
        }

        /* Form Inputs */
        QLineEdit, QSpinBox {
            background: #090d16;
            border: 1.5px solid #1e293b;
            border-radius: 9px;
            padding: 8px 12px;
            min-height: 22px;
            color: #f8fafc;
            font-size: 13px;
        }
        QLineEdit:focus, QSpinBox:focus {
            background: #0f172a;
            border: 2px solid #bef264;
            padding: 7px 11px;
        }
        QLineEdit:disabled, QSpinBox:disabled {
            background: #111827;
            color: #475569;
            border-color: #1f2937;
        }

        /* Buttons */
        QPushButton {
            background: #1e293b;
            color: #f1f5f9;
            border: 1px solid #334155;
            border-radius: 9px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 700;
        }
        QPushButton:hover {
            border-color: #bef264;
            background: #273549;
            color: #ffffff;
        }
        QPushButton:pressed {
            background: #172033;
        }

        /* Hero timer action buttons */
        QPushButton#hero_start {
            background: #bef264;
            color: #090d16;
            border: 1px solid #bef264;
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }
        QPushButton#hero_start:hover {
            background: #d9f99d;
            border-color: #d9f99d;
            color: #000000;
        }
        QPushButton#hero_pause {
            background: #451a03;
            color: #fde68a;
            border: 1.5px solid #78350f;
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }
        QPushButton#hero_pause:hover {
            background: #78350f;
            border-color: #b45309;
        }
        QPushButton#hero_resume {
            background: #064e3b;
            color: #a7f3d0;
            border: 1.5px solid #065f46;
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }
        QPushButton#hero_resume:hover {
            background: #065f46;
            border-color: #10b981;
        }

        QPushButton#stop {
            background: #450a0a;
            color: #fca5a5;
            border: 1px solid #7f1d1d;
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }
        QPushButton#stop:hover {
            background: #7f1d1d;
            border-color: #991b1b;
        }

        QPushButton#complete {
            background: #059669;
            color: #ffffff;
            border: 1px solid #047857;
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }
        QPushButton#complete:hover {
            background: #10b981;
        }

        QPushButton#danger {
            background: #dc2626;
            color: #ffffff;
            border: 1px solid #b91c1c;
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }
        QPushButton#danger:hover {
            background: #ef4444;
        }

        QPushButton#comment_action {
            background: #1e293b;
            color: #e2e8f0;
            border: 1px solid #334155;
            border-radius: 9px;
            padding: 9px 16px;
            font-size: 12px;
            font-weight: 700;
        }
        QPushButton#comment_action:hover {
            background: #273549;
            border-color: #bef264;
            color: #ffffff;
        }

        /* Steppers numéricos */
        QPushButton#stepper_button {
            background: #1e293b;
            color: #f1f5f9;
            border: 1px solid #334155;
            border-radius: 8px;
            min-width: 32px;
            max-width: 32px;
            min-height: 32px;
            max-height: 32px;
            padding: 0px;
        }
        QPushButton#stepper_button:hover {
            background: #273549;
            border-color: #bef264;
            color: #ffffff;
        }
        QPushButton#stepper_button:pressed {
            background: #0f172a;
        }
        QPushButton#stepper_button:disabled {
            background: #111827;
            color: #475569;
            border-color: #1f2937;
        }

        QPushButton#toolbar_primary {
            background: #bef264;
            color: #090d16;
            border: 1px solid #bef264;
            font-weight: 800;
            padding: 8px 16px;
            border-radius: 8px;
        }
        QPushButton#toolbar_primary:hover {
            background: #d9f99d;
            color: #000000;
        }

        QPushButton#secondary_action {
            background: #1e293b;
            color: #e2e8f0;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 8px 14px;
            font-weight: 700;
        }
        QPushButton#secondary_action:hover {
            background: #273549;
            border-color: #bef264;
            color: #ffffff;
        }

        QPushButton#table_action_icon {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 4px;
            min-width: 28px;
            min-height: 28px;
        }
        QPushButton#table_action_icon:hover {
            background: #273549;
            border-color: #64748b;
        }

        QPushButton#table_delete_icon {
            background: #450a0a;
            border: 1px solid #7f1d1d;
            border-radius: 6px;
            padding: 4px;
            min-width: 28px;
            min-height: 28px;
        }
        QPushButton#table_delete_icon:hover {
            background: #7f1d1d;
            border-color: #ef4444;
        }

        /* Table Badges */
        QLabel#table_badge_completed {
            background: #064e3b;
            color: #6ee7b7;
            border: 1px solid #059669;
            border-radius: 6px;
            padding: 2px 8px;
            font-weight: 700;
            font-size: 11px;
        }
        QLabel#table_badge_incomplete {
            background: #450a0a;
            color: #fca5a5;
            border: 1px solid #7f1d1d;
            border-radius: 6px;
            padding: 2px 8px;
            font-weight: 700;
            font-size: 11px;
        }

        /* Table */
        QTableWidget {
            background: #0d121f;
            border: 1px solid #1e293b;
            border-radius: 12px;
            gridline-color: #1e293b;
            alternate-background-color: #111827;
            selection-background-color: #1e293b;
            selection-color: #ffffff;
            color: #f1f5f9;
        }
        QHeaderView::section {
            background: #090d16;
            color: #94a3b8;
            border: none;
            border-bottom: 1.5px solid #1e293b;
            padding: 10px 8px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;
        }

        /* Progress Bar */
        QProgressBar {
            background: #111827;
            border: 1px solid #1e293b;
            border-radius: 8px;
            text-align: center;
            color: #f8fafc;
            font-weight: 700;
            font-size: 11px;
            min-height: 20px;
        }
        QProgressBar::chunk {
            background: #84cc16;
            border-radius: 7px;
        }

        /* Scrollbars */
        QScrollBar:vertical {
            background: #090d16;
            width: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #1e293b;
            min-height: 24px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #334155;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QScrollBar:horizontal {
            background: #090d16;
            height: 10px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background: #1e293b;
            min-width: 24px;
            border-radius: 5px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #334155;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }

        /* Dialogs and Lists */
        QListWidget {
            background: #090d16;
            color: #f8fafc;
            border: 1px solid #1e293b;
            border-radius: 8px;
        }
        QListWidget::item {
            padding: 8px;
            border-radius: 6px;
        }
        QListWidget::item:hover {
            background: #1e293b;
        }
        QListWidget::item:selected {
            background: #1e293b;
            color: #bef264;
        }
        QCheckBox {
            color: #f1f5f9;
        }

        /* Filters and Sorting Panel */
        QFrame#filter_panel {
            background: #0b1120;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 6px 12px;
        }
        QLabel#filter_label {
            color: #94a3b8;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;
        }
        QComboBox {
            background: #111827;
            color: #e2e8f0;
            border: 1px solid #1e293b;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 12px;
            min-height: 22px;
        }
        QComboBox:hover {
            border-color: #334155;
            background: #1a2234;
        }
        QComboBox:focus {
            border-color: #bef264;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: none;
        }
        QComboBox QAbstractItemView {
            background: #0f172a;
            color: #f1f5f9;
            border: 1px solid #334155;
            selection-background-color: #1e293b;
            selection-color: #bef264;
            padding: 4px;
            outline: none;
        }
        QPushButton#filter_reset_btn {
            background: #1e293b;
            color: #94a3b8;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 700;
        }
        QPushButton#filter_reset_btn:hover {
            background: #334155;
            color: #f8fafc;
            border-color: #64748b;
        }
        QPushButton#sort_dir_btn {
            background: #1e293b;
            color: #bef264;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 4px 8px;
            font-weight: 800;
            min-width: 28px;
        }
        QPushButton#sort_dir_btn:hover {
            background: #273549;
            border-color: #bef264;
        }

        /* Excel Filter Popup */
        QDialog#excelFilterPopup {
            background: #0d121f;
            border: 1px solid #334155;
            border-radius: 10px;
        }
        QLabel#filter_popup_title {
            color: #bef264;
            font-size: 13px;
            font-weight: 800;
        }
        QPushButton#filter_sort_btn {
            background: #111827;
            color: #e2e8f0;
            border: 1px solid #1e293b;
            border-radius: 6px;
            text-align: left;
            padding: 6px 10px;
            font-size: 12px;
            font-weight: 600;
        }
        QPushButton#filter_sort_btn:hover {
            background: #1e293b;
            border-color: #3b82f6;
            color: #ffffff;
        }
        QFrame#filter_sep {
            color: #1e293b;
            background-color: #1e293b;
            height: 1px;
            border: none;
        }
        QListWidget#excelFilterList {
            background: #090d16;
            color: #f1f5f9;
            border: 1px solid #1e293b;
            border-radius: 6px;
        }
        QListWidget#excelFilterList::item {
            padding: 4px 6px;
            border-radius: 4px;
        }
        QListWidget#excelFilterList::item:hover {
            background: #1e293b;
        }
        """

    # --- MODO CLARO (Default / Classic) ---
    return """
        /* --- MODO CLARO --- */
        QWidget {
            color: #0f172a;
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            font-size: 13px;
        }
        QMainWindow {
            background: #f8fafc;
        }
        QDialog {
            background: #f8fafc;
            color: #0f172a;
        }
        QToolTip {
            background-color: #0f172a;
            color: #f8fafc;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 5px 8px;
            font-size: 12px;
        }

        /* Top Toolbar */
        QToolBar#main_toolbar {
            background: #ffffff;
            border-bottom: 1px solid #e2e8f0;
            padding: 5px 12px;
            spacing: 8px;
        }
        QToolButton#file_toolbar_button, QToolButton#view_toolbar_button, QToolButton#config_toolbar_button {
            background: #ffffff;
            color: #1e293b;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 6px 14px;
            font-size: 12px;
            font-weight: 700;
        }
        QToolButton#file_toolbar_button:hover, QToolButton#view_toolbar_button:hover, QToolButton#config_toolbar_button:hover {
            background: #f8fafc;
            border-color: #84cc16;
            color: #0f172a;
        }
        QToolButton#file_toolbar_button:pressed, QToolButton#view_toolbar_button:pressed, QToolButton#config_toolbar_button:pressed {
            background: #f1f5f9;
        }

        /* Menus */
        QMenu {
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 6px;
        }
        QMenu::item {
            background-color: transparent;
            color: #1e293b;
            padding: 7px 26px 7px 14px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
        }
        QMenu::item:selected {
            background-color: #f1f5f9;
            color: #0f172a;
        }
        QMenu::item:disabled {
            color: #94a3b8;
        }
        QMenu::separator {
            height: 1px;
            background: #e2e8f0;
            margin: 4px 8px;
        }
        QMenu::indicator {
            width: 16px;
            height: 16px;
            margin-left: 4px;
        }

        /* Tabs */
        QTabWidget::pane {
            border: none;
            background: #f8fafc;
        }
        QTabBar {
            background: #0f172a;
            border: none;
        }
        QTabBar::tab {
            background: #0f172a;
            color: #94a3b8;
            padding: 13px 28px;
            border: none;
            font-size: 13px;
            font-weight: 700;
            min-width: 140px;
        }
        QTabBar::tab:selected {
            color: #bef264;
            background: #1e293b;
            border-bottom: 3px solid #bef264;
        }
        QTabBar::tab:hover:!selected {
            color: #f8fafc;
            background: #1e293b;
        }

        /* Scroll containers */
        QScrollArea#homeScroll, QScrollArea#statsScroll {
            background: transparent;
            border: none;
        }
        QWidget#homeContainer, QWidget#statsContainer {
            background: transparent;
        }

        /* Headers & Meta */
        QLabel#brand {
            color: #0f172a;
            font-size: 26px;
            font-weight: 800;
            letter-spacing: -0.5px;
        }
        QLabel#eyebrow {
            color: #64748b;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 1.2px;
        }
        QLabel#record_meta {
            color: #64748b;
            font-size: 12px;
            font-weight: 700;
        }
        QLabel#location_badge {
            background: #f8fafc;
            border: 1.5px solid #e2e8f0;
            border-radius: 10px;
            color: #0f172a;
            font-size: 24px;
            font-weight: 800;
            padding: 8px 16px;
        }
        QLabel#status {
            color: #64748b;
            font-size: 13px;
            font-weight: 600;
        }
        QLabel#status_badge {
            background: #f1f5f9;
            color: #475569;
            border: 1px solid #cbd5e1;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;
            padding: 5px 12px;
        }

        /* Cards */
        QFrame#heroCard, QFrame#metricCard, QFrame#sectionCard, QFrame#panelCard, QFrame#kpiCard {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
        }
        QFrame#heroCard {
            border-top: 3px solid #84cc16;
        }

        /* Clocks */
        QFrame#exerciseCard, QFrame#breakCard {
            background: #090d16;
            border: 1px solid #1e293b;
            border-radius: 14px;
        }
        QLabel#digital_clock_exercise {
            color: #e2e8f0;
            font-family: 'Consolas', 'Cascadia Code', 'Segoe UI Mono', monospace;
            font-weight: 800;
        }
        QLabel#digital_clock_break {
            color: #94a3b8;
            font-family: 'Consolas', 'Cascadia Code', 'Segoe UI Mono', monospace;
            font-weight: 700;
        }

        /* Header today card */
        QFrame#todayCard {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
        }
        QLabel#today_label {
            color: #64748b;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1px;
        }
        QLabel#today_value {
            color: #0f172a;
            font-size: 16px;
            font-weight: 800;
            font-family: 'Consolas', monospace;
        }

        /* KPI Cards in Registros */
        QLabel#kpi_title {
            color: #64748b;
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 1px;
        }
        QLabel#kpi_value {
            color: #0f172a;
            font-size: 17px;
            font-weight: 800;
            font-family: 'Consolas', monospace;
        }

        /* Statistics KPI Labels */
        QLabel#stat_hero_value {
            color: #0f172a;
            font-size: 32px;
            font-weight: 800;
            font-family: 'Consolas', monospace;
        }
        QLabel#stat_sub_value {
            color: #64748b;
            font-size: 20px;
            font-weight: 700;
            font-family: 'Consolas', monospace;
        }
        QLabel#stat_sub_text {
            color: #64748b;
            font-size: 16px;
            font-weight: 700;
        }

        /* Form Inputs */
        QLineEdit, QSpinBox {
            background: #f8fafc;
            border: 1.5px solid #cbd5e1;
            border-radius: 9px;
            padding: 8px 12px;
            min-height: 22px;
            color: #0f172a;
            font-size: 13px;
        }
        QLineEdit:focus, QSpinBox:focus {
            background: #ffffff;
            border: 2px solid #84cc16;
            padding: 7px 11px;
        }
        QLineEdit:disabled, QSpinBox:disabled {
            background: #f1f5f9;
            color: #94a3b8;
            border-color: #e2e8f0;
        }

        /* Buttons */
        QPushButton {
            background: #ffffff;
            color: #1e293b;
            border: 1px solid #cbd5e1;
            border-radius: 9px;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 700;
        }
        QPushButton:hover {
            border-color: #84cc16;
            background: #f8fafc;
            color: #0f172a;
        }
        QPushButton:pressed {
            background: #f1f5f9;
        }

        /* Hero timer action buttons */
        QPushButton#hero_start {
            background: #0f172a;
            color: #bef264;
            border: 1px solid #0f172a;
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }
        QPushButton#hero_start:hover {
            background: #1e293b;
            border-color: #1e293b;
            color: #d9f99d;
        }
        QPushButton#hero_pause {
            background: #fffbeb;
            color: #b45309;
            border: 1.5px solid #fde68a;
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }
        QPushButton#hero_pause:hover {
            background: #fef3c7;
            border-color: #f59e0b;
        }
        QPushButton#hero_resume {
            background: #ecfdf5;
            color: #047857;
            border: 1.5px solid #a7f3d0;
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }
        QPushButton#hero_resume:hover {
            background: #d1fae5;
            border-color: #10b981;
        }

        QPushButton#stop {
            background: #fef2f2;
            color: #dc2626;
            border: 1px solid #fecaca;
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }
        QPushButton#stop:hover {
            background: #fee2e2;
            border-color: #ef4444;
        }

        QPushButton#complete {
            background: #10b981;
            color: #ffffff;
            border: 1px solid #059669;
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }
        QPushButton#complete:hover {
            background: #059669;
        }

        QPushButton#danger {
            background: #ef4444;
            color: #ffffff;
            border: 1px solid #dc2626;
            font-size: 13px;
            font-weight: 800;
            padding: 10px 18px;
            border-radius: 10px;
        }
        QPushButton#danger:hover {
            background: #dc2626;
        }

        QPushButton#comment_action {
            background: #f8fafc;
            color: #334155;
            border: 1px solid #cbd5e1;
            border-radius: 9px;
            padding: 9px 16px;
            font-size: 12px;
            font-weight: 700;
        }
        QPushButton#comment_action:hover {
            background: #f1f5f9;
            border-color: #94a3b8;
            color: #0f172a;
        }

        /* Steppers numéricos */
        QPushButton#stepper_button {
            background: #ffffff;
            color: #1e293b;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            min-width: 32px;
            max-width: 32px;
            min-height: 32px;
            max-height: 32px;
            padding: 0px;
        }
        QPushButton#stepper_button:hover {
            background: #f8fafc;
            border-color: #84cc16;
            color: #0f172a;
        }
        QPushButton#stepper_button:pressed {
            background: #e2e8f0;
        }
        QPushButton#stepper_button:disabled {
            background: #f1f5f9;
            color: #94a3b8;
            border-color: #e2e8f0;
        }

        QPushButton#toolbar_primary {
            background: #0f172a;
            color: #bef264;
            border: 1px solid #0f172a;
            font-weight: 800;
            padding: 8px 16px;
            border-radius: 8px;
        }
        QPushButton#toolbar_primary:hover {
            background: #1e293b;
            color: #d9f99d;
        }

        QPushButton#secondary_action {
            background: #ffffff;
            color: #334155;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 8px 14px;
            font-weight: 700;
        }
        QPushButton#secondary_action:hover {
            background: #f8fafc;
            border-color: #94a3b8;
            color: #0f172a;
        }

        QPushButton#table_action_icon {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 4px;
            min-width: 28px;
            min-height: 28px;
        }
        QPushButton#table_action_icon:hover {
            background: #f1f5f9;
            border-color: #cbd5e1;
        }

        QPushButton#table_delete_icon {
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 6px;
            padding: 4px;
            min-width: 28px;
            min-height: 28px;
        }
        QPushButton#table_delete_icon:hover {
            background: #fee2e2;
            border-color: #ef4444;
        }

        /* Table Badges */
        QLabel#table_badge_completed {
            background: #ecfdf5;
            color: #047857;
            border: 1px solid #a7f3d0;
            border-radius: 6px;
            padding: 2px 8px;
            font-weight: 700;
            font-size: 11px;
        }
        QLabel#table_badge_incomplete {
            background: #fef2f2;
            color: #b91c1c;
            border: 1px solid #fecaca;
            border-radius: 6px;
            padding: 2px 8px;
            font-weight: 700;
            font-size: 11px;
        }

        /* Table */
        QTableWidget {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            gridline-color: #f1f5f9;
            alternate-background-color: #f8fafc;
            selection-background-color: #f1f5f9;
            selection-color: #0f172a;
            color: #0f172a;
        }
        QHeaderView::section {
            background: #f8fafc;
            color: #475569;
            border: none;
            border-bottom: 1.5px solid #e2e8f0;
            padding: 10px 8px;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;
        }

        /* Progress Bar */
        QProgressBar {
            background: #f1f5f9;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            text-align: center;
            color: #0f172a;
            font-weight: 700;
            font-size: 11px;
            min-height: 20px;
        }
        QProgressBar::chunk {
            background: #84cc16;
            border-radius: 7px;
        }

        /* Scrollbars */
        QScrollBar:vertical {
            background: #f8fafc;
            width: 10px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background: #cbd5e1;
            min-height: 24px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #94a3b8;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QScrollBar:horizontal {
            background: #f8fafc;
            height: 10px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background: #cbd5e1;
            min-width: 24px;
            border-radius: 5px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #94a3b8;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }

        /* Dialogs and Lists */
        QListWidget {
            background: #ffffff;
            color: #0f172a;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }
        QListWidget::item {
            padding: 8px;
            border-radius: 6px;
        }
        QListWidget::item:hover {
            background: #f1f5f9;
        }
        QListWidget::item:selected {
            background: #f1f5f9;
            color: #0f172a;
        }
        QCheckBox {
            color: #0f172a;
        }

        /* Filters and Sorting Panel */
        QFrame#filter_panel {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 6px 12px;
        }
        QLabel#filter_label {
            color: #64748b;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 0.5px;
        }
        QComboBox {
            background: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 12px;
            min-height: 22px;
        }
        QComboBox:hover {
            border-color: #94a3b8;
            background: #f8fafc;
        }
        QComboBox:focus {
            border-color: #65a30d;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: none;
        }
        QComboBox QAbstractItemView {
            background: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            selection-background-color: #f1f5f9;
            selection-color: #0f172a;
            padding: 4px;
            outline: none;
        }
        QPushButton#filter_reset_btn {
            background: #f1f5f9;
            color: #64748b;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 700;
        }
        QPushButton#filter_reset_btn:hover {
            background: #e2e8f0;
            color: #0f172a;
            border-color: #94a3b8;
        }
        QPushButton#sort_dir_btn {
            background: #f1f5f9;
            color: #4d7c0f;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            padding: 4px 8px;
            font-weight: 800;
            min-width: 28px;
        }
        QPushButton#sort_dir_btn:hover {
            background: #e2e8f0;
            border-color: #65a30d;
        }

        /* Excel Filter Popup */
        QDialog#excelFilterPopup {
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 10px;
        }
        QLabel#filter_popup_title {
            color: #0f172a;
            font-size: 13px;
            font-weight: 800;
        }
        QPushButton#filter_sort_btn {
            background: #f8fafc;
            color: #334155;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            text-align: left;
            padding: 6px 10px;
            font-size: 12px;
            font-weight: 600;
        }
        QPushButton#filter_sort_btn:hover {
            background: #f1f5f9;
            border-color: #3b82f6;
            color: #0f172a;
        }
        QFrame#filter_sep {
            color: #e2e8f0;
            background-color: #e2e8f0;
            height: 1px;
            border: none;
        }
        QListWidget#excelFilterList {
            background: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
        }
        QListWidget#excelFilterList::item {
            padding: 4px 6px;
            border-radius: 4px;
        }
        QListWidget#excelFilterList::item:hover {
            background: #f1f5f9;
        }
        """


def get_dialog_stylesheet(theme: str) -> str:
    """Devuelve el estilo para el diálogo de selección inicial según el tema."""
    if theme == THEME_DARK:
        return """
            QDialog { background: #0f172a; }
            QLabel#title { color: #f8fafc; font-size: 22px; font-weight: 800; }
            QLabel#subtitle { color: #94a3b8; font-size: 13px; }
            QLabel#version { color: #64748b; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
            QListWidget { background: #090d16; color: #f8fafc; border: 1px solid #1e293b; border-radius: 8px; min-height: 96px; }
            QListWidget::item:hover { background: #1e293b; }
            QListWidget::item:selected { background: #1e293b; color: #bef264; }
            QPushButton { min-height: 38px; min-width: 140px; border-radius: 9px; font-size: 12px; font-weight: 700; }
            QPushButton#primary { background: #bef264; color: #090d16; border: 1px solid #bef264; font-weight: 800; }
            QPushButton#primary:hover { background: #d9f99d; }
            QPushButton#secondary { background: #1e293b; color: #f1f5f9; border: 1px solid #334155; }
            QPushButton#secondary:hover { background: #273549; border-color: #bef264; }
            QPushButton#ghost { background: transparent; color: #94a3b8; border: 1px solid #1e293b; }
            QPushButton#ghost:hover { background: #1e293b; color: #f8fafc; }
        """
    return """
        QDialog { background: #f8fafc; }
        QLabel#title { color: #0f172a; font-size: 22px; font-weight: 800; }
        QLabel#subtitle { color: #64748b; font-size: 13px; }
        QLabel#version { color: #94a3b8; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
        QListWidget { background: #ffffff; color: #0f172a; border: 1px solid #e2e8f0; border-radius: 8px; min-height: 96px; }
        QListWidget::item:hover { background: #f1f5f9; }
        QListWidget::item:selected { background: #f1f5f9; color: #0f172a; }
        QPushButton { min-height: 38px; min-width: 140px; border-radius: 9px; font-size: 12px; font-weight: 700; }
        QPushButton#primary { background: #0f172a; color: #bef264; border: 1px solid #0f172a; font-weight: 800; }
        QPushButton#primary:hover { background: #1e293b; }
        QPushButton#secondary { background: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; }
        QPushButton#secondary:hover { background: #f8fafc; border-color: #84cc16; }
        QPushButton#ghost { background: transparent; color: #64748b; border: 1px solid #e2e8f0; }
        QPushButton#ghost:hover { background: #f1f5f9; }
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
        return "background: #f1f5f9; color: #334155; border: 1px solid #cbd5e1; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;"
    elif state == "play":
        if is_dark:
            return "background: #064e3b; color: #6ee7b7; border: 1px solid #059669; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;"
        return "background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;"
    elif state == "break":
        if is_dark:
            return "background: #451a03; color: #fde68a; border: 1px solid #78350f; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;"
        return "background: #fffbeb; color: #b45309; border: 1px solid #fde68a; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;"
    else:  # waiting / idle
        if is_dark:
            return "background: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;"
        return "background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; border-radius: 10px; font-size: 11px; font-weight: 800; padding: 5px 12px;"


def get_timer_cards_style(state: str, is_dark: bool) -> tuple[str, str]:
    """Devuelve la tupla de estilos (exercise_card_style, break_card_style) según el estado.

    Args:
        state: 'paused', 'play', 'break', o 'waiting'.
        is_dark: True si el tema activo es oscuro.
    """
    if state == "paused":
        return (
            "QFrame#exerciseCard { background: #050811; border: 1px solid #334155; border-radius: 14px; }",
            "QFrame#breakCard { background: #050811; border: 1px solid #334155; border-radius: 14px; }",
        )
    elif state == "play":
        return (
            "QFrame#exerciseCard { background: #071510; border: 2px solid #10b981; border-radius: 14px; }",
            "QFrame#breakCard { background: #050811; border: 1px solid #1e293b; border-radius: 14px; }",
        )
    elif state == "break":
        return (
            "QFrame#exerciseCard { background: #050811; border: 1px solid #1e293b; border-radius: 14px; }",
            "QFrame#breakCard { background: #191408; border: 2px solid #f59e0b; border-radius: 14px; }",
        )
    else:  # waiting
        return (
            "QFrame#exerciseCard { background: #050811; border: 1px solid #1e293b; border-radius: 14px; }",
            "QFrame#breakCard { background: #050811; border: 1px solid #1e293b; border-radius: 14px; }",
        )

