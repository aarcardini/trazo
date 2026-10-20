# Base de tipologías — convención de los DXF y prompt para prepararlos

Para mejorar los planos del motor con planos reales: tipologías de vivienda (una unidad por archivo) y plantas enteras de vivienda colectiva (cómo se organizan las unidades, los pasillos y los núcleos). Los planos se preparan **fuera de este repositorio**, en un proyecto de Claude (o con otra herramienta) que los homogeneiza con la convención de la sección 1; después, un lector de Trazo (`engine/tipologias.py`, pendiente: R5.16 del ROADMAP) los lee desde `data/tipologias/` y arma el catálogo (frente × fondo, superficie de cada estancia, posición del núcleo húmedo, entrada, fachadas) que sirve para calibrar los típicos, para pruebas («con 6 × 7 m el motor tiene que sacar algo parecido a esta tipología») y, más adelante, para un catálogo de distribuciones.

El primer lote (67 DXF de seis proyectos de Montevideo) ya está en `data/tipologias/`. Lo que se decidió al prepararlo quedó como regla en esta convención; `data/tipologias/CRITERIOS.md` es el registro de ese lote: las decisiones, en qué se apartaron los archivos de la convención tal como estaba y las diferencias con cada fuente.

## 1. Convención de los archivos

**Formato.** DXF de texto (no binario), versión AutoCAD 2000 (AC1015) **completo** —tablas, handles y subclases, como lo escribe ezdxf— con LWPOLYLINE; los textos en cp1252, como declara `$DWGCODEPAGE` (así `Baño` se lee bien). Unidades: **metros**, con `$INSUNITS` = 6 en el HEADER; todo en Z = 0. Sin SPLINE, HATCH, cotas (DIMENSION), bloques anidados ni referencias externas. Coordenadas redondeadas a 0,01 m; vértices ajustados a una grilla de 0,05 m cuando el original lo permite. Sin tildes ni espacios en los nombres de capa. El ejemplo mínimo `tests/dxf/tipologia_2d.dxf` sirve para las pruebas del visor, no como modelo de formato: los lectores estrictos lo rechazan. (El lector de Trazo también acepta R12, con POLYLINE.)

**Orientación y origen.** Planos ortogonales a los ejes: se rota el dibujo para que la **fachada principal** (la de la calle) quede **arriba** y, si hay, el **pasillo común** abajo y horizontal. En una unidad, el origen (0, 0) es la esquina inferior izquierda de su contorno y el pasillo común está **abajo** (lado y = 0). Si el pasillo común no puede quedar abajo (unidad de punta que se entra por el extremo, de esquina…), manda la fachada principal arriba y la excepción se explica en `observaciones`. En una planta entera, el origen es la esquina inferior izquierda de la caja que contiene la planta; con la calle a la izquierda de la página se gira en sentido horario, con la calle abajo, 180°. En una planta, un palier corto puede quedar vertical (se anota) y un palier en anillo no se gira: si la calle ya está arriba, la planta queda como está. Un lindero o un muro oblicuo se dibuja oblicuo, sin enderezarlo.

**Norte.** Se dibuja aparte (capa `Trazo_Norte`, una línea) y no se gira el plano hacia él; el ángulo va en `norte:` de los metadatos, calculado para el giro de cada archivo. Si la fuente no trae el símbolo, `norte: desconocido` y sin línea; `ver_dxf` no avisa «sin norte» en ese caso.

**Capas** (nombre exacto; «cerrada» = polilínea cerrada, sin autointersecciones, sin superponerse con otras de la misma capa):

