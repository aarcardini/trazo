# Padrón de Montevideo — servicios abiertos para R1.6

Investigación del 23 de octubre de 2026 para ver si Trazo puede traer, a partir de un **número de padrón**, el polígono del lote y los parámetros urbanísticos (retiros, FOS, altura, uso) desde un servicio abierto de la Intendencia de Montevideo (IM) o del Estado, **solo con la biblioteca estándar de Python** y desde el servidor local (`urllib`, `json`).

Cómo leer las cifras:
- **(F)** dato observado en la respuesta de la fuente. **(D)** derivado por nosotros a partir de lo observado. **(S)** supuesto o interpretación sin fuente; hay que confirmarlo.
- Las pruebas son del 23/10/2026 desde un entorno con proxy de salida; cada consulta tardó entre 0,6 y 2,1 s y una dio un `TimeoutError` en el saludo TLS (ver riesgos). Las respuestas crudas están fuera del repo, en `scratchpad/out/padron/` (las citadas abajo llevan su nombre de archivo). Los scripts de prueba (`urllib` solo, sin dependencias) están en `scratchpad/scripts_padron/` y no forman parte del repositorio.

## 1. Resumen ejecutivo

**Es viable, con una advertencia sobre los parámetros.**

- **Polígono del lote: sí, y es sólido.** El GeoServer de la IM (`https://montevideo.gub.uy/app/geoserver/wfs`) publica las 208 596 parcelas de Montevideo (F). Se pide con un GET, sin clave ni registro, y devuelve GeoJSON en **EPSG:32721 (UTM 21 S, metros)** (F), el mismo sistema en el que Trazo ya trabaja sin mover coordenadas. Una consulta por padrón pesa 1 kB o menos. Probado con `urllib.request` solo y con 8 padrones reales (§3).
- **Parámetros urbanísticos: sí, pero de una capa que parece heredada.** La capa `mapstore-tematicas:ot_v_mdg_parcelas_cat_suelo` trae por padrón `categoria`, `sub_categoria`, `area_diferenciada`, `rgs`, `retiro`, `altura`, `fos`, `usopre` y otros, como texto (F). Hay tres problemas: (1) el visor MontevIMap ya no la usa (sus capas de categoría y subcategoría pasaron al espacio `citim:`, y retiros, alturas y FOS se muestran con tres capas «CITIM 03/2026» de solo visualización); (2) en esas capas de visualización, **alturas y FOS no se pueden consultar por punto** (`QUERY_LAYERS` no soportado) y solo los retiros sí; (3) **en 1 de 7 padrones el retiro de `cat_suelo` no coincide con el de la capa CITIM 03/2026** (65411: 7 m contra 5 m). Es decir: sirve como dato **orientativo**, no como el certificado.
- **El certificado oficial no se puede automatizar.** El «Certificado de información territorial integral de Montevideo» (CITIM) se obtiene en `https://informacionterritorial.montevideo.gub.uy/app/citim/` con un formulario protegido por reCAPTCHA (F); el formulario viejo (`regulacionterritorial…/BInforme.php`) ya solo remite al CITIM (probado con 4 padrones). Para un permiso de construcción vale ese certificado o el informe de alineaciones y parámetros (150 días de validez), no un dato del WFS. Trazo puede mostrar los parámetros, nunca reemplazarlo; y no se intenta saltear el reCAPTCHA.
- **Medianeras y frente: se deducen, no vienen.** Con la misma capa de parcelas (los vecinos de la caja del lote) y los puntos de numeración de puertas se separan los linderos con vecino (posibles medianeras) de los que dan a calle. Probado en 5 padrones, con resultados coherentes (§5); un lote en esquina da dos frentes. Siempre hay que dejarlo editable.
- **Licencia:** «De uso libre según resolución 640/10 del Intendente Municipal de Montevideo de fecha 22/02/2010» (F, metadato del catálogo de la IM); el catálogo nacional lo publica con la «Licencia de Datos Abiertos de Uruguay» (`odc-uy`, F). Se pide citar la fuente.
- **Respaldo sin servicio en vivo:** la Dirección Nacional de Catastro (DNC) publica el parcelario de todo el país en SHP y DXF en el catálogo nacional (112 MB en SHP, actualizado el 20/10/2026), pero en coordenadas geográficas SIRGAS-ROU98, sin parámetros urbanísticos y con el padrón repetido entre departamentos (§2.5).
- **Tamaño propuesto: M** para el WFS (ruta, lector GeoJSON, deducción de medianeras, panel de Normativa y pruebas con respuestas guardadas); el respaldo con el shapefile local sería un **S/M** aparte. Decisión pendiente del usuario en §8.

