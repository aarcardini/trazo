# ROADMAP — Trazo

Estado de partida: **v1.8** (medianeras y retiros) · **v1.7** (medidas reales y normativa, núcleo con escalera y ascensores, oficinas, comercio y estacionamiento) — antes **v1.5** (masa, alas automáticas, polilíneas, núcleos manuales, mix, axonometría 3D con selección de niveles por programa, planos día/noche con grafo de conexiones y comprobaciones; puente Rhino sin probar en Rhino real).

Cómo usar este archivo: cada ítem es una tarea para **una sesión de Claude Code y un PR**. Pide "implementa R1.2 del ROADMAP".
Cada PR marca su tarea con `[x]`: queda marcada cuando el PR se acepta. El orden importa: no saltes de fase sin acuerdo.

Leyenda de esfuerzo: S = pequeño, M = mediano, L = grande (dividir antes de empezar).

---

## Fase 0 — Base del repositorio
- [x] **R0.1 (S) README para Mac y Windows.** Instalación paso a paso en ambos sistemas (el `.gitignore` ya está incluido).
  *Hecho cuando:* el README explica cómo instalar, arrancar y usar el puente con Rhino en Mac y en Windows.
- [x] **R0.2 (S) Pruebas en GitHub Actions.** Workflow que ejecuta `python tests/test_engine.py` y valida la sintaxis del script de Rhino en cada PR (sin usar Claude, no consume saldo).
  *Hecho cuando:* un PR muestra el check verde o rojo.
- [x] **R0.3 (M) Pruebas de regresión.** Guardar en `tests/golden/` las métricas de cada ejemplo de `samples/` (unidades, eficiencia, sin usar, núcleos) y una prueba que avise si cambian más de un margen.
  *Hecho cuando:* cambiar el motor sin querer rompe una prueba con un mensaje claro. **Requisito de R2.1.**

## Fase 1 — Puente con Rhino fiable (requiere pruebas del usuario)
- [x] **R1.1 (M) Diagnóstico en Rhino.** Mensajes claros en la consola de Rhino para cada fallo (servidor apagado, objeto no válido, sin base plana, unidades). Comando de prueba que muestre versión de Rhino, unidades y estado del servidor.
  *Hecho cuando:* el usuario ejecuta Enviar/Recibir en Mac y Windows sin errores, o con un mensaje que explica qué hacer.
- [ ] **R1.2 (S) Modo archivo de respaldo.** Si la conexión HTTP falla, el script guarda/lee un JSON en una carpeta conocida, y la web permite cargarlo/descargarlo.
- [~] **R1.3 (M) Masas con varios volúmenes y huecos.** (v2.4: patios que separan la masa en bloques, automáticos y manuales, también desde Rhino con la capa `Trazo::Patios`; v2.6: patios rodeados de edificio —U cerrada o claustro— en masas ortogonales, con el pasillo alrededor del patio; falta: varias masas a la vez, con alturas distintas por bloque) Aceptar varias masas a la vez y huellas con patios (huecos interiores).
  *Hecho cuando:* una masa en U cerrada (con patio) genera unidades alrededor del patio.
- [x] **R1.4 (S) Recibir sin duplicar.** (v2.5: pregunta Reemplazar / Agregar / Cancelar; reemplaza también lo oculto o bloqueado y quita los niveles que sobran; los patios recibidos van en `Trazo::Lnn::Patios`) Al recibir de nuevo, borrar o reemplazar las capas `Trazo::L..` anteriores (preguntando antes).

## Fase 2 — Ordenar el motor (sin cambiar resultados)
- [x] **R2.1 (L) Dividir `layout.py`** (hecho: `massing.py`, `circulation.py`, `units.py` y `patios.py`; los planos de cada unidad ya estaban en `plans.py`; resultados idénticos byte a byte) en `massing.py`, `circulation.py` (piezas, uniones, núcleos), `units.py` (segmentos y mix), `plans.py` (estancias), con `layout.generate` como fachada.
  *Hecho cuando:* las pruebas de regresión de R0.3 pasan sin cambios. Dividir en 2-3 PRs si hace falta.
