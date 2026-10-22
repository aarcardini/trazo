# Medidas y normativa — Trazo

Valores que usa el motor (`engine/standards.py`) y que se editan en la web en el grupo **Normativa** (riel de la izquierda).
**Mínimo** = exigencia normativa encontrada. **Típico** = criterio de proyecto (no normativo) para que los espacios salgan "reales".
Verificar siempre con la normativa vigente del departamento y del organismo correspondiente antes de usar en un proyecto.
Las medidas de mercado (superficie típica de cada tipología, frente y fondo, mix de tipologías de la Vivienda Promovida y de otros mercados) están en `REFERENCIAS.md`; las medidas con fuente del equipamiento y las convenciones de dibujo, en `EQUIPAMIENTO.md`; el costo de construcción por gama y la fórmula de factibilidad, en `COSTOS.md`; las normas de asoleamiento y la geometría solar de Montevideo, en `ASOLEAMIENTO.md` (investigaciones de octubre de 2026, con propuestas pendientes de decisión).

## Vivienda

| Estancia | Mínimo (área / lado) | Típico (área / frente × fondo) | Referencia del mínimo |
|---|---|---|---|
| Dormitorio principal | 8,5 m² / 2,60 m | 11,5 m² / 3,20 × 3,60 | Normativa Nacional de Edificación (NNE), art. 8 b) |
| Dormitorio secundario | 7,0 m² / 2,00 m | 9,0 m² / 2,80 × 3,20 | NNE, art. 8 c): dormitorios adicionales |
| Estar-comedor | 10,0 m² / 2,60 m | 15–24 m² según dormitorios | NNE, art. 8 a): al menos un local principal habitable de 10 m² y lado 2,60. Típico (`estar_por_dorms`, R5.16, v2.61): 18 (monoamb.), 15 (1 dorm.), 18 (2), 21 (3), 24 (4); fuente: base de tipologías (`data/tipologias/RESUMEN.md`, 4.3), medianas de 18,1 / 14,5 / 17,3 / 21,2 / 23,2 m² en 49 viviendas de Montevideo (antes 18 / 18 / 20 / 24 / 27) |
| Estudio | 7,0 m² / 2,00 m | 8,0 m² / 2,60 × 3,10 | NNE, art. 8 c): un local que puede usarse como dormitorio (presunción de destino, art. 6). Más chico es un local secundario, sin mínimo (art. 29) |
| Cocina | 4,0 m² / 1,60 m (3 m² si abre a un local principal o a un corredor en el 70 % del lado mayor) | 7,0 m² / 2,40 × 2,90 | NNE, arts. 21 y 22. Hoy Trazo no dibuja cocinas con ventana propia: todas son integradas (fila siguiente) |
| Cocina integrada al estar sin ventana (R10.8) | 3,0 m² / 1,40 m; **máximo 5,0 m²** | — | NNE, art. 27: integrada al estar sin ventana propia, de 3 a 5 m² con lado 1,40; el vano del estar ilumina los dos locales (1/10 de su superficie, con 2 m² como mínimo); más grande necesita su propia luz y ventilación (art. 24). Trazo la dibuja con 5 m² como máximo (criterio del usuario): ver abajo |
| Baño principal | 3,00 m² / 1,20 m; ducha de 0,70 m² y lado 0,70 | 4,0 m² / 1,70 × 2,40 | NNE, art. 17: lavabo, ducha e inodoro; bidé optativo |
| Baño auxiliar | 1,50 m² / 0,80 m con dos artefactos; 2,00 m² / 1,00 m con tres | 2,6 m² / 1,20 × 2,20 | NNE, art. 18. En Trazo, un baño 2 donde no entra la ducha queda como toilette (dos artefactos) |
| Lavadero / terraza de servicio | 1,5 m² | 2,5 m² / 1,20 × 2,10 | MVOT Reglamento de producto, art. 6 g) (vivienda de interés social). Para la NNE es un local secundario, sin mínimo (arts. 4 y 29) |
| Depósito | 1,0 m² / 0,80 m; hasta 4,0 m² (0 = sin depósito) | — | Criterio del usuario (v2.33): uno solo, si queda lugar. El placard es el armario del dormitorio (ver «Equipamiento y muebles»), no una estancia |
| Vestidor (opcional, R5.10) | 3,0 m² / 1,20 m de fondo | 2,00 × 1,50 | La NNE no lo regula. Neufert: módulo de placard de 0,60 m con su paso delante, de 0,60 m (vestidor de 1,20 m) a 0,90 m (1,50 m). Solo en los tipos del mix con «Vest.» (criterio del usuario: opcional, junto al dormitorio principal) |
| Pasillo interno | 0,90 m (0,80 si es un solo tramo de hasta 4 m que no lleva a un local accesible) | 1,00 m | NNE, art. 36 |
| Pasaje / hall de entrada | 1,20 m (1,00 si ≤ 5 m) | 1,40 × 1,80 | NNE, art. 34 |
| Altura libre | 2,40 m habitables; 2,20 m cocina, baño y locales secundarios | — | NNE, arts. 9, 17, 21 y 29 |

Las medidas mínimas se cumplen en cualquier dirección: la parte de un local que no llega al lado mínimo no cuenta para su área (NNE, arts. 7 y 10).