## 2. Servicios

### 2.1 GeoServer de la IM, WFS (el que sirve)
- **Dirección:** `https://montevideo.gub.uy/app/geoserver/wfs` (también `…/ows`; hay un WMS en `…/wms`). GeoServer; `GetCapabilities` en WFS 1.1.0 (187 kB, 205 capas: `im_wfs_capas.txt`); `GetFeature` en WFS 2.0.0 con `outputFormat=application/json` (F). También ofrece `csv` (probado) y `SHAPE-ZIP` (figura en la ficha de la IM; no probado).
- **Clave o registro:** ninguno. Respondió desde aquí: sí.
- **Coordenadas:** EPSG:32721 salvo `ot_retiros_desde_1947` y `retiros_1947` (EPSG:31981); GeoJSON con `"crs": "urn:ogc:def:crs:EPSG::32721"`. El WFS acepta filtros CQL (`cql_filter=padron=421264`, `BBOX(...)`, `ILIKE`, `IN (...)`) y `propertyName`, `count`, `startIndex`.
- **Capas útiles** (campos de `DescribeFeatureType`):
  - `mapstore-base:cb_v_mdg_parcelas_citim` («Padrones»): `gid`, `padron` (int), `the_geom` (polígono), `areatot` (m², de la geometría), `areacat` (m², catastral), `ph` (0/1, propiedad horizontal), `imponible`, `carpeta_ph`.
  - `mapstore-tematicas:ot_v_mdg_parcelas_cat_suelo` y `…_subcat_suelo`: lo anterior más `categoria`, `sub_categoria`, `area_diferenciada`, `cortado_rn`, `rn_area_diferenciada`, `rgs`, `retiro`, `galibo`, `altura`, `fos`, `usopre`, `planesp`, `planparcial`, `promo`, `fis`, `nom_trans`, `tipo_trans`, `estado_trans`.
  - `mapstore-base:cb_v_mdg_accesos_puerta` («Números de puerta»): punto por puerta con `padron`, `num_puerta`, `letra`, `nom_calle`, `concatenado`, `gid_tramo_via`. Sirve para **buscar por dirección** (`nom_calle ILIKE '%BARRIOS AMORIN' AND num_puerta=1162`; los nombres vienen en mayúsculas y sin tildes, con título: «DR JAVIER BARRIOS AMORIN»).
  - `mapstore-base:cb_v_sig_vias` (ejes de calle: `nom_calle`, `tipo`), `cb_v_sig_aceras`, `cb_v_sig_manzanas_materializadas`, `mapstore-tematicas:ic_v_mdg_manzanas`.
  - `mapstore-tematicas:ot_v_pat_constanciars` (`padron`, `rgs`, `mhn_bid`, `lindero`, `ap`, `cautela`, `aec`: patrimonio), `ot_retiros_desde_1947`, `ot_ret_exoneracion_retiros`, `ot_v_sig_alineaciones`, `ic_v_ce_permisos_construccion_geom`, `ic_v_sca_djcu_mayo2023`.
  - Espacio `citim:` (categorías, subcategorías, áreas diferenciadas de suelo, suelo potencialmente transformable, grados de protección de Centro y Ciudad Vieja): polígonos de zona, sin número de padrón.
- **Petición de ejemplo (real):**
  `GET https://montevideo.gub.uy/app/geoserver/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=mapstore-tematicas:ot_v_mdg_parcelas_cat_suelo&cql_filter=padron=421264&outputFormat=application/json`
  Respuesta recortada (`padron_421264_cat_suelo.json`):
  ```json
  {"type":"FeatureCollection","numberMatched":1,"numberReturned":1,"crs":{"type":"name","properties":{"name":"urn:ogc:def:crs:EPSG::32721"}},
   "features":[{"geometry":{"type":"Polygon","coordinates":[[[574591.7216342,6144572.4917357],[574609.087147,6144565.1541117],[574600.9522971,6144555.1739012],[574588.6803246,6144565.1767707],[574591.7216342,6144572.4917357]]]},
    "properties":{"gid":25858464,"padron":421264,"areatot":177,"areacat":196,"ph":0,"categoria":"U","sub_categoria":"SUCIn","area_diferenciada":"Casavalle Piedras Blancas- Manga","rgs":"RGE","retiro":"4","galibo":null,"altura":"9-12","fos":"60","usopre":"MC","promo":"PEMI"}}]}
  ```
