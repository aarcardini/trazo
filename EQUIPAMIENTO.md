# Equipamiento: medidas, pasos libres y graficación — referencias

Investigación del 14 de octubre de 2026 para dos cosas: dar fuente a las medidas de `standards.equipamiento` (hoy casi todas «criterio del usuario») y mejorar cómo se dibujan los muebles y artefactos en la web, el DXF y Rhino (hoy, rectángulos con nombre). Complementa a `STANDARDS.md`.

Cómo leer las cifras:
- **(F)** dato de la fuente citada; **«vía Neufert»**: cifra del Neufert tomada de blogs que lo citan (el libro, el Metric Handbook, el PDF de baños de la NKBA y los textos de UNE 1032, ISO 128 e IRAM no se pudieron abrir). **(S)** criterio propio, sin fuente. Lo que no se encontró se dice.
- De UNIT solo se leyó la UNIT 200:2021 (accesibilidad; copia con licencia individual publicada por la Intendencia: se citan valores, no texto).
- Medidas comerciales de Uruguay: fichas de Divino (colchones y sommiers) y de Sodimac Uruguay (casi todo lo demás). No se encontraron fichas de Sommier Center, Piero, James, Enxuta, Ferrum, Taller 21 ni Tienda Inglesa fuera de las que vende Sodimac.
- Pulgadas convertidas a 0,0254 m. Ancho × fondo [× alto] en metros; «bloque» = la pieza más su espacio de uso.

## 1. Medidas

### Puertas

| Pieza | Trazo hoy | Referencia | Recomendación |
|---|---|---|---|
| Puerta interior / de entrada (hoja) | 0,70 / 0,90 | hojas de 0,625 (baños), 0,725 (paso estándar), 0,825, 0,925 (acceso); alto 2,01 o 2,11 (vía Neufert) | dejar |
| Puerta accesible (hoja) | 0,82 | **luz libre de paso ≥ 0,80** y alto libre 2,00 (UNIT 200, 4.11.4.6); los baños abren hacia afuera o son corredizos | **revisar:** con hoja de 0,82 la luz libre queda en ≈ 0,75–0,78 (S); para cumplir la luz libre, hoja de 0,90. En `STANDARDS.md` y `ROADMAP.md` (R10.11) se dio por cumplido comparando hoja con luz libre: corregirlo cuando se decida |

### Baño

| Pieza | Trazo hoy | Pieza real (F) | Bloque con uso (F) | Recomendación |
|---|---|---|---|---|
| Inodoro | 0,75 × 0,70 | con depósito: Ferrum Bari 0,43 × 0,66 × 0,75; Urban 0,37 × 0,72 × 0,73 (Sodimac); EE. UU. ancho 0,51, fondo 0,69–0,76 (dimensions.com) | vía Neufert: libre 0,70 × 1,20, 0,15 a otro artefacto y 0,20 a pared, módulo 0,80 (hasta 0,90); IRC: 0,381 del eje a pared (módulo 0,76) y 0,533 al frente; NKBA: 0,457 (módulo 0,91) y 0,762 al frente | dejar (0,75 ≈ el módulo de 0,76 del código); 0,80 si el baño lo permite |
| Bidé | 0,70 × 0,60 | Urban 0,345 × 0,545 × 0,40; Gala 0,35 × 0,55 (Sodimac); EE. UU. 0,36–0,41 × 0,61–0,71 | igual que el inodoro; entre artefactos 0,305 mínimo, 0,38–0,46 recomendado | dejar; el fondo puede bajar a 0,55 |
| Lavatorio | 0,70 × 0,50 | con pedestal: 0,47–0,52 × 0,37–0,43 (Sodimac); vía Neufert 0,60 × 0,45 (doble 1,20); alto 0,85 | pedestal + 2 × 0,10 a pared (NKBA) = 0,67–0,72; frente: IRC 0,533, NKBA 0,762, Arrevol 0,70 | dejar |
| Ducha (receptáculo) | 0,85 × 0,85 | cabinas de 0,80 × 0,80 y 0,90 × 0,90 × 2,00; mampara con receptáculo 0,80 × 1,00 (Sodimac); NKBA: interior recomendado 0,91 × 0,91, mínimo 0,762; vía Neufert: nunca menos de 0,60 × 0,60, cómodo desde 0,70 | frente: IRC 0,61, NKBA 0,762, vía Neufert 0,60 (0,50 con vidrio fijo) | dejar; los receptáculos sueltos de 0,70/0,80/0,90/1,00 × 0,80 no se encontraron en catálogo en Uruguay |
| Ducha a nivel (accesible) | 1,20 × 0,90 | 0,80 × 1,20 libres como mínimo, con transferencia lateral contigua, sin escalón (UNIT 200, 4.11.4.4 a.4) | | dejar |
| Transferencia y giro | 0,80; Ø 1,50 | 0,80 × 1,20; Ø 1,50 (Ø 1,20 en accesibilidad básica) (UNIT 200, 4.1.2 y 4.1.3) | | dejar |
| Bañera (no existe) | — | 1,50 × 0,70 × 0,38; 1,20 × 0,70; autoportante 1,80 × 0,80 (Sodimac); vía Neufert ancho 0,70, largo 1,00–2,00 | lado libre: NKBA 0,762 (cómodo 1,12, mínimo 0,56); frente IRC 0,533 | agregar `banera` [1,50, 0,70] (y 1,70) |
| Termotanque (no existe) | — | 50 L: Ø 0,385–0,44; calefón 50 L Ø 0,435 × 0,61 (Sodimac) | | opcional, símbolo Ø 0,45 |

