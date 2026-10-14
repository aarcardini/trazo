# Asoleamiento y orientación — referencias y método

Investigación del 14 de octubre de 2026 para que Trazo compruebe, vivienda por vivienda, el **sol directo de invierno** que exige la Vivienda Promovida. Hoy el motor no sabe dónde está el norte: la propuesta agrega un parámetro `norte` y una comprobación en la ficha («cumple», «con tolerancia» o «sin sol en invierno»). Complementa a `STANDARDS.md`.

Cómo leer las cifras: **(F)** de la fuente citada; **(D)** derivado; **(S)** criterio propio; **(†)** visto solo en el resumen de un buscador. Ángulos en grados; horas en hora local de Uruguay (UTC−3, sin cambio de hora).

## 1. Resumen

- **Vivienda Promovida** (Reglamentación de la Ley 18.795, MVOTMA, art. 6 D para obra nueva y art. 7 para reciclajes; texto verificado): cada vivienda recibe **sol directo una hora como mínimo durante todo el período de invierno** en al menos un dormitorio, estar o comedor; se admite **media hora menos en hasta el 10 % de las viviendas**. No define la fecha, el punto de medición ni cómo se cuentan las obstrucciones; el técnico lo declara bajo juramento. Si no se cumple remite al art. R.1652.9 del Digesto, que en 2009 trataba vidrios y protección solar y desde 2024 trata condensación: la remisión quedó ambigua.
- **MVOT / DINAVI** (estándares de desempeño, HC DH_02): mínimo **1 h en al menos un local habitable el 23 de junio**, verificado con estudios gráficos de asoleamiento; recomienda 2 h en la mitad de los locales habitables.
- **Digesto de Montevideo y Normativa Nacional de Edificación 2016:** no exigen asoleamiento por vivienda (solo patios, antepechos y criterios cualitativos). El Digesto tuvo una recomendación de 1 h (R.1652.10, 2009), sustituida en 2024.
- **Fecha de cálculo propuesta: 21 de junio**, el peor día para todas las orientaciones (el 23 de junio del MVOT difiere menos de 0,1°).
- **Montevideo, 21 de junio:** sale a las 07:52 (acimut 62°), mediodía solar a las 12:46 con altura máxima 31,7°, se pone a las 17:40 (acimut 298°). Horas de sol sobre una fachada sin obstáculos (altura del sol mayor que 5°): **N 8,7; NE y NO 7,5; E y O 4,4; SE y SO 1,2 (rasante); S 0**. Una fachada cuya normal está a menos de 44° del sur no llega a 1 h aunque no tenga obstáculos: es el único caso que falla siempre.
- **Método:** para cada ventana, un rayo hacia el sol contra los prismas de la propia masa (con sus patios) y de los vecinos por medianera; se suman los minutos con sol, se toma el mejor local de la vivienda y se aplica la tolerancia del 10 %.
- **Ejemplo:** edificio de 27 m con un patio de 6 m entre dos alas: la ventana de planta baja y la del piso 5 del muro que mira al norte reciben **0 h** (obstrucción de 76,8° y 60,3° contra un sol máximo de 31,7°); solo el último piso recibe sol (8,0 h). El muro que mira al sur, 0 h en cualquier piso. Con 27 m la NNE pide un patio principal de 6,75 m de lado y 54 m² (art. 44): uno de 6 m solo vale como secundario.

## 2. Normas de Uruguay