- [x] **R2.2 (M) Geometría robusta.** (v2.7: `clip_rect_parts`, `clip_halfplane_parts`, `largest_part`; viviendas, pasillos, manzanas y lotes ya no salen unidos por puentes) Recorte de polígonos que devuelva varias partes cuando el corte separa la figura (reemplaza los puentes de ancho cero de Sutherland-Hodgman).

## Fase 3 — Calidad de la planta
- [x] **R3.1 (M) Sin restos pequeños.** (v2.8: el núcleo de una punta se apoya contra la fachada cuando deja una franja demasiado chica para una vivienda, si llega a la fachada y la evacuación lo permite) Los tramos menores que el ancho mínimo se suman a la unidad vecina en vez de descartarse.
  *Hecho cuando:* "Sin usar" baja en los ejemplos L y T de `samples/` sin empeorar el match score.
- [x] **R3.2 (M) Codos más eficientes.** (v2.9: sin viviendas a oscuras en codos; el núcleo de la punta corta va a la esquina interior sin luz; la esquina exterior es de las viviendas del ala que llega; lo que queda sin luz se marca) Unidad de esquina en el codo interior (en L) en lugar de hueco.
- [x] **R3.3 (L) Cruces en X** (v2.10: la línea más corta se corta en el cruce y cada mitad se une a la otra como una T; tampoco hay solapes en codos de plantas anchas, ramas de una U, bolsillos de núcleos ni puntas con dos núcleos; la evacuación pasa por las uniones dibujadas en los dos sentidos) entre polilíneas sin solapes.
- [x] **R3.4 (L) Plantas no ortogonales en automático** (v2.12: los brazos con otra dirección se separan por una cuerda y cada parte se divide en alas en su propio marco; quiebres a inglete, T oblicuas, Y y ochavas; las convexas siguen con un solo pasillo) (por ejemplo, alas a 45° o trapecios): eje por ala.
- [x] **R3.5 (S) Núcleos con tamaño propio** (v2.13: clic en un núcleo en la planta: frente, fondo y giro; con giro 90° la escalera sube a lo largo del pasillo) y rotación 0/90°, editables por núcleo.
- [x] **R3.6 (M) Reglas de evacuación configurables** (v2.14: fondo de saco medido hasta un punto con dos direcciones de salida; estado y aviso por vivienda; tramos de pasillo y viviendas resaltados con la casilla «Evacuación») (fondo de saco, recorrido máximo) con aviso por unidad y resaltado en el plano.

## Fase 4 — Edición en la web
- [x] **R4.1 (M) Guardar y abrir proyectos** (v2.16: «Guardar proyecto» y «Abrir proyecto…» en la web; el archivo `.trazo.json` es el pedido al motor más nombre, versión y fecha, con solo las medidas cambiadas; también abre masas sueltas) (JSON con masa, líneas, núcleos, mix y parámetros).
- [x] **R4.2 (S) Deshacer/rehacer** (v2.17: botones ↶ ↷ y Ctrl/Cmd+Z, Ctrl/Cmd+Shift+Z o Ctrl+Y; también medianeras y patios) para líneas y núcleos.
- [x] **R4.3 (M) Arrastrar núcleos** (v2.18: vista previa punteada; al soltar pasa a manual, el motor lo ajusta al pasillo del lado donde quedó; se deshace con Ctrl+Z) con el ratón (como los vértices).
- [ ] **R4.4 (L) Editar unidades:** mover el tabique entre dos unidades vecinas, fusionar y dividir; métricas se actualizan.
- [x] **R4.5 (M) Variantes:** (v2.19: «Guardar como variante» y «Comparar»; tabla con lo mejor de cada columna en verde, abrir, renombrar, borrar y copiar a una planilla; se guardan con el proyecto) guardar varias soluciones y compararlas en una tabla (unidades, eficiencia, match, circulación).

## Fase 5 — Planos de unidad y conexiones internas
Hecho en v1.5: zonas día/noche, pasillo interno, puertas, grafo de conexiones (abierto/puerta) y comprobaciones por unidad.
- [ ] **R5.1 (M) Programa de la vivienda editable:** tabla en la web por tipología con estancias (m² y ancho mínimos) y conexiones requeridas (abierta, puerta, en suite). El motor la usa en lugar de las reglas fijas de `plans.py`.
  *Hecho cuando:* cambiar «cocina cerrada» (puerta) por «cocina integrada» (abierta) cambia el plano y su comprobación.