### Cocina y lavadero

| Pieza | Trazo hoy | Pieza real (F) | Bloque con uso (F) | Recomendación |
|---|---|---|---|---|
| Mesada (fondo) | 0,60 | 0,60 vía Neufert; 0,61 (24 in); accesible: fondo máximo 0,60; alto 0,90 | sección 2 | dejar |
| Heladera | 0,70 × 0,70 | James 0,545 × 0,61 × 1,52; 0,625 × 0,58 × 1,70; 0,60 × 0,67 × 1,64 (Sodimac); James RJ-65K 0,79 × 0,735 × 1,76 (pliego estatal †); grandes 0,80–0,90 de fondo, hasta 1,00 con tirador (vía Neufert) | apoyo junto a la heladera 0,381 del lado de la manija (NKBA) | dejar (cubre hasta 0,70); side-by-side no encontradas en Uruguay |
| Bacha de cocina | 0,80 (módulo) | pileta y media 0,69 × 0,40; simple 0,34 × 0,40 (Sodimac) | apoyo a cada lado 0,61 y 0,457 (NKBA) | dejar |
| Cocina con horno, 4 hornallas | 0,60 (módulo) | Smartlife 0,50 × 0,60 × 0,86; Enxuta 0,60 × 0,60 × 0,85 (Sodimac); EE. UU. 0,76 × 0,64 | apoyo junto a la placa 0,305 y 0,381 (NKBA); vía Neufert 0,50 a cada lado recomendado | dejar 0,60; variante 0,50 |
| Mesada de trabajo entre bacha y cocina | 0,60 | mínimo 0,60 entre lavado y cocción (Arrevol, NKBA) | | dejar |
| Anafe (no existe) | — | 0,594 × 0,514 × 0,09 (Sodimac) | | agregar [0,60, 0,52] |
| Horno empotrable (no existe) | — | 0,594 × 0,555 × 0,60 (Sodimac); hasta 0,75 del piso (Arrevol) | | agregar [0,60, 0,56] |
| Microondas (no existe) | — | 20 L 0,456 × 0,326; 30 L 0,495 × 0,382 (Sodimac) | | agregar [0,50, 0,40] como accesorio |
| Lavavajillas (no existe) | — | 12–14 cubiertos 0,60 × 0,57–0,60 × 0,85; compacto 0,55 × 0,50 (Sodimac) | libre al frente 1,00 (Arrevol) | agregar [0,60, 0,60] |
| Lavarropas | 0,60 × 0,60 | carga frontal 0,595–0,64 × 0,44–0,55 × 0,85 (Sodimac) | | dejar (el bloque incluye mangueras y puerta) |
| Secarropas (no existe) | — | 0,595 × 0,55 × 0,84 (Sodimac) | | agregar [0,60, 0,60] |
| Pileta de lavar | 0,55 × 0,45 | de apoyo 0,51 × 0,38; de acero 0,60 × 0,45; doble 0,78 × 0,42 (Sodimac) | | dejar |
| Tender | — | no encontrado (una ficha da «0,598 × 1,06» sin aclarar el eje) | | no agregar |