Franja de servicios (v2.33, criterio de proyecto; editable en «Vivienda»): la franja sin luz entre el pasillo interno y el pasillo común lleva los baños, el lavadero y el depósito. Su fondo va de 1,80 a 2,80 m: el menor con el que entran con sus superficies típicas (los baños, con ducha: con menos de 2,30 m de fondo, de 1,60 m de ancho como mínimo), y lo que queda va a los dormitorios, hasta 4,50 m de fondo. Si la cocina es tan angosta que va en L, la franja deja que llegue a 2,20 m. Lo que sobra a lo largo de la franja: A, el dormitorio principal pasa al final del pasillo, en suite, con su baño en la franja (hasta su máximo; lo demás va al dormitorio); si no se puede, B, baños, lavadero y depósito más grandes, hasta su máximo (baño 6,0 m², baño auxiliar 4,0, lavadero 4,0, depósito 4,0), y si después queda poco (menos de 0,90 m de largo o de 1 m²), que no da para otra estancia, va a la última estancia de la franja que no es el depósito, aunque pase de su máximo; y si aún sobra, C, queda sin uso, con aviso (criterio del usuario). Lo mismo con un rincón sin luz de más de 4 m².

Banda de servicios (R5.11, v2.42, criterio del usuario): en una vivienda muy profunda (con las medidas por defecto, de más de 9,30 m: dormitorios de 4,50 m, pasillo interno, franja de 2,80 m y 1 m o más) la tira sin luz junto al pasillo común lleva la cocina integrada y el lavadero. El hall va al extremo del estar, con la entrada; la cocina (5 m² como máximo, art. 27) corre de él hacia la tira, con la mesada en línea (de 1,60 a 1,85 m de fondo) o en L (de 2,20 a 2,50 m), y sigue el lavadero, con puerta desde la cocina; el estar (o el comedor, si ya lo había) baja hasta la banda, sin partirse en un comedor aparte. El fondo de la banda no pasa del fondo típico de la cocina (2,90 m, «Cocina» en esta tabla): lo que queda sobre ella, si es menos de 1 m, va a la franja y, si no, queda sin uso con aviso. Lo que sobra a lo largo agranda el lavadero hasta su máximo (4,0 m²); si después queda poco (menos de 0,90 m de largo o de 1 m²), también va al lavadero, aunque pase de su máximo (hasta unos 6,6 m², la misma regla que la franja), y lo demás queda sin uso. El depósito va en la franja, que ya no lleva el lavadero, o, si así queda menos sin uso, en la banda, con puerta desde el lavadero. Con una tira de 1,00 a 1,60 m (no entra la mesada), o si el estar quedaría a más de 3 veces su ancho (art. 14) o sin ventana suficiente para él y la cocina (art. 27), la cocina sigue en la zona de día y la tira lleva el lavadero, con puerta desde el hall (o desde la cocina, con el hall en el extremo); con menos de 1,20 m (el lavarropas, de 0,60 m, y su paso, de 0,60 m), solo si igual entran el lavarropas y la pileta, con su paso (el lavarropas, contra una pared del costado). Con un muro oblicuo o un entrante, la banda se mide con el contorno real (el hall, con 0,90 m sobre el pasillo común para la puerta de entrada y al menos 1,44 m², su lado mínimo al cuadrado; la cocina integrada, con 3 m² y su mesada; el lavadero, con 1,5 m² y sus artefactos; el depósito, con más de 1 m²) y va solo si el plano no empeora; en una vivienda con tira, la suite va solo si el dormitorio principal y su baño quedan dentro de la vivienda y, con la banda, si su baño queda completo.

Vestidor (R5.10, criterio del usuario; casilla «Vest.» de cada tipo del mix, apagada por defecto): va de todo el ancho del dormitorio principal, entre el pasillo interno y el dormitorio, que sigue con su ventana a la fachada y abierto a él; el principal ya no lleva placard. Con la suite (A) toma lo que el dormitorio tenía detrás del pasillo interno, sin luz, y su baño, de su superficie típica, se abre desde el vestidor; con vestidor, la suite se hace aunque no sobre franja si los demás dormitorios no pierden fondo (la vivienda puede perder el depósito: el vestidor guarda). Sin la suite, va a la entrada del dormitorio. Su fondo es el típico o menos, hasta el mínimo, para que al dormitorio le queden su medida mínima y el fondo de la cama doble con su paso al pie (2,50 m). Si no entra, o si el plano empeora con él (por ejemplo, si un muro oblicuo no deja lugar para los estantes), no se agrega y la ficha dice por qué.

Superficie de la vivienda (R10.8, v2.41): la NNE (art. 3) pide 32 m² con un dormitorio, 44 con dos, 56 con tres y 68 con cuatro, medidos con los muros exteriores hasta su cara exterior y hasta el eje de los muros divisorios; con más de cuatro, Trazo suma 12 m² por dormitorio (el mismo salto). El estudio dibujado cuenta como dormitorio (art. 6, presunción de destino). El art. 2 pide estar, cocina, dormitorio y baño, con el dormitorio y el baño como locales independientes: un monoambiente no lo cumple, pero se acepta si tiene al menos 32 m² con muros (criterio del usuario). Editable en «Normativa → Vivienda → Superficie mínima con muros» (monoambiente, 1, 2, 3 y 4 dormitorios).
Superficie con muros (`area_muros`, la ficha la muestra junto a la libre): cada borde de la vivienda se corre hasta la cara exterior del muro exterior en la fachada, en un patio y en la medianera (criterio del usuario: el muro entero, 0,35 m); hasta el eje del muro con la vivienda vecina (0,15 m), con el pasillo común (0,075 m: la mitad del medio muro que las separa) y con el núcleo (0,075 m: su muro está dentro de la caja); un borde sin nada cerca (una zona sin luz, un rincón), hasta el eje de un tabique (0,15 m). Con la vecina, el pasillo y el núcleo se mide la separación real: dos viviendas que se tocan (en los cruces de pasillos dibujados) llegan cada una hasta el borde común y no se cuentan dos veces. En los ejemplos da entre un 4 y un 16 % más que la superficie libre. La superficie libre («m²» de la vivienda, NSA y eficiencia) no cambia.
Rango de referencia ANV según dormitorios: monoambiente 25–40 m², 1 dorm. 35–50, 2 dorm. 50–75, 3 dorm. 65–100, 4 dorm. 80–125.
Ley 13.728, art. 18: mínimo 25 m²; 35 m² para 1 dormitorio y +15 m² por dormitorio adicional.

