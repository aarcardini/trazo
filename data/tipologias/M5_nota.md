# M5 (Punta Gorda): nota de la preparación

## Fuente

- Brochure de venta «M5», 27 págs., sin fecha. En la tapa: proyecto **MAG** y desarrollo **GiA** (solo los logos, sin más
  datos).
- Edificio en la calle Alejandro Gallinal, Punta Gorda (Montevideo), en un lote entre medianeras de unos 12,2 m de frente.
  - Dos bloques separados por un patio:
    - el del frente, sobre la calle, con viviendas en los niveles 1 a 6;
    - el del fondo, con viviendas en los niveles 1 a 3 y amenities en el 4.
  - Abajo, una PB con cocheras y el acceso, y un subsuelo con cocheras.
- **Cada ficha trae un plano clave vectorial** (CAD a 1:400) con muros, aberturas y equipamiento. La planta de la ficha
  es una imagen, pero los nombres y las medidas de los locales son texto.
  - **Escala**: 1:400 (7,087 pt por m). Se verificó con las 70 medidas de locales de las fichas:
    - razón mediana 0,996;
    - en baños, toilettes, vestidores y dormitorios, el lado corto difiere 2 cm (mediana).
  - Los nombres de las fichas se calzaron sobre el plano clave por correlación. Así se comprobó qué local es cada uno.

**Precisión alta**: es dibujo vectorial a escala conocida y comprobada.

## Qué hay

- **Plantas** (`P_`), cada una con su `_comparacion.png`:

  | Archivo | Nivel | Viviendas |
  |---|---|---|
  | `P_MVD_M5_1` | 1 | 101 a 106, con jardines y patios propios |
  | `P_MVD_M5_tipo` | 2 y 3 | 201 a 206 y 301 a 306 |
  | `P_MVD_M5_4` | 4 | 401 y 402; amenities en el bloque del fondo |
  | `P_MVD_M5_5` | 5 y 6 | 501, 502, 601 y 602; solo el bloque del frente |

- **Unidades** (`U_`): 8 tipologías.

  | Archivo | Unidades | Tipo |
  |---|---|---|
  | `_01` | 201 y 301 (y la 101) | 2D al frente, sobre la calle |
  | `_02` | 202 y 302 (y la 102) | 2D al patio entre bloques |
  | `_03` | 203 y 303 (y la 103) | 1D pasante, de la calle al patio |
  | `_04` | 204 y 304 (y la 104) | 1D del bloque del fondo |
  | `_05` | 205 y 305 (y la 105) | monoambiente del bloque del fondo |
  | `_06` | 206 y 306 (y la 106) | la 204 en espejo |
  | `_07` | 501 y 601 (y la 401) | 2D al frente, en esquina |
  | `_08` | 502 y 602 (y la 402) | 2D al contrafrente, en esquina |

- **Sin DXF**: la PB (cocheras 1 a 13, bicicletero y acceso) y el subsuelo (cocheras 14 a 29), porque no tienen viviendas.
- **Índice**: se agregaron 12 filas a `indice.csv`.

## Cómo se midió

- **Muros**: son los contornos negros del plano clave; se rellenaron.
  - Los trazos finos (vidrios, hojas de puertas, barandas) son barrera.
  - Los huecos de hasta 1,3 m a lo largo de un muro se cerraron como puertas.
- **Locales**: cada uno es el espacio libre entre muros.
  - Se separaron con los límites de zona y se llevaron a polígonos ortogonales.
  - Los cierres falsos dentro de un mismo local (el lavatorio en nicho, la ducha del toilette) se unieron al local.
- **Contornos**: los muros se repartieron entre viviendas, palier y núcleo por cercanía.
  - Quedan al eje entre ellos y por la cara exterior hacia afuera.
  - Después se recortaron en el eje de los muros de lindero (el lindero izquierdo es apenas oblicuo y quedó así).
- **Puertas**: los huecos cerrados entre dos locales de la misma vivienda.
- **Ventanas**: los tramos de fachada sin muro macizo.
- **Equipamiento**: los trazos grises del plano clave, sin los marcos de las ventanas (que son del mismo gris).
  - Los nombres (`Cama`, `Mesa 4`, `Sofa`, `Mesada`) salen del tamaño de cada mueble.
- **Áreas**: los contornos dan entre −3,6 y +0,4 % del «área interna» de las fichas, que viene redondeada al m².
  - La excepción es la 204: 42,2 m² contra 45. La 206, que es su espejo, da 42,7 contra 43.

## Criterios que conviene revisar

- **Viviendas iguales en otros niveles**: sus muros coinciden en 99 % o más, así que no llevan `U_` aparte. Cada una se
  anota en las observaciones del `U_` correspondiente.
  - Las 101 a 106 son las 201 a 206 con jardines o patios propios en lugar de terrazas.
  - Las 401 y 402 son las 501 y 502 con una terraza abierta grande sobre el lateral (donde abajo está la 203).
- **501 y 401 no son la 201**: en esos niveles el bloque ya no ocupa el lugar de la 203, y el lado izquierdo pasa a ser
  fachada con ventanas. Por eso van como tipologías aparte, en esquina.
- **Planta girada 180°**: la calle queda arriba.
  - `Trazo_Terreno` es el lote por la cara exterior de los muros de lindero, desde la línea de retiro. Las terrazas del
    frente la pasan, como balcones.
  - Lo libre del lote en cada nivel va en `Trazo_Patios`: el patio entre bloques, el fondo, y en el 5 y 6 todo lo que no
    es el bloque del frente.
- **Nivel 1**: los jardines del fondo y los patios entre bloques son de las viviendas. Van en `Trazo_Patios` y, con el
  número de la vivienda, en `Trazo_Cotas`.
- **Nivel 4**: las amenities van en `Trazo_Cotas` con su nombre: SUM/Barbacoa, Gimnasio, Lavandería, un baño, la Terraza
  de uso común y un balcón común. El palier y el núcleo del bloque del fondo van como en los otros niveles.
- **Fachadas**: van rotuladas así:
  - la de la calle, `Calle`;
  - las del patio entre bloques, `Patio`;
  - la del fondo del bloque trasero, `Contrafrente`; en el 5 y 6, también la trasera del bloque del frente;
  - las laterales, sin rótulo.
- **Orientación de las unidades**:
  - Las del frente (201, 203 y 501) van giradas 180°, con la calle arriba.
  - Las demás van como en la planta.
  - La 203, la 204 y la 206 tienen la entrada a un costado; cada archivo lo dice.
- **Paso del dormitorio principal** (201 y 501): de él salen el baño en suite y el dormitorio, sin puerta hacia este. Va
  dentro del `Dormitorio 1`.
- **205**: la ficha la vende como monoambiente pero rotula el ambiente «dormitorio».
  - Va como `Mono` con el ambiente como `Dormir`.
  - Decidido por el usuario; con `Dormir`, `ver_dxf` ya no avisa (v2.58).
- **104**: su ficha repite por error las superficies de la 401. Se anota.
- **Norte**: el símbolo apunta 56,6° a la izquierda de la vertical de la página.
  - En las plantas y en las unidades giradas, `norte: 237`.
  - En las demás, `norte: 57`.
- **Formato**: igual que en los casos anteriores. Todos pasan `ver_dxf` sin errores y `ezdxf.recover` sin arreglos.
  - Los avisos eran los de los comedores interiores y el de la 205 (desde la v2.58 el visor no los da).
