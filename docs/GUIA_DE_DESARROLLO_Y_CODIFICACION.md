# Guía de Desarrollo, Arquitectura y Estándares de Codificación

**Study Timetrial — Manual Técnico de Ingeniería**  
**Versión:** 2.0  

---

## 1. Topología del Proyecto y Responsabilidad de Capas

```text
study_timetrial_demo/
├── domain/            <- Entidades puras, Value Objects, contratos invariantes y cronómetro
├── application/       <- Casos de uso, servicios de orquestación, cálculo de métricas y consultas
├── infrastructure/    <- Persistencia en disco (JSON), adaptadores de audio, sistema operativo
├── presentation/      <- Presenters (Python puro) + Vistas Pasivas (PySide6) + Estilos
├── data/              <- Almacenamiento local (records, ambient tracks, themes)
├── docs/              <- Documentación, especificaciones ramificadas (docs/specs/) y normativas
└── tests/             <- Suite de pruebas automatizadas (unitarias, integración y UI headless)
```

---

## 2. Reglas de Inversión de Dependencias y Acoplamiento

1. **La regla de dependencia es unidireccional hacia adentro:**
   $$\text{Presentation} \longrightarrow \text{Application} \longrightarrow \text{Domain}$$
   $$\text{Infrastructure} \longrightarrow \text{Domain}$$
2. **Prohibición de Frameworks Gráficos en Capas Internas:**
   * Ningún archivo en `domain/`, `application/`, `infrastructure/` o cualquier `*presenter.py` puede importar `PySide6`, `PyQt`, `QtWidgets` o `QtCore`.
   * El código interno debe ejecutarse íntegramente en un entorno headless de consola.

---

## 3. Estándar de Codificación (Clean Code)

### A. Tipado Estricto con `typing`
* Todo archivo nuevo debe comenzar con:
  ```python
  from __future__ import annotations
  ```
* Todas las funciones, métodos y constructores deben poseer firmas de tipo completas (argumentos y tipo de retorno `-> None`, `-> int`, etc.).
* Usar `Protocol` de `typing` para definir interfaces entre Vistas y Presenters.

### B. Inmutabilidad y Modelado de Datos
* Las entidades de dominio o DTOs deben modelarse prioritariamente con `dataclasses`:
  ```python
  @dataclass(frozen=True)
  class UserSettings:
      theme_name: str
      sound_muted: bool
  ```

### C. Nombres y Convenciones
* **Clases:** `PascalCase` (`HomePresenter`, `TimerService`, `TimerItem`).
* **Funciones y Métodos:** `snake_case` (`start_session()`, `toggle_break()`).
* **Constantes:** `UPPER_SNAKE_CASE` (`MAX_ACTIVE_TRACKS`, `STATUS_COMPLETED`).
* **Módulos privados o de soporte:** Prefijo `_` (`_sync()`, `_on_player_error()`).

### D. Manejo Defensivo de Excepciones y Persistencia
* Las escrituras a disco deben ser atómicas.
* Nunca enmascarar errores críticos con `except: pass` sin dejar un valor de degradación seguro documentado o fallback determinista.

---

## 4. Estándar de Pruebas Unitarias

* Todo nuevo servicio o Presenter debe incluir su suite en `tests/test_<nombre>.py`.
* Los tests de Presenter deben usar un `MockView` simple en memoria para asegurar ejecución instantánea sin abrir ventanas.
* Para verificar la suite completa:
  ```powershell
  python -m unittest discover -s tests -v
  ```
* Para verificar compilación sintáctica:
  ```powershell
  python -m py_compile main.py
  ```