- **Padrón inexistente:** HTTP 200 con `numberMatched: 0` (probado con 99999999). **Unicidad:** el número de padrón no se repite en la capa (30 000 filas de muestra, sin repetidos) (F).
- **Qué no hay:** los datos de PH por unidad (la capa tiene el padrón madre; la propia IM pide no ingresar el número de unidad), ni nada de lo que dice el CITIM sobre afectaciones y alineaciones (la capa de alineaciones es de líneas sin padrón).

### 2.2 Capas «CITIM 03/2026» de visualización (solo WMS)
- Espacio `citim_no_descargable` (`…/app/geoserver/citim_no_descargable/ows`): `ot_citim_vis_FOS` («Factor de ocupación del suelo 03/2026»), `ot_citim_vis_alturas` («Alturas máximas 03/2026») y `ot_citim_vis_retiro` («Retiros frontales 03/2026»). En MontevIMap su ventana de información está desactivada (`featureInfo.format = HIDDEN`).
- Su **leyenda** (`GetLegendGraphic`, `format=application/json`) dice qué significa cada código (F, §4): `leyenda_ot_citim_vis_*.json`.
- `GetFeatureInfo` funciona solo con `ot_citim_vis_retiro` (devuelve `{"retiroDSC": "4 metros", "retiro": "4"}`); con alturas y FOS responde `OperationNotSupported … no layer was queryable` (F). El nombre del espacio y esa restricción indican que la IM no quiere que se descarguen: **no usarlas como fuente** (solo la leyenda, para entender los códigos).

### 2.3 Catálogo de datos geográficos de la IM (GeoNetwork)
- `https://geoweb.montevideo.gub.uy/geonetwork` (GeoNetwork 3.12.1). Respondió (CSW 2.0.2 `GetCapabilities`, búsqueda `/srv/spa/q?_content_type=json&fast=index&any=padron`, ficha ISO `/srv/api/records/<uuid>/formatters/xml`). Su GeoServer (`geoweb…/geoserver`) devolvió respuesta vacía: el vivo es el de `montevideo.gub.uy/app/geoserver`.
- Fichas leídas: «GEOMETRIA DE PARCELAS» (639c4c9f-fda9-4d2f-b1da-40acabc208c3) y «PADRONES» (6b49748c-6fb7-41e4-9540-29656de8ad74), del Servicio de Catastro y Avalúo (imcatastro@imm.gub.uy): EPSG:32721, actualización mensual, licencia de uso libre (res. 640/10), y la advertencia «esta información puede contener errores; errores u omisiones deberán ser señalados al Servicio de Catastro y Avalúo». También existe «CONSTANCIA DE RÉGIMEN DE SUELO» (81c7c741-334e-46ba-aece-661540691546).
- Enlaces de descarga que cita: shapefile de parcelas `https://intgis.montevideo.gub.uy/sit/php/common/datos/generar_zip2.php?nom_tab=v_mdg_parcelas_geom&tipo=gis` (genera un zip al vuelo; no se descargó) y `…/wfs?…&outputFormat=SHAPE-ZIP`.

