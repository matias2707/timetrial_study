# Especificación Técnica: Skin High Night [Dinámico]

**Identificador:** `THEME-SPEC-003`  
**Capa de Referencia:** `presentation/theming/` / `data/themes/high_night.json` / `presentation/app_toolbar.py`  
**Estado:** Invariante / Producción  

---

## 1. Propósito Funcional

Proveer una piel visual temática dinámica **High Night [Dinámico]** para **Study Timetrial**, ofreciendo una experiencia nocturna ultra profunda, mineral y concentrada.
Toma como referencia los fundamentos de contraste de *Midnight*, pero evoluciona hacia una atmósfera más oscura y monocromática basada en **Turmalina Negra**, acentos joya **Amatista**, textos de cristal/luz **Cuarzo y Perla**, y una animación estelar de cielo profundo con destellos ("beat") fugaces individuales periódicos (cada 2 a 5 segundos).

---

## 2. Paleta Cromática y Referencias Minerales

| Elemento | Mineral / Concepto | Hex / Rango | Razón de Diseño |
| :--- | :--- | :--- | :--- |
| **Fondo Base (`bg_app`, `bg_tab_bar`)** | Turmalina Negra | `#040405`, `#020203` | Negro mineral profundo, ultra oscuro y monocromático (sin el matiz azul marino/índigo de Midnight). |
| **Superficies & Tarjetas (`bg_surface`, `bg_card`, `bg_dialog`)** | Obsidiana / Carbón | `#070709`, `#0b0b0e`, `#111116` | Elevación sutil por luminancia anti-halación para distinguir tarjetas y modales. |
| **Tipografía Primaria & Títulos** | Cuarzo & Perla | `#fafafc`, `#f3f3f6` | Claridad cristalina y suavidad aperlada que garantizan contraste WCAG AA sobre fondos turmalina. |
| **Textos Secundarios & Muted** | Cuarzo Grisáceo | `#c5c5cf`, `#888894`, `#555562` | Jerarquía visual descansada para cronómetros secundarios y metadatos. |
| **Acento Primario (`focus`, `card_top`, `buttons`)** | Amatista Joya | `#9d4edd`, `#7b2cbf` | Reemplaza el violeta estándar por una amatista brillante y noble. |
| **Acento Claro (`hover`, selecciones, badges)** | Amatista Claro / Orquídea | `#c77dff`, `#e0aaff` | Máxima visibilidad y realce interactivo en elementos seleccionados. |
| **Acento Profundo (`hero_resume`, badges bg)** | Amatista Nocturna | `#3c096c`, `#240046` | Fondos de botones secundarios y badges de estado completado. |

---

## 3. Dinámica del Efecto Ambiental (`effect: "high_night"`)

La simulación de partículas en `AmbientParticleOverlay` para High Night implementa la siguiente física:

1. **Estrellas Base:**
   * Tamaño reducido y delicado: radio/tamaño entre `1.2` y `3.2` px (más pequeñas que en Midnight `2.5 - 6.0`).
   * Color base claro: Cuarzo y Perla con leve matiz amatista pálido (`#d8d8e8`, `#e4e4ee`, `#cfcfe0`, `#edeef5`, `#c8c4dc`).
   * Opacidad sutil en reposo (`alpha` de 0.18 a 0.42 con titilación suave).
   * Deriva muy lenta casi imperceptible (`vy: 0.01 - 0.05`, `vx: -0.03 - 0.03`).

2. **Destello Fugaz ("Beat" / Pulso Individual):**
   * **Cadencia:** Cada 2 a 5 segundos (intervalo aleatorio entre 60 y 150 frames a 30 FPS).
   * **Individualidad:** En cada intervalo se selecciona **una única estrella** del firmamento estelar para emitir su beat.
   * **Duración:** Fugaz (~0.5 a 0.7 segundos / 14 a 20 frames).
   * **Color del destello:** Tono claro blanco/grisáceo brillante (no blanco puro `#ffffff`, sino luz de cuarzo/perla `#eef0f6`, `#e8eaf2`, `#f0f2f8`, `#e5e7eb`).
   * **Comportamiento:** La estrella seleccionada incrementa transitoriamente su tamaño (escala ~1.8x) y su opacidad hasta `0.85 - 0.90` siguiendo una curva senoidal suave antes de regresar a su estado base de reposo.

---

## 4. Modularidad y Contratos

1. **Definición Declarativa JSON:**
   * Archivo: `data/themes/high_night.json`.
   * Valida estrictamente con `data/themes/theme.schema.json`.
   * Cualquier propiedad omitida se hereda automáticamente de `DARK_TOKENS`.
2. **Descubrimiento Dinámico:**
   * `theme_loader.get_available_themes()` detecta `high_night.json` automáticamente.
3. **Integración en Toolbar:**
   * Registrado en `thematic_skins` en `presentation/app_toolbar.py` con icono temático amatista (`fa5s.moon` o `fa5s.star-and-crescent`) y label `"High Night [Dinámico]"`.
4. **Constante y Exports:**
   * `THEME_HIGH_NIGHT = "high_night"` en `presentation/theme_tokens.py` y `presentation/theme.py`.
