"""Contenedor de Inyección de Dependencias y Composition Root de la capa de Aplicación.

Centraliza la creación y resolución desacoplada de servicios de dominio, persistencia
y aplicación, permitiendo swapping transparente para testing o ejecución headless.
"""

from __future__ import annotations

from typing import Callable

from application.application_service import StudyApplicationService
from domain.timer_service import TimerService
from infrastructure.storage_service import StorageService


class AppContainer:
    """Composition Root que gestiona el ciclo de vida y la resolución de dependencias."""

    def __init__(
        self,
        storage_factory: Callable[[], StorageService] | None = None,
        timer_factory: Callable[[], TimerService] | None = None,
    ) -> None:
        self._storage_factory = storage_factory or StorageService
        self._timer_factory = timer_factory or TimerService

        self._storage_instance: StorageService | None = None
        self._timer_instance: TimerService | None = None
        self._app_service_instance: StudyApplicationService | None = None

    @property
    def storage(self) -> StorageService:
        """Retorna la instancia singleton de persistencia local."""
        if self._storage_instance is None:
            self._storage_instance = self._storage_factory()
        return self._storage_instance

    @property
    def timer(self) -> TimerService:
        """Retorna la instancia singleton de la máquina de estados del cronómetro."""
        if self._timer_instance is None:
            self._timer_instance = self._timer_factory()
        return self._timer_instance

    @property
    def app_service(self) -> StudyApplicationService:
        """Retorna la instancia del servicio orquestador principal."""
        if self._app_service_instance is None:
            self._app_service_instance = StudyApplicationService(
                storage=self.storage,
                timer=self.timer,
            )
        return self._app_service_instance

    def reset(self) -> None:
        """Reinicia las instancias activas para aislamiento en suites de prueba."""
        self._storage_instance = None
        self._timer_instance = None
        self._app_service_instance = None
