# Especificación Técnica: Catálogo de Skins, Temas Dinámicos y Creación Personalizada

**Identificador:** `THEME-SPEC-002`  
**Capa de Referencia:** `presentation/theming/` / `data/themes/` / `presentation/app_toolbar.py`  
**Estado:** Invariante / Producción  

---

## 1. Propósito Funcional

Proveer una colección rica, ergonómica y expandible de pieles visuales (skins) para **Study Timetrial**, incluyendo paletas estacionales de la naturaleza, selecciones Pantone Color of the Year, temáticas de fantasía gótica y festiva, así como una capa de partículas ambientales sutiles para **Skins Dinámicos** sin comprometer la legibilidad ni la ergonomía visual.

### Catálogo de Skins Incluidos (13 skins + 2 temas base):
1. **Skins Temáticos & Dinámicos (`[Dinámico]`):**
   * **Sakura `[Dinámico]`:** Inspirado en los cerezos japoneses en flor. Fondo papel washi mate cálido anti-reflejo (`#f8f1f3`), tarjetas elevadas (`#fcf7f8`), tipografía mora profunda (`#4a0e2e`), acentos fucsia y caída suave de pétalos rosáceos (`effect: "sakura"`). Modo claro.
   * **Black Sakura `[Dinámico]`:** Fusión nocturna entre la noche de carbón obsidiana (`#0c0a0e`), acentos florales rosa neón (`#f472b6`) y carmín rubí con lluvia de pétalos oscuros (`effect: "sakura"`). Modo oscuro.
   * **Winter `[Dinámico]`:** Inspirado en el hielo cristalino, la escarcha ártica y la noche polar. Tonos pizarra azulada (`#090e17`), acentos cian glaciar y sutil ventisca de nieve suave (`effect: "snow"`). Modo oscuro.
   * **Spring `[Dinámico]`:** Inspirado en praderas de primavera y rocío matutino. Fondo lino pradera relajante (`#eff5ec`), tarjetas marfil (`#f6faf3`), verde brote y flotación suave de hojas jóvenes (`effect: "leaves"`). Modo claro.
   * **Bamboo `[Dinámico]`:** Bosque zen de Kioto y tatamis de bambú. Fondo papel pergamino cálido (`#f3ede1`), madera clara, verde oliva y hojas alargadas de bambú planeando suavemente (`effect: "bamboo"`). Modo claro.
   * **Midnight `[Dinámico]`:** Abismo astronómico y nebulosas cósmicas. Fondo obsidiana espacial (`#05070e`), violeta nebulosa y cielo titilante de estrellas lejanas (`effect: "stars"`). Modo oscuro.
   * **Vampyr `[Dinámico]`:** Atmósfera gótica noir y misterio nocturno. Fondos abisales de terciopelo oscuro (`#080405`), tipografía ceniza plateada, acentos carmesí sangre y rescoldos ardientes ascendentes (`effect: "vampyr"`). Modo oscuro.
   * **Halloween `[Dinámico]`:** Noche otoñal de Jack-o'-lantern y misterio espectral. Fondo carbón tostado (`#0c0907`), calabaza quemada vibrante (`#ea580c`), acentos naranja dorado y chispas de hoguera (`effect: "halloween"`). Modo oscuro.

2. **Paletas Pantone & Diseñador (Estáticas):**
   * **Classic Blue (Pantone 19-4052):** Azul clásico atemporal, serenidad índigo y elegancia zafiro. Modo oscuro.
   * **Peach Fuzz (Pantone 13-1023):** Durazno aterciopelado cálido, suave confort albaricoque y arena mate anti-halación (`#f8efe6`). Modo claro.
   * **Marsala (Pantone 18-1438):** Rojo vino terroso, borgoña sofisticado y acentos oro rosa. Modo oscuro.
   * **Emerald (Pantone 17-5641):** Verde esmeralda joya botánica, selva profunda y menta luminosa. Modo oscuro.
   * **Illuminating (Pantone 17-5104 + 13-0647):** Gris arquitectónico contemporáneo combinado con amarillo solar vibrante. Modo oscuro.
   * **Nord Polar:** Paleta ártica pastel fría inspirada en el diseño nórdico. Modo oscuro.