| Norma | Horas | Fecha o período | Local | Cómo se mide | Obstrucciones | Fuente |
|---|---|---|---|---|---|---|
| Reglamentación Ley 18.795, art. 6 D (obra nueva) y art. 7 (reciclajes) | 1 h de sol directo; 0,5 h menos en ≤ 10 % de las viviendas | «todo el período de invierno» (no definido) | al menos uno de dormitorio, estar o comedor | no definido; declaración jurada del técnico responsable (MVOT, 2025) | no dice | ANV, reglamentación (abril de 2020) (F) |
| MVOT / DINAVI, estándares de desempeño (HC DH_02, ítem 02-2) | mínimo 1 h; recomendación 2 h en la mitad de los locales habitables (atribuida a la UNIT 1026, no verificado) | **23 de junio** | al menos un local habitable, en el interior | memoria y estudios gráficos de asoleamiento; en prototipos, por orientaciones viables | «condicionantes de implantación» | MVOT (F) |
| Digesto IM, R.1652.10 (Res. 2928/09) | recomendación de 1 h | «durante el invierno» | dormitorio, estar o comedor | no definido | no dice | Res. 2928/09 (F); sustituido por Res. 1962/24 (cerramientos opacos) |
| Digesto IM, R.1652.9 (el que cita el reglamento) | no es de asoleamiento | — | — | 2009: transmitancia de vidrios y protección solar por orientación preponderante (hasta 20° de desvío); 2024: control de condensación. Su tabla 3 define «invierno: mayo a setiembre» solo para simular energía | — | Res. 2928/09 y 1962/24 (F) |
| Digesto IM, locales habitables y patios (D.3315–D.3322, D.3355–D.3359, D.224.266.13) | sin exigencia de sol | — | — | D.3317: antepecho de hasta 1,50 m; patio principal S = 2a, L = a/4, L ≥ 2 m | — | normativa.montevideo.gub.uy (F) |
| Digesto IM, Vol. IV, D.223.142 e) y D.223.233.6 | sin número | — | — | evitar «perjuicios de asoleamiento» a linderos (retiros especiales); analizar el asoleamiento por encima de 31 m | — | (F) |
| NNE 2016, arts. 43–52 | sin exigencia de sol | — | — | art. 44: patio principal S = 2h, L = h/4 ≥ 2,85 m; secundario S = 3h/4, L = h/10 + 1,20 m; art. 45: h desde el piso del local más bajo hasta el pretil más alto | — | copia del usuario (F; no se leyeron los 63 artículos) |

«Período de invierno»: ninguna norma uruguaya lo define para el asoleamiento. El MVOT lo resuelve con una fecha (23 de junio). La lectura más exigente del reglamento («cada día del invierno») se verifica con el día más desfavorable, el solsticio: las horas crecen desde el 21 de junio hasta el 21 de setiembre en todas las orientaciones (N 8,7 → 11,1; E y O 4,4 → 5,5; SE y SO 1,2 → 3,5).

## 3. Referencias internacionales (método)

| Norma | Horas | Fecha | Local | Cómo se mide | Obstrucciones | Fuente |
|---|---|---|---|---|---|---|
| NSW Apartment Design Guide, 4A-1 (Australia) | ≥ 70 % de las viviendas con 2 h (3 h fuera de Sydney, Newcastle y Wollongong); ≤ 15 % sin sol | 21 de junio, 9 a 15 h | estar y espacio exterior privado | 1 m² de sol directo a 1 m sobre el piso durante ≥ 15 min; comprobación «view from the sun» | otros edificios, sin árboles; minimizar viviendas solo al sur | ADG parte 4; nota técnica SEPP 65 (F) |
| BRE BR 209 (2011), APSH (Reino Unido) | 25 % anual y 5 % en invierno de las horas de sol probables | invierno: 21 de setiembre a 21 de marzo | ventanas de estares | cara exterior de la ventana; se estudia si hay obstáculo a menos de 25° y la ventana mira a ≤ 90° del sur | 25° desde el centro de la ventana | ayuda de IES VE (F); Camden (†) |
| BRE BR 209 (2022) y EN 17037 (Europa) | 1,5 h mínimo, 3 h medio, 4 h alto | un día entre el 1 de febrero y el 21 de marzo (sugerido el 21) | estar principal | punto en la cara interior del vidrio, con la jamba limitando el ángulo; altura solar mínima nacional (11,4°–14,6° en Europa central) | incluidas | IES VE; Acta Polytechnica CTU 38 (2022) (F) |
| DIN 5034-1 (Alemania) | ≥ 4 h el 21 de marzo; ≥ 1 h el 17 de enero para asegurar el invierno | 21 de marzo y 17 de enero | al menos un local de estancia por vivienda | centro de la ventana en el plano de fachada | incluidas | informes municipales (†); edición vigente sin confirmar |
| País Vasco, Decreto 80/2022 (guía de soleamiento) | 2 h en fachadas SE, S y SO (planeamiento); un estar orientado de E a O por el sur | solsticio de invierno, 9–15 h solar | fachada de la primera planta residencial | punto a 1 m sobre el forjado; sombras por el ángulo de elevación al obstáculo | edificios circundantes con sus alturas | guía de aplicación (2023) (F) |
| Chile, OGUC (arts. 2.6.3 y 2.6.11–14) | no es por vivienda | — | — | rasantes y sombra proyectada para conservar el sol de los vecinos | la sombra del proyecto no mayor que la del volumen teórico | MINVU DDU 168/456 (†) |
| CABA | no encontrado | | | | | |

