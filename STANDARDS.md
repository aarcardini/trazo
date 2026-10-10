# Medidas y normativa — Trazo

Valores que usa el motor (`engine/standards.py`) y que se editan en la web en **0 · Medidas y normativa**.
**Mínimo** = exigencia normativa encontrada. **Típico** = criterio de proyecto (no normativo) para que los espacios salgan "reales".
Verificar siempre con la normativa vigente del departamento y del organismo correspondiente antes de usar en un proyecto.

## Vivienda

| Estancia | Mínimo (área / lado) | Típico (área / frente × fondo) | Referencia del mínimo |
|---|---|---|---|
| Dormitorio principal | 10,0 m² / 2,50 m | 11,5 m² / 3,20 × 3,60 | Ordenanza de higiene de la vivienda, art. 8 a): "una habitación" 10 m², lado 2,50 |
| Dormitorio secundario | 6,5 m² / 2,00 m (o 7 m² / 1,80) | 9,0 m² / 2,80 × 3,20 | Ídem, art. 8 b) |
| Estar-comedor | 10,0 m² / 2,50 m | 18–27 m² según dormitorios | Habitación (art. 8). Típico: 18 (monoamb./1 dorm.), 20 (2), 24 (3), 27 (4) |
| Cocina | 4,0 m² / 1,60 m (3 m² si abre a paso en 70 % del lado mayor) | 7,0 m² / 2,40 × 2,90 | Ídem, arts. 26-27 |
| Baño principal | 2,40 m² / 1,20 m (3,00 m² / 1,40 con bañera) | 4,0 m² / 1,70 × 2,40 | Ídem, art. 14 |
| Baño auxiliar | 1,50 m² / 0,80 m | 2,6 m² / 1,20 × 2,20 | Ídem, art. 14-15 |
| Lavadero / terraza de servicio | 1,5 m² | 2,5 m² / 1,20 × 2,10 | MVOT Reglamento de producto, art. 6 g) |
| Pasillo interno | 0,90 m (0,80 si tramo ≤ 4 m) | 1,00 m | Ordenanza, art. 41 |
| Pasaje / hall de entrada | 1,20 m (1,00 si ≤ 5 m) | 1,40 × 1,80 | Ordenanza, art. 41 |
| Altura libre | 2,40 m habitables; 2,20 m cocina, baño, circulaciones | — | Ordenanza, arts. 9, 14, 26 |

Superficie de la vivienda según dormitorios (rango de referencia ANV): monoambiente 25–40 m², 1 dorm. 35–50, 2 dorm. 50–75, 3 dorm. 65–100, 4 dorm. 80–125.
Ley 13.728, art. 18: mínimo 25 m²; 35 m² para 1 dormitorio y +15 m² por dormitorio adicional.

Reglas de distribución que aplica el motor: dormitorios y estar con fachada; dormitorios y baños accesibles desde el pasillo interno; cocina, comedor y estar integrados (conexión abierta); frente mínimo de la unidad = estar + dormitorios (para que todos tengan ventana).

## Núcleo de circulación vertical

| Elemento | Valor | Referencia |
|---|---|---|
| Ancho de tramo de escalera | 1,20 m (general) — 1,65 m en ciertos usos > 750 m² o > 12 m | Bomberos IT 19, 6.2.2.1 |
| Escalera colectiva (higiene) | 1,00 m con ascensor / 1,20 m sin ascensor | Ordenanza de higiene, art. 33 |
| Contrahuella | 16–18 cm (máx. 0,18; 0,19 con ascensor en ordenanzas) | IT 19 / Ordenanza art. 31 |
| Huella | 2a + b = 0,64 m (→ 0,29 con 17,5 cm) | IT 19 / Ordenanza art. 31 |
| Altura máxima por tramo | 3,70 m | IT 19 |
| Tipo de escalera (vivienda) | común ≤ 12 m; protegida (EP) 12–30 m; presurizada (PFP) > 30 m | IT 19, Anexo C, tabla 3 (grupo A) |
| Recorrido máximo de evacuación (vivienda, pisos altos) | 40 m (una salida) / 45 m (más de una), sin detección | IT 19, Anexo B, tabla 2 |
| Ducto de ascensor accesible | 1,75 × 1,95 m (accesibilidad básica 1,70 × 1,75) | Intendencia de Montevideo, ductos y cabinas |
| Cabina accesible | 1,10 × 1,40 m, puerta 0,80 m | Ídem |
| Ascensor obligatorio | acceso a más de 9 m de altura | MVOT, estándares de desempeño (cl. 58) |
| Palier frente a ascensores | 1,50 m (círculo de giro); palier común 1,20 (≤ 4 aptos) / 1,40 (> 4) | Accesibilidad / Ordenanza art. 41 |

Cantidad de ascensores (criterio de proyecto, editable): 1 cada 60 unidades servidas; mínimo 2 desde 10 niveles.
El núcleo se dimensiona sumando caja de escalera de ida y vuelta + ascensores + ducto de instalaciones; el fondo es el mayor entre la escalera y palier + ducto de ascensor.

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
| Retiro desde medianera para abrir ventanas | 3,00 m | Criterio indicado por el usuario (práctica en Montevideo); confirmar en el Digesto |
| Ancho mínimo de patio para iluminar | 3,00 m | Criterio indicado por el usuario (mismo criterio que el retiro para ventanas); confirmar en el Digesto, que puede exigir más según la altura |

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
- [Ordenanza de higiene de edificios destinados a vivienda (San José, Res. 1244/1977)](https://sanjose.gub.uy/wp-content/uploads/2015/07/ordenanzahigieneedificios.pdf)
- [Higiene de la vivienda (Río Negro, Dec. 92/1979)](https://innovacionpublica.anii.org.uy/wp-content/uploads/2023/04/HIGIENE-DE-LA-VIVIENDA.pdf)
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

Nota: el Digesto de Montevideo (normativa.montevideo.gub.uy) no estaba disponible al consultar; los mínimos de habitabilidad provienen de ordenanzas departamentales uruguayas que siguen el mismo modelo. Confirmar los valores de Montevideo cuando el servicio esté disponible.
