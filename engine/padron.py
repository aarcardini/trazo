"""Padrón de Montevideo (R1.6): el lote de un número de padrón como masa de Trazo. Solo biblioteca estándar.

`consultar(numero)` pide al GeoServer público de la Intendencia de Montevideo (WFS, GeoJSON en EPSG:32721 = UTM 21 S, el
sistema en el que Trazo ya trabaja) la parcela del padrón, las parcelas vecinas de su caja, los números de puerta del propio
padrón y los datos de suelo (categoría, retiro, altura, FOS, uso), y devuelve lo mismo que `dxf_lector.leer` (`footprint`
antihorario en metros, `medianeras`, `name`, `warnings`) más `source: "padron"` y `padron` (fuente, fecha, áreas, direcciones,
frentes, el lote tal cual y la normativa con la fuente y la fecha de cada dato). Detalle de los servicios y de los códigos en
PADRON.md.

Solo la parcela es obligatoria: sin las vecinas no se deducen medianeras, sin la capa de suelo `normativa` es None, sin las
puertas los frentes no llevan el nombre de la calle; cada falta se avisa en `warnings`. Padrón inexistente o servicio caído
levantan `ErrorPadron` con un mensaje en español que dice qué hacer (carga a mano o DXF).

Medianeras y frentes se DEDUCEN (PADRON.md §5): por cada lado del polígono, qué fracción de sus puntos queda a menos de 0,4 m
del contorno de alguna vecina. Con vecino (70 % o más) es medianera, sin vecino (menos de 30 %) es frente (calle) y en el
medio queda dudoso y se avisa. Es una propuesta que el usuario edita. Los parámetros urbanísticos son orientativos: no
reemplazan al CITIM (certificado oficial de la Intendencia).

`aplicar_retiro(masa, retiro)` es una función pura (sin red): corre los frentes del lote hacia adentro. La red se inyecta
(`RED`, o `red=`) para probar con respuestas guardadas (`tests/padron/`)."""
import copy
import datetime
import json
import math
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

from . import geometry as G

WFS = "https://montevideo.gub.uy/app/geoserver/wfs"
CAPAS = {"parcelas": "mapstore-base:cb_v_mdg_parcelas_citim",
         "cat_suelo": "mapstore-tematicas:ot_v_mdg_parcelas_cat_suelo",
         "puertas": "mapstore-base:cb_v_mdg_accesos_puerta"}
FUENTE = "Intendencia de Montevideo, Servicio de Catastro y Avalúo (GeoServer WFS, uso libre res. 640/10)"
FUENTE_NORMATIVA = "IM, GeoServer, capa ot_v_mdg_parcelas_cat_suelo"
CITIM = "https://informacionterritorial.montevideo.gub.uy/app/citim/"
NOTA = "orientativo; validar con el CITIM"
TIEMPO = 20.0            # s por petición
PAUSA = 0.5              # s antes del reintento
MARGEN_CAJA = 3.0        # m: la caja del lote, ampliada, donde se buscan las vecinas
MUESTREO = 0.25          # m entre los puntos que se prueban en cada lado
TOL_VECINO = 0.4         # m: un punto "toca" a una vecina si está a esto o menos de su contorno
CON_VECINO = 0.70        # fracción de puntos con vecino desde la que el lado es lindero (medianera)
SIN_VECINO = 0.30        # fracción de puntos con vecino por debajo de la que el lado es frente (calle)
LADO_MIN = 0.30          # m: los lados más cortos no se clasifican (ochavas, quiebres mínimos)
PUERTA_MAX = 0.5         # m: una puerta del padrón a esto o menos de un frente le pone el nombre de la calle
AREA_MIN = 10.0          # m²: un lote con retiro que queda más chico no se aplica
DIF_AREA = 0.10          # el área de la geometría y la catastral difieren más que esto: aviso
AVISO_RETIRO = "Retiro frontal de"

# Los datos de `cat_suelo` que se muestran: clave de Trazo -> (campo de la capa, etiqueta en español). Las etiquetas viajan en
# cada dato (`etiqueta`): la web no las inventa.
CAMPOS = (("categoria", "categoria"), ("sub_categoria", "sub_categoria"), ("area_diferenciada", "area_diferenciada"),
          ("regimen", "rgs"), ("retiro_frontal", "retiro"), ("altura", "altura"), ("fos", "fos"), ("uso_preferente", "usopre"))
