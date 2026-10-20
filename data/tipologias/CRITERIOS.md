# Base de tipologías: criterios y desviaciones de todos los casos

Reúne en un solo lugar lo que se decidió al preparar los planos y todo lo que se apartó de la Convención Trazo
(`TIPOLOGIAS.md`) o de la fuente, en los seis casos procesados hasta ahora. Sale de `claude/criterios_aplicados.md` y de
las notas de cada caso (`data/tipologias/*_nota.md`).

Lo marcado **[usuario]** lo decidió o lo pidió el usuario. Lo marcado **[pendiente]** está sin confirmar. El resto lo
decidió Claude y el usuario no lo objetó.

## Los casos

| Caso | Fuente | Plantas | Escala | Precisión | Archivos |
|---|---|---|---|---|---|
| Mauá | carpeta comercial de Près, julio de 2025 | vectoriales (Illustrator) | 1:150; fichas 1:100 | alta | 5 `P_`, 9 tipologías (con dúplex y tríplex por nivel) |
| Isla de Flores | dossier de Près, ©2023 | vectoriales | 1:125; fichas 1:75 | alta | 3 `P_`, 5 `U_` |
| Barrios Amorín | carpeta comercial de Près, 29/7/2025 | vectoriales; lote irregular, muros oblicuos | 1:150; fichas 1:125 | alta | 2 `P_`, 5 `U_` |
| GR 1591 | dossier de Près+, 5/2/2026 | imágenes JPEG | escala gráfica (unos 1:182), verificada con cotas | media | 2 `P_`, 4 `U_` |
| Aruma | brochure de GROU, diciembre de 2025 | imágenes, sin escala ni cotas | deducida de las áreas publicadas | media | 2 `P_`, 13 `U_` |
| M5 | brochure de MAG y GiA, sin fecha | plano clave vectorial; fichas en imagen | 1:400, verificada con las medidas de las fichas | alta | 4 `P_`, 8 `U_` |

## 1. Criterios aplicados

### Viviendas y locales

- **Viviendas en varios niveles [usuario]**: un DXF por nivel, con el mismo número de unidad y el sufijo `-N1`, `-N2`,
  `-N3` (por ejemplo `U_MVD_Maua_3D_5.79x9.43_05-N1.dxf`).
  - Todos los niveles usan el mismo origen (la caja de todos los niveles), así que se superponen tal cual.
  - `tipologia` y `dormitorios` son los de toda la vivienda.
  - `superficie_muros` es la del nivel; la total va entre paréntesis.
- **Que se lean los usos [usuario]**: en Rhino tienen que distinguirse la cocina, el comedor, el estar y los
  dormitorios. Para eso:
  - El espacio de estar abierto se separa en `Estar`, `Comedor` y `Cocina integrada`, como polígonos contiguos sin muro
    entre ellos.
    - Los límites siguen el amueblamiento: la cocina es la mesada más la zona de trabajo, el comedor es la mesa con sus
      sillas y el estar es el sofá.
    - Si no hay sofá ni una mesa de comedor clara, el ambiente va entero como `Estar-Comedor`.
    - Se anota en `estimado`.
  - Cada estancia lleva un color según su tipo (color por entidad, dentro de `Trazo_Estancias`):

    | Estancia | Color |
    |---|---|
    | Dormitorio | 5 |
    | Estudio | 150 |
    | Estar y Estar-Comedor | 2 |
    | Comedor | 40 |
    | Cocina | 30 |
    | Baño y Toilette | 4 |
    | Hall y Pasillo | 8 |
    | Lavadero, Depósito y Vestidor | 6 |

  - En los locales angostos, el nombre va girado 90° a lo largo del local.
