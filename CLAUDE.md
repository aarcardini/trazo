# CLAUDE.md — Trazo

Instrucciones para Claude Code. Léelas al inicio de cada sesión. El plan de trabajo está en `ROADMAP.md`.

## Qué es
**Trazo** (antes «Finch Local»): herramienta local de estudio de **planta tipo** inspirada en el flujo público de Finch3D:
masa → planta → pasillo y núcleos → mix de unidades → planos de unidad.
Usuario: arquitecto (no programador), trabaja con **Rhino 8 en Mac y en Windows**. Interfaz y mensajes **en español**.
Es una implementación propia: no copiar código, textos, marcas ni datos de Finch.
Tiene dos modos en el mismo repositorio: **Edificio** (`/`, planta tipo) y **Masterplan** (`/masterplan`, calles, veredas, manzanas, lotes y construcciones; Fase 8 del roadmap). Un lote del Masterplan se abre en el modo Edificio con su huella, altura y medianeras.

## Arquitectura
| Ruta | Qué hace |
|---|---|
| `engine/geometry.py` | Geometría 2D pura: área y centroide (desde el primer vértice: precisos con coordenadas UTM), recortes (Sutherland-Hodgman; `clip_rect_parts`/`clip_halfplane_parts`/`largest_part` separan las partes cuando el corte divide una figura cóncava), marcos locales, offsets; `subtract` (resta de polígonos que devuelve varias partes) y `union_parts`; `line_intervals_multi` (polígonos con huecos). |
| `engine/layout.py` | Fachada del motor: `generate(data)` es la entrada única (orquesta las etapas). Contiene `VERSION`, `DEFAULT_PARAMS` y `merge_params`, y reexporta las funciones de los módulos de abajo (`layout.split_blocks`, etc.). |
| `engine/massing.py` | Masa: retiros y medianeras (`apply_setbacks`, `make_blind`), `build_massing` (planta y niveles), descomposición en alas (`decompose_wings`, también con patios interiores; `descomponer_alas` para plantas no ortogonales, R3.4) y distancias a bordes. |
| `engine/circulation.py` | Pasillo y núcleos: piezas automáticas (`build_pieces`, alas puente en anillos) y de polilíneas (`build_user_pieces`, cruces en X con `_cruces`), uniones (`_link`, `_connect`), núcleos (`_add_core`), evacuación (`egress_at`) y el caso entre medianeras (`is_between`). Entrada: `generate_circulation`. |
| `engine/evacuacion.py` | Evacuación (R3.6): la red de pasillos como grafo; desde la puerta de cada vivienda, `recorrido` hasta el núcleo más cercano y `saco` (tramo con una sola dirección de salida, hasta un núcleo o un punto con dos direcciones; un anillo da dos aunque lleguen al mismo núcleo) y `tramos` de pasillo fuera de norma. |
| `engine/units.py` | Viviendas: tramos laterales libres (`_segments`), reparto del mix (`generate_unit_mix`), `sin_solapes` (pasillos dibujados: recorta o quita la vivienda que pise a otra, a un pasillo o a un núcleo), `metrics_mix` y `unit_rooms` (planos de cada unidad con `plans.layout_unit`). |
| `engine/patios.py` | Patios y bloques: `auto_patios`, `split_blocks` (bloques y anillos), `make_patio_dark`, `_block_of`. |
| `engine/plans.py` | Planos de unidad: zonas día/noche, pasillo interno, puertas, grafo de conexiones y comprobaciones. |
| `engine/standards.py` | Medidas mínimas (normativa) y típicas; cálculo de escalera, ascensores, núcleo e inodoros. Ver `STANDARDS.md`. |
| `engine/programs.py` | Núcleo por partes (escalera, ascensores, palier, ductos), oficinas/comercio (hall + baños + planta libre) y estacionamiento. |
| `engine/dxf.py` | Exportador DXF R12 (polilíneas por capa). |
| `engine/masterplan.py` | Modo Masterplan: `damero()` (trazado automático) y `generate(data)` (calles → manzanas → ochavas → lotes → construcción → métricas). |
| `server.py` | Servidor HTTP stdlib en `127.0.0.1:8765`. Recarga `engine/` si cambian los archivos. |
| `web/index.html` | Interfaz completa (HTML+CSS+JS en un archivo, sin dependencias). Dos vistas: «Planta 2D» (SVG, zoom/desplazamiento, edición de líneas y núcleos, ficha de unidad) y «Axonometría 3D» (SVG proyectado, algoritmo del pintor, selección de niveles por clic o por programa). Proyectos (R4.1): «Guardar proyecto» escribe un `.trazo.json` = cuerpo de `/api/generate` (`footprint`, `height`, `stage`, `params()`) más `trazo: "proyecto"`, `formato`, `version_motor`, `guardado` y `name`, con `params.standards` solo con las medidas cambiadas; «Abrir proyecto…» (`abrirProyecto`) devuelve cada parámetro simple a su control con el mismo id y los demás (líneas, núcleos, mix, medidas, medianeras, patios, programa por planta) uno por uno, y también abre masas sueltas (formato de `samples/`). Un parámetro nuevo en `params()` necesita un control con su mismo id o su línea en `abrirProyecto` (lo comprueba `test_proyectos`). Deshacer (R4.2): todo lo que cambie polilíneas, núcleos, medianeras o patios llama antes a `recordar('qué se hizo')` (foto del estado); `deshacer`/`rehacer` vuelven a esa foto y recalculan; otra masa, un proyecto o «Nuevo» llaman a `olvidarHistoria()`. `test_deshacer` busca cada cambio sin `recordar`. Arrastrar núcleos (R4.3): `dragCore` en la planta; al soltar, `coresManual[i]` = centro del núcleo + desplazamiento (en automático, `ensureManual` y el mismo orden de `result.cores`); el motor lo ajusta al pasillo. Variantes (R4.5): `variantes` = [{nombre, guardada, proyecto (`proyecto()`), metricas (`resumen(result)`)}]; van en el archivo del proyecto (`archivoProyecto`), `abrirVariante` usa `abrirProyecto(..., {variante:true})` (no cambia la lista) y «Nuevo» las borra; `test_variantes` comprueba que las métricas que lee `resumen` existen en el resultado del motor. Viviendas editadas (R4.4): `ediciones` (= `params.unit_edits`); con una vivienda elegida, sus tabiques (`data-tab`) se arrastran (`dragTab`) y su ficha tiene «Dividir en dos» y «Unir con…»; todo pasa por `editar(op, txt)` (registra para deshacer y recalcula). |
| `web/masterplan.html` | Interfaz del modo Masterplan (un archivo): predio, calles, usos de manzana, mix de lotes, construcción, planta 2D y axonometría, «Abrir en modo Edificio». |
| `samples/masterplan/*.json` | Predios de ejemplo del modo Masterplan (`damero: true` traza el damero al cargar). |
| `rhino/trazo_rhino.py` | Puente Rhino 8 (CPython 3, `rhinoscriptsyntax`/RhinoCommon): Enviar masa / Recibir resultado / Diagnostico. Recibir dibuja solo en las capas de resultado (`Trazo::Footprint` y `Trazo::L00…` con subcapas) y, si ya hay un resultado, pregunta si reemplazarlo; las capas de entrada (`Trazo::Centerline`, `Cores`, `Medianeras`, `Patios`) no se tocan. |
| `samples/*.json` | Masas de ejemplo que aparecen en el desplegable de la web. |
| `tests/test_engine.py` | Pruebas del motor (`python tests/test_engine.py`). |
| `tests/test_rhino.py` | Pruebas del script de Rhino sin Rhino: lo carga con Rhino simulado (`unittest.mock`) y habla con `server.py` real. Mensajes, diagnóstico, menú y Recibir sin duplicar (qué capas se reemplazan, qué se borra, qué se pregunta); la geometría solo se prueba en Rhino. |
| `tests/regresion.py`, `tests/golden/` | Pruebas de regresión: métricas de referencia de cada ejemplo de `samples/` (unidades, eficiencia, sin usar, núcleos, lotes…) con un margen por métrica. Corren dentro de `test_engine.py`. |