Muros: el muro entre viviendas es de 0,30 m («Muro entre viviendas» en la web, antes «Muro medianero»); la NNE pide al menos 0,20 m de hormigón o mampostería, o un aislamiento acústico Rw de 45 dB o más (art. 54).

Reglas de distribución que aplica el motor: dormitorios y estar con fachada; dormitorios y baños accesibles desde el pasillo interno; cocina, comedor y estar integrados (conexión abierta); frente mínimo de la unidad = estar + dormitorios (para que todos tengan ventana). Toda vivienda lleva baño y cocina (NNE, arts. 17 y 21): si el plano no los tiene, la ficha lo avisa y baja la calidad del plano; la cocina dentro del hall («Hall / Cocina») cuenta (v2.30).

Calibración con la base de tipologías (R5.16, v2.60; parámetros de `engine/layout.py`, no de `standards.py`): frente mínimo de la vivienda de 3,5 m (`min_unit_width`, antes 5,0 m: la base llega a 3,20 m y solo 4 de 44 viviendas miden menos de 3,5 m), fondo máximo de 16 m (`max_unit_depth`, antes 14 m: la base llega a 15,9 m; el fondo típico sigue en 7,0–7,5 m) y pasillo común de 1,5 m (`corridor_width`, antes 2,0 m; ver «Núcleo de circulación vertical»). Un proyecto guardado conserva los valores con que se hizo.

Cocina integrada de 5 m² como máximo (R10.8, v2.41, criterio del usuario; NNE, art. 27): la cocina pierde fondo, que gana el estar, hasta el que pide su mesada: 1,60 m en línea (heladera, bacha, mesada y cocina, 2,70 m, con su paso de 0,90 m); en L, 2,00 m con 2,20 m de ancho (la mesada contra la pared del costado y la heladera contra el pasillo común) o 2,20 m con 2,00 m de ancho (al revés); y 2,70 m si tiene menos de 2,00 m de ancho (la mesada entera contra la pared del costado). Si aun así pasa de 5 m², se angosta y lo que deja va al hall; si ningún acomodo de la mesada entra en 5 m², se angosta con el fondo que tiene. En una vivienda poco profunda y en un monoambiente, el baño y el hall comparten el fondo de la cocina: primero la cocina se angosta (el baño conserva su fondo y su bidé) y, solo si su mesada no entra así, la franja pierde fondo, sin que el baño baje de su mínimo. El fondo que pierde la cocina no lleva al estar (con el comedor interior) a más de 3 veces su ancho (art. 14) ni crea un comedor interior que no había, salvo que la cocina no entre de otro modo. Si la pared del costado tiene una puerta (el depósito que se abre desde la cocina) o una abertura, la mesada no se apoya en ella. Con un muro oblicuo se mide lo que queda dentro de la vivienda. En un «Hall / Cocina» cuenta solo la parte de la cocina (sin el ancho del hall). Una cocina integrada de más de 5 m² (por ejemplo, con un tabique corrido a mano) se avisa. Pendiente (decisión del usuario): las cocinas con fachada, con ventana propia y su superficie típica (art. 24).

## Equipamiento de baños, cocina y lavadero (F5)

Cada artefacto ocupa un módulo contra una pared maciza (largo a lo largo de la pared × fondo) y deja libre su paso delante; no se apoya en un borde abierto a otra estancia ni pisa el barrido de las puertas. Editables en la web («Normativa → Equipamiento»).

| Elemento | Valor por defecto | Referencia |
|---|---|---|
| Puerta interior (dormitorios, baños, lavadero) | 0,70 m | Criterio indicado por el usuario |
| Puerta de entrada a la vivienda | 0,90 m | Criterio de proyecto (NNE, art. 35: luz libre de paso de 0,80 m como mínimo) |
| Inodoro (con mochila) | módulo 0,75 × 0,70 m | E. Neufert, *Arte de proyectar en arquitectura* (medidas habituales) |
| Bidé | módulo 0,70 × 0,60 m | Ídem |
| Lavatorio | módulo 0,70 × 0,50 m | Ídem |
| Ducha | 0,85 × 0,85 m (en un baño angosto, de pared a pared en la pared del fondo) | Ídem (0,80 × 0,80 mínimo habitual) |
| Paso libre delante de los artefactos del baño | 0,60 m | Ídem |
| Fondo de mesada | 0,60 m | Criterio indicado por el usuario |
| Heladera | 0,70 × 0,70 m | Medida habitual de heladera con freezer |
| Bacha de cocina / cocina con horno | 0,80 m / 0,60 m de largo en la mesada | Medidas habituales |
| Mesada libre entre bacha y cocina | 0,60 m | Criterio de proyecto (zona de trabajo) |
| Paso libre delante de la mesada | 0,90 m | Neufert (0,90–1,20 m) |
| Lavarropas / pileta de lavar | 0,60 × 0,60 m / 0,55 × 0,45 m, con 0,60 m de paso | Medidas habituales |

Reglas del motor: el baño principal lleva ducha, inodoro y lavatorio (y bidé si entra); un segundo baño donde no entra la ducha queda como toilette (inodoro y lavatorio, con aviso). La puerta de un baño o lavadero va al centro del borde o junto a una esquina, donde mejor entran los artefactos. El ancho mínimo de un baño sale del inodoro con su paso (0,70 + 0,60 = 1,30 m) y el del lavadero, del lavarropas con su paso (1,20 m). La cocina lleva una mesada corrida con heladera, bacha, mesada de trabajo y cocina; si no entra en línea, la heladera va en otra pared (en L). Lo que no entra se avisa en la ficha de la vivienda.

## Muebles de dormitorios, estar y comedor (F5)