## 4. Geometría solar de Montevideo

Latitud φ = −34,9°, longitud λ = −56,2° (este positivo), huso UTC−3. Fórmulas (Spencer / NOAA), con J = día del año (21 de junio = 172) y h = hora local decimal:
- γ = 2π/365 · (J − 1 + (h − 12)/24)
- ET (min) = 229,18 · (0,000075 + 0,001868 cos γ − 0,032077 sin γ − 0,014615 cos 2γ − 0,040849 sin 2γ)
- δ (rad) = 0,006918 − 0,399912 cos γ + 0,070257 sin γ − 0,006758 cos 2γ + 0,000907 sin 2γ − 0,002697 cos 3γ + 0,00148 sin 3γ
- hora solar verdadera (min) = 60 h + ET + 4 λ − 60 · huso (= 60 h + ET − 44,8); ángulo horario ω = TSV/4 − 180
- sin α = sin φ sin δ + cos φ cos δ cos ω; acimut desde el norte, horario: Az = atan2(sin ω, cos ω sin φ − tan δ cos φ) + 180 (mod 360)
- orto y ocaso (refracción −0,833°): cos ω0 = (sin(−0,833°) − sin φ sin δ) / (cos φ cos δ); altura máxima del solsticio: 90 − |φ| − 23,44 = 31,66°.

Verificación: contra un algoritmo tipo Meeus, 0,10° en altura y 0,14° en acimut como máximo; contra timeanddate (29/06/2025: sale 07:53, mediodía 12:48, se pone 17:43, altura 31,9°) el modelo da 07:53, 12:48, 17:43 y 31,8°; contra sunrisesunset.io, el día más corto (21/06/2026) dura 9 h 48 min y el modelo da 9 h 49 min.

**21 de junio** (declinación −23,45°, ET = −1,3 min; hora solar ≈ hora local − 46 min):

| Hora local | Altura | Acimut (desde el N) |
|---|---|---|
| 07:52 (orto) | −0,8° | 61,6° |
| 09:00 | 10,8° | 51,2° |
| 10:00 | 19,6° | 40,2° |
| 11:00 | 26,5° | 27,2° |
| 12:00 | 30,6° | 12,3° |
| 12:46 (mediodía solar) | 31,65° | 0,0° |
| 14:00 | 29,1° | 340,6° |
| 15:00 | 23,6° | 326,5° |
| 16:00 | 15,7° | 314,5° |
| 17:00 | 6,2° | 304,4° |
| 17:40 (ocaso) | −0,8° | 298,4° |

**Horas de sol sobre un plano vertical sin obstáculos** (el sol «delante»: |acimut − normal| < 90°):

| Normal de la fachada | altura > 0° | **altura > 5°** | altura > 10° | tramo (altura > 5°) | altura > 5° e incidencia ≤ 75° |
|---|---|---|---|---|---|
| N (0°) | 9,7 | **8,7** | 7,7 | 08:26–17:08 | 8,7 |
| NE (45°) / NO (315°) | 8,0 | 7,5 | 7,0 | 08:26–15:58 / 09:36–17:08 | 6,3 |
| E (90°) / O (270°) | 4,8 | 4,4 | 3,9 | 08:26–12:47 / 12:47–17:08 | 3,4 |
| SE (135°) / SO (225°) | 1,7 | 1,2 | 0,7 | 08:26–09:36 / 15:58–17:08 | 0,0 |
| S (180°) | 0 | 0 | 0 | — | 0 |

No llegan a 1 h aunque no haya obstáculos: con corte de 5°, las normales a menos de 44° del sur (a menos de 39° con corte de 0°, 49° con 10°); a 0,5 h, a menos de 38° del sur.

**Fachada norte frente a un muro paralelo** (21 de junio), según el ángulo de obstrucción β = atan((H − z) / d): β 0° → 9,65 h; 10° → 8,6; 15° → 7,9; 20° → 6,9; 25° → 5,6; 28° → 4,3; 30° → 3,0; 31° → 1,9; 31,5° → 0,9; **31,7° o más → 0 h** (el corte es abrupto).