API: `GET /api/version`, `GET|POST /api/mass` (Rhino→web y Masterplan→Edificio), `POST /api/generate` (web→motor), `GET /api/result` (→Rhino), `GET /api/dxf`, `GET /api/samples`, `POST /api/reset` (botón «Nuevo»: el servidor olvida la masa y el resultado).
Masterplan: `GET /masterplan`, `GET /api/mp_samples`, `POST /api/masterplan` (→ `masterplan.generate`), `POST /api/damero` ({predio, masterplan} → {streets}).

### Modelo del motor (layout.py y sus módulos: massing, circulation, units, patios)
- Unidades: **metros**. Coordenadas de mundo en planta (x, y). La altura solo afecta a plantas (`stories`).
- La planta (`plate`) es la huella con el muro exterior descontado (`inset`).
- **Piezas** (`pieces`): cada tramo de pasillo es una pieza con marco local (`origin`, `angle`): x a lo largo del pasillo, y transversal; el pasillo ocupa |y| ≤ ancho/2.
  - Modo automático: `decompose_wings` divide plantas ortogonales en rectángulos (alas). Si no es ortogonal (R3.4), `descomponer_alas` separa los brazos con otra dirección por cuerdas desde un vértice entrante (`_partir`: cada parte, más borde en una sola dirección y dos lados largos paralelos) y divide cada parte en alas en su propio marco (`_alas_en_marco`: se rectifica por fuera, como una ochava, y se recorta con la planta real). Cada pieza guarda `eje` (dónde su eje corta el borde del ala: inglete o cuerda); en un inglete no hay conector (los pasillos ya se encuentran) y un conector oblicuo no pasa del otro borde del pasillo; los núcleos se corren hasta entrar enteros (`_x_que_entra`). Las plantas convexas y las que no se dejan dividir siguen con un solo pasillo (`pick_frame`).
  - Modo usuario: `build_user_pieces` crea una pieza por tramo de cada polilínea (`params.centerlines`). Cruces en X → `_cruces` (R3.3): la línea más larga sigue de largo y la otra se corta en el cruce, y cada mitad es un empalme en T (si una línea pasa del otro lado menos de `corridor_width + 2.5`, ese sobrante se quita). Giros ~90° → cortes ortogonales (la franja interior del tramo anterior no pisa la del siguiente donde la planta se ensancha); otros ángulos → bisectriz; empalmes en T → `_stem_vs_trunk` (unión en los dos sentidos; un ramal oblicuo bloquea solo la franja que atraviesa); paralelas, también las ramas de una U → `_split_parallel`. Al final, `units.sin_solapes` recorta o quita la vivienda que todavía pise a otra, a un pasillo o a un núcleo.
  - `side_region[±1]`: región de unidades de cada lado del pasillo (en el marco local).
  - `extra_blocks[±1]`: intervalos en x bloqueados (conectores, núcleos de otras piezas).
  - `junctions`: uniones entre piezas, usadas por `egress_at` (distancia de evacuación por el pasillo).
- Núcleos: automáticos (`cores_mode="auto"`, en extremos libres + los que pida la evacuación) o manuales (`cores_mode="manual"`, `params.cores` = puntos de mundo que se ajustan al pasillo más cercano). Un núcleo manual puede ser `{"p": [x, y], "frente", "fondo", "giro": 0|90}` (R3.5; `nucleo_punto`, `medidas_nucleo`): frente a lo largo del pasillo, fondo sin el pasillo (si es propio no se estira hasta la fachada) y giro 90 = escalera a lo largo del pasillo (`ST.core_size(..., giro=90)`, `PR.core_parts(..., giro)`). Rhino manda puntos; la web edita cada núcleo con un clic (`corePanel`).
- Unidades: `_segments` da los tramos laterales libres; `generate_unit_mix` los corta en franjas con el mix objetivo (estado compartido entre piezas para respetar porcentajes).
- Planos: `unit_rooms` (units.py) pasa cada unidad a su marco propio (x = fachada, v = profundidad desde el pasillo común) y llama a `plans.layout_unit`.
  `plans.py` decide zona de día/noche (el rectángulo principal va bajo la parte del fondo con luz y lo demás es anexo/depósito: `_main_con_luz`), crea rectángulos de estancias, deduce conexiones abiertas (estancias de día que comparten borde) y con puerta (pasillo→dormitorios/baños), coloca puertas y comprueba: alcance desde la entrada (BFS), fachada de estancias habitables (`is_facade` contra el borde de la planta), anchos mínimos (`MIN_W`) y frente mínimo (`facade_min`). Unidades no rectangulares: rectángulo principal + anexos (estudio/depósito).
