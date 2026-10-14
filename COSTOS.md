# Costo de construcción por m² y factibilidad — referencias

Investigación del 14 de octubre de 2026 para que Trazo estime el **costo de un proyecto según la gama de construcción** (baja, media, alta) elegida en la configuración, y lo compare con el ingreso por venta de cada variante. Complementa a `REFERENCIAS.md` (medidas y mix de mercado) y a `STANDARDS.md` (normativa).

Cómo leer las cifras:
- **(F)** dato de la fuente citada. **(D)** derivado por nosotros a partir de la fuente. **(S)** supuesto propio, sin fuente. **(†)** visto solo en el resumen de un buscador: menos peso.
- Monedas: USD salvo que se diga otra cosa; UYU a 40 por USD cuando hubo que convertir (S). UI ≈ USD 0,164 (D, de la ANV, primer semestre de 2026).
- **Advertencia principal:** no existe una fuente pública que dé el costo de obra por m² de **edificios de vivienda colectiva** en Uruguay por gama (ni la Cámara de la Construcción, ni la APPCU, ni las consultoras lo publican). Los valores de la sección 2 se triangularon con rangos de prensa y portales, el nivel de precios de venta de la ANV y un tope de lujo. La confianza es **baja a media**: antes de fijarlos en el programa conviene validarlos con dos o tres presupuestos de constructoras.

## 1. Resumen

| Gama | Costo de obra, USD por m² bruto cerrado (S, triangulado) | Qué incluye |
|---|---|---|
| **Baja** (Vivienda Promovida estándar) | **1.350** (1.200–1.500) | Materiales, mano de obra con leyes sociales, gastos generales y beneficio de la constructora. **Neto de IVA** (recuperable en la promovida). Sin terreno, honorarios, tasas ni imprevistos |
| **Media** | **1.750** (1.600–1.900) | ídem |
| **Alta** (premium) | **2.500** (2.200–2.800) | ídem |

- El resto del costo de un desarrollo (honorarios, ingeniería, tasas, imprevistos, administración, financieros, comercialización) suma ≈ 44 % de la obra en el ejemplo de la sección 7; la obra es ≈ 70 % del costo total. El terreno es un dato de entrada, no un porcentaje.
- Precio de venta de referencia en Montevideo (ANV, informe n.º 50, año móvil a abril de 2026, verificado): **USD 3.115 por m² habitable** (el comparable con los m² vendibles de Trazo) y 2.411 por m² construido con la cuota de bienes comunes.
- En el ejemplo (3.000 m² brutos, 2.400 vendibles, Cordón), la gama baja deja ≈ 20 % de margen, la media ≈ 4 % y la alta no cierra: en Cordón solo funciona la gama baja, que es la de mayor volumen en la ANV. El precio de equilibrio por m² vendible (2.373 / 3.147 / 4.609) es el resultado más robusto.

## 2. Costo de obra por m² en Uruguay: lo que hay

| Fuente (año) | Tipo | USD/m² | Qué incluye | Nota |
|---|---|---|---|---|
| Infonegocios, citando al CEO de InfoCasas (≈ 2016–2017) (F) | promedio país | 1.500–2.000 | no lo aclara | muy desactualizada |
| Estudio Pinares (2023) (F) | casa, construcción tradicional | 1.000–1.600 | mano de obra + materiales | constructora de casas |
| Que.es / Merca2 sobre Estudio Pinares (2023) (†) | promedio país | 1.500–1.900 | no lo aclara | |
| Grupo Placo (2024) (†) | calidad media a alta | 1.200–1.800 | no lo aclara | la página no abrió |
| realestate-in-uruguay.com (2025) (F) | residencial «alta calidad» | 1.600–2.800 | no lo aclara | guía para compradores extranjeros |
| cuantomecuesta.com (abril de 2026) (F) | casa económica / media / premium | 700–900 / 900–1.400 / 1.400–2.200 | obra, sin honorarios, BPS, permiso ni conexiones | agregador de baja confiabilidad; casas |
| Uruguay XXI, informe de diciembre de 2025 (F) | SLS Punta del Este: 2 torres de 24 pisos, 52.000 m², inversión USD 120 M | ≈ 2.308 (D) | «inversión» total declarada; no aclara terreno, hotel ni subsuelos | tope de lujo en la costa |
| Chequeo con la ANV (D) | promovida | ≈ 1.400 | obra neta | con USD 3.115 de venta y 15 % de margen, la obra que cierra la cuenta es ≈ 1.400 |

