# Referencias de mercado — medidas de apartamentos y mix de tipologías

Investigación del 13 de octubre de 2026 para fijar los **valores predeterminados** de Trazo: cuánto mide un apartamento estándar de cada tipología (superficie, frente y fondo, estancias) y qué mix de tipologías conviene proponer en un proyecto de desarrollo. Complementa a `STANDARDS.md` (mínimos normativos y típicos del motor): aquí van datos de mercado y de otras guías de diseño, no exigencias.

Cómo leer las cifras:
- **(F)** dato tomado de la fuente citada. **(D)** derivado por nosotros a partir de cifras de la fuente (una división, un resto). **(S)** síntesis o criterio propio, sin fuente. **(†)** tomado del resumen de un buscador, sin abrir la página: menos peso.
- Las superficies de Uruguay son **habitables** (concepto legal de la Vivienda Promovida: pisos, circulación interna y muros exteriores hasta 0,20 m; divisorios a eje; sin terrazas ni balcones): comparables con la «superficie con muros» de Trazo (`area_muros`). Las del Reino Unido y Australia son interiores, sin el muro perimetral; las de EE. UU. son promedios de alquiler de todo el parque.
- Lo que no se encontró se dice; no se inventó. Fuentes al final.

## 1. Qué dice la ley en Uruguay sobre la superficie de cada tipología

| Norma | Qué fija |
|---|---|
| Ley 13.728, art. 18 A (redacción de la Ley 19.996 de 2021) (F) | Superficie habitable mínima: 25 m² (monoambiente), 35 m² con un dormitorio y 15 m² más por cada dormitorio adicional (50, 65 y 80 m² con 2, 3 y 4) |
| Decreto 355/011, art. 5 (redacción del Decreto 129/020) (F) | Vivienda Promovida (Ley 18.795): monoambiente de 25 a 40 m²; con dormitorios, de 35 a 125 m² según la cantidad de dormitorios. Antes: 32 a 107 m² (2011 y Decreto 34/017), 35 a 125 (Decreto 249/018), y el monoambiente entra en 2020 |
| Tabla de la ANV «Áreas vigentes según dormitorios» (F) | Mínimas 25 / 35 / 50 / 65 / 80 m² y máximas 40 / 50 / 75 / 100 / 125 m² para 1 ambiente / 1 / 2 / 3 / 4 dormitorios. **Es la tabla que ya usa Trazo** (`vivienda.rango_vivienda`; la ficha avisa «fuera del rango de referencia ANV») |
| Reglamentación de la Ley 18.795 (MVOTMA, texto de abril de 2020) (F) | Los monoambientes no pueden pasar del **25 % de las viviendas promovidas** del proyecto (art. 6 A). Su tabla de áreas (art. 10: 25/35/45/56/68 a 45/55/75/100/120) es anterior a la vigente y quedó superada por la de la ANV |
| Normativa Nacional de Edificación 2016, art. 3 (F) | Mínimo higiénico nacional, otro concepto: 32 m² con 1 dormitorio y 12 m² más por dormitorio (`vivienda.superficie_min` = [32, 32, 44, 56, 68]). La ordenanza de Río Negro alojada en ANII pide 32 + 15 por dormitorio: es departamental, no la norma nacional |

Riesgo a tener en cuenta: un proyecto de ley de 2026 (senador Gustavo González) pediría 35 m² mínimos y un dormitorio separado en la Vivienda Promovida; en julio de 2026 seguía en discusión en el Senado y los promotores dicen que ya frena inversión. La tipología monoambiente tiene que seguir siendo configurable.

## 2. Medidas de referencia por tipología