| Capa | Entidades | Qué es | Etiqueta (TEXT dentro de la figura) |
|---|---|---|---|
| `Trazo_Datos` | TEXT, una línea por dato | metadatos del plano, `clave: valor` (ver abajo) | — |
| `Trazo_Norte` | una LINE | del punto base a la punta, apuntando al norte | — |
| `Trazo_Unidad` | una polilínea cerrada por vivienda | contorno de la vivienda: **eje de los muros divisorios y de los muros al pasillo común (o al palier y al núcleo), cara exterior del muro de fachada, eje de los muros de lindero** (la superficie «con muros» de la ANV, comparable con `area_muros` de Trazo); sin balcones, terrazas ni patios propios, que van en `Trazo_Cotas` | `<tipología> <m²>`: `Mono 30.5`, `1D 42.0`, `2D 58.3`, `3D 78.0` (la tipología por la cantidad de dormitorios cerrados, los `Dormitorio n`; `Mono` si no hay ninguno, aunque haya una zona `Dormir`; en una vivienda de varios niveles, la de toda la vivienda) |
| `Trazo_Estancias` | una polilínea cerrada por local, por la cara interior de sus muros | cada estancia de la vivienda, sin solaparse, con su color (ver «Estancias») | el nombre, de la lista de «Estancias» |
| `Trazo_Puertas` | una LINE por puerta, sobre la línea del muro, del largo de la hoja (luz libre) | puertas interiores; opcional, un ARC con el barrido | — |
| `Trazo_Entrada` | una LINE | la puerta de entrada de la vivienda (igual que las otras, en su capa); el nivel de una vivienda que no tiene puerta al palier no la lleva | — |
| `Trazo_Ventanas` | una LINE por ventana, sobre la cara exterior del muro, del ancho del vano | ventanas y puertas-ventana | opcional: `h <alto> a <antepecho>` (`h 1.20 a 0.90`) |
| `Trazo_Fachada` | LINE o polilínea abierta | los tramos del contorno de la vivienda que dan al exterior (fachada, patio, pasarela, terraza): es lo que da luz | opcional: `Calle`, `Contrafrente`, `Patio` (también el patio entre dos bloques y el frente a una pasarela); las fachadas laterales, sin rótulo |
| `Trazo_Medianeras` | una LINE por tramo | tramos del contorno contra un lindero ciego (en una planta entera, los del terreno; un edificio exento no lleva) | — |
| `Trazo_Muros` | polilíneas cerradas (opcional) | los muros cortados, con su espesor (si el original los tiene) | — |
| `Trazo_Equipamiento` | polilíneas, LINE, ARC, CIRCLE (opcional) | muebles y artefactos tal como están dibujados en el original (sirven para los símbolos); muebles en color 9 y artefactos en color 8 | el nombre de los principales: `Cama 1.40x1.90`, `Sofa`, `Mesa 4`, `Placard`, `Escritorio` y, de los artefactos, `Mesada`, `Heladera`, `Lavarropas`, `Inodoro` |
| `Trazo_Terreno` | una polilínea cerrada | solo en plantas enteras: el contorno exterior del edificio (ver «Plantas enteras») | — |
| `Trazo_Patios` | polilíneas cerradas | patios y vacíos del edificio (dentro o al borde del terreno) y, cuando el terreno es el lote, lo libre de cada planta | — |
| `Trazo_Pasillo` | polilíneas cerradas | solo en plantas enteras: los pasillos y palieres comunes y las pasarelas al aire libre; una planta sin él es un piso al que no se entra | — |
| `Trazo_Nucleos` | una polilínea cerrada por núcleo | solo en plantas enteras: escalera + ascensores + ductos de cada núcleo | `Nucleo 1`, `Nucleo 2`; dentro, opcional, `Escalera`, `Ascensor`, `Ducto` en sus rectángulos |
| `Trazo_Cotas` | polilíneas cerradas con su texto, LINE, TEXT (opcional) | lo que queda fuera de la vivienda o del edificio: balcones, terrazas, patios y jardines propios, cocheras, amenities y otros locales que no son vivienda; también las cotas y textos del original, por si hace falta volver a mirar. El lector del catálogo no la usa; `ver_dxf` lista las polilíneas cerradas con texto como «otros recintos» | el nombre y, si se quiere, las medidas o la superficie: `Balcón 1.00x5.80`, `Cochera 12`, `Gimnasio 18.97 m2` |

En una planta entera van **todas** las capas: cada vivienda con su `Trazo_Unidad` y, si el original lo permite, sus `Trazo_Estancias`, puertas y ventanas; si no hay tiempo de estanciar todas, por lo menos los contornos de las unidades, el pasillo, los núcleos, los patios y la entrada de cada vivienda.

**Estancias.** Las etiquetas de `Trazo_Estancias` son: `Hall`, `Estar`, `Comedor`, `Estar-Comedor` (un solo local), `Cocina`, `Cocina integrada` (abierta al estar), `Pasillo` (interno; también las escaleras interiores), `Dormitorio 1` (el principal), `Dormitorio 2`…, `Dormir`, `Baño`, `Baño 2`, `Baño en suite`, `Toilette`, `Lavadero`, `Depósito`, `Estudio`, `Vestidor`. Nada más: si un local no encaja, el más parecido y una nota en `observaciones`. Para los casos dudosos:

- **`Dormir`** es la zona de dormir de un monoambiente, sin cerramiento (la separa un placard, un tabique bajo o nada). Es habitable —necesita ventana— pero no cuenta como dormitorio: `Mono` es la vivienda sin dormitorio cerrado, con `dormitorios: 0`, aunque la fuente la venda como «1 dormitorio» (se anota en `observaciones`).
- **Exteriores propios** (balcón, terraza, patio, jardín): no son estancias. Van **fuera** del contorno de la vivienda, en `Trazo_Cotas`, como polilínea cerrada con su texto (el nombre y, si se quiere, las medidas). Sus medidas, y las de la fuente si difieren, van en `observaciones`. Si el patio propio es además un patio del edificio (un jardín en PB, el fondo del lote en el piso 1), en la planta va en `Trazo_Patios` y en el `U_`, en `Trazo_Cotas`.
- **Dormitorio o estudio:** un local cerrado se nombra según su amueblamiento; con escritorio es `Estudio`, y la tipología cuenta solo los `Dormitorio n`. Si es el único local cerrado de la vivienda, aunque esté amueblado como oficina, es `Dormitorio 1` (se vende como 1 dormitorio y no pasa a `Mono` con un cuarto cerrado) y el amueblamiento va en `observaciones`; si hay otros dormitorios, es `Estudio`. Si la fuente anuncia otra cosa (un dormitorio donde hay un escritorio), también en `observaciones`.
- **Estar abierto:** el ambiente de estar, comedor y cocina sin muros se parte en `Estar`, `Comedor` y `Cocina integrada` como polígonos contiguos, sin muro entre ellos. Los límites siguen el amueblamiento: la cocina es la mesada y su zona de trabajo, el comedor la mesa con sus sillas, el estar el sofá. Si no hay sofá ni una mesa de comedor clara, el ambiente va entero como `Estar-Comedor`. Los límites son una deducción: se anota en `estimado`. El comedor o el estar interior de ese ambiente no es una falla de fachada (ver el control 6).
- **Nicho o antebaño sin puerta propia** va con el local al que abre: el nicho de la heladera junto a la entrada, con el `Hall`; el antebaño, con el `Baño`; el pasillo de los dormitorios sin puerta hacia el hall, con el `Hall`; el paso del dormitorio principal al baño en suite, abierto al dormitorio, con el `Dormitorio 1`.
- **Tabique corredizo** entre el estar y un dormitorio: cuenta como cerramiento y cada hoja que abre va como una puerta.
- **Vestidor** abierto al dormitorio, sin muro: va como `Vestidor`, separado por una línea de zona.
- **Entrada no dibujada** (frente vidriado sin puerta): el paño corredizo que marca la ficha es la entrada y los demás paños son ventanas; se anota en `estimado`.

**Color y rótulos.** Cada estancia lleva su color (color por entidad, dentro de `Trazo_Estancias`), para que los usos se lean en Rhino: Dormitorio 5; Estudio 150; Estar y Estar-Comedor 2; Comedor 40; Cocina y Cocina integrada 30; Baño y Toilette 4; Hall y Pasillo 8; Lavadero, Depósito y Vestidor 6; `Dormir`, el mismo que Dormitorio (5). En los locales angostos, el nombre va girado 90° a lo largo del local. En `Trazo_Equipamiento`, los muebles van en color 9 y los artefactos en color 8, y los muebles y artefactos principales con su nombre (`Cama 1.40x1.90`, `Sofa`, `Mesa 4`, `Placard`, `Escritorio`, `Mesada`, `Heladera`, `Lavarropas`, `Inodoro`).

**Viviendas en varios niveles** (dúplex, tríplex): un DXF por nivel, con el mismo número de unidad y el sufijo `-N1`, `-N2`, `-N3` antes de `.dxf` (`U_MVD_Maua_3D_5.79x9.43_05-N1.dxf`). Todos los niveles con el mismo origen (la esquina inferior izquierda de la caja de todos los niveles), así que se superponen tal cual. `tipologia` y `dormitorios` son los de toda la vivienda; `superficie_muros` es la del nivel, con la total entre paréntesis. El nivel sin puerta al palier no lleva `Trazo_Entrada` y lo dice en `nivel:` (`nivel 2 de 2, nivel superior: dormitorios y baño`). Las escaleras interiores van como `Pasillo`. `ver_dxf` lee el sufijo: con cualquier `-N` no compara la tipología con los dormitorios del nivel y desde `-N2` no pide `Trazo_Entrada`. Si una planta muestra un solo nivel de una de esas viviendas, su etiqueta sigue siendo la de toda la vivienda (el visor avisa que no coincide con los dormitorios dibujados: es un aviso que se acepta).