No se encontraron cifras de la CCU, la APPCU, Revista Construcción, ni de Cross, Fiddler, Kosak, Altius, Ebital, Mastermind o Dinarq; tampoco notas de prensa con USD/m² de obra de torres. Un documento de BMU mencionaba «llave en mano desde USD 1.680/m²» (†), sin poder leerlo.

**Evolución del costo (INE, ICCV base junio de 2023 = 100):** en 2024 el ICCVPu bajó 1,6 % real y subió 2,3 % en USD corrientes (Uruguay XXI); de mayo a agosto de 2026 acumuló ≈ + 4,0 % (D, con datosUruguay, que cita al INE). El ICCV está en pesos: un costo anclado en USD se actualiza como `c(t) = c(t0) × ICCV(t) / ICCV(t0) × TC(t0) / TC(t)`.

## 3. Composición del costo

### 3.1 Dentro de la obra (INE, ICCV base junio de 2023, lámina «Ponderaciones»; sobre el precio de obra con IVA) (F)

| Rubro | Torre económica y media (tipología 8) | Torre confortable (tipología 9) | ICCV general |
|---|---|---|---|
| Hormigón armado | 20,4 % | 23,9 % | 20,3 % |
| Albañilería | 17,3 % | 16,7 % | 17,8 % |
| Construcciones livianas | 1,8 % | 4,6 % | 3,7 % |
| Aluminio | 3,5 % | 4,0 % | 3,8 % |
| Instalación eléctrica | 3,6 % | 2,8 % | 3,7 % |
| Instalación sanitaria | 3,6 % | 2,8 % | 3,8 % |
| Ascensor | 1,3 % | 0,6 % | 0,7 % |
| Materiales y mano de obra directa (rubros 1 a 16) | 62,7 % (D) | — | — |
| Gastos generales | 4,8 % | 3,8 % | 6,2 % |
| Impuestos (casi todo IVA) | 15,9 % | 14,2 % | 11,1 % (0 % en la tipología con aporte público) |
| Leyes sociales | 16,4 % | 16,9 % | 17,3 % |
| Permisos de construcción | 0,2 % | 0,3 % | 0,2 % |

- Mano de obra con leyes sociales / materiales / gastos generales e impuestos: 48 % / 34 % / 18 % (ICCVPu, Uruguay XXI) (F).
- **Aporte unificado de la construcción: 71,8 % sobre los jornales** (patronales 9 %, personales 17,9 %, cargas salariales 29,9 %, SNS 9 %, BSE 6 %; BPS, 2026) (F). Además, 4 % del monto de mano de obra para la Caja de Profesionales en obras de arquitectura (Ley 17.738, art. 71 E) (F): ≈ 1,1 % de la obra neta (D).
- Mano de obra imponible ≈ 22,8 % del precio con IVA, ≈ 27 % de la obra neta (D).
- **IVA no recuperable** (proyecto no promovido): la obra sube 18,9 % (tipología 8) o 16,6 % (tipología 9) (D).

### 3.2 Fuera de la obra