### Dormitorio

| Pieza | Trazo hoy | Pieza real (F) | Bloque con uso (F) | Recomendación |
|---|---|---|---|---|
| Cama individual | 0,90 × 1,90 | colchón Divino 0,80 × 1,85; vía Neufert 0,90 o 1,05 × 1,90/2,00; Reino Unido 0,92 × 1,88; Europa 0,90 × 2,00; EE. UU. 0,97 × 1,91 (dimensions.com) | con 0,60 por lado: 2,10 × 2,50 | dejar |
| Cama de 1 ½ plaza (no existe) | — | colchón Divino 1,08 × 1,88 | | agregar [1,05, 1,90] (el mercado va de 1,05 a 1,08) |
| Cama doble | 1,40 × 1,90 | colchón Divino 1,38 × 1,88; vía Neufert 1,35 × 1,90/2,00; Reino Unido 1,35 × 1,90; Europa 1,40 × 2,00; EE. UU. 1,37 × 1,91 | con 0,60 por lado y al pie 2,60 × 2,50; con 0,70, 2,80 × 2,60; con 0,762 (dimensions.com) 2,92 × 2,66 | dejar |
| Queen (no existe) | — | sommier y colchón Divino 1,58 × 1,98 (cama con marco 1,70 × 2,10); Europa 1,60 × 2,00; EE. UU. 1,52 × 2,03 | lados y pie 0,762 mínimo, 0,914 cómodo; dormitorio mínimo 9,8 m² (dimensions.com) | agregar [1,60, 2,00] |
| King (no existe) | — | sommier Divino 1,78 × 1,98; Europa 1,80 × 2,00; EE. UU. 1,93 × 2,03; super king 2,00 × 2,00 (vía Neufert) | 11 m² con holgura | agregar [1,80, 2,00] |
| Mesa de luz | 0,45 × 0,40 | 0,385 × 0,295 a 0,48 × 0,39, alto 0,50–0,65 (Sodimac); 0,45 × 0,35 × 0,65 (Emmme) | a 0,05 del colchón | dejar |
| Placard | fondo 0,60; largo 1,80 / 1,20 | fondo 0,60 con puertas abatibles y 0,65 con corredizas (vía Neufert); 0,61 cómodo y 0,51 mínimo (dimensions.com); accesible: estantes de 0,35 a 0,60 (UNIT 200); prefabricados 0,47–0,54 × 1,82–2,00 (Sodimac); hoja abatible ≈ 0,50 | sección 2 | dejar; opcional 0,65 si es corredizo |
| Escritorio (no existe) | — | ancho mínimo 0,80, recomendado desde 1,00; fondo 0,40 mínimo, 0,50 ideal (Arrevol); 1,20 × 0,48 × 0,75 (Sodimac) | silla 0,50 × 0,50 | agregar [1,20, 0,60] |

### Estar y comedor

| Pieza | Trazo hoy | Pieza real (F) | Recomendación |
|---|---|---|---|
| Sofá de 3 cuerpos | 2,00 × 0,90 | 1,83–2,44, típico 2,13, fondo 0,90–1,00 (dimensions.com); sofá cama 2,04 × 0,85 (Sodimac) | dejar como mínimo; opción [2,10, 0,90] |
| Sofá de 2 cuerpos (no existe) | — | 1,22–1,83 (dimensions.com); 1,50 × 0,94 (Sodimac) | agregar [1,60, 0,90] |
| Butaca | 0,80 × 0,80 | 0,59 × 0,52 a 0,75 × 0,71 (Sodimac) | dejar |
| Rack de TV | 1,60 × 0,45 | 1,80 × 0,43; 1,84 × 0,40; 2,22 × 0,40 (Sodimac); fondo 0,40–0,50; un mueble de 1,65 admite TV de hasta 73 in (dimensions.com) | dejar; opción [1,80, 0,40] |
| Puesto por comensal | 0,60 | mínimo 0,60 × 0,40, recomendado 0,75 × 0,45 (Arrevol); 0,61 × 0,53 mínimo, 0,76 × 0,69 óptimo (dimensions.com) | dejar |
| Fondo de la mesa | 0,90 | 0,80 permite un comensal por lado; habitual 0,90 o 1,00; mesa de 4: 0,86–1,12; de 6: 0,91–1,02 | dejar |
| Mesa de 4 y de 6 | calculada (0,60 × n) | de 4: 1,20–1,40 × 0,80–0,90; de 6: 1,50–1,60 × 0,80–0,90 o redonda Ø 1,10–1,20 (Emmme, vía Neufert, Arrevol) | dejar el cálculo (las mesas reales son algo más cortas) |
| Silla | una línea | se inscribe en 0,50 × 0,50; asiento a 0,45 (Emmme, Arrevol); 0,44 × 0,54 (Sodimac); sentada ocupa 0,40–0,50 desde el borde de la mesa | dibujar como cuadrado de 0,45 (sección 3) |

## 2. Pasos libres

| Dónde | Trazo | Referencia (F) | Recomendación |
|---|---|---|---|
| Lados y pie de cama | 0,60 | 0,60 mínimo y 0,80 con armario al costado (Emmme, vía Neufert); 0,70 en todas direcciones (Arrevol); 0,762 mínimo y 0,914 cómodo (dimensions.com); accesible: 0,90 a un lado de la cama y frente al armario, con giro Ø 1,50 (UNIT 200, 4.11.4.1) | dejar 0,60 como mínimo; probar primero 0,70 en `_combinar`; en tipos `accesible`, 0,90 a un lado y frente al placard |
| Frente al placard | 0,60 (= paso de cama) | 0,80 con armario lateral (Emmme); cómoda 1,07–1,22 (dimensions.com); accesible 0,90 (UNIT 200); una hoja abatible de 0,50 deja ≈ 0,10 con 0,60 | **crear `paso_placard` = 0,80** |
| Mesada, un cocinero | 0,90 | pasillo mínimo 0,914 (NKBA); persona con bandeja 0,85–0,90 (Arrevol); accesible ≥ 0,90 y aproximación 0,80 × 0,85 (UNIT 200) | dejar |
| Mesada con hilera enfrentada | no distingue | un cocinero 1,067, dos o más 1,219 entre frentes (NKBA); vía Neufert 1,20 mínimo; dimensions.com 1,22 | agregar `paso_cocina_doble` = 1,07 (1,22 con dos cocineros) |
| Frente al inodoro / bidé | 0,60 | IRC 0,533; 0,61 mínimo y 0,91 recomendado (dimensions.com); NKBA 0,762; vía Neufert bloque 0,70 × 1,20 | dejar |
| Frente al lavatorio | 0,60 | IRC 0,533; NKBA 0,762; Arrevol 0,70 | dejar; opción 0,70 |
| Frente a la ducha | 0,60 | IRC 0,61; NKBA 0,762; vía Neufert 0,60 (0,50 con vidrio fijo) | dejar |
| Lado de la bañera | — | NKBA 0,762; cómodo 1,12; mínimo 0,56 | 0,76 |
| Entre silla y pared o mueble | 0,75 | para levantarse 0,60–0,75 (Emmme, Arrevol); NKBA 0,813 si nadie pasa, 0,914 para pasar de costado, 1,118 para caminar | dejar 0,75; 0,91 si se circula por detrás |
| Estar (pasos) | 0,90 | tránsito ≥ 0,80, recomendado 0,90–1,00 (Arrevol); NKBA 0,914 | dejar |
| Sofá a TV | 1,50 libres (≈ 2,2 a los ojos) | al menos 2,20 desde el sofá; ≈ 4,50 para 55 in (Emmme, opinión); norma de distancia de visión no encontrada | dejar |
| Frente al lavarropas | 0,60 | sin fuente específica; en cocina, 0,762 × 1,219 junto a cada artefacto (ICC A117.1 vía NKBA); lavavajillas 1,00 (Arrevol) | dejar 0,60; con puerta frontal 0,80 (S) |
| Transferencia, giro y aproximación | 0,80; Ø 1,50 | 0,80 × 1,20; Ø 1,50; lavabo 0,80 × 0,85 frontal (UNIT 200) | dejar |

## 3. Graficación

### 3.1 Convenciones generales

- **Grosores de línea** (serie ISO: 0,13 – 0,18 – 0,25 – 0,35 – 0,50 – 0,70 – 1,00 mm; learnarchitecture.net, no la norma): lo cortado (muros) lleva la línea más gruesa, lo visto bajo el corte (hojas de puerta, mobiliario, antepechos) una intermedia, y rayados, cotas y texturas la más fina; al achicar la escala se baja un escalón y lo fino se borra en vez de adelgazarlo bajo 0,13. Tipos (ISO 128): continua lo visible, discontinua lo oculto, mixta los ejes. **Pesos propuestos** (S): muro cortado 0,70 a 1:50 y 0,50 a 1:100; marco y vidrio cortados 0,50 / 0,35; mobiliario, artefactos y hoja de puerta 0,35 / 0,25; detalles del símbolo, cotas y rayado 0,18 / 0,13; arco de puerta y espacio de uso 0,13 discontinua.
- **Texto:** 2,5 – 3,5 – 5 – 7 mm (ISO 3098 †); 2,5 mm para cotas y rótulos de artefactos, 3,5 mm para nombres de ambiente; **el 1,8 mm no se confirmó**: 2,5 como mínimo. En el modelo, altura = mm × escala / 1000 (2,5 mm = 0,125 m a 1:50 y 0,25 m a 1:100).
- **Escalas** de la planta de obra: 1:50 o 1:100 (UNAM).
- **Puertas:** siempre abiertas; una línea fina marca el recorrido (arco de 90°) y hacia qué lado abre y si pisa un inodoro o un mueble (UNAM, Cedreo); propuesta (S): hoja a 90° con línea de 0,35 y arco fino punteado de radio igual al ancho de hoja.
- **Ventanas:** se cortan marco y vidrio (gruesa) y se ve el antepecho más lejos (UNAM); convención de tres líneas finas paralelas que cruzan el hueco (Cedreo); propuesta: hueco interrumpido en el muro, dos líneas de cara y una central de vidrio, antepecho 0,02–0,05 por dentro de la cara interior.
- **Rayados:** muros con poché sólido a escala chica (a 1:100 alcanza); a 1:50 rayado a 45° (paso: S); patios con contorno de 0,25 y relleno liviano (S). Los rayados de ISO 128-50 / UNE 1032 no se encontraron.
- **Símbolos conocidos** (Cedreo): ducha = cuadrado con X y círculo central; bañera = rectángulo dentro de rectángulo; cocina, lavarropas y heladera con símbolos de electrodomésticos.

### 3.2 Fichas de símbolos (propuesta de diseño, S)

Marco de cada pieza: `s` a lo largo de la pared (0 a A), `n` hacia el interior (0 a F), espalda en n = 0. Clases de línea: **P** contorno de la pieza (0,35 mm a 1:50), **d** detalle (0,18), **u** uso o paso (0,13, discontinua, en capa aparte apagable).

