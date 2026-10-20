# Barrios Amorín (Près / adamo-faiden): nota de la preparación

## Fuente

- Carpeta comercial «Barrios Amorín» de Près (pres.uy), 29 de julio de 2025, 26 págs.
- Edificio en Barrios Amorín 1168, Palermo, Montevideo. Lote irregular de 237 m²: el lindero de arriba en la página es
  oblicuo (9,1°) y hay una franja al fondo.
- Plantas vectoriales a 1:150 y fichas a 1:125. Las dos escalas se verificaron con la escala gráfica y con los locales.

**Precisión alta**: nada se midió a ojo.

## Qué hay

- **Plantas** (`P_`): planta tipo (pisos 2 a 9) y primer piso. Cada una tiene su `_comparacion.png` con lo dibujado
  sobre el original:
  - rojo: contornos;
  - naranja: estancias;
  - verde: entradas;
  - azul: ventanas;
  - magenta: puertas;
  - celeste: balcones, patios y terraza;
  - verde claro: patio del lote.
- **Unidades** (`U_`):
  - `_01`: 201 (1D al frente; igual del 201 al 901).
  - `_02`: 202 (2D al contrafrente; igual del 202 al 902).
  - `_03`: 203 (1D pasante; igual del 203 al 903).
  - `_04`: 101 (al frente, en toda la profundidad).
  - `_05`: 102 (3D con patios y terraza).
- **Sin DXF**, porque no tienen viviendas: la PB (hall, cocheras y bicicletero), el subsuelo (cocheras) y el piso 10
  (azotea común con parrillero).
- **Índice**: se agregaron 7 filas a `indice.csv`.

## Cómo se midió (forma compleja)

- **Locales**: los muros oblicuos impiden medir con rectángulos, así que cada local es el relleno del espacio libre entre
  muros del PDF.
  - Los rellenos se cortaron con las puertas, los vidrios y los límites entre zonas.
  - Después se limpiaron (sin las muescas de lámparas, marcos y artefactos) y se ajustaron lado por lado a la cara del
    muro.
  - Los muros oblicuos quedan oblicuos.
- **Contornos**:
  - eje de los muros entre viviendas, con el palier y con el núcleo;
  - cara exterior de las fachadas;
  - eje del muro del lindero.
- **Coincidencia con la carpeta**: los contornos quedan entre 1,4 y 2,4 % por debajo del «área interior», en las 5
  unidades. Los balcones, patios y terraza quedan dentro de un 5 % de las superficies semicubiertas y descubiertas de la carpeta,
  salvo los balcones de la 202 (+16 %).
- **Norte**: la carpeta trae el símbolo, 5° a la derecha de la vertical de la página. Va en `Trazo_Norte` y en
  `norte:`:
  - 265° en las plantas, la 201, la 203 y la 101, que están giradas con la calle arriba;
  - 175° en la 202 y la 102, giradas 180°.

## Locales y equipamiento

- **Usos**: se siguieron los criterios del Mauá:
  - estar, comedor y cocina separados según los muebles;
  - colores por tipo de local;
  - el equipamiento de la ficha calzado sobre la planta (86-98 % de coincidencia), con los nombres de los muebles
    principales.

## Criterios que conviene revisar

- **101 como 1D**: la carpeta la amuebla como oficina: mesa de reuniones, escritorio doble y, en el local cerrado,
  escritorio y sillones.
  - Por el criterio del Mauá, ese local sería `Estudio` y la vivienda quedaría `Mono`.
  - Lo dejé `Dormitorio 1` porque es el único local cerrado, la carpeta la vende como «1 dormitorio» y en los pisos de
    arriba el mismo lugar tiene cama.
  - El estar, sin sofá, va como `Estar-Comedor`.
- **Tabiques corredizos** (201 y 101, entre el estar y el dormitorio): tienen dos hojas a los lados de un paño fijo y se
  dibujaron como dos puertas.
- **102**:
  - La suite tiene un vestidor (`Vestidor`) sin muro hacia el dormitorio.
  - El lavarropas está dentro del baño 2.
  - Los dos patios sobre la PB y la terraza del fondo van en `Trazo_Cotas`.
  - El cuadrado con cruz del patio es el vacío sobre la rampa de la PB: va en `Trazo_Patios` de la planta.
- **Planta tipo**: lo libre del lote a esa altura (el fondo, sobre los patios del piso 1) va en `Trazo_Patios`.
- **Lote**: el `Trazo_Terreno` va por las caras exteriores de los muros de lindero y da 242 m². La carpeta dice 237 m².
- **Orientación**: la fachada principal va arriba.
  - 201, 101 y 203: la calle arriba.
  - 202: el contrafrente arriba.
  - 102: los patios arriba.
  - En la 201 y la 101 la entrada queda abajo. En las demás queda a un costado, y cada archivo lo dice.
- **Formato**: igual que en los casos anteriores. Todos pasan `ver_dxf` sin errores y `ezdxf.recover` sin arreglos. Los
  únicos avisos son el del comedor interior de la 203.