Cada mueble es un módulo con su paso libre. Ninguno va delante de las aberturas al hall, al pasillo o a la cocina (paso del estar), el placard y el rack de TV no van contra una ventana, y desde cada puerta o abertura se llega a todos (un paso de unos 0,50 m como mínimo entre muebles). Editables en la web («Normativa → Equipamiento y muebles»).

| Elemento | Valor por defecto | Referencia |
|---|---|---|
| Cama doble | 1,40 × 1,90 m (ancho × largo) | E. Neufert (medidas habituales) |
| Cama individual | 0,90 × 1,90 m | Ídem |
| Mesa de luz | 0,45 × 0,40 m | Ídem |
| Paso junto a la cama | 0,60 m a los lados y al pie de la cama doble; entre dos individuales y a un costado de una sola | Ídem (0,60–0,75 m) |
| Placard | 0,60 m de fondo; 1,80 m de largo en el dormitorio principal y 1,20 m en los demás, con 0,60 m de paso | Medidas habituales |
| Mesa del comedor | 0,60 m de largo por asiento (mínimo 0,80), 0,90 m de ancho, 0,75 m para las sillas a cada lado | Neufert |
| Asientos | 2 en un monoambiente; 4 con un dormitorio y 2 más por cada dormitorio siguiente (6 con dos, 8 con tres) | Criterio indicado por el usuario |
| Sofá / butaca | 2,00 × 0,90 m / 0,80 × 0,80 m | Medidas habituales |
| Rack de TV | 1,60 × 0,45 m, a 1,50 m o más del sofá | Neufert (unos 2,2 m de los ojos a la pantalla) |
| Paso delante de las aberturas del estar | 0,90 m | Criterio de proyecto (circulación del hall al pasillo y a la cocina) |

Reglas del motor: el dormitorio principal lleva la cama doble (mejor con la cabecera contra una pared sin ventana ni puerta) y su placard; los demás, dos camas individuales o, si no entran, una (aviso informativo). Si el placard no entra entero, se prueba más corto (de a 0,30 m, hasta 0,90 m) antes que dejarlo afuera. En el estar, el rack va contra una pared maciza sin ventana y el sofá enfrente, contra la pared opuesta o suelto a la distancia de la TV; la mesa va cerca de la cocina. Si la mesa no entra con todos los asientos, se prueba una más chica y se avisa (para un dormitorio, una mesa más chica es aceptable y el aviso es informativo). El comedor y el estar contiguos se amueblan juntos. En una estancia que ya no llega a su lado o área mínima no se suma el aviso de lo que no entra. Al repartir el frente entre los dormitorios, el principal conserva el ancho de su cama doble con el placard al costado (paso + cama + paso + placard: 3,20 m con las medidas por defecto) cuando el fondo no deja ponerlo al pie de la cama, siempre que los demás dormitorios lleguen a su mínimo (criterio del usuario, v2.29).

## Vivienda accesible (F5)

Para los tipos del mix marcados «Acc.». Editables en «Normativa → Equipamiento y muebles».

| Elemento | Valor por defecto | Referencia |
|---|---|---|
| Puertas de dormitorios y baño | 0,82 m | Criterio indicado por el usuario (paso de la silla de ruedas). UNIT 200:2021, 4.11.4.6: luz libre de paso de 0,80 m como mínimo y 2,00 m de alto; con aproximación lateral, al lado de la puerta queda libre B ≥ 0,90 m si la hoja mide 0,90, 0,95 si mide 0,85 y 1,00 si mide 0,80 |
| Círculo de giro en el baño | Ø 1,50 m, libre de artefactos (puede pisar la ducha a nivel) | UNIT 200:2021, 4.1.2 (espacio de maniobra: Ø 1,50 m; 1,20 m en accesibilidad básica) |
| Espacio de transferencia junto al inodoro | 0,80 m de ancho a un costado, del fondo del inodoro más su paso | UNIT 200:2021, 4.1.3 (0,80 × 1,20 m) y 4.11.4.4 a.1 (transferencia lateral al inodoro) |
| Ducha a nivel (sin plato) | 1,20 × 0,90 m, con asiento rebatible | UNIT 200:2021, 4.11.4.4 a.4: 0,80 × 1,20 m libres como mínimo, al nivel del piso del baño, con transferencia lateral contigua |
| Baño de la vivienda accesible | 2,20 m de frente (el fondo lo da la planta; la comprobación es el giro) | Criterio de proyecto. UNIT 200:2021, 4.11.4.4: la puerta abre hacia afuera o es corrediza (en accesibilidad básica puede abrir hacia adentro si se puede quitar desde afuera) |
| Pasillo interno de la vivienda accesible | 0,90 m (el mismo de la NNE, art. 36) | UNIT 200:2021, 4.11.3: pasillos y galerías dentro de la vivienda, 0,90 m; de uso público, 1,20 m (0,90 en básica) |

Reglas del motor: el baño principal abre hacia afuera (el barrido de la hoja no quita lugar al giro); no lleva bidé; el costado del inodoro sin transferencia va, si se puede, contra la pared (barra de apoyo). Si el baño no llega, se dibuja el baño común y la ficha avisa. Pendiente: círculos de giro en cocina y dormitorios (UNIT 200:2021, 4.11.4.1: el dormitorio accesible lleva el espacio de maniobra y un paso libre de 0,90 m hasta el placard y, por lo menos, a un costado de la cama, y da a un baño accesible). Los valores se compararon con la norma el 13/10/2026 (R10.11) y todos cumplen; la norma la publica la Intendencia de Montevideo con licencia individual de UNIT, así que aquí van solo los valores con su apartado.

## Ventanas (R5.5)

Una ventana por estancia habitable (dormitorios, estar, comedor y estudio) con fachada. Editables en «Normativa → Ventanas».