1. **Cama** (A × F, cabecera en n = 0): P rectángulo; d cabecero A × 0,05 contra la pared; d almohadas, k = 1 (individual) o 2 (doble, queen), esquinas de 0,04, ancho = min(0,60; (A − 0,10·(k + 1)) / k), fondo 0,35, a 0,08 de la cabecera, centradas (hoy la individual las tiene de 0,70); d pliegue, línea paralela a la cabecera en n ≈ 0,29·F y diagonal de 0,30 × 0,30 en una punta.
2. **Mesa de luz** (0,45 × 0,40): P rectángulo; d círculo de lámpara Ø ≈ 0,45·min(A, F).
3. **Placard** (A × 0,60): P rectángulo; d barral en n = F/2 de 0,03 a A − 0,03; d perchas, marcas diagonales (± 0,06 en s, ± 0,20 en n) cada 0,25; d frente en n = F partido cada ≤ 0,50 si es abatible (dos líneas a 0,04 si es corredizo); u arcos de 90° de las hojas. Variante «una diagonal»: costumbre de dibujo, sin fuente.
4. **Sofá** (A × F): P rectángulo con esquinas de 0,05; d respaldo A × 0,20 contra la pared; d brazos 0,18 × F; d asientos N = redondeo((A − 0,36) / 0,60), N ≥ 2, con N − 1 divisorias de n = 0,20 a F (hoy, una sola); d almohadones opcionales, cuadrados de 0,40 a 45° en las esquinas.
5. **Butaca** (0,80 × 0,80): como el sofá con N = 1, respaldo 0,18, brazos 0,15.
6. **Mesa con sillas:** P mesa lisa (rectángulo A × F o círculo); sillas, cuadrado de 0,45 con esquinas de 0,05, uno por puesto de 0,60, 0,10 bajo el tablero (línea d) y 0,35 fuera (hoy, una línea suelta a 0,08); u `paso_silla` hacia afuera.
7. **Rack de TV** (A × 0,40–0,45): P rectángulo; d pantalla de s = 0,25 a A − 0,25, n = 0,08 a 0,14.
8. **Escritorio** (1,20 × 0,60): P rectángulo; d silla 0,45 al frente centrada, 0,15 bajo el tablero; d monitor, línea de 0,50 en n = 0,15.
9. **Inodoro** (cuerpo a ≈ 0,40 centrado en el módulo): P depósito a × 0,19 contra la pared; d botón 0,05 × 0,03; P taza, elipse de semiejes a/2 y ≈ 0,255 desde n = 0,19 hasta 0,70; d asiento y tapa, elipse concéntrica a escala 0,72 (hoy, depósito y una elipse).
10. **Bidé** (0,35 × 0,55): P elipse; d elipse interior a 0,70; d grifería, círculo r 0,03 en n = 0,06 con dos de r 0,015 a ± 0,07.
11. **Lavatorio** (0,50 × 0,42; con encimera 0,60–0,70 × 0,45–0,50): P contorno con esquinas de 0,06; d cubeta, elipse a 0,70 en s y 0,65 en n centrada en n = 0,55·F; d grifo r 0,025 en (A/2; 0,12·F).
12. **Ducha** (A × F): P rectángulo; d dos diagonales y desagüe Ø 0,08 al centro (Cedreo); d mampara sobre el borde abierto (u arco de 90° si es abatible). **Ducha a nivel** (1,20 × 0,90): contorno discontinuo, X y desagüe, asiento rebatible 0,40 × 0,45.
13. **Bañera** (1,50–1,70 × 0,70): P rectángulo; d interior retranqueado 0,05 con el pie redondeado (r ≈ 0,20); d desagüe Ø 0,05 a 0,12 del pie; d dos círculos Ø 0,04 en la cabecera.
14. **Cocina de 4 hornallas** (0,60 × 0,60): P rectángulo; d círculos en (0,27·A; 0,30·F), (0,73·A; 0,30·F), (0,27·A; 0,70·F), (0,73·A; 0,70·F) de r 0,09 / 0,07 / 0,07 / 0,05 con uno interior a la mitad; d 4 perillas en n = F − 0,03 (hoy, cuatro círculos iguales). **Anafe:** lo mismo sin cuerpo, 0,59 × 0,51.
15. **Heladera** (0,70 × 0,70): P rectángulo; d diagonal de (0, F) a (A, 0); u opcional, arco de 90° de radio A desde la bisagra.
16. **Lavarropas** (0,60 × 0,60): P rectángulo; d círculo Ø 0,72·min(A, F) y otro interior a 0,5 (puerta del tambor). **Lavavajillas:** P rectángulo, d línea a 0,20 del frente y rótulo «LV». **Secarropas:** como el lavarropas.
17. **Pileta de lavar / bacha:** P rectángulo; d cubeta retranqueada 0,06 con esquinas de 0,03; d desagüe Ø 0,05; d grifo r 0,02 detrás al centro.
18. **Termotanque:** P círculo Ø 0,45 y rótulo «TT».
19. **Círculo de giro:** u círculo Ø 1,50 punteado (ya existe, pieza `giro`). **Espacio de uso:** u rectángulo punteado con el paso de cada pieza, en capa propia apagable.

### 3.3 DXF y Rhino