ETIQUETAS = {"categoria": "Categoría de suelo", "sub_categoria": "Subcategoría", "area_diferenciada": "Área diferenciada",
             "regimen": "Régimen de gestión", "retiro_frontal": "Retiro frontal (m)", "altura": "Altura máxima (m)",
             "fos": "FOS (%)", "uso_preferente": "Uso preferente"}
NUMERICOS = ("retiro_frontal", "altura", "fos")      # los que pueden traer un número (y la web aplicar)
# Significado de los códigos que tienen leyenda en el GeoServer de la IM (PADRON.md §4); el resto se muestra tal cual
SIGNIFICADOS = {
    "categoria": {"R": "rural", "S": "suburbano", "U": "urbano"},
    "sub_categoria": {"RN": "rural natural", "RP": "rural productivo", "RI": "rural de interfase",
                      "RIC": "rural de interfase costero", "SUH": "suburbano habitacional",
                      "SUNH": "suburbano no habitacional", "SUNHI": "suburbano no habitacional intensivo",
                      "SUNHS": "suburbano no habitacional de servicios", "SUCCe": "urbano consolidado central",
                      "SUCCo": "urbano consolidado costero", "SUCIn": "urbano consolidado intermedio",
                      "SUCO": "urbano consolidado, otros", "SUNC": "urbano no consolidado"},
    "regimen": {"RGE": "Régimen General"}}
_NUMERO = re.compile(r"^\d+(?:[.,]\d+)?$")
_RANGO = re.compile(r"^\d+(?:[.,]\d+)?\s*-\s*\d+(?:[.,]\d+)?$")
_ACORDAMIENTO = re.compile(r"^\d+(?:[.,]\d+)?\s*CA$", re.I)


class ErrorPadron(Exception):
    """Un padrón que no se puede abrir. `mensaje` dice qué hacer; `codigo` es el estado HTTP que le toca (400 número inválido,
    404 padrón inexistente, 502 servicio caído o respuesta ilegible); `warnings`, lo que se alcanzó a avisar."""

    def __init__(self, mensaje, codigo=502, warnings=None):
        Exception.__init__(self, mensaje)
        self.mensaje, self.codigo, self.warnings = mensaje, codigo, list(warnings or [])


class _Caida(Exception):
    """Una petición que no sirvió (red, HTTP o respuesta ilegible); `motivo` va corto, para el aviso."""

    def __init__(self, motivo):
        Exception.__init__(self, motivo)
        self.motivo = motivo


# ------------------------------------------------------------------ red
def url_wfs(capa, cql):
    """La petición GetFeature de una capa (clave de CAPAS o nombre completo) con un filtro CQL, en GeoJSON."""
    q = urllib.parse.urlencode([("service", "WFS"), ("version", "2.0.0"), ("request", "GetFeature"),
                                ("typeNames", CAPAS.get(capa, capa)), ("cql_filter", cql),
                                ("outputFormat", "application/json")])
    return WFS + "?" + q


def red_urllib(url, version=""):
    """GET de `url` -> bytes. Tiempo máximo de 20 s, `User-Agent: Trazo/<versión>` y un reintento si falla (el servicio de la
    Intendencia a veces corta el saludo TLS y al repetir responde); un error HTTP 4xx no se reintenta."""
    req = urllib.request.Request(url, headers={"User-Agent": "Trazo/%s" % (version or "0"), "Accept": "application/json"})
    for intento in (0, 1):
        try:
            with urllib.request.urlopen(req, timeout=TIEMPO) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if intento or 400 <= e.code < 500:
                raise
        except Exception:
            if intento:
                raise
        time.sleep(PAUSA)


RED = red_urllib         # las pruebas lo reemplazan (`padron.RED = falsa`); consultar(red=...) tiene prioridad


def _motivo(e):
    """Por qué falló una petición, en pocas palabras."""
    if isinstance(e, urllib.error.HTTPError):
        return "respuesta HTTP %d" % e.code
    if isinstance(e, urllib.error.URLError) and isinstance(getattr(e, "reason", None), BaseException):
        e = e.reason
    if isinstance(e, (TimeoutError, socket.timeout)):
        return "tiempo de espera agotado"
    txt = " ".join(str(e).split())[:80]
    return "%s%s" % (type(e).__name__, ": " + txt if txt else "")