- **Equipamiento** (`Trazo_Equipamiento`): muebles en color 9 y artefactos en color 8.
  - En las fuentes vectoriales con fichas, sale de la ficha, calzada sobre la planta por correlación de los muros (giro,
    simetría y traslación). Se descartan los contornos de muros, los vidrios, los marcos de puertas y los pilares de
    fachada que trae la ficha.
  - Los muebles principales llevan nombre: `Cama AxB`, `Sofa`, `Mesa N`, `Placard`, `Escritorio`, `Mesada`,
    `Heladera`, `Lavarropas`, `Inodoro`.
  - **Varias unidades del mismo tipo con muebles distintos** (GR 1591):
    - En la planta, cada unidad lleva los muebles que la planta le dibuja, y sus zonas se cortan según esos muebles.
    - Los artefactos, que son fijos, salen de la ficha del tipo; en espejo si la unidad es el espejo del tipo.
    - En el `U_` del tipo, muebles, artefactos y zonas salen de la ficha.
- **Nombre del local según su amueblamiento**: un local cerrado amueblado con escritorio es `Estudio`, no dormitorio, y
  la tipología cuenta solo los `Dormitorio`. Si la fuente anuncia otra cosa, se anota en `observaciones`.
- **Único local cerrado amueblado como oficina [pendiente]**: queda `Dormitorio 1`, no `Estudio`, para que la vivienda
  no pase a `Mono` con un cuarto cerrado. El amueblamiento se anota en `observaciones` (la 101 de Barrios Amorín).
- **Monoambiente con zona de dormir [pendiente]**: tipología `Mono` y `dormitorios: 0`, como pide la convención, con la
  zona de dormir etiquetada `Dormitorio 1` para que se lea.
  - Casos: la 001 de Isla de Flores y la 02 de GR 1591, que las fuentes venden como «1 dormitorio»; la 205 de M5, que se
    vende como monoambiente pero la ficha rotula el ambiente «dormitorio».
- **Tabique corredizo entre estar y dormitorio**: cuenta como cerramiento. Cada hoja que abre va como una puerta.
- **Vestidor sin muro hacia el dormitorio**: va como `Vestidor`, separado del dormitorio por una línea de zona.
- **Escaleras interiores**: van como `Pasillo`.
- **Nicho o antebaño sin puerta propia**: va con el local al que abre.
  - El nicho de la heladera junto a la entrada, con el `Hall`.
  - El antebaño, con el `Baño`.
  - El pasillo de los dormitorios sin puerta hacia el hall, con el `Hall`.
  - El paso del dormitorio principal al baño en suite, abierto al dormitorio, con el `Dormitorio 1`.
- **Entrada no dibujada** (frente vidriado sin puerta): la entrada es el paño corredizo que marca la ficha y los otros
  paños van como ventana. Se anota en `estimado`.

### Exteriores, contornos y orientación

- **Contornos**: eje de los muros entre viviendas y hacia el palier y el núcleo; cara exterior de las fachadas; eje de
  los muros de lindero. Si el lindero es oblicuo, se dibuja oblicuo, sin enderezarlo.
- **Balcones, terrazas y patios propios**: van en `Trazo_Cotas` (polilínea con su texto), fuera de `Trazo_Unidad`.
  - Sus medidas, y las de la fuente si difieren, van en `observaciones`.
  - Si el patio propio es además el patio del edificio (un jardín en PB o el fondo del lote en el piso 1), en la planta
    va en `Trazo_Patios` y en el `U_`, en `Trazo_Cotas`.
- **Pasarelas al aire libre**: son el `Trazo_Pasillo`. El vacío del patio y los otros vacíos van en `Trazo_Patios`. El
  frente de la vivienda hacia la pasarela es fachada.
- **`Trazo_Terreno`**:
  - En general, el contorno exterior del edificio: incluye los patios contra los linderos y deja afuera los retiros
    abiertos a la calle y los balcones.
  - Si el edificio no llena el lote en todos los pisos (Barrios Amorín, GR 1591, M5): el lote por la cara exterior de
    los muros de lindero, desde la línea de retiro. Lo libre del lote en cada planta va en `Trazo_Patios`, también donde
    un bloque ya terminó.
  - Edificio exento (Aruma): el contorno de la losa con las terrazas, y sin `Trazo_Medianeras`.