- **DXF** (hoy R12 solo con ENTITIES y POLYLINE): agregar HEADER con `$INSUNITS` = 6 (metros; `dxf_lector` ya lo lee), TABLES con capas, color y tipo de línea, y una sección BLOCKS (nombre en 2, indicador en 70, punto base en 10/20/30); cada INSERT con nombre, punto, escalas (41/42) y rotación (50); las entidades del bloque en capa «0» para que tomen la de la inserción (el lector de Trazo ya lo entiende). R12 tiene ancho de polilínea (40/41) para dibujar grosor sin lineweights; **HATCH** (desde R13) y el grosor por capa (código 370, desde R2000) no existen en R12: el rayado va con LINE. Capas propuestas: `Trazo_Lnn_Equip_Sanit`, `_Cocina`, `_Dorm`, `_Estar` y `_Pasos`, conservando `Trazo_Lnn_Equipamiento` con polilíneas como opción «sin bloques». Nombres `TRZ_<tipo>[_<ancho>x<fondo>]` (`TRZ_INODORO`, `TRZ_CAMA_140X190`); las piezas que se estiran (placard, mesa, rack) como bloque unitario escalado en X, las de círculos con tamaño fijo. Punto base = esquina trasera izquierda (s = 0, n = 0), x a lo largo de la pared, y hacia el interior; si el marco de la pieza está en espejo (determinante de `es`, `en` negativo), escala Y = −1 y rotación `atan2(es.y, es.x)`. Opcional: ATTRIB con KIND, ROOM, A y F.
- **Rhino** (`trazo_rhino.py`): definir los bloques una vez en `Trazo::Bloques` con el mismo nombre que en DXF y en unidades del documento; crear uno solo si `rs.IsBlock(nombre)` es falso (si el usuario lo redefinió, se respeta); al «Recibir», borrar solo las instancias; insertar con `rs.InsertBlock(nombre, punto, escala, ángulo)` (escala (1, −1, 1) en espejo; verificar en Rhino 8 si hace falta `InsertBlock2` con matriz); instancias en `Trazo::Lnn::Equipamiento::<categoría>`; el usuario reemplaza un bloque con el comando Block y todas las instancias cambian; grosor en el `PlotWeight` de la capa.

## 4. Cambios propuestos (pendientes de decisión)

**`engine/standards.py`, `equipamiento`** (los valores que cambien, a `STD_ANTES` con la versión de corte en la web, como pide CLAUDE.md; cada uno con su fuente en `STANDARDS.md`):
- Revisar `puerta_accesible`: 0,82 → 0,90 de hoja si se quiere la luz libre de 0,80 de la UNIT 200.
- Nuevas: `cama_plaza_y_media` [1,05, 1,90], `cama_queen` [1,60, 2,00], `cama_king` [1,80, 2,00], `sofa_2` [1,60, 0,90], `escritorio` [1,20, 0,60], `banera` [1,50, 0,70] (y 1,70), `anafe` [0,60, 0,52], `horno_empotrado` [0,60, 0,56], `lavavajillas` [0,60, 0,60], `microondas` [0,50, 0,40], `secarropas` [0,60, 0,60]; `paso_placard` 0,80; `paso_cocina_doble` 1,07 (1,22 con dos cocineros); `paso_cama_accesible` 0,90. Opcionales: `termotanque` Ø 0,45; `paso_cama` 0,70 como preferido.
- Sin cambios (coinciden con las fuentes): inodoro, bidé, lavatorio, ducha, heladera, cocina, lavarropas, pileta, camas doble e individual, mesita, placard, butaca, rack, mesa, pasos de estar, silla, baño y cocina, giro y transferencia.

**Web:** redibujar los símbolos con las fichas de 3.2 (silla como cuadrado, sofá con N cuerpos, inodoro con tapa, cama con almohadas acotadas, bañera, hornallas diferenciadas); clases de línea con grosor en milímetros y un selector de escala de impresión (1:50, 1:100); capa «Espacios de uso» apagable; arco de 90° en las puertas y tres líneas en las ventanas.

**DXF y Rhino:** lo de 3.3 (bloques, capas por categoría, INSERT con espejo, definiciones reemplazables, respaldo con polilíneas). **Pruebas:** una por pieza nueva, por cada `paso_*` y por el DXF con bloques (que `dxf_lector` lo relea).

## Fuentes

