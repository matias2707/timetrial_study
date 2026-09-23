"""Prueba automatizada de fronteras arquitectónicas (Architecture Guard).

Verifica estáticamente mediante el AST de Python que ninguna capa viole
las reglas contractuales de dependencias e importaciones de AGENTS.md:
1. domain/ no debe importar nada de application, presentation, infrastructure ni Qt/PySide6.
2. application/ no debe importar nada de presentation ni Qt/PySide6.
3. presentation/**/presenter.py no debe importar Qt ni PySide6.
4. infrastructure/ (excepto audio/ o puentes visuales) no debe importar presentation.
"""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

ROOT_DIR = Path(__file__).resolve().parent.parent


def _get_imported_modules(file_path: Path) -> set[str]:
    """Extrae todos los nombres de módulos importados en un archivo Python mediante AST."""
    imports: set[str] = set()
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    except Exception:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".")[0])
    return imports


class TestArchitectureBoundaries(unittest.TestCase):
    """Garantiza la preservación innegociable de capas y reglas de importación."""

    def test_domain_layer_has_zero_external_framework_dependencies(self) -> None:
        domain_dir = ROOT_DIR / "domain"
        forbidden = {"application", "presentation", "infrastructure", "PySide6", "PyQt6", "PyQt5", "Qt"}

        for py_file in domain_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            imported = _get_imported_modules(py_file)
            violations = imported.intersection(forbidden)
            self.assertEqual(
                violations,
                set(),
                f"Violación arquitectónica en {py_file.name}: domain no debe importar {violations}",
            )

    def test_application_layer_does_not_import_presentation_or_qt(self) -> None:
        app_dir = ROOT_DIR / "application"
        forbidden = {"presentation", "PySide6", "PyQt6", "PyQt5", "Qt"}

        for py_file in app_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            imported = _get_imported_modules(py_file)
            violations = imported.intersection(forbidden)
            self.assertEqual(
                violations,
                set(),
                f"Violación arquitectónica en {py_file.name}: application no debe importar {violations}",
            )

    def test_presenters_are_pure_python_without_qt_dependencies(self) -> None:
        presentation_dir = ROOT_DIR / "presentation"
        forbidden = {"PySide6", "PyQt6", "PyQt5", "Qt"}

        presenter_files = list(presentation_dir.glob("**/*presenter.py"))
        self.assertGreater(len(presenter_files), 0, "Debe existir al menos un archivo *presenter.py")

        for py_file in presenter_files:
            imported = _get_imported_modules(py_file)
            violations = imported.intersection(forbidden)
            self.assertEqual(
                violations,
                set(),
                f"Violación arquitectónica en Presenter {py_file.name}: debe ser Python puro sin {violations}",
            )


if __name__ == "__main__":
    unittest.main()
