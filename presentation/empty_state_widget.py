"""Componente visual para el estado vacío (sin proyecto activo)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
import qtawesome as qta


class EmptyStateWidget(QWidget):
    """Panel de estado vacío que invita al usuario a abrir o crear un registro."""

    request_new = Signal()
    request_open = Signal()

    def __init__(
        self,
        title: str = "Ningún proyecto activo",
        subtitle: str = "Abre un registro existente o crea uno nuevo para comenzar a cronometrar y planificar tu estudio.",
        is_dark_mode: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title_text = title
        self._subtitle_text = subtitle
        self._is_dark = is_dark_mode

        self._init_ui()

    def _init_ui(self) -> None:
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 32, 24, 32)
        root_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Contenedor estilo tarjeta
        self.card = QFrame(self)
        self.card.setObjectName("emptyStateCard")
        self.card.setMaximumWidth(520)
        self.card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(32, 28, 32, 28)
        card_layout.setSpacing(14)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icono central
        self.icon_label = QLabel(self.card)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.icon_label)

        # Título
        self.title_label = QLabel(self._title_text, self.card)
        self.title_label.setObjectName("empty_state_title")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.title_label)

        # Subtítulo
        self.subtitle_label = QLabel(self._subtitle_text, self.card)
        self.subtitle_label.setObjectName("empty_state_subtitle")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        card_layout.addWidget(self.subtitle_label)

        # Botones de acción
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        buttons_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_new = QPushButton("  Crear nuevo registro", self.card)
        self.btn_new.setObjectName("empty_state_btn_new")
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.clicked.connect(self.request_new.emit)
        buttons_layout.addWidget(self.btn_new)

        self.btn_open = QPushButton("  Abrir registro...", self.card)
        self.btn_open.setObjectName("empty_state_btn_open")
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.clicked.connect(self.request_open.emit)
        buttons_layout.addWidget(self.btn_open)

        card_layout.addLayout(buttons_layout)
        root_layout.addWidget(self.card, 0, Qt.AlignmentFlag.AlignCenter)

        self._apply_theme()

    def set_dark_mode(self, is_dark: bool) -> None:
        self._is_dark = is_dark
        self._apply_theme()

    def _apply_theme(self) -> None:
        is_dark = self._is_dark
        icon_color = "#64748b" if is_dark else "#94a3b8"
        self.icon_label.setPixmap(qta.icon("fa5s.folder-open", color=icon_color).pixmap(48, 48))

        card_bg = "#111827" if is_dark else "#f8fafc"
        card_border = "#1f2937" if is_dark else "#e2e8f0"
        title_color = "#f9fafb" if is_dark else "#0f172a"
        sub_color = "#9ca3af" if is_dark else "#64748b"

        self.card.setStyleSheet(
            f"""
            QFrame#emptyStateCard {{
                background-color: {card_bg};
                border: 1px dashed {card_border};
                border-radius: 16px;
            }}
            """
        )

        self.title_label.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {title_color};"
        )
        self.subtitle_label.setStyleSheet(
            f"font-size: 13px; color: {sub_color}; line-height: 1.4;"
        )

        btn_new_bg = "#bef264" if is_dark else "#15803d"
        btn_new_fg = "#0f172a" if is_dark else "#ffffff"
        btn_new_hover = "#a3e635" if is_dark else "#166534"
        self.btn_new.setIcon(qta.icon("fa5s.plus", color=btn_new_fg))
        self.btn_new.setStyleSheet(
            f"""
            QPushButton#empty_state_btn_new {{
                background-color: {btn_new_bg};
                color: {btn_new_fg};
                font-size: 13px;
                font-weight: 700;
                padding: 9px 18px;
                border-radius: 8px;
                border: none;
            }}
            QPushButton#empty_state_btn_new:hover {{
                background-color: {btn_new_hover};
            }}
            """
        )

        btn_open_bg = "#1e293b" if is_dark else "#e2e8f0"
        btn_open_fg = "#f1f5f9" if is_dark else "#1e293b"
        btn_open_border = "#334155" if is_dark else "#cbd5e1"
        btn_open_hover = "#334155" if is_dark else "#cbd5e1"
        self.btn_open.setIcon(qta.icon("fa5s.folder-open", color=btn_open_fg))
        self.btn_open.setStyleSheet(
            f"""
            QPushButton#empty_state_btn_open {{
                background-color: {btn_open_bg};
                color: {btn_open_fg};
                font-size: 13px;
                font-weight: 600;
                padding: 9px 18px;
                border-radius: 8px;
                border: 1px solid {btn_open_border};
            }}
            QPushButton#empty_state_btn_open:hover {{
                background-color: {btn_open_hover};
            }}
            """
        )
