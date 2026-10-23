# PADRON.md — Investigación de R1.6 «Abrir padrón de Montevideo» (23/10/2026)

**INCOMPLETO: falta probar un padrón céntrico y uno de la base de tipologías, buscar por dirección (`cb_v_mdg_accesos_puerta`), confirmar el significado de cada código de `cat_suelo` (`retiro`, `altura`, `fos`, `usopre`, `rgs`, `promo`) contra el Digesto Departamental o el CITIM, comprobar que `urllib` (y no solo `curl`) llega al servicio, y revisar catalogodatos.gub.uy, ide.uy y la Dirección Nacional de Catastro (algunos no respondieron desde este entorno). Hasta aquí: SÍ hay un servicio abierto y consultable.**

Las respuestas crudas están fuera del repo (`scratchpad/out/padron/`). Todo se consultó con `curl -sS -m 20` a través del proxy del entorno; la máquina del usuario no tiene ese proxy.

## 1. Resumen ejecutivo (provisorio)
- **Viable.** La Intendencia de Montevideo (IM) publica un GeoServer abierto con WFS: `https://montevideo.gub.uy/app/geoserver/wfs` (también `/ows`), sin clave ni registro. Se consulta con un GET y devuelve GeoJSON (`outputFormat=application/json`), así que alcanzan `urllib` y `json` del servidor local.
- **Polígono del lote:** capa `mapstore-base:cb_v_mdg_parcelas_citim` (208 596 padrones), campo `padron`, geometría en **EPSG:32721 (UTM 21 S), en metros**: es el mismo sistema que Trazo ya usa (sin conversión).
- **Parámetros urbanísticos:** la capa `mapstore-tematicas:ot_v_mdg_parcelas_cat_suelo` trae, por padrón, la geometría y los campos `categoria`, `sub_categoria`, `area_diferenciada`, `rgs`, `retiro`, `galibo`, `altura`, `fos`, `usopre`, `planesp`, `planparcial`, `promo`, `fis`. Con el padrón de prueba devolvió `retiro` = «4», `altura` = «9-12», `fos` = «60», `usopre` = «MC». Son cadenas de texto con códigos: falta confirmar su significado y unidades.
- **Licencia:** «De uso libre según resolución 640/10 del Intendente Municipal de Montevideo de fecha 22/02/2010» (metadato de GeoNetwork). Actualización mensual; el propio metadato avisa «esta información puede contener errores».
- **No da:** las medianeras (hay que deducirlas de los linderos sin frente a calle), la normativa como documento, ni garantía de servicio. La página de geoservicios de la IM dice que están «temporalmente fuera de servicio para Internet, solo Intranet», pero el WFS respondió desde aquí (ver riesgos).

## 2. Servicios
### 2.1 WFS de la IM (el que sirve)
- Dirección: `https://montevideo.gub.uy/app/geoserver/wfs` (GeoServer; WFS 1.0.0, 1.1.0 y 2.0.0 en GetFeature). `GetCapabilities`: `…/ows?service=WFS&version=1.1.0&request=GetCapabilities` (187 kB, 205 capas; lista en `im_wfs_capas.txt`).
- Clave / registro: ninguno. Responde: sí (200).
- Consulta por padrón (petición real):
  `GET https://montevideo.gub.uy/app/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=mapstore-base:cb_v_mdg_parcelas_citim&cql_filter=padron=421264&outputFormat=application/json`