**Plantas enteras.**

- `Trazo_Terreno` es el contorno exterior del edificio: incluye los patios contra los linderos y deja afuera los retiros abiertos a la calle y los balcones. Si el edificio no llena el lote en todos los pisos, es el lote por la cara exterior de los muros de lindero, desde la línea de retiro, y lo libre del lote en cada planta (también donde un bloque ya terminó) va en `Trazo_Patios`. Edificio exento: la losa con las terrazas, sin `Trazo_Medianeras`.
- Dos bloques en un lote: cada uno con su palier y su núcleo (`Nucleo 1`, `Nucleo 2`). Un núcleo que el palier parte va en dos polígonos, rotulado una sola vez.
- Las pasarelas al aire libre son `Trazo_Pasillo`; los vacíos (el del patio y los otros), `Trazo_Patios`; el frente de la vivienda hacia la pasarela es fachada, rotulada «Patio».
- Cocheras, amenities y otros locales que no son vivienda (la planta baja de cocheras, los amenities de un nivel con viviendas): en `Trazo_Cotas`, cada uno con su nombre y, si se quiere, su superficie. El hall, el pasillo a las cocheras y el lobby van en `Trazo_Pasillo`.
- Pisos a los que no se entra (los niveles superiores de un dúplex): sin `Trazo_Pasillo`; si la franja del pasillo es un vacío, las ventanas hacia él llevan `Trazo_Fachada` «Patio». El visor dice «planta sin palier» y no avisa de entradas.
- Los niveles sin superficie cerrada de vivienda (azoteas descubiertas o comunes, la PB y el subsuelo sin viviendas) no llevan DXF; se anotan en `observaciones` de los otros niveles.

**Pisos que repiten las mismas viviendas.** Un piso con las mismas viviendas que otro (sin balcones, o con patios propios en lugar de balcones) lleva su `P_` propio, pero sus viviendas no llevan `U_` aparte: se anotan en las `observaciones` del `U_` que se repite (vale también para viviendas sueltas de niveles con otra planta; el `U_` sale del nivel que más se repite). Si el dibujo está corrido unos centímetros pero los muros coinciden (99 % o más), se usan las medidas de la planta tipo y se dice en `estimado`. Si cambia una fachada (un lado contra otra vivienda pasa a tener ventanas), es otra tipología.

**Superficies y números.** `superficie_util` es la suma de las estancias medida en el DXF; las superficies de la fuente (el «área interior» de la carpeta, la total) van en `observaciones`, y no se corrige el dibujo para que coincidan. Las unidades que la fuente no numera se nombran por su posición («norte izquierda»).

**Metadatos** (`Trazo_Datos`, un TEXT por línea, en cualquier lugar fuera del dibujo; las claves en minúscula):

```
fuente: proyecto propio | revista | portal inmobiliario | concurso | otro (y el nombre o el enlace)
ciudad: Montevideo
proyecto: Edificio Cordón 12
autor: (estudio o desarrollador, si se sabe)
anio: 2021
tipo: unidad | planta
nivel: planta tipo (o 3, PB…; en un nivel de varios: «nivel 2 de 2, nivel superior: dormitorios y baño»)
tipologia: 2D (en varios niveles, la de toda la vivienda)
dormitorios: 2 (los Dormitorio n; Dormir no cuenta)
superficie_util: 52.4 (suma de las estancias, medida en el DXF)
superficie_muros: 58.3 (la del contorno de Trazo_Unidad, medida en el DXF; en varios niveles, la del nivel y la total entre paréntesis)
frente: 8.00 (ancho sobre la fachada principal)
fondo: 7.25 (desde el pasillo común hasta la fachada)
crujia: doble | simple | esquina | pasante | duplex
norte: 15 | desconocido (grados, antihorario desde +Y, igual que la línea de Trazo_Norte)
escala_original: 1:100 (o «sin escala: ancho de puerta 0,80 supuesto»)
precision: alta | media | baja (ver «Verificación y qué esperar de cada origen»)
estimado: (qué se dedujo y cómo, si hay algo)
observaciones: (lo que no encaja en la convención)
```