| Tipología | Rango legal Vivienda Promovida | Mercado de Vivienda Promovida, Uruguay (D) | Reino Unido, NDSS (F) | Australia NSW, ADG (F) | EE. UU., parque de alquiler 2024 (F) | **Propuesta para Trazo** (S): área con muros y frente × fondo en crujía doble |
|---|---|---|---|---|---|---|
| Monoambiente | 25–40 m² | ≈ 30 m² | 37–39 m² (37 con ducha en vez de bañera) | 35 m² | 42,5 m² (457 sf) | **30 m²** (26–35); 5,0 × 6,0 m |
| 1 dormitorio | 35–50 m² | ≈ 40–41 m² | 50 m² (1b2p) | 50 m² | 68 m² (735 sf) | **42 m²** (36–48); 6,0 × 7,0 m |
| 2 dormitorios | 50–75 m² | ≈ 54–55 m² | 61 m² (2b3p) / 70 m² (2b4p) | 70 m² | 102 m² (1.097 sf) | **58 m²** (52–68); 8,0 × 7,25 m |
| 3 dormitorios | 65–100 m² | ≈ 75–77 m² | 74 m² (3b4p) / 86 m² (3b5p) | 90 m² | 124 m² (1.336 sf) | **78 m²** (70–90); 10,5 × 7,4 m |
| 4 dormitorios | 80–125 m² | no encontrado | 90 m² (4b5p) | 102 m² (90 + 12 por el cuarto dormitorio) | — | **100 m²** (90–110); 12,5 × 8,0 m |

- **Mercado (D):** precio medio de venta por tipología de la Vivienda Promovida en 2023 (ANV, informe de precios n.º 43: monoambiente USD 84.721, 1 dormitorio 112.999, 2 dormitorios 153.107, 3 dormitorios 212.941) dividido por el precio por m² habitable (USD 2.826 en el país; 2.778 en Montevideo). Es una estimación gruesa: el precio por m² sube en las unidades chicas, así que sus superficies reales son algo menores.
- **Superficie media de lo vendido** en Montevideo (Vivienda Promovida, m² construidos con cuota de bienes comunes): 68 m² en 2015, 59 en 2023 y **58 en 2025** (ANV). Sirve para calibrar: con el mix «Inversor» de la sección 4 y las superficies propuestas, la media sale ≈ 59 m² (D).
- **Buenos Aires:** la obra nueva está en 45–50 m² en casi todos los barrios (≈ 47 m² en pozo); la mediana bajó de 60–62 m² a 46 m² desde 2010 (Mirando.ai vía Ámbito, 2026). Zonaprop usa como unidades de referencia 40 m² + 4 de balcón (monoambiente), 50 (2 ambientes) y 70 (3 ambientes).
- **Fondo de la vivienda:** NSW limita la profundidad de un ambiente a 8 m desde la ventana y las viviendas con una sola orientación a 8 m de fondo (F); en EE. UU. las fuentes (débiles) dan 9,1–12,2 m de fondo y edificios de ≈ 20 m de espesor. Fondo total de crujía doble con 6,5–8,0 m por lado y pasillo de 1,5–2,0: **14,5–18 m** (S). En Trazo, `max_unit_depth` = 14 m es un tope, no un valor típico; el fondo típico que proponen las medidas de arriba es **7,0–7,5 m**.
- **No se encontró** ninguna fuente que dé frente y fondo de viviendas por tipología (ni Neufert ni Metric Handbook en línea): los frentes de la tabla son el área sobre un fondo de 6–8 m (S), con 5,0 m como mínimo (`min_unit_width`).

### Estancias

| Estancia | Trazo hoy (`standards.py`: mínimo NNE / típico) | Otras referencias (F) |
|---|---|---|
| Dormitorio principal | 8,5 m², lado 2,60 / 11,5 m² (3,20 × 3,60) | Reino Unido: 11,5 m² doble, ancho ≥ 2,75 m (los demás dobles, ≥ 2,55). Chile DS 49 (social): 7,20 m², ancho 2,60; accesible 10,5 m², ancho 3,00 |
| Dormitorio secundario | 7,0 m², lado 2,00 / 9,0 m² (2,80 × 3,20) | Reino Unido: 7,5 m² simple, ancho ≥ 2,15. Chile: 7,0 m², ancho 2,20 |
| Estar-comedor | 10,0 m², lado 2,60 / 20 m²; por dormitorios [18, 18, 20, 24, 27] (`estar_por_dorms`) | NSW: ancho del estar ≥ 3,6 m (monoambiente y 1 dormitorio) y ≥ 4,0 m (2 y 3). Chile: 9,4 m², ancho 2,10 (mesa de 4 y sofá). Cataluña: estar + comedor + cocina ≥ 20 m² y ≥ 4 m² por persona |
| Cocina | 4,0 m², lado 1,60 / 7,0 m² (2,40 × 2,90) | Chile: 4,0 m² (5,0 con lavarropas), ancho 1,30. Brasil MCMV: ancho ≥ 1,60 |
| Baño | 3,0 m², lado 1,20 / 4,0 m² (1,70 × 2,40) | Chile: 2,5 m² (3,5 con lavarropas), ancho 1,10. NSW: + 5 m² de vivienda por cada baño adicional |
| Lavadero | 1,5 m², lado 0,90 / 2,5 m² | Chile: logia de 2,0 m², ancho 1,10 |
| Guardado | placards dentro del dormitorio | Reino Unido: 1,0 / 1,5 / 2,0 / 2,5 m² empotrados según tipología (un placard cuenta en el dormitorio hasta 0,72 m²). Chile: módulo de 1,00 × 0,60 m aparte del dormitorio |