## 5. Método para Trazo

1. **Orientación de cada ventana.** Cada vivienda ya trae `ventanas` (`poly`, `lines`, `seg`): punto medio P y normal exterior n del borde (en un polígono antihorario con borde p1 → p2, n = (dy, −dx) normalizado; si no se conoce el sentido, el lado opuesto al centroide). Parámetro nuevo **`norte`** = ángulo antihorario desde +Y del mundo hasta el norte (0 si +Y es el norte; 90 si el norte apunta a −X). Acimut de la fachada Az_f = (atan2(nx, ny) + norte) mod 360; dirección horizontal del sol en el mundo β = Az_sol − norte, s = (sin β, cos β); el sol está delante si n · s > 0.
2. **Obstrucciones como prismas** (polígono, cota de la cima): la propia masa, bloque por bloque con sus patios (huecos), de altura `height` (o por bloque cuando exista); los vecinos por medianera, un prisma detrás de cada `params.medianeras[i]` de altura `altura_vecinos` (por defecto la propia); por los lados sin medianera, calle o retiro sin obstáculo salvo que el usuario dibuje vecinos. Para un muro paralelo de altura H a distancia d con el sol de frente, β = atan((H − z) / d); con incidencia oblicua Δ el ángulo de perfil es atan(tan α / cos Δ): para E, O, SE y SO conviene el rayo completo.
3. **Cota de la ventana:** z = cota del nivel + antepecho + alto / 2 (`ventanas.alto` ya existe, 1,20 m; `antepecho` nuevo, 0,90 m propuesto, con tope normativo de 1,50 m del D.3317): el centro queda a 1,50 m del piso.
4. **Un instante:** rayo horizontal desde P + 0,02 n, a la distancia t está a altura z + t · tan α; para cada borde de cada prisma, si el rayo lo cruza en t > 0 y la altura del rayo ahí es menor que la cima, el sol está bloqueado (se prueban todos los cruces). Sol directo si α > α_min, n · s > 0 y no hay bloqueo.
5. **Horas:** recorrer el día en pasos de 5 min; sol de la ventana = unión de intervalos; sol del local = unión de sus ventanas (no se suman a ciegas); sol de la vivienda = **máximo** entre dormitorios, estar y comedor (la norma pide al menos un ambiente, no la suma).
6. **Clasificación:** `cumple` si ≥ 1,0 h; `tolerancia` si 0,5 ≤ h < 1,0; `no cumple` si < 0,5. Edificio: N viviendas de todos los niveles residenciales; cumple si ninguna «no cumple» y las de tolerancia son ≤ 10 % de N (sin redondear hacia arriba; lectura estricta, a confirmar con el organismo evaluador).
7. **Dudosas:** horas logradas solo con incidencia mayor de 75° o a menos del 15 % del mínimo; fachadas E, O, SE y SO (pocas horas y sol bajo: un obstáculo lateral las anula; en SE y SO el haz entra menos de 1 m en el local).

Código de referencia (solo `math`; `horas_ventana` devuelve las horas de sol de una ventana):