**Nombres de archivo** (sin espacios ni tildes): unidades `U_<ciudad>_<proyecto>_<tipologia>_<frente>x<fondo>_<nn>.dxf` (`U_MVD_Cordon12_2D_8.0x7.25_01.dxf`; un nivel de una vivienda en varios, con `-N<n>` antes de `.dxf`); plantas `P_<ciudad>_<proyecto>_<nivel>.dxf` (`P_MVD_Cordon12_tipo.dxf`). Junto a los DXF, un `indice.csv` (UTF-8, separador «;», coma decimal) con una fila por archivo y las columnas: `archivo; tipo; ciudad; proyecto; anio; fuente; tipologia; dormitorios; superficie_util; superficie_muros; frente; fondo; crujia; estancias (n); precision; observaciones`.

**Control antes de entregar cada plano:**
1. Todas las polilíneas de `Trazo_Unidad`, `Trazo_Estancias`, `Trazo_Terreno`, `Trazo_Patios`, `Trazo_Pasillo` y `Trazo_Nucleos` están cerradas y no se cruzan a sí mismas.
2. Las estancias no se superponen entre sí y quedan dentro de su unidad; la suma de sus superficies más los muros interiores es parecida a la del contorno (diferencia menor del 8 %).
3. Cada estancia tiene una etiqueta de la lista, y una sola; cada unidad tiene la suya. Ningún exterior propio (balcón, terraza, patio) es una estancia.
4. La `superficie_muros` de los metadatos coincide con el área del contorno medida en el DXF (diferencia menor del 2 %); si la fuente da otra superficie, se anota en `observaciones`, no se corrige el dibujo para que coincida.
5. Hay una `Trazo_Entrada` por vivienda, sobre un borde que da al pasillo común (o a la calle en planta baja); las puertas y ventanas están sobre las líneas de los muros. Se exceptúan el nivel superior de una vivienda en varios niveles (`-N2`…) y las plantas sin `Trazo_Pasillo`.
6. Hay `Trazo_Fachada` en todos los tramos que dan al exterior; todo dormitorio, estudio, `Dormir`, estar y comedor toca una fachada. Un estar o un comedor interior de un ambiente abierto no necesita tocarla si otro local contiguo del mismo ambiente (`Estar`, `Comedor`, `Cocina integrada`, `Dormir`) la toca, en cadena (`Cocina integrada` → `Comedor` → `Estar` con fachada). Los dormitorios y estudios cerrados sí; si alguno no la toca, se anota en `observaciones`.
7. El plano está rotado con la fachada principal arriba y, en una unidad, el pasillo común horizontal y abajo; el norte, en `Trazo_Norte` (o `norte: desconocido`); el origen, en la esquina inferior izquierda.
8. Unidades en metros (`$INSUNITS` = 6), Z = 0, sin SPLINE, HATCH, cotas ni bloques anidados; nombres de capa exactos; textos en cp1252 según `$DWGCODEPAGE`.
9. Metadatos completos; lo deducido, marcado como `estimado`.

**Verificación y qué esperar de cada origen.** Un plano redibujado puede *parecer* correcto sin serlo (un tabique corrido, una puerta en el lado equivocado), así que cada DXF se verifica antes de entrar al repositorio:

- `ver_dxf` sobre cada archivo (en el entorno donde se preparó y otra vez en el repositorio): `python tools/ver_dxf.py plano.dxf` escribe `plano.svg` (capas con color, estancias con su superficie, entrada, ventanas, norte, datos, los otros recintos de `Trazo_Cotas`) e imprime el informe de control: polilíneas abiertas, estancias sin etiqueta o con una que no está en la lista, estancias fuera de su vivienda o superpuestas, vivienda sin entrada, habitables que no tocan la fachada, `superficie_muros` distinta de la medida y datos que faltan; termina con 1 si hay errores. El visor no avisa de lo que la convención acepta (el nivel superior sin entrada, la planta sin palier, el comedor o el estar interior de un ambiente abierto); un aviso que queda se explica en los metadatos (por ejemplo, `norte: desconocido`).
- Una imagen de lo dibujado (SVG o PNG) para compararla con el original y, por cada planta, una `_comparacion.png` con lo dibujado sobre el original. Las imágenes y los originales quedan fuera del repositorio.
- La lectura del DXF sin errores ni reparaciones en un lector estricto (`ezdxf.recover`) y una vista CAD para comprobar que los usos se leen (cocina, comedor, estar y dormitorios, con su color y su rótulo).
- En el repositorio, `test_base_tipologias` pasa todos los DXF de `data/tipologias/` por el control (sin errores) y los cruza con `indice.csv`.