| Rubro | Valor | Base | Fuente |
|---|---|---|---|
| **Honorarios de arquitectura** (Arancel SAU 1997, vigente como mínimo) | tramos acumulativos sobre el valor de obra en millones de pesos de marzo de 1997 (hasta 5 / 5–13 / 13–26 / 26–130 / más de 130). Categoría A, económica: 6 / 5 / 4 / 3 / 2 %. B, media y confortable: 10 / 9 / 7 / 5 / 3 %. C, suntuaria: 12 / 10 / 8 / 6 / 4 %. Incluyen la dirección de obra (B: 3,5 / 3 / 2,5 / 1,7 / 1 %); excluyen las ingenierías | obra = insumos + IVA + mano de obra con leyes sociales + gastos generales y beneficio; los tramos se actualizan con C = IPC / 12,68 (9,13 en marzo de 2026); la categoría E de unidades repetitivas no rige para plantas repetidas en altura | SAU (F) |
| Honorarios efectivos sobre obra neta (D, TC 40, C = 9,13) | obra de USD 2 M: A 6,5 % / B 11,3 % / C 13,0 %; USD 4 M: 5,8 / 10,1 / 11,6; USD 6 M: 5,2 / 9,1 / 10,5; USD 10 M: 4,6 / 7,8 / 9,1; USD 25 M: 4,0 / 6,7 / 7,9 | | cálculo propio |
| Estructura (categoría F del arancel) | 1,3 % de la obra | | SAU (F) |
| Ingeniería de instalaciones, suelos, mensura, copias y tasas | no incluidas en el arancel | | SAU (F) |
| **Permiso de construcción, Intendencia de Montevideo** (Digesto, art. 224) | vivienda: 25 UI/m² (unidades hasta 70 m²), 30 (hasta 140 m²), 35 (más de 140 m²); comercio y oficinas 35 / 42 / 47; otros 25 | cada m² del permiso; ≈ USD 4–6 por m² ≈ 0,3 % de la obra (D) | Digesto (F) |
| Final de obra, registro de obra en BPS, Bomberos, UTE, OSE, gas, escribanía y reglamento de copropiedad, mensura | **no encontrado** para edificios (para casas, cuantomecuesta da UTE UYU 15–45 mil, OSE 22–85 mil, mensura 35–55 mil, baja confiabilidad) | | |
| Imprevistos | 10–15 % sugerido para casas; sin fuente para edificios con contrato | presupuesto | cuantomecuesta (F) |
| Comisión inmobiliaria | 3 % + IVA (≈ 3,66 %) | precio de venta | aviso de InfoCasas (terreno en Cordón, 2026) (F); para apartamentos (S) |
| Costos financieros, administración del desarrollador, publicidad, margen esperado | **no encontrado** | | |
| Compra en pozo | 10–15 % de descuento sobre el precio terminado | | Piso Inmobiliario (2026) (F), sin verificar |
| **Ley 18.795 (Vivienda Promovida), art. 4** | exoneración de IRAE, Impuesto al Patrimonio, IVA a las ventas y a las obras e ITP en la primera transmisión; crédito por el IVA de insumos y servicios de la obra; exoneración de la renta de alquiler durante 10 ejercicios (60 % en general, según Ingar) | | IMPO (F); Ingar (F): confirmar el alcance con un contador |
| Topes de precio de venta de la promovida (UI, por zona) | **no encontrado**; según Ingar, los decretos de 2020 suprimieron los precios máximos en parte de los casos | | ver Decretos 355/011 y 129/020 |

## 4. Terreno

No hay estudios de incidencia por zona; solo precios pedidos en avisos (F):

| Zona | Dato | Cuenta (D) |
|---|---|---|
| Cordón | InfoCasas, septiembre de 2026: 510 m², 12 m de frente, FOS 100 %, altura máxima 27 m, retiro 0, comisión 3 % + IVA; pedido USD 490.000 | **USD 961 por m² de terreno**. Con 27 m caben ≈ 9 pisos y hasta ≈ 4.590 m² brutos (S): ≈ USD 107 por m² bruto y 133 por m² vendible, es decir 4,0–4,4 % del precio a USD 3.000–3.300; con 3.000 m² brutos, 204 por m² vendible = 6,2–6,8 % |
| Pocitos | InfoCasas, mayo de 2025: predio de 652 m² con 790 m² edificados; pedido USD 1.000.000 | **USD 1.534 por m² de terreno**; sin FOT ni altura, no se calculó la incidencia |
| Carrasco | no encontrado | |

Contexto: el CEO de Liderus habla de lotes «en muchos casos exorbitantes» en ubicaciones privilegiadas (Bloomberg Línea); Plaza Mayor recoge la crítica de que la ley de Vivienda Promovida encarece el suelo. Conclusión para Trazo: **el terreno es un dato de entrada** (USD por m² de terreno o total), y su incidencia es una salida.

## 5. Precio de venta por m² por zona

**ANV, Vivienda Promovida (declaraciones juradas; informe n.º 50, mayo de 2026; verificado):**