def _pedir(capa, cql, red, version):
    """Una capa con su filtro -> el GeoJSON ya leído. Levanta _Caida si la red o la respuesta fallan."""
    try:
        crudo = red(url_wfs(capa, cql), version)
    except Exception as e:
        raise _Caida(_motivo(e))
    try:
        datos = json.loads(crudo.decode("utf-8") if isinstance(crudo, (bytes, bytearray)) else crudo)
    except ValueError:
        raise _Caida("respuesta ilegible: no es JSON")
    if not isinstance(datos, dict) or not isinstance(datos.get("features"), list):
        raise _Caida("respuesta ilegible: no trae parcelas")
    return datos


def _numero_valido(numero):
    try:
        n = int(str(numero).strip())
    except (TypeError, ValueError):
        n = 0
    if n <= 0:
        raise ErrorPadron("Trazo: «%s» no es un número de padrón. Escribe solo el número (por ejemplo 421264)." % numero, 400)
    return n


# ------------------------------------------------------------------ geometría del lote
def _anillo(coords):
    pts = [(float(q[0]), float(q[1])) for q in coords]
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    return pts


def _partes(geom):
    """Polygon o MultiPolygon de GeoJSON -> [(exterior, [huecos])], cada anillo sin el vértice final repetido."""
    t, c = (geom or {}).get("type"), (geom or {}).get("coordinates")
    try:
        if t == "Polygon":
            polis = [c]
        elif t == "MultiPolygon":
            polis = c
        else:
            return []
        return [(_anillo(p[0]), [_anillo(h) for h in p[1:]]) for p in polis if p]
    except (TypeError, ValueError, IndexError):
        raise _Caida("respuesta ilegible: geometría rara")


def _limpio(pts, colineales=True):
    """Antihorario, sin vértices a menos de 1 cm del anterior ni, con `colineales`, casi colineales (giro menor que 0,006°)."""
    return [[p[0], p[1]] for p in G.ensure_ccw(G.clean_rel(pts, ang=1e-4 if colineales else 1e-9, dist=0.01))]


def _dist_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def _segmentos(anillos):
    return [(r[i], r[(i + 1) % len(r)]) for r in anillos for i in range(len(r))]


def _fraccion_con_vecino(a, b, segs):
    """Qué fracción del lado ab queda a TOL_VECINO o menos del contorno de alguna vecina. Se prueban puntos cada MUESTREO m
    (a la mitad de cada tramo) sin los primeros y últimos 0,5 m: ahí el lado de la calle roza el lindero de la parcela de al lado."""
    largo = math.hypot(b[0] - a[0], b[1] - a[1])
    corte = min(0.5, largo / 4.0)
    n = max(2, int(math.ceil((largo - 2 * corte) / MUESTREO)))
    x0, x1 = min(a[0], b[0]) - TOL_VECINO, max(a[0], b[0]) + TOL_VECINO
    y0, y1 = min(a[1], b[1]) - TOL_VECINO, max(a[1], b[1]) + TOL_VECINO
    cerca = [(p, q) for p, q in segs if min(p[0], q[0]) <= x1 and max(p[0], q[0]) >= x0 and
             min(p[1], q[1]) <= y1 and max(p[1], q[1]) >= y0]
    if not cerca:
        return 0.0
    con = 0
    for k in range(n):
        s = (corte + (largo - 2 * corte) * (k + 0.5) / n) / largo
        pt = (a[0] + s * (b[0] - a[0]), a[1] + s * (b[1] - a[1]))
        if any(_dist_seg(pt, p, q) <= TOL_VECINO for p, q in cerca):
            con += 1
    return con / float(n)


def _calle_de(a, b, puertas):
    """La calle de la puerta del padrón más cercana al lado ab, si alguna queda a PUERTA_MAX m o menos."""
    mejor = None
    for p, calle in puertas:
        d = _dist_seg(p, a, b)
        if calle and d <= PUERTA_MAX and (mejor is None or d < mejor[0]):
            mejor = (d, calle)
    return mejor[1] if mejor else None


def _derecho(a, b, c):
    """El quiebre en b entre ab y bc es nulo (giro menor que 0,006°) y no vuelve sobre sí mismo."""
    ux, uy, vx, vy = b[0] - a[0], b[1] - a[1], c[0] - b[0], c[1] - b[1]
    return ux * vx + uy * vy > 0 and abs(ux * vy - uy * vx) <= 1e-4 * math.hypot(ux, uy) * math.hypot(vx, vy)


