"""Reloj monotónico y estados de una sesión de estudio."""

from __future__ import annotations

import time
from enum import Enum

from domain.models import TimerItem


class TimerMode(Enum):
    """Representa el estado actual del contador."""

    WAITING = "waiting"
    PLAY = "play"
    BREAK = "break"


class TimerService:
    """Centraliza la lógica del cronómetro principal y del tiempo de descanso."""

    def __init__(self) -> None:
        self.mode = TimerMode.WAITING
        self.exercise_time_ms = 0
        self.break_time_ms = 0
        self._last_tick = 0.0
        self.is_paused = False

    def _sync(self) -> None:
        """Acumula el tiempo transcurrido según el estado actual del temporizador."""
        if self.mode is TimerMode.WAITING or self.is_paused:
            return

        now = time.perf_counter()
        delta = max(0, round((now - self._last_tick) * 1000))
        self._last_tick = now

        if self.mode is TimerMode.PLAY:
            self.exercise_time_ms += delta
        elif self.mode is TimerMode.BREAK:
            self.break_time_ms += delta

    def pause(self) -> None:
        """Pausa / congela los contadores sin alterar el modo."""
        if self.is_paused or self.mode is TimerMode.WAITING:
            return
        self._sync()
        self.is_paused = True

    def resume(self) -> None:
        """Reanuda los contadores sin acumular el lapso pausado."""
        if not self.is_paused:
            return
        self._last_tick = time.perf_counter()
        self.is_paused = False

    def start(self) -> None:
        """Inicia o reanuda el conteo del tiempo de ejercicio."""
        self._sync()
        self.is_paused = False
        self.mode = TimerMode.PLAY
        self._last_tick = time.perf_counter()

    def toggle_break(self) -> None:
        """Alterna entre modo de ejercicio y modo de descanso."""
        self._sync()
        self.is_paused = False
        self.mode = TimerMode.PLAY if self.mode is TimerMode.BREAK else TimerMode.BREAK
        self._last_tick = time.perf_counter()

    def reset(self) -> None:
        """Reinicia todos los contadores y deja el temporizador en espera."""
        self.mode = TimerMode.WAITING
        self.exercise_time_ms = 0
        self.break_time_ms = 0
        self._last_tick = 0.0
        self.is_paused = False

    def stop(self) -> TimerItem | None:
        """Detiene el contador sin devolver ningún item. Se mantiene por compatibilidad."""
        if self.mode is TimerMode.WAITING:
            return None
        self._sync()
        self.mode = TimerMode.WAITING
        self._last_tick = 0.0
        self.is_paused = False
        return None

    def snapshot(self) -> tuple[int, int]:
        """Devuelve el estado actual del ejercicio y del descanso."""
        self._sync()
        return self.exercise_time_ms, self.break_time_ms