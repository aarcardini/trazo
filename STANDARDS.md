# Medidas y normativa — Trazo

Valores que usa el motor (`engine/standards.py`) y que se editan en la web en **0 · Medidas y normativa**.
**Mínimo** = exigencia normativa encontrada. **Típico** = criterio de proyecto (no normativo) para que los espacios salgan "reales".
Verificar siempre con la normativa vigente del departamento y del organismo correspondiente antes de usar en un proyecto.

## Vivienda

| Estancia | Mínimo (área / lado) | Típico (área / frente × fondo) | Referencia del mínimo |
|---|---|---|---|
| Dormitorio principal | 8,5 m² / 2,60 m | 11,5 m² / 3,20 × 3,60 | Normativa Nacional de Edificación (NNE), art. 8 b) |
| Dormitorio secundario | 7,0 m² / 2,00 m | 9,0 m² / 2,80 × 3,20 | NNE, art. 8 c): dormitorios adicionales |
| Estar-comedor | 10,0 m² / 2,60 m | 18–27 m² según dormitorios | NNE, art. 8 a): al menos un local principal habitable de 10 m² y lado 2,60. Típico: 18 (monoamb./1 dorm.), 20 (2), 24 (3), 27 (4) |
| Estudio | 7,0 m² / 2,00 m | 8,0 m² / 2,60 × 3,10 | NNE, art. 8 c): un local que puede usarse como dormitorio (presunción de destino, art. 6). Más chico es un local secundario, sin mínimo (art. 29) |
| Cocina | 4,0 m² / 1,60 m (3 m² si abre a un local principal o a un corredor en el 70 % del lado mayor; integrada: 3 a 5 m², lado 1,40) | 7,0 m² / 2,40 × 2,90 | NNE, arts. 21, 22 y 27 |
| Baño principal | 3,00 m² / 1,20 m; ducha de 0,70 m² y lado 0,70 | 4,0 m² / 1,70 × 2,40 | NNE, art. 17: lavabo, ducha e inodoro; bidé optativo |
| Baño auxiliar | 1,50 m² / 0,80 m con dos artefactos; 2,00 m² / 1,00 m con tres | 2,6 m² / 1,20 × 2,20 | NNE, art. 18. En Trazo, un baño 2 donde no entra la ducha queda como toilette (dos artefactos) |
| Lavadero / terraza de servicio | 1,5 m² | 2,5 m² / 1,20 × 2,10 | MVOT Reglamento de producto, art. 6 g) (vivienda de interés social). Para la NNE es un local secundario, sin mínimo (arts. 4 y 29) |
| Pasillo interno | 0,90 m (0,80 si es un solo tramo de hasta 4 m que no lleva a un local accesible) | 1,00 m | NNE, art. 36 |
| Pasaje / hall de entrada | 1,20 m (1,00 si ≤ 5 m) | 1,40 × 1,80 | NNE, art. 34 |
| Altura libre | 2,40 m habitables; 2,20 m cocina, baño y locales secundarios | — | NNE, arts. 9, 17, 21 y 29 |

Las medidas mínimas se cumplen en cualquier dirección: la parte de un local que no llega al lado mínimo no cuenta para su área (NNE, arts. 7 y 10).

Superficie de la vivienda: la NNE (art. 3) pide 32 m² con un dormitorio, 44 con dos, 56 con tres y 68 con cuatro, medidos con los muros exteriores hasta su cara exterior y hasta el eje de los muros divisorios. El art. 2 pide estar, cocina, dormitorio y baño, con el dormitorio y el baño como locales independientes: un monoambiente no lo cumple, pero se acepta si tiene al menos 32 m² (criterio del usuario). Trazo todavía no comprueba estos dos artículos (ROADMAP R10.8).
Rango de referencia ANV según dormitorios: monoambiente 25–40 m², 1 dorm. 35–50, 2 dorm. 50–75, 3 dorm. 65–100, 4 dorm. 80–125.
Ley 13.728, art. 18: mínimo 25 m²; 35 m² para 1 dormitorio y +15 m² por dormitorio adicional.

Muros: el muro entre viviendas es de 0,30 m («Muro medianero» en la web); la NNE pide al menos 0,20 m de hormigón o mampostería, o un aislamiento acústico Rw de 45 dB o más (art. 54).

Reglas de distribución que aplica el motor: dormitorios y estar con fachada; dormitorios y baños accesibles desde el pasillo interno; cocina, comedor y estar integrados (conexión abierta); frente mínimo de la unidad = estar + dormitorios (para que todos tengan ventana). Toda vivienda lleva baño y cocina (NNE, arts. 17 y 21): si el plano no los tiene, la ficha lo avisa y baja la calidad del plano; la cocina dentro del hall («Hall / Cocina») cuenta (v2.30).

## Equipamiento de baños, cocina y lavadero (F5)

Cada artefacto ocupa un módulo contra una pared maciza (largo a lo largo de la pared × fondo) y deja libre su paso delante; no se apoya en un borde abierto a otra estancia ni pisa el barrido de las puertas. Editables en la web («Medidas y normativa → Equipamiento»).

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

Cada mueble es un módulo con su paso libre. Ninguno va delante de las aberturas al hall, al pasillo o a la cocina (paso del estar), el placard y el rack de TV no van contra una ventana, y desde cada puerta o abertura se llega a todos (un paso de unos 0,50 m como mínimo entre muebles). Editables en la web («Medidas y normativa → Equipamiento y muebles»).

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

Para los tipos del mix marcados «Acc.». Editables en «Medidas y normativa → Equipamiento y muebles».

| Elemento | Valor por defecto | Referencia |
|---|---|---|
| Puertas de dormitorios y baño | 0,82 m | Criterio indicado por el usuario (paso de la silla de ruedas) |
| Círculo de giro en el baño | Ø 1,50 m, libre de artefactos (puede pisar la ducha a nivel) | Criterio habitual de accesibilidad (UNIT 200, ISO 21542) |
| Espacio de transferencia junto al inodoro | 0,80 m de ancho a un costado, del fondo del inodoro más su paso | Ídem |
| Ducha a nivel (sin plato) | 1,20 × 0,90 m, con asiento rebatible | Ídem |
| Baño de la vivienda accesible | 2,20 m de frente (el fondo lo da la planta; la comprobación es el giro) | Criterio de proyecto |

Reglas del motor: el baño principal abre hacia afuera (el barrido de la hoja no quita lugar al giro); no lleva bidé; el costado del inodoro sin transferencia va, si se puede, contra la pared (barra de apoyo). Si el baño no llega, se dibuja el baño común y la ficha avisa. Pendiente: círculos de giro en cocina y dormitorios.

## Ventanas (R5.5)

Una ventana por estancia habitable (dormitorios, estar, comedor y estudio) con fachada. Editables en «Medidas y normativa → Ventanas».

| Elemento | Valor por defecto | Referencia |
|---|---|---|
| Vano mínimo de iluminación | 10 % de la superficie del local (1/10) | NNE, art. 11: vano de iluminación directa no menor a 1/10 de la superficie del local; antepecho no mayor a 1,50 m. Art. 13: la parte móvil, al menos el 50 % del vano mínimo (una ventana corrediza de dos hojas lo cumple). Lo mismo dice el Digesto de Montevideo («De los locales habitables», D.3319) |
| Alto de la ventana | 1,20 m | Criterio de proyecto (con él se pasa del área al ancho) |
| Ancho típico | 1,50 m en dormitorios y estudio; 2,00 m en el estar y el comedor | Criterio de proyecto: se agranda si el vano mínimo pide más |
| Libre a una esquina o tabique | 0,20 m | Criterio de proyecto |

Reglas del motor: la ventana va centrada en el tramo de fachada más largo de la estancia, primero en la fachada del fondo; si no llega al vano mínimo, se agrega otra en el tramo siguiente (por ejemplo, la fachada lateral de una esquina). Una estancia de esquina lleva además una ventana del ancho típico en la otra fachada, si entra (R5.3). El comedor sin fachada se ilumina por el estar: el vano del estar cuenta la superficie de los dos. La ventana va en el muro exterior y solo donde del otro lado hay aire: junto a una esquina entrante no se mete en el muro de la otra ala. Si no alcanza, o si no entra ninguna, la ficha lo avisa (salvo en una estancia ya avisada por no tener fachada o por no llegar a su medida mínima).

Lo que la NNE pide y Trazo todavía no comprueba (ROADMAP R10.8 y R11.3):
- profundidad del local de hasta 3 veces su lado menor, con la ventana en el lado menor o en el primer tercio del mayor (art. 14);
- cocina integrada al estar sin ventana propia: de 3 a 5 m² con lado de 1,40 m, y el vano del estar de 1/10 de los dos locales, con 2 m² como mínimo, y ventilación de 1 m² (art. 27); una cocina más grande necesita su propia luz y ventilación (art. 24: 0,40 m² como mínimo);
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
| Pasillo común (accesos, pasillos de piso y palier) | 2,00 m en Trazo («Ancho de pasillo») | NNE, art. 35: 1,20 m hasta 3 viviendas, 1,40 de 4 a 10 y 1,60 con 11 o más; 2,00 m si un tramo recto pasa de 15 m (salvo con el 60 % de sus paredes vidriado o abierto); ducto de ventilación de 0,20 × 0,20 m cada 15 m. Trazo no lo comprueba todavía (ROADMAP R10.8) |
| Ducto de instalaciones | 0,60 m de ancho | NNE, art. 39 D: ducto colectivo con cañerías de 0,60 m² y 0,60 m de ancho, transitable, con escalera marinera |

Cantidad de ascensores (criterio de proyecto, editable): 1 cada 60 unidades servidas; mínimo 2 desde 10 niveles.
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
| Retiro desde medianera para abrir ventanas | 3,00 m | NNE, arts. 46, 48 y 52: los espacios abiertos y los patios que iluminan quedan a 3 m o más del eje del muro divisorio. Art. 53 e): un edificio que se separa de la divisoria queda a 1 m como mínimo |
| Ancho mínimo de patio para iluminar | 3,00 m (fijo) | Criterio indicado por el usuario. La NNE (arts. 44 y 45) lo pide según la altura h del patio, medida desde el piso del local más bajo que ilumina: patio principal, lado L = h/4 (nunca menos de 2,85 m) y superficie S = 2h; patio secundario (solo cocinas, baños y locales secundarios), L = h/10 + 1,20 y S = 3h/4. Con h = 12 m da 3,00 m; con más altura, más. Pendiente (ROADMAP R11.2) |

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
| Calle de circulación | 6,00 m | Ídem |
| Módulo de peine doble | 5,00 + 6,00 + 5,00 = 16,00 m | — |

Pendiente: rampas, plazas accesibles y radios de giro (ver ROADMAP).

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
- [Digesto de Montevideo — De los locales habitables](https://normativa.montevideo.gub.uy/articulos/82820) y [D.3318](https://normativa.montevideo.gub.uy/content/d3318) (iluminación de locales habitables; D.3319 sobre la parte móvil). Consultados a través de un buscador: el texto no se pudo abrir desde aquí

Nota: desde v2.27 los mínimos de la vivienda siguen la Normativa Nacional de Edificación (2016), que rige en todos los departamentos (confirmado por el usuario). El Digesto de Montevideo (normativa.montevideo.gub.uy) no estaba disponible al consultar.