def _lados(poly, vecinas, puertas):
    """Clasifica cada lado de `poly` (antihorario; vecinas: anillos exteriores, vacía si no hay; puertas: [(punto, calle)]) y
    junta los lados seguidos que siguen derechos y son de la misma clase (el frente de 13 m que el catastro parte en 6,1 + 6,9
    es un lado; un lindero que sigue derecho como frente conserva su vértice). Devuelve (poly, medianeras, frentes, dudosos):
    el polígono sin los vértices que sobran, medianeras [{a, b, retiro: 0}], frentes [{a, b, calle, largo}] y dudosos
    [(largo, fracción con vecino)]. Los lados de menos de LADO_MIN no se clasifican."""
    segs = _segmentos(vecinas)
    n = len(poly)
    cls = []
    for i, a in enumerate(poly):
        b = poly[(i + 1) % n]
        f = _fraccion_con_vecino(a, b, segs) if math.hypot(b[0] - a[0], b[1] - a[1]) >= LADO_MIN else None
        cls.append(None if f is None else ("M", f) if f >= CON_VECINO else ("F", f) if f < SIN_VECINO else ("D", f))
    quedan = [i for i in range(n) if not (n > 3 and cls[i - 1] and cls[i] and cls[i][0] == cls[i - 1][0] != "D" and
                                          _derecho(poly[i - 1], poly[i], poly[(i + 1) % n]))]
    pts = [poly[i] for i in quedan]
    meds, frentes, dudosos = [], [], []
    for k, i in enumerate(quedan):
        a, b = pts[k], pts[(k + 1) % len(pts)]
        largo = math.hypot(b[0] - a[0], b[1] - a[1])
        if cls[i] is None:
            continue
        if cls[i][0] == "M":
            meds.append({"a": list(a), "b": list(b), "retiro": 0})
        elif cls[i][0] == "F":
            frentes.append({"a": list(a), "b": list(b), "calle": _calle_de(a, b, puertas), "largo": round(largo, 2)})
        else:
            dudosos.append((largo, cls[i][1]))
    return [list(p) for p in pts], meds, frentes, dudosos


def lados(poly, vecinas, puertas):
    """(medianeras, frentes, dudosos) de `_lados`, sin el polígono."""
    return _lados(poly, vecinas, puertas)[1:]


# ------------------------------------------------------------------ normativa (cat_suelo)
def _numero(texto):
    """El número de un texto que es solo un número («4», «27», «13.50», «60»); None si trae letras, rangos o códigos."""
    if texto is not None and _NUMERO.match(texto):
        return float(texto.replace(",", "."))
    return None


def _nota_codigo(clave, texto, numero):
    """Lo que se agrega a la nota cuando el valor no es un número que Trazo pueda aplicar."""
    if texto is None:
        return "sin dato en la capa"
    if clave in NUMERICOS and numero is None:
        if _RANGO.match(texto):
            return "rango: depende de las condiciones del predio"
        if clave == "retiro_frontal" and _ACORDAMIENTO.match(texto):
            return "con acordamiento (art. D.223.130, según la leyenda del CITIM); no se aplica solo"
        return "código sin leyenda pública, se muestra tal cual"
    if clave in ("uso_preferente", "regimen") and texto not in SIGNIFICADOS.get(clave, {}):
        return "código sin leyenda pública, se muestra tal cual"
    return None


def dato(clave, valor, fecha):
    """Un dato de la capa de suelo: {etiqueta, valor (texto original o None), numero (solo si es un número simple), significado
    (si el código tiene leyenda), fuente, fecha, nota}."""
    texto = None if valor is None else str(valor).strip() or None
    numero = _numero(texto) if clave in NUMERICOS else None
    extra = _nota_codigo(clave, texto, numero)
    return {"etiqueta": ETIQUETAS[clave], "valor": texto, "numero": numero,
            "significado": SIGNIFICADOS.get(clave, {}).get(texto), "fuente": FUENTE_NORMATIVA, "fecha": fecha,
            "nota": NOTA + (" · " + extra if extra else "")}


def normativa(props, fecha):
    """Las propiedades de una fila de cat_suelo -> {clave: dato}."""
    return dict((clave, dato(clave, props.get(campo), fecha)) for clave, campo in CAMPOS)


# ------------------------------------------------------------------ consulta
def _area_txt(v):
    return ("%.0f" % v) if abs(v - round(v)) < 0.05 else ("%.1f" % v).replace(".", ",")