| Indicador | Valor |
|---|---|
| Montevideo, año móvil a abril de 2026 | USD 2.411 por m² construido (15.125 UI) y **3.115 por m² habitable** (19.539 UI) |
| Montevideo, primer semestre de 2026 | 2.477 por m² construido (récord; + 6,9 % sobre el primer semestre de 2025; en UI, estancado) |
| País / Canelones / Ciudad de la Costa / Maldonado (construido) | 2.450 / 2.845 / 3.026 / 2.173 |
| Barrios (construido) | Malvín 2.832; Capurro–Bella Vista 2.783; Larrañaga 2.761; Prado más de 2.600; Atahualpa y Tres Cruces más de 2.500; Parque Batlle ≈ 2.500; La Figurita 2.039 (mínimo); Cordón + 7 % interanual (nivel solo en gráfico) |
| Precio medio por tipología, Montevideo | monoambiente 97.051; 1 dormitorio 126.774; 2 dormitorios 166.175; 3 dormitorios 254.980 |
| Montevideo, 2025 (informe n.º 49) | 2.375 construido y 3.020 habitable; Prado 2.828; Reducto 1.757 |

Definiciones de la ANV: «construido» = bienes individuales más la cuota parte de bienes comunes, ponderada; «habitable» = piso más muros (exteriores hasta 0,20 m, divisorios a eje). El habitable es ≈ 29 % más caro por m² que el construido (D).

**Precios pedidos, usados y nuevos (referenciales):** Piso Inmobiliario (2026): Carrasco 4.349; Villa Biarritz 4.207; Puerto del Buceo 4.200; Pocitos 3.850; Punta Carretas 3.497; Cordón 2.700; Tres Cruces y La Blanqueada 2.650; Centro 2.200; Reducto 1.525. Bloomberg Línea (relevamiento RIAL, ≈ 2025): promedio de Montevideo 3.454; un proyecto nuevo en Cordón: monoambiente de 31,1 m² a USD 106.900 (3.437/m²), 1 dormitorio de 41,3 m² a 149.900 (3.630/m²), 2 dormitorios de 67,3 m² a 173.900 (2.584/m²). Premium: Le Mont (Puerto del Buceo) hasta USD 10.000/m² (Uruguay XXI); Torre Trump (Punta del Este) 5.500–6.000 (†).

## 6. Contraste: Argentina y España

- **Argentina.** APYMECO, vivienda tipo de 100 m²: USD 1.428/m² en enero de 2026 (1.334 en diciembre de 2025; pico ≈ 1.850 en noviembre de 2023) (F). Eficiencia Constructiva (marzo de 2026): promedio 1.300–1.450; básica 900–1.200; intermedia 1.300–1.500; premium 1.500–2.000 o más (F). Zonaprop (junio de 2026): departamentos en CABA a USD 2.467/m²; el costo CAC en USD subió 16 % en el primer semestre de 2026 y está 3,5 veces por encima del mínimo de octubre de 2020 (F). La mano de obra pesa 35–50 % (†). No se encontraron el CAC de edificios en altura, la incidencia del terreno en CABA ni la tabla de honorarios del CPAU.
- **España.** Comunidad de Madrid, método oficial de costes de referencia (2022) (F): coste de ejecución material por m² construido, bloque abierto 871–1.064 €, manzana cerrada 856–1.046, garaje bajo rasante 482–590 (≈ 0,55 de la vivienda), aislada 1.161–1.419; fórmula base × CS (zona 1,00 / 1,08 / 1,16) × CA (acabados: 0,92 reducido / 1,00 medio / 1,23 alto / 1,53 lujo) × CH × CDA; sin gastos generales, beneficio, IVA ni honorarios. APCE Cataluña (2025): plurifamiliar 1.645 €/m² (+ 25 % desde 2019) (F). Hacecuentas (†): básica 1.300–1.600, media 1.600–1.900, premium 2.000–2.500 €/m². Lectura: en Madrid la distancia entre acabado reducido y lujo es 1,53 / 0,92 ≈ 1,7; en la propuesta para Uruguay, alta / baja = 2.500 / 1.350 ≈ 1,85, del mismo orden.

## 7. Propuesta para Trazo

### 7.1 Parámetros por gama (todos editables; la gama se elige en la configuración del proyecto)

