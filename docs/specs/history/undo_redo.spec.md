# Especificación Técnica: Sistema de Deshacer y Rehacer (Undo / Redo)

**Identificador:** `HIST-SPEC-001`  
**Capa de Referencia:** `application/undo/` / `domain/`  
**Estado:** Especificación oficial / Listo para implementación  
**Fecha:** 2026-09-30  

---

## 1. Propósito Funcional

Proporcionar a **Study Timetrial** un sistema completo, determinista y seguro de reversión y repetición de cambios (*Undo / Redo*) en memoria, protegiendo al usuario frente a eliminaciones involuntarias, errores de tipeo, reajustes erróneos de cronómetros o modificaciones accidentales de la estructura curricular.

El sistema sigue el patrón de diseño **Command Pattern**, implementado en **Python puro** dentro de la capa de aplicación (`application/undo/`), garantizando cero dependencias con librerías gráficas (PySide6/Qt) y desacoplamiento total de la vista, en estricto cumplimiento de `AGENTS.md`.

---

## 2. Alcance de Comandos Reversibles

Toda mutación de datos en el registro activo debe encapsularse en un comando reversible que almacene el estado delta necesario para aplicar (`execute()`), revertir (`undo()`) y reaplicar (`redo()`).

### Catálogo de Comandos Estándar

| Comando | Acción del Usuario | Operación Inversa (`undo`) |
|---|---|---|
| `AddItemCommand` | Agrega un nuevo `TimerItem` al historial. | Remueve el ítem por su `id` (UUID). |
| `DeleteItemCommand` | Elimina un `TimerItem` del historial. | Restaura el ítem idéntico en su posición original con su UUID. |
| `ReplaceItemCommand` | Edita propiedades de un `TimerItem` (comentario, completado, tiempos, inciso). | Restaura el estado previo completo del `TimerItem`. |
| `UpdateCommentCommand` | Modifica el comentario de un ítem existente. | Restaura el texto previo del comentario. |
| `PromoteIncisoCommand` | Asigna o rectifica el número de inciso de uno o varios ítems en conflicto. | Restaura los incisos previos (`None` o valor anterior). |
| `AddOrUpdateSectionCommand` | Agrega o actualiza una sección en el organizador curricular. | Restaura la sección previa o la remueve si era nueva. |
| `DeleteSectionCommand` | Elimina una sección completa del organizador. | Restaura la sección completa (ejercicios, notas y etiquetas). |
| `SetExerciseNoteCommand` | Asigna o edita los apuntes/notas Markdown de un ejercicio o inciso. | Restaura el texto previo de la nota. |
| `SetExerciseTagsCommand` | Asigna o remueve etiquetas a un ejercicio o inciso. | Restaura la lista previa de `tag_ids`. |
| `AddTagDefinitionCommand` | Crea una nueva etiqueta en el catálogo de la materia. | Remueve la etiqueta del catálogo y desvincula sus referencias. |
| `DeleteTagDefinitionCommand`| Elimina una etiqueta del catálogo. | Restaura la etiqueta y sus asociaciones a ejercicios. |
| `SetScheduleCommand` | Modifica fechas de cursada o hitos evaluativos (*Milestones*). | Restaura el cronograma `OrganizerSchedule` anterior. |
| `FinishItemCommand` | Registra el cierre de un intento desde el cronómetro (`COMPLETO`/`INCOMPLETO`). | Remueve el ítem guardado y recarga el cronómetro con los tiempos acumulados si el usuario desea continuar. |

---

## 3. Contratos de Entrada y Salida (Interfaces y DTOs)

### 3.1 Protocolo `ICommand` (`application/undo/command_protocol.py`)

```python
from __future__ import annotations
from typing import Protocol

class ICommand(Protocol):
    """Contrato base para todo comando ejecutable y reversible."""

    @property
    def description(self) -> str:
        """Descripción legible en lenguaje natural de la acción (ej: 'Eliminar intento 4')."""
        ...

    def execute(self) -> None:
        """Aplica la modificación sobre el estado de la aplicación/registro."""
        ...

    def undo(self) -> None:
        """Revierte la modificación exacta, restaurando el estado previo."""
        ...

    def redo(self) -> None:
        """Vuelve a aplicar la modificación revertida."""
        ...
```