Presupuesto de superficies por tipología (S, m² con muros; sirve para comprobar que el plano del motor «cierra»):
- Monoambiente de 30 m²: ambiente único con kitchenette ≈ 19, baño 3, hall 2, placard 1,5, muros ≈ 3.
- 1 dormitorio de 42 m²: dormitorio 10–11, estar-comedor 14–15, cocina 4–5, baño 3,5, lavadero o placard 2.
- 2 dormitorios de 58 m²: principal 10–11, secundario 8–9, estar-comedor 16–17, cocina 5–6, baño 3,5–4, lavadero 1,5–2.
- 3 dormitorios de 78 m²: principal 11,5, secundarios 9–10 y 8–9, estar-comedor ≈ 20, cocina 6–7, baño 4 + auxiliar 2,5, lavadero 2.

## 3. Mix de tipologías: qué se construye y qué se vende

### 3.1 Uruguay (Vivienda Promovida, Ley 18.795)

| Universo (fuente, año) | Monoambiente | 1 dormitorio | 2 dormitorios | 3 o más |
|---|---|---|---|---|
| Aprobadas 2011–2018, ≈ 16.200 (ANV vía El Observador, 2026) | 0 (no existía) | ≈ 34 % (D) | ≈ 55 % | 3 dorm. ≈ 10 % (D) |
| Aprobadas 2020–2025, 28.703 (ídem) | 9,2 % (D) | 51,1 % | 32,9 % | ≈ 6,8 % (D) |
| Acumulado 2011–2026, 49.325 (ídem) | mono + 3 o más = 13,8 % (D) | 45,5 % | 40,7 % | 4 dorm. 0,5 % |
| Aprobadas abr 2020 – dic 2024, 22.706 (FADU, Del Castillo y Lamoglie, vía El Observador, 2025) | 10 % | 51,4 % (D) | — | — |
| **Vendidas 2025**, 3.174 (ANV vía El Observador, 2026) | — | 51,9 % | ≈ 30,4 % (D) | resto 17,7 % (mono + 3 o más) |
| Vendidas 2024, 3.607 (ídem) | — | 52,3 % | 31,2 % (D) | — |
| Vendidas 2021–2025 (ídem) | — | 52,5 % | 32 % | — |

- Los 2 dormitorios pasaron de ≈ 60 % de lo aprobado en 2013 a 32–35 % en 2024–2025; los 3 o más, de 11 % en 2012 a 8,8 % en 2025. Hasta 2020 la mitad de las unidades de un proyecto tenía que ser de 2 dormitorios o más; desde 2020 el 1 dormitorio no tiene límite y el monoambiente entró con tope del 25 %.
- La cuota vendida coincide con la aprobada (1 dormitorio: 51,9 % vendido, 51,1 % aprobado): no hay señal de sobreoferta de una tipología. Montevideo concentra el 79,7 % de las ventas; barrios con más ventas: Cordón 26,6 %, Tres Cruces 9,4 %, Centro 6,9 %, Barrio Sur 5,7 %, Palermo 5,2 % (ANV, informe n.º 49, 2026).
- Stock al cierre de 2025: 28.233 viviendas terminadas, 13.151 en obra y 5.124 en proyecto (ANV vía El Observador).