| Parámetro | Baja | Media | Alta | Estado |
|---|---|---|---|---|
| Obra, USD por m² bruto cerrado, neto de IVA | 1.350 | 1.750 | 2.500 | (S) triangulado |
| Categoría del arancel SAU | A | B | C | (F) |
| Honorarios de arquitectura y dirección | fórmula SAU (≈ 5,8 % con obra de USD 4 M) | fórmula SAU (≈ 9,6 %) | fórmula SAU (≈ 9,8 %) | (F)/(D) |
| Ingeniería y estudios | 2,0 % de la obra | 2,5 % | 3,0 % | solo la estructura (1,3 %) tiene fuente; el resto (S) |
| Permiso de la Intendencia | 25 UI por m² del permiso (30 o 35 según el tamaño de las unidades) | ídem | ídem | (F) |
| Caja de Profesionales | 4 % × 27 % de la obra ≈ 1,1 % | ídem | ídem | (F)/(D) |
| Conexiones, Bomberos, escribanía y reglamento | 1,5 % de la obra | 1,5 % | 1,5 % | (S) |
| Imprevistos | 5 % | 5 % | 7 % | (S) |
| Administración del desarrollador | 2,0 % de la obra | 2,0 % | 2,5 % | (S) |
| Costos financieros | 3 % de (obra + terreno) | 4 % | 5 % | (S) |
| Comercialización, sobre el ingreso | 5,0 % | 5,5 % | 7,0 % | comisión 3 % + IVA (F); el resto (S) |
| IVA no recuperable (proyecto no promovido) | obra × 1,17–1,19 | ídem | ídem | (D); el IVA de la venta de vivienda nueva no está verificado |

Coeficientes del costo de obra por tipo de superficie: sobre rasante cerrado 1,00; subsuelo y cochera **0,55** (relación de Madrid); balcones y terrazas cubiertas 0,50 (S); amenities interiores 1,2–1,3 (S); altura: 0,90 hasta planta baja + 3 sin ascensor, 1,00 hasta 10 pisos, 1,08 de 11 a 20 (S, sin fuente).

### 7.2 Fórmulas

- `obra = Σ (m²_k × costo_gama × f_k)` por tipo de superficie k (cerrado, subsuelo, balcones, amenities).
- `honorarios = Σ tramos SAU(M)`, con `M = obra × 1,19 × TC / (IPC / 12,68) / 10⁶` (millones de pesos de marzo de 1997).
- `tasas_trámites = 25 UI × m²_permiso × 0,164 + 0,04 × 0,27 × obra + 1,5 % × obra`.
- `terreno = precio_terreno × (1 + 3,66 %)`: dato de entrada (USD por m² de terreno o total).
- `costo_total = obra + honorarios + ingeniería + tasas_trámites + imprevistos + administración + terreno + financieros + comercialización`.
- `ingreso = m²_vendibles × precio_venta_por_m²_vendible` (referencia ANV «habitable»: Montevideo 3.115; por barrio, sección 5).
- `comercialización = % × ingreso`; `margen = ingreso − costo_total`; también `margen / ingreso`, `margen / costo` y el **precio de equilibrio** = costo_total / m²_vendibles (sin la comercialización, que depende del precio).
- Opción del proyecto: promovida (IVA recuperable) o no promovida (obra × 1,17–1,19).
- Actualización en el tiempo: ICCV y tipo de cambio (sección 2).

### 7.3 Ejemplo: 3.000 m² brutos, 2.400 m² vendibles, Cordón

Terreno de USD 490.000 (sección 4) más 3,66 % de comisión = 507.934. Precios de venta por gama supuestos (S) con la ANV y Bloomberg como base.