- Medianeras: `params.medianeras` = [{a, b, retiro}]. `apply_setbacks` recorta la huella; `make_blind` crea `params["_blind"](punto)` para saber si un punto está sobre una medianera ciega (retiro < `predio.retiro_ventanas`). Lo usan la comprobación de fachada, `_single_frame` (pasillo contra la medianera) y `is_between` (predio entre medianeras: franja central con núcleo `side=0` y hall).
- **Patios y bloques** (v2.4): `params.patios_mode` = `auto` (por defecto: `auto_patios` abre patios del ancho `predio.patio_min` en predios entre medianeras demasiado profundos) o `manual` (`params.patios` = polígonos de mundo). `split_blocks` resta los patios de la huella (`G.subtract`) y da los **bloques**; `generate` procesa cada bloque con su copia de parámetros (`pb`: pasillo, núcleos —al menos uno por bloque—, unidades, programas) y comparte el estado del mix. `make_patio_dark` crea `params["_patio_dark"](punto)` para las caras que dan a un patio más angosto que el mínimo. El resultado agrega `blocks` [{footprint, plate}], `patios`, `patios_auto` y `metrics.blocks`/`patio_area`; `plate` es la del primer bloque. Sin patios, el resultado es idéntico al de antes. Pendiente: alturas por bloque (varias masas a la vez).
- **Patios rodeados de edificio** (v2.6): un patio dentro de la masa deja un hueco; `split_blocks` devuelve bloques y plantas como `(exterior, [huecos])` (`_anillo`: el muro también hacia el patio) y descarta, con aviso, los anillos que no se pueden dividir en alas ortogonales. Con `pb["_huecos"]`: `decompose_wings(plate, holes=, blind=)` corta las franjas también en los huecos (y puntúa menos las alas a lo largo de una medianera); `_bridge_axis` marca las alas que unen otras dos junto al patio y su pasillo va de lado a lado, así el pasillo da la vuelta; `_connect` agrega las uniones en los dos sentidos; `_ring_single` elige pasillo de borde en alas playas; `_ring_corners` no pone viviendas donde el fondo de la franja no da a una fachada ni al patio; las puntas libres a ≤ `egress_single` de una unión no llevan núcleo propio. `is_between` es falso con huecos; la fachada (`unit_rooms`) cuenta las caras al patio; en estacionamiento, los patios son obstáculos. `res.blocks[i]` agrega `holes` y `plate_holes`; la web dibuja la planta con huecos (`fill-rule: evenodd`) y en la axonometría las caras interiores del patio. Polilíneas en un bloque con patio interior: se ignoran con un aviso.
- Evacuación (R3.6): `params.egress_single` = fondo de saco máximo, `params.egress_multi` = recorrido máximo. Cada vivienda trae `egress` (recorrido), `saco` y `egress_status` (`ok`, `saco` o `fail`); `res["evacuacion"]` = {`saco`, `recorrido`: tramos del eje del pasillo que no cumplen, límites}; avisos por vivienda. La ubicación de núcleos automáticos sigue usando `egress_at` (mismo recorrido).
- **Viviendas editadas** (R4.4): `params.unit_edits` = [{`op`: `tabique`|`fusionar`|`dividir`, `p`: [x, y], `a`: [x, y]}] en orden, con puntos de mundo. `units.editar_unidades` los aplica en cada bloque después del mix y antes de `sin_solapes`: cada vivienda recuerda su franja (`_region`), `vecinas` da los pares contiguos de una franja, cada parte queda con al menos medio ancho mínimo y una vivienda unida o dividida toma el tipo del mix si su superficie se parece (±35 %) o uno por dormitorios. El resultado trae `tabiques` [{a, b, seg, dir}] (los arrastra la web) y `editada` en las viviendas cambiadas; los cambios que no entran se avisan.
- Programas por nivel: `params.stories` = [{program, height}]. Solo `Residential` recibe distribución; `metrics.programs` resume GFA/NIA/NSA por programa.