**Demanda en InfoCasas (informe 2025):**

| Búsquedas de apartamentos | Monoambiente | 1 dormitorio | 2 dormitorios | 3 o más |
|---|---|---|---|---|
| Para comprar | 23 % | 42 % | 27 % | 8 % |
| Para alquilar | 17 % | 44 % | 29 % | 8 % (3) + 2 % (4 o más) |

Perfil del monoambiente (encuesta InfoCasas a más de 15.000 usuarios, 2026): entre los compradores, 52 % invierte y 48 % lo habita; el 91 % de los inquilinos lo usa como vivienda y el 79 % vive solo; el 54 % tiene entre 26 y 40 años. El 29,2 % de los hogares uruguayos es unipersonal (Censo 2023). Se buscan sobre todo en Cordón, Centro, Punta Carretas, Pocitos y La Blanqueada.

### 3.2 Precios y rentas

| Tipología | Precio medio de venta 2025 (ANV, n.º 49) | Rango de proyectos (InfoCasas 2025) | Alquiler mediano 2025, Centro–Cordón–Palermo / Pocitos–Malvín (InfoCasas, UYU por mes) |
|---|---|---|---|
| Monoambiente | USD 94.473 (+4 %) | USD 90–110 mil | 19.000 / 22.900 |
| 1 dormitorio | USD 123.551 (+3 %) | USD 110–150 mil | 24.000 / 29.000 |
| 2 dormitorios | USD 161.885 (+0,4 %) | USD 150–250 mil | 27.500 / 39.000 |
| 3 dormitorios | USD 279.432 (+27 %) | más de USD 250 mil | — |

- Precio por m² construido en Montevideo, 2025: USD 2.375 (2.420 en el segundo semestre, máximo de la serie; Prado 2.828, Reducto 1.757). Entre 2016 y 2025 el tamaño medio bajó de 67 a 58 m² y el precio por m² subió 32 % (ANV).
- **El precio por m² por tipología no lo publica la ANV.** En Buenos Aires sí se mide: el monoambiente vale ≈ 10 % más por m² que el 2 ambientes (USD 2.240 contra 2.039; Roomix vía Ámbito, 2026), porque cocina y baño son costos fijos repartidos en menos superficie y el ticket bajo atrae al primer comprador y al inversor.
- Rentabilidad bruta (D, con precios ANV 2025 y alquileres del centro a 40 UYU/USD): monoambiente ≈ 6,0–6,3 %, 1 dormitorio ≈ 5,8–6,2 %, 2 dormitorios ≈ 5,1–5,5 %. Solo vale la dirección: baja con el tamaño. En Buenos Aires, 5,7 % y 5,4 % (Ámbito, 2026). El salto de alquiler de 1 a 2 dormitorios es + 15 % en el centro y + 59 % en Punta Gorda–Carrasco.
- Absorción y días en mercado por tipología: no encontrado (solo 27 días de promedio para alquilar, sin desglose).

### 3.3 Buenos Aires

- El monoambiente es el 28 % de las unidades a estrenar en CABA, contra 13 % del stock usado (Roomix vía Ámbito, 2026), o el 35 % de lo que se construye (38 % en el norte, 19 % en el sur; Mirando.ai vía Infobae y Ámbito, 2026, con 53.424 avisos). Las dos cifras difieren por base y método.
- Oferta de alquiler 2024: monoambientes 32,2 % (25,3 % en 2023), 2 ambientes 43,2 % (IDECBA †). Precios medios, nov 2024: monoambiente USD 102.418, 2 ambientes 122.898, 3 ambientes 169.057 (Zonaprop †).
- Hay voces de sobreoferta de monoambientes (Castelli, Punto Uno, vía Ámbito 2026). Porcentajes de 2 y 3 ambientes en obra nueva: no encontrado.

### 3.4 Internacional