- Padrón de prueba **421264** (no es de la base de tipologías; es el primero que devolvió la capa): `numberMatched` 1; `areatot` 177 m², `areacat` 196 m² (catastral), `ph` 0; polígono de 4 lados (5 vértices), UTM 32721:
```
Archivo: padron_421264_parcela.json
  numberMatched: 1 | numberReturned: 1
  propiedades: {"gid": 25858464, "padron": 421264, "areatot": 177, "areacat": 196, "ph": 0, "imponible": null, "carpeta_ph": 0}
  geometria: Polygon 5 vertices; [[574591.7216342, 6144572.4917357], [574609.087147, 6144565.1541117], [574600.9522971, 6144555.1739012], [574588.6803246, 6144565.1767707], [574591.7216342, 6144572.4917357]]
Archivo: padron_421264_cat_suelo.json
  numberMatched: 1 | numberReturned: 1
  propiedades: {"gid": 25858464, "padron": 421264, "areatot": 177, "areacat": 196, "ph": 0, "imponible": null, "carpeta_ph": 0, "categoria": "U", "sub_categoria": "SUCIn", "area_diferenciada": "Casavalle Piedras Blancas- Manga", "cortado_rn": false, "rn_area_diferenciada": null, "rgs": "RGE", "retiro": "4", "galibo": null, "altura": "9-12", "fos": "60", "usopre": "MC", "planesp": null, "planparcial": null, "promo": "PEMI", "fis": null, "nom_trans": null, "tipo_trans": null, "estado_trans": null}
  geometria: Polygon 5 vertices; [[574591.7216342, 6144572.4917357], [574609.087147, 6144565.1541117], [574600.9522971, 6144555.1739012], [574588.6803246, 6144565.1767707], [574591.7216342, 6144572.4917357]]
```
- Capas útiles (todas en EPSG:32721 salvo `retiros_1947` y `ot_retiros_desde_1947`, en 31981):
  - `mapstore-base:cb_v_mdg_parcelas_citim`: `gid`, `padron`, `the_geom`, `areatot`, `areacat`, `ph`, `imponible`, `carpeta_ph`.
  - `mapstore-tematicas:ot_v_mdg_parcelas_cat_suelo` (y `…_subcat_suelo`): los de arriba más `categoria`, `sub_categoria`, `area_diferenciada`, `cortado_rn`, `rn_area_diferenciada`, `rgs`, `retiro`, `galibo`, `altura`, `fos`, `usopre`, `planesp`, `planparcial`, `promo`, `fis`, `nom_trans`, `tipo_trans`, `estado_trans`.
  - `mapstore-tematicas:ot_v_pat_constanciars`: `padron`, `rgs`, `mhn_bid`, `lindero`, `ap`, `cautela`, `aec` (patrimonio).
  - `mapstore-base:cb_v_mdg_accesos_puerta`: `padron`, `num_puerta`, `letra`, `nom_calle`, punto: sirve para buscar por dirección.
  - `mapstore-base:cb_v_sig_vias`, `cb_v_sig_aceras`, `cb_v_sig_manzanas_materializadas`, `ic_v_mdg_manzanas`: calles, aceras y manzanas (para decidir qué linderos dan a calle).
  - `mapstore-tematicas:ot_retiros_desde_1947`, `ot_ret_exoneracion_retiros`, `ot_v_sig_alineaciones`, `ic_v_ce_permisos_construccion_geom`, `ic_v_sca_djcu_mayo2023`: retiros históricos, exoneraciones, alineaciones, permisos de construcción y DJCU (por padrón).
  - Espacio `citim`: `ot_citim_v_categorias_suelo`, `ot_citim_v_subcategorias_suelo`, `ot_citim_v_areas_diferenciadas_suelo`, `ot_v_citim_suelos_apt`, grados de protección (Centro y Ciudad Vieja).
- Otras descargas: `https://intgis.montevideo.gub.uy/sit/php/common/datos/generar_zip2.php?nom_tab=v_mdg_parcelas_geom&tipo=gis` (shapefile de parcelas, no probado) y el mismo WFS con `outputFormat=SHAPE-ZIP`.