| USD | Baja | Media | Alta |
|---|---|---|---|
| Obra (3.000 × 1.350 / 1.750 / 2.500) | 4.050.000 | 5.250.000 | 7.500.000 |
| Honorarios SAU (A / B / C) | 233.865 (5,8 %) | 501.822 (9,6 %) | 736.360 (9,8 %) |
| Ingeniería | 81.000 | 131.250 | 225.000 |
| Tasas y trámites | 116.812 | 147.772 | 205.822 |
| Imprevistos | 202.500 | 262.500 | 525.000 |
| Administración | 81.000 | 105.000 | 187.500 |
| Terreno | 507.934 | 507.934 | 507.934 |
| Financieros | 136.738 | 230.317 | 400.397 |
| Comercialización | 360.000 | 435.600 | 655.200 |
| **Costo total** | **5.769.850** | **7.572.196** | **10.943.213** |
| USD por m² bruto (total) | 1.923 | 2.524 | 3.648 |
| USD por m² vendible (total) | 2.404 | 3.155 | 4.560 |
| Precio de venta supuesto, USD por m² vendible | 3.000 | 3.300 | 3.900 |
| **Ingreso** | 7.200.000 | 7.920.000 | 9.360.000 |
| **Margen** | **1.430.150 (19,9 %)** | **347.804 (4,4 %)** | **− 1.583.213 (− 16,9 %)** |
| Precio de equilibrio, USD por m² vendible | 2.373 | 3.147 | 4.609 |
| Terreno, % del ingreso | 7,1 | 6,4 | 5,4 |

Lecturas: las partidas ajenas a la obra suman ≈ 44 % de la obra y la obra es ≈ 70 % del costo total; en Cordón solo cierra la gama baja; la alta exige USD 4.600 o más por m² vendible, que solo se da en Pocitos, Punta Carretas, Carrasco o el Buceo; el resultado es muy sensible al salto de honorarios entre las categorías A y B y al precio de venta.

### 7.4 Antes de fijar los números

1. Pedir dos o tres presupuestos de constructoras para un edificio tipo de cada gama y ajustar las tres cifras de obra (la mayor incertidumbre).
2. Confirmar con un contador el IVA de la venta de vivienda nueva no promovida y el alcance de la exoneración de la Ley 18.795.
3. Confirmar si los honorarios reales se negocian por debajo del arancel mínimo de la SAU.
4. Obtener de la Intendencia el cálculo exacto de las tasas del permiso; faltan el final de obra y las conexiones de UTE, OSE y gas de edificios.
5. Para el terreno, usar un precio de entrada; falta el dato de Carrasco.

### 7.5 Qué podría hacer Trazo con esto (propuesta, pendiente de decisión)

Un panel de **factibilidad** en el resumen: la gama (baja / media / alta) y el precio del terreno en la configuración del proyecto; el precio de venta por m² vendible (por defecto el de la ANV para Montevideo, editable por barrio); el programa calcula obra (con la superficie bruta por nivel y programa que ya tiene `metrics.programs`, con los coeficientes de subsuelo y balcones), honorarios SAU por tramos, el resto de las partidas por porcentaje, el ingreso con la NSA, el margen y el precio de equilibrio; todo por variante, para comparar. Los porcentajes y los costos por m² van en `standards.py` (sección nueva `costos`) y en `STANDARDS.md`, con las marcas de esta investigación, y son editables en Normativa.

## Fuentes