- [NKBA — Kitchen Planning Guidelines (PDF)](https://kb.nkba.org/uploads/2022/05/Kitchen-Planning-Guidelines.pdf); [NKBA — colocación de artefactos de baño (extracto en Supply House Times)](https://supplyht.com/articles/92491-nkba-placement-of-bath-fixtures) (el PDF de baños de la NKBA dio «Access Denied»)
- [UNIT 200:2021 (copia de la Intendencia de Montevideo, licencia individual)](https://montevideo.gub.uy/sites/default/files/biblioteca/unit2002021.pdf)
- dimensions.com: [camas](https://www.dimensions.com/element/queen-beds), [dormitorio](https://www.dimensions.com/element/queen-bedroom-layouts), [baño](https://www.dimensions.com/element/toilet-clearances), [cocina](https://www.dimensions.com/element/kitchen-cabinetry-clearances), [comedor](https://www.dimensions.com/element/dining-room-clearances), [sofás](https://www.dimensions.com/collection/sofas-couches), [mesas](https://www.dimensions.com/collection/dining-tables), [racks](https://www.dimensions.com/collection/tv-stands-media-consoles), [escritorios](https://www.dimensions.com/collection/desks-work-tables), [placards](https://www.dimensions.com/element/closet-depths)
- Arrevol (cita el Neufert): [50 medidas](https://arrevol.com/blog/50-medidas-que-todo-arquitecto-deberia-saberse-de-memoria/), [aparatos sanitarios](https://arrevol.com/blog/como-dimensionar-correctamente-un-bano-dimensiones-minimas-de-los-aparatos-sanitarios/), [baños](https://arrevol.com/blog/como-dimensionar-correctamente-un-bano-distribuciones-para-banos-y-aseos/), [dormitorio](https://arrevol.com/blog/como-dimensionar-un-dormitorio-medidas-minimas-y-consejos/), [cocina](https://arrevol.com/blog/como-disenar-correctamente-una-cocina-dimensiones-minimas-y-consejos/), [salón-comedor](https://arrevol.com/blog/como-dimensionar-disenar-un-salon-comedor-medidas-minimas-y-consejos/), [armario](https://arrevol.com/blog/como-disenar-un-armario-medidas-minimas-y-recomendadas/)
- [Emmme Interiorismo — medidas y distancias estándar (parte II)](https://www.emmmestudio.com/blogarchivo/2021/12/28/medidas-y-distancias-estndar-a-la-hora-de-disear-parte-ii)
- [Divino Uruguay — fichas de colchones, sommiers y camas](https://www.divino.com.uy/) (1 plaza, 1 ½, 2 plazas, queen y king)
- [Sodimac Uruguay — fichas de producto](https://www.sodimac.com.uy/) (sanitarios Ferrum, bañeras, termotanques, heladeras James, cocinas Enxuta y Smartlife, anafes, hornos, microondas, lavavajillas, lavarropas, secarropas, piletas, muebles)
- [Pliego estatal con la heladera James RJ-65K †](https://www.comprasestatales.gub.uy/Aclaraciones/aclar_llamado_797744_0.pdf)
- [learnarchitecture.net — pesos de línea](https://learnarchitecture.net/articles/39292-architectural-line-weights.html); [UNAM — planos de planta](https://www.ingenieria.unam.mx/luiscr/licenciatura_ic/1407_rc/1407_material/planos.pdf); [Cedreo — símbolos de planos](https://cedreo.com/es/blog/simbolos-planos-casas/); [ISO 128-2 (ficha AFNOR)](https://www.boutique.afnor.org/en-gb/standard/iso-12822022/technical-product-documentation-tpd-general-principles-of-representation-pa/xs142178/335890); resúmenes de UNE 1032 / ISO 3098 (†, no leídos completos)
- Autodesk, referencia DXF: [INSERT](https://help.autodesk.com/cloudhelp/2020/ENU/AutoCAD-DXF/files/GUID-28FA4CFB-9D5E-4880-9F11-36C97578252F.htm), [BLOCKS](https://help.autodesk.com/cloudhelp/2020/ENU/AutoCAD-DXF/files/GUID-9DDFC343-6C87-4AF8-B3B9-77E0AB5A3031.htm), [POLYLINE](https://help.autodesk.com/cloudhelp/2020/ENU/AutoCAD-DXF/files/GUID-ABF6B778-BE20-4B49-9B58-A94E64CEFFF3.htm), [LAYER](https://help.autodesk.com/cloudhelp/2020/ENU/AutoCAD-DXF/files/GUID-D94802B0-8BE8-4AC9-8054-17197688AFDB.htm), [HATCH](https://help.autodesk.com/cloudhelp/2020/ENU/AutoCAD-DXF/files/GUID-C6C71CED-CE0F-4184-82A5-07AD6241F15B.htm)
- McNeel — bloques en RhinoScript: [AddBlock](https://developer.rhino3d.com/api/rhinoscript/block_methods/addblock.htm), [InsertBlock](https://developer.rhino3d.com/api/rhinoscript/block_methods/insertblock.htm), [IsBlock](https://developer.rhino3d.com/api/rhinoscript/block_methods/isblock.htm)
