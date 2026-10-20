# GR 1591 (Près+ / Adamo-Faiden con Plan Común): nota de la preparación

## Fuente

- Dossier comercial «GR 1591» de Près+ (pres.uy): archivo del 5 de febrero de 2026, 22 págs. (la primera versión es de
  noviembre de 2024). No da la dirección.
- Dos volúmenes de 5 pisos (norte y sur) en un lote de 10,94 × 31,21 m, separados por un patio central con pasarelas.
- **Las plantas y las fichas no son vectoriales**: son imágenes JPEG de 1240 × 1755 px por página.
  - Debajo de las plantas visibles hay imágenes de más resolución de una versión anterior, con otros baños y otros
    muebles. No se usaron.
- Escala: la escala gráfica de las plantas (0-1-2-5 m) da 44,30 px/m, o sea 2,26 cm por px (unos 1:182 en la página).
  Las fichas están al doble. Se verificó con las cotas de las fichas:

  | Cota de la ficha | Medida en la planta |
  |---|---|
  | ancho de las unidades 3,37 | 3,36 a 3,37 |
  | ambiente único 7,10 | 7,09 |
  | baño 2,29 × 1,72 | 2,28 × 1,68 |
  | baño 2,30 × 1,96 | 2,28 × 1,94 |
  | patio 3,85 × 3,37 | 3,82 × 3,37 |

**Precisión media** (imagen con cotas).

## Qué hay

- **Plantas** (`P_`): planta tipo (pisos 2 a 4) y piso 1. Cada una tiene su `_comparacion.png` con lo dibujado sobre la
  imagen original:
  - rojo: contornos;
  - naranja: estancias;
  - verde: entradas;
  - azul: ventanas;
  - magenta: puertas;
  - celeste: balcones;
  - verde claro: patios;
  - gris: pasarelas y núcleo;
  - violeta y marrón: muebles y artefactos.
- **Unidades** (`U_`), una por tipo:
  - `_01`: norte clásica, 1D (norte izquierda y norte medio de cada piso).
  - `_02`: norte junto al núcleo, un solo ambiente: `Mono` (ver abajo).
  - `_03`: sur clásica, 1D (sur izquierda y sur medio).
  - `_04`: sur junto al núcleo, 1D invertida: el dormitorio da a la pasarela. La carpeta no trae ficha de esta unidad.
- **Sin DXF**, porque no tienen viviendas: la PB (hall, cocheras, bicicletero y sala de estudio) y la azotea (pabellón
  multiuso al norte y jardín con parrilleros al sur).
- **Índice**: se agregaron 6 filas a `indice.csv`.

## Cómo se midió (imagen)

- **Muros**: perfiles de grises promediados a lo largo de cada muro, con las caras interpoladas entre píxeles. El error
  es de 1 a 2 cm.
- **Muros largos**: no son exactamente paralelos (de 0,14° a 0,27°): el lote se angosta unos 6 cm hacia el fondo. Se
  dibujaron así, sin enderezarlos. Las líneas horizontales sí son exactas.
- **Fichas**: se calzaron sobre las plantas por correlación de los muros (coincidencia del 92 al 100 %).
- **Equipamiento**: vectorizado de la imagen, así que los trazos son aproximados (unos 2 cm).
  - Muebles: el trazo celeste, reducido a su eje.
  - Artefactos: el trazo negro de baños y cocinas de las fichas, sin la grilla de azulejos ni los rótulos.
- **Coincidencia con la carpeta**:

  | | Dibujo | Carpeta |
  |---|---|---|
  | contornos | 35,0 a 35,1 m² | área interior 35,41 a 35,42 (−0,9 a −1,2 %) |
  | balcón | 0,84 × 3,58 = 3,01 m² | 3,01 |
  | patio del piso 1 | 12,82 m² | 13,00 |
  | pasarela frente a cada unidad | 4,30 m² | 4,48 de áreas comunes |

- **Norte**: 12° a la derecha de la vertical de la página:
  - 168° en las plantas (giradas 180°, con la calle arriba), en la 03 y en la 04;
  - 348° en la 01 y en la 02.

## Locales y equipamiento

- **Usos**: se siguieron los criterios de los casos anteriores. Estar, comedor y cocina se separan según los muebles, y
  cada local lleva el color de su tipo.
- **Plantas**:
  - Los muebles son los de la propia planta. Cambian de una unidad a otra, aun en el mismo tipo, y por eso los cortes
    entre estar, comedor y cocina también cambian.
  - Los artefactos son los de las fichas, porque son fijos. En la sur junto al núcleo van los de la ficha sur, en
    espejo: coinciden con la planta.
- **Unidades**: muebles y artefactos de la ficha. En la 04, los muebles son los de la planta tipo.
- **Rótulos**: `Cama`, `Mesa 4`, `Sofa`, `Placard`, `Escritorio`, `Mesada`, `Inodoro`, `Lavarropas`.

## Criterios que conviene revisar

- **02 como `Mono`**: es un solo ambiente de 7,10 × 3,37 con la cama a la vista. La carpeta la vende como «dos
  ambientes / un dormitorio».
  - Se siguió el mismo criterio que la 001 de Isla de Flores, todavía sin confirmar: `Mono` con la zona de la cama como
    `Dormitorio 1`.
  - Por eso `ver_dxf` avisa.
- **Entrada de las clásicas (01 y 03)**: la puerta no está dibujada. El frente a la pasarela es todo vidriado, en dos
  paños.
  - Se tomó como entrada el paño que las fichas marcan con una flecha de corrediza (el de la derecha en la página).
  - El otro paño va como ventana.
- **04**: la pasarela toca solo la parte izquierda del frente vidriado; el resto da a un vacío.
  - La entrada se supuso ahí, y cae en el dormitorio, como lo muestra la planta.
  - Del dormitorio se pasa al pasillo junto al baño.
- **Piso 1**: no lleva `U_` aparte. Sus viviendas son las de la planta tipo (los muros coinciden píxel a píxel).
  - Las del edificio norte tienen patios propios de 3,82 × 3,37 al fondo del lote en lugar de balcón: van en
    `Trazo_Patios` de la planta y se nombran en las observaciones de la 01 y la 02.
  - La carpeta numera las unidades 10 a 15 pero no dice cuál es cuál: los archivos las nombran por su posición.
- **Contorno**: va por la cara exterior de los dos frentes vidriados, porque los dos son fachada (también el que da a la
  pasarela abierta). Así coincide con el área APPCU.
- **Pasarelas y patio**:
  - Las pasarelas al aire libre son el `Trazo_Pasillo`.
  - En `Trazo_Patios` van:
    - el vacío del patio central;
    - el vacío junto al ascensor;
    - en la planta tipo, lo libre al fondo del lote, sobre los patios del piso 1;
    - en el piso 1, el jardín.
- **Formato**: igual que en los casos anteriores. Todos pasan `ver_dxf` sin errores y `ezdxf.recover` sin arreglos. Los
  únicos avisos son los del estar y el comedor interiores y el de la Mono.