| Elemento | Valor por defecto | Referencia |
|---|---|---|
| Vano mínimo de iluminación | 10 % de la superficie del local (1/10) | NNE, art. 11: vano de iluminación directa no menor a 1/10 de la superficie del local; antepecho no mayor a 1,50 m. Art. 13: la parte móvil, al menos el 50 % del vano mínimo (una ventana corrediza de dos hojas lo cumple). Lo mismo dice el Digesto de Montevideo («De los locales habitables», D.3319) |
| Alto de la ventana | 1,20 m | Criterio de proyecto (con él se pasa del área al ancho) |
| Ancho típico | 1,50 m en dormitorios y estudio; 2,00 m en el estar y el comedor | Criterio de proyecto: se agranda si el vano mínimo pide más |
| Libre a una esquina o tabique | 0,20 m | Criterio de proyecto |
| Profundidad del local (R10.8) | hasta 3 veces su lado menor | NNE, art. 14. Trazo lo comprueba en dormitorios, estar, comedor y estudio (salvo en uno ya avisado por su medida o por no tener fachada) y en el estar con el comedor interior: su profundidad desde la ventana contra su ancho |
| Vano del estar con la cocina integrada (R10.8) | 1/10 del estar y la cocina, 2 m² como mínimo | NNE, art. 27 («vano mín. del estar» en «Normativa → Vivienda → Cocina integrada»). Solo cuenta la cocina sin ventana propia (R10.9) |
| Ventana de la cocina con fachada (R10.9) | 0,40 m² como mínimo; 1/10 de su superficie si pide más; ancho típico 1,00 m | NNE, art. 24: la cocina con ventana propia, vano no menor a 0,40 m² (y el 1/10 del art. 11). El ancho típico es criterio de proyecto; las dos medidas se editan en «Normativa → Ventanas» |

Reglas del motor: la ventana va centrada en el tramo de fachada más largo de la estancia, primero en la fachada del fondo; si no llega al vano mínimo, se agrega otra en el tramo siguiente (por ejemplo, la fachada lateral de una esquina). Una estancia de esquina lleva además una ventana del ancho típico en la otra fachada, si entra (R5.3). El comedor sin fachada se ilumina por el estar: el vano del estar cuenta la superficie de los dos, y también la de la cocina integrada sin ventana propia, con 2 m² como mínimo (art. 27). La ventana va en el muro exterior y solo donde del otro lado hay aire: junto a una esquina entrante no se mete en el muro de la otra ala. Si no alcanza, o si no entra ninguna, la ficha lo avisa (salvo en una estancia ya avisada por no tener fachada o por no llegar a su medida mínima).

Cocinas (R10.9, decisión del usuario en v2.41): la cocina con un tramo de fachada en el que entra una ventana (en las viviendas de punta o de esquina, donde la cocina toca la fachada lateral) lleva la suya (art. 24) y es una cocina según el art. 21 (mínimo 4 m², lado 1,60 m): se dibuja con su superficie típica (7 m²) como máximo en vez de los 5 m² de la cocina integrada, conserva su fondo (se angosta primero; lo que deja va al hall, al baño o a un depósito, como con la integrada; el fondo no deja al estar más ancho que 3 veces su fondo, art. 14) y no suma su superficie al vano del estar. La cocina sin fachada sigue integrada al estar, de 5 m² como máximo (art. 27), y se ventila con extractor eléctrico: la ficha dice «con extractor».

Lo que la NNE pide y Trazo todavía no comprueba (ROADMAP R10.8 y R11.3):
- la ventana en el lado menor del local o en el primer tercio del mayor (art. 14; la profundidad de hasta 3 veces el lado menor sí se comprueba desde v2.41);
- la ventilación de 1 m² de la cocina integrada (art. 27): desde v2.46 se resuelve con extractor (decisión del usuario; la cocina con fachada lleva su ventana, art. 24, R10.9);
- baños: sin luz natural obligatoria, pero ventilados por un vano (0,10 m² al exterior, 0,20 m² por una logia) o por un ducto (arts. 19 y 38 a 40);
- iluminación indirecta por logias de más de 1,20 m de fondo: vano de 1/6 del local si da al espacio abierto y de 1/5 si no (art. 12).

## Segunda fachada (R5.3)

Para viviendas con fachada en todo el fondo y en un solo costado (de esquina o de extremo). No usa medidas nuevas: las de la vivienda y las ventanas.

Reglas del motor: si el frente alcanza para el estar y los dormitorios al fondo, el estar va al costado con fachada (en la esquina: luz y ventana por dos fachadas). Si no alcanza y entre el pasillo común y el pasillo interno hay fondo para un dormitorio (3,00 m), el último dormitorio va a ese costado, con su ventana; Trazo compara los dos planos y lo hace solo si mejora la calidad del plano y no pierde estancias (cocina, lavadero, estar, dormitorios; el segundo baño, solo con hasta 2 dormitorios: criterio del usuario). En una vivienda irregular, el plano al revés se usa solo si no es peor. Si el fondo no es todo fachada, o la vivienda da a los dos costados, el plano no cambia. Pendiente: viviendas sin fachada al fondo con luz solo por un costado.

## Núcleo de circulación vertical

| Elemento | Valor | Referencia |
|---|---|---|
| Ancho de tramo de escalera | 1,20 m (general) — 1,65 m en ciertos usos > 750 m² o > 12 m | Bomberos IT 19, 6.2.2.1 |
| Escalera colectiva (higiene) | 1,00 m con ascensor / 1,20 m sin ascensor; descanso cada 18 escalones | NNE, art. 31 A.1 y A.2 |
| Ancho de tramo con ascensor (R5.16, v2.60; clave `nucleo.escalera_ancho_con_ascensor`) | 1,00 m en un edificio con ascensor (el descanso y la meseta miden lo mismo); sin ascensor sigue valiendo `nucleo.escalera_ancho` (1,20 m) | NNE, art. 31 A.1: escalera colectiva de 1,00 m con ascensor. La base de tipologías mide núcleos de 13,7 m² de mediana (`data/tipologias/RESUMEN.md`, 4.4); con esta medida el núcleo del motor sin palier baja de 23,5 a 19,5 m² (escalera perpendicular al pasillo) y de 19,6 a 16,7 m² (a lo largo) |
| Contrahuella | 16–18 cm (máx. 0,18 sin ascensor; 0,19 con ascensor) | IT 19 / NNE art. 31 |
| Huella | 2a + b = 0,64 m (→ 0,29 con 17,5 cm) | IT 19 / NNE art. 31 |
| Altura máxima por tramo | 3,70 m | IT 19 |
| Tipo de escalera (vivienda) | común ≤ 12 m; protegida (EP) 12–30 m; presurizada (PFP) > 30 m | IT 19, Anexo C, tabla 3 (grupo A) |
| Recorrido máximo de evacuación (vivienda, pisos altos) | 40 m (una salida) / 45 m (más de una), sin detección | IT 19, Anexo B, tabla 2 |
| Criterio de proyecto en Trazo (editable) | fondo de saco ≤ 18 m (tramo con una sola dirección de salida); recorrido ≤ 30 m hasta el núcleo más cercano | Más exigente que IT 19; ajustar en «Fondo de saco máx.» y «Recorrido máx. a un núcleo» |
| Ducto de ascensor accesible | 1,75 × 1,95 m (accesibilidad básica 1,70 × 1,75) | Intendencia de Montevideo, ductos y cabinas |
| Cabina accesible | 1,10 × 1,40 m, puerta 0,80 m | Ídem |
| Ascensor obligatorio | acceso a más de 9 m de altura | MVOT, estándares de desempeño (cl. 58) |
| Palier frente a ascensores | 1,50 m (círculo de giro) | Accesibilidad. El palier se comunica en cada piso con la escalera (NNE, art. 35) |
| Pasillo común (accesos, pasillos de piso y palier) | 1,50 m en Trazo («Ancho de pasillo»; v2.60, antes 2,00 m: la base de tipologías mide 1,50 m de mediana, de 1,21 a 2,18 m); cada tramo puede tener el suyo (R10.8) | NNE, art. 35: 1,20 m hasta 3 viviendas, 1,40 de 4 a 10 y 1,60 con 11 o más; 2,00 m si un tramo recto pasa de 15 m (salvo con el 60 % de sus paredes vidriado o abierto); ducto de ventilación de 0,20 × 0,20 m cada 15 m. Trazo lo comprueba en cada tramo (v2.39): las viviendas que sirve son las que pasan por él en su recorrido más corto al núcleo, y el largo del tramo recto incluye el conector hasta el pasillo al que llega. No detecta las paredes vidriadas ni pide el ducto. Valores editables en «Normativa → Núcleo» |
| Ducto de instalaciones | 0,60 m de ancho | NNE, art. 39 D: ducto colectivo con cañerías de 0,60 m² y 0,60 m de ancho, transitable, con escalera marinera |

Cantidad de ascensores (v2.32): cada núcleo lleva los que piden las viviendas que sirve, las que tienen en él su recorrido más corto: 1 cada 60 (criterio de proyecto, editable) y al menos 1 si el acceso pasa de 9 m. En automático todos los núcleos son iguales y llevan los del más cargado. Desde 10 niveles, el edificio lleva al menos 2 en total: el mínimo es por edificio (criterio del usuario). Se pueden fijar a mano: en la ficha de un núcleo (0 es un núcleo solo con escalera), para todos («Ascensores por núcleo») o desde Rhino, con un punto llamado «ascensores=2». Con una cantidad propia, el frente del núcleo toma las medidas de la normativa para esa cantidad.
El núcleo se dimensiona sumando caja de escalera de ida y vuelta + ascensores + ducto de instalaciones; el fondo es el mayor entre la escalera y palier + ducto de ascensor. Con giro 90° (la escalera sube a lo largo del pasillo) el frente es el largo de la escalera + ascensores + ducto y el fondo, el mayor entre el ancho de la escalera y palier + ducto de ascensor: un núcleo más ancho y menos profundo. Cada núcleo manual puede tener frente y fondo propios.

## Oficinas y comercio

| Parámetro | Valor | Referencia |
|---|---|---|
| Inodoros | 1 cada 15 trabajadores hasta 100; 1 cada 20 de 101 a 200; 1 cada 30 después (por sexo) | Decreto 406/988, art. 78 |
| Servicios separados por sexo | más de 5 trabajadores | Decreto 406/988, art. 77 |
| Densidad de oficinas | 10 m²/puesto (proyecto); 7 m²/persona para evacuación | IT 19 (grupo D) |
| Densidad comercial | 20 m²/persona para baños (proyecto); 5 m²/persona para evacuación | IT 19 (C1–C3) |
| Cubículo de inodoro | 0,95 × 1,50 m | Criterio de proyecto |
| Baño accesible | 1,80 × 2,00 m | Criterio de proyecto (giro 1,50) |

Distribución: hall de acceso frente al núcleo, batería de baños (mujeres, hombres, accesible) junto al núcleo y **el resto como planta libre**.

## Predio