### 2.4 MontevIMap, ficha web del padrón y CITIM oficial
- `https://montevimap.montevideo.gub.uy/` redirige a `https://montevideo.gub.uy/app/mapas/#/viewer/26` (MapStore). Su configuración (`/app/mapas/rest/geostore/data/26`, 304 capas) está publicada y es la que permitió encontrar las capas anteriores.
- Ficha «Datos territoriales del padrón» (HTML que arma el servidor de la IM: `intgis.montevideo.gub.uy/sit/aplicaciones/montevimap/formularios_mapstore/padrones.php?gid=<gid>&…&_fragment=1`; guardada en `ficha_padron_421264_fragmento.html`): número, CCZ, municipio, carpeta catastral, área DNC, régimen de propiedad, planos de mensura, **direcciones**, categoría, subcategoría, área diferenciada y régimen de gestión («Régimen General» para 421264). **No muestra retiro, altura ni FOS**: remite a la solicitud del informe. Dice: «puede existir algún desfasaje transitorio entre la información vigente y la que contiene el formulario».
- Certificado oficial: trámite «Informe de alineaciones y parámetros para suelo urbano» (`tramites.montevideo.gub.uy`, costo $ 1.552, validez 150 días, «no se expiden informes para predios en régimen patrimonial»); se obtiene por el CITIM (reCAPTCHA v3) o, si no está, por correo a uit@imm.gub.uy. La Resolución 0796/23 fija que la información territorial «se obtiene de la página web de la IM» y se expide solo para régimen general.
- La página SIG (`sig.montevideo.gub.uy/geoservicios-ogc.html`) dice **«Geoservicios en Internet temporalmente fuera de servicio… disponibles solo para usuarios de Intranet»**, aunque el WFS de §2.1 respondía el 23/10/2026. No hay ArcGIS REST (`/arcgis/rest/services`: 404).

### 2.5 Catálogo nacional de datos abiertos (`catalogodatos.gub.uy`) y DNC
- API CKAN pública (`/api/3/action/package_search`, `package_show`), sin clave, respondió. Conjuntos útiles (todos con licencia `odc-uy`, F):
  - **«Parcelas catastrales» (IM)**: shapefile de polígonos, único dato el número de padrón, actualización mensual; enlace al mismo `generar_zip2.php` de §2.3.
  - **«Shapes del parcelario rural y urbano» (DNC)**: `paisurbano_shp.zip`, 112 142 858 bytes, actualizado el 20/10/2026, con `Accept-Ranges`. Dentro: `PaisUrbano.shp/.dbf/.shx/.prj/.cpg`; 1 052 399 registros (padrón urbano de todo el país); campos `NOMDEPTO`, `CODDEPTO`, `NOMLOCCAT`, `CODLOCCAT`, `PADRON`, `NUMCARCAT`, `NUMMANCAT`, `AREA`, `REGIMEN`. **Coordenadas geográficas SIRGAS-ROU98** (grados; leído del `.prj` con peticiones por rango, sin bajar los 112 MB). El padrón solo es único dentro de departamento y localidad catastral.
  - «DXF del parcelario urbano y rural» (DNC): `paisurbano_dxf.zip`, 152 MB.
  - «Direcciones oficiales de Montevideo» (IM): shapefile de puntos (calle, número, padrón).
- Sirve de **respaldo sin servicio en vivo**, no de fuente principal: pesa mucho, hay que convertir grados a UTM (fórmula propia en la biblioteca estándar) y no trae ningún parámetro urbanístico.

### 2.6 IDE Uruguay y Catastro: no respondieron
| Host | Resultado desde este entorno |
|---|---|
| `www.catastro.gub.uy`, `visualizador.catastro.gub.uy` (DNC) | reinicio de conexión / rechazo del proxy |
| `www.ide.uy`, `geoservicios.ide.uy` | reinicio de conexión / 502 del proxy |
| `visualizador.ide.uy` | la portada responde; `…/geoserver/ows` da 404 |
| `documentos.montevideo.gub.uy`, `normativa.montevideo.gub.uy` (Digesto) | 502 / respuesta vacía |
| `www.gub.uy/infraestructura-datos-espaciales/` | responde (HTML), sin servicios WFS que citar |
No se pudo leer el Digesto Departamental desde aquí; los significados de §4 salen de las leyendas del propio GeoServer.

## 3. Padrones de prueba
Todos con `urllib` (script `contraste.py`) y guardados en `padron_<n>_parcela.json` y `padron_<n>_cat_suelo.json`. «CITIM retiro» es el `GetFeatureInfo` de `ot_citim_vis_retiro` en el centro del lote.

| Padrón | Dónde (por puerta) | Área geom. / catastral | Zona | `retiro` | `altura` | `fos` | `usopre` | `rgs` | CITIM retiro |
|---|---|---|---|---|---|---|---|---|---|
| **421264** | Sara Otermin 3953 / Pedro Fuentes 1521 (esquina, Casavalle) | 177 / 196 m² | SUCIn · Casavalle Piedras Blancas-Manga | 4 | 9-12 | 60 | MC | RGE | 4 metros |
| **432478** | Dr. Javier Barrios Amorín 1162, Palermo/Centro (**proyecto «Barrios Amorín»**, `data/tipologias/BarriosAmorin_nota.md`: «lote de 237 m²») | 232 / 238 m² | SUCCe · Centro | 0 | 27 | 100 | PF | RPU | 0 metros |
| 1531 | Barrios Amorín 1160 | 120 / 116 m² | SUCCe · Centro | 0 | 27 | 100 | PF | RPU | – |
| 1391 | Constituyente 1704-1710, Cordón | 115 / 127 m² | SUCCe · Centro | 0 | 31 | 100 | PF | RGE | 0 metros |
| 32512 | Benito Blanco 909 / Bv. España 2947, Pocitos (esquina) | 111 / 144 m² (PH) | SUCCo · Pocitos | 4 | 31 | 80 | RSEC | RGE | 4 metros |
| 65411 | Dr. Alejandro Gallinal 2485-2495 (la IM lo ubica en Malvín Norte; misma calle que el proyecto M5, que dice Punta Gorda, pero **no** es M5: su nota no da número) | 568 / 521 m² | SUCIn · Malvín Norte-La Cruz | **7** | 9-12 | 60 | RSEC | RGE | **5 metros** (no coincide) |
| 9202 | Isla de Flores 1381, Palermo (misma calle que el proyecto «Isla de Flores», no es ese lote) | 2 861 / 2 880 m² | SUCCe · Barrio Sur-Parque Rodó-Palermo | 0 | 9 | 100 | RSEC | RPU | Patrimonial |
| 9108 | Av. 18 de Julio 1360 (Palacio Municipal) | 18 581 / 19 951 m² | SUCCe · Centro | RET.ESP. | ALT.ESP. | 100 | PF | RPU | – |

- **El padrón 432478 es el lote del proyecto «Barrios Amorín»** (F/D): el área catastral 238 m² (232 m² por geometría) coincide con los 237 m² de la nota; la altura 27 m coincide con un edificio de planta baja y 9 pisos; la fachada de 13 m da a la calle. Polígono (UTM, m): `(574547.63, 6136752.91) (574529.70, 6136752.87) (574529.15, 6136758.97) (574528.54, 6136765.87) (574552.98, 6136762.68) (574553.04, 6136759.90) (574551.18, 6136759.74) (574546.96, 6136759.62)`. La numeración «1168» de la nota no figura entre las puertas oficiales: el lote tiene la puerta 1162 y un número de padrón alto, probablemente nuevo por fusión (S).
- **Padrón de prueba pedido, 421264:** polígono de 4 lados `(574591.72, 6144572.49) (574609.09, 6144565.15) (574600.95, 6144555.17) (574588.68, 6144565.18)`; lado de 7,9 m, 15,8 m, 12,9 m y 18,9 m; esquina entre dos calles.
- **Contraste con MontevIMap/CITIM.** No se pudo obtener el CITIM del padrón (reCAPTCHA) ni la ficha de parámetros (el visor y la ficha web no muestran altura ni FOS por padrón). Lo que se pudo comparar: **retiro** con la capa CITIM 03/2026, en 7 padrones (los seis de la tabla con celda CITIM más el 7968, 18 de Julio 1361): 4 coinciden, 2 dicen «Patrimonial» donde `cat_suelo` dice `0` (9202 y 7968) y **1 difiere en valor (65411: 7 contra 5)**. La categoría, subcategoría, área diferenciada y régimen de gestión de 421264 coinciden con la ficha web de la IM («Suelo Urbano Consolidado Intermedio», «Casavalle Piedras Blancas-Manga», «Régimen General»). Altura y FOS no se pudieron contrastar con ninguna fuente pública consultable; las leyendas sí confirman que sus valores existen en el catálogo CITIM (§4).

