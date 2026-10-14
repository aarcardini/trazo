# Base de tipologías — convención de los DXF y prompt para prepararlos

Para mejorar los planos del motor con planos reales: tipologías de vivienda (una unidad por archivo) y plantas enteras de vivienda colectiva (cómo se organizan las unidades, los pasillos y los núcleos). Los planos se preparan **fuera de este repositorio**, en un proyecto de Claude (o con otra herramienta) que los homogeneiza con la convención de la sección 1; después, un lector de Trazo (`engine/tipologias.py`, pendiente: R5.16 del ROADMAP) los lee desde `data/tipologias/` y arma el catálogo (frente × fondo, superficie de cada estancia, posición del núcleo húmedo, entrada, fachadas) que sirve para calibrar los típicos, para pruebas («con 6 × 7 m el motor tiene que sacar algo parecido a esta tipología») y, más adelante, para un catálogo de distribuciones.

## 1. Convención de los archivos

**Formato.** DXF **ASCII** (texto), versión AutoCAD 2000 (AC1015, con LWPOLYLINE) o R12 (con POLYLINE). Unidades: **metros**, con `$INSUNITS` = 6 en el HEADER; todo en Z = 0. Sin SPLINE, HATCH, cotas (DIMENSION), bloques anidados ni referencias externas. Coordenadas redondeadas a 0,01 m; vértices ajustados a una grilla de 0,05 m cuando el original lo permite. Sin tildes ni espacios en los nombres de capa.

**Orientación y origen.** Planos ortogonales a los ejes: se rota el dibujo para que el **pasillo común** (o la fachada principal, si no hay pasillo) quede **horizontal**. En una unidad, el origen (0, 0) es la esquina inferior izquierda de su contorno, el pasillo común está **abajo** (lado y = 0) y la fachada principal **arriba** (y = fondo). En una planta entera, el origen es la esquina inferior izquierda de la caja que contiene la planta. El norte se dibuja aparte (capa `Trazo_Norte`), no se gira el plano hacia él.

**Capas** (nombre exacto; «cerrada» = polilínea cerrada, sin autointersecciones, sin superponerse con otras de la misma capa):

| Capa | Entidades | Qué es | Etiqueta (TEXT dentro de la figura) |
|---|---|---|---|
| `Trazo_Datos` | TEXT, una línea por dato | metadatos del plano, `clave: valor` (ver abajo) | — |
| `Trazo_Norte` | una LINE | del punto base a la punta, apuntando al norte | — |
| `Trazo_Unidad` | una polilínea cerrada por vivienda | contorno de la vivienda: **eje de los muros divisorios y de los muros al pasillo común, cara exterior del muro de fachada** (la superficie «con muros» de la ANV, comparable con `area_muros` de Trazo) | `<tipología> <m²>`: `Mono 30.5`, `1D 42.0`, `2D 58.3`, `3D 78.0` (la tipología por la cantidad de dormitorios reales; `Mono` si no hay dormitorio cerrado) |
| `Trazo_Estancias` | una polilínea cerrada por local, por la cara interior de sus muros | cada estancia de la vivienda, sin solaparse | el nombre: `Hall`, `Estar`, `Comedor`, `Estar-Comedor` (un solo local), `Cocina`, `Cocina integrada` (abierta al estar), `Pasillo` (interno), `Dormitorio 1` (el principal), `Dormitorio 2`…, `Baño`, `Baño 2`, `Baño en suite`, `Toilette`, `Lavadero`, `Depósito`, `Estudio`, `Vestidor`, `Balcón`, `Terraza`, `Patio` (privado). Nada más: si un local no encaja, el más parecido y una nota en `Trazo_Datos` |
| `Trazo_Puertas` | una LINE por puerta, sobre la línea del muro, del largo de la hoja (luz libre) | puertas interiores; opcional, un ARC con el barrido | — |
| `Trazo_Entrada` | una LINE | la puerta de entrada de la vivienda (igual que las otras, en su capa) | — |
| `Trazo_Ventanas` | una LINE por ventana, sobre la cara exterior del muro, del ancho del vano | ventanas y puertas-ventana | opcional: `h <alto> a <antepecho>` (`h 1.20 a 0.90`) |
| `Trazo_Fachada` | LINE o polilínea abierta | los tramos del contorno de la vivienda que dan al exterior (fachada, patio, terraza): es lo que da luz | opcional: `Calle`, `Patio`, `Contrafrente` |
| `Trazo_Medianeras` | una LINE por tramo | tramos del contorno contra un lindero ciego (en una planta entera, los del terreno) | — |
| `Trazo_Muros` | polilíneas cerradas (opcional) | los muros cortados, con su espesor (si el original los tiene) | — |
| `Trazo_Equipamiento` | polilíneas, LINE, ARC, CIRCLE (opcional) | muebles y artefactos tal como están dibujados en el original (sirven para los símbolos) | el nombre: `Cama 1.40x1.90`, `Inodoro`, `Mesada`, `Heladera`, `Lavarropas`, `Sofa`, `Mesa 4`, `Placard` |
| `Trazo_Terreno` | una polilínea cerrada | solo en plantas enteras: el contorno de la planta (cara exterior) | — |
| `Trazo_Patios` | polilíneas cerradas | patios del edificio (dentro o al borde del terreno) | — |
| `Trazo_Pasillo` | polilíneas cerradas | solo en plantas enteras: los pasillos y palieres comunes | — |
| `Trazo_Nucleos` | una polilínea cerrada por núcleo | solo en plantas enteras: escalera + ascensores + ductos de cada núcleo | `Nucleo 1`; dentro, opcional, `Escalera`, `Ascensor`, `Ducto` en sus rectángulos |
| `Trazo_Cotas` | lo que sea (opcional) | cotas y textos del original, por si hace falta volver a mirar; el lector la ignora | — |

