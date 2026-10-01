# Especificación Técnica: Control Robusto de Archivos, Guardado, Autoguardado y Recuperación de Fallos

**Identificador:** `DATA-SPEC-002`  
**Capa de Referencia:** `infrastructure/` / `application/` / `presentation/`  
**Estado:** Implementación oficial completada / Verificada con tests  
**Fecha:** 2026-09-30  

---

## 1. Propósito Funcional

Garantizar la **integridad absoluta, persistencia confiable y protección contra pérdida de datos** en **Study Timetrial**. Esta especificación establece los contratos y mecanismos para:
1. **Guardado Explícito y Seguimiento de Estado Modificado (*Dirty State Tracking*):** Control transparente entre el estado en memoria y el archivo en disco, con acción directa de guardado (`Ctrl+S`).
2. **Motor de Autoguardado (*Autosave Engine*):** Persistencia periódica y por eventos sin congelar la fluidez de la interfaz de usuario.
3. **Escritura Atómica en Disco (*Atomic File Writing*):** Reemplazo atómico vía archivo temporal y `os.replace()` para inmunizar los archivos JSON ante cortes de energía, bloqueos del SO o caídas repentinas.
4. **Diario de Recuperación de Sesión Activa (*Crash Recovery Journal*):** Checkpoints automáticos mientras el cronómetro está corriendo, evitando la pérdida de minutos u horas de estudio si la aplicación se interrumpe antes de presionar `COMPLETADO`.
5. **Detección Preventiva de Modificaciones Externas (*Cloud Sync Guard*):** Detección de colisiones al sincronizar la carpeta de datos mediante Google Drive, Dropbox o OneDrive, impidiendo la sobrescritura ciega de cambios externos.
6. **Bloqueo de Concurrencia (*Single-Writer File Lock*):** Protección para evitar que dos instancias simultáneas de la aplicación abran y corrompan el mismo archivo JSON.

---

## 2. Modelos, Estados y DTOs

### 2.1 Modos de Guardado (`SavePolicy`)

```python
from enum import Enum

class SavePolicy(str, Enum):
    """Política de guardado configurada por el usuario."""
    AUTO_IMMEDIATE = "auto_immediate"  # Guarda en disco tras cada mutación (comportamiento ágil)
    AUTO_PERIODIC = "auto_periodic"    # Guarda periódicamente cada N segundos solo si is_dirty=True
    MANUAL = "manual"                  # Guarda exclusivamente a petición explícita (Ctrl+S o salir)
```

### 2.2 Estado Modificado (*Dirty State*)
* `is_dirty: bool`: Propiedad reactiva de `StudyApplicationService`.
  * Se establece en `True` cuando cualquier comando modifica el `Record` en memoria.
  * Se restablece a `False` inmediatamente después de una escritura exitosa en disco (`save()`).
  * Emite señal/callback hacia la vista para actualizar el título de la ventana y el estado de la acción de guardar.

### 2.3 Estructura del Checkpoint de Sesión Activa (`.session_draft.json`)

Ubicado en `data/.drafts/<stem_archivo>_draft.json`:

```json
{
  "version": 1,
  "record_path": "d:/Proyectos/Algebra.json",
  "updated_at": "2026-09-30T18:20:00",
  "session_started_at": "2026-09-30T17:35:00",
  "timer_mode": "PLAY",
  "is_paused": false,
  "exercise_time_ms": 2700000,
  "break_time_ms": 120000,
  "location": {
    "section_type": "Guía",
    "section_number": 2,
    "exercise": 5,
    "inciso": 1
  },
  "comment": "Demostración de matrices ortogonales",
  "editing_item_id": null
}
```

### 2.4 Estructura del Archivo de Bloqueo (`.lock`)

Ubicado adyacente al archivo original como `.<stem_archivo>.lock`:

```json
{
  "pid": 12450,
  "hostname": "DESKTOP-MATIAS",
  "acquired_at": "2026-09-30T18:00:00",
  "record_path": "d:/Proyectos/Algebra.json"
}
```

---

## 3. Protocolos y Contratos de Servicios

### 3.1 Escritura Atómica en `StorageService` (`infrastructure/storage_service.py`)

La función de escritura debe garantizar la atomicidad física mediante volcado temporal y reemplazo:

```python
def save_atomic(target_path: Path, payload: str, encoding: str = "utf-8") -> None:
    """Escribe el contenido en un archivo temporal adyacente y aplica reemplazo atómico."""
    target_path = Path(target_path).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.parent / f".{target_path.name}.{os.getpid()}.tmp"

    try:
        temp_path.write_text(payload, encoding=encoding)
        # os.replace es una operación atómica a nivel de sistema de archivos
        os.replace(temp_path, target_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        raise
```

