# Base de tipologías — resumen (Trazo v2.61)

Se leyeron 67 archivos de `data/tipologias/`: 49 viviendas (44 distintas: las de varios niveles cuentan una vez, con la suma de sus niveles) y 18 plantas enteras. Las superficies son m² con muros (el contorno de la vivienda por el eje de los muros divisorios y la cara exterior de la fachada) y las medidas, metros; cada celda con rango da la mediana y, entre paréntesis, el mínimo y el máximo. El ancho y el fondo de una estancia son los de su caja alineada con los ejes del dibujo (ancho a lo largo de la fachada), de las estancias rectangulares.

## 1. Viviendas por tipología

| Tipología | n | Superficie con muros (m²) | Superficie útil mediana (m²) | Frente mediano (m) | Fondo mediano (m) | Precisión |
|---|---|---|---|---|---|---|
| Mono | 4 | 32,7 (28,6–39,5) | 28,9 | 3,4 | 9,6 | alta 3, media 1 |
| 1D | 18 | 41,7 (35,0–55,2) | 37,0 | 4,4 | 8,9 | alta 12, media 6 |
| 2D | 12 | 61,6 (52,0–80,5) | 54,9 | 8,5 | 7,4 | alta 8, media 4 |
| 3D | 8 | 92,9 (80,5–98,7) | 80,2 | 7,7 | 11,8 | alta 4, media 4 |
| 4D | 2 | 113,1 | 96,1 | 13,4 | 12,0 | media 2 |

## 2. Estancias por tipología

Cada celda: superficie mediana en m² (ancho × fondo medianos en m) y cantidad de estancias medidas (n). Con pocas, la mediana es casi un dato suelto.

| Estancia | Mono | 1D | 2D | 3D | 4D |
|---|---|---|---|---|---|
| Hall | 2,4 (1,2 × 2,5) n=2 | 2,0 (1,2 × 1,4) n=8 | 3,2 (1,3 × 2,1) n=6 | 5,6 (1,5 × 1,9) n=7 | 9,0 (2,8 × 5,4) n=2 |
| Estar | 8,8 (3,4 × 2,2) n=2 | 8,8 (3,2 × 2,8) n=15 | 10,1 (3,2 × 3,1) n=12 | 13,4 (3,6 × 3,6) n=8 | 14,0 (4,2 × 3,3) n=2 |
| Comedor | 6,1 (3,4 × 1,5) n=2 | 6,3 (3,2 × 1,8) n=14 | 6,8 (3,1 × 1,6) n=12 | 8,6 (3,3 × 2,9) n=8 | 9,2 (2,7 × 3,4) n=2 |
| Estar-Comedor | 13,7 (3,1 × 4,4) n=1 | 13,2 (3,5 × 3,8) n=3 | — | — | — |
| Cocina | — | 5,5 (1,6 × 3,4) n=1 | 6,8 (1,6 × 4,2) n=2 | 8,9 (2,0 × 4,5) n=2 | 8,4 (2,2 × 3,9) n=2 |
| Cocina integrada | 3,9 (3,2 × 1,6) n=4 | 3,8 (3,2 × 2,3) n=17 | 7,9 (2,9 × 2,7) n=10 | 5,2 (3,5 × 2,5) n=6 | — |
| Pasillo | 2,2 (0,9 × 2,5) n=1 | 4,7 (0,9 × 1,9) n=7 | 2,4 (2,5 × 1,0) n=8 | 4,2 (2,7 × 2,4) n=9 | 3,5 (3,5 × 1,0) n=2 |
| Dormitorio 1 | — | 10,4 (3,1 × 3,4) n=18 | 13,1 (2,8 × 3,9) n=12 | 13,9 (5,2 × 2,7) n=8 | 14,1 (5,2 × 2,7) n=2 |
| Dormitorio 2 | — | — | 8,7 (2,5 × 3,3) n=12 | 8,6 (4,0 × 2,4) n=8 | 10,8 (4,0 × 2,7) n=2 |
| Dormitorio 3 | — | — | — | 8,2 (4,0 × 2,6) n=8 | 9,8 (4,0 × 2,4) n=2 |
| Dormitorio 4 | — | — | — | — | 9,4 (3,5 × 2,7) n=2 |
| Dormir | 11,9 (3,4 × 3,7) n=3 | — | — | — | — |
| Baño | 4,2 (2,6 × 1,5) n=4 | 3,9 (2,1 × 1,8) n=17 | 4,3 (2,2 × 2,2) n=10 | 4,2 (1,6 × 2,6) n=9 | 3,9 (1,6 × 2,5) n=2 |
| Baño 2 | — | — | — | 5,3 (3,1 × 2,1) n=1 | — |
| Baño en suite | — | 3,8 (2,1 × 1,8) n=1 | 3,7 (1,5 × 2,5) n=2 | 4,0 (1,6 × 2,5) n=4 | 4,0 (1,6 × 2,5) n=2 |
| Toilette | — | 2,1 (2,1 × 1,2) n=1 | 3,1 (1,0 × 1,6) n=3 | 1,9 (1,3 × 1,5) n=2 | — |
| Lavadero | — | 1,2 (0,7 × 1,6) n=1 | — | 1,2 (1,4 × 0,9) n=1 | — |
| Estudio | — | — | 6,9 (2,7 × 2,6) n=1 | — | — |
| Vestidor | — | 4,1 (2,1 × 2,0) n=1 | — | 6,0 (3,5 × 1,9) n=1 | — |