## 4. Significado de los códigos de `cat_suelo`
De las leyendas del GeoServer (`GetLegendGraphic`), de la ficha web y del contraste de §3.
- `categoria`: R rural, S suburbano, U urbano (F). `sub_categoria` (F): RN rural natural, RP rural productivo, RI rural de interfase, RIC rural de interfase costero, SUH suburbano habitacional, SUNH no habitacional, SUNHI no habitacional intensivo, SUNHS no habitacional de servicios, **SUCCe urbano consolidado central**, **SUCCo costero**, **SUCIn intermedio**, SUCO otros, SUNC no consolidado.
- `retiro` (retiro **frontal**, en metros) (F, leyenda CITIM): «0» a «40»; el sufijo **CA** es «con acordamiento Art. D.223.130» (`5CA` = 5 m con acordamiento, `4CA`, `7CA`); `CEP` es otro código sin leyenda (aparece a la vez en `retiro`, `altura` y `fos` de ~4,5 % de las filas de la muestra); `PATRIMONIAL`, `PAU9`/`PAU 10`, textos «Ver Art. D.223.202» y «D.223.207» remiten a otra norma. En una muestra de 30 000 filas (`startIndex=60000`, no aleatoria): `5CA` 59 %, `5` 15 %, vacío 11 %, `CEP` 4,5 %, `4` 4,4 %, `4CA` 3,9 %, `15` 1,4 %.
- `altura` (metros, máximos) (F): un número («9», «27», «13.50») o un **rango «9-12»** (leyenda: «9 a 12 metros»; la leyenda no explica de qué depende; **(S)** puede depender de las condiciones de cada predio y no se debe tomar el máximo sin consultar); también `ESPECIAL`/`ALT.ESP.`/`Esp 218`, `PATRIMONIAL`, `PAU10`, `Art.202`, `Art.204.5`, `Art.207`.
- `fos` (F): porcentaje entero («100», «80», «60», «15») o escalones por superficie del predio en suelo rural y suburbano (códigos con **R**, p. ej. `35R`: «hasta 0,5 ha: 35 % con máximo 1 250 m²; …»), `ALDR` («área libre de retiros»), `PATRIMONIAL`, `PAU10`, `PUDAN`, `PM7`, `PPC`.
- `usopre` (uso preferente): valores vistos `RMC`, `MC`, `RSEC`, `PF`, `AGR`, `IND`, `LG`, `LGIND`, `R1`, `M`. **Sin leyenda pública (S):** no se puede dar la expresión; se muestra el código tal cual. `rgs` (régimen): `RGE` aparece con «Régimen General» en la ficha de la IM (F); `RPU`, `RPR` y `RA` sin leyenda: en 2 de los 3 padrones con `RPU` que se compararon el CITIM dice «Patrimonial» y en el otro no, así que **no se interpreta (S)**. `promo` (`APHB`, `PEMI`, `APMC`), `galibo` (`G`), `planesp` (`PR`, `PR_ant`, `18J`) y `fis`: sin leyenda.

## 5. Medianeras y frente: cómo deducirlos
Probado con `linderos.py` (solo `urllib`, `math`) sobre 5 padrones; no se lee ningún dato del que no se disponga hoy.
1. Se pide la parcela y las **vecinas dentro de la caja del lote ampliada 3 m** (`BBOX(the_geom, …) AND padron<>N`, ≤ 6 resultados en las pruebas).
2. Para cada borde del polígono (antihorario) se muestrea cada 0,25 m y se mide qué fracción queda a menos de 0,4 m del contorno de alguna vecina. **≥ 70 %: lindero con vecino** (candidato a medianera); < 30 %: **sin vecino** (calle u otro espacio público); en el medio, dudoso.
3. Se confirma el frente con los **puntos de numeración de puertas** del propio padrón (`cb_v_mdg_accesos_puerta`): el borde sin vecino que tiene una puerta a ≤ 0,5 m es el frente (con su `nom_calle`). Un lote en esquina da dos frentes.
Resultados (F): 432478 → 6 bordes con vecino (6,7; 4,2; 1,9; 2,8; 24,7 y 17,9 m) y 2 colineales sin vecino (6,9 + 6,1 m, puerta a 0,3 m): un frente de 13 m y el resto lindero; 421264 → 2 bordes con vecino y 2 frentes (Sara Otermin, Pedro Fuentes); 1531 → 1 frente de 6,6 m; 32512 → 2 frentes y 2 linderos; 1391 → dos lados sin vecino (9,6 m y 13,2 + 0,9 m) con puertas a ≤ 0,5 m: lote en esquina o con dos frentes (no verificado). Fallos posibles (S): un lindero con un baldío sin parcela, un pasaje o una servidumbre aparece como «sin vecino»; una vecina que retrocede de la línea oficial aparece como «parcial». Por eso el resultado es una **propuesta editable**, con los bordes dudosos señalados.
- La capa de **ejes de calle** (`cb_v_sig_vias`, con `nom_calle` y `tipo`) sirve para el rumbo de la calle; las aceras (`cb_v_sig_aceras`) dieron un tiempo agotado en la única prueba y no son necesarias.