Lo que se puede esperar según el origen (el método de cada uno, en pocas líneas):

| Origen | Cómo se procesa | Precisión | Para qué sirve |
|---|---|---|---|
| DXF o PDF vectorial con muros ortogonales (las líneas se pueden seleccionar en el visor) | la geometría se extrae con código, se escala y se clasifica por capa; hay que revisar la clasificación (muro, mueble, cota) y cerrar las estancias; los locales se ajustan como rectángulos a las caras de los muros y los contornos, a los ejes y caras medidos en el PDF | `alta` | todo: calibrar medidas de estancias, pruebas de regresión, catálogo |
| Vectorial con muros oblicuos | cada local es el relleno del espacio libre entre muros, cortado con las puertas, los vidrios y los límites de zona y limpio de las muescas de lámparas, marcos y artefactos; después se ajusta lado por lado a la cara del muro, y los oblicuos quedan oblicuos | `alta` | igual |
| Plano clave vectorial con fichas en imagen | muros, aberturas y equipamiento salen de los vectores del plano; la escala se verifica con las medidas de las fichas; los locales son el espacio libre entre muros (un cierre falso dentro de un local, como un lavatorio en nicho, se une a él); los muros se reparten por cercanía entre viviendas, palier y núcleo y los contornos se recortan en el eje de los linderos | `alta` | igual |
| Imagen o PDF escaneado **con escala gráfica y cotas** | se usa la imagen visible; la escala sale de la escala gráfica y se verifica con las cotas de las fichas; cada muro se mide con perfiles de grises (caras interpoladas, 1 a 2 cm de error); coordenadas a 1 cm; el equipamiento se vectoriza de la imagen (trazos aproximados, se dice en `estimado`). Sin escala gráfica, la planta se redibuja por estimación con las medidas de las cotas o de la superficie (errores de 5–10 %) | `media` | tipología, mix, superficies, organización (núcleo húmedo, entrada, estar y comedor en línea), pasillos y núcleos de la planta entera |
| Imagen **sin escala ni cotas, con las superficies publicadas** | la escala sale de las superficies (la que hace coincidir la suma de los contornos con la suma de las áreas) y se controla con el ancho de las puertas interiores y las camas; como las áreas se usaron para la escala, su coincidencia no es un control independiente (se dice en `estimado`); los locales son rellenos entre muros con las puertas cerradas y un recorrido desde la entrada comprueba que se llega a todos; las ventanas son los tramos de fachada sin muro macizo; los muebles se nombran por el tamaño de su grupo de trazos y, si no es claro, no llevan nombre | `media` | igual |
| Imagen **sin cotas ni superficies** | igual, con la escala deducida de una puerta o una cama; `estimado` lo dice | `baja` | solo la organización y la tipología; no para calibrar medidas |
| DWG | no se puede leer: exportar a DXF de texto (AutoCAD 2000) desde Rhino o AutoCAD | — | — |

Para plantas enteras conviene pedir primero solo contornos de unidades, pasillo, núcleos, patios y entradas (lo más fácil de ver y lo más útil para estudiar circulaciones) y estanciar solo las unidades con cotas. Las tipologías que más importen se calcan mejor a mano en Rhino sobre la imagen, con las capas de la convención (10–15 minutos por unidad): el proyecto de Claude solo valida y arma los metadatos.

## 2. Prompt para el proyecto de Claude que prepara los planos

Copiar como instrucciones del proyecto (tal cual, incluida la convención de la sección 1, pegada al final).

---

Eres un dibujante técnico que prepara planos de vivienda para alimentar una base de datos de tipologías. Recibes planos de apartamentos y de plantas enteras de edificios de vivienda colectiva (en DXF, PDF, imágenes PNG o JPG, o descripciones con medidas) y los devuelves **homogeneizados en un DXF por plano** (por nivel, si la vivienda tiene varios), siguiendo al pie de la letra la **Convención Trazo** que está al final de estas instrucciones. Trabajas en español neutro, con el usuario, que es arquitecto.