- [ ] **R5.2 (M) Variantes de distribución por unidad:** generar 3-4 alternativas (cocina a fachada o interior, dormitorio en suite, baño compartido) y elegir con la mejor puntuación o a mano.
- [ ] **R5.3 (M) Segunda fachada:** unidades de esquina o extremo usan la fachada lateral (dormitorios o estar ahí) y se reconoce en la comprobación de luz.
- [ ] **R5.4 (M) Biblioteca de plantas tipo** en JSON (estancias en proporciones relativas) con estiramiento al tamaño de la unidad y muros bloqueados, como la "adaptive plan library" de Finch.
- [ ] **R5.5 (S) Ventanas** en fachada por estancia habitable, exportables a Rhino.
- [ ] **R5.6 (L) Mobiliario básico** por estancia (bloques 2D) y comprobación de que cabe (círculo de giro, paso libre).
- [ ] **R5.7 (M) Editar la unidad a mano:** mover tabiques y puertas en la ficha de la unidad; las comprobaciones se recalculan.

## Fase 6 — Varias plantas
- [ ] **R6.1 (M) Plantas distintas por nivel** (por ejemplo, PB comercial y tipo residencial) con su propio mix.
- [ ] **R6.2 (L) Retranqueos:** masas cuya huella cambia con la altura (cortes por nivel desde Rhino).

## Fase 7 — Salida
- [ ] **R7.1 (M) Exportar a Rhino con muros con espesor** (extrusiones por nivel) además de las polilíneas.
- [ ] **R7.2 (S) Tabla de unidades** en CSV (id, tipo, m², dormitorios, nivel, evacuación).
- [ ] **R7.3 (M) Lámina PDF** de la planta tipo con métricas.

## Fase 8 — Modo Terreno (masterplan / fraccionamiento)
Segundo modo de la herramienta: subdividir un predio en calles, veredas, manzanas y lotes. **Prototipo hecho en v2.0** (`engine/masterplan.py`, `web/masterplan.html`): damero y calles dibujadas con cruces y T, ochavas, usos de manzana, lotes por mix, construcción por lote y paso al modo Edificio. Lo que falta abajo.
- [x] **R8.0 (S) Selector de modo al abrir la web:** (v2.0: dos páginas enlazadas, `/` y `/masterplan`) «Edificio» (lo actual) o «Terreno». El modo viaja en `/api/generate` como `mode`; el modo Edificio no cambia.
- [~] **R8.1 (M) Predio de entrada:** (v2.0: dibujado en la web y ejemplos; falta Rhino y huecos) curva cerrada en la capa `Trazo::Terreno` desde Rhino, o dibujada en la web. Admite preexistencias a respetar (huecos).
- [~] **R8.2 (L) Calles con perfil:** (v2.0: perfil por calle, cruces, T, ochavas; faltan calles curvas, radio de cordón y quiebres a mitad de manzana) polilíneas de eje con perfil configurable (calzada + veredas a cada lado), cruces en X y T, esquinas con ochava o radio de cordón.
  *Hecho cuando:* un predio con dos calles cruzadas muestra calzadas, veredas y cuatro manzanas sin solapes.
- [x] **R8.3 (M) Manzanas:** áreas resultantes del predio menos las calles; marcar manzanas como espacio verde o equipamiento.
- [~] **R8.4 (L) Lotes:** (v2.0: mix, dos filas, esquinas, fusión de lotes chicos; falta subdividir manzanas en L o muy irregulares por cada frente) subdividir cada manzana por frente a calle con frente mínimo, área mínima y fondo máximo; mix de tamaños de lote (como el mix de unidades); lotes de esquina.
- [x] **R8.5 (M) Métricas y normativa configurable:** % viario, % de cesiones (verde/equipamiento), área vendible, nº de lotes, área media. Los valores normativos los ingresa el usuario (no se asume una norma).
- [ ] **R8.6 (M) Salida:** a Rhino y DXF con capas para ejes, cordones, líneas de propiedad y numeración de lotes; tabla de lotes en CSV.
- [x] **R8.7 (M) Del lote al edificio:** (v2.0, sin FOT todavía) generar una masa en un lote a partir de retiros, FOS y FOT/altura, y abrirla en el modo Edificio.
- [ ] **R8.8 (M) Calles curvas y rotondas:** ejes con arcos (polilínea suavizada), radio de cordón en esquinas.
- [ ] **R8.9 (S) Normativa departamental del fraccionamiento:** ancho de calle, ochava y cesiones según el departamento (Montevideo, Canelones, Maldonado) como valores preestablecidos.
- [ ] **R8.10 (M) Lotes en manzanas irregulares:** lotear cada frente por separado (manzanas en L, triangulares) y lotes «en martillo».