| Parámetro | Valor | Referencia |
|---|---|---|
| Retiro desde medianera para abrir ventanas | 3,00 m | NNE, arts. 46, 48 y 52: los espacios abiertos y los patios que iluminan quedan a 3 m o más del eje del muro divisorio |
| Retiro mínimo si el edificio se separa de la divisoria (R10.8) | 1,00 m | NNE, art. 53 e). Un retiro de medianera de más de 0 y menos de 1 m se avisa («pon 0 (adosado) o 1 m o más»); de 1 a 3 m sigue el aviso de que no admite ventanas. Pendiente: los linderos sin medianera del terreno rectangular (se descuentan en la web y el motor no los ve) |
| Ancho mínimo de patio para iluminar | 3,00 m (fijo) | Criterio indicado por el usuario. La NNE (arts. 44 y 45) lo pide según la altura h del patio, medida desde el piso del local más bajo que ilumina: patio principal, lado L = h/4 (nunca menos de 2,85 m) y superficie S = 2h; patio secundario (solo cocinas, baños y locales secundarios), L = h/10 + 1,20 y S = 3h/4. Con h = 12 m da 3,00 m; con más altura, más. Pendiente (ROADMAP R11.2) |

Una medianera puede ocupar solo parte de un borde (hoy se dibuja así en Rhino, en la capa `Trazo::Medianeras`): el retiro se aplica solo a lo largo de su tramo y la huella queda escalonada (v2.31). Varios tramos en un mismo lado, por ejemplo 0–12 m ciega y 12–30 m con 3 m de retiro, se marcan como medianeras separadas.

## Masterplan (fraccionamiento)

| Parámetro | Valor por defecto | Referencia |
|---|---|---|
| Área mínima de lote | 300 m² | Ley 10.723 de Centros Poblados, art. 16 (redacción dada por la Ley 19.044): suelo urbano y suburbano |
| Frente mínimo de lote | 12 m | Ley 10.723, art. 16 en su texto original (ancho medio 12 m). Hoy lo fijan los instrumentos departamentales: editable |
| Calzada / veredas | 9 m + 2 × 4 m = 17 m | Criterio de proyecto (la ley no fija un ancho único): ajustar según el departamento |
| Ochava | 3 m por lado | Criterio de proyecto: ajustar a la ordenanza departamental |
| Manzana (damero) | 80 × 120 m | Criterio de proyecto |
| Fondo mínimo para dos filas de lotes | 25 m por fila | Criterio de proyecto |
| Fondo máximo sugerido | 50 m | Criterio de proyecto (aviso: conviene calle intermedia o pasaje) |
| Retiro frontal / lateral / de fondo | 4 m / 0 m / 20 % del fondo | Criterio de proyecto: verificar en el plan local |
| FOS | 60 % | Criterio de proyecto: verificar en el plan local |
| Superficie por vivienda (estimación) | 75 m² construidos (80 % aprovechable) | Criterio de proyecto |
| Reserva para espacios libres y equipamiento | ≥ 10 % del predio, sin contar calles (el departamento puede bajarla hasta 8 %) | Ley 18.308, art. 38: se cede de pleno derecho a la Intendencia; la red vial la ejecuta el fraccionador |

El modo informa la **reserva** (verde + equipamiento, contra el mínimo) y las **cesiones** totales (calles + verde + equipamiento), y avisa si la reserva no llega al mínimo.

## Estacionamiento

| Parámetro | Valor | Referencia |
|---|---|---|
| Plaza | 2,50 × 5,00 m | Práctica habitual en Uruguay (indicado por el usuario) |
| Calle de circulación | 6,00 m | Ídem; coincide con la calle de maniobra a 90° del Digesto (abajo) |
| Módulo de peine doble | 5,00 + 6,00 + 5,00 = 16,00 m | — |

Digesto de Montevideo (Vol. XV, Título V, Cap. XVIII, «Edificios y espacios destinados a estacionamientos», arts. D.4082.50 a D.4082.98; leído el 13/10/2026 en normativa.montevideo.gub.uy). Todavía no los usa el motor (R10.10 del ROADMAP):

| Parámetro | Valor | Referencia |
|---|---|---|
| Sitios | el 80 % de 4,30 × 2,15 m y el 20 % restante de 4,80 × 2,40 m | D.4082.55 |
| Sitios en boxes | cada medida mínima + 0,50 m; tabique de 0,10 m | D.4082.55 |
| Calle de maniobra según el ángulo de los sitios | 90°: 6,00 m; 60°: 5,00; 45°: 4,00; 30°: 3,75; 0° (en paralelo): 3,00 | D.4082.55 |
| Reducción admitida del ancho | hasta 0,20 m, en 1,00 m de largo como máximo, por estructura o cañerías | D.4082.55 |
| Sitios sin acceso directo desde la calle | hasta 2 dentro del mínimo exigido (salvo a 0°) | D.4082.55 |
| Estructura | no va en calles ni en sitios; solo en sus divisorias o esquinas | D.4082.55 |
| Vereda entre el ascensor y la calle o los sitios | 1,20 m con cordón de 0,10 m | D.4082.55 |
| Circulaciones (rampas y calles de acceso) | 2,70 m hasta 50 vehículos; 4,80 m con más (y estudio de impacto de tránsito) | D.4082.54 |
| Pendiente de las rampas | 15 % como máximo; 20 % si el edificio es solo de vivienda u oficinas; 4,00 m al 5 % antes de la vereda | D.4082.54 |
| Altura libre | 2,20 m (2,00 m bajo la estructura) | D.4082.52 |
| Estacionamiento individual (no se le aplica el capítulo) | hasta 3 vehículos | D.4082.51 |
| Plaza accesible | franja lateral libre de 1,10 m del largo del sitio (2,40 m con rampa lateral; dos sitios pueden compartirla) o posterior de 2,40 m | UNIT 200:2021, 4.9.1 |

Pendiente: rampas, plazas accesibles y radios de giro en el motor (ver ROADMAP).

## Ochava y lotes en Montevideo (R8.9, pendiente en el motor)