- **Dos bloques en un lote** (M5): cada uno con su palier y su núcleo (`Nucleo 1`, `Nucleo 2`).
- **Núcleo partido por el palier**: dos polígonos en `Trazo_Nucleos`; `Nucleo 1` se rotula una sola vez.
- **Planta baja con cocheras**: cada cochera en `Trazo_Cotas` con su nombre. El hall, el pasillo a las cocheras y el
  lobby, en `Trazo_Pasillo`.
- **Amenities en un nivel con viviendas**: en `Trazo_Cotas`, cada local con su nombre y su superficie.
- **Orientación de las unidades**: la fachada principal arriba. Si el pasillo no puede quedar abajo, se explica en
  `observaciones`.
- **Orientación de las plantas**: igual, con la fachada principal arriba (calle a la izquierda de la página: giro
  horario; abajo: 180°).
  - Un palier corto puede quedar vertical; se anota.
  - Un palier en anillo no puede quedar horizontal: si la calle ya está arriba, la planta no se gira.
- **Rótulos de `Trazo_Fachada`**: `Calle` el frente, `Contrafrente` el opuesto, `Patio` los patios (también el patio
  entre dos bloques y el frente a una pasarela) y sin rótulo las laterales.
- **Norte**: si la fuente trae el símbolo, va una línea en `Trazo_Norte` y el ángulo en `norte:`, calculado para el giro
  de cada archivo. Si no lo trae, «desconocido».
- **Unidades sin número en la fuente**: se nombran por su posición (por ejemplo, «norte izquierda»).
- **Niveles sin DXF**: los que no tienen superficie cerrada de vivienda (azoteas descubiertas o comunes), la PB y el
  subsuelo sin viviendas. Se anotan en `observaciones` de los otros niveles.

### Medición, según el tipo de fuente

- **Vectorial con muros ortogonales**: los locales se ajustan como rectángulos a las caras de los muros; los contornos,
  a los ejes y caras medidos en el PDF. Precisión `alta`.
- **Vectorial con muros oblicuos** (Barrios Amorín):
  - Cada local es el relleno del espacio libre entre muros, cortado con las puertas, los vidrios y los límites de zona,
    y limpio de las muescas de lámparas, marcos y artefactos.
  - Después se ajusta lado por lado a la cara del muro; los oblicuos quedan oblicuos.
- **Imagen con escala gráfica y cotas** (GR 1591): precisión `media`.
  - Se usa la imagen visible, no la versión anterior escondida debajo.
  - La escala sale de la escala gráfica y se verifica con las cotas de las fichas.
  - Cada muro se mide con perfiles de grises promediados, con las caras interpoladas (1 a 2 cm). Los muros largos que
    no son exactamente paralelos se dibujan así.
  - Coordenadas redondeadas a 1 cm.
  - Equipamiento vectorizado de la imagen (trazos aproximados, se dice en `estimado`).
- **Imagen sin escala ni cotas** (Aruma): precisión `media`.
  - La escala sale de las superficies publicadas (la que hace coincidir la suma de los contornos con la suma de las
    áreas). Se controla con el ancho de las puertas interiores y las camas. Cada página puede llevar su escala.
  - Como las áreas se usaron para la escala, su coincidencia no es un control independiente; se dice en `estimado`.
  - Los locales son rellenos entre muros con las puertas cerradas automáticamente; un recorrido desde la entrada
    comprueba que se llega a todos.
  - Las ventanas son los tramos de fachada sin muro macizo.
  - Los nombres de los muebles salen del tamaño de cada grupo de trazos (medidas nominales); si no es claro, no llevan
    nombre.
- **Plano clave vectorial con fichas en imagen** (M5): precisión `alta`.
  - Muros, aberturas y equipamiento salen de los vectores; la escala del dibujo se verifica con las medidas de las
    fichas (en M5 estaban en una fuente cifrada y se decodificaron leyendo unas pocas en la imagen).
  - Los locales son el espacio libre entre muros; los cierres falsos dentro de un local (un lavatorio en nicho, una
    ducha) se unen a ese local.
  - Los muros se reparten por cercanía entre viviendas, palier y núcleo, y los contornos se recortan en el eje de los
    linderos.
  - El equipamiento excluye los marcos de las ventanas cuando son del mismo color que los muebles.

### Pisos que se repiten y superficies

- **Pisos con las mismas viviendas** (sin balcones, o con patios propios en lugar de balcones):
  - Llevan su `P_` propio.
  - Sus viviendas no llevan `U_` aparte; se anotan en las observaciones del `U_` que se repite.
  - Si el dibujo está corrido unos centímetros pero los muros coinciden (99 % o más), se usan las medidas de la planta
    tipo y se dice en `estimado`.
  - Vale también para viviendas sueltas de niveles con otra planta. El `U_` sale del nivel que más se repite.
  - Si cambia una fachada (un lado contra otra vivienda pasa a tener ventanas), es otra tipología.
- **Superficies de la fuente** (por ejemplo, el «área interior» APPCU): van en `observaciones`. `superficie_util` es
  la suma de las estancias medida en el DXF, y se dice así.
- **Pisos a los que no se entra** (niveles superiores de dúplex): sin `Trazo_Pasillo`. Si la franja del pasillo es
  vacío, las ventanas hacia él llevan `Trazo_Fachada` «Patio».

### Formato y verificación

- **Formato**: DXF AutoCAD 2000 completo, escrito con ezdxf (handles y subclases), con los textos en cp1252 como declara
  `$DWGCODEPAGE`. El formato mínimo del ejemplo `tests/dxf/tipologia_2d.dxf` lo rechazan los lectores estrictos.
- **Verificación** de cada caso:
  - `ver_dxf` sobre cada archivo, en el contenedor y otra vez en la carpeta del usuario;
  - una `_comparacion.png` por planta, con lo dibujado sobre el original;
  - todos los archivos por `ezdxf.recover` sin errores;
  - una vista CAD para comprobar que los usos se leen.

## 2. Desviaciones de la convención

Lo que no sigue `TIPOLOGIAS.md` al pie de la letra, y por qué.

| Desviación | Dónde | Motivo |
|---|---|---|
| Balcones, terrazas y patios propios fuera del contorno, en `Trazo_Cotas`, aunque `Balcón`, `Terraza` y `Patio` están en la lista de estancias | todos los casos | el contorno va por la cara exterior de la fachada, y `ver_dxf` da error si una estancia queda fuera de su vivienda |
| Escaleras interiores como `Pasillo` | dúplex y tríplex del Mauá | la lista de estancias no tiene «Escalera» |
| `Mono` con un local `Dormitorio 1` | Isla de Flores 001, GR 1591 02, M5 205 | la convención pide `Mono` si no hay dormitorio cerrado; el rótulo es para que se lea en Rhino **[pendiente]** |
| `Dormitorio 1` en un local amueblado como oficina | Barrios Amorín 101 | es el único local cerrado y la fuente la vende como «1 dormitorio» **[pendiente]** |
| `Estudio` donde la fuente anuncia un dormitorio | Mauá 102/103 (2D; la carpeta dice «3/4 dormitorios») | el local está amueblado con escritorio |
| Niveles superiores sin `Trazo_Entrada` | Mauá, `-N2` de los dúplex y el tríplex | no tienen puerta al palier |
| Pasillo común que no queda abajo en la unidad (entrada a un costado o arriba) | Mauá 301, 304, 305; Isla de Flores 201, 204, 001; Barrios Amorín 202, 203, 102; Aruma, las de esquina; M5 203, 204, 206 | la fachada principal manda arriba; cada archivo lo explica |
| Palier que no queda horizontal en la planta | Isla de Flores (palier corto, vertical); Aruma (palier en anillo, planta sin girar) | no hay pasillo largo que alinear |
| Núcleo en dos polígonos | Isla de Flores | el palier lo parte |
| `Trazo_Terreno` = el lote y no el contorno del edificio | Barrios Amorín, GR 1591, M5 | el edificio no llena el lote en todos los pisos |
| `Trazo_Terreno` = losa con terrazas, sin medianeras | Aruma | edificio exento |
| Cocheras y amenities en `Trazo_Cotas` | Isla de Flores (PB), M5 (nivel 4) | la convención no tiene capa para ellas |
| Viviendas sin `U_` propio (iguales a otra) | Isla de Flores piso 1; GR 1591 piso 1; M5 101 a 106 y 401, 402 | muros iguales al 99 % o más; solo cambian los exteriores |
| Unidades nombradas por su posición | GR 1591 | la carpeta numera 10 a 15 pero no dice cuál es cuál |
| `norte: desconocido` | Mauá, Isla de Flores | la fuente no trae el símbolo |
| `anio` sin dato y autores por los logos | M5 | el brochure no tiene fecha ni créditos escritos |
| `MVD` en el nombre de archivo | Aruma | los Lagos de Carrasco quedan, hasta donde sé, en Canelones; los datos dicen «área metropolitana» |
| Precisión `media` | GR 1591, Aruma | plantas en imagen |

