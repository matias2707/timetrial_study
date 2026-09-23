"""Pruebas unitarias para el Composition Root / AppContainer."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from application.container import AppContainer
from domain.timer_service import TimerService
from infrastructure.storage_service import StorageService


class TestAppContainer(unittest.TestCase):
    """Verifica la resolución y ciclo de vida de dependencias en AppContainer."""

    def test_container_provides_singletons(self) -> None:
        container = AppContainer()
        storage1 = container.storage
        storage2 = container.storage
        self.assertIs(storage1, storage2)
        self.assertIsInstance(storage1, StorageService)

        timer1 = container.timer
        timer2 = container.timer
        self.assertIs(timer1, timer2)
        self.assertIsInstance(timer1, TimerService)

        app1 = container.app_service
        app2 = container.app_service
        self.assertIs(app1, app2)

    def test_container_reset(self) -> None:
        container = AppContainer()
        storage1 = container.storage
        container.reset()
        storage2 = container.storage
        self.assertIsNot(storage1, storage2)

    def test_container_custom_factories(self) -> None:
        mock_storage = MagicMock(spec=StorageService)
        mock_storage.create_automatic.return_value = MagicMock()

        container = AppContainer(storage_factory=lambda: mock_storage)
        self.assertIs(container.storage, mock_storage)
        self.assertIs(container.app_service.storage, mock_storage)


if __name__ == "__main__":
    unittest.main()
