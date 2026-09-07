# Operación y validación

**Fecha de revisión:** 2026-09-07

## Requisitos

- Windows, macOS o Linux con Python compatible con PySide6.
- Dependencia `PySide6>=6.8`.

## Instalación y ejecución

Desde la raíz del proyecto:

```powershell
python -m pip install -r requirements.txt
python main.py
```

La aplicación crea o asocia un registro local `StudyTimetrial_YYYYMMDD.json`
al iniciar. Desde **Registros** se puede crear otro archivo, abrir uno
existente, guardar como, renombrarlo o cerrarlo.

## Validación automática

La suite no levanta Qt y cubre los casos de uso, persistencia auxiliar y
formateo de tiempos:

```powershell
python -m unittest discover -s tests -v
```

La comprobación de sintaxis de todos los módulos principales es:

```powershell
python -m py_compile main.py presentation/main_window.py presentation/presentation_dialogs.py presentation/presentation_formatters.py application/application_service.py domain/models.py domain/timer_service.py infrastructure/storage_service.py
```

## Validación manual de interfaz

Después de cambios en PySide6, iniciar `main.py` y comprobar:

1. Crear o abrir un registro desde el diálogo inicial.
2. Iniciar una sesión, activar un receso, reanudar y finalizar como completo.
3. Finalizar otra sesión como incompleta y confirmar ambos tiempos en Registros.
4. Verificar que la ubicación se bloquea durante la sesión y se desbloquea al terminar.
5. Probar navegación anterior/siguiente y confirmar que los intentos se guardan.
6. Editar, comentar, resetear, importar y eliminar un item.
7. Cerrar la ventana durante una sesión y verificar el diálogo de confirmación.

## Diagnóstico y límites

- Un error de esquema o JSON inválido se debe tratar como problema del archivo,
  no como una migración manual improvisada.
- La ruta activa y las rutas recientes se gestionan desde infraestructura.
- La lógica de aplicación debe seguir siendo comprobable sin `QApplication`.
- No se deben modificar JSON de usuario para hacer pasar una prueba.