## 3. Plantas

Circulación = (pasillos + núcleos) / planta; eficiencia = viviendas / planta, con planta = terreno menos patios. El ancho del pasillo es el que hay frente a cada puerta de entrada. Un piso sin palier (los niveles superiores de un dúplex) no tiene pasillo.

| Proyecto | Nivel | Viviendas | Núcleos | Viviendas por núcleo | Ancho de pasillo mediano (m) | Circulación (%) | Eficiencia (%) | Planta (m²) |
|---|---|---|---|---|---|---|---|---|
| Aruma | 5 | 5 | 1 | 5,0 | 1,52 | 9,1 | 54,2 | 851,9 |
| Aruma | tipo | 8 | 1 | 8,0 | 1,57 | 9,5 | 67,7 | 863,2 |
| Barrios Amorín | 1 | 2 | 1 | 2,0 | 1,58 | 8,4 | 55,2 | 234,2 |
| Barrios Amorín | tipo | 3 | 1 | 3,0 | 1,60 | 12,1 | 77,9 | 165,9 |
| GR 1591 | 1 | 6 | 1 | 6,0 | 1,50 | 17,7 | 78,0 | 270,1 |
| GR 1591 | tipo | 6 | 1 | 6,0 | 1,21 | 15,0 | 78,0 | 270,1 |
| Isla de Flores | 1 | 4 | 1 | 4,0 | 1,50 | 10,2 | 88,6 | 208,4 |
| Isla de Flores | PB | 1 | 1 | 1,0 | 2,18 | 22,8 | 18,9 | 208,3 |
| Isla de Flores | tipo | 4 | 1 | 4,0 | 1,50 | 10,2 | 88,6 | 208,4 |
| M5 | 1 | 6 | 2 | 3,0 | 1,36 | 12,4 | 83,4 | 338,1 |
| M5 | 4 | 2 | 2 | 1,0 | 1,36 | 11,9 | 31,7 | 362,4 |
| M5 | 5 | 2 | 1 | 2,0 | 1,34 | 14,9 | 74,5 | 153,8 |
| M5 | tipo | 6 | 2 | 3,0 | 1,36 | 11,3 | 75,6 | 372,8 |
| Mauá | 1 | 5 | 1 | 5,0 | 1,50 | 11,9 | 52,8 | 360,3 |
| Mauá | 10 | 3 | 1 | 3,0 | — | — | 57,0 | 211,7 |
| Mauá | 2 | 5 | 1 | 5,0 | — | — | 72,8 | 287,2 |
| Mauá | 9 | 3 | 1 | 3,0 | 1,50 | 18,7 | 44,2 | 273,1 |
| Mauá | tipo | 5 | 1 | 5,0 | 1,50 | 13,9 | 74,1 | 287,2 |
| **Mediana** (con palier) |  |  |  | 3,5 | 1,50 | 12,0 | 74,3 |  |