### 3.2 Detección de Cambios Externos (`CloudSyncGuard`)

`StorageService` mantiene la marca temporal de modificación (`mtime`) y/o hash SHA-256 del archivo cargado:

```python
class FileMetadataWatcher:
    """Supervisa la integridad del archivo en disco respecto a la versión en memoria."""
    
    def __init__(self, path: Path) -> None:
        self.path = path
        self.last_known_mtime: float = path.stat().st_mtime if path.exists() else 0.0
        self.last_known_hash: str = self._compute_hash() if path.exists() else ""

    def has_external_modification(self) -> bool:
        """Determina si un proceso externo (ej. Dropbox/OneDrive) modificó el archivo en disco."""
        if not self.path.exists():
            return False
        current_mtime = self.path.stat().st_mtime
        if current_mtime != self.last_known_mtime:
            current_hash = self._compute_hash()
            return current_hash != self.last_known_hash
        return False

    def update_snapshot(self) -> None:
        """Actualiza los metadatos de control tras un guardado local."""
        if self.path.exists():
            self.last_known_mtime = self.path.stat().st_mtime
            self.last_known_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        import hashlib
        return hashlib.sha256(self.path.read_bytes()).hexdigest()
```

### 3.3 Gestor de Borradores de Sesión Activa (`SessionDraftManager`)

* **Escritura periódica:** Mientras `TimerService.mode != WAITING`, se escribe el estado transitorio del reloj cada 15 segundos en `data/.drafts/`.
* **Limpieza determinista:** Al presionar `finish_item()` (guardado) o `stop_session()` (descarte) o cerrar el registro formalmente, el borrador se elimina de inmediato.
* **Detección al inicio:** Al abrir un archivo de registro, `SessionDraftManager.check_for_draft(path)` busca si existe un borrador huérfano fechado en el disco. Si existe, notifica al servicio para consultar al usuario si desea recuperar o descartar el intento pendiente.

---

## 4. Comportamiento ante Errores y Casos de Borde

1. **Conflicto de Nube detectado antes de guardar:**
   * Si `has_external_modification() == True` al intentar guardar:
     * La aplicación suspende el guardado automático.
     * Despliega un diálogo modal de resolución de conflicto:
       * **[Recargar de disco]:** Descarta cambios locales y carga la versión nueva sincronizada.
       * **[Sobrescribir disco]:** Guarda la versión local como versión definitiva.
       * **[Guardar como copia]:** Guarda la versión local en un nuevo archivo (ej. `Algebra_ConflictoLocal.json`).
2. **Archivo bloqueado por otra instancia:**
   * Si `.lock` existe y el proceso referenciado sigue activo en el sistema operativo:
     * La aplicación informa: *“El archivo se encuentra abierto en otra instancia de Study Timetrial. Se abrirá en modo de solo lectura o podrá cancelar la operación”*.
3. **Cierre de aplicación con cambios sin guardar:**
   * Si `is_dirty == True` y se cierra la ventana o el registro:
     * Diálogo con opciones: `[Guardar cambios]` (ejecuta guardado atómico y cierra), `[Descartar]` (cierra sin guardar), `[Cancelar]` (aborta el cierre).
4. **Espacio en disco insuficiente o permisos denegados:**
   * La escritura atómica falla en el temporal `.tmp`, dejando intacto el archivo JSON original sin truncarlo a 0 bytes.
   * La interfaz muestra un aviso de error sin cerrar el programa, preservando los datos en memoria para reintentar.

---

## 5. Eventos de Usuario e Interacciones Soportadas

1. **Acción "Guardar" (`Ctrl+S`):**
   * Incorporada en Menú Archivo y Barra de Herramientas.
   * Icono interactivo (`fa5s.save`). Se resalta visualmente cuando `is_dirty == True`.
2. **Indicador de Título Reactivo:**
   * Sin cambios pendientes: `Study Timetrial — Álgebra`
   * Con cambios pendientes: `Study Timetrial — Álgebra *`
3. **Selector de Política de Guardado en Configuración / Preferencias:**
   * Radio options:
     * `(•) Guardado automático continuo (Recomendado)`
     * `( ) Guardado automático periódico (cada 60 segundos)`
     * `( ) Guardado manual exclusivamente`
4. **Diálogo de Recuperación de Sesión Inesperada:**
   * Si tras un apagón o reinicio se detecta borrador:
     * *“Se encontró una sesión de cronómetro no finalizada del 30/09 a las 18:15 (45 min 12 seg en Guía 2 Ejercicio 5). ¿Desea reanudar esta sesión?”* -> `[Reanudar en cronómetro]` / `[Descartar borrador]`.
