# Isla de Flores (Près / Adamo-Faiden + Giusto Van Campenhout): nota de la preparación

Fuente: dossier comercial «Isla de Flores» de Près (pres.uy), ©2023, 21 págs. Edificio en Palermo, Montevideo, en la
esquina de Isla de Flores y una calle lateral. Las plantas son vectoriales, a 1:125, y las fichas de las unidades a 1:75.
La escala se verificó con los locales que traen medidas (por ejemplo, el dormitorio de la 203: 3,50 × 3,30 m en la ficha
y en la planta). Precisión **alta**. Nada se midió a ojo, salvo lo que se dice abajo.

## Qué hay

- **Plantas** (`P_`): planta tipo (pisos 2 a 4), piso 1 y planta baja. Cada una tiene su imagen `_comparacion.png` con lo
  dibujado sobre el original:
  - rojo: contornos;
  - naranja: estancias;
  - verde: entradas;
  - azul: ventanas;
  - magenta: puertas;
  - celeste: balcones, patios propios y cocheras.
- **Unidades** (`U_`): las 5 tipologías del dossier.
  - `_01`: 201 (2D pasante). Es igual en 301, 401 y 101.
  - `_02`: 202 (1D en esquina). Es igual en 302, 402 y 102.
  - `_03`: 203 (1D sobre Isla de Flores). Es igual en 303, 403 y 103.
  - `_04`: 204 (1D pasante). Es igual en 304, 404 y 104.
  - `_05`: 001 (monoambiente en PB, con jardín).
  - Las del piso 1 (101 a 104) no tienen archivo propio: son las mismas viviendas sin balcón. Su espacio exterior está en
    la azotea.
- `indice.csv`: se agregaron 8 filas, una por archivo.

## Locales y equipamiento

Se siguieron los mismos criterios que en el Mauá:

- El estar abierto va separado en `Estar`, `Comedor` y `Cocina integrada`, según dónde están el sofá, la mesa y la mesada
  en la ficha.
- Cada estancia lleva su color según el tipo.
- `Trazo_Equipamiento` tiene los muebles y artefactos de la ficha.
  - Se calzó sobre la planta correlacionando los muros, con 93-99 % de coincidencia.
  - Los principales llevan nombre: `Cama 1.40x1.90`, `Sofa`, `Mesa 4`, `Placard`, `Escritorio`, `Mesada`, `Heladera`,
    `Lavarropas`.

## Criterios que conviene revisar

- **001 = `Mono` con un `Dormitorio 1`**. La zona de dormir está separada del estar por un placard, sin muro. El plano
  general la marca «M»; la ficha la vende como «1 dormitorio con patio».
  - Se siguió la convención («Mono si no hay dormitorio cerrado»), con `dormitorios: 0`.
  - La zona se etiquetó `Dormitorio 1` para que se lea en Rhino. Por eso `ver_dxf` avisa que la etiqueta Mono no
    coincide.
  - Si preferís 1D, es cambiar la etiqueta, el nombre del archivo y la fila del índice.
- **Plantas giradas 180°**: Isla de Flores queda arriba. El palier (1,50 × 3,75 m) queda vertical: es corto y no hay
  pasillo largo que poner horizontal.
- **Núcleo**: son dos polígonos en `Trazo_Nucleos`, a cada lado del palier:
  - la escalera, con su vestíbulo y los ductos;
  - el ascensor, con sus ductos.
- **Orientación de las unidades**: la fachada principal va arriba.
  - 203: la entrada queda abajo.
  - 202: la entrada también queda abajo; arriba va la calle lateral e Isla de Flores a la derecha.
  - 201, 204 y 001: se entra por un costado; cada archivo lo explica.
- **Medianera izquierda oblicua** (2,2 cm por metro): se dibujó tal cual, no se enderezó.
- **Planta baja**:
  - Las 5 cocheras van en `Trazo_Cotas`. La 1 y la 4 están dibujadas como espacios de trabajo; la 5 tiene una puerta al
    patio chico de la 001.
  - El hall (palier, pasillo a las cocheras y lobby de la esquina) es el `Trazo_Pasillo`.
  - Junto al lobby hay un local con una cruz; no se sabe qué es.
  - El jardín de la 001 es el patio del edificio (`Trazo_Patios`). En el archivo de la 001 va en `Trazo_Cotas`, con el
    patio chico.
- **Piso 1**: es la planta tipo sin balcones. El dibujo de esa página está corrido 3 cm; corregido eso, el 99,7 % de los
  muros coincide, así que se usaron las medidas de la planta tipo. La PB está corrida unos 6 cm y se midió aparte.
- **Azotea** (pág. 8): no lleva DXF. Es la terraza común con parrillas, más las áreas exteriores asignadas a 101-104.
- **Balcones**: van en `Trazo_Cotas`, como en el Mauá. Las medidas son las del dibujo; las de la carpeta, en
  `observaciones`. Algunas no coinciden: la 203 mide 1,00 × 7,35 y la carpeta dice 1,00 × 6,80.
- **Estimado**: la puerta del dormitorio 2 de la 201. Es un tabique corredizo y el paso se dibujó al medio.
- **Áreas**: los contornos quedan cerca del «área interior» APPCU de la carpeta:

  | Unidad | Diferencia |
  |---|---|
  | 201 | −3,7 % |
  | 202 | −1,9 % |
  | 203 | +4,3 % |
  | 204 | −1,1 % |
  | 001 | −6,2 % |

- **Norte**: el dossier no lo trae.
- **Formato**: igual que el Mauá. DXF AutoCAD 2000 escritos con ezdxf, con los textos en cp1252. Todos pasan por
  `ver_dxf` sin errores y por `ezdxf.recover` sin arreglos.