### Modelo del modo Masterplan (masterplan.py)
- Entrada: `predio` (polígono), `streets` [{pts, calzada, vereda}] (ejes), `frontage` (índices de bordes del predio que dan a calle existente; por defecto todos), `block_uses` {"x,y" del centroide: 'lotes'|'verde'|'equipamiento'}, `lot_mix` [{name, frente, percent}], `params.masterplan` (sobrescribe `standards.masterplan`).
- Calles: cada tramo recto de eje parte las piezas que **atraviesa** (`_spans`); un tramo que termina dentro de una manzana no la corta y avisa. Las T funcionan terminando el tramo sobre el eje de la otra calle; los quiebres deben estar en cruces o en el borde.
- Manzanas = piezas menos la franja de la calle (`_band`); ochava en esquinas convexas con ambos lados a calle (`_chamfer`).
- Lotes (`_lots_for_block`): marco del borde con calle más largo; dos filas si hay calle en ambos lados largos (tolerancia ±25° para bordes inclinados) y fondo ≥ 2 × `fondo_min`. La cantidad de lotes por fila es la mayor que entra sin achicar los frentes del mix; los lotes de borde bajo el área mínima se funden con el vecino. Estado del mix compartido entre manzanas.
- Construcción (`_building`): retiro frontal (también en el lado de esquina), lateral, de fondo (% del fondo) y tope de FOS; si el retiro lateral es 0 devuelve medianeras.
- `metrics`: predio, calles, calles_pct, manzanas, verde, equipamiento, cesiones_pct, reserva_pct (verde + equipamiento contra `reserva_min_pct`), lotes, lote_medio, lotes_obs, ocupacion, construible, viviendas_est.

### Colores (web)
Cada programa tiene un color base en `PROGS` (editable por el usuario y guardado en `localStorage`). Las áreas internas usan tonos del color de su programa con `tone(hex, L)`: estancias según `ROOM_L`, tipos de unidad según `UNIT_L`, pasillos y núcleos con el color de `Circulation`. No uses colores fijos para áreas: usa `roomColor(kind, programa)`, `unitColor(u)` o `circColor(parte)`.

### Medidas
Ningún tamaño de estancia, núcleo, baño o plaza se escribe a mano en el código: se lee de `standards.merged(params["standards"])`. Si agregas un espacio nuevo, agrega su mínimo y su típico a `standards.py` y a `STANDARDS.md` con la fuente.

## Reglas
1. **Solo biblioteca estándar de Python** en `engine/`, `server.py` y `tests/`. Si una dependencia es imprescindible, propónla primero y espera aprobación.
2. El script de Rhino debe funcionar en **Rhino 8 Mac y Windows** (CPython 3, línea `#! python 3` primera). Sin paquetes externos.
3. La web sigue siendo **un solo archivo** sin CDN ni build. Textos en español.
4. No cambiar el formato JSON de `/api/generate` o `/api/mass` sin mantener compatibilidad (Rhino y la web dependen de él). Si cambia, actualiza los tres lados.
5. Toda funcionalidad nueva o bug corregido lleva **una prueba** en `tests/`. Nunca dejes pruebas rotas.
6. Cambios pequeños y enfocados: una tarea del roadmap por rama/PR. No reformatees ni reorganices archivos que no tocas.
7. Al cerrar una tarea que cambia el comportamiento: sube `VERSION` en `engine/layout.py` y añade una línea en "Novedades" del `README.md`.