| País / fuente (año) | Mix real o recomendado | Tipo |
|---|---|---|
| EE. UU., Census, unidades multifamiliares terminadas en 2025 (484.000) | 1 dorm. 42 %; 3 o más 10 %; estudios + 2 dorm. 48 % (D). Mediana 93 m² en alquiler y 109 m² en venta | Real |
| EE. UU., KTGY y CoStar vía WealthManagement | De ≈ 50/50 entre 1 y 2 dormitorios antes de 2008 a ≈ 65/35 hoy. Vacancia de los 1 dormitorio más chicos ≈ 5,0 % contra 5,5 % en los grandes (3,0 % contra 3,5 % en centros urbanos) | Real, renta |
| EE. UU., estudio de mercado de Germantown, Wisconsin † | Estudios 5–15 %, 1 dorm. 45–55 %, 2 dorm. 35–45 %, 3 dorm. 0–10 % | Recomendado, renta |
| EE. UU., proyecto en Newton, Massachusetts † | ≈ 6 % estudios, 55 % 1 dorm., 28 % 2 dorm., 11 % 3 dorm. | Proyecto |
| Canadá, RENX | Estudios + 1 dorm.: 45,5 % antes de 2012 y 54,4 % después †; Toronto exige 10 % de 3 dormitorios en alquiler nuevo. En edificios de 50 o más unidades, más de la mitad son de 1 dormitorio | Real y normativa |
| Reino Unido, Camden (Dwelling Size Priorities) † | Vivienda de mercado: prioridad alta a 2 y 3 dormitorios, baja a estudios y 1 dormitorio | Normativa |
| Chile, Colliers, Santiago, stock nuevo, 1.er trimestre de 2024 | 2 dorm./2 baños 33 % (39 % cinco años antes); 1 dorm./1 baño 31 % (21 %); juntos 64 % | Real, venta |

La regla «10–20 % estudios, 50–60 % 1 dormitorio, 25–35 % 2 dormitorios, 5 % 3 dormitorios» que circula en EE. UU. no apareció respaldada por una fuente única; los rangos hallados son parecidos. Para el London Plan, España (promotoras) y Chile (GfK, TocToc, DS 19) no se encontraron porcentajes.

### 3.5 Según destino y barrio (reglas con fuente)

- **Inversión y renta en el centro** (Cordón, Centro, Tres Cruces, Palermo, La Blanqueada, Aguada, Unión, Parque Rodó; cerca de la Udelar o de un eje de transporte): manda el ticket de entrada (USD 95–160 mil): monoambiente y 1 dormitorio (InfoCasas 2025, ANV 2026). El monoambiente funciona donde hay universidades y transporte (8.747 estudiantes del interior ingresaron a la Udelar en 2024); en EE. UU. solo en zonas de renta muy alta, casi nada en suburbios (RENX).
- **Usuario final y barrios residenciales** (Pocitos, Malvín, Buceo, Punta Gorda, Carrasco, Prado, Ciudad de la Costa): 2 y 3 dormitorios, USD 200–290 mil; en Punta Gorda–Carrasco el 2 dormitorios alquila + 59 % sobre el 1 dormitorio. Camden prioriza 2 y 3 dormitorios; Toronto exige 10 % de 3.
- **Proyectos para hogares de menor ingreso:** predominan las unidades familiares (RENX).
- **Vivienda Promovida:** monoambientes hasta el 25 % del proyecto; si prospera el proyecto de ley, 35 m² mínimos y dormitorio separado.

## 4. Mixes propuestos para Trazo

Superficies en m² con muros (comparables con la «superficie con muros» de la ficha), dentro del rango de la ANV.

| Mix | Monoambiente | 1 dormitorio | 2 dormitorios | 3 dormitorios | Superficies (mono / 1 / 2 / 3) | Fundamento |
|---|---|---|---|---|---|---|
| **Equilibrado** (propuesto por defecto) | 5 % | 45 % | 40 % | 10 % | 30 / 42 / 60 / 82 | Calza con el acumulado 2011–2026 de la Vivienda Promovida (1 dorm. 45,5 %, 2 dorm. 40,7 %, resto 13,8 %) y con los rangos de EE. UU.; acota el riesgo del monoambiente |
| **Inversor / renta** | 10 % | 55 % | 30 % | 5 % | 28 / 40 / 58 / 78 | Replica lo aprobado 2020–2025 y lo vendido en 2025 (mono 9–10 %, 1 dorm. 51–52 %, 2 dorm. 31–33 %, 3 o más ≈ 7 %); superficie media ≈ 59 m² contra 58 real (D) |
| **Familiar / venta** | 0 % | 25 % | 55 % | 20 % | — / 45 / 65 / 90 | Hipótesis (S) con evidencia indirecta: 2011–2018 (1 dorm. 34 %, 2 dorm. 55 %, 3 dorm. 10 %), Camden y Toronto |