```python
import math
LAT, LON, TZ = -34.9, -56.2, -3.0

def pos_sol(J, h, lat=LAT, lon=LON, tz=TZ):
    g = 2*math.pi/365*(J-1+(h-12)/24)
    et = 229.18*(0.000075+0.001868*math.cos(g)-0.032077*math.sin(g)
                 -0.014615*math.cos(2*g)-0.040849*math.sin(2*g))
    d = (0.006918-0.399912*math.cos(g)+0.070257*math.sin(g)-0.006758*math.cos(2*g)
         +0.000907*math.sin(2*g)-0.002697*math.cos(3*g)+0.00148*math.sin(3*g))
    w = math.radians((60*h+et+4*lon-60*tz)/4-180)
    f = math.radians(lat)
    alt = math.asin(math.sin(f)*math.sin(d)+math.cos(f)*math.cos(d)*math.cos(w))
    az = math.atan2(math.sin(w), math.cos(w)*math.sin(f)-math.tan(d)*math.cos(f))
    return math.degrees(alt), (math.degrees(az)+180) % 360

def cruce(P, s, A, B):                  # t > 0 donde el rayo P + t·s corta el segmento AB, o None
    ex, ey = B[0]-A[0], B[1]-A[1]
    den = s[0]*ey - s[1]*ex
    if abs(den) < 1e-12: return None
    qx, qy = A[0]-P[0], A[1]-P[1]
    t = (qx*ey - qy*ex)/den
    u = (qx*s[1] - qy*s[0])/den
    return t if t > 1e-6 and -1e-9 <= u <= 1+1e-9 else None

def horas_ventana(P, n, z0, prismas, J, norte=0.0, alt_min=5.0, paso_min=5):
    # prismas: [(vertices, z_cima)]; n: normal exterior unitaria; z0: cota del centro de la ventana
    P = (P[0]+0.02*n[0], P[1]+0.02*n[1])
    tot = 0.0
    for m in range(0, 24*60, paso_min):
        alt, az = pos_sol(J, (m+paso_min/2)/60)
        if alt <= alt_min: continue
        b = math.radians(az - norte)
        s = (math.sin(b), math.cos(b))
        if n[0]*s[0] + n[1]*s[1] <= 0: continue
        tga = math.tan(math.radians(alt))
        libre = True
        for pol, ztop in prismas:
            for i in range(len(pol)):
                t = cruce(P, s, pol[i], pol[(i+1) % len(pol)])
                if t is not None and z0 + t*tga < ztop:
                    libre = False; break
            if not libre: break
        if libre: tot += paso_min/60
    return tot
```

Valores para las pruebas: fachada norte sin obstáculo 8,70 h (α_min = 5°) y 9,65 h (0°); sur 0 h; el ejemplo de abajo.

**Ejemplo: 27 m de altura, patio de 6 m entre dos alas** (muros paralelos, cima a 27 m, antepecho 0,90 y ventana de 1,20 —centro a 1,50 m—, entrepiso 3,0 m, 21 de junio). Para pasar por encima de un muro de altura H a distancia d con el sol de frente hace falta (H − z) / d ≤ tan 31,65° = 0,617: con d = 6 m, z ≥ 23,3 m.

| Nivel (muro del patio que mira al norte) | z del centro | β | Horas |
|---|---|---|---|
| Planta baja | 1,5 m | 76,8° | **0** |
| Piso 5 | 16,5 m | 60,3° | **0** |
| Piso 7 | 22,5 m | 36,9° | 0 |
| Piso 8 (último) | 25,5 m | 14,0° | 8,0 (08:46–16:47) |

El muro que mira al sur: 0 h en cualquier piso. Para 1 h, la ventana de planta baja necesita d ≥ 41,6 m y la del piso 5, d ≥ 17,1 m.

**Parámetros nuevos propuestos**

| Parámetro | Valor por defecto | Nota |
|---|---|---|
| `norte` | 0° | antihorario desde +Y del mundo |
| `asoleamiento.fecha` | 21 de junio | el 23 de junio del MVOT da lo mismo |
| `asoleamiento.horas_min` | 1,0 | reglamento 18.795 y MVOT |
| `asoleamiento.tolerancia_horas` / `tolerancia_pct` | 0,5 / 10 | reglamento 18.795 |
| `asoleamiento.alt_min_sol` | 5° | (S); con 0° hay más horas en E, O, SE y SO |
| `asoleamiento.antepecho` | 0,90 m | (S); D.3317: máximo 1,50 |
| `asoleamiento.altura_vecinos` | la propia, por medianera; 0 en el resto | (S), configurable |
| `asoleamiento.locales` | dormitorio, estar, comedor | reglamento 18.795 |
| `asoleamiento.paso_min` / `incidencia_dudosa` | 5 min / 75° | (S) |

## 6. Limitaciones

- Voladizos, balcones, parasoles y aleros no están en el motor y reducen el sol de invierno que entra.
- La vegetación no se modela (NSW no la cuenta como obstrucción).
- Edificios enfrentados de otra altura, vecinos futuros y topografía: el motor solo sabe lo que el usuario dibuja o declara; «vecino = altura propia» es conservador en muchas calles, pero no es un dato.
- Incidencia rasante (E, O, SE, SO): el espesor del muro y las jambas recortan el haz; un cálculo en planta sobrestima esas horas.
- La norma pide sol «en el interior»; el método mide sol en el plano de la ventana. La prueba de NSW (1 m² a 1 m del piso durante 15 min) puede sumarse en una segunda etapa.
- No hay método oficial para el reglamento 18.795: lo que Trazo informe es una verificación de proyecto, no una declaración de cumplimiento. Cielo despejado, como todas las normas citadas.
- Sin verificar: contenido de la UNIT 1026; edición vigente de la DIN 5034-1; textos de BR 209 (2022) y EN 17037; CABA; la búsqueda de texto en el sitio del Digesto puede ser incompleta.