### 2.2 Catálogo GeoNetwork de la IM
- `https://geoweb.montevideo.gub.uy/geonetwork` (GeoNetwork 3.12.1). Responde. CSW: `/srv/spa/csw?service=CSW&version=2.0.2&request=GetCapabilities`; búsqueda JSON: `/srv/spa/q?_content_type=json&fast=index&any=padron`; ficha ISO: `/srv/api/records/<uuid>/formatters/xml`.
- Fichas leídas: «GEOMETRIA DE PARCELAS» (639c4c9f-fda9-4d2f-b1da-40acabc208c3) y «PADRONES» (6b49748c-6fb7-41e4-9540-29656de8ad74): Servicio de Catastro y Avalúo (imcatastro@imm.gub.uy), EPSG:32721, actualización mensual, shapefile, licencia de uso libre (res. 640/10). También existe «CONSTANCIA DE RÉGIMEN DE SUELO» (81c7c741-334e-46ba-aece-661540691546).
- El GeoServer de este mismo host (`geoweb.montevideo.gub.uy/geoserver`) devolvió «Empty reply»: el servicio vivo es el de `montevideo.gub.uy/app/geoserver`.

### 2.3 Visor MontevIMap y portal SIG
- `https://montevimap.montevideo.gub.uy/` redirige a `https://montevideo.gub.uy/app/mapas/#/viewer/26` (visor MapStore; las capas salen del WFS de arriba). `https://sig.montevideo.gub.uy/` responde, y su página de geoservicios (`geoservicios-ogc.html`) trae el aviso de «temporalmente fuera de servicio / solo Intranet». `sig.montevideo.gub.uy/arcgis/rest/services` da 404 (no hay ArcGIS REST).

### 2.4 No respondieron desde este entorno
| Host | Resultado |
|---|---|
| `www.catastro.gub.uy` (DNC) | conexión reiniciada (reset) |
| `www.ide.uy` | conexión reiniciada |
| `geoservicios.ide.uy` | 502 del proxy al CONNECT (política o servidor caído) |
| `documentos.montevideo.gub.uy` | 502 del proxy |
| `normativa.montevideo.gub.uy`, `geoweb…/geoserver` | respuesta vacía |
| `catalogodatos.gub.uy`, `visualizador.ide.uy` | la portada respondió 200; no se exploró nada más |

## 3. Riesgos
- **Sin garantía de servicio:** el portal avisa que los geoservicios de Internet están «temporalmente» solo en Intranet; el WFS de `montevideo.gub.uy/app/geoserver` es el de MapStore y puede cambiar de dirección, capas o campos sin aviso. Hay que tolerar fallos y dejar la carga a mano / DXF (R1.5).
- **Códigos sin documentar:** `retiro`, `altura`, `fos`, `usopre`, `rgs`, `promo` son texto («4», «9-12», «60», «MC», «RGE», «PEMI»). Hay que validarlos con el Digesto o el CITIM antes de usarlos; el parcelario puede tener errores (aviso del metadato); los retiros reales pueden depender de alineaciones y régimen de excepción (capas aparte).
- **Padrón repetido:** no se comprobó si el número puede repetirse (rural / urbano o por localidad); la consulta devolvió 1 para 421264.
- **Linderos y medianeras:** el servicio da el polígono, no cuáles linderos son medianeras; habría que deducirlos con calles / aceras / puertas.

## 4. Propuesta de diseño (provisoria)
- `GET /api/padron?numero=421264` en `server.py`: dos GetFeature (parcela y `cat_suelo`) con `urllib.request`, timeout corto, GeoJSON con `json`; error claro en español si no hay red o el servicio cambió.
- Devuelve lo que espera `/api/mass`: `footprint` en metros UTM (antihorario, sin el vértice repetido), `medianeras` deducidas de los linderos sin frente a calle, `name` = «Padrón N», y `normativa` {dato: {valor, fuente, fecha}} con `retiro`, `altura`, `fos`, `usopre`, `categoria`, `area_diferenciada` y la fecha de la consulta.
- Panel Normativa: mostrar esos valores con su fuente y fecha, sin aplicarlos solos; el retiro y la altura se copian a los controles si el usuario lo pide. Lo que el servicio no da (medianeras dudosas, retiros especiales) queda a mano.
- Tamaño: **M** (una ruta, un parser GeoJSON, la deducción de medianeras y la tabla de normativa; las pruebas con respuestas guardadas en `tests/`). Decisión del usuario pendiente: aceptar depender de un servicio público sin garantía.