## Fase 11 — Predio y restricciones (continúa v1.8)
- [ ] **R11.1 (M) Predio y edificio separados:** dibujar el predio completo y el retiro frontal/posterior (FOS, retiros obligatorios) para que la masa se calcule desde el predio.
- [~] **R11.2 (M) Patios de aire y luz:** (v2.4: patios entre bloques con ancho mínimo editable; las estancias que dan a ellos tienen luz) abrir patios interiores con medida mínima y que las estancias que dan al patio cuenten como iluminadas.
- [ ] **R11.3 (S) Ventanas de baño y cocina a patio o ducto** según normativa (ventilación por ducto permitida para baños).
- [ ] **R11.4 (M) Entre medianeras con más de dos viviendas por piso:** pasillo a lo largo contra una medianera y viviendas pasantes o con patio.
- [ ] **R11.5 (S) Confirmar con el Digesto de Montevideo** la regla de 3 m de retiro para abrir vanos hacia el lindero.

## Fase 10 — Medidas y programas (continúa v1.7)
- [ ] **R10.1 (S) Confirmar mínimos de Montevideo** en el Digesto (Volumen XV) y ajustar `standards.py` si difieren de las ordenanzas usadas.
- [ ] **R10.2 (M) Rampas de estacionamiento** (pendiente, ancho, radio de giro) y plazas accesibles; ubicación de la rampa junto a la calle transversal.
- [ ] **R10.3 (M) Antecámara y presurización** de la escalera según altura (EP/PFP) dibujadas en el núcleo; segunda escalera cuando el recorrido lo exija.
- [ ] **R10.4 (M) Locales comerciales** opcionales: dividir la planta libre en locales con frente a calle y tamaño objetivo.
- [ ] **R10.5 (S) Exportar núcleo, baños y plazas** a Rhino y DXF con capas propias.
- [ ] **R10.6 (M) Muebles de referencia** en dormitorios, baños y cocina para validar que las medidas típicas funcionan.

## Fase 9 — Ideas tomadas de Finch3D (documentación pública)
- [ ] **R9.1 (M) Propiedades por programa:** costo/m², emisiones/m² u otras métricas propias, sobre GFA o NIA, visibles en el anillo y por nivel ("custom properties" de Finch).
- [ ] **R9.2 (S) Excluir programas de GFA/NIA** (por ejemplo, estacionamiento).
- [ ] **R9.3 (M) Copiar planta entre niveles** y plantas distintas por nivel (complementa R6.1).
- [ ] **R9.4 (M) Pesos de prioridad** (sliders): ajuste al mix, precisión de m², alineación a grilla, luz natural, cuadratura; el generador los usa para elegir entre alternativas.
- [ ] **R9.5 (M) Atractores de núcleos:** indicar fachadas o puntos hacia donde se orientan los núcleos.
- [ ] **R9.6 (M) Comparar variantes** con un diagrama de ejes paralelos (unidades, eficiencia, match, circulación, costo).
- [ ] **R9.7 (M) Sol:** posición solar por fecha/hora en la axonometría y sombras simples.
- [ ] **R9.8 (S) Atajos de teclado** (W muro, D cotas, Shift para alinear) y cotas en la planta.

## Ideas sin priorizar
Topografía y pendientes de calles en el modo Terreno; calles curvas;
Componentes de Grasshopper; optimización con varias soluciones y puntuación (como los "sliders de prioridad" de Finch); soleamiento por fachada; costos por m² en pesos uruguayos.

---

## Plantilla para pedir una tarea nueva
```
Título:
Objetivo (qué quiero ver en la planta o en la web):
Criterios de aceptación (cómo sé que está bien):
-
Ejemplo para probar (archivo de samples/ o coordenadas):
Fuera de alcance:
```