### 3.2 Servicio Gestor de Historial `UndoManager` (`application/undo/undo_manager.py`)

```python
from __future__ import annotations
from typing import Callable, Optional

class UndoManager:
    """Gestiona las pilas de Deshacer y Rehacer con límite de profundidad."""

    def __init__(self, max_depth: int = 50) -> None:
        self.max_depth = max_depth
        self._undo_stack: list[ICommand] = []
        self._redo_stack: list[ICommand] = []
        self.on_stack_changed: list[Callable[[], None]] = []

    @property
    def can_undo(self) -> bool:
        """Indica si hay al menos una acción disponible para deshacer."""
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        """Indica si hay al menos una acción disponible para rehacer."""
        return len(self._redo_stack) > 0

    @property
    def undo_description(self) -> str:
        """Texto descriptivo de la acción al tope de la pila de deshacer."""
        return self._undo_stack[-1].description if self._undo_stack else ""

    @property
    def redo_description(self) -> str:
        """Texto descriptivo de la acción al tope de la pila de rehacer."""
        return self._redo_stack[-1].description if self._redo_stack else ""

    def push_and_execute(self, command: ICommand) -> None:
        """Ejecuta el comando, lo agrega a la pila de deshacer y limpia la pila de rehacer."""
        command.execute()
        self._undo_stack.append(command)
        if len(self._undo_stack) > self.max_depth:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._notify_changed()

    def undo(self) -> Optional[ICommand]:
        """Revierte la última acción ejecutada."""
        if not self.can_undo:
            return None
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        self._notify_changed()
        return command

    def redo(self) -> Optional[ICommand]:
        """Reaplica la última acción deshecha."""
        if not self.can_redo:
            return None
        command = self._redo_stack.pop()
        command.redo()
        self._undo_stack.append(command)
        self._notify_changed()
        return command

    def clear(self) -> None:
        """Vacía las pilas de historial (ej: al cargar un nuevo archivo o cerrar)."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify_changed()

    def _notify_changed(self) -> None:
        for callback in self.on_stack_changed:
            callback()
```

---

## 4. Comportamiento ante Errores y Casos de Borde

1. **Pila vacía:** Si el usuario invoca `undo()` o `redo()` cuando no hay acciones en la pila, la invocación retorna `None` de forma silenciosa sin arrojar excepciones ni alterar el estado.
2. **Cierre o cambio de archivo activo:** Al invocar `close_record()`, `load()` o `new_record()`, `UndoManager.clear()` se ejecuta obligatoriamente para evitar referencias cruzadas entre distintos archivos de registro.
3. **Persistencia y Estado "Dirty":** Cada ejecución de `push_and_execute()`, `undo()` y `redo()` marca el registro como modificado (`is_dirty = True`) y notifica a las vistas para su refresco reactivo.
4. **Fallo en ejecución de un comando:** Si `command.execute()` o `command.undo()` genera una excepción no controlada, el comando no entra a la pila (o se restaura la pila a su estado previo) garantizando la consistencia del historial.

---

## 5. Eventos de Usuario e Interacciones Soportadas

1. **Atajos de teclado universales:**
   * `Ctrl+Z` (Windows/Linux) o `Cmd+Z` (macOS): Dispara `application.undo()`.
   * `Ctrl+Y` o `Ctrl+Shift+Z`: Dispara `application.redo()`.
2. **Menú "Edición" y Barra de Herramientas:**
   * Botón `[ ↶ Deshacer ]`: Se deshabilita (`setEnabled(False)`) si `can_undo == False`. Al pasar el cursor, el tooltip muestra `Deshacer: <descripción> (Ctrl+Z)`.
   * Botón `[ ↷ Rehacer ]`: Se deshabilita (`setEnabled(False)`) si `can_redo == False`. Tooltip muestra `Rehacer: <descripción> (Ctrl+Y)`.
3. **Feedback visual en diálogos destructivos:**
   * La leyenda anterior `“Esta acción no se puede deshacer”` en el diálogo de eliminación se reemplaza por: `“¿Está seguro de eliminar este registro? (Podrá deshacer esta acción con Ctrl+Z)”`.