### Avisos y errores de `ver_dxf` aceptados

- **«no toca ninguna fachada»** del comedor (o del estar) interior, que es parte del mismo ambiente:
  - Mauá: algunos comedores y el estar de los tríplex;
  - Barrios Amorín: 203;
  - GR 1591: estar y comedor interiores;
  - Aruma: 106, 103, 102, 107 y 504;
  - M5: 201, 202 y 203 (y sus plantas).
- **«etiquetada Mono y tiene 1 dormitorio»**: Isla de Flores 001, GR 1591 02, M5 205.
- **Error «no tiene entrada»** y aviso de tipología distinta de los dormitorios del nivel: los `-N2` del Mauá.

## 3. Diferencias con la fuente, caso por caso

### Mauá

- **Áreas** (contorno frente al «área interior» APPCU):
  - planta tipo: entre −0,5 y −4 %;
  - dúplex: 101 −3 %, 102/103 +3 %, 104 **+10 %**, 105 **+14 %** (probablemente la carpeta no cuenta el hueco de la
    escalera en el piso de arriba);
  - tríplex 901-903: −1 %.
- **Sin dibujar**: las zonas rayadas junto a los toilettes de 102 y 103 y junto al lavadero de 104 (no se sabe qué son),
  los placards bajo los baños de 302 y 303 y los volúmenes técnicos de la azotea, en el piso 10.
- **Sin DXF**: el piso 11 (azotea de los tríplex, terrazas descubiertas), la PB y el subsuelo.

### Isla de Flores

- **Áreas**: 201 −3,7 %, 202 −1,9 %, 203 +4,3 %, 204 −1,1 %, 001 −6,2 %.
- **Balcones**: algunos no coinciden con la carpeta; el de la 203 mide 1,00 × 7,35 y la carpeta dice 1,00 × 6,80.
- **Dibujos corridos**: el piso 1 está corrido 3 cm (con eso corregido, el 99,7 % de los muros coincide y se usaron las
  medidas de la planta tipo); la PB, unos 6 cm, y se midió aparte.
- **Estimado**: la puerta del dormitorio 2 de la 201, que es un tabique corredizo; el paso se dibujó al medio.
- **Sin identificar**: un local con una cruz junto al lobby de la PB.
- **Sin DXF**: la azotea (terraza común y áreas asignadas a 101-104).

### Barrios Amorín