## 6. Cómo se consulta con la biblioteca estándar
- `urllib.request.urlopen(url, timeout=20)` con `urllib.parse.urlencode` y `json.loads`: alcanza para todo lo de arriba (F, probado en Python 3.13). El proxy del entorno de pruebas lo toma `urllib` de `HTTPS_PROXY`; en la computadora del usuario no hay proxy y vale el almacén de certificados del sistema.
- Sin `xml.etree` ni dependencias: se pide JSON, no GML. Para la leyenda, JSON también.
- Tiempos medidos: 0,6–2,1 s por consulta; una consulta falló con `TimeoutError` en el saludo TLS (transitoria, al repetir respondió). Hay que poner un tiempo máximo de 20 s, un reintento y un mensaje en español que diga qué hacer.
- **Normas de cortesía:** una consulta por padrón (2 o 3 peticiones pequeñas), con `User-Agent: Trazo/<versión>`; no descargar la capa completa ni usar las capas «no descargables».

## 7. Riesgos
1. **Servicio sin garantía.** La propia IM dice que los geoservicios de Internet están «temporalmente solo en Intranet» (§2.4) y el visor ya reemplazó las capas `ot_v_mdg_parcelas_cat_suelo` por `citim:`. El WFS puede cambiar de dirección o cerrarse sin aviso. Mitigación: tratar la dirección y los nombres de capa como configuración (`standards` o `params`), probar con respuestas guardadas y dejar siempre la carga a mano y el DXF (R1.5).
2. **Los parámetros pueden estar desactualizados o ser incorrectos** (7 contra 5 m en el padrón 65411) y no son el certificado: el permiso exige el CITIM / informe de alineaciones. Trazo debe decirlo en el panel («orientativo; validar con el CITIM»).
3. **Códigos sin leyenda** (`usopre`, `rgs`, `promo`, `CEP`) y valores no numéricos (`5CA`, `9-12`, `ALT.ESP.`, `35R`, `PATRIMONIAL`): hay que mostrarlos tal cual y no aplicarlos solos; con régimen patrimonial no hay informe oficial.
4. **Capa con aspecto de heredada y alturas/FOS «no descargables» en CITIM:** usar `cat_suelo` para altura y FOS va contra lo que parece la intención de la IM; conviene consultar a la Unidad de Información Territorial (uit@imm.gub.uy) y al Servicio de Geomática (sig@imm.gub.uy) antes de depender de ella.
5. **Licencia y atribución:** uso libre, con cita de fuente: «Intendencia de Montevideo, Servicio de Catastro y Avalúo; Dirección Nacional de Catastro»; el catálogo nacional pide la «Licencia de Datos Abiertos de Uruguay».
6. **Coordenadas:** el WFS de padrones está en EPSG:32721; algunas capas de retiros históricos en EPSG:31981 (otro huso) y el parcelario de la DNC en grados SIRGAS-ROU98. Solo se usa 32721.
7. **Geometría:** una parcela puede ser MultiPolygon, tener huecos (patios) o vértices casi colineales; PH da el padrón madre (unidades no están); `areatot` de la geometría y `areacat` difieren (232 / 238, 111 / 144): usar la geometría para dibujar y avisar si la diferencia pasa de ±10 %.
8. **Privacidad:** el número de padrón sale de la computadora del usuario hacia un servicio público; las consultas llevan su dirección IP. Es un dato público, pero hay que decirlo.

## 8. Propuesta de diseño para R1.6

**Tamaño: M** (una ruta nueva, un lector, la deducción de medianeras, un bloque de la interfaz y pruebas con respuestas guardadas; menos de ~300 líneas). El respaldo con shapefile local es un S/M aparte (no incluido).