Uruguay
- [INE — ICCV, nueva base junio de 2023 (presentación metodológica)](https://www.gub.uy/instituto-nacional-estadistica/sites/instituto-nacional-estadistica/files/documentos/noticias/ICCV.%20Nueva%20Base%20Junio%202023.pdf)
- [Uruguay XXI — Sectores: construcción e inmobiliario (diciembre de 2025)](https://www.uruguayxxi.gub.uy/es/centro-informacion/articulo/informe-construccion-e-inmobiliario/?download=es)
- [datosUruguay — ICCV 2026 (cita al INE)](https://datosuruguay.com/indice-costo-construccion-vivienda) y [julio de 2026](https://datosuruguay.com/actualizaciones/iccv-julio-2026)
- [BPS — Aportación de construcción (2026)](https://www.bps.gub.uy/837/aportacion-construccion.html)
- [Ley 17.738 (Caja de Profesionales), art. 71 E (IMPO)](https://www.impo.com.uy/bases/leyes/17738-2004)
- [Ley 18.795, art. 4 (IMPO)](https://www.impo.com.uy/bases/leyes/18795-2011)
- [SAU — Arancel de honorarios (1997, vigente)](https://www.sau.org.uy/content/Arancel_Honorarios_SAU.pdf), [coeficientes de actualización](https://www.sau.org.uy/arancel-de-honorarios/) y [vigencia (2021)](https://www.sau.org.uy/vigencia-del-arancel-de-honorarios-profesionales-sau/)
- [Intendencia de Montevideo — Digesto, art. 224 (tasas del permiso)](https://normativa.montevideo.gub.uy/armado/60308)
- [ANV — Informe de precios n.º 50 (mayo de 2026)](https://www.anv.gub.uy/sites/default/files/2026-06/INFORME_DE_PRECIOS_%20202605.pdf) y [n.º 49 (enero de 2026)](https://anv.gub.uy/sites/default/files/2026-05/INFORME_DE_PRECIOS_202601.pdf)
- [InfoCasas — Radiografía 2025](https://cdn1.infocasas.com.uy/web/6984f20dba60e_2025.pdf), [terreno en Cordón (septiembre de 2026)](https://www.infocasas.com.uy/terreno-para-desarrollo-en-cordon/194223644) y [predio en Pocitos (mayo de 2025)](https://www.infocasas.com.uy/venta-excepcional-pu-para-desarrolladores-en-pocitos/192460085)
- [Bloomberg Línea — Por qué es tan caro comprar un predio en Montevideo (≈ 2025)](https://www.bloomberglinea.com/latinoamerica/uruguay/por-que-es-tan-caro-comprar-un-predio-y-vivir-en-montevideo-empresarios-inmobiliarios-explican/)
- [Piso Inmobiliario — precios por zona 2026](https://www.pisoinmobiliario.com/blog-entry/95-precios-inmuebles-montevideo-2026-datos-reales-zona), [precio por m² por barrio](https://www.pisoinmobiliario.com/blog-entry/240-precio-m-montevideo-2026-analisis-barrio) y [Vivienda Promovida 2025](https://www.pisoinmobiliario.com/blog-entry/11-iinforme-2025-evolucion-de-precios-y-tendencias-de-la-vivienda-promovida-en-uruguay)
- [Plaza Mayor — Guía de la Ley de Vivienda Promovida (2025–2026)](https://www.plazamayor.com.uy/ley-de-vivienda-promovida-en-uruguay-guia/)
- [Ingar — Beneficios fiscales de la Ley 18.795 (2026)](https://ingar.com.uy/blog/ley-de-vivienda-promovida-beneficios-fiscales)
- [Infonegocios — El m² de construcción más caro de Sudamérica (≈ 2016–2017)](https://infonegocios.biz/nota-principal/uy-tiene-el-m2-de-construccion-mas-caro-de-sudamerica-detras-de-una-ve-sobrevaluada)
- [Estudio Pinares — Cuánto cuesta construir en Uruguay (2023)](https://estudiopinares.com/cuanto-cuesta-construir-en-uruguay/), [Que.es (2023) †](https://www.que.es/2023/07/04/el-precio-de-construir-una-casa-en-uruguay-con-estudio-pinares/)
- [realestate-in-uruguay.com — Building and renovating (2025)](https://www.realestate-in-uruguay.com/blog/building-renovating-uruguay-2025-guide/)
- [cuantomecuesta.com — Construir una casa (abril de 2026; baja confiabilidad)](https://cuantomecuesta.com/uy/construir-casa/)

Argentina y España
- [iProfesional — Costo de construcción en dólares (2026)](https://www.iprofesional.com/realestate/448329-sube-fuerte-el-costo-de-construccion-en-dolares-cuanto-hay-que-invertir-por-m2)
- [Eficiencia Constructiva — Valor del m² de construcción 2026](https://www.eficienciaconstructiva.com.ar/noticias/2026/03/04/8387-valor-del-metro-cuadrado-de-construccion-en-argentina--2026)
- [Zonaprop — Index CABA (junio de 2026)](https://www.zonaprop.com.ar/blog/wp-content/uploads/2026/07/INDEX_CABA_REPORTE_2026-06.pdf)
- [Hacecuentas — CABA †](https://hacecuentas.com/argentina/caba/calculadora-costo-m2-construccion-argentina) y [España †](https://hacecuentas.com/es/calculadora-costo-construccion-m2-espana)
- [Comunidad de Madrid — Método de determinación de costes de referencia de la edificación (2022)](https://gestiona.comunidad.madrid/cred_inter/resources/pdf/Metodo_determinacion_costes_referencia_edificacion_2022.pdf)
- [Merca2 — Coste de construir vivienda en España (julio de 2026)](https://www.merca2.es/2026/07/21/coste-construir-vivienda-espana-subida-25-2421492/)