- **Áreas**: los contornos dan entre 1,4 y 2,4 % menos que el «área interior».
- **Exteriores**: dentro de un 5 % de las superficies de la carpeta, salvo los balcones de la 202 (+16 %).
- **Lote**: dibujado da 242 m²; la carpeta dice 237.
- **101**: amueblada como oficina en la carpeta (ver la tabla de desviaciones).
- **Sin DXF**: la PB, el subsuelo y el piso 10 (azotea común con parrillero).

### GR 1591

- **Fuente**: bajo las plantas visibles hay imágenes de una versión anterior, con otros baños y muebles; no se usaron.
  La carpeta no da la dirección.
- **Escala**: verificada con cinco cotas de las fichas, con 0 a 4 cm de diferencia.
- **Áreas**: contornos de 35,0 a 35,1 m² contra 35,41-35,42 (−0,9 a −1,2 %); patio del piso 1, 12,82 contra 13,00;
  pasarela frente a cada unidad, 4,30 contra 4,48 de áreas comunes; el balcón coincide (3,01).
- **Muros largos**: no son exactamente paralelos (0,14° a 0,27°; el lote se angosta unos 6 cm hacia el fondo).
- **Entradas supuestas**: en 01 y 03 la puerta no está dibujada (se tomó el paño con flecha de corrediza); en la 04, que
  no tiene ficha, se supuso donde la pasarela toca el frente, y cae en el dormitorio.
- **Sin DXF**: la PB y la azotea (pabellón multiuso y jardín con parrilleros).

### Aruma

- **Escala**: de las áreas propias: 25,47 pt por m en los pisos 1 a 4 y 25,81 en el piso 5 (esa planta está dibujada un
  1,3 % más grande). Las puertas interiores dan 0,80 m de mediana (0,77 a 0,85).
- **Áreas**: entre −0,5 y +0,4 % en los pisos 1 a 4, y entre −1,3 y +0,8 % en el piso 5; no es un control independiente.
- **503**: la carpeta no da su área propia, solo el total (130,21 m²). Su contorno da 93,0; la 505, su espejo, 94,22 en
  la carpeta.
- **Trazado a mano**: los contornos, el palier, el núcleo y los patios, con las medidas de la imagen. También tres
  puertas de la 502 y una de la 501, junto a esquinas.
- **Equipamiento**: vectorizado de la imagen; trazos aproximados.
- **Sin DXF**: la PB (hall, cocheras 24 a 40 y laundry) y el subsuelo (cocheras 1 a 23).

### M5

- **Escala**: 1:400 verificada con 70 medidas de las fichas (razón mediana 0,996; en baños, toilettes, vestidores y
  dormitorios, 2 cm de diferencia mediana en el lado corto).
- **Áreas**: entre −3,6 y +0,4 % del «área interna», que viene redondeada al m²; la excepción es la 204, 42,2 contra 45
  (−6,3 %), cuando su espejo, la 206, da 42,7 contra 43.
- **Errores de la fuente**:
  - la ficha de la 104 repite las superficies de la 401;
  - la ficha de la 203 da el dormitorio de 3,00 × 3,60 y la de la 103, con los mismos muros, de 3,00 × 3,00 (el dibujo
    da 3,05 × 3,13).
- **501 y 502 aparte de 201 y 202**: desde el nivel 4 el bloque no ocupa el lugar de la 203 y el lado izquierdo pasa a
  ser fachada.
- **Sin DXF**: la PB (cocheras 1 a 13, bicicletero y acceso) y el subsuelo (cocheras 14 a 29).

## 4. Para confirmar

- **[pendiente]** Monoambiente con zona de dormir como `Mono` con `Dormitorio 1` (Isla de Flores 001, GR 1591 02,
  M5 205). Si se prefiere 1D, es cambiar la etiqueta, el nombre del archivo y la fila del índice.
- **[pendiente]** Único local cerrado amueblado como oficina como `Dormitorio 1` (Barrios Amorín 101).
- **Error menor de `tools/ver_dxf.py`**: escribe `width="100%%"` en el rectángulo de fondo del SVG; debería ser `100%`.