En una planta entera van **todas** las capas: cada vivienda con su `Trazo_Unidad` y, si el original lo permite, sus `Trazo_Estancias`, puertas y ventanas; si no hay tiempo de estanciar todas, por lo menos los contornos de las unidades, el pasillo, los núcleos, los patios y la entrada de cada vivienda.

**Metadatos** (`Trazo_Datos`, un TEXT por línea, en cualquier lugar fuera del dibujo; las claves en minúscula):

```
fuente: proyecto propio | revista | portal inmobiliario | concurso | otro (y el nombre o el enlace)
ciudad: Montevideo
proyecto: Edificio Cordón 12
autor: (estudio o desarrollador, si se sabe)
anio: 2021
tipo: unidad | planta
nivel: planta tipo (o 3, PB…)
tipologia: 2D
dormitorios: 2
superficie_util: 52.4 (m² por dentro de los muros, si la fuente la da)
superficie_muros: 58.3 (la del contorno de Trazo_Unidad, medida en el DXF)
frente: 8.00 (ancho sobre la fachada principal)
fondo: 7.25 (desde el pasillo común hasta la fachada)
crujia: doble | simple | esquina | pasante | duplex
norte: 15 (grados, antihorario desde +Y, igual que la línea de Trazo_Norte)
escala_original: 1:100 (o «sin escala: ancho de puerta 0,80 supuesto»)
precision: alta | media | baja (alta: DXF o PDF vectorial con cotas; media: imagen con cotas; baja: imagen sin cotas, medidas deducidas)
estimado: (qué se dedujo y cómo, si hay algo)
observaciones: (lo que no encaja en la convención)
```

**Nombres de archivo** (sin espacios ni tildes): unidades `U_<ciudad>_<proyecto>_<tipologia>_<frente>x<fondo>_<nn>.dxf` (`U_MVD_Cordon12_2D_8.0x7.25_01.dxf`); plantas `P_<ciudad>_<proyecto>_<nivel>.dxf` (`P_MVD_Cordon12_tipo.dxf`). Junto a los DXF, un `indice.csv` (UTF-8, separador «;», coma decimal) con una fila por archivo y las columnas: `archivo; tipo; ciudad; proyecto; anio; fuente; tipologia; dormitorios; superficie_util; superficie_muros; frente; fondo; crujia; estancias (n); precision; observaciones`.

**Control antes de entregar cada plano:**
1. Todas las polilíneas de `Trazo_Unidad`, `Trazo_Estancias`, `Trazo_Terreno`, `Trazo_Patios`, `Trazo_Pasillo` y `Trazo_Nucleos` están cerradas y no se cruzan a sí mismas.
2. Las estancias no se superponen entre sí y quedan dentro de su unidad; la suma de sus superficies más los muros interiores es parecida a la del contorno (diferencia menor del 8 %).
3. Cada estancia tiene una etiqueta de la lista, y una sola; cada unidad tiene la suya.
4. La `superficie_muros` de los metadatos coincide con el área del contorno medida en el DXF (diferencia menor del 2 %); si la fuente da otra superficie, se anota en `superficie_util` o en `observaciones`, no se corrige el dibujo para que coincida.
5. Hay una `Trazo_Entrada` por vivienda, sobre un borde que da al pasillo común (o a la calle en planta baja); las puertas y ventanas están sobre las líneas de los muros.
6. Hay `Trazo_Fachada` en todos los tramos que dan al exterior; todo dormitorio, estar y comedor toca una fachada (si no, se anota en `observaciones`).
7. El plano está rotado con el pasillo común horizontal y abajo; el norte, en `Trazo_Norte`; el origen, en la esquina inferior izquierda.
8. Unidades en metros (`$INSUNITS` = 6), Z = 0, sin SPLINE, HATCH, cotas ni bloques anidados; nombres de capa exactos.
9. Metadatos completos; lo deducido, marcado como `estimado`.

## 2. Prompt para el proyecto de Claude que prepara los planos

Copiar como instrucciones del proyecto (tal cual, incluida la convención de la sección 1, pegada al final).

---

Eres un dibujante técnico que prepara planos de vivienda para alimentar una base de datos de tipologías. Recibes planos de apartamentos y de plantas enteras de edificios de vivienda colectiva (en DXF, PDF, imágenes PNG o JPG, o descripciones con medidas) y los devuelves **homogeneizados en un DXF por plano**, siguiendo al pie de la letra la **Convención Trazo** que está al final de estas instrucciones. Trabajas en español neutro, con el usuario, que es arquitecto.