## Cómo trabajar
1. Lee la tarea (issue o ítem del `ROADMAP.md`). Si es ambigua, pregunta antes de programar.
2. **Propón un plan breve y espera aprobación** antes de cambios grandes (más de ~100 líneas o que toquen el modelo de piezas).
3. Implementa, ejecuta `python tests/test_engine.py` y, si tocas la web, comprueba en navegador headless que la página carga sin errores de consola (Playwright si está disponible).
   Si el motor cambia métricas de los ejemplos **a propósito**, actualiza las referencias (`python tests/regresion.py --actualizar`) y pega en el PR la tabla de `python tests/regresion.py` con lo que cambió. Si cambian sin querer, es un error: corrígelo.
4. En el PR explica en lenguaje de arquitecto: qué cambia en la planta, cómo probarlo en la web y en Rhino, y qué no se pudo probar.
5. **No puedes probar con Rhino.** Lo que no depende de la geometría se prueba en `tests/test_rhino.py` (Rhino simulado). Indica en el PR los pasos exactos para que el usuario lo pruebe y qué mensaje debería ver. Los mensajes del script empiezan con «Trazo:» y siempre dicen qué hacer.

## Comandos
```bash
python tests/test_engine.py        # pruebas (incluye las de regresión)
python tests/regresion.py          # tabla de métricas de cada ejemplo: referencia vs ahora
python tests/regresion.py --actualizar   # nuevas referencias (solo si el cambio es intencional o hay un ejemplo nuevo)
python server.py                   # http://127.0.0.1:8765
python -c "import ast;ast.parse(open('rhino/trazo_rhino.py').read())"   # sintaxis del script de Rhino
```
En GitHub, `.github/workflows/pruebas.yml` ejecuta las pruebas y valida el script de Rhino (sintaxis y primera línea `#! python 3`) en cada PR, con Python 3.9 y el más reciente, en Linux y Windows. El check «Pruebas» debe quedar verde antes de pedir que se acepte el PR.

## Problemas conocidos (contexto, no tareas)
- `clip_halfplane`/`clip_rect` siguen siendo Sutherland-Hodgman: en polígonos cóncavos dejan puentes de ancho cero si el corte separa la figura. Donde el resultado tiene que ser una figura (tramos de viviendas, unidades, pasillos, núcleos, retiros, manzanas, lotes) se usan `clip_rect_parts`, `clip_halfplane_parts` o `largest_part` (R2.2); úsalos también en código nuevo.
- Pasillos dibujados: tres o más líneas por un mismo punto y los cruces oblicuos dejan planta sin usar (sin solapes); en los empalmes en T y X, las viviendas del pasillo que sigue de largo junto al ramal pueden quedar sin luz (la lógica de codos de R3.2 es solo del modo automático).
- Codos (R3.2): donde el fondo de una franja da a otra ala no se ponen viviendas (`_franjas_sin_luz`); un núcleo de punta corta va a esa esquina (`_nucleo_en_codo`), la franja del ala que llega baja hasta la esquina exterior si su fondo da a la fachada (`_codos`) y lo que queda se marca «Sin luz natural» (`_zonas_oscuras`, `metrics.dark_area`). En las T y en codos donde el núcleo no entra, esa esquina queda sin luz. Tramos menores que el ancho mínimo se descartan (salvo los que quedaban entre un núcleo de punta y la fachada: R3.1).
- Plantas no ortogonales (R3.4): los patios interiores, el caso entre medianeras y los anillos siguen siendo solo ortogonales; las formas curvas (arcos) siguen con un solo pasillo.
- Masterplan: calles curvas, cruces en ángulo muy agudo y quiebres de calle a mitad de manzana no se resuelven todavía; no hay salida a Rhino/DXF del masterplan.

## Glosario
Masa: volumen del edificio. Zona de día: hall, cocina, comedor, estar. Zona de noche: pasillo interno, dormitorios, baños.
 Planta / plate: superficie útil por nivel. Crujía doble: pasillo central con unidades a ambos lados; simple: pasillo de borde.
Núcleo: escalera/ascensor. Ala: tramo rectangular de una planta. Mix: proporción de tipos de unidad.
GFA: superficie bruta. NSA: superficie neta vendible. Eficiencia: NSA / superficie de planta.
