# Mauá (Près / adamo-faiden): nota de la preparación

Fuente: carpeta comercial «Mauá» de Près (pres.uy), julio de 2025, 29 págs. Las plantas son vectoriales (Illustrator),
a 1:150. La escala se verificó con los locales cerrados: miden lo que dice su etiqueta, con 1-3 cm de diferencia.
Precisión **alta**. Nada se midió a ojo.

## Qué hay

- **Plantas** (`P_`): tipo 3-8, 1, 2, 9 y 10. Cada una tiene su imagen `_comparacion.png` con lo dibujado sobre el
  original (rojo: contornos; naranja: estancias; verde: entradas; azul: ventanas; magenta: puertas).
- **Unidades** (`U_`): las 9 tipologías de la carpeta.
  - `_01` a `_04`: planta tipo (301, 302/303, 304, 305).
  - `_05` a `_08`: dúplex 101, 102/103, 104 y 105, con un archivo por nivel (`-N1`, `-N2`).
  - `_09`: tríplex 901/902/903, con un archivo por nivel (`-N1`, `-N2`).
  - Los niveles de una misma vivienda comparten el origen, así que se superponen tal cual.
- `indice.csv`: una fila por archivo.

## Locales y equipamiento

- **Espacio de estar abierto**: se separa en `Estar`, `Comedor` y `Cocina integrada`, como polígonos contiguos sin muro
  entre ellos. Los límites se trazaron según dónde están el sofá, la mesa y la mesada en la ficha de la unidad
  (`estimado` lo dice). Por eso `ver_dxf` avisaba que algunos comedores (o el estar de los tríplex) no tocan la fachada:
  son parte del mismo ambiente. Desde la v2.58 el visor no lo avisa si otro local del ambiente toca la fachada.
- **`Trazo_Equipamiento`**: lleva los muebles y artefactos de la ficha de cada unidad (1:100), calzada sobre la planta.
  - El calce se hizo correlacionando los muros, con 97-99 % de coincidencia.
  - Los muebles van en color 9 y los artefactos en color 8.
  - Los principales llevan nombre: `Cama 1.40x1.90`, `Sofa`, `Mesa 4`, `Placard`, `Escritorio`, `Mesada`, `Heladera`,
    `Lavarropas`.
- **Colores**: cada estancia tiene un color según su tipo, dentro de la capa `Trazo_Estancias`:
  - dormitorios: azul;
  - estar: amarillo;
  - comedor y cocina: naranja;
  - baños: cian;
  - circulación: gris;
  - lavadero: magenta.
- **102/103**: el local de abajo la ficha lo amuebla con escritorio, así que es `Estudio` y la vivienda es **2D**. La
  carpeta la vende como «3/4 dormitorios». En la 101, ese local tiene cama y es `Dormitorio 3`.

## Criterios que conviene revisar

- **Balcones, terrazas y patios propios** van en `Trazo_Cotas`, fuera de los contornos. El contorno se mide por la
  cara exterior de la fachada, y `ver_dxf` da error si una estancia queda fuera de su vivienda. Sus medidas están en
  `observaciones`.
- **Escaleras interiores**: se etiquetaron `Pasillo`, porque la lista de etiquetas no tiene «Escalera».
- **Niveles superiores** (`-N2`): no tienen `Trazo_Entrada`, así que `ver_dxf` daba el error «no tiene entrada». También
  avisaba que la etiqueta (la tipología de toda la vivienda, por ejemplo `3D`) no coincidía con los dormitorios de ese
  nivel. Desde la v2.58 el visor lee el sufijo `-N` y no da ninguno de los dos.
- **Piso 11**: es la azotea de los tríplex. Son terrazas descubiertas con la llegada de la escalera y no tienen
  superficie cerrada, así que no llevan DXF (está anotado en `_09`).
- **PB y subsuelo**: no tienen viviendas (hall, cowork y cocheras). No se dibujaron.
- **Norte**: la carpeta no lo trae («desconocido»).
- **Orientación**: la fachada principal va siempre arriba. En 301, 304 y 305 la entrada no puede quedar abajo; cada
  archivo lo explica.
- **Áreas**: los contornos quedan cerca del «área interior» APPCU de la carpeta:
  - planta tipo: entre −0,5 y −4 %;
  - dúplex: 101 −3 %, 102/103 +3 %;
  - tríplex 901-903: −1 %.

  Las excepciones son la 104 (+10 %) y la 105 (+14 %). La diferencia viene probablemente de que la carpeta no cuenta el
  hueco de la escalera en el piso de arriba.
- **Sin dibujar**:
  - Las zonas rayadas junto a los toilettes de 102 y 103 y junto al lavadero de 104, en el piso 1 (no se sabe qué son).
  - Los placards bajo los baños de 302 y 303.
  - Los volúmenes técnicos de la azotea del núcleo, en el piso 10.
- **Formato**: los DXF son AutoCAD 2000 completos (handles y subclases), escritos con ezdxf y con los textos en cp1252,
  como declara el encabezado. `ver_dxf` los lee porque, si el archivo no es UTF-8, prueba cp1252.
