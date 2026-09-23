"""Pruebas unitarias para la jerarquía de excepciones de dominio."""

from __future__ import annotations

import unittest

from domain.exceptions import (
    BoundaryExceededError,
    InvalidSectionError,
    MilestoneDateError,
    RecordCorruptedError,
    RecordError,
    RecordNotFoundError,
    RecordValidationError,
    StudyTimetrialError,
    TimerConflictError,
    TimerDomainError,
)


class TestDomainExceptions(unittest.TestCase):
    """Verifica que las excepciones de dominio cumplan con los contratos e invariantes."""

    def test_base_error_formatting(self) -> None:
        err = StudyTimetrialError("Fallo general", code="ERR_BASE")
        self.assertEqual(str(err), "[ERR_BASE] Fallo general")
        self.assertEqual(err.code, "ERR_BASE")
        self.assertEqual(err.message, "Fallo general")

    def test_record_exceptions_inheritance(self) -> None:
        corrupted = RecordCorruptedError("JSON inválido")
        self.assertIsInstance(corrupted, RecordError)
        self.assertIsInstance(corrupted, StudyTimetrialError)
        self.assertEqual(corrupted.code, "RecordCorruptedError")

        not_found = RecordNotFoundError("Archivo no existe")
        self.assertIsInstance(not_found, RecordError)

        validation = RecordValidationError("Tiempo negativo")
        self.assertIsInstance(validation, RecordError)

    def test_timer_exceptions_inheritance(self) -> None:
        conflict = TimerConflictError("Transición inválida")
        self.assertIsInstance(conflict, TimerDomainError)
        self.assertIsInstance(conflict, StudyTimetrialError)

        boundary = BoundaryExceededError("Tiempo fuera de rango")
        self.assertIsInstance(boundary, TimerDomainError)

    def test_planner_exceptions_inheritance(self) -> None:
        invalid_sec = InvalidSectionError("Sección desconocida")
        self.assertIsInstance(invalid_sec, StudyTimetrialError)

        milestone_err = MilestoneDateError("Fecha fuera de rango")
        self.assertIsInstance(milestone_err, StudyTimetrialError)


if __name__ == "__main__":
    unittest.main()
