"""Superposición visual de partículas ambientales para skins dinámicos de Study Timetrial.

Proporciona efectos atmosféricos sutiles (pétalos de sakura, nieve, estrellas,
hojas de bambú, rescoldos de Halloween/Vampyr) sin interferir en la usabilidad,
legibilidad ni eventos del ratón.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
import random

from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


def _is_test_env() -> bool:
    """Detecta si la aplicación se ejecuta en suite de tests o en modo offscreen."""
    return bool(os.environ.get("STUDY_TIMETRIAL_TEST") or os.environ.get("QT_QPA_PLATFORM") == "offscreen")


@dataclass
class Particle:
    """Estado y propiedades de una partícula ambiental individual."""

    x: float
    y: float
    vx: float
    vy: float
    size: float
    alpha: float
    rotation: float
    v_rot: float
    phase: float
    wobble_speed: float
    color_hex: str
    kind: str


class AmbientParticleOverlay(QWidget):
    """Widget de superposición transparente e interactiva para partículas ambientales.

    Garantiza WA_TransparentForMouseEvents para que el usuario pueda interactuar
    con botones, tablas y campos de texto situados debajo sin ninguna interferencia.
    """

    SUPPORTED_EFFECTS = {
        "sakura",
        "snow",
        "stars",
        "bamboo",
        "leaves",
        "halloween",
        "vampyr",
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ambient_particle_overlay")

        # Configuración de widget pasivo no bloqueante
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._effect: str = "none"
        self._particles: list[Particle] = []
        self._timer = QTimer(self)
        self._timer.setInterval(33)  # ~30 FPS para máxima fluidez con bajo impacto de CPU
        self._timer.timeout.connect(self._update_particles)

        if parent is not None:
            parent.installEventFilter(self)
            self.setGeometry(parent.rect())

    @property
    def current_effect(self) -> str:
        """Nombre del efecto actualmente activo ('none' si está desactivado)."""
        return self._effect

    def set_effect(self, effect: str) -> None:
        """Establece o cambia el efecto ambiental.

        Si effect es 'none' o vacío, el timer se detiene y el overlay se oculta,
        liberando el 100% de los ciclos de renderizado.
        """
        cleaned = (effect or "none").strip().lower()
        if cleaned == self._effect and self._particles:
            return

        self._effect = cleaned

        if self._effect in ("none", "") or self._effect not in self.SUPPORTED_EFFECTS:
            self._timer.stop()
            self._particles.clear()
            self.hide()
            return

        # Inicializar partículas y activar animación
        w = max(self.width(), 800)
        h = max(self.height(), 600)
        self._init_particles(w, h)
        self.show()
        self.raise_()

        if not _is_test_env() and not self._timer.isActive():
            self._timer.start()

        self.update()

    def _init_particles(self, w: int, h: int) -> None:
        """Crea el conjunto de partículas calibrado según la temática elegida."""
        self._particles.clear()
        count = 30  # Cantidad óptima: atmósfera zen sin saturar la pantalla

        if self._effect == "sakura":
            palette = ["#fbcfe8", "#f472b6", "#fda4af", "#fecdd3", "#ffffff"]
            for _ in range(count):
                self._particles.append(
                    Particle(
                        x=random.uniform(0, w),
                        y=random.uniform(-h, h),
                        vx=random.uniform(0.3, 0.9),
                        vy=random.uniform(0.7, 1.6),
                        size=random.uniform(9.0, 15.0),
                        alpha=random.uniform(0.25, 0.45),
                        rotation=random.uniform(0, 360),
                        v_rot=random.uniform(-1.5, 1.5),
                        phase=random.uniform(0, math.tau),
                        wobble_speed=random.uniform(0.02, 0.05),
                        color_hex=random.choice(palette),
                        kind="sakura",
                    )
                )

        elif self._effect == "snow":
            palette = ["#ffffff", "#e0f2fe", "#bae6fd", "#f0f9ff"]
            for _ in range(count + 5):
                self._particles.append(
                    Particle(
                        x=random.uniform(0, w),
                        y=random.uniform(-h, h),
                        vx=random.uniform(-0.2, 0.4),
                        vy=random.uniform(0.6, 1.4),
                        size=random.uniform(3.0, 7.0),
                        alpha=random.uniform(0.20, 0.50),
                        rotation=random.uniform(0, 360),
                        v_rot=random.uniform(-0.8, 0.8),
                        phase=random.uniform(0, math.tau),
                        wobble_speed=random.uniform(0.015, 0.04),
                        color_hex=random.choice(palette),
                        kind="snow",
                    )
                )

        elif self._effect == "stars":
            palette = ["#ffffff", "#c4b5fd", "#e0e7ff", "#f5d0fe", "#a78bfa"]
            for _ in range(count):
                self._particles.append(
                    Particle(
                        x=random.uniform(0, w),
                        y=random.uniform(0, h),
                        vx=random.uniform(-0.05, 0.05),
                        vy=random.uniform(0.02, 0.10),
                        size=random.uniform(2.5, 6.0),
                        alpha=random.uniform(0.20, 0.55),
                        rotation=random.uniform(0, 360),
                        v_rot=random.uniform(-0.5, 0.5),
                        phase=random.uniform(0, math.tau),
                        wobble_speed=random.uniform(0.03, 0.08),  # Pulso de brillo
                        color_hex=random.choice(palette),
                        kind="stars",
                    )
                )

        elif self._effect == "bamboo":
            palette = ["#84cc16", "#a3e635", "#65a30d", "#4d7c0f", "#bef264"]
            for _ in range(24):
                self._particles.append(
                    Particle(
                        x=random.uniform(0, w),
                        y=random.uniform(-h, h),
                        vx=random.uniform(0.4, 1.1),
                        vy=random.uniform(0.9, 1.8),
                        size=random.uniform(10.0, 18.0),
                        alpha=random.uniform(0.22, 0.40),
                        rotation=random.uniform(0, 360),
                        v_rot=random.uniform(-1.8, 1.8),
                        phase=random.uniform(0, math.tau),
                        wobble_speed=random.uniform(0.02, 0.05),
                        color_hex=random.choice(palette),
                        kind="bamboo",
                    )
                )

        elif self._effect == "leaves":
            palette = ["#4ade80", "#86efac", "#22c55e", "#bbf7d0"]
            for _ in range(24):
                self._particles.append(
                    Particle(
                        x=random.uniform(0, w),
                        y=random.uniform(-h, h),
                        vx=random.uniform(0.3, 0.9),
                        vy=random.uniform(0.7, 1.5),
                        size=random.uniform(8.0, 14.0),
                        alpha=random.uniform(0.20, 0.38),
                        rotation=random.uniform(0, 360),
                        v_rot=random.uniform(-1.2, 1.2),
                        phase=random.uniform(0, math.tau),
                        wobble_speed=random.uniform(0.02, 0.04),
                        color_hex=random.choice(palette),
                        kind="leaves",
                    )
                )

        elif self._effect == "halloween":
            palette = ["#fb923c", "#ea580c", "#f97316", "#f59e0b", "#c2410c"]
            for _ in range(count):
                self._particles.append(
                    Particle(
                        x=random.uniform(0, w),
                        y=random.uniform(0, h),
                        vx=random.uniform(-0.3, 0.3),
                        vy=random.uniform(-1.2, -0.4),  # Rescoldos flotando hacia arriba
                        size=random.uniform(3.5, 7.5),
                        alpha=random.uniform(0.25, 0.55),
                        rotation=random.uniform(0, 360),
                        v_rot=random.uniform(-2.0, 2.0),
                        phase=random.uniform(0, math.tau),
                        wobble_speed=random.uniform(0.04, 0.09),
                        color_hex=random.choice(palette),
                        kind="halloween",
                    )
                )

        elif self._effect == "vampyr":
            palette = ["#ef4444", "#dc2626", "#b91c1c", "#991b1b", "#7f1d1d"]
            for _ in range(count):
                self._particles.append(
                    Particle(
                        x=random.uniform(0, w),
                        y=random.uniform(0, h),
                        vx=random.uniform(-0.25, 0.25),
                        vy=random.uniform(-1.0, -0.3),  # Rescoldos carmesíes ascendentes
                        size=random.uniform(3.0, 7.0),
                        alpha=random.uniform(0.20, 0.50),
                        rotation=random.uniform(0, 360),
                        v_rot=random.uniform(-1.5, 1.5),
                        phase=random.uniform(0, math.tau),
                        wobble_speed=random.uniform(0.03, 0.08),
                        color_hex=random.choice(palette),
                        kind="vampyr",
                    )
                )

    def _update_particles(self) -> None:
        """Avanza la simulación física de cada partícula."""
        if not self.isVisible() or (self.window() and self.window().isMinimized()):
            return

        w = max(self.width(), 100)
        h = max(self.height(), 100)

        for p in self._particles:
            p.phase += p.wobble_speed
            p.rotation += p.v_rot

            # Movimiento ondulatorio suave en X
            wobble = math.sin(p.phase) * 0.4
            p.x += p.vx + wobble
            p.y += p.vy

            # Reposicionamiento cíclico fuera de bordes
            if p.vy > 0:  # Partículas descendentes
                if p.y > h + 20:
                    p.y = -20
                    p.x = random.uniform(0, w)
            else:  # Partículas ascendentes (halloween, vampyr)
                if p.y < -20:
                    p.y = h + 20
                    p.x = random.uniform(0, w)

            if p.x > w + 25:
                p.x = -20
            elif p.x < -25:
                p.x = w + 20

        self.update()

    def step_simulation(self) -> None:
        """Avanza manualmente la simulación (utilizado en pruebas automatizadas)."""
        self._update_particles()

    def paintEvent(self, event) -> None:
        """Renderiza las partículas con antialiasing y transparencia calibrada."""
        if self._effect in ("none", "") or not self._particles:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)

        for p in self._particles:
            # Calcular alpha pulsante suave para estrellas y rescoldos
            if p.kind in ("stars", "halloween", "vampyr"):
                pulse = 0.5 + 0.5 * math.sin(p.phase)
                current_alpha = max(0.1, min(0.65, p.alpha * (0.7 + 0.6 * pulse)))
            else:
                current_alpha = p.alpha

            color = QColor(p.color_hex)
            color.setAlphaF(current_alpha)
            painter.setBrush(QBrush(color))

            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(p.rotation)

            if p.kind == "sakura":
                # Silueta orgánica de pétalo de cerezo con leve concavidad en la punta
                path = QPainterPath()
                sz = p.size
                path.moveTo(0, -sz * 0.5)
                path.cubicTo(sz * 0.4, -sz * 0.25, sz * 0.4, sz * 0.35, 0, sz * 0.5)
                path.cubicTo(-sz * 0.4, sz * 0.35, -sz * 0.4, -sz * 0.25, 0, -sz * 0.5)
                painter.drawPath(path)

            elif p.kind == "bamboo":
                # Hoja esbelta lanceolada de bambú
                path = QPainterPath()
                sz = p.size
                path.moveTo(0, -sz * 0.5)
                path.cubicTo(sz * 0.22, -sz * 0.2, sz * 0.22, sz * 0.2, 0, sz * 0.5)
                path.cubicTo(-sz * 0.22, sz * 0.2, -sz * 0.22, -sz * 0.2, 0, -sz * 0.5)
                painter.drawPath(path)

            elif p.kind == "leaves":
                # Hoja pequeña de primavera
                path = QPainterPath()
                sz = p.size
                path.moveTo(0, -sz * 0.4)
                path.cubicTo(sz * 0.3, -sz * 0.15, sz * 0.3, sz * 0.25, 0, sz * 0.4)
                path.cubicTo(-sz * 0.3, sz * 0.25, -sz * 0.3, -sz * 0.15, 0, -sz * 0.4)
                painter.drawPath(path)

            elif p.kind == "snow":
                # Copo de nieve suave
                r = p.size * 0.5
                painter.drawEllipse(QPointF(0, 0), r, r)

            elif p.kind == "stars":
                # Estrella titilante de cuatro puntas
                sz = p.size
                path = QPainterPath()
                path.moveTo(0, -sz)
                path.lineTo(sz * 0.25, -sz * 0.25)
                path.lineTo(sz, 0)
                path.lineTo(sz * 0.25, sz * 0.25)
                path.lineTo(0, sz)
                path.lineTo(-sz * 0.25, sz * 0.25)
                path.lineTo(-sz, 0)
                path.lineTo(-sz * 0.25, -sz * 0.25)
                path.closeSubpath()
                painter.drawPath(path)

            elif p.kind in ("halloween", "vampyr"):
                # Rescoldo / chispa espectral con forma de rombo suave
                sz = p.size
                path = QPainterPath()
                path.moveTo(0, -sz * 0.7)
                path.lineTo(sz * 0.4, 0)
                path.lineTo(0, sz * 0.7)
                path.lineTo(-sz * 0.4, 0)
                path.closeSubpath()
                painter.drawPath(path)

            painter.restore()

        painter.end()

    def eventFilter(self, watched, event) -> bool:
        """Mantiene sincronizado el tamaño del overlay con el de su widget padre."""
        if watched == self.parent() and event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self.setGeometry(self.parent().rect())
            self.raise_()
        return super().eventFilter(watched, event)