Cómo elegir: 1) destino (inversor con renta → Inversor; usuario final → Familiar); 2) barrio (centro y ejes de transporte → Inversor; barrios residenciales → Familiar; mixto o en duda → Equilibrado); 3) ticket objetivo (hasta USD 160 mil por unidad → Inversor; USD 160–300 mil → Equilibrado o Familiar); 4) si el proyecto va a Vivienda Promovida, avisar cuando el monoambiente pase del 25 % o quede por debajo de 35 m².

Comparación con el mix predeterminado de hoy (`unit_mix` = 2 dormitorios de 75 m² y 3 dormitorios de 95 m², 50 % cada uno): está en el máximo legal de la ANV para 2 dormitorios y cerca del máximo para 3, sin unidades chicas; es un mix «familiar de gama alta», no el de mercado. El mix «Inversor» pone ≈ 40 % más puertas por m² de planta que el «Familiar» (superficie media 46 contra 65 m²), lo que presiona la cantidad de núcleos por evacuación (D).

## 5. Métricas de edificio

| Métrica | Valor de referencia | Fuente |
|---|---|---|
| Eficiencia (vendible / bruta) | ≈ 0,79 en Montevideo y en el país, 0,81 en Canelones, 0,73 en Maldonado (habitable / construida computada, D con ANV 2025); ≈ 80 % en promociones plurifamiliares (Tinsa, España †) | ANV n.º 49; Tinsa |
| Pasillo común | ≥ 1,20 m (MVOT, estándares de desempeño, art. 61 a; la NNE art. 35 pide 1,20 / 1,40 / 1,60 según viviendas y 2,00 en tramos rectos de más de 15 m, ver `STANDARDS.md`); 1,52–1,83 m como cómodo (Archgyan, fuente débil). Trazo: 2,00 m por defecto | MVOT; NNE |
| Viviendas por núcleo | hasta 8 por pasillo de crujía doble (NSW, documento de planificación; confianza media). Sin referencia uruguaya | NSW |
| Ascensor | obligatorio con acceso a más de 9 m de altura (MVOT, art. 58) | MVOT |
| Superficie media por unidad | 58 m² construidos en Montevideo (2025); 45–50 m² en CABA (2026); 93 m² en alquiler en EE. UU. (2025) | ANV; Mirando.ai; Census |
| Vacancia según tamaño | las unidades más chicas tienen ≈ 0,5 puntos menos de vacancia (CoStar) | WealthManagement |

No se encontró literatura académica sobre mix óptimo y rentabilidad; lo más cercano es el estudio cualitativo de la FADU (2025) y la nota de CoStar sobre vacancia.

## 6. Qué aplicar en Trazo (propuesta, pendiente de decisión del usuario)

1. **Mix predeterminado «Equilibrado»** con cuatro tipos (Mono 30 / 1 dorm. 42 / 2 dorm. 60 / 3 dorm. 82 m²; 5 / 45 / 40 / 10 %) en `DEFAULT_PARAMS["unit_mix"]` (`engine/layout.py`) y en el `mix` inicial de `web/index.html`. Cambia las métricas de todos los ejemplos a propósito: `python tests/regresion.py --actualizar` y la tabla en el PR. (M, motor + web.)
2. **Mixes preestablecidos en la web** (Viviendas → selector «Equilibrado / Inversor / Familiar / Personalizado»): carga los porcentajes y superficies de la sección 4 en el mix editable. (S, solo web.)
3. **Aviso de Vivienda Promovida** (casilla en Normativa): monoambientes por encima del 25 % del mix o con superficie objetivo menor de 35 m², además del aviso por vivienda que ya existe («fuera del rango de referencia ANV»). (S, motor.)
4. **Resumen:** mostrar la superficie media por vivienda (con muros) para compararla con los 58 m² de referencia. (S, web.)
5. **Fondos:** dejar `max_unit_depth` = 14 m como tope y anotar en `STANDARDS.md` el fondo típico de 7,0–7,5 m; no cambia el motor.
6. **Estancias:** los típicos actuales (`typ_area`, `estar_por_dorms`) quedan dentro de las referencias; no se cambian. El estar de 18 m² para monoambiente y 1 dormitorio está en el extremo alto: revisar con los planos reales del motor en la tipología de 30 y 42 m².