Qué hacer con cada plano que te den:
1. **Identificar la fuente y la escala.** Si el archivo es DXF, úsalo directamente. Si es PDF vectorial, extrae la geometría con código (no la redibujes). Si es una imagen o un PDF escaneado, **redibuja** la planta con las cotas, la escala gráfica o la superficie publicada y dilo en `precision` (`media`); si no hay cotas, busca cotas; si no hay, deduce la escala con un elemento conocido (una puerta interior de 0,70–0,80 m, un inodoro de 0,70 m de fondo, una cama de 1,40 × 1,90) y declara el supuesto en `escala_original` y `estimado`. El método de cada tipo de fuente y su precisión están en la convención. Si te dan un DWG, pide que lo exporten a DXF de texto (AutoCAD 2000): no puedes leerlo.
2. **Orientar.** Rota el plano para que la fachada principal quede arriba y, en una unidad, el pasillo común abajo y horizontal (si no puede quedar abajo, explícalo en `observaciones`); en una planta, el pasillo principal horizontal (un palier corto puede quedar vertical; uno en anillo no se gira). Lleva el origen a la esquina inferior izquierda. Dibuja el norte en `Trazo_Norte` y su ángulo en `norte:` si la fuente lo da; si no, `norte: desconocido`.
3. **Trazar.** El contorno de cada vivienda en `Trazo_Unidad` (eje de los muros divisorios y del muro al pasillo, cara exterior de la fachada); cada estancia en `Trazo_Estancias` por la cara interior de sus muros, con su etiqueta de la lista y su color; los balcones, terrazas y patios propios **fuera** del contorno, en `Trazo_Cotas`, con su texto; puertas, entrada, ventanas, fachadas y medianeras en sus capas; en una planta entera, además el terreno, los patios, los pasillos comunes y los núcleos. Parte el estar abierto en `Estar`, `Comedor` y `Cocina integrada` según el amueblamiento (sin sofá ni mesa clara, `Estar-Comedor`) y anótalo en `estimado`; rotula `Dormir` la zona de dormir de un monoambiente. Dibuja el equipamiento en `Trazo_Equipamiento` si el original lo tiene (muebles en color 9, artefactos en color 8, los principales con nombre). Redondea a 0,01 m y ajusta a 0,05 m cuando el original lo permita.
4. **Medir y comprobar.** Calcula la superficie del contorno y de cada estancia; completa los metadatos de `Trazo_Datos`; pasa la lista de control de la convención (nueve puntos) y corrige lo que falle. `superficie_util` es la suma de las estancias que mediste en el DXF. No ajustes el dibujo para que coincida con una superficie publicada: dibuja lo que se ve y anota la diferencia en `observaciones`.
5. **Entregar.** El DXF con el nombre de la convención; **una imagen de lo que dibujaste** (SVG o PNG, con las estancias y sus etiquetas) para compararla con el original, y por cada planta una `_comparacion.png` con lo dibujado sobre el original; la fila para `indice.csv`; y una nota corta con lo estimado, lo que no encajó y lo que no pudiste leer. Nunca inventes lo que no se ve: márcalo como estimado o déjalo fuera y dilo.