Núcleo (escalera + ascensor + ductos, sin el palier, que va en el pasillo): 21 medidos, de 13,7 m² como mediana y una caja de 6,1 × 3,3 m (lado mayor × lado menor). Ancho de pasillo de todas las puertas: 1,50 (1,21–2,18) m (68 puertas). Hay 16 plantas con palier de 18; cada nivel cuenta una vez, aunque dos niveles de un proyecto sean casi iguales.

## 4. Comparación con `standards.py` y `REFERENCIAS.md`

### 4.1 Superficie de la vivienda

Medida: mediana de la superficie con muros. «Norma» es `vivienda.superficie_min` (norma nacional, art. 3) y «ANV», `vivienda.rango_vivienda`; «Propuesta» es la de `REFERENCIAS.md` (sección 2); «Mix del motor» es el área del tipo con esos dormitorios en `DEFAULT_PARAMS["unit_mix"]`. `standards.py` no tiene un típico por tipología.

| Tipología | n | Medida (m²) | Norma (m²) | ANV (m²) | Propuesta (m²) | Mix del motor (m²) | Medida / propuesta | Frente × fondo medido (m) | Frente × fondo propuesto (m) |
|---|---|---|---|---|---|---|---|---|---|
| Mono | 4 | 32,7 | 32 | 25–40 | 30 | 33 | +9 % | 3,4 × 9,6 | 5 × 6 |
| 1D | 18 | 41,7 | 32 | 35–50 | 42 | 42 | -1 % | 4,4 × 8,9 | 6 × 7 |
| 2D | 12 | 61,6 | 44 | 50–75 | 58 | 62 | +6 % | 8,5 × 7,4 | 8 × 7,25 |
| 3D | 8 | 92,9 | 56 | 65–100 | 78 | 93 | +19 % | 7,7 × 11,8 | 10,5 × 7,4 |
| 4D | 2 | 113,1 | 68 | 80–125 | 100 | — | +13 % | 13,4 × 12,0 | 12,5 × 8 |

### 4.2 Estancias

Medida: mediana de todas las tipologías juntas. Típico y mínimo, de `engine/standards.py` (`vivienda.<clave>`): el área de `typ_area` (o frente × fondo de `typ`), `typ` como frente × fondo y `min_area`; «Tope» es `max_area` (la cocina integrada se dibuja con 5 m² como máximo).

| Estancia | n | Medida (m²) | Típico (m²) | Medida / típico | Mínimo (m²) | Tope (m²) | Medida ancho × fondo (m) | Típico frente × fondo (m) | Clave |
|---|---|---|---|---|---|---|---|---|---|
| Dormitorio 1 | 40 | 11,8 | 11,5 | +3 % | 8,5 | — | 3,2 × 3,4 | 3,2 × 3,6 | vivienda.dorm_principal |
| Dormitorio 2 | 22 | 8,9 | 9,0 | -2 % | 7,0 | — | 3,1 × 2,7 | 2,8 × 3,2 | vivienda.dorm_secundario |
| Dormitorio 3 | 10 | 9,3 | 9,0 | +4 % | 7,0 | — | 4,0 × 2,6 | 2,8 × 3,2 | vivienda.dorm_secundario |
| Cocina | 7 | 8,3 | 7,0 | +19 % | 4,0 | — | 2,0 × 3,9 | 2,4 × 2,9 | vivienda.cocina |
| Cocina integrada | 37 | 5,0 | — | — | 3,0 | 5,0 | 3,1 × 2,4 | — | vivienda.cocina_integrada |
| Baño | 42 | 4,2 | 4,0 | +4 % | 3,0 | 6,0 | 2,1 × 2,0 | 1,7 × 2,4 | vivienda.bano |
| Baño en suite | 9 | 3,8 | 4,0 | -6 % | 3,0 | 6,0 | 1,6 × 2,5 | 1,7 × 2,4 | vivienda.bano |
| Toilette | 6 | 2,3 | 2,6 | -12 % | 1,5 | 4,0 | 1,0 × 1,5 | 1,2 × 2,2 | vivienda.bano_aux |
| Lavadero | 2 | 1,2 | 2,5 | -52 % | 1,5 | 4,0 | 1,1 × 1,2 | 1,2 × 2,1 | vivienda.lavadero |
| Hall | 25 | 3,0 | 2,5 | +21 % | — | — | 1,3 × 1,7 | 1,4 × 1,8 | vivienda.hall |
| Estudio | 1 | 6,9 | 8,0 | -13 % | 7,0 | — | 2,7 × 2,6 | 2,6 × 3,1 | vivienda.estudio |
| Vestidor | 2 | 5,0 | 3,0 | +68 % | 3,0 | — | 2,1 × 2,0 | 2 × 1,5 | vivienda.vestidor |