## Fuentes

- [ANV — Reglamentación de la Ley 18.795 (MVOTMA, abril de 2020)](https://www.anv.gub.uy/sites/default/files/2020-04/Reglamentacion_Ley_18795_-_MVOTMA.pdf)
- [MVOT — Declaración jurada del técnico responsable (2025)](https://www.gub.uy/ministerio-vivienda-ordenamiento-territorial/sites/ministerio-vivienda-ordenamiento-territorial/files/2025-05/declaraci%C3%B3n%20jurada%20de%20T%C3%89CNICO%20RESPONSABLE_0.pdf)
- [MVOT / DINAVI — Estándares de desempeño y requisitos](https://www.gub.uy/ministerio-vivienda-ordenamiento-territorial/sites/ministerio-vivienda-ordenamiento-territorial/files/2021-06/SCNT_ESTANDARES_0_0_0.pdf)
- [Intendencia de Montevideo — Res. 2928/09 (copia del MIEM)](https://www.gub.uy/ministerio-industria-energia-mineria/sites/ministerio-industria-energia-mineria/files/2020-05/Resolucion2928-09_Fecha20090720.pdf) y [Res. 1962/24 (análisis de la Facultad de Arquitectura ORT)](https://fa.ort.edu.uy/innovaportal/file/146864/1/nueva-normativa-de-aislamiento-termico-realmente-representa-un-cambio-significativo-hacia-la-sostenibilidad.pdf)
- Digesto de Montevideo: [locales habitables](https://normativa.montevideo.gub.uy/articulos/82820), [patios](https://normativa.montevideo.gub.uy/articulos/82892), [D.224.266.13](https://normativa.montevideo.gub.uy/articulos/84641), [D.223.142](https://normativa.montevideo.gub.uy/articulos/51240), [D.223.233.6](https://normativa.montevideo.gub.uy/articulos/90833)
- Normativa Nacional de Edificación 2016 (copia del usuario)
- [NSW — Apartment Design Guide, parte 4](https://www.planning.nsw.gov.au/sites/default/files/2023-03/apartment-design-guide-part-4-designing-the-building.pdf) y [Solar access requirements in SEPP 65](https://www.planning.nsw.gov.au/sites/default/files/2023-03/solar-access-requirements-in-sepp-65.pdf)
- IES VE: [Exposure to sunlight hours (EN 17037, BR 209 2022)](https://help.iesve.com/ve2026/10_4_exposure_to_sunlight_hours.htm) y [Annual probable sunlit hours (BR 209 2011)](https://help.iesve.com/ve2025/10_3_annual_probable_sunlit_hours.htm)
- [Acta Polytechnica CTU 38 (2022) — EN 17037](https://ojs.cvut.cz/ojs/index.php/APP/article/download/8250/6523/32574)
- [Gobierno Vasco — Guía de soleamiento, Decreto 80/2022 (2023)](https://www.euskadi.eus/contenidos/informacion/dec_habitabi_gida/es_def/adjuntos/SOLEAMIENTO-2023-02-28-cast.pdf)
- [Camden — daylight and sunlight †](https://camdocs.camden.gov.uk/CMWebDrawer/Record/6897552/file/document); [Erfurt — DIN 5034 †](https://www.erfurt.de/mam/ef/leben/stadtplanung/bplan/dab/dab707/dab707_anl4.5_belichtung.pdf); [MINVU — DDU 168/456 †](https://www.minvu.gob.cl/wp-content/uploads/2019/06/DDU-168-Modificado-por-DDU-456-punto3-letras-a-y-b.pdf)
- [sunrisesunset.io — Montevideo](https://sunrisesunset.io/uy/montevideo-department/montevideo/) y [timeanddate — Montevideo](https://timeanddate.com/astronomy/uruguay/montevideo)