def _num_txt(v):
    return ("%g" % v).replace(".", ",")


def _direcciones(feats):
    """Las puertas del padrón -> (direcciones [{calle, numero}] sin repetir y ordenadas, [(punto, calle)])."""
    vistas, dirs, pts = set(), [], []
    for f in feats:
        p = f.get("properties") or {}
        g = f.get("geometry") or {}
        calle = (p.get("nom_calle") or "").strip() or None
        try:
            if g.get("type") == "Point":
                pts.append(((float(g["coordinates"][0]), float(g["coordinates"][1])), calle))
        except (TypeError, ValueError, IndexError, KeyError):
            pass
        num = p.get("num_puerta")
        if calle and num:
            letra = (p.get("letra") or "").strip()
            clave = (calle, num, letra)
            if clave not in vistas:
                vistas.add(clave)
                d = {"calle": calle, "numero": num}
                if letra:
                    d["letra"] = letra
                dirs.append(d)
    dirs.sort(key=lambda d: (d["calle"], d["numero"] if isinstance(d["numero"], (int, float)) else 0, d.get("letra", "")))
    return dirs, pts


def consultar(numero, red=None, version=""):
    """El padrón `numero` -> la masa de Trazo (ver el docstring del módulo). `red(url, version)` -> bytes (por defecto `RED`).
    Levanta ErrorPadron: 400 (número inválido), 404 (no figura en el parcelario), 502 (servicio caído o respuesta ilegible)."""
    n = _numero_valido(numero)
    red = red or RED
    fecha = datetime.date.today().isoformat()
    caido = ("Trazo: no se pudo consultar el padrón %d en la Intendencia de Montevideo (%%s). Carga el terreno a mano "
             "(terreno rectangular) o con «Abrir DXF…»." % n)
    try:
        datos = _pedir("parcelas", "padron=%d" % n, red, version)
        _revisar_sistema(datos)
        feats = datos["features"]
        if not feats:
            raise ErrorPadron("Trazo: el padrón %d no figura en el parcelario de Montevideo. Revisa el número (si es una unidad "
                              "de propiedad horizontal, usa el padrón madre) o carga el terreno a mano." % n, 404)
        feat = next((f for f in feats if (f.get("properties") or {}).get("padron") == n), feats[0])
        partes = _partes(feat.get("geometry"))
    except _Caida as e:
        raise ErrorPadron(caido % e.motivo, 502)
    props = feat.get("properties") or {}
    avisos = []
    partes = [p for p in partes if len(p[0]) >= 3 and abs(G.area(p[0])) > 1e-6]
    if not partes:
        raise ErrorPadron(caido % "el servicio no trae el polígono del lote", 502)
    partes.sort(key=lambda p: -abs(G.area(p[0])))
    exterior, huecos = partes[0]
    pts = _limpio(exterior, colineales=False)          # con todos los vértices del catastro: los clasifica `_lados`, que junta los que sobran
    area_geom = abs(G.area(pts))
    if len(pts) < 3 or area_geom < 1.0:
        raise ErrorPadron(caido % "el polígono del lote es degenerado", 502)
    ph = bool(props.get("ph"))
    areatot, areacat = props.get("areatot"), props.get("areacat")
    if ph:
        avisos.append("El padrón %d es propiedad horizontal: el polígono es el del padrón madre (todo el edificio)." % n)
    if isinstance(areatot, (int, float)) and isinstance(areacat, (int, float)) and areacat > 0 and \
            abs(areatot - areacat) > DIF_AREA * areacat:
        avisos.append("El área del polígono (%s m²) y la catastral (%s m²) difieren en más de %d %%: dibuja con el polígono, "
                      "pero revisa el dato." % (_area_txt(areatot), _area_txt(areacat), round(DIF_AREA * 100)))
    if len(partes) > 1:
        avisos.append("El padrón %d tiene %d partes separadas: tomé la mayor (%s m²)." % (n, len(partes), _area_txt(area_geom)))
    if huecos:
        avisos.append("El lote tiene %d hueco%s (patios cerrados) que Trazo no dibuja." % (len(huecos), "" if len(huecos) == 1 else "s"))
    # --- las puertas del propio padrón (direcciones y nombre de la calle de cada frente)
    dirs, puertas = [], []
    try:
        dirs, puertas = _direcciones(_pedir("puertas", "padron=%d" % n, red, version)["features"])
    except _Caida as e:
        avisos.append("No se pudieron leer los números de puerta del padrón (%s): los frentes quedan sin el nombre de la calle." % e.motivo)
    # --- las vecinas de la caja del lote, para deducir medianeras y frentes
    x0, y0, x1, y1 = G.bbox(pts)
    cql = "BBOX(the_geom,%.2f,%.2f,%.2f,%.2f) AND padron<>%d" % (math.floor(x0 - MARGEN_CAJA), math.floor(y0 - MARGEN_CAJA),
                                                                  math.ceil(x1 + MARGEN_CAJA), math.ceil(y1 + MARGEN_CAJA), n)
    meds, frentes = [], []
    try:
        vecinas = [f for f in _pedir("parcelas", cql, red, version)["features"] if (f.get("properties") or {}).get("padron") != n]
        anillos = [p[0] for f in vecinas for p in _partes(f.get("geometry"))]
        pts, meds, frentes, dudosos = _lados(pts, anillos, puertas)
        if not anillos:
            avisos.append("No se encontraron parcelas vecinas: no se deducen medianeras.")
        for largo, f in dudosos:
            avisos.append("Lado de %s m sin vecino claro (%d %% con vecino): márcalo a mano como medianera o frente." %
                          (_num_txt(round(largo, 1)), round(f * 100)))
    except _Caida as e:
        pts = _limpio(exterior)                        # sin vecinas no hay clasificación: los vértices colineales no importan
        avisos.append("No se pudieron leer las parcelas vecinas (%s): no se deducen medianeras ni frentes; márcalos a mano." % e.motivo)
    # --- la normativa: orientativa, de una capa aparte; si no está, la parcela alcanza
    norma = None
    try:
        filas = _pedir("cat_suelo", "padron=%d" % n, red, version)["features"]
        if not filas:
            raise _Caida("la capa no tiene el padrón")
        norma = normativa(filas[0].get("properties") or {}, fecha)
    except _Caida as e:
        avisos.append("No se pudo leer la normativa del padrón (capa %s): %s." % (CAPAS["cat_suelo"].split(":")[-1], e.motivo))
    res = {"name": "Padrón %d" % n, "footprint": pts, "source": "padron", "warnings": avisos}
    if meds:
        res["medianeras"] = meds
    res["padron"] = {"numero": n, "fuente": FUENTE, "fecha": fecha, "gid": props.get("gid"), "areatot": areatot,
                     "areacat": areacat, "ph": ph, "direcciones": dirs, "frentes": frentes,
                     "lote": [list(p) for p in pts], "medianeras_lote": copy.deepcopy(meds), "retiro_aplicado": 0,
                     "normativa": norma}
    return res


