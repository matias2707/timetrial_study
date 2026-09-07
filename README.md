# Study Timetrial

Aplicación de escritorio local para cronometrar ejercicios, registrar intentos
y guardarlos en archivos JSON.

## Inicio rápido

En PowerShell, desde la raíz del proyecto:

```powershell
python -m pip install -r requirements.txt
python main.py
```

La primera ejecución crea un registro local. La aplicación no requiere servidor
ni base de datos.

## Estructura

- `main.py`: punto de entrada y composición mínima de Qt.
- `presentation/`: ventana, diálogos y adaptadores visuales.
- `application/`: casos de uso, sesión, navegación y coordinación.
- `domain/`: modelos persistidos y estados del cronómetro.
- `infrastructure/`: JSON local y archivos recientes.
- `tests/`: pruebas unitarias sin levantar Qt.
- `docs/`: documentación normativa y operativa.

## Documentación

Consulta el [índice documental](docs/README.md):

- [Arquitectura](docs/ARQUITECTURA_2026-09-07.md)
- [Especificación funcional](docs/Study%20Timetrial%20%E2%80%94%20Especificaci%C3%B3n%20funcional%20y%20estructura%20de%20datos.md)
- [Contrato JSON](docs/CONTRATO_JSON.md)
- [Operación y validación](docs/OPERACION_Y_VALIDACION.md)

## Pruebas

```powershell
python -m unittest discover -s tests -v
```

La inyección de `StorageService` y `TimerService` permite probar la capa de
aplicación sin iniciar una ventana Qt.