Qué hacer con cada plano que te den:
1. **Identificar la fuente y la escala.** Si el archivo es DXF, úsalo directamente. Si es PDF vectorial, extrae la geometría. Si es una imagen, busca cotas; si no hay, deduce la escala con un elemento conocido (una puerta interior de 0,70–0,80 m, un inodoro de 0,70 m de fondo, una cama de 1,40 × 1,90) y declara el supuesto en `escala_original` y `estimado`. Si te dan un DWG, pide que lo exporten a DXF ASCII (AutoCAD 2000 o R12): no puedes leerlo.
2. **Orientar.** Rota el plano para que el pasillo común quede horizontal y abajo (en una unidad) o para que el pasillo principal quede horizontal (en una planta). Lleva el origen a la esquina inferior izquierda. Dibuja el norte en `Trazo_Norte` si la fuente lo da; si no, anótalo como desconocido.
3. **Trazar.** El contorno de cada vivienda en `Trazo_Unidad` (eje de los muros divisorios y del muro al pasillo, cara exterior de la fachada); cada estancia en `Trazo_Estancias` por la cara interior de sus muros, con su etiqueta de la lista; puertas, entrada, ventanas, fachadas y medianeras en sus capas; en una planta entera, además el terreno, los patios, los pasillos comunes y los núcleos. Dibuja el equipamiento en `Trazo_Equipamiento` si el original lo tiene. Redondea a 0,01 m y ajusta a 0,05 m cuando el original lo permita.
4. **Medir y comprobar.** Calcula la superficie del contorno y de cada estancia; completa los metadatos de `Trazo_Datos`; pasa la lista de control de la convención (nueve puntos) y corrige lo que falle. No ajustes el dibujo para que coincida con una superficie publicada: dibuja lo que se ve y anota la diferencia.
5. **Entregar.** El DXF como archivo de texto, con el nombre de la convención; la fila para `indice.csv`; y una nota corta con lo estimado, lo que no encajó y lo que no pudiste leer. Nunca inventes lo que no se ve: márcalo como estimado o déjalo fuera y dilo.

Reglas:
- Un DXF por plano; en una planta entera, todas las viviendas en el mismo archivo. Si el usuario quiere además cada vivienda de esa planta como unidad suelta, genera un `U_…` por cada una, ya rotado con su pasillo abajo.
- Solo las capas y las etiquetas de la convención. Si algo no encaja, usa lo más parecido y explícalo en `observaciones`; no inventes capas ni nombres.
- Formato DXF ASCII; LWPOLYLINE (código 70 = 1 para cerrada) o POLYLINE/VERTEX/SEQEND; LINE, ARC, CIRCLE y TEXT. Nada de SPLINE, HATCH, DIMENSION ni bloques anidados. HEADER con `$INSUNITS` = 6. Escribe el archivo completo (HEADER, TABLES con las capas, ENTITIES, EOF) y revisa que los pares código/valor estén bien formados.
- Precisión: las medidas de un DXF o de un PDF vectorial con cotas son `alta`; de una imagen con cotas, `media`; de una imagen sin cotas, `baja`. Dilo en los metadatos.
- Derechos: de proyectos del usuario, todo; de planos publicados (revistas, portales, concursos), solo la geometría y las medidas, con la fuente anotada; no copies textos, logos ni rótulos.
- Si recibes varios planos de un mismo edificio, usa el mismo `proyecto` en todos y numera las unidades (`_01`, `_02`…).
- Cuando dudes de una medida que cambia el resultado (el fondo de la vivienda, el ancho del pasillo), pregunta antes de entregar; para el resto, decide, anótalo y sigue.

Convención Trazo: (pegar aquí la sección 1 completa de `TIPOLOGIAS.md`).

---

## 3. Qué hará Trazo con los archivos (R5.16, pendiente)

- `data/tipologias/` guarda los DXF y el `indice.csv`.
- `engine/tipologias.py` (solo biblioteca estándar, sobre `dxf_lector`): lee cada DXF, arma por vivienda `{tipologia, dormitorios, frente, fondo, area_muros, estancias: [{nombre, kind, area, rect, fachada}], entrada, puertas, ventanas, fachadas, crujia, fuente, precision}` y por planta `{terreno, patios, pasillos, nucleos, unidades}`; guarda el catálogo en `data/tipologias/catalogo.json`.
- Usos, en orden: (a) tablas de calibración contra `standards.py` (superficie de cada estancia por tipología, fondo de cocina y baño, `estar_por_dorms`, frente × fondo típicos, pasillos y viviendas por núcleo en las plantas); (b) pruebas de regresión: para cada tipología con precisión alta, el motor arma la vivienda con su frente × fondo y se compara la distribución (qué estancias, dónde cae el núcleo húmedo, la entrada) con la real; (c) catálogo: cuando el frente × fondo y la tipología de una vivienda del mix coinciden con una guardada, el motor puede usar esa distribución en lugar de calcularla (opción del usuario).