def _revisar_sistema(datos):
    """El GeoJSON de la IM viene en EPSG:32721 (UTM 21 S); si un día cambia, las coordenadas no serían metros de Trazo."""
    nombre = (((datos.get("crs") or {}).get("properties") or {}).get("name")) or ""
    if nombre and "32721" not in str(nombre):
        raise _Caida("el servicio devolvió otro sistema de coordenadas (%s) en vez de EPSG:32721" % nombre)


# ------------------------------------------------------------------ retiro frontal
def _es_simple(poly):
    n = len(poly)
    for i in range(n):
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            if G.seg_intersection(poly[i], poly[(i + 1) % n], poly[j], poly[(j + 1) % n]) is not None:
                return False
    return True


def _mismo_lado(a, b, c, d, tol=1e-6):
    return (math.hypot(a[0] - c[0], a[1] - c[1]) < tol and math.hypot(b[0] - d[0], b[1] - d[1]) < tol) or \
           (math.hypot(a[0] - d[0], a[1] - d[1]) < tol and math.hypot(b[0] - c[0], b[1] - c[1]) < tol)


def _sobre(a, b, med, tol=0.05):
    """El lado ab queda sobre la medianera `med` (colineal con ella, dentro de su tramo)."""
    p, q = med["a"], med["b"]
    largo = math.hypot(q[0] - p[0], q[1] - p[1])
    if largo < 1e-9:
        return False
    ux, uy = (q[0] - p[0]) / largo, (q[1] - p[1]) / largo
    fuera = lambda r: abs((r[0] - p[0]) * uy - (r[1] - p[1]) * ux)
    t = (((a[0] + b[0]) / 2.0 - p[0]) * ux + ((a[1] + b[1]) / 2.0 - p[1]) * uy) / largo
    return fuera(a) <= tol and fuera(b) <= tol and -tol / largo <= t <= 1 + tol / largo