Reglas:
- Un DXF por plano; en una planta entera, todas las viviendas en el mismo archivo. Si el usuario quiere además cada vivienda de esa planta como unidad suelta, genera un `U_…` por cada una, ya rotado con su pasillo abajo. Los pisos que repiten las mismas viviendas llevan su `P_` pero no `U_` aparte.
- Una vivienda en varios niveles (dúplex, tríplex): un DXF por nivel, con el sufijo `-N1`, `-N2`… y el mismo origen en todos; `tipologia` y `dormitorios` de toda la vivienda; el nivel sin puerta al palier no lleva `Trazo_Entrada` (dilo en `nivel:`).
- Solo las capas y las etiquetas de la convención. Si algo no encaja, usa lo más parecido y explícalo en `observaciones`; no inventes capas ni nombres. En los casos dudosos (un local amueblado como oficina, un nicho o antebaño sin puerta, un tabique corredizo, un vestidor abierto, una entrada no dibujada) aplica los criterios de la convención y dilo.
- Plantas enteras: `Trazo_Terreno`, `Trazo_Patios`, `Trazo_Pasillo` (también las pasarelas), `Trazo_Nucleos` (`Nucleo 1`, `Nucleo 2`), cocheras y amenities en `Trazo_Cotas`, y los rótulos de `Trazo_Fachada` (`Calle`, `Contrafrente`, `Patio`; las laterales, sin rótulo).
- Formato: DXF de texto, AutoCAD 2000 (AC1015) completo —HEADER con `$INSUNITS` = 6 y `$DWGCODEPAGE`, TABLES con las capas, ENTITIES con handles y subclases, EOF—, por ejemplo escrito con ezdxf; textos en cp1252; LWPOLYLINE (código 70 = 1 para cerrada), LINE, ARC, CIRCLE y TEXT. Nada de SPLINE, HATCH, DIMENSION ni bloques anidados. Comprueba que el archivo se lee sin errores ni reparaciones en un lector estricto (`ezdxf.recover`) y mira una vista CAD para ver que los usos se leen.
- Precisión: las medidas de un DXF o de un PDF vectorial con cotas son `alta`; de una imagen con cotas o con superficies publicadas, `media`; de una imagen sin cotas ni superficies, `baja`. Dilo en los metadatos.
- El ejemplo `tests/dxf/tipologia_2d.dxf` del repositorio de Trazo (una vivienda de 1 dormitorio de 8,00 × 7,00 m) sirve para ver las capas, las etiquetas y los datos; no lo imites en el formato del archivo, que es mínimo y los lectores estrictos lo rechazan. Después, el usuario pasa cada DXF por `tools/ver_dxf.py`, que dibuja el plano y marca los errores de la lista de control: lo que ese control rechace vuelve a ti para corregirlo.
- Derechos: de proyectos del usuario, todo; de planos publicados (revistas, portales, concursos), solo la geometría y las medidas, con la fuente anotada; no copies textos, logos ni rótulos.
- Si recibes varios planos de un mismo edificio, usa el mismo `proyecto` en todos y numera las unidades (`_01`, `_02`…; si la fuente no las numera, nómbralas por su posición en `observaciones`).
- Cuando dudes de una medida que cambia el resultado (el fondo de la vivienda, el ancho del pasillo), pregunta antes de entregar; para el resto, decide, anótalo y sigue. Si el usuario te adjunta `CRITERIOS.md`, es el registro de lo decidido en el primer lote: úsalo como precedente.

Convención Trazo: (pegar aquí la sección 1 completa de `TIPOLOGIAS.md`).

---

## 3. Qué hará Trazo con los archivos (R5.16)

- Hecho (v2.57): `tools/ver_dxf.py`, el visor y control de cada DXF (SVG + informe; ver arriba), y el ejemplo `tests/dxf/tipologia_2d.dxf`.
- Hecho (v2.57.1): `data/tipologias/` guarda el primer lote (67 DXF de seis proyectos, `indice.csv` y una nota por proyecto). `data/tipologias/CRITERIOS.md` registra las decisiones y las desviaciones de ese lote.
- Hecho (v2.58): esta convención y el visor al día con `CRITERIOS.md` (etiqueta `Dormir`, viviendas en varios niveles, ambiente abierto, `Trazo_Cotas`) y `test_base_tipologias`, que controla toda la base.
- `engine/tipologias.py` (solo biblioteca estándar, sobre `dxf_lector`): lee cada DXF, arma por vivienda `{tipologia, dormitorios, frente, fondo, area_muros, estancias: [{nombre, kind, area, rect, fachada}], entrada, puertas, ventanas, fachadas, crujia, fuente, precision}` y por planta `{terreno, patios, pasillos, nucleos, unidades}`; guarda el catálogo en `data/tipologias/catalogo.json`.
- Usos, en orden: (a) tablas de calibración contra `standards.py` (superficie de cada estancia por tipología, fondo de cocina y baño, `estar_por_dorms`, frente × fondo típicos, pasillos y viviendas por núcleo en las plantas); (b) pruebas de regresión: para cada tipología con precisión alta, el motor arma la vivienda con su frente × fondo y se compara la distribución (qué estancias, dónde cae el núcleo húmedo, la entrada) con la real; (c) catálogo: cuando el frente × fondo y la tipología de una vivienda del mix coinciden con una guardada, el motor puede usar esa distribución en lugar de calcularla (opción del usuario).