| Parámetro | Valor | Referencia |
|---|---|---|
| Ochava | perpendicular a la bisectriz, de 5 m como mínimo (8 m fuera de los centros urbanos); en ángulo agudo, 3,53 m sobre cada alineación desde el vértice; con 135° o más no se exige | Digesto, Vol. XV, arts. D.3186 a D.3193; Vol. IV, D.223.97 y siguientes (trazados nuevos) |
| Ochava en Trazo (`masterplan.ochava`) | 3,0 m sobre cada lado (4,24 m a 90°) | Criterio de proyecto; queda corto para Montevideo |
| Lote en suelo urbano | 10 m de frente y 200 m² (Central; Intermedia con FOS 80 y 60 %; Periférica y otras áreas con saneamiento), 12 m y 300 m² (Intermedia con FOS 50 %; Costera con FOS 80 y 60 %; Periférica sin saneamiento) o 15 m y 500 m² (Intermedia con FOS 35 %; Costera con FOS 50 y 35 %); con frente a rutas o vías de enlace, 15 m y 500 m² | Digesto, Vol. IV, D.223.97 y D.223.97.1 (Dto. JDM 39.163 de 2025) |
| Tolerancia | hasta dos lotes con el 10 % menos de frente y el 15 % menos de superficie | Digesto, Vol. IV, fraccionamientos |

## Fuentes consultadas
- Normativa Nacional de Edificación — Higiene de la Vivienda (Congreso de Intendentes, MVOTMA y SAU, 2016; comisión con participación de la Intendencia de Montevideo). PDF aportado por el usuario
- [Ordenanza de higiene de edificios destinados a vivienda (San José, Res. 1244/1977)](https://sanjose.gub.uy/wp-content/uploads/2015/07/ordenanzahigieneedificios.pdf) (fuente de los mínimos hasta v2.26)
- [Higiene de la vivienda (Río Negro, Dec. 92/1979)](https://innovacionpublica.anii.org.uy/wp-content/uploads/2023/04/HIGIENE-DE-LA-VIVIENDA.pdf) (ídem)
- [Ley 13.728, art. 18 (IMPO)](https://www.impo.com.uy/bases/leyes/13728-1968/18)
- [ANV — áreas vigentes según dormitorios](https://www.anv.gub.uy/sites/default/files/2020-07/AREAS_VIGENTES_SEGUN_DORM.pdf)
- [MVOT — Estándares de desempeño y requisitos para la vivienda de interés social](https://www.gub.uy/ministerio-vivienda-ordenamiento-territorial/sites/ministerio-vivienda-ordenamiento-territorial/files/documentos/publicaciones/estanddesempeno_0.pdf)
- [MVOT — Reglamento de producto](https://www.gub.uy/ministerio-vivienda-ordenamiento-territorial/sites/ministerio-vivienda-ordenamiento-territorial/files/documentos/publicaciones/reglapro.pdf)
- [Dirección Nacional de Bomberos — IT 19 Salidas de emergencia](https://www.gub.uy/ministerio-interior/sites/ministerio-interior/files/documentos/publicaciones/IT%2019%20Salidas%20de%20emergencia_0.pdf)
- [Intendencia de Montevideo — dimensiones mínimas de ductos y cabinas de ascensor](https://montevideo.gub.uy/sites/default/files/biblioteca/medidasdeductodeascensor_0.pdf)
- [Ley 10.723 de Centros Poblados y modificativas (Intendencia de Montevideo)](https://montevideo.gub.uy/sites/default/files/biblioteca/leydecentrospobladosymodificativasactnov2018.pdf)
- [Ley 10.723, art. 16 (IMPO)](https://www.impo.com.uy/bases/leyes/10723-1946/16)
- [Ley 18.308, art. 38 (IMPO)](https://www.impo.com.uy/bases/leyes/18308-2008/38)
- [Decreto 406/988 — Reglamento de seguridad e higiene ocupacional (IMPO)](https://www.impo.com.uy/bases/decretos-reglamento/406-1988)
- [Digesto de Montevideo — De los locales habitables](https://normativa.montevideo.gub.uy/articulos/82820) y [D.3318](https://normativa.montevideo.gub.uy/content/d3318) (iluminación de locales habitables; D.3319 sobre la parte móvil). Consultados a través de un buscador cuando el sitio no se podía abrir desde aquí
- [Digesto de Montevideo — Edificios y espacios destinados a estacionamientos](https://normativa.montevideo.gub.uy/articulos/82846) (Vol. XV, Tít. V, Cap. XVIII, arts. D.4082.52 a D.4082.98; [disposiciones generales](https://normativa.montevideo.gub.uy/articulos/86214), D.4082.50 y D.4082.51). Leído el 13/10/2026
- [Digesto de Montevideo — De las ochavas](https://normativa.montevideo.gub.uy/articulos/82696) (Vol. XV, arts. D.3186 a D.3193) y [Fraccionamientos y reparcelamientos](https://normativa.montevideo.gub.uy/articulos/92429) (Vol. IV, D.223.97 y siguientes). Leídos el 13/10/2026
- [Digesto de Montevideo — Condiciones de accesibilidad en edificaciones destinadas a viviendas, escritorios y oficinas](https://normativa.montevideo.gub.uy/articulos/90772) (Vol. XVI, arts. R.1894.8 a R.1894.9.1: rige desde 4 viviendas; itinerario accesible hasta el estar comedor y accesibilidad convertible en un dormitorio, un baño y la cocina)
- [UNIT 200:2021 — Accesibilidad de las personas al medio físico](https://montevideo.gub.uy/sites/default/files/biblioteca/unit2002021.pdf) (copia que publica la Intendencia de Montevideo, con licencia individual de UNIT: aquí se citan valores y apartados, no texto). Leída el 13/10/2026

Nota: desde v2.27 los mínimos de la vivienda siguen la Normativa Nacional de Edificación (2016), que rige en todos los departamentos (confirmado por el usuario). El Digesto de Montevideo (normativa.montevideo.gub.uy) no estaba disponible al consultar entonces; desde el 13/10/2026 se leyó directamente (estacionamiento, ochavas, lotes y accesibilidad).