def aplicar_retiro(res, retiro):
    """Función pura (sin red): una copia de la masa `res` de `consultar` con el retiro frontal aplicado al lote. Cada lado que es
    frente se corre `retiro` m hacia adentro (`G.desfase`) y los demás quedan; la huella es el lote menos esa franja y las
    medianeras son los lados nuevos que quedan sobre una medianera del lote. Con retiro 0 devuelve el lote. Si el retiro deja
    un polígono inválido (menos de 10 m², cruzado o fuera del lote) no se aplica y se avisa. `padron.retiro_aplicado` dice el
    que quedó. Parte siempre del lote (`padron.lote` y `padron.medianeras_lote`), así que aplicar otro retiro sobre un
    resultado ya con retiro da lo mismo que sobre el original."""
    try:
        retiro = float(retiro)
    except (TypeError, ValueError):
        retiro = -1.0
    if not (0.0 <= retiro <= 100.0):
        raise ValueError("el retiro frontal tiene que ser un número de metros entre 0 y 100")
    out = copy.deepcopy(res)
    pad = out["padron"]
    lote = [(float(p[0]), float(p[1])) for p in pad["lote"]]
    out["warnings"] = [w for w in out.get("warnings", []) if not w.startswith(AVISO_RETIRO)]

    def sin_retiro(aviso=None):
        pad["retiro_aplicado"] = 0
        out["footprint"] = [list(p) for p in lote]
        meds = copy.deepcopy(pad.get("medianeras_lote") or [])
        if meds:
            out["medianeras"] = meds
        else:
            out.pop("medianeras", None)
        if aviso:
            out["warnings"].append(aviso)
        return out
    if retiro <= 0:
        return sin_retiro()
    n = len(lote)
    frentes = pad.get("frentes") or []
    ds = [-retiro if any(_mismo_lado(lote[i], lote[(i + 1) % n], f["a"], f["b"]) for f in frentes) else 0.0 for i in range(n)]
    cuantos = sum(1 for d in ds if d)
    if not cuantos:
        return sin_retiro("%s %s m no se aplicó: el lote no tiene frentes deducidos (márcalo a mano con el terreno rectangular "
                          "o las medianeras)." % (AVISO_RETIRO, _num_txt(retiro)))
    nuevo = [(p[0], p[1]) for p in G.clean_rel(G.desfase(lote, ds), ang=1e-4, dist=0.01)]
    a_lote = abs(G.area(lote))
    ok = len(nuevo) >= 3 and AREA_MIN <= G.area(nuevo) <= a_lote + 1e-6 and _es_simple(nuevo) and \
        all(G.point_in_poly(p, lote) or min(_dist_seg(p, lote[i], lote[(i + 1) % n]) for i in range(n)) < 0.05 for p in nuevo)
    if not ok:
        return sin_retiro("%s %s m no se aplicó: deja un polígono de menos de %d m² o que no cabe en el lote. Prueba con un retiro "
                          "menor o carga el terreno a mano." % (AVISO_RETIRO, _num_txt(retiro), AREA_MIN))
    nuevo = [[round(p[0], 6) + 0.0, round(p[1], 6) + 0.0] for p in nuevo]
    originales = pad.get("medianeras_lote") or []
    meds = [{"a": list(nuevo[i]), "b": list(nuevo[(i + 1) % len(nuevo)]), "retiro": 0} for i in range(len(nuevo))
            if math.hypot(nuevo[(i + 1) % len(nuevo)][0] - nuevo[i][0], nuevo[(i + 1) % len(nuevo)][1] - nuevo[i][1]) >= 0.05 and
            any(_sobre(nuevo[i], nuevo[(i + 1) % len(nuevo)], m) for m in originales)]
    out["footprint"] = nuevo
    if meds:
        out["medianeras"] = meds
    else:
        out.pop("medianeras", None)
    pad["retiro_aplicado"] = retiro
    out["warnings"].append("%s %s m aplicado %s del lote (el edificio se calcula sobre el lote menos esa franja)." %
                           (AVISO_RETIRO, _num_txt(retiro), "al frente" if cuantos == 1 else "a los %d frentes" % cuantos))
    return out
