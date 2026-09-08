"""Layout de flujo dinámico (FlowLayout) para PySide6.

Distribuye los widgets horizontalmente uno al lado del otro con espaciado constante,
y salta a la siguiente línea cuando se alcanza el límite de ancho disponible (flex-wrap).
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QLayoutItem, QSizePolicy, QWidget


class FlowLayout(QLayout):
    """Layout estilo flex-wrap que distribuye widgets horizontalmente con salto de línea.

    Garantiza que todos los elementos tengan un espaciado horizontal y vertical uniforme,
    sin forzar anchos de columnas rígidas como ocurre con QGridLayout.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        margin: int = 0,
        h_spacing: int = 8,
        v_spacing: int = 8,
    ) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self) -> None:
        while self._items:
            self.takeAt(0)

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def horizontalSpacing(self) -> int:
        return self._h_spacing

    def verticalSpacing(self) -> int:
        return self._v_spacing

    def setHorizontalSpacing(self, spacing: int) -> None:
        self._h_spacing = spacing
        self.invalidate()

    def setVerticalSpacing(self, spacing: int) -> None:
        self._v_spacing = spacing
        self.invalidate()

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int) -> QLayoutItem | None:
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), apply_geometry=False)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, apply_geometry=True)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, apply_geometry: bool) -> int:
        margins = self.contentsMargins()
        effective_rect = rect.adjusted(
            margins.left(), margins.top(), -margins.right(), -margins.bottom()
        )
        x = effective_rect.x()
        y = effective_rect.y()
        space_x = self.horizontalSpacing()
        space_y = self.verticalSpacing()

        lines: list[list[tuple[QLayoutItem, int, QSize]]] = []
        current_line: list[tuple[QLayoutItem, int, QSize]] = []

        for item in self._items:
            item_size = item.sizeHint()
            next_x = x + item_size.width() + space_x
            if next_x - space_x > effective_rect.right() and current_line:
                lines.append(current_line)
                current_line = []
                x = effective_rect.x()
                next_x = x + item_size.width() + space_x

            current_line.append((item, x, item_size))
            x = next_x

        if current_line:
            lines.append(current_line)

        for line in lines:
            line_height = max(item_size.height() for _, _, item_size in line)
            if apply_geometry:
                for item, item_x, item_size in line:
                    item_y = y + (line_height - item_size.height()) // 2
                    item.setGeometry(QRect(QPoint(item_x, item_y), item_size))
            y += line_height + space_y

        total_y = y - space_y if lines else effective_rect.y()
        return total_y - rect.y() + margins.bottom()
