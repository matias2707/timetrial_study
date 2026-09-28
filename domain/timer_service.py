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
    """Centraliza la lógica del cronómetro principal y del tiempo de descanso con precisión anclada."""

    def __init__(self) -> None:
        self.mode = TimerMode.WAITING
        self.exercise_time_ms = 0
        self.break_time_ms = 0
        self._segment_start: float | None = None
        self._last_tick: float = 0.0
        self.is_paused = False

    def _sync(self) -> None:
        """Sincroniza y consolida el tiempo transcurrido en el tramo activo sin derivas de reloj.

        Utiliza avance fraccional exacto: consume únicamente milisegundos enteros y desplaza
        el ancla por el tiempo equivalente exacto, preservando el remanente sub-milisegundo
        para el siguiente ciclo.
        """
        if self.mode is TimerMode.WAITING or self.is_paused or self._segment_start is None:
            return

        now = time.perf_counter()
        elapsed_s = max(0.0, now - self._segment_start)
        consumed_ms = int(elapsed_s * 1000)

        if consumed_ms > 0:
            self._segment_start += consumed_ms / 1000.0
            self._last_tick = self._segment_start

            if self.mode is TimerMode.PLAY:
                self.exercise_time_ms += consumed_ms
            elif self.mode is TimerMode.BREAK:
                self.break_time_ms += consumed_ms

    def pause(self) -> None:
        """Pausa / congela los contadores sin alterar el modo."""
        if self.is_paused or self.mode is TimerMode.WAITING:
            return
        self._sync()
        self.is_paused = True
        self._segment_start = None

    def resume(self) -> None:
        """Reanuda los contadores sin acumular el lapso pausado."""
        if not self.is_paused:
            return
        self._segment_start = time.perf_counter()
        self._last_tick = self._segment_start
        self.is_paused = False

    def start(self) -> None:
        """Inicia o reanuda el conteo del tiempo de ejercicio."""
        self._sync()
        self.is_paused = False
        self.mode = TimerMode.PLAY
        self._segment_start = time.perf_counter()
        self._last_tick = self._segment_start

    def toggle_break(self) -> None:
        """Alterna entre modo de ejercicio y modo de descanso."""
        self._sync()
        self.is_paused = False
        self.mode = TimerMode.PLAY if self.mode is TimerMode.BREAK else TimerMode.BREAK
        self._segment_start = time.perf_counter()
        self._last_tick = self._segment_start

    @property
    def has_accumulated_time(self) -> bool:
        """Indica si existe tiempo acumulado en ejercicio o en descanso."""
        self._sync()
        return self.exercise_time_ms > 0 or self.break_time_ms > 0

    def load_accumulated_times(self, exercise_ms: int, break_ms: int) -> None:
        """Carga tiempos acumulados previos de manera determinista."""
        self.mode = TimerMode.WAITING
        self.exercise_time_ms = max(0, exercise_ms)
        self.break_time_ms = max(0, break_ms)
        self._segment_start = None
        self._last_tick = 0.0
        self.is_paused = False

    def reset(self) -> None:
        """Reinicia todos los contadores y deja el temporizador en espera."""
        self.mode = TimerMode.WAITING
        self.exercise_time_ms = 0
        self.break_time_ms = 0
        self._segment_start = None
        self._last_tick = 0.0
        self.is_paused = False

    def stop(self) -> TimerItem | None:
        """Detiene el contador sin devolver ningún item. Se mantiene por compatibilidad."""
        if self.mode is TimerMode.WAITING:
            return None
        self._sync()
        self.mode = TimerMode.WAITING
        self._segment_start = None
        self._last_tick = 0.0
        self.is_paused = False
        return None

    def snapshot(self) -> tuple[int, int]:
        """Devuelve el estado actual del ejercicio y del descanso."""
        self._sync()
        return self.exercise_time_ms, self.break_time_ms