# Arquitectura de Retrocompatibilidad, Migraciones y Respaldos

## 1. Visión General y Propósito

A medida que **Study Timetrial** evoluciona e incorpora nuevas funcionalidades (por ejemplo, enriquecimiento de notas con Markdown, nuevos metadatos en ejercicios, etiquetas personalizadas o cambios de esquema en archivos JSON de registros), es mandatorio garantizar que **ningún archivo de usuario previo quede inaccesible, se corrompa o pierda datos**.

Para ello, se establece un subsistema dedicado en la capa de infraestructura:
`infrastructure/compatibility/`

Este módulo centraliza todas las rutinas de transformación de formatos antiguos, detección de versiones legadas y generación preventiva de respaldos (*backups*).

---

## 2. Principios de Diseño

1. **Transformaciones Inyectivas (Unidireccionales)**:
   - Toda migración de datos (como la conversión de texto plano legacy a Markdown) debe ser inyectiva y determinista:
     $$f(T_{\text{plain}}) \to T_{\text{markdown}}$$
   - Aplicar la función repetidas veces sobre un texto ya migrado es idempotente:
     $$f(f(x)) = f(x)$$
   - No se destruye información original; los caracteres especiales, sangrías o viñetas de texto plano se mapean limpiamente a la semántica estándar de Markdown (`- `, `### `, párrafos separados por doble salto de línea).

2. **Migración en Lectura Transparente (*Transparent On-Read Upgrade*)**:
   - En `infrastructure/storage_service.py`, al leer un archivo `.json` de registro con `StorageService.read()`, se evalúan automáticamente los migrators registrados (`migrate_record_notes_to_markdown`, etc.).
   - Si se detecta un formato legacy, el objeto en memoria se normaliza de inmediato sin requerir intervención del usuario ni romper compatibilidad con vistas o diálogos actuales.

3. **Respaldos Preventivos Automáticos (*Safe Backups*)**:
   - `infrastructure/compatibility/backup_service.py` proporciona la utilidad `create_backup_file(path, reason)` para generar copias instantáneas con timestamp (`.bak_YYYYMMDD_HHMMSS_<reason>`) antes de cualquier reescritura estructural de archivos.
   - Permite listar y restaurar archivos dañados con `restore_backup_file()`.

---

## 3. Componentes del Módulo `infrastructure/compatibility/`

### `markdown_migrator.py`
- **`convert_plain_text_to_markdown(raw_text: str) -> str`**: Normaliza texto plano libre o notas antiguas con viñetas no estandarizadas (`* ` o listas numeradas manuales) hacia Markdown limpio y legible.
- **`migrate_record_notes_to_markdown(record: StudyRecord) -> bool`**: Recorre `record.exercise_notes` y `record.session_history[*].comment` actualizando cualquier texto plano al formato Markdown. Devuelve `True` si se aplicaron cambios.

### `backup_service.py`
- **`create_backup_file(file_path: str, reason: str = "auto") -> str | None`**: Crea una copia de seguridad en el mismo directorio del archivo o en una carpeta de respaldo dedicada, preservando fecha y hora.
- **`restore_backup_file(backup_path: str, target_path: str | None = None) -> bool`**: Restaura un archivo de datos a partir de una copia previa.
- **`list_backups_for_file(file_path: str) -> list[str]`**: Retorna la lista de respaldos existentes ordenados cronológicamente.

---

## 4. Guía para Agregar Nuevas Migraciones de Esquema

Cuando en el futuro se requiera modificar la estructura del modelo de datos de `StudyRecord` o `TimerItem`:

1. Crear un nuevo archivo en `infrastructure/compatibility/` (por ejemplo, `schema_v2_migrator.py`).
2. Definir una función de migración pura que acepte el diccionario crudo o el modelo `StudyRecord` y lo transforme al esquema más reciente.
3. Exponer la función en `infrastructure/compatibility/__init__.py`.
4. Integrar la llamada dentro de `StorageService.read()` en `infrastructure/storage_service.py`.
5. Crear pruebas unitarias en `tests/test_compatibility.py` verificando casos borde, idempotencia y preservación de datos.