Decisiones que quedan para el usuario: qué mix va por defecto (Equilibrado o Inversor), si el monoambiente se incluye por defecto (riesgo del proyecto de ley) y los nombres de los tipos («Mono», «1 dorm», «2 dorm», «3 dorm»).

## Fuentes

Uruguay
- [Ley 13.728, art. 18 (IMPO)](https://impo.com.uy/bases/leyes/13728-1968/18)
- [Decreto 355/011, art. 5, versión vigente (IMPO)](https://impo.com.uy/bases/decretos/355-2011/5)
- [ANV — Áreas vigentes según dormitorios](https://www.anv.gub.uy/sites/default/files/2020-07/AREAS_VIGENTES_SEGUN_DORM.pdf)
- [ANV — Reglamentación de la Ley 18.795 (MVOTMA, abril de 2020)](https://www.anv.gub.uy/sites/default/files/2020-04/Reglamentacion_Ley_18795_-_MVOTMA.pdf)
- [ANV — Informe de precios de viviendas promovidas n.º 43 (febrero de 2024)](https://www.anv.gub.uy/sites/default/files/2024-02/INFORME_DE_PRECIOS_AL_01_01_2024.pdf)
- [ANV — Informe de precios de viviendas promovidas n.º 49 (enero de 2026)](https://www.anv.gub.uy/sites/default/files/2026-05/INFORME_DE_PRECIOS_202601.pdf)
- [MVOT / DINAVI — Estándares de desempeño y requisitos](https://www.gub.uy/ministerio-vivienda-ordenamiento-territorial/sites/ministerio-vivienda-ordenamiento-territorial/files/2021-06/SCNT_ESTANDARES_0_0_0.pdf)
- [El Observador — Un dormitorio: el nuevo rey de la Vivienda Promovida (junio de 2026)](https://www.elobservador.com.uy/economia-y-empresas/un-dormitorio-el-nuevo-rey-la-vivienda-promovida-que-desplazo-al-formato-familiar-n6045957)
- [El Observador — Una de cada dos unidades vendidas es de un dormitorio (junio de 2026)](https://www.elobservador.com.uy/economia-y-empresas/vivienda-promovida-una-cada-dos-unidades-vendidas-es-un-dormitorio-n6046355)
- [El Observador — Estudio de la FADU sobre monoambientes (mayo de 2025)](https://www.elobservador.com.uy/economia-y-empresas/vivienda-promovida-estudio-cuestiona-exoneraciones-fiscales-para-construccion-de-monoambientes-n6001803)
- [El Observador — La ley que el gobierno quiere cambiar (julio de 2025)](https://www.elobservador.com.uy/economia-y-empresas/vivienda-promovida-la-ley-que-el-gobierno-quiere-cambiar-y-que-la-construccion-defienden-n6007516)
- [El Observador — Discusión de monoambientes (julio de 2026)](https://www.elobservador.com.uy/discusion-monoambientes-suma-un-nuevo-capitulo-promotores-advierten-que-se-ralentizo-la-inversion-n6050776)
- [El Observador — Precio promedio de los monoambientes (2025)](https://www.elobservador.com.uy/economia-y-empresas/vivienda-promovida-el-precio-promedio-los-monoambientes-supera-los-us-92000-n6021235/amp)
- [Montevideo Portal — Monoambientes: quiénes los compran †](https://www.montevideo.com.uy/Noticias/Monoambientes-quienes-los-compran-que-edades-alquilan-y-el-impacto-de-su-prohibicion-uc954879)
- [InfoCasas — Informe 2025](https://cdn1.infocasas.com.uy/web/6984f20dba60e_2025.pdf), [Radiografía 2025](https://www.infocasas.com.uy/blog/radiografia-2025) y [análisis de monoambientes (2026)](https://www.infocasas.com.uy/blog/?p=2342)
- [Ordenanza de higiene de la vivienda de Río Negro (alojada en ANII)](https://innovacionpublica.anii.org.uy/wp-content/uploads/2023/04/HIGIENE-DE-LA-VIVIENDA.pdf)

Argentina
- [Ámbito — La paradoja de los monoambientes (2026)](https://www.ambito.com/real-estate/la-paradoja-los-monoambientes-son-los-departamentos-mas-chicos-pero-tienen-el-m2-mas-caro-caba-n6330616)
- [Ámbito — De 100 m² a menos de 50 (2026)](https://www.ambito.com/real-estate/de-100-m2-menos-50-como-cambio-el-departamento-porteno-y-que-se-construye-cada-vez-mas-chico-n6330723)
- [Infobae — Los departamentos en CABA son cada vez más chicos (octubre de 2026) †](https://www.infobae.com/economia/2026/10/03/los-departamentos-en-caba-son-cada-vez-mas-chicos-cuantos-metros-cuadrados-se-perdieron-en-el-ultimo-siglo/)
- [Zonaprop — Index CABA (julio de 2026)](https://www.zonaprop.com.ar/blog/wp-content/uploads/2026/08/INDEX_CABA_REPORTE_2026-07.pdf)

Otros países
- [Reino Unido — Nationally Described Space Standard](https://www.gov.uk/government/publications/technical-housing-standards-nationally-described-space-standard/technical-housing-standards-nationally-described-space-standard)
- [Australia NSW — Apartment Design Guide, preguntas frecuentes](https://www.planning.nsw.gov.au/sites/default/files/2023-03/better-apartment-design-faq.pdf)
- [Chile MINVU — Cuadro normativo del DS 49 (2026)](https://www.minvu.gob.cl/wp-content/uploads/2026/04/Cuadro-Normativo-Abreviado-Llamado-Adquisicion-Terrenos-2026.pdf)
- [Chile — Colliers, stock nuevo en Santiago (Diario Estrategia, 2024)](https://www.diarioestrategia.cl/texto-diario/mostrar/4858945/departamentos-1-2-dormitorios-acaparan-64-stock-total-capital)
- [Brasil — Especificaciones de apartamentos Minha Casa Minha Vida (2012)](https://antigo.mdr.gov.br/images/stories/ArquivosSNH/ArquivosPDF/Publicacoes/Especificacoes_APTO_Tabela2_09-11-2012.pdf)
- [Cataluña — 36 m² mínimos (La Marea, 2023)](https://www.lamarea.com/2023/05/26/infraviviendas-legales-cuales-son-las-condiciones-minimas-de-un-piso)
- [EE. UU. — Census, Characteristics of New Housing](https://www.census.gov/construction/chars/highlights.html)
- [EE. UU. — RentCafe vía Multifamily Executive (2024)](https://www.multifamilyexecutive.com/design-development/design/u-s-apartment-sizes-inch-upward-in-2024_o)
- [EE. UU. — WealthManagement: unidades chicas, vacancia y rentas (KTGY, CoStar)](https://www.wealthmanagement.com/real-estate/smaller-apartment-units-outperform-the-market-on-both-vacancy-and-rents)
- [Canadá — RENX: Achieving the right unit mix](https://renx.ca/achieving-right-unit-mix-apartment-developers)
- [Reino Unido — Camden, Dwelling Size Priorities †](https://camdocs.camden.gov.uk/CMWebDrawer/Record/8236159/file/document)
- [Tinsa — superficie residencial construida en España †](https://www.tinsa.es/blog/vivienda/cuanta-superficie-residencial-se-construye-anualmente-espana)
- [Archgyan — How to design an apartment (fuente débil)](https://archgyan.com/how-to-design-an-apartment/)