### Servidor
- `GET /api/padron?numero=421264` (también `?direccion=` en una segunda etapa, con calle y número sobre `cb_v_mdg_accesos_puerta`). Módulo nuevo `engine/padron.py` (biblioteca estándar; la entrada de red inyectable, para probar sin red) y la ruta en `server.py`, que hace las peticiones: la web no sale a internet.
- Devuelve lo que `/api/mass` espera, con `source: "padron"` (como el DXF) y `mass_version` + 1:
  - `footprint`: anillo exterior en metros UTM, antihorario, sin el vértice repetido; si es MultiPolygon, la parte mayor con aviso; los huecos se avisan.
  - `medianeras`: [{a, b, retiro: 0}] de los bordes con vecino ≥ 70 %, por tramo (el formato de `dxf_lector`); los dudosos van en `warnings` («lado de 3,2 m sin vecino claro: confirmar») y los frentes en `frentes` [{a, b, calle, largo}].
  - `name`: «Padrón 421264», más `direcciones` [{calle, numero}] y el área catastral y la medida.
  - `normativa`: {`categoria`, `sub_categoria`, `area_diferenciada`, `regimen`, `retiro_frontal`, `altura`, `fos`, `uso_preferente`}, cada una como {`valor` (texto original), `numero` (el número, si lo hay), `fuente` («IM, GeoServer, capa ot_v_mdg_parcelas_cat_suelo»), `fecha` (de la consulta), `nota` («orientativo; validar con el CITIM»; «código sin leyenda»)}.
  - `avisos`: servicio caído → 502 con `error` en español («Trazo: no se pudo consultar el padrón de la Intendencia: … Cargue el terreno a mano o con “Abrir DXF…”»); padrón inexistente → 404 «El padrón N no figura en el parcelario de Montevideo (si es una unidad de propiedad horizontal, use el padrón madre)».
- Sin cambios al formato de `/api/generate` ni a lo que Rhino manda; `normativa` es una clave nueva y optativa (compatible).

### Web (`web/index.html`)
- Botón «Abrir padrón…» junto a «Abrir DXF…» (Proyecto): pide el número; `setMass(m, true)` con la respuesta, como `leerDxf`; origen «Padrón» en el selector y avisos con «Padrón:» antes de los del resultado.
- **Panel Normativa:** una sección «Datos del padrón» (solo si hay `normativa`) con cada dato, su fuente y su fecha, y el aviso «orientativo, no reemplaza al CITIM» con el enlace oficial. Botones «Aplicar retiro frontal de X m» (con el desfase existente de R10.8) y «Usar altura de X m»: solo con valores numéricos simples; los códigos (`5CA`, `9-12`, `ALT.ESP.`) se muestran sin aplicar. El FOS y la altura se comparan con el resultado («FOS usado 71 % de 60 %») como aviso, sin cambiar la planta.
- Las medianeras propuestas se dibujan como las de Rhino y se editan con las herramientas existentes; el proyecto guarda `padron` (número, fuente, fecha) para reabrirlo sin red.

### Qué queda a mano si el servicio no da algo
Padrón inexistente o PH, servicio caído, régimen patrimonial, valores con código, medianeras dudosas, retiros laterales y de fondo (el servicio solo da el frontal) y alturas con rango: el usuario carga el terreno y los números a mano (terreno rectangular, R1.5 DXF o Rhino), como hasta ahora.

### Orden sugerido
1. Pruebas con respuestas guardadas en `tests/` (los JSON de este documento, 3 o 4 padrones) y el lector. 2. Ruta y botón. 3. Medianeras. 4. Panel de Normativa. 5. Dirección y respaldo con shapefile (aparte).

### Decisiones pendientes del usuario
1. **¿Aceptar depender de un servicio público sin garantía** (que la propia IM marca como «temporalmente solo Intranet» y cuya capa de parámetros parece heredada)? Si no, el alcance baja a polígono + medianeras (el WFS de parcelas sí figura como dato abierto con licencia) o a solo respaldo con shapefile.
2. **¿Mostrar altura, FOS y uso aunque sean orientativos** y no coincidan siempre con el CITIM (1 de 7 padrones con retiro distinto), o limitarse a categoría y retiro frontal?
3. **¿Escribir antes a la IM** (uit@imm.gub.uy, sig@imm.gub.uy) para preguntar si la capa y los campos son de uso previsto y estables? Recomendado antes de la etapa 4.
4. Si la deducción de medianeras es «propuesta editable» o «solo señalar los lados con vecino».