3. **Temas Base Canónicos:**
   * **Modo claro:** Tono papel hueso descansado anti-deslumbramiento.
   * **Modo oscuro:** Deep navy slate anti-halación sin negros puros OLED.

---

## 2. Motor de Partículas Ambientales (`AmbientParticleOverlay`)

Para enriquecer la experiencia visual sin degradar el rendimiento ni la ergonomía de lectura:

```
[ MainWindow ]
   ├── QTabWidget (Central Widget)
   │     ├── HomeView / RecordsView / Stats / Planner / Ambience
   │     └── AmbientParticleOverlay (Capa Superior No Bloqueante)
   │           └── QPainter (30 FPS, alfa suave 0.20-0.45, física zen)
```

### Principios y Restricciones Técnicas:
1. **Transparencia Total de Eventos de Ratón:**
   * `self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)`: el overlay nunca intercepta clics, desplazamientos, arrastres ni selecciones de texto dirigidas a las pestañas y vistas inferiores.
2. **Cero Sobrecarga en Modo Estático:**
   * Cuando un tema estático (`effect: "none"` o ausente) está seleccionado, el temporizador interno `QTimer` se detiene y el widget se oculta con `hide()`, consumiendo 0% de CPU y GPU.
3. **Pausa Automática en Segundo Plano:**
   * La animación se suspende si la ventana se minimiza o si la suite de pruebas se ejecuta en modo `offscreen` o con `STUDY_TIMETRIAL_TEST=1`.
4. **Calibración Cromática y Opacidad:**
   * Partículas renderizadas con `alpha` entre 0.20 y 0.45 para no comprometer nunca el contraste WCAG AA de los números del cronómetro, gráficos ni textos de las tablas.

---

## 3. ¿Cómo Funciona la Creación de Skins Personalizados por el Usuario?

El sistema de temas de **Study Timetrial** está diseñado bajo el principio de **arquitectura abierta orientada a datos**:

1. **Ubicación de Archivos:**
   Cualquier usuario puede crear un nuevo tema simplemente guardando un archivo JSON en la carpeta `data/themes/<mi_tema>.json`.
2. **Descubrimiento Automático:**
   Al iniciar la aplicación o consultar el menú de temas, `theme_loader.get_available_themes()` escanea dinámicamente `data/themes/` y registra automáticamente cualquier archivo `.json` válido.
3. **Sección Automática en la Barra de Herramientas:**
   Si el tema creado no pertenece al catálogo predeterminado, la barra de herramientas `AppToolbar` crea automáticamente una sección `"Temas personalizados"` y añade la opción con un icono dinámico.
4. **Habilitación de Efectos Animados:**
   Si el usuario añade el atributo `"effect": "sakura"` (o `"snow"`, `"stars"`, `"bamboo"`, `"leaves"`, `"halloween"`, `"vampyr"`) en su JSON:
   * La interfaz le añade automáticamente el sufijo `[Dinámico]` en el menú.
   * La capa `AmbientParticleOverlay` activa la simulación correspondiente.
   * Si se omite o se coloca `"none"`, el tema opera como una piel estática sin animación.
5. **Robustez ante Errores y Herencia Automática:**
   Si el archivo del usuario solo define los colores principales (`bg_app`, `bg_card`, `text_primary`), los más de 50 tokens secundarios heredan de forma segura los valores por defecto del tema canónico (`DARK_TOKENS` o `LIGHT_TOKENS` según el valor de `is_dark`).

---

## 4. Convención de Nomenclatura UI: `[Dinámico]`

Todos los temas que incluyan un efecto de partículas activo exponen el sufijo descriptivo `[Dinámico]` en su acción de menú:
* Ejemplo: `Sakura [Dinámico]`, `Winter [Dinámico]`, `Black Sakura [Dinámico]`, `Halloween [Dinámico]`.
* Los temas que son exclusivamente cromáticos (ej. `Modo claro`, `Classic Blue`, `Peach Fuzz`, `Nord Polar`) no llevan sufijo, indicando su naturaleza estática.