### 4.3 Estar-comedor

Estar + comedor (y, en el monoambiente, la zona de dormir: el motor la dibuja dentro del «Estar-Dormitorio») por vivienda, comparado con `vivienda.estar_por_dorms`.

| Tipología | n | Medida (m²) | `estar_por_dorms` (m²) | Medida / motor |
|---|---|---|---|---|
| Mono | 4 | 18,1 | 18,0 | 0 % |
| 1D | 18 | 14,5 | 15,0 | -4 % |
| 2D | 12 | 17,3 | 18,0 | -4 % |
| 3D | 8 | 21,2 | 21,0 | +1 % |
| 4D | 2 | 23,2 | 24,0 | -3 % |

### 4.4 Plantas y parámetros del motor

Parámetros por defecto de `engine/layout.py`. El núcleo del motor es el de un ascensor y 3,0 m de piso: la caja de `standards.core_size` partida en sus piezas con `programs.core_parts`, con la escalera perpendicular al pasillo (giro 0) o a lo largo (giro 90).

| Medida | Motor | Base de tipologías |
|---|---|---|
| Ancho del pasillo común (m) | 1,5 (`corridor_width`); norma 1,2 / 1,4 / 1,6 | 1,50 (1,21–2,18) |
| Núcleo del motor sin palier (escalera + ascensor + ductos), superficie (m²) | 19,5 con giro 0; 16,7 con giro 90 | 13,7 |
| Núcleo del motor con palier (`core_size`), superficie (m²) | 23,3 con giro 0; 26,2 con giro 90 | — (el palier está en `Trazo_Pasillo`) |
| Caja del núcleo sin palier (m) | 4,9 × 4,6 con giro 0; 7,1 × 3,6 con giro 90 | 6,1 × 3,3 (lado mayor × lado menor) |
| Frente mínimo de la vivienda (m) | 3,5 (`min_unit_width`) | 3,20; 4 de 44 viviendas están por debajo |
| Fondo máximo de la vivienda (m) | 16,0 (`max_unit_depth`) | 15,92 |
| Viviendas por núcleo | — | 3,5 (1,0–8,0) |
| Circulación (%) | — | 12,0 (8,4–22,8) |
| Eficiencia (%) | — | 74,3 (18,9–88,6) |

Sobre el núcleo: `Trazo_Nucleos` es escalera + ascensores + ductos y el palier de los ascensores va en `Trazo_Pasillo`, así que la circulación medida (12 %) sí incluye el palier y el núcleo del motor se compara sin él. La base pone la escalera a lo largo del pasillo, como el giro 90 del motor: su caja (6,1 × 3,3) se parece más a la del giro 90 (7,1 × 3,6) que a la del giro 0 (4,9 × 4,6).

---

_Generado por `python -m engine.tipologias`; no editar a mano._
