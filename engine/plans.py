"""Planos de unidad: distribución por zonas (día / noche) y grafo de conexiones entre estancias.

Marco local de la unidad: x a lo largo de la fachada, v en profundidad.
v = v0 es el muro del pasillo común (entrada); v = v1 es la fachada (luz natural).

Modelo:
- Zona de día (junto a la entrada): Hall, Cocina, Estar-Comedor (a fachada).
- Zona de noche: Pasillo interno que reparte a Dormitorios (a fachada) y Baños.
- Conexiones: 'abierto' (sin puerta, espacios integrados) o 'puerta'.
Cada conexión se comprueba geométricamente (borde compartido suficiente) y se verifica
que todas las estancias se alcanzan desde la entrada y que las habitables tienen fachada.
"""
import re
from . import geometry as G
from . import standards as ST
from . import equipamiento as EQ

HALL = 1.1            # ancho del pasillo interno
DOOR = ST.DEFAULTS["equipamiento"]["puerta_interior"]     # ancho de puerta interior (configure lo toma de la web)
ENTRY = ST.DEFAULTS["equipamiento"]["puerta_entrada"]     # puerta de la vivienda
DOOR_ACC = ST.DEFAULTS["equipamiento"]["puerta_accesible"]    # dormitorios y baño de una vivienda accesible
LIV_MIN = 3.4         # frente mínimo del estar
BED_MAIN = 3.2        # frente dormitorio principal
BED_W = 2.8           # frente dormitorio secundario
BED_D = 3.0           # fondo mínimo de un dormitorio detrás del pasillo interno
MIN_W = {"bedroom": 2.6, "living": 3.0, "dining": 2.4, "bath": 1.5, "hallway": 0.9, "kitchen": 1.6, "hall": 1.1,
         "laundry": 1.0, "storage": 0.8, "study": 2.2}
DAY = ("hall", "kitchen", "dining", "living", "hallway")     # se conectan en abierto si comparten borde
BATH_W1, BATH_W2, HALL_W, KITCH_D, LAV_W, BATH2_D = 1.7, 1.3, 1.4, 2.9, 1.2, 2.0
BATH_MIN = 1.3        # el baño más angosto: el inodoro contra la pared larga y su paso (configure lo toma de equipamiento)
BATH_MIN_D = 1.45     # el baño menos profundo: la ducha y su paso, con los artefactos en fila (ídem)
BATH_FULL = (1.6, 2.3)    # baño con ducha: con menos fondo que el segundo valor, al menos el primero de ancho (ídem)
FR_MIN, FR_MAX = 1.8, 2.8     # fondo de la franja de servicios (configure lo toma de vivienda["franja_servicios"])
BED_MAX = 4.5         # fondo máximo de un dormitorio al fondo
KITCH_LINE = 2.7      # mesada en línea con la heladera (configure lo toma de equipamiento)
KITCH_L = 2.2         # fondo de una cocina en L: la mesada, su paso y la heladera en la otra pared (ídem)
KITCH_MESADA = 2.0    # R10.8: largo de la mesada sin la heladera: bacha, mesada de trabajo y cocina (ídem)
KITCH_FRENTE = 1.5    # R10.8: la mesada y su paso delante (ídem)
V = ST.DEFAULTS["vivienda"]      # las medidas de trabajo (R5.8a: las lineales llevan el tabique, ver _trabajo)
VN = ST.DEFAULTS["vivienda"]     # R5.8a: las medidas de la norma (libres), para las comprobaciones (_std_for)
# R5.8a (v2.73): espesor del tabique interior (vivienda["tabique"], 0,10 m) y su mitad. Los rectángulos de las estancias
# se tocan por el eje del tabique: una estancia dimensionada con `libre + TAB` deja `libre` entre las caras de dos tabiques
# (T2 a cada lado). Las constantes de trabajo de abajo llevan + TAB (configure); el contorno de la vivienda (fachada,
# patio, medianera, vecina, pasillo común, núcleo) ya tiene su muro fuera del polígono y no descuenta nada (_libres)
TAB, T2 = 0.0, 0.0
_BED_D0 = 3.0         # fondo mínimo de un dormitorio detrás del pasillo interno, libre (BED_D = _BED_D0 + T2: un tabique)
_LINEALES = ("min_side", "max_side", "typ_side")       # las medidas lineales de cada estancia de vivienda (y «typ»)
_FACTOR = {"cocina": 0.5, "cocina_integrada": 0.5}      # estancias con medio tabique (ver _trabajo)
KT = 0.0              # R5.8a: lo que suma el ancho de la cocina (T2: a lo sumo un tabique al costado); su fondo, nada


def _trabajo(vivienda, tab):
    """R5.8a: la copia de trabajo de vivienda con la que el plano dimensiona cada estancia: cada medida lineal (min_side,
    max_side, typ_side y los dos valores de typ) lleva el tabique sumado, así la estancia queda con su medida libre entre
    las caras de dos tabiques; las superficies (min_area, typ_area, max_area, las listas) no cambian: las convierte _wa.
    La cocina (y la integrada) lleva medio tabique: abierta a la zona de día tiene a lo sumo un tabique en su ancho (el
    baño, el depósito o el lavadero al costado) y ninguno en su fondo (el pasillo común y el estar abierto). Con tab = 0
    es una copia igual."""
    out = {}
    for k, v in vivienda.items():
        if isinstance(v, dict):
            d, t_ = dict(v), tab * _FACTOR.get(k, 1.0)
            for m in _LINEALES:
                if isinstance(d.get(m), (int, float)):
                    d[m] = d[m] + t_
            if isinstance(d.get("typ"), (list, tuple)):
                d["typ"] = [t + t_ for t in d["typ"]]
            out[k] = d
        else:
            out[k] = v
    return out


def _wa(area, d, nd=2, nw=2):
    """R5.8a: el ancho al eje que necesita una estancia de superficie libre «area» con el otro lado d (al eje), que tiene nd
    tabiques (T2 cada uno) y en el ancho nw: area / (d − nd·T2) + nw·T2. Reemplaza a «area / d» donde el plano saca un
    ancho de una superficie mínima, típica o máxima. Con TAB = 0 es area / d."""
    return area / max(d - nd * T2, 0.1) + nw * T2


def _area_libre(w, d, nw=2, nd=2):
    """R5.8a: la superficie libre de un rectángulo al eje de w × d con nw y nd tabiques en cada dirección."""
    return max(0.0, w - nw * T2) * max(0.0, d - nd * T2)


def _cama_placard(eq):
    """Dormitorio principal con su cama doble y el placard (criterio del usuario, v2.29): (ancho con el placard al costado
    de la cama, fondo con el placard al pie). Con las medidas por defecto, 3,20 y 3,10 m."""
    return (2 * eq["paso_cama"] + eq["cama_doble"][0] + eq["placard_fondo"],
            eq["cama_doble"][1] + eq["paso_cama"] + eq["placard_fondo"])


CAMA_PLACARD = _cama_placard(ST.DEFAULTS["equipamiento"])
CAMA_FONDO = 2.5      # R5.10: el principal sin placard (con vestidor), la cama doble y su paso al pie (ídem)


def configure(vivienda, equip=None, accesible=False):
    """Ajusta las medidas de proyecto a partir de la tabla de estándares (standards.py / web). accesible: el baño
    principal toma el ancho del baño accesible.
    R5.8a (v2.73): las constantes de trabajo llevan el tabique (TAB = vivienda["tabique"]): V es la copia de trabajo
    (_trabajo: las medidas lineales + TAB) y VN la norma; las que salen del equipamiento (el inodoro con su paso, la
    mesada, la cama con el placard) suman TAB (o T2 donde la estancia solo tiene un tabique en esa dirección: el fondo de
    un dormitorio, entre el pasillo interno y la fachada, y el frente del estar, entre el contorno y la zona de noche)."""
    global HALL, LIV_MIN, BED_MAIN, BED_W, BATH_W1, BATH_W2, HALL_W, KITCH_D, LAV_W, BATH2_D, V, DOOR, ENTRY, DOOR_ACC
    global CAMA_PLACARD, CAMA_FONDO, BATH_MIN, BATH_MIN_D, BATH_FULL, FR_MIN, FR_MAX, KITCH_LINE, KITCH_L, KITCH_MESADA
    global KITCH_FRENTE, EQUIPO, TAB, T2, VN, BED_D, KT
    VN = vivienda
    TAB = float(vivienda.get("tabique") or 0.0)
    T2 = KT = TAB / 2.0
    V = _trabajo(vivienda, TAB)
    eq = EQUIPO = equip or ST.DEFAULTS["equipamiento"]
    cp = _cama_placard(eq)
    CAMA_PLACARD = (cp[0] + TAB, cp[1] + T2)           # el frente, entre dos tabiques; el fondo, hasta la fachada
    CAMA_FONDO = eq["cama_doble"][1] + eq["paso_cama"] + T2
    BED_D = _BED_D0 + T2
    DOOR, ENTRY, DOOR_ACC = eq["puerta_interior"], eq["puerta_entrada"], eq["puerta_accesible"]
    MIN_SHARE["puerta"] = DOOR + 0.1
    HALL = max(V["pasillo"]["min_side"], V["pasillo"]["typ_side"])
    BED_MAIN = max(V["dorm_principal"]["min_side"], V["dorm_principal"]["typ"][0])
    BED_W = max(V["dorm_secundario"]["min_side"], V["dorm_secundario"]["typ"][0])
    LIV_MIN = max(VN["estar_comedor"]["min_side"], 0.95 * VN["estar_comedor"]["typ"][0]) + T2    # el contorno en x0
    inodoro = eq["inodoro"][1] + eq["paso_bano"] + TAB     # un baño angosto: el inodoro contra la pared larga y su paso
    BATH_W1 = max(V["bano"]["min_side"], V["bano"]["typ"][0], inodoro, eq["bano_accesible"][0] + TAB if accesible else 0.0)
    BATH_W2 = max(V["bano_aux"]["min_side"], V["bano_aux"]["typ"][0], inodoro)
    LAV_W = max(V["lavadero"]["min_side"], eq["lavarropas"][1] + eq["paso_lavadero"] + TAB)
    BATH2_D = eq["inodoro"][1] + eq["paso_bano"] + eq["lavatorio"][0] + TAB   # fondo mínimo de un segundo baño (toilette)
    HALL_W = max(VN["hall"]["min_side"], VN["hall"]["typ"][0]) + T2    # un tabique: la zona de noche (la cocina, abierta)
    KITCH_D = V["cocina"]["typ"][1]
    BATH_MIN = max(V["bano"]["min_side"], inodoro)
    BATH_MIN_D = max(V["bano"]["min_side"], eq["ducha"][1] + eq["paso_bano"] + TAB)
    BATH_FULL = (eq["ducha"][0] + eq["inodoro"][0] + TAB, eq["ducha"][1] + eq["inodoro"][0] + eq["lavatorio"][0] + TAB)
    FR_MIN, FR_MAX = V["franja_servicios"]["min_side"], V["franja_servicios"]["max_side"]
    KITCH_LINE = eq["heladera"][0] + eq["bacha_cocina"] + eq["mesada_trabajo"] + eq["cocina_horno"]   # (libres: la
    KITCH_L = eq["mesada_fondo"] + eq["paso_cocina"] + eq["heladera"][1]                                # cocina suma KT
    KITCH_MESADA = eq["bacha_cocina"] + eq["mesada_trabajo"] + eq["cocina_horno"]                       # solo en su
    KITCH_FRENTE = eq["mesada_fondo"] + eq["paso_cocina"]                                                 # ancho)
MIN_SHARE = {"puerta": DOOR + 0.1, "abierto": 0.85}
EQUIPO = ST.DEFAULTS["equipamiento"]     # R10.8: las medidas de equipamiento (configure; la mesada de la cocina)
NAMES = {"hall": "Hall", "kitchen": "Cocina", "living": "Estar-Comedor", "dining": "Comedor", "hallway": "Pasillo",
         "bath": "Baño", "bedroom": "Dormitorio", "laundry": "Lavadero", "storage": "Depósito", "study": "Estudio",
         "vestidor": "Vestidor"}


def bedrooms_for(area):
    if area < 45:
        return 0
    if area < 65:
        return 1
    if area < 85:
        return 2
    return 3


def fondo_min():
    """Fondo mínimo de una vivienda: el pasillo interno y un dormitorio detrás."""
    return BED_D + HALL


def fondo_sin_tira():
    """R3.7: el fondo más grande que el plano aprovecha entero: dormitorios (hasta su máximo), pasillo interno y franja de
    servicios (hasta la suya); con 1 m más, queda una tira sin uso junto al pasillo común (v2.33)."""
    return BED_MAX + HALL + FR_MAX + 0.95


def fondo_profundo():
    """R11.4 (v2.72): el fondo más chico con el que el plano es «profundo» (_plan_rects: dormitorios, pasillo interno y
    franja de servicios, el hall en su esquina y la cocina en la zona de día) en vez de «poco profundo» (hall, baño y
    cocina en fila junto al pasillo común, que pide más frente). Es el fondo mínimo de una vivienda con fachada lateral
    (su ancho a lo largo del pasillo del esquema «pasillo lateral con patios»: plan_lateral y units.generate_unit_mix),
    donde el frente es fijo y el plano con el hall en la esquina del pasillo necesita la franja de servicios."""
    return BED_D + HALL + FR_MIN


def frente_principal(bedD=None):
    """R5.16b (v2.65): el frente del dormitorio principal: el típico (BED_MAIN, 3,00 m con las medidas por defecto: la cama
    doble con su paso a los lados y el placard al pie) o, si el fondo que le queda (bedD) no deja el placard al pie de la
    cama (CAMA_PLACARD[1], 3,10 m), el de la cama con el placard al costado (CAMA_PLACARD[0], 3,20 m): lo mismo que hace
    _anchos_dormitorios al repartir el frente de la zona de noche. Sin bedD, el típico."""
    if bedD is not None and bedD < CAMA_PLACARD[1] - 1e-6:
        return max(BED_MAIN, CAMA_PLACARD[0])
    return BED_MAIN


def fondo_dormitorios(D):
    """R5.16b (v2.65): el fondo que _plan_rects deja a los dormitorios en una vivienda de fondo D, antes de repartir: con
    franja de servicios (profunda), lo que queda tras el pasillo interno y la franja más chica (hasta BED_MAX); si no,
    lo que queda tras el pasillo interno."""
    if D - HALL - BED_D >= FR_MIN - 1e-9:
        return min(BED_MAX, D - HALL - FR_MIN)
    return D - HALL


def facade_min(nb, bedD=None):
    """Frente mínimo de fachada para estar + dormitorios con ventana (R5.16b, v2.65: con el fondo bedD de los
    dormitorios, el principal pide el ancho del placard al costado si no entra al pie: frente_principal)."""
    return 4.0 if nb == 0 else LIV_MIN + frente_principal(bedD) + BED_W * (nb - 1)


def frente_min(nb, D=None, fila=None):
    """R5.16b: el frente que pide el plano de una vivienda de nb dormitorios y fondo D (sin D, el de una profunda), el
    que usa units.generate_unit_mix para repartir las viviendas (nunca menos que facade_min). fila (v2.67): con una
    segunda fachada (1 o -1, el costado; 0, el borde del pasillo común: pasante), el frente del esquema en fila
    (frente_fila) si entra con ese fondo; si no, el de siempre:
    - con dormitorios: facade_min, el estar y los dormitorios en la fachada (v2.65: con el fondo que les queda,
      fondo_dormitorios: si no deja el placard al pie de la cama doble, el principal pide 3,20 m en vez de 3,00); en
      una vivienda poco profunda (sin franja de servicios: D < BED_D + HALL + FR_MIN, ver _plan_rects) la zona de día
      lleva en fila junto al pasillo común el hall, el baño y la cocina con su mesada y su heladera (_ancho_cocina con
      el fondo kd de esa franja), y pide eso en vez del frente del estar (con menos, la vivienda queda sin cocina o sin
      heladera);
    - monoambiente: el hall con su lado mínimo, el baño con su ducha y la cocina con su heladera, en fila (ver el
      monoambiente de _plan_rects; con menos, el hall queda bajo su mínimo o la heladera no entra)."""
    if nb == 0:
        kd = min(2.4, D * 0.4) if D else 2.4
        bano = max(BATH_FULL[0], _wa(V["bano"]["min_area"], kd))
        return max(facade_min(0), min(HALL_W, V["hall"]["min_side"]) + bano + (_ancho_cocina(kd) or KITCH_LINE + KT))
    if fila is not None and D is not None:
        w = frente_fila(nb, D, fila)
        if w is not None:
            return w
    bedD = fondo_dormitorios(D) if D is not None else None
    if D is None or D - HALL - BED_D >= FR_MIN - 1e-9:
        return facade_min(nb, bedD)
    kd = min(2.6, max(1.8, D * 0.4))
    return facade_min(nb, bedD) - LIV_MIN + max(LIV_MIN, HALL_W + BATH_W1 + max(1.8, _ancho_cocina(kd) or KITCH_LINE + KT))


def _shared(r1, r2, tol=0.05):
    """Segmento compartido entre dos rectángulos (x0,v0,x1,v1). Devuelve (p, q) o None."""
    for a, b in ((r1, r2), (r2, r1)):
        if abs(a[2] - b[0]) < tol:                       # borde vertical x = a.x1
            lo, hi = max(a[1], b[1]), min(a[3], b[3])
            if hi - lo > tol:
                return ((a[2], lo), (a[2], hi))
        if abs(a[3] - b[1]) < tol:                       # borde horizontal v = a.v1
            lo, hi = max(a[0], b[0]), min(a[2], b[2])
            if hi - lo > tol:
                return ((lo, a[3]), (hi, a[3]))
    return None


def paredes(R):
    """Tabiques interiores: donde se tocan dos estancias, por línea, unidos si se tocan. [(eje, c, lo, hi)]: eje 0 = pared
    vertical (x = c, de v = lo a hi), que se mueve en x; eje 1 = horizontal (v = c, de x = lo a hi), que se mueve en v."""
    tramos, ids = {}, list(R)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            seg = _shared(R[ids[i]][1], R[ids[j]][1])
            if not seg:
                continue
            vert = abs(seg[0][0] - seg[1][0]) < 1e-6
            eje, c = (0, seg[0][0]) if vert else (1, seg[0][1])
            lo, hi = sorted((seg[0][1], seg[1][1]) if vert else (seg[0][0], seg[1][0]))
            tramos.setdefault((eje, round(c, 3)), []).append((lo, hi, c))
    out = []
    for (eje, _), ts in sorted(tramos.items()):
        ts.sort()
        a, b, c = ts[0]
        for lo, hi, _c in ts[1:]:
            if lo <= b + 0.05:
                b = max(b, hi)
            else:
                out.append((eje, c, a, b))
                a, b = lo, hi
        out.append((eje, c, a, b))
    return out


def _mover_pared(R, e, minimo=None):
    """R5.7: mueve el tabique que pasa por e["p"] hasta e["a"] (marco de la vivienda): corre el lado de todas las
    estancias que se apoyan en él; cada una conserva al menos `minimo` (R5.8a: 0,60 m libres, más el tabique, al eje).
    Devuelve si se aplicó."""
    minimo = 0.6 + TAB if minimo is None else minimo
    p, a = e["p"], e["a"]
    cerca = []
    for eje, c, lo, hi in paredes(R):
        u, w = (p[0], p[1]) if eje == 0 else (p[1], p[0])
        dd = ((u - c) ** 2 + max(lo - w, 0.0, w - hi) ** 2) ** 0.5
        if dd < 0.3:
            cerca.append((dd, eje, c, lo, hi))
    if not cerca:
        return False
    _, eje, c, lo, hi = min(cerca)
    k0, k1, o0, o1 = (0, 2, 1, 3) if eje == 0 else (1, 3, 0, 2)
    while True:                                        # el tabique sigue por las estancias que se apoyan en él
        mueven = [(i, k) for i, (_, r, _) in R.items() for k in (k0, k1)
                  if abs(r[k] - c) < 1e-3 and min(r[o1], hi) - max(r[o0], lo) > -0.05]
        lo2 = min([lo] + [R[i][1][o0] for i, _ in mueven])
        hi2 = max([hi] + [R[i][1][o1] for i, _ in mueven])
        if lo2 >= lo - 1e-9 and hi2 <= hi + 1e-9:
            break
        lo, hi = lo2, hi2
    d = a[eje] - p[eje]
    for i, k in mueven:                                # cada estancia conserva al menos el mínimo
        r = R[i][1]
        if k == k1:
            d = max(d, r[k0] + minimo - c)
        else:
            d = min(d, r[k1] - minimo - c)
    if abs(d) < 0.01 or not mueven:
        return False
    for i, k in mueven:
        kind, r, name = R[i]
        r = list(r)
        r[k] += d
        R[i] = (kind, tuple(r), name)
    return True


def _editar_puerta(doors, rect, e, v0):
    """R5.7: la puerta entre las estancias e["entre"] (o, sin él, la más cercana a e["p"]) se corre a lo largo de su borde
    hasta e["a"], toma el ancho e["ancho"] o abre hacia el otro lado (e["abre"]). rect(id): rectángulo de una estancia.
    Devuelve si se aplicó."""
    if e.get("entre"):                                 # por sus estancias: sigue valiendo si después se movió un tabique
        par = set(e["entre"])
        d = next((d for d in doors if {d["a"], d["b"]} == par), None)
        if d is None:
            return False
    else:
        dist = lambda d: _dist_seg(e["p"], d["p"], d["q"])
        d = min(doors, key=dist, default=None)
        if d is None or dist(d) > 0.4:
            return False
    if d.get("entry"):                                 # la de entrada, en el borde del hall sobre el pasillo común
        r = rect(d["b"])                               # (R11.4: vertical, en el borde lateral del hall)
        seg = ((r[0], r[1]), (r[0], r[3])) if d["vertical"] else ((r[0], v0), (r[2], v0))
    else:
        seg = _shared(rect(d["a"]), rect(d["b"]))
    if not seg:
        return False
    k = 1 if d["vertical"] else 0
    lo, hi = sorted((seg[0][k], seg[1][k]))
    lo, hi = lo + T2, hi - T2                          # R5.8a: dentro del tramo libre (sin pisar el tabique perpendicular)
    w = ((d["q"][0] - d["p"][0]) ** 2 + (d["q"][1] - d["p"][1]) ** 2) ** 0.5
    if e.get("ancho"):
        w = max(0.5, min(float(e["ancho"]), hi - lo - 0.1))
    m = ((d["p"][0] + d["q"][0]) / 2, (d["p"][1] + d["q"][1]) / 2)
    c = e["a"][k] if e.get("a") else m[k]
    c = (lo + hi) / 2 if hi - lo < w + 0.1 else max(lo + w / 2 + 0.05, min(hi - w / 2 - 0.05, c))
    if d["vertical"]:
        d["p"], d["q"] = (m[0], c - w / 2), (m[0], c + w / 2)
    else:
        d["p"], d["q"] = (c - w / 2, m[1]), (c + w / 2, m[1])
    d["ancho"] = w
    if e.get("abre") and not d.get("entry"):           # la hoja abre hacia la otra estancia
        d["a"], d["b"], d["into"] = d["b"], d["a"], -d["into"]
    return True


# ---------------------------------------------------------------- R5.12 (v2.70): estancias editables
TIPOS_ESTANCIA = {"dormitorio": "bedroom", "estudio": "study", "deposito": "storage", "depósito": "storage",
                  "lavadero": "laundry", "comedor": "dining"}          # la función que se pide → el kind
EDITABLES = ("bedroom", "study", "storage", "laundry", "dining")      # las estancias que cambian de función
_NOMBRE_DORM = re.compile(r"^Dormitorio( principal| \d+)?$")


def _estancia_en(R, p):
    """R5.12: la estancia cuyo rectángulo contiene p (marco de la vivienda); si varios lo contienen (la caja de un anexo
    puede pisar otra), el más chico. None si ninguno."""
    if not p:
        return None
    dentro = [(abs((r[2] - r[0]) * (r[3] - r[1])), i) for i, (_, r, _) in R.items()
              if r[0] - 1e-6 <= p[0] <= r[2] + 1e-6 and r[1] - 1e-6 <= p[1] <= r[3] + 1e-6]
    return min(dentro)[1] if dentro else None


def _union_rect(a, b, tol=0.05):
    """R5.12: la unión de dos rectángulos contiguos si es un rectángulo (comparten un lado entero); si no, None."""
    if (abs(a[0] - b[0]) < tol and abs(a[2] - b[2]) < tol and (abs(a[3] - b[1]) < tol or abs(b[3] - a[1]) < tol)) or \
            (abs(a[1] - b[1]) < tol and abs(a[3] - b[3]) < tol and (abs(a[2] - b[0]) < tol or abs(b[2] - a[0]) < tol)):
        return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
    return None


def _largo(seg):
    return ((seg[1][0] - seg[0][0]) ** 2 + (seg[1][1] - seg[0][1]) ** 2) ** 0.5 if seg else 0.0


def _union_con_pasillo(R, E, i, j):
    """R5.12: la unión de los dormitorios i y j cuando no es un rectángulo porque entre los dos queda un tramo del pasillo
    interno que ya no sirve a nadie (en la vivienda poco profunda el último dormitorio toma la punta, v0..v1, y el anterior
    queda detrás del pasillo): el pasillo se recorta como cuando sobra pasillo, si el tramo está en una de sus puntas y las
    demás estancias que abren a él (con puerta o en abierto) siguen tocándolo. Devuelve (rectángulo unido, id del pasillo,
    rectángulo que le queda) o None."""
    a, b = R[i][1], R[j][1]
    bb = (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
    ar = lambda r: max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])
    falta = ar(bb) - ar(a) - ar(b)
    if falta < 0.01:
        return None
    for h, (hk, hr, _) in R.items():
        if hk != "hallway":
            continue
        pz = (max(hr[0], bb[0]), max(hr[1], bb[1]), min(hr[2], bb[2]), min(hr[3], bb[3]))
        if pz[2] - pz[0] < 0.01 or pz[3] - pz[1] < 0.01 or abs(ar(pz) - falta) > 0.01:
            continue
        resto = None                                   # el tramo que se va, en una punta y de todo el ancho del pasillo
        if abs(pz[1] - hr[1]) < 1e-6 and abs(pz[3] - hr[3]) < 1e-6:
            if abs(pz[0] - hr[0]) < 1e-6 and pz[2] < hr[2] - 0.3:
                resto = (pz[2], hr[1], hr[2], hr[3])
            elif abs(pz[2] - hr[2]) < 1e-6 and pz[0] > hr[0] + 0.3:
                resto = (hr[0], hr[1], pz[0], hr[3])
        elif abs(pz[0] - hr[0]) < 1e-6 and abs(pz[2] - hr[2]) < 1e-6:
            if abs(pz[1] - hr[1]) < 1e-6 and pz[3] < hr[3] - 0.3:
                resto = (hr[0], pz[3], hr[2], hr[3])
            elif abs(pz[3] - hr[3]) < 1e-6 and pz[1] > hr[1] + 0.3:
                resto = (hr[0], hr[1], hr[2], pz[1])
        if resto is None:
            continue
        ok = _largo(_shared(bb, resto)) >= MIN_SHARE["puerta"] - 1e-6     # la unida, con lugar para su puerta
        for o, (ok_, orr, _) in R.items():
            if not ok or o in (i, j, h):
                continue
            tipos = [t_ for a_, b_, t_ in E if {a_, b_} == {h, o}]
            if not tipos and ok_ in DAY and _largo(_shared(orr, hr)) >= MIN_SHARE["abierto"] - 1e-6:
                tipos = ["abierto"]                    # se abría al pasillo (zona de día): tiene que seguir abierta
            for t_ in tipos:
                if _largo(_shared(orr, resto)) < MIN_SHARE.get(t_, MIN_SHARE["puerta"]) - 1e-6:
                    ok = False
        if ok:
            return bb, h, resto
    return None


def _dormitorios(R):
    return [i for i, (k, _, _) in R.items() if k == "bedroom"]


def _promover(R, est):
    """R5.12: el dormitorio principal tras quitar o unir: si el usuario no fijó cuál es (est["fijado"]) o el principal ya
    no existe, el más grande (a igual superficie, el que ya era principal; después, bed1)."""
    beds = _dormitorios(R)
    if not beds:
        est["principal"] = None
    elif not est["fijado"] or est["principal"] not in beds:
        ar = lambda i: round((R[i][1][2] - R[i][1][0]) * (R[i][1][3] - R[i][1][1]), 3)
        est["principal"] = max(beds, key=lambda i: (ar(i), i == est["principal"], i == "bed1"))


def _nombres_dormitorios(R, est):
    """R5.12: los nombres por defecto de los dormitorios («Dormitorio principal», «Dormitorio 2»…, o «Dormitorio» si hay uno
    solo) siguen al principal y a la cantidad; los que puso el usuario (est["nombres"]) no se tocan."""
    beds = _dormitorios(R)
    n, k = len(beds), 2
    for i in beds:
        kind, rect, name = R[i]
        if i in est["nombres"] or not _NOMBRE_DORM.match(name):
            if i != est["principal"]:
                k += 1
            continue
        if n == 1:
            nuevo = "Dormitorio"
        elif i == est["principal"]:
            nuevo = "Dormitorio principal"
        else:
            nuevo, k = "Dormitorio %d" % k, k + 1
        R[i] = (kind, rect, nuevo)


def _renombrar(R, E, e, est):
    """R5.12: el nombre de la estancia que contiene e["p"] pasa a e["nombre"] (vacío: el de su función). Un «Hall / Cocina»
    conserva «Cocina» en el nombre (es lo que dice que la cocina está en el hall). Devuelve (encontrada, aviso)."""
    i = _estancia_en(R, e.get("p"))
    if i is None:
        return False, None
    kind, rect, name = R[i]
    nuevo = str(e.get("nombre") or "").strip()[:40]
    if not nuevo:
        nuevo = NAMES.get(kind, name)
        est["nombres"].discard(i)
    else:
        est["nombres"].add(i)
    if kind == "hall" and "Cocina" in name and "Cocina" not in nuevo:
        nuevo += " / Cocina"
    R[i] = (kind, rect, nuevo)
    return True, None


def _conectar(R, E, i):
    """R5.12: una estancia que cambió de función y no tiene conexión: puerta desde la mejor vecina (el pasillo interno o el
    hall si le dan lugar a la puerta; si no, la de borde compartido más largo, salvo baños y lavaderos)."""
    if any(i in (a, b) for a, b, _ in E):
        return True
    cands = []
    for o, (k, r, _) in R.items():
        if o == i or k in ("bath", "laundry", "storage"):
            continue
        L = _largo(_shared(r, R[i][1]))
        if L >= MIN_SHARE["puerta"] - 1e-6:
            cands.append((k not in ("hallway", "hall"), -L, o))
    if not cands:
        return False
    E.append((min(cands)[2], i, "puerta"))
    return True


def _cambiar_tipo(R, E, e, est):
    """R5.12: la estancia que contiene e["p"] cambia de función (e["tipo"]: dormitorio, estudio, depósito, lavadero o
    comedor; solo entre esas) o, si es un dormitorio, pasa a principal o secundario (la cama doble y el placard siguen al
    principal: est["principal"]; est["fijado"] apaga la promoción automática del más grande). Un depósito o un lavadero
    conservan la puerta desde donde estaba (una abertura pasa a puerta); un comedor se abre al estar si es contiguo y, si
    no, conserva su puerta y se avisa. Devuelve (encontrada, aviso)."""
    i = _estancia_en(R, e.get("p"))
    if i is None:
        return False, None
    kind, rect, name = R[i]
    t = str(e.get("tipo") or "").strip().lower()
    if t in ("principal", "secundario"):
        if kind != "bedroom":
            return True, "«%s» no es un dormitorio: solo un dormitorio pasa a principal o secundario; el plano queda " \
                         "como estaba" % name
        est["fijado"] = True
        if t == "principal":
            est["principal"] = i
        elif est["principal"] == i:
            otros = [j for j in _dormitorios(R) if j != i]
            ar = lambda j: (R[j][1][2] - R[j][1][0]) * (R[j][1][3] - R[j][1][1])
            est["principal"] = max(otros, key=ar) if otros else None
        _nombres_dormitorios(R, est)
        return True, None
    nuevo = TIPOS_ESTANCIA.get(t)
    if nuevo is None:
        return True, "«%s»: función «%s» desconocida (dormitorio, estudio, depósito, lavadero o comedor); el plano queda " \
                     "como estaba" % (name, t)
    if kind not in EDITABLES:
        return True, "«%s» no cambia de función: solo dormitorios, estudios, depósitos, lavaderos y comedores; el plano " \
                     "queda como estaba" % name
    if nuevo == kind:
        return True, None
    aviso, abierto = None, False
    if nuevo == "dining":
        est_ = next((o for o, (k, _, _) in R.items() if k == "living"), None)
        if est_ is not None and _largo(_shared(R[est_][1], rect)) >= MIN_SHARE["abierto"] - 1e-6:
            E[:] = [x for x in E if i not in x[:2]]    # abierto al estar (la zona de día se conecta sola, sin puerta)
            abierto = True
        else:
            aviso = "«%s» pasa a comedor, pero no es contiguo al estar: queda cerrado, con su puerta" % name
    else:
        E[:] = [(a, b, "puerta" if i in (a, b) and t_ == "abierto" else t_) for a, b, t_ in E]
    R[i] = (nuevo, rect, name if i in est["nombres"] else NAMES[nuevo])
    if not abierto and not _conectar(R, E, i):
        aviso = "«%s» cambia de función, pero no hay desde dónde ponerle la puerta" % R[i][2]
    if "bedroom" in (kind, nuevo):
        est["cambiado"] = True
        if est["principal"] not in _dormitorios(R):
            _promover(R, est)
        _nombres_dormitorios(R, est)
    return True, aviso


def _unir(R, E, i, j, est):
    """R5.12: el dormitorio i se une al j (que se queda con el id y el nombre): la unión tiene que ser un rectángulo
    (_union_rect) o cerrarse con el tramo de pasillo interno que sobra (_union_con_pasillo); si no, aviso y nada cambia.
    Las conexiones de i pasan a j; el principal, si era i, pasa a j, y después (si el usuario no lo fijó) el más grande."""
    ni, nj = R[i][2], R[j][2]
    if _largo(_shared(R[i][1], R[j][1])) < 0.3:
        return "«%s» y «%s» no se unen: no son contiguos; el plano queda como estaba" % (ni, nj)
    u = _union_rect(R[i][1], R[j][1])
    if u is None:
        con = _union_con_pasillo(R, E, i, j)
        if con is None:
            return "«%s» y «%s» no se unen: la unión no da un rectángulo; el plano queda como estaba" % (ni, nj)
        u, h, resto = con
        R[h] = (R[h][0], resto, R[h][2])
    R[j] = (R[j][0], u, nj)
    del R[i]
    nuevos = []
    for a, b, t_ in E:
        a, b = (j if a == i else a), (j if b == i else b)
        if a != b and (a, b, t_) not in nuevos:
            nuevos.append((a, b, t_))
    E[:] = nuevos
    est["cambiado"] = True
    est["nombres"].discard(i)
    if est["principal"] == i:
        est["principal"] = j
    _promover(R, est)
    _nombres_dormitorios(R, est)
    return None


def _quitar_dormitorio(R, E, e, est):
    """R5.12: el dormitorio que contiene e["p"] se quita: se une al dormitorio contiguo (el que se agranda con su cama):
    primero el que da un rectángulo sin tocar el pasillo, después el principal, después el de borde compartido más largo.
    Devuelve (encontrada, aviso)."""
    i = _estancia_en(R, e.get("p"))
    if i is None:
        return False, None
    kind, rect, name = R[i]
    if kind != "bedroom":
        return True, "«%s» no se quita: solo se quita un dormitorio (se une al contiguo); el plano queda como estaba" % name
    vecinos = [j for j in _dormitorios(R) if j != i and _largo(_shared(R[j][1], rect)) >= 0.3]
    if not vecinos:
        return True, "«%s» no se quita: no tiene un dormitorio contiguo con el que unirse; el plano queda como estaba" % name
    clave = lambda j: (_union_rect(rect, R[j][1]) is None, j != est["principal"], -_largo(_shared(R[j][1], rect)), j)
    return True, _unir(R, E, i, min(vecinos, key=clave), est)


def _unir_dormitorios(R, E, e, est):
    """R5.12: el dormitorio que contiene e["p"] se une con el que contiene e["a"]; se queda el principal, si uno lo es, y
    si no el de e["p"]. Devuelve (encontrada, aviso)."""
    i, j = _estancia_en(R, e.get("p")), _estancia_en(R, e.get("a"))
    if i is None:
        return False, None
    if j is None or j == i:
        return True, "«%s» no se une: no hay otra estancia en el punto pedido; el plano queda como estaba" % R[i][2]
    if R[i][0] != "bedroom" or R[j][0] != "bedroom":
        return True, "«%s» y «%s» no se unen: solo se unen dos dormitorios; el plano queda como estaba" % (R[i][2], R[j][2])
    if j == est["principal"]:
        i, j = j, i
    return True, _unir(R, E, j, i, est)


OPS_ESTANCIA = {"nombre": _renombrar, "tipo": _cambiar_tipo, "quitar": _quitar_dormitorio, "unir": _unir_dormitorios}


def _dist_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2)) if L2 > 0 else 0.0
    return ((p[0] - a[0] - t * dx) ** 2 + (p[1] - a[1] - t * dy) ** 2) ** 0.5


def _tramos_fachada(poly, borde, is_facade, v1, paso=0.25):
    """R5.5: tramos de los bordes de una estancia (polígono antihorario) que dan a la fachada: [(a, b, n)], con n la
    normal hacia afuera. borde: contorno de la vivienda (la ventana va en él, no en un tabique). Sin is_facade, la
    fachada es el fondo (v = v1); si is_facade trae una prueba estricta (is_facade.ventana), se usa esa: junto a una
    esquina entrante, la tolerancia de la prueba común tomaría como fachada un tramo que da al interior."""
    is_facade = getattr(is_facade, "ventana", is_facade)
    out = []
    for i in range(len(poly)):
        p, q = poly[i], poly[(i + 1) % len(poly)]
        L = ((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2) ** 0.5
        if L < 1.0:
            continue
        n = ((q[1] - p[1]) / L, -(q[0] - p[0]) / L)
        m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        if min(_dist_seg(m, borde[j], borde[(j + 1) % len(borde)]) for j in range(len(borde))) > 0.05:
            continue
        if is_facade is None:
            if abs(p[1] - v1) < 0.05 and abs(q[1] - v1) < 0.05:
                out.append((p, q, n))
            continue
        k = max(1, int(round(L / paso)))
        pt = lambda j: (p[0] + (q[0] - p[0]) * j / k, p[1] + (q[1] - p[1]) * j / k)
        tramo = None
        for j in range(k):
            if is_facade(pt(j), pt(j + 1)):
                tramo = (tramo[0] if tramo else pt(j), pt(j + 1))
            elif tramo:
                out.append(tramo + (n,))
                tramo = None
        if tramo:
            out.append(tramo + (n,))
    return out


def _entra_ventana(L, S):
    """R5.5: el tramo de fachada de largo L da para una ventana (la mitad de la típica de un dormitorio, con sus
    mochetas)."""
    return L - 2 * S["mocheta"] >= 0.5 * S["ancho_dormitorio"]


def _ventanas(rooms, borde, is_facade, v1, S, cocinas=None):
    """R5.5: una ventana por estancia habitable, centrada en su tramo de fachada (primero el del fondo, después el más
    largo), del ancho típico o del que pide el vano mínimo (S["iluminacion"] de su superficie), sin pasar de la mocheta;
    si no alcanza, otra en el tramo siguiente. R5.3: en una esquina, también una (típica) en la otra fachada. El comedor
    sin fachada se ilumina por el estar: su superficie se suma a la del estar. R10.9 (norma nacional, art. 24): una
    cocina (también la de un «Hall / Cocina») con tramo de fachada lleva su propia ventana, de S["ancho_cocina"] o
    del ancho que pida el 10 % de su superficie, con S["vano_cocina"] como mínimo. R10.8 (art. 27): cocinas, {id:
    superficie} de las cocinas integradas al estar; las que quedan sin ventana propia se suman a la superficie del estar
    y su vano no baja de cocina_integrada["vano_min"]. Devuelve (ventanas en el marco de la vivienda, comprobaciones con
    la estancia en "room")."""
    largo = lambda t: ((t[1][0] - t[0][0]) ** 2 + (t[1][1] - t[0][1]) ** 2) ** 0.5
    cocinas = cocinas or {}
    es_cocina = lambda r: r["kind"] == "kitchen" or "Cocina" in r["name"]
    habit = [r for r in rooms if r["kind"] in ("bedroom", "living", "dining", "study") or es_cocina(r)]
    libre = lambda r: (r.get("libre") or {}).get("poly") or r["poly"]    # R5.8a: la mocheta, desde la cara del tabique
    tramos = {r["id"]: sorted(_tramos_fachada(libre(r), borde, is_facade, v1),     # primero la fachada del fondo
                              key=lambda t: (t[2][1] < 0.7, -largo(t))) for r in habit}
    comedor = [r for r in habit if r["kind"] == "dining" and not tramos[r["id"]]]
    con_v = lambda i: any(_entra_ventana(largo(t), S) for t in tramos.get(i, ()))    # un tramo con lugar para la ventana
    sin_v = sum(a for i, a in cocinas.items() if not con_v(i))          # R10.9: las cocinas que quedan sin ventana
    out, checks = [], []
    for r in habit:
        if r in comedor:                               # el comedor interior se ilumina por el estar
            continue
        estar, cocina = r["kind"] == "living", es_cocina(r)
        if cocina and not con_v(r["id"]):              # R10.9: sin fachada, se ventila con extractor (y la cuenta
            continue                                   # el vano del estar si es integrada, art. 27)
        area = r["area"] + (sum(c["area"] for c in comedor) + sin_v if estar else 0.0)
        req = S["iluminacion"] * area
        art = ""
        if estar and sin_v:                            # R10.8: el vano del estar con la cocina integrada (art. 27)
            req = max(req, _ci()["vano_min"])
            art = ", %g m² como mínimo: norma nacional, art. 27" % _ci()["vano_min"]
        elif cocina:                                   # R10.9: la ventana de la cocina (art. 24)
            req = max(req, S["vano_cocina"])
            art = ", %g m² como mínimo: norma nacional, art. 24" % S["vano_cocina"]
        tip = S["ancho_estar"] if r["kind"] in ("living", "dining") else S["ancho_cocina"] if cocina else \
            S["ancho_dormitorio"]
        hecho, n_, usadas = 0.0, 0, []
        for a, b, n in tramos[r["id"]]:
            L = largo((a, b))
            if not _entra_ventana(L, S):
                continue                               # el tramo no da para una ventana
            if hecho >= req - 1e-6:                    # ya alcanza; R5.3: en una esquina, una por fachada si entra
                if L - 2 * S["mocheta"] < tip or any(abs(n[0] - o[0]) + abs(n[1] - o[1]) < 0.5 for o in usadas):
                    continue
                w = tip
            else:
                w = min(max((req - hecho) / S["alto"], tip), L - 2 * S["mocheta"])
            c, u = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
            out.append({"room": r["id"], "p": (c[0] - u[0] * w / 2, c[1] - u[1] * w / 2),
                        "q": (c[0] + u[0] * w / 2, c[1] + u[1] * w / 2), "n": n, "ancho": round(w, 2),
                        "alto": S["alto"], "area": round(w * S["alto"], 2), "minimo": round(req, 2)})
            hecho, n_ = hecho + w * S["alto"], n_ + 1
            usadas.append(n)
        if not n_:
            checks.append({"ok": False, "room": r["id"], "msg": "%s: no entra una ventana en su fachada (vano mínimo "
                                                                "%.2f m²)" % (r["name"], req)})
        elif hecho < req - 1e-6:
            de = [] if not estar else ["el estar"] + (["el comedor"] if comedor else []) + (["la cocina"] if sin_v else [])
            de = " de " + ", ".join(de[:-1]) + " y " + de[-1] if len(de) > 1 else ""
            checks.append({"ok": False, "room": r["id"], "msg": "%s: ventana%s de %.2f m² < %.2f m² (%.0f %% de la "
                           "superficie%s)" % (r["name"], "s" if n_ > 1 else "", hecho, req, 100 * S["iluminacion"],
                                              de.replace(" de el ", " del ", 1) + art)})
    return out, checks


def _frente_noche(W, nb, lateral=False, bedD=None):
    """Frente de la zona de noche y el que pide: los dormitorios al fondo (R5.3, lateral: menos el último, que va al
    costado). Si el frente no alcanza para el estar, se ajusta. bedD (v2.65): el fondo de los dormitorios, si ya se
    conoce: con menos del que pide el placard al pie de la cama doble, el principal pide el ancho del placard al costado
    (frente_principal)."""
    need = frente_principal(bedD) + BED_W * (nb - 2 if lateral else nb - 1)
    if W - need >= LIV_MIN:
        return need + min(max((W - need) - 6.0, 0.0), 0.8 * nb), need    # estar de más de 6 m: a los dormitorios
    return max(0.0, W - max(3.0, W * 0.38)), need


def _ancho(clave, d, acc=None):
    """Ancho, a lo largo de la franja de servicios de fondo d, del baño (bath1), del segundo baño (bath2), del baño en
    suite (suite) o del lavadero: el de su superficie típica, sin bajar del que piden sus artefactos (v2.33). El baño de
    una vivienda accesible (acc), con su medida."""
    if clave == "bath1" and acc:
        return acc[0]
    sd, minimo = {"bath1": (V["bano"], BATH_MIN), "suite": (V["bano"], BATH_MIN), "bath2": (V["bano_aux"], BATH_MIN),
                  "laundry": (V["lavadero"], LAV_W)}[clave]
    if clave != "laundry" and d < BATH_FULL[1] - 1e-6:     # con poco fondo, el ancho que deja lugar a la ducha
        minimo = max(minimo, BATH_FULL[0])
    return max(minimo, _wa(sd["typ_area"], d))


def _tope(clave, d):
    """Ancho máximo de una estancia de la franja de fondo d: hasta ahí la agranda lo que sobra (B, v2.33)."""
    return _wa({"bath1": V["bano"], "suite": V["bano"], "bath2": V["bano_aux"], "laundry": V["lavadero"],
                "storage": V["deposito"]}[clave]["max_area"], d)


def _fondo_franja(claves, L, lo, hi, acc=None):
    """Fondo de la franja de servicios (v2.33): el menor entre lo y hi con el que sus estancias entran en el largo L (así
    los dormitorios ganan fondo); si no entran ni con hi, hi."""
    d = lo
    while d < hi - 1e-9 and sum(_ancho(k, d, acc) for k in claves) > L + 1e-6:
        d = min(hi, d + 0.05)
    return d


def _servicios(L, nb, hi, acc=None, lo=0.0):
    """Estancias de la franja de servicios de largo L y su fondo (v2.33): el baño, el segundo baño (con 2 dormitorios o
    más, si entra) y el lavadero, con el menor fondo (no menos de lo) con el que entran, hasta hi."""
    lo = min(hi, max(FR_MIN, acc[1] if acc else 0.0, lo))
    if nb >= 2 and max(lo, BATH2_D) <= hi + 1e-9:
        claves = ["bath1", "bath2", "laundry"]
        d = _fondo_franja(claves, L, max(lo, BATH2_D), hi, acc)
        if _ancho("bath1", d, acc) + _ancho("bath2", d) + 1.0 <= L + 1e-6:
            return claves, d
    claves = ["bath1", "laundry"]
    return claves, _fondo_franja(claves, L, lo, hi, acc)


def _repartir(claves, anchos, L, d):
    """B (v2.33): lo que sobra del largo L de la franja agranda sus estancias, en proporción a lo que a cada una le falta
    para su máximo. Devuelve los anchos y lo que sigue sobrando (C: sin uso)."""
    sobra = L - sum(anchos)
    for _ in range(len(claves)):
        margen = [max(0.0, _tope(k, d) - w) for k, w in zip(claves, anchos)]
        if sobra <= 1e-6 or sum(margen) <= 1e-6:
            break
        f = min(1.0, sobra / sum(margen))
        anchos = [w + m * f for w, m in zip(anchos, margen)]
        sobra = L - sum(anchos)
    return anchos, max(0.0, sobra)


def _anchos_dormitorios(Wn, nf, bedD):
    """Frente de cada dormitorio al fondo: el típico, estirado a Wn, y que cada uno llegue a su área mínima con el fondo
    bedD (si el frente lo permite); el principal, el ancho de su cama doble con el placard al costado (v2.29)."""
    widths = [BED_MAIN] + [BED_W] * (nf - 1)
    k = Wn / sum(widths)
    widths = [w * k for w in widths]
    specs = [V["dorm_principal"]] + [V["dorm_secundario"]] * (nf - 1)
    mw = [max(sp["min_side"], _wa(sp["min_area"], bedD, 1) + 0.02) for sp in specs]   # (R5.8a: un tabique en el fondo)
    if bedD < CAMA_PLACARD[1] - 1e-6 and sum(mw[1:]) + max(mw[0], CAMA_PLACARD[0]) <= Wn + 1e-6:
        mw[0] = max(mw[0], CAMA_PLACARD[0])
    if sum(mw) <= Wn + 1e-6:
        widths = [max(w, m_) for w, m_ in zip(widths, mw)]
        over = sum(widths) - Wn
        slack = [w - m_ for w, m_ in zip(widths, mw)]
        if over > 1e-6 and sum(slack) > 0:
            widths = [w - over * s_ / sum(slack) for w, s_ in zip(widths, slack)]
    return widths


def _ci():
    """R10.8: medidas de la cocina integrada al estar sin ventana propia (norma nacional, art. 27)."""
    return V.get("cocina_integrada") or ST.DEFAULTS["vivienda"]["cocina_integrada"]


def _modos_cocina(costado=True):
    """R10.8: (fondo, ancho) mínimos con que entra la mesada de una cocina (con la heladera y su paso delante) contra la
    pared del pasillo común (a lo ancho) y la del costado (a lo hondo): en línea contra el pasillo común; en L, la mesada
    contra el pasillo común y la heladera en la pared del costado, después del paso; y si la pared del costado es maciza
    desde el pasillo común (costado: sin puerta ni abertura), en L al revés o la mesada entera contra ella. El fondo, no
    menos del lado mínimo de una cocina."""
    linea = max(V["cocina"]["min_side"], KITCH_FRENTE)
    return [(linea, KITCH_LINE + KT), (max(linea, KITCH_L), KITCH_MESADA + KT)] + (     # (R5.8a: el ancho, con KT)
        [(max(linea, KITCH_MESADA), KITCH_L + KT), (max(linea, KITCH_LINE), max(KITCH_FRENTE + KT, _ci()["min_side"]))]
        if costado else [])


def _fondo_cocina(w, costado=True):
    """R10.8: el menor fondo con el que entra la mesada de una cocina de ancho w (ver _modos_cocina); si no entra con
    ninguno, el mayor."""
    modos = _modos_cocina(costado)
    fondos = [f for f, a in modos if w >= a - 1e-6]
    return min(fondos) if fondos else max(f for f, _ in modos)


def _ancho_cocina(f, costado=True):
    """R10.8: el menor ancho con el que entra la mesada de una cocina de fondo f (None si no entra con ninguno)."""
    anchos = [a for f_, a in _modos_cocina(costado) if f >= f_ - 1e-6]
    return min(anchos) if anchos else None


def _hasta(fn, lo, hi, tope):
    """El mayor t entre lo y hi con fn(t) <= tope (fn creciente); lo si ni así."""
    if fn(hi) <= tope + 1e-6:
        return hi
    for _ in range(40):
        m = (lo + hi) / 2.0
        lo, hi = (m, hi) if fn(m) <= tope + 1e-6 else (lo, m)
    return lo


def _cocina_integrada(w, kd, kd_min=0.0, real=None, angostar=True, costado=True, entra=None, tope=None, lado=None):
    """R10.8 (norma nacional, art. 27; criterio del usuario: Trazo la dibuja así): (ancho, fondo) de la cocina integrada
    sin ventana de ancho w y fondo kd, con cocina_integrada["max_area"] como máximo. Primero pierde fondo (lo gana el
    estar), hasta el que pide su mesada (_fondo_cocina) y no menos de kd_min; si aún pasa, se angosta, con el fondo que
    pida su nuevo ancho, no menos de kd_min y sin pasar de kd (lo que deja va al hall): la más ancha que entre. Si ningún
    acomodo de la mesada entra en el tope y angostar, se angosta con el fondo que ya tiene (sin lado menor que el mínimo);
    si ni así entra (medidas cambiadas), la más chica: la comprobación lo avisa. Una cocina que ya entra no cambia.
    real(ancho, fondo): su superficie dentro de la vivienda, desde su borde fijo (un muro oblicuo puede cortarla).
    costado: la pared del costado es maciza (ver _modos_cocina). entra(ancho, fondo): si su mesada entra de verdad
    (un muro oblicuo la corta: _entra_mesada); si no entra en la elegida, la más ancha en el tope en la que sí.
    tope y lado (R10.9): otra superficie máxima y otro lado mínimo (la cocina con ventana propia: los de una cocina)."""
    w_, f_ = _cocina_ajustada(w, kd, kd_min, real, angostar, costado, tope, lado)
    if entra is None or (w_, f_) == (w, kd) or entra(w_, f_):
        return w_, f_
    tope, lado, real = tope or _ci()["max_area"], lado or _ci()["min_side"], real or (lambda a, b: a * b)
    lo = max(kd_min, min(f for f, _ in _modos_cocina(costado)))
    fondos = {lo + 0.05 * k for k in range(int(max(0.0, kd - lo) / 0.05) + 1)} | {kd}
    cands = []                                         # en cada fondo, la más ancha en el tope; de las que entran,
    for f in sorted(fondos):                           # la más ancha (y la menos profunda)
        a = min(w, _hasta(lambda t: real(t, f), 0.0, w, tope))
        if a >= lado - 1e-6 and real(a, f) <= tope + 1e-6 and entra(a, f):
            cands.append((a, -f))
    if not cands:
        return w_, f_
    a, f = max(cands)
    return a, -f


def _cocina_ajustada(w, kd, kd_min=0.0, real=None, angostar=True, costado=True, tope=None, lado=None):
    """_cocina_integrada sin la prueba de la mesada."""
    tope, lado = tope or _ci()["max_area"], lado or _ci()["min_side"]
    rect = lambda a, b: a * b
    real = real or rect
    if w <= 0 or real(w, kd) <= tope + 1e-6:
        return w, kd
    if abs(real(w, kd) - w * kd) < 1e-6:               # entera dentro de la vivienda: como rectángulo (más rápido)
        real = rect
    f = min(kd, max(_fondo_cocina(w, costado), kd_min, _hasta(lambda t: real(w, t), 0.0, kd, tope)))
    if real(w, f) <= tope + 1e-6:
        return w, f

    def clave(a, b):                                   # primero las que entran (la más ancha); si no, la más chica
        sup = real(a, b)
        return (sup > tope + 1e-6, sup if sup > tope + 1e-6 else -a, a, b)
    mejor = clave(w, f)
    for f_ in sorted({max(t, kd_min) for t, _ in _modos_cocina(costado)} | {f}):
        lo = _ancho_cocina(f_, costado)
        if f_ > kd + 1e-6 or lo is None or w < lo - 1e-6:
            continue
        mejor = min(mejor, clave(min(w, max(lo, _hasta(lambda t: real(t, f_), 0.0, w, tope))), f_))
    if mejor[0] and angostar:                          # ningún acomodo entra en el tope: más angosta con su fondo
        mejor = min(mejor, clave(min(w, max(lado, _hasta(lambda t: real(t, f), 0.0, w, tope))), f))
    return mejor[2], mejor[3]


def _entra_mesada(rect, forma_de, costado=True, libre=False, desde_x0=True):
    """R10.8: ¿entra la mesada de la cocina del rectángulo rect (con bacha y cocina, y la heladera) si un muro oblicuo
    la corta? Se prueba con el equipamiento en la parte de rect dentro de la vivienda (forma_de(rect)): abierta al estar
    (v1) y en el borde que se mueve (salvo libre: una pared maciza) y, si no es costado (puerta o paso), en el fijo.
    desde_x0: el borde fijo es x0. Sin muro oblicuo (o sin forma_de), sí: la miden _modos_cocina."""
    k0, kv0, k1, kv1 = rect
    a, b = k1 - k0, kv1 - kv0
    forma = forma_de(rect) if forma_de else None
    if not forma or a <= 0 or b <= 0 or abs(G.area(forma)) >= a * b - 0.01:     # como el equipamiento: un rectángulo
        lo = _ancho_cocina(b, costado)
        return lo is not None and a >= lo - 1e-6
    forma = [(x - k0, y - kv0) for x, y in G.ensure_ccw(forma)]
    r = EQ._estancia(a, b, forma)
    izq, der = ((0.0, 0.0), (0.0, b)), ((a, 0.0), (a, b))
    fijo, mueve = (izq, der) if desde_x0 else (der, izq)
    abiertos = [((0.0, b), (a, b))] + ([] if libre else [mueve]) + ([] if costado else [fijo])
    libres, zonas = EQ._paredes(r, abiertos, [])
    return not EQ._cocina(r, libres, zonas, EQUIPO)[1]


def _entra_lavadero(rect, deposito=False, forma=None):
    """R5.11 (revisión): ¿entran el lavarropas y la pileta, con su paso, en el lavadero rect de la banda (forma: su
    contorno, si un muro oblicuo lo recorta)? Su puerta va en la pared de x0 (desde el hall o la cocina), donde la pondría
    _distribuir (al medio o junto a una punta) y, con deposito, la del depósito al medio de la de x1. Se prueba con el
    equipamiento (EQ.resolver): en una tira de menos de LAV_W (el lavarropas y su paso) pueden entrar contra las paredes
    del costado, o no."""
    x0, v0, x1, v1 = rect[0] + T2, rect[1], rect[2] - T2, rect[3] - T2    # R5.8a: el rectángulo libre (v0 es el
    rect = (x0, v0, x1, v1)                                                # pasillo común: sin tabique)
    if forma and TAB > 0:
        forma = G.clip_rect(forma, x0, x1, v0, v1) or None
    d, h = v1 - v0, DOOR / 2
    if d < DOOR + 0.1 - 1e-6:
        return False
    rm = {"id": "laundry", "kind": "laundry", "name": "Lavadero", "rect": rect,
          "poly": forma or [(x0, v0), (x1, v0), (x1, v1), (x0, v1)]}
    dep = [{"p": (x1, v0 + d / 2 - h), "q": (x1, v0 + d / 2 + h), "a": "laundry", "b": "storage", "ancho": DOOR}] \
        if deposito else []
    for c in [d / 2] + ([h + 0.1, d - h - 0.1] if d > DOOR + 0.3 else []):
        pu = [{"p": (x0, v0 + c - h), "q": (x0, v0 + c + h), "a": "hall", "b": "laundry", "ancho": DOOR}] + dep
        if not EQ.resolver(rm, pu, {}, EQUIPO)[1]:
            return True
    return False


def _entra_bano_suite(rect, forma=None):
    """R5.11 (revisión): ¿entran la ducha, el inodoro y el lavatorio en el baño en suite rect, si un muro oblicuo lo
    recorta (forma: su contorno)? La puerta, desde el dormitorio, en su pared de v1, donde la pondría _distribuir (al medio
    o junto a una punta). Si no entran, quedaría como toilette."""
    x0, v0, x1, v1 = rect[0] + T2, rect[1] + T2, rect[2], rect[3] - T2    # R5.8a: el rectángulo libre (x1 es el
    rect = (x0, v0, x1, v1)                                                # contorno de la vivienda: sin tabique)
    if forma and TAB > 0:
        forma = G.clip_rect(forma, x0, x1, v0, v1) or None
    w, h = x1 - x0, DOOR / 2
    if w < DOOR + 0.1 - 1e-6:
        return False
    rm = {"id": "bath2", "kind": "bath", "name": "Baño en suite", "rect": rect,
          "poly": forma or [(x0, v0), (x1, v0), (x1, v1), (x0, v1)]}
    for c in [w / 2] + ([h + 0.1, w - h - 0.1] if w > DOOR + 0.3 else []):
        _, falta, info = EQ.resolver(rm, [{"p": (x0 + c - h, v1), "q": (x0 + c + h, v1), "a": "bed1", "b": "bath2",
                                           "ancho": DOOR}], {}, EQUIPO)
        if not falta and not info:
            return True
    return False


def _banda(e, dz, L):
    """R5.11 (criterio del usuario): la tira sin luz de fondo e junto al pasillo común de una vivienda muy profunda lleva
    la cocina y el lavadero. La cocina, integrada al estar sin ventana (art. 27: de cocina_integrada["max_area"] como
    máximo), va desde el hall, en x0, hacia la tira, con el fondo de la banda: para cada acomodo de su mesada
    (_modos_cocina, en línea o en L: la pared del costado lleva la puerta del lavadero), el mayor con el que entra sin
    pasar de esa superficie, no más que e ni que el fondo típico de una cocina (vivienda["cocina"]["typ"][1]). dz: el
    ancho de la zona de día al lado del hall (la cocina se abre al estar por ahí); L: el largo de la banda desde el hall,
    donde también entra el lavadero. Devuelve [(fondo de la banda, ancho de la cocina)], del más profundo al menos."""
    tope, cands = _ci()["max_area"], []
    for f, a in _modos_cocina(False):
        eb = min(e, KITCH_D, tope / a)
        wk = min(tope / eb, L - _ancho("laundry", eb)) if eb > 0 else 0.0
        if eb >= f - 1e-6 and wk >= a - 1e-6 and min(wk, dz) >= MIN_SHARE["abierto"] + 0.01:
            cands.append((eb, wk))
    return sorted(set(cands), reverse=True)


def _plan_rects(x0, v0, x1, v1, nb, warnings, acc=None, lateral=False, hall_x0=False, vestidor=False, area_de=None,
                prop=None, forma_de=None, vent=None, con_banda=True, luz=None):
    """Rectángulos de estancias, conexiones con puerta (las abiertas de la zona de día se deducen después) y lo que queda
    sin uso [(rect, aviso)]. acc: frente y fondo del baño de una vivienda accesible (None si no lo es). lateral (R5.3): el
    costado x1 es fachada y el frente no alcanza: el último dormitorio va a ese costado, entre el pasillo común y el
    pasillo interno. hall_x0 (R3.7): el hall, y con él la entrada, en el extremo x0 (el pasillo común solo llega ahí);
    la cocina queda entre el hall y la zona de noche. vestidor (R5.10): el dormitorio principal lleva vestidor (ver
    _vestidor). area_de(rect): superficie del rectángulo dentro de la vivienda (R10.8: la cocina, de 5 m² como máximo).
    prop (R10.8, art. 14): el estar, con el comedor interior, de hasta prop veces su ancho (ventanas["proporcion_max"]):
    el fondo que pierde la cocina no lo lleva más allá. vent: las medidas de las ventanas (R5.11: la cocina va a la tira
    si al estar le sigue alcanzando la suya). con_banda (R5.11): la tira puede ser una banda de servicios (si no, como en
    v2.41). luz(rect) (R10.9): la cocina rect tiene un tramo de fachada en el que entra su ventana: lleva la suya (art.
    24) y no es la integrada sin ventana (art. 27): se dibuja con la superficie típica de una cocina como máximo,
    conservando su fondo (ver cocina).
    v2.33 (criterio del usuario): el placard es el armario del dormitorio, no una estancia. La franja sin luz entre el
    pasillo interno y el pasillo común lleva baños, lavadero y un depósito de hasta 4 m², con el menor fondo con el que
    entran (lo demás va a los dormitorios). Si sobra franja: A, el dormitorio principal pasa al final del pasillo, en
    suite, con su baño en la franja; si no se puede, B, baños, lavadero y depósito más grandes (hasta su máximo); y si
    aún sobra, C, queda sin uso, con aviso."""
    W, D = x1 - x0, v1 - v0
    R = {}          # id -> (kind, rect, name)
    E = []          # (id_a, id_b, tipo)
    vacios = []     # C: (rect, aviso)

    def add(i, kind, rect, name=None):
        if rect[2] - rect[0] > 0.3 and rect[3] - rect[1] > 0.3:
            R[i] = (kind, rect, name or NAMES[kind])

    def real(rect, menos=0.0):
        """Superficie del rectángulo dentro de la vivienda (sin area_de, la del rectángulo), menos «menos»."""
        return (area_de(rect) if area_de else (rect[2] - rect[0]) * (rect[3] - rect[1])) - menos

    def fuera(rect):
        """R5.11 (revisión): lo que un muro oblicuo o un entrante deja del rectángulo fuera de la vivienda (el aviso de
        lo que queda sin uso dice solo lo que está en ella)."""
        d = (rect[2] - rect[0]) * (rect[3] - rect[1]) - real(rect)
        return d if d > 1e-6 else 0.0                  # (entero: sin el ruido del redondeo)

    prop = prop or ST.DEFAULTS["ventanas"]["proporcion_max"]
    tope = _ci()["max_area"]

    def cocina(wk, kd, caja, pisos, costado=True, libre=False, techo=None):
        """R10.8: la cocina con 5 m² como máximo (_cocina_integrada), probando los fondos mínimos de pisos de a uno, del
        más exigente al menos: el primero con el que su mesada entra en el tope; si con ninguno, el último (y se angosta
        con el fondo que tenga). caja(ancho, fondo): su rectángulo, desde su borde fijo. Si un muro oblicuo la corta, la
        mesada se prueba con el equipamiento (_entra_mesada; libre: el borde que se mueve es una pared maciza): la primera
        en la que entra; si en ninguna, como sin la prueba. R10.9: con un tramo de fachada para su ventana (luz), es una
        cocina con ventana propia (art. 24): de vivienda["cocina"]["typ_area"] como máximo (sus mínimos, los de una
        cocina), conserva su fondo y se angosta primero (lo que deja va al hall, al baño o a un depósito), con techo como
        fondo máximo (el que deja al estar no más ancho que prop veces su fondo, art. 14); si al achicarse pierde la
        fachada, como integrada."""
        if luz and luz(caja(wk, kd)):
            kd_ = min(kd, max(techo, min(f for f, _ in _modos_cocina(costado)))) if techo is not None else kd
            w_, f_ = cascada(wk, kd_, caja, [kd_] + [p_ for p_ in pisos if p_ < kd_ - 1e-9], costado, libre,
                             V["cocina"]["typ_area"], V["cocina"]["min_side"])
            if luz(caja(w_, f_)):
                return w_, f_
        return cascada(wk, kd, caja, pisos, costado, libre, tope, _ci()["min_side"])

    def cascada(wk, kd, caja, pisos, costado, libre, tope, lado):
        """La cocina de cocina(): de tope como máximo, con lado como lado mínimo."""
        fija = lambda a, b: real(caja(a, b))
        entra = lambda a, b: _entra_mesada(caja(a, b), forma_de, costado, libre, caja(a, b)[0] > caja(0.0, b)[0] - 1e-9)
        if fija(wk, kd) >= wk * kd - 0.01:            # sin muro oblicuo: lo miden _modos_cocina, como antes
            entra = lambda a, b: True
        pisos = [max(0.0, min(kd, p_)) for p_ in pisos]
        hechas = []
        for p_ in pisos[:-1]:
            w_, f_ = _cocina_integrada(wk, kd, p_, fija, False, costado, entra, tope, lado)
            if fija(w_, f_) <= tope + 1e-6:
                if entra(w_, f_):
                    return w_, f_
                hechas.append((w_, f_))
        ultima = _cocina_integrada(wk, kd, pisos[-1], fija, True, costado, entra, tope, lado)
        return hechas[0] if hechas and not entra(*ultima) else ultima

    def sobrante(resto, sup, d, bano=True, hall=False):
        """R10.8: el ancho resto que la cocina (de 5 m² como máximo) deja en la franja de la entrada, de fondo d: primero
        al baño (de superficie sup; si bano), hasta su superficie máxima; después, un depósito cerrado que se abre al
        estar, hasta la suya (si queda menos que el depósito más chico, el baño se lo da); y lo que aún sobre, C (v2.33):
        sin uso, con aviso, o al hall si hall (en la vivienda poco profunda no: el hall abierto al estar le quitaría la
        pared del sofá o del rack). Lo poco que no da para una estancia, al depósito, al baño o al hall. Devuelve, en
        ancho, (lo que gana el baño, el depósito, lo que queda sin uso, lo que gana el hall)."""
        dep = V["deposito"]
        resto = max(resto, 0.0)
        mas = min(resto, max(0.0, (V["bano"]["max_area"] - sup) / d)) if bano else 0.0
        resto -= mas
        wd = 0.0
        if dep["max_area"] > 0 and resto > 1e-6:
            wmin = max(dep["min_side"], MIN_SHARE["puerta"], _wa(dep["min_area"], d))
            if resto >= wmin - 1e-6:
                wd = min(resto, _wa(dep["max_area"], d))
            elif mas >= wmin - resto:                  # el baño le da al depósito lo que le falta
                mas, wd = mas - (wmin - resto), wmin
            resto = max(0.0, resto - wd)
        poco = resto < MIN_W["storage"] + 0.1 or resto * d < 1.0
        if resto > 1e-6 and poco and not hall and (wd > 0 or bano):
            wd, mas, resto = (wd + resto, mas, 0.0) if wd > 0 else (wd, mas + resto, 0.0)
        return (mas, wd, 0.0, resto) if hall or poco else (mas, wd, resto, 0.0)

    def sin_uso(x, w, d):
        """C (v2.33): el ancho w de la franja de la entrada que no lleva estancia, desde x."""
        if w > 1e-6:
            vacios.append(((x, v0, x + w, v0 + d), "Sin uso: %.1f m² de franja sin luz junto al pasillo común: la "
                                                   "vivienda tiene más frente del que su tipo necesita" % (w * d)))

    if nb == 0:     # monoambiente
        kd = min(2.4, D * 0.4)
        bw = min(2.0, W * 0.35)
        hw = min(1.4, max(1.1, W * 0.2))
        if acc and W - acc[0] - hw >= 1.6 - 1e-6:      # baño accesible, si la cocina sigue entrando
            bw, kd = acc[0], max(kd, min(acc[1], D - 3.5))
        hmin, ka = min(HALL_W, V["hall"]["min_side"]), _ancho_cocina(kd) or KITCH_FRENTE + KT
        entero = lambda a: real((x1 - a, v0, x1, v0 + kd) if hall_x0 else (x0, v0, x0 + a, v0 + kd)) >= a * kd - 0.01
        if hw < hmin:                                  # v2.41: el hall, con su lado mínimo, solo si la cocina conserva
            if W - bw - hmin >= ka - 1e-6:             # el ancho de su acomodo (con la heladera)
                hw = hmin
            elif bw != (acc or (0.0,))[0] and W - hmin - ka >= max(BATH_FULL[0], _wa(V["bano"]["min_area"], kd)) - 1e-6 \
                    and entero(W - hmin - ka):         # o si se lo da el baño, que conserva su ducha (sin muro oblicuo)
                bw, hw = W - hmin - ka, hmin
            elif W - bw - hw < ka - 1e-6 and W - bw - hmin >= KITCH_FRENTE + KT - 1e-6:
                hw = hmin                              # la cocina ya no tenía su acomodo: el hall, sin quitarle la mesada
        # R10.8: un muro oblicuo que corta el extremo x1 junto al pasillo común: la estancia de ese extremo (el baño con el
        # hall en x0; si no, el hall, con la puerta de entrada) se ensancha lo que pierde su borde recto, sin que la
        # cocina baje del frente de su mesada
        c0 = max(0.0, W / 2 - real((x0 + W / 2, v0, x1, v0 + 0.01)) / 0.01) if area_de else 0.0
        if c0 > 1e-3 and hall_x0:
            bw = max(bw, min(W - hw - KITCH_FRENTE - KT, bw + c0))
        elif c0 > 1e-3:
            hw = max(hw, min(W - bw - KITCH_FRENTE - KT, hw + c0))
        # R10.8: la cocina integrada, de 5 m² como máximo (art. 27): la franja de la entrada comparte el fondo con el baño:
        # primero se angosta (lo que deja: sobrante); si no entra, la franja pierde fondo, sin que el baño baje de su mínimo
        # (si un muro oblicuo lo corta o es el accesible, no lo pierde) y, si se puede, sin que el estar-dormitorio pase de
        # prop veces su ancho (art. 14)
        kb = x1 - bw if hall_x0 else x0
        fb = kd if (acc and bw == acc[0]) or real((kb, v0, kb + bw, v0 + kd)) < bw * kd - 1e-6 else \
            max(BATH_MIN_D, _wa(V["bano"]["min_area"], bw))
        caja = (lambda a, b, bw: (x1 - bw - a, v0, x1 - bw, v0 + b)) if hall_x0 else \
            (lambda a, b, bw: (x0 + bw, v0, x0 + bw + a, v0 + b))
        wk, kd = cocina(W - bw - hw, kd, lambda a, b: caja(a, b, bw), [kd, max(fb, D - prop * W), fb],
                        techo=D - W / prop)
        sup = real((kb, v0, kb + bw, v0 + kd))         # lo que deja la cocina: al baño (si la cocina no gana superficie al
        mb, wd, _, mh = sobrante(W - bw - hw - wk, sup, kd, True, True)      # correrse), a un depósito y al hall (que
        if real(caja(wk, kd, bw + mb)) > real(caja(wk, kd, bw)) + 1e-6:      # en el monoambiente no le quita el sofá
            mb, wd, _, mh = sobrante(W - bw - hw - wk, sup, kd, False, True)   # ni el rack al estar)
        bw, hw = bw + mb, hw + mh
        if hall_x0:                                    # R3.7: la entrada en x0, el baño en el otro extremo
            add("hall", "hall", (x0, v0, x0 + hw, v0 + kd))
            add("storage", "storage", (x0 + hw, v0, x1 - bw - wk, v0 + kd), "Depósito")
            add("kitchen", "kitchen", (x1 - bw - wk, v0, x1 - bw, v0 + kd))
            add("bath1", "bath", (x1 - bw, v0, x1, v0 + kd))
        else:
            add("bath1", "bath", (x0, v0, x0 + bw, v0 + kd))
            add("kitchen", "kitchen", (x0 + bw, v0, x0 + bw + wk, v0 + kd))
            add("storage", "storage", (x0 + bw + wk, v0, x1 - hw, v0 + kd), "Depósito")
            add("hall", "hall", (x1 - hw, v0, x1, v0 + kd))
        add("living", "living", (x0, v0 + kd, x1, v1), "Estar-Dormitorio")
        E.append(("living", "bath1", "puerta"))
        if "storage" in R:
            E.append(("living", "storage", "puerta"))
        if vestidor:
            warnings.append(("info", "Vestidor: un monoambiente no lo lleva (no tiene dormitorio)"))
        return R, E, vacios

    # ---- reparto del frente entre día y noche
    nf = nb - 1 if lateral else nb                     # dormitorios al fondo (R5.3: el último, al costado)
    ws = BED_W if lateral else 0.0                     # frente del dormitorio lateral
    Wn, need = _frente_noche(W, nb, lateral, fondo_dormitorios(D))     # v2.65: el principal, con su placard
    if W - need < LIV_MIN:
        hard = 3.0 + V["dorm_principal"]["min_side"] + V["dorm_secundario"]["min_side"] * (nf - 1)
        if W >= hard:
            warnings.append(("info", "Frente de %.1f m: estar y dormitorios ajustados por debajo del frente típico (%.1f m)" %
                             (W, LIV_MIN + need)))
        else:
            warnings.append("Frente de %.1f m insuficiente para estar + %d dormitorio(s) (mín. %.1f m)" %
                            (W, nb, hard))
    xs = x1 - Wn                                       # inicio de la zona de noche
    xb = x1 - ws                                       # R5.3: el dormitorio lateral, en el extremo
    hw = HALL_W
    deep = D - HALL - BED_D >= FR_MIN - 1e-9
    suite, modo = False, None                          # modo (R5.11): la banda de servicios en la tira

    if deep:
        # zona de noche (de fachada hacia el pasillo común): dormitorios | pasillo | franja de servicios | (sobrante)
        hi = min(FR_MAX, D - HALL - BED_D)
        dep = V["deposito"]
        angosta = xs - x0 - hw < KITCH_LINE + KT       # la cocina va en L: la franja no la deja sin su fondo
        lo_k = KITCH_L - (HALL - MIN_SHARE["abierto"] - 0.01) if angosta else 0.0

        def fondos(d):
            """(dormitorios, franja, tira junto al pasillo común) con una franja de fondo d: los dormitorios hasta su
            máximo; muy profunda, la franja crece hasta el suyo y lo que queda es la tira (si es de menos de 1 m, va a la
            franja)."""
            bD = min(BED_MAX, D - HALL - d)
            d = min(FR_MAX, D - HALL - bD)
            e = D - HALL - bD - d
            return (bD, d + e, 0.0) if e < 1.0 else (bD, d, e)

        def franja(claves, L, d, con_dep):
            """Anchos de una franja de largo L y fondo d: sus estancias y, si queda lugar, el depósito (hasta su
            máximo). Devuelve también lo que sobra."""
            anchos = [_ancho(k, d, acc) for k in claves]
            while len(claves) > 1 and sum(anchos) > L + 1e-6 and claves[-1] == "laundry" and \
                    L - sum(anchos[:-1]) < 1.0:        # el lavadero, solo si queda más de 1 m
                claves, anchos = claves[:-1], anchos[:-1]
            if sum(anchos) > L + 1e-6:                 # no entran: la última hasta el final
                anchos[-1] = max(0.0, L - sum(anchos[:-1]))
                return claves, anchos, 0.0
            libre = L - sum(anchos)
            if con_dep and dep["max_area"] > 0 and libre >= max(dep["min_side"], _wa(dep["min_area"], d)) - 1e-6:
                claves, anchos = claves + ["storage"], anchos + [min(libre, _wa(dep["max_area"], d))]
            return claves, anchos, L - sum(anchos)

        if lateral:                                    # R5.3: el dormitorio lateral pide el fondo entre los pasillos
            bedD = max(BED_D, min(BED_MAX, D - HALL - BED_D))
            d = min(FR_MAX, D - HALL - bedD)
            e = D - HALL - bedD - d
            d, e = (d + e, 0.0) if e < 1.0 else (d, e)
            claves = ["bath1"] + (["bath2"] if nb >= 2 and d + 1e-6 >= BATH2_D and xb - xs >= _ancho("bath1", d, acc) +
                                  _ancho("bath2", d) + 1.0 else []) + ["laundry"]
        else:
            claves, d = _servicios(xb - xs, nb, hi, acc, lo_k)
            bedD, d, e = fondos(d)
            if bedD < CAMA_PLACARD[1] - 1e-6 and frente_principal(bedD) > frente_principal(fondo_dormitorios(D)) + 1e-6:
                # v2.65: la franja de servicios le quitó al principal el fondo del placard al pie de la cama: pide el
                # ancho del placard al costado (frente_principal), si el estar conserva su frente mínimo (lo mismo que
                # hace _anchos_dormitorios, que solo puede dárselo si entra en Wn); la franja se rehace con lo que queda
                Wn2, need2 = _frente_noche(W, nb, lateral, bedD)
                if Wn2 > Wn + 1e-6 and W - need2 >= LIV_MIN - 1e-6:
                    Wn, need, xs = Wn2, need2, x1 - Wn2
                    angosta = xs - x0 - hw < KITCH_LINE + KT
                    lo_k = KITCH_L - (HALL - MIN_SHARE["abierto"] - 0.01) if angosta else 0.0
                    claves, d = _servicios(xb - xs, nb, hi, acc, lo_k)
                    bedD, d, e = fondos(d)
        tira = e >= 1.0                                # R5.11: la vivienda tiene tira (sin ella, todo como en v2.41)
        # R5.11 (criterio del usuario): la tira junto al pasillo común (de 1 m o más) es una banda de servicios. Con fondo
        # para la mesada (_banda), «cocina»: el hall va a x0, con la entrada, y la cocina corre de él hacia la tira,
        # seguida del lavadero (puerta desde la cocina); si no, «servicios»: la cocina sigue en la zona de día y la tira
        # lleva el lavadero, desde el hall (o desde la cocina, con el hall en x0). La franja ya no lleva el lavadero y el
        # depósito vuelve a ella (o, si deja menos sin uso, va a la banda, desde el lavadero). La banda no pasa del fondo
        # típico de una cocina: lo que queda sobre ella, si es menos de 1 m, va a la franja; si no, queda sin uso. La
        # cocina va a la banda solo si el estar (con el comedor interior) no queda a más de prop veces su ancho (art. 14)
        # ni deja de alcanzarle la ventana del fondo (con la cocina integrada, art. 27; salvo que no le alcance tampoco con
        # una cocina de fondo típico): si no, sigue en la zona de día, donde la cuida su fondo mínimo
        # Con un muro oblicuo o un entrante, cada banda se mide con el contorno real: el hall de x0 conserva un borde sobre
        # el pasillo común para la puerta de entrada y su lado mínimo; la cocina, su superficie mínima y su mesada
        # (_entra_mesada); el lavadero y el depósito, su superficie mínima y el lavadero sus artefactos (ver entran: en una
        # tira de menos de LAV_W, el lavarropas y su paso, el lavadero va a ella solo si entran). Si ninguna banda entra,
        # todo sigue como en v2.41
        bandas = []                                    # (modo, fondo, ancho de la cocina), de la más profunda a la menos
        if e >= 1.0 and con_banda:
            Sv = vent or ST.DEFAULTS["ventanas"]
            cabe = (xs - x0 - 2 * Sv["mocheta"]) * Sv["alto"]      # el vano más grande del estar en su fachada
            pide = lambda f, a: max(Sv["iluminacion"] * ((D - f) * (xs - x0) + a), _ci()["vano_min"])
            for eb_, wk_ in _banda(e, xs - x0 - hw, xb - x0 - hw):
                xk_ = max(x0 + hw, xs - wk_)
                coc = (xk_, v0, xk_ + wk_, v0 + eb_)
                if D - eb_ <= prop * (xs - x0) + 1e-6 and (cabe >= pide(eb_, wk_ * eb_) - 1e-6 or
                                                           cabe < pide(KITCH_D, tope) - 1e-6) and \
                        real((x0, v0, xk_, v0 + 0.01)) >= 0.01 * ENTRY - 1e-9 and \
                        real((x0, v0, xk_, v0 + eb_)) >= V["hall"]["min_side"] ** 2 - 1e-6 and \
                        real(coc) >= _ci()["min_area"] - 1e-6 and _entra_mesada(coc, forma_de, False):
                    bandas.append(("cocina", eb_, wk_))
            if xb - xs >= max(LAV_W, _wa(V["lavadero"]["min_area"], min(e, KITCH_D))) - 1e-6:
                bandas.append(("servicios", min(e, KITCH_D), 0.0))     # (solo si ninguna «cocina» entra: abajo)
        widths = _anchos_dormitorios(Wn, nf, bedD)

        def noche(d, e, claves, con_dep=None, dep_suite=None):
            """La zona de noche con una franja de fondo d (y la tira de fondo e) de largo xb - xs: sus estancias (claves)
            y, con con_dep, el depósito, si entra (con_dep None: sin banda, solo si no hay tira; dep_suite: lo mismo en
            la franja de la suite, si es otro); lo que sobra: A, B y lo poco que queda, a la última estancia. Devuelve
            sus medidas y los dormitorios por debajo de su lado o su superficie mínima («chicos»)."""
            banda = con_dep is not None
            bD, d_, e_, w, xm_ = bedD, d, e, widths, None
            cl, an, so = franja(claves, xb - xs, d_, con_dep if banda else e_ == 0.0)
            su = False
            if not lateral and nb >= 2 and (so >= 1.0 - 1e-6 or vestidor):
                # A: el principal, al final del pasillo, en suite (su baño en la franja); el pasillo termina en su puerta y
                # la franja de los demás ya no lleva el segundo baño: se rehace con su fondo (R5.10: con vestidor, la suite
                # aunque no sobre franja, si los dormitorios no pierden fondo: el vestidor va entre el principal y su baño)
                c1 = ["bath1"] if banda else ["bath1", "laundry"]
                d1 = _fondo_franja(c1, xb - xs - w[0], min(hi, max(FR_MIN, acc[1] if acc else 0.0, lo_k)), hi, acc)
                bD1, d1, e1 = (bD, d_, e_) if banda else fondos(d1)    # con banda, la tira ya está decidida
                w1 = _anchos_dormitorios(Wn, nf, bD1)
                xm1 = x1 - w1[0]
                vs1 = v1 - bD1 - HALL - d1 + min(d1, max(BATH_MIN_D, _wa(V["bano"]["typ_area"], w1[0])))
                vq = v1 - bD1 - HALL - d1 + min(d1, max(BATH_MIN_D, _wa(V["bano"]["typ_area" if vestidor else "max_area"],
                                                                        w1[0])))      # el principal en suite, desde su baño
                bs = (xm1, v1 - bD1 - HALL - d1, x1, vq)       # el baño en suite
                if w1[0] >= BATH_MIN - 1e-6 and _area_libre(w1[0], min(d1, max(BATH_MIN_D, _wa(V["bano"]["max_area"], w1[0])))) \
                        >= V["bano"]["min_area"] - 1e-6 and sum(_ancho(k, d1, acc) for k in c1) <= xm1 - xs + 1e-6 and \
                        (so >= 1.0 - 1e-6 or (bD1 >= bD - 1e-6 and _medidas_vestidor(w1[0], vs1, v1, v1 - bD1, True)[2])) \
                        and (not tira or real((xm1, vq, x1, v1)) > 1.0 and real(bs) > 1.0 and (not banda or real(bs) >= (
                            bs[2] - bs[0]) * (bs[3] - bs[1]) - 0.05 or _entra_bano_suite(bs, forma_de(bs)))):
                    # (R5.11, con tira: un muro oblicuo no se come el principal ni su baño, que quedaría sin acceso o se
                    # perdería; y la suite que habilita la banda lleva un baño completo, no un toilette)
                    su, bD, d_, e_, w, xm_ = True, bD1, d1, e1, w1, xm1
                    cl, an, so = franja(c1, xm_ - xs, d_, (con_dep if dep_suite is None else dep_suite) if banda else
                                        e_ == 0.0)
            xz = xm_ if su else xb
            chicos = 0
            for j, wj in enumerate(w):
                sd = V["dorm_principal"] if j == 0 else V["dorm_secundario"]
                prof = bD if not (su and j == 0) else bD + HALL + d_ - min(d_, max(BATH_MIN_D, _wa(V["bano"][
                    "typ_area" if vestidor else "max_area"], wj)))          # el principal en suite: hasta su baño
                chicos += (wj < sd["min_side"] - 1e-6) + (_area_libre(wj, prof, 2, 1) < sd["min_area"] - 1e-6)
            an, so = _repartir(cl, an, xz - xs, d_)
            if so < MIN_W["storage"] + 0.1 or so * d_ < 1.0:   # lo poco que queda (no da para una estancia), a la
                j = max(i for i, k in enumerate(cl) if k != "storage" or i == 0)     # última (no al depósito, que no
                an[j] += so                                                          # pasa de su máximo)
                so = 0.0
            return {"suite": su, "bedD": bD, "d": d_, "e": e_, "widths": w, "xm": xm_, "xz": xz, "claves": cl,
                    "anchos": an, "sobra": so, "chicos": chicos}

        def servicios(L, eb, con_dep):
            """R5.11: la banda de largo L y fondo eb después de la cocina (o desde el hall): el lavadero, hasta su máximo;
            con_dep, el depósito, hasta el suyo; lo poco que queda, al lavadero. Devuelve ([[clave, ancho]], lo que queda
            sin uso)."""
            wl = min(L, max(_ancho("laundry", eb), _wa(V["lavadero"]["max_area"], eb)))
            out, rest = [["laundry", wl]], L - wl
            if con_dep and dep["max_area"] > 0 and rest >= max(dep["min_side"], _wa(dep["min_area"], eb)) - 1e-6:
                out.append(["storage", min(rest, _wa(dep["max_area"], eb))])
                rest -= out[-1][1]
            if rest < MIN_W["storage"] + 0.1 or rest * eb < 1.0:
                out[0][1] += max(0.0, rest)
                rest = 0.0
            return out, rest

        def entran(pz, x, eb):
            """R5.11 (revisión): el lavadero y el depósito de la banda, desde x, en la vivienda real: si un muro oblicuo o un
            entrante los recorta, con su superficie mínima (y más de 1 m²: si no, _distribuir los quitaría sin aviso) y el
            lavadero con sus artefactos (_entra_lavadero, con su contorno); entero, el lavadero con sus artefactos si la
            tira tiene menos de LAV_W."""
            for i, (k, w) in enumerate(pz):
                r = (x, v0, x + w, v0 + eb)
                a, x, sigue = real(r), x + w, i + 1 < len(pz)
                if a >= w * eb - 0.05:                 # entero
                    if k == "laundry" and eb < LAV_W - 1e-6 and not _entra_lavadero(r, sigue):
                        return False
                elif a <= max(V["lavadero" if k == "laundry" else "deposito"]["min_area"] - 1e-6, 1.0) or \
                        (k == "laundry" and not _entra_lavadero(r, sigue, forma_de(r))):
                    return False
            return True

        modo, wk_b, resto, xk, opciones = None, 0.0, 0.0, x0 + hw, []
        for grupo in ([b for b in bandas if b[0] == "cocina"], [b for b in bandas if b[0] == "servicios"]):
            # para cada banda posible, el depósito en la franja (criterio del usuario) o en la banda, desde el lavadero
            # (también si no entra en la franja), y la suite decidida sin él con el depósito en su franja: la que deja
            # menos rincones sin uso y dormitorios por debajo de su mínimo y, con los mismos, menos superficie sin uso;
            # con depósito antes que sin él; si da igual, la banda más profunda y el depósito en la franja. Lo que queda
            # sobre la banda, si es menos de 1 m, va a la franja o, si así deja menos rincones, queda sin uso con la banda.
            # La banda de servicios, solo si ninguna con la cocina entra
            if opciones:
                break
            tiras = [(m_, eb_, wk_, r_) for m_, eb_, wk_ in grupo for r_ in (
                [True] if e - eb_ >= 1.0 else [False, True] if (e - eb_) * (xb - xs) >= 1.0 else [False])]
            for modo_, eb_, wk_, sobre in tiras:       # sobre: lo que queda sobre la banda, sin uso (si no, a la franja)
                d_t, e_t, r_t = (d, eb_, e - eb_) if sobre else (d + e - eb_, eb_, 0.0)
                cl_t = [k for k in claves if k != "laundry"]
                if nb >= 2 and "bath2" not in cl_t and d_t + 1e-6 >= BATH2_D and \
                        _ancho("bath1", d_t, acc) + _ancho("bath2", d_t) <= xb - xs + 1e-6:
                    cl_t = ["bath1", "bath2"]
                xk_t = max(x0 + hw, xs - wk_)          # la cocina, desde el hall o, si cabe en la zona de día, hasta su
                xl_t = xs if modo_ == "servicios" else xk_t + wk_   # borde (lo que deja, al hall)
                for cd in ((True, None), (False, None), (False, True)) if dep["max_area"] > 0 else ((True, None),):
                    N = noche(d_t, e_t, cl_t, *cd)
                    pz, rest = servicios(xb - xl_t, eb_, "storage" not in N["claves"])
                    if not entran(pz, xl_t, eb_):
                        continue
                    con = "storage" in N["claves"] or any(k == "storage" for k, _ in pz)
                    huecos = (N["sobra"] > 1e-6) + (rest > 1e-6 or r_t > 1e-6) + N["chicos"]
                    opciones.append(((huecos, round(N["sobra"] * N["d"] + rest * eb_ + r_t * (xb - xs), 1), not con,
                                      len(opciones)), (N, pz, rest, modo_, wk_, r_t, xk_t, xl_t)))
        if opciones:
            N, pz, rest, modo, wk_b, resto, xk, xl = min(opciones, key=lambda o: o[0])[1]
        else:                                          # sin banda (o ninguna entra en la vivienda real): como en v2.41
            N, pz, rest = noche(d, e, claves), [], 0.0
        suite, bedD, d, e, widths, xm = N["suite"], N["bedD"], N["d"], N["e"], N["widths"], N["xm"]
        claves, anchos, sobra, xz = N["claves"], N["anchos"], N["sobra"], N["xz"]
        hv0, hv1 = v1 - bedD - HALL, v1 - bedD
        bv0 = hv0 - d
        if suite:                                      # el baño en suite, hasta su máximo: lo demás, al dormitorio
            wm = widths[0]                             # (R5.10: con vestidor, el típico: lo demás, al vestidor)
            vs = bv0 + min(d, max(BATH_MIN_D, _wa(V["bano"]["typ_area" if vestidor else "max_area"], wm)))
            add("hallway", "hallway", (xs, hv0, xm, hv1))
            add("bath2", "bath", (xm, bv0, x1, vs), "Baño en suite")
            E.append(("bed1", "bath2", "puerta"))
        else:
            add("hallway", "hallway", (xs, hv0, x1, hv1))
        nombres = {"bath1": "Baño", "bath2": "Baño 2", "laundry": "Lavadero", "storage": "Depósito"}
        bx = xs
        for k, w in zip(claves, anchos):
            add(k, "storage" if k == "storage" else "laundry" if k == "laundry" else "bath", (bx, bv0, bx + w, hv0),
                nombres[k])
            E.append(("hallway", k, "puerta"))
            bx += w
        if sobra > 1e-6:                               # C: queda sin uso
            vacios.append(((bx, bv0, xz, hv0), "Sin uso: %.1f m² de franja sin luz junto al pasillo común: la vivienda "
                                               "tiene más frente del que su tipo necesita" % (sobra * d)))
        if modo:                                       # R5.11: la banda de servicios, de fondo e (= eb)
            vb = v0 + e
            if modo == "cocina":
                add("hall", "hall", (x0, v0, xk, vb))
                add("kitchen", "kitchen", (xk, v0, xk + wk_b, vb))
            x, ant = xl, ("kitchen" if modo == "cocina" or (hall_x0 and xs - x0 - hw >= 1.8) else "hall")
            for k, w in pz:
                add(k, k, (x, v0, x + w, vb), nombres[k])
                E.append((ant, k, "puerta"))           # el lavadero, desde la cocina o el hall; el depósito, desde él
                ant, x = k, x + w
            if rest * e + resto * (xb - xs) >= 1.0:    # lo que queda en la banda y sobre ella: un aviso para los dos
                sup = rest * e + resto * (xb - xs) - fuera((x, v0, xb, vb)) - (fuera((xs, vb, xb, bv0)) if resto > 1e-6
                                                                               else 0.0)
                vacios.append(((x, v0, xb, vb), "Sin uso: %.1f m² junto al pasillo común: la vivienda tiene %.1f m de "
                                                "fondo" % (sup, D)))
                if resto > 1e-6:
                    vacios.append(((xs, vb, xb, bv0), ""))        # el mismo aviso
        elif bv0 - v0 >= 1.0:                          # muy profunda: entre la franja y el pasillo común, el depósito
            e, lado, fondo = bv0 - v0, 0.0, 0.0        # junto al hall y lo demás, C: sin uso
            if dep["max_area"] > 0 and e >= dep["min_side"]:
                lado = max(dep["min_side"], min(xb - xs, e, dep["max_area"] ** 0.5))
                fondo = min(e, _wa(dep["max_area"], lado))
                add("storage", "storage", (xs, v0, xs + lado, v0 + fondo), "Depósito")
                E.append(("kitchen" if hall_x0 and xs - x0 - hw >= 1.8 else "hall", "storage", "puerta"))
            resto = (xb - xs) * e - lado * fondo
            if resto >= 1.0:                           # (R5.11: la superficie, la que está dentro de la vivienda)
                sup = resto - fuera((xs + lado, v0, xb, bv0)) - fuera((xs, v0 + fondo, xs + lado, bv0))
                aviso = "Sin uso: %.1f m² junto al pasillo común: la vivienda tiene %.1f m de fondo" % (sup, D)
                vacios.append(((xs + lado, v0, xb, bv0), aviso))
                if fondo < e - 0.3:
                    vacios.append(((xs, v0 + fondo, xs + lado, bv0), ""))      # el mismo aviso
        if lateral:
            add("bed%d" % nb, "bedroom", (xb, v0, x1, hv0), "Dormitorio %d" % nb)
            E.append(("hallway", "bed%d" % nb, "puerta"))
        kd = max(1.8, min(KITCH_D, hv0 - v0))
        if modo == "cocina":                           # R5.11: la cocina, en la banda: el estar baja hasta ella
            kd = e
        elif xs - x0 - hw < KITCH_LINE + KT:           # la heladera no entra en línea: la cocina, más profunda (en L),
            kd = max(kd, min(KITCH_D, hv1 - v0 - MIN_SHARE["abierto"] - 0.01))   # sin cerrar la boca del pasillo
    else:
        # unidad poco profunda: pasillo interno junto al pasillo común, dormitorios detrás; el pasillo termina en la
        # puerta del último dormitorio, que toma lo que queda (v2.33: sin punta de pasillo)
        hv0, hv1 = v0, v0 + HALL
        bedD = D - HALL
        if bedD < BED_D:
            warnings.append("Fondo de %.1f m escaso para dormitorios (mín. %.1f m)" % (D, fondo_min()))
        kd = min(2.6, max(1.8, D * 0.4))
        widths = _anchos_dormitorios(Wn, nf, bedD)
        add("hallway", "hallway", (xs, hv0, x1 - widths[-1] if nf >= 2 else x1, hv1))

    nombre = lambda j: "Dormitorio principal" if j == 0 and nb > 1 else ("Dormitorio %d" % (j + 1) if nb > 1 else
                                                                         "Dormitorio")
    if suite:                                          # A: los demás desde la zona de día; el principal, al final
        bxs = xs
        for j, w in enumerate(widths[1:], 1):
            add("bed%d" % (j + 1), "bedroom", (bxs, v1 - bedD, bxs + w, v1), nombre(j))
            E.append(("hallway", "bed%d" % (j + 1), "puerta"))
            bxs += w
        add("bed1", "bedroom", (xm, vs, x1, v1), nombre(0))
        E.append(("hallway", "bed1", "puerta"))
    else:
        bxs = xs
        for j, w in enumerate(widths):
            fin = not deep and nf >= 2 and j == nf - 1         # poco profunda: el último, al final del pasillo
            add("bed%d" % (j + 1), "bedroom", (bxs, v0 if fin else v1 - bedD, bxs + w, v1), nombre(j))
            E.append(("hallway", "bed%d" % (j + 1), "puerta"))
            bxs += w

    if vestidor:
        _vestidor(R, E, warnings, suite, hv1)

    # ---- zona de día: hall junto a la zona de noche, cocina, comedor/estar a fachada
    sp = min(v1 - 5.0, hv0) if deep else v1 - 5.0      # el estar debe abarcar la boca del pasillo interno
    comedor = lambda lv: v1 - lv > 7.0 and sp - lv >= 2.4      # estar muy profundo: comedor interior + estar a fachada
    # R10.8: la cocina integrada al estar sin ventana, de 5 m² como máximo (norma nacional, art. 27): pierde fondo (lo gana
    # el estar) hasta el que pide su mesada y, si aún pasa, se angosta y lo que deja va al hall. Si se puede, el estar, con
    # el comedor interior, no pasa de prop veces su ancho (art. 14) ni aparece un comedor interior que no había
    p14 = D - prop * (xs - x0)
    t14 = D - (xs - x0) / prop                         # R10.9: el fondo máximo de la cocina con ventana (ver cocina)
    pcom = p14 if comedor(v0 + kd) else max(p14, min(D - 7.0, sp - v0 - 2.4 + 0.01))
    if hall_x0:                                        # la cocina, desde su borde fijo (el de la zona de noche o x0)
        caja = lambda a, b: (xs - a, v0, xs, v0 + b)
    else:
        caja = lambda a, b: (x0, v0, x0 + a, v0 + b)
    if deep and modo == "cocina":                      # R5.11: el hall y la cocina ya están, en la banda
        pass
    elif deep:
        # v2.65: una cocina aparte de 1,80 a 1,99 m de ancho (el estar de 3,04 m deja 1,64–1,99 m) solo lleva su mesada
        # entera contra la pared del costado, con 2,70 m de fondo (_modos_cocina); si la franja de la entrada no llega a
        # ese fondo (kd_max: sin cerrar la boca del pasillo interno), la cocina va dentro del hall («Hall / Cocina»),
        # donde la mesada usa también la pared de la entrada (antes iba aparte y no entraba la heladera). Con
        # KITCH_MESADA (2,00 m) o más, aparte como siempre (la cascada de fondos cuida el art. 14 y la banda)
        wk0 = xs - x0 - hw
        puerta = ("kitchen", "storage", "puerta") in E or ("kitchen", "laundry", "puerta") in E   # pared del costado
        kd_max = max(kd, min(KITCH_D, hv1 - v0 - MIN_SHARE["abierto"] - 0.01))
        entra = any(a <= wk0 + 1e-6 and f <= kd_max + 1e-6 for f, a in _modos_cocina(not puerta))
        if wk0 >= 1.8 - 1e-6 and (wk0 >= KITCH_MESADA + KT - 1e-6 or entra):   # el depósito (o, R5.11, el lavadero de la tira) se abre desde la
            pp = KITCH_L if puerta else 0.0                     # de la cocina: su puerta, fuera de la mesada
            wk, kd = cocina(xs - x0 - hw, kd, caja, [max(pcom, pp), max(p14, pp), pp], not puerta, techo=t14)
            if hall_x0:                                # R3.7: el hall en x0 y la cocina hacia la zona de noche
                add("kitchen", "kitchen", (xs - wk, v0, xs, v0 + kd))
                add("hall", "hall", (x0, v0, xs - wk, v0 + kd))
            else:
                add("kitchen", "kitchen", (x0, v0, x0 + wk, v0 + kd))
                add("hall", "hall", (x0 + wk, v0, xs, v0 + kd))
        else:                                          # la cocina dentro del hall: cuenta solo su parte (sin el hall)
            parte = lambda a, b: real((x0, v0, xs, v0 + b), hw * b)
            kd_ = None
            if luz and luz((x0, v0, xs, v0 + kd)):     # R10.9: con fachada, con su ventana: su parte, de la superficie
                kd_ = min(kd, max(t14, min(f for f, _ in _modos_cocina())))      # típica de una cocina como máximo
                kd_ = _cocina_integrada(xs - x0 - hw, kd_, 0.0, parte, tope=V["cocina"]["typ_area"],
                                        lado=V["cocina"]["min_side"])[1]
            con_luz = kd_ is not None and luz((x0, v0, xs, v0 + kd_))
            kd = kd_ if con_luz else _cocina_integrada(xs - x0 - hw, kd, 0.0, parte)[1]
            tope_hc = V["cocina"]["typ_area"] if con_luz else tope
            if parte(0.0, kd) > tope_hc + 1e-6:        # R5.8a: _cocina_integrada angostó la cocina, pero en el hall no hay
                kd = max(min(f for f, _ in _modos_cocina()),   # parte que angostar: la parte pierde fondo hasta el tope
                         _hasta(lambda t: parte(0.0, t), 0.0, kd, tope_hc))   # (la mesada, en la pared del costado o en L)
            add("hall", "hall", (x0, v0, xs, v0 + kd), "Hall / Cocina")
    else:
        bw = BATH_W1
        wk = xs - x0 - hw - bw                         # la franja de la entrada, con el fondo del baño (no menos de 1,80)
        con_cocina = wk >= 1.8 - 1e-6                  # (R5.16b: justo con el frente de frente_min, sin ruido de redondeo)
        wd = wv = 0.0
        if con_cocina:                                 # (R3.7: con el hall en x0, se pasa por ella al pasillo interno)
            wk, kd = cocina(wk, kd, caja, [kd, max(1.8, p14), 1.8], not hall_x0, True, techo=t14)
            sup = real((x0 + hw, v0, x0 + hw + bw, v0 + kd) if hall_x0 else (x0 + wk, v0, x0 + wk + bw, v0 + kd))
            mb, wd, wv, _ = sobrante(xs - x0 - hw - bw - wk, sup, kd)   # lo que deja la cocina: al baño, a un depósito
            bw += mb                                                    # y lo demás sin uso (el hall no crece)
        if hall_x0:                                    # R3.7: hall en x0, baño a su lado y la cocina hasta la zona de
            if con_cocina:                             # noche (se pasa por ella al pasillo interno)
                add("hall", "hall", (x0, v0, x0 + hw, v0 + kd))
                add("bath1", "bath", (x0 + hw, v0, x0 + hw + bw, v0 + kd), "Baño")
                sin_uso(x0 + hw + bw, wv, kd)
                add("storage", "storage", (x0 + hw + bw + wv, v0, xs - wk, v0 + kd), "Depósito")
                add("kitchen", "kitchen", (xs - wk, v0, xs, v0 + kd))
            else:
                add("hall", "hall", (x0, v0, x0 + hw, v0 + kd))
                add("bath1", "bath", (x0 + hw, v0, xs, v0 + kd), "Baño")
        else:
            if con_cocina:
                add("kitchen", "kitchen", (x0, v0, x0 + wk, v0 + kd))
                add("storage", "storage", (x0 + wk, v0, x0 + wk + wd, v0 + kd), "Depósito")
                sin_uso(x0 + wk + wd, wv, kd)
                add("bath1", "bath", (x0 + wk + wd + wv, v0, xs - hw, v0 + kd), "Baño")
                add("hall", "hall", (xs - hw, v0, xs, v0 + kd))
            else:
                add("bath1", "bath", (x0, v0, xs - hw, v0 + kd), "Baño")
                add("hall", "hall", (xs - hw, v0, xs, v0 + kd))
        E.append(("hall", "bath1", "puerta"))
        if "storage" in R:
            E.append(("living", "storage", "puerta"))
    lv0 = v0 + kd
    if comedor(lv0) and (modo != "cocina" or comedor(v0 + max(1.8, min(KITCH_D, hv0 - v0)))):
        # (R5.11: la cocina en la banda no parte el estar en un comedor que sin ella no había: el estar sigue entero, como
        # lo midió la banda para el art. 14 y su ventana)
        add("dining", "dining", (x0, lv0, xs, sp))
        add("living", "living", (x0, sp, xs, v1), "Estar")
    else:
        add("living", "living", (x0, lv0, xs, v1))
    return R, E, vacios


def _medidas_vestidor(w, by0, by1, hv1, suite):
    """R5.10: (tope, queda, entra) del vestidor de un dormitorio principal de ancho w que va de by0 (el pasillo interno o,
    en suite, su baño) a by1 (la fachada): el vestidor va de by0 a tope, con su fondo típico o, si el dormitorio no llega
    a queda (su medida mínima y el fondo de la cama doble con su paso al pie), menos, hasta su mínimo; en suite, al menos
    hasta el borde del pasillo interno (hv1), que entra por él."""
    sv, sd = V["vestidor"], V["dorm_principal"]
    queda = max(sd["min_side"], CAMA_FONDO, _wa(sd["min_area"], w, 2, 1))     # (R5.8a: hasta la fachada, un tabique)
    vmin = max(sv["min_side"], _wa(sv["min_area"], w, 2, 1))
    vd = max(vmin, min(sv["typ"][1], by1 - by0 - queda))
    tope = max(hv1, by0 + vd) if suite else by0 + vd
    return tope, queda, by1 - tope >= queda - 1e-6 and w >= max(sv["min_side"], sd["min_side"]) - 1e-6


def _vestidor(R, E, warnings, suite, hv1):
    """R5.10 (criterio del usuario: opcional, por tipo del mix): vestidor del dormitorio principal, de todo su ancho, entre
    el pasillo interno y el dormitorio, que sigue con su ventana a la fachada (pasillo → vestidor → dormitorio, abierto a
    él). Con la suite toma lo que el dormitorio tenía detrás del pasillo interno, sin luz, y el baño en suite se abre desde
    el vestidor; sin ella, el fondo de vivienda["vestidor"] a la entrada del dormitorio. El dormitorio conserva su medida
    mínima y el fondo de la cama doble con su paso al pie (sin placard: lo reemplaza el vestidor); si no entra, se avisa
    (no baja la calidad del plano)."""
    if "bed1" not in R or ("hallway", "bed1", "puerta") not in E:
        warnings.append(("info", "Vestidor: no entra (la vivienda no tiene lugar para el dormitorio principal)"))
        return
    k1, (bx0, by0, bx1, by1), n1 = R["bed1"]
    tope, queda, entra = _medidas_vestidor(bx1 - bx0, by0, by1, hv1, suite)
    ancho = max(V["vestidor"]["min_side"], V["dorm_principal"]["min_side"])
    if bx1 - bx0 < ancho - 1e-6:
        warnings.append(("info", "Vestidor: no entra (el dormitorio principal tiene %.2f m de frente y necesita %.2f m)" %
                         (bx1 - bx0, ancho)))
        return
    if not entra:
        warnings.append(("info", "Vestidor: no entra (el dormitorio principal tiene %.2f m de fondo y necesita %.2f m: "
                                 "%.2f m de vestidor y %.2f m de dormitorio)" % (by1 - by0, tope - by0 + queda,
                                                                                 tope - by0, queda)))
        return
    R["vest"] = ("vestidor", (bx0, by0, bx1, tope), NAMES["vestidor"])
    R["bed1"] = (k1, (bx0, tope, bx1, by1), n1)
    E.remove(("hallway", "bed1", "puerta"))
    E += [("hallway", "vest", "puerta"), ("vest", "bed1", "abierto")]
    if ("bed1", "bath2", "puerta") in E:               # la suite: su baño, desde el vestidor
        E.remove(("bed1", "bath2", "puerta"))
        E.append(("vest", "bath2", "puerta"))


# ---------------------------------------------------------------- R5.16b (v2.67): dormitorios en fila sobre la segunda fachada
FILA_SV_MAX = 3.0        # ancho máximo de la columna de servicios del esquema de esquina (lo demás, a los dormitorios)
FILA_BX_MAX = 5.5        # fondo máximo de un dormitorio hacia el interior (la base: el principal de Aruma, 5,2 m)
FILA_BV_MAX = 4.0        # frente máximo de un dormitorio sobre la fachada lateral


def _largos_fila(piezas, L):
    """R5.16b (v2.67): largos de piezas en fila que comparten el largo L; cada pieza es (mínimo, típico, tope). Si entran
    los típicos, lo que sobra se reparte hasta los topes en proporción a lo que a cada una le falta, y lo que aún sobra
    se devuelve; si no, cada una entre su mínimo y su típico, en proporción. (None, 0) si ni los mínimos entran."""
    mins = [p[0] for p in piezas]
    tips = [max(p[0], p[1]) for p in piezas]
    tops = [max(t, p[2]) for t, p in zip(tips, piezas)]
    if sum(mins) > L + 1e-6:
        return None, 0.0
    if sum(tips) <= L + 1e-6:
        out, sobra = list(tips), L - sum(tips)
        for _ in range(len(out) + 1):
            margen = [max(0.0, t - w) for t, w in zip(tops, out)]
            if sobra <= 1e-6 or sum(margen) <= 1e-6:
                break
            f = min(1.0, sobra / sum(margen))
            out = [w + m * f for w, m in zip(out, margen)]
            sobra = L - sum(out)
        return out, max(0.0, sobra)
    t = (L - sum(mins)) / max(1e-9, sum(tips) - sum(mins))
    return [m + (ti - m) * t for m, ti in zip(mins, tips)], 0.0


def _pieza_servicio(clave, w, acc=None):
    """(mínimo, típico, tope) del largo de una pieza de servicio de ancho w: el baño (bath1; el accesible, con su medida),
    el segundo baño (bath2), el lavadero y el depósito."""
    if clave == "bath1":
        sd = V["bano"]
        return (max(BATH_MIN_D, _wa(sd["min_area"], w), acc[1] if acc else 0.0), _wa(sd["typ_area"], w), _wa(sd["max_area"], w))
    if clave == "bath2":
        sd = V["bano_aux"]
        return (max(BATH2_D, _wa(sd["min_area"], w)), _wa(sd["typ_area"], w), _wa(sd["max_area"], w))
    if clave == "laundry":
        sd = V["lavadero"]
        return (max(LAV_W, _wa(sd["min_area"], w)), _wa(sd["typ_area"], w), _wa(sd["max_area"], w))
    sd = V["deposito"]
    return (max(sd["min_side"], _wa(sd["min_area"], w)), max(sd["min_side"], _wa(sd["min_area"], w)), _wa(sd["max_area"], w))


def _servicios_fila(nb, w, L, acc=None):
    """Las piezas de servicio que entran en fila en un largo L con ancho w: el baño siempre y, en este orden mientras
    entren con su mínimo, el segundo baño (con 2 dormitorios o más), el lavadero y un depósito. Devuelve (claves,
    piezas) o None si ni el baño entra."""
    claves = ["bath1"] + (["bath2"] if nb >= 2 else []) + ["laundry", "storage"]
    while claves:
        piezas = [_pieza_servicio(k, w, acc) for k in claves]
        if sum(p[0] for p in piezas) <= L + 1e-6:
            return claves, piezas
        claves = claves[:-1]
    return None


NOMBRE_SERVICIO = {"bath1": ("bath", "Baño"), "bath2": ("bath", "Baño 2"), "laundry": ("laundry", "Lavadero"),
                   "storage": ("storage", "Depósito")}


def _fila_esquina(x0, v0, x1, v1, nb, add, E, vacios, acc, prop):
    """El esquema en fila con la segunda fachada en el costado x1 (la de esquina de la base): la zona de día de todo el
    ancho en la fachada principal (v1); debajo, tres columnas: los dormitorios uno tras otro sobre la fachada lateral
    (el principal arriba, junto al estar; cada uno con su frente sobre esa fachada y el mismo fondo hacia el interior,
    bx), el pasillo interno a lo largo de ellos y, contra el otro costado, la columna de servicios (la cocina arriba,
    abierta al estar y al pasillo; el baño, el segundo baño, el lavadero y el depósito, con puerta al pasillo) con el
    hall y la puerta de entrada abajo, junto al pasillo común. Devuelve si entra."""
    W, D = x1 - x0, v1 - v0
    sv = max(BATH_W1, KITCH_MESADA + KT, acc[0] if acc else 0.0)
    kd = _fondo_cocina(sv, True)                       # la cocina en L: su largo en la columna
    kd += T2                                           # (R5.8a: el baño debajo; arriba, abierta al estar)
    sv_max = max(sv, min(FILA_SV_MAX, _ci()["max_area"] / kd))
    bx = W - HALL - sv
    if bx > FILA_BX_MAX:                               # con más frente, la columna de servicios se ensancha
        sv = min(sv_max, W - HALL - FILA_BX_MAX)
        bx = W - HALL - sv
    if bx < BED_D - 1e-6 or bx > FILA_BX_MAX + 0.05:
        return False
    estar_typ = V["estar_por_dorms"][min(nb, len(V["estar_por_dorms"]) - 1)]
    dd = max(LIV_MIN, W / prop, min(4.5, estar_typ / W))
    specs = [V["dorm_principal"]] + [V["dorm_secundario"]] * (nb - 1)
    bvs, sobra = _largos_fila([(max(sd["min_side"], _wa(sd["min_area"], bx, 1)), sd["typ"][0], FILA_BV_MAX) for sd in specs],
                              D - dd)
    if bvs is None:
        return False
    if sobra > 1e-6:                                   # lo que sobra, al estar (hasta 4,5 m de fondo)
        extra = min(sobra, max(0.0, 4.5 - dd))
        dd, sobra = dd + extra, sobra - extra
    v_top = v1 - dd
    xb = x1 - bx
    hd = max(HALL_W, V["hall"]["min_side"])            # el hall, de todo el ancho de servicios y pasillo
    Ls = v_top - (v0 + hd)
    sf = _servicios_fila(nb, sv, Ls - kd, acc)
    if sf is None:
        return False
    claves, piezas = sf
    largos, sobra_s = _largos_fila(piezas, Ls - kd)
    hd += sobra_s                                      # lo que sobra en la columna, al hall
    nombre = lambda j: "Dormitorio principal" if j == 0 and nb > 1 else ("Dormitorio %d" % (j + 1) if nb > 1 else
                                                                         "Dormitorio")
    v = v_top
    for j, bv in enumerate(bvs):
        add("bed%d" % (j + 1), "bedroom", (xb, v - bv, x1, v), nombre(j))
        E.append(("hallway", "bed%d" % (j + 1), "puerta"))
        v -= bv
    if v - v0 > 0.3:                                   # (no entra con los frentes típicos en fila: queda sin uso)
        vacios.append(((xb, v0, x1, v), "Sin uso: %.1f m² al pie de los dormitorios en fila" % ((v - v0) * bx)))
    add("hall", "hall", (x0, v0, xb, v0 + hd))
    add("hallway", "hallway", (xb - HALL, v0 + hd, xb, v_top))
    wk = min(sv, _ci()["max_area"] / kd)               # la cocina, de 5 m² como máximo (art. 27)
    add("kitchen", "kitchen", (x0, v_top - kd, x0 + wk, v_top))
    if sv - wk > 0.3:
        vacios.append(((x0 + wk, v_top - kd, x0 + sv, v_top), ""))
    v = v_top - kd
    for k, l in zip(claves, largos):
        kind, nm = NOMBRE_SERVICIO[k]
        add(k, kind, (x0, v - l, x0 + sv, v), nm)
        E.append(("hallway", k, "puerta"))
        v -= l
    add("living", "living", (x0, v_top, x1, v1))
    return True


def _fila_pasante(x0, v0, x1, v1, nb, add, E, vacios, acc, prop):
    """El esquema en fila de una vivienda pasante (el borde del pasillo común da al aire: la pasarela o el patio): la
    zona de día en ese borde, con la puerta de entrada en el estar, junto al paso; después la cocina, cerrada, con
    puerta desde el paso (así el estar conserva una pared sin ventana para el rack de la TV, con el sofá bajo la
    ventana: con la cocina abierta, el paso delante de la abertura y la puerta de entrada no dejaban lugar en 3,6 m de
    ancho), el paso a lo largo del costado x1 y, junto a él, el baño (y el segundo baño, el lavadero y el depósito, si
    entran); al fondo, sobre la fachada principal, los dormitorios (uno de todo el ancho; con dos o más, uno al lado
    del otro con su pasillo interno). Si la vivienda es más ancha que la cocina de 5 m², lo que queda junto a ella es un
    depósito con puerta desde el paso. Devuelve si entra."""
    W, D = x1 - x0, v1 - v0
    pw = V["pasillo"]["min_side"]                      # el paso, de su lado mínimo (0,90 m): la cocina en línea entra
    wk_lib = W - pw                                    # en 3,60 m
    if wk_lib - T2 < max(KITCH_FRENTE + KT, _ci()["min_side"]) - 1e-6 or W < V["dorm_principal"]["min_side"] - 1e-6:
        return False
    kd = _fondo_cocina(wk_lib - T2, True) + TAB        # (R5.8a: la cocina cerrada tiene tabiques en los cuatro lados: el
                                                       # paso y el depósito al costado, el estar y el baño en el fondo)
    wk = min(wk_lib, V["cocina"]["typ_area"] / kd)     # cerrada: hasta su superficie típica (no rige el art. 27)
    pw = min(1.5, max(pw, W - wk))                     # lo que la cocina no usa, al paso (hasta 1,50 m)
    wd = W - pw - wk                                   # y si queda más, un depósito junto a la cocina
    if wd < max(V["deposito"]["min_side"], _wa(V["deposito"]["min_area"], kd)) - 1e-6:
        wk, wd = wk + wd, 0.0
    bedD = max(BED_D, CAMA_PLACARD[1] if W < CAMA_PLACARD[0] - 1e-6 else BED_D)   # el placard al pie si no entra al costado
    h2 = HALL if nb >= 2 else 0.0                      # el pasillo interno de los dormitorios
    ld_min = max(V["estar_comedor"]["min_side"], _wa(V["estar_comedor"]["min_area"], W, 0, 1), W / prop)
    estar_typ = V["estar_por_dorms"][min(nb, len(V["estar_por_dorms"]) - 1)]
    ld_typ = max(ld_min, min(5.0, estar_typ / W))
    sf = _servicios_fila(nb, W - pw, D - ld_min - kd - bedD - h2, acc)
    if sf is None:
        return False
    claves, piezas = sf
    rem = D - kd - h2 - bedD - ld_min - sum(p[0] for p in piezas)
    ld = ld_min + min(rem, ld_typ - ld_min)
    rem -= ld - ld_min
    largos, _ = _largos_fila(piezas, sum(p[0] for p in piezas) + rem)
    rem -= sum(largos) - sum(p[0] for p in piezas)
    bd = bedD + min(rem, max(0.0, BED_MAX - bedD))
    rem -= bd - bedD
    ld += rem                                          # lo que queda, al estar (con el comedor si es muy profundo)
    if ld > 7.0 and ld - 5.0 >= 2.4:
        add("living", "living", (x0, v0, x1, v0 + 5.0), "Estar")
        add("dining", "dining", (x0, v0 + 5.0, x1, v0 + ld))
    else:
        add("living", "living", (x0, v0, x1, v0 + ld))
    vk = v0 + ld
    xk = x1 - pw - wk                                  # la cocina, contra el paso (su puerta)
    add("kitchen", "kitchen", (xk, vk, xk + wk, vk + kd))
    E.append(("hallway", "kitchen", "puerta"))
    E.append(("living", "kitchen", "muro"))            # (sin abertura entre el estar y la cocina)
    if wd > 0.3:
        add("storage", "storage", (x0, vk, xk, vk + kd), "Depósito")
        E.append(("living", "storage", "puerta"))      # el depósito, del otro lado, con puerta desde el estar
    v_top = v1 - bd - h2                               # donde empiezan los dormitorios (o su pasillo)
    add("hallway", "hallway", (x1 - pw, vk, x1, v_top))
    v = vk + kd
    for k, l in zip(claves, largos):
        kind, nm = NOMBRE_SERVICIO[k]
        add(k, kind, (x0, v, x1 - pw, v + l), nm)
        E.append(("hallway", k, "puerta"))
        v += l
    if v_top - v > 0.3:
        vacios.append(((x0, v, x1 - pw, v_top), "Sin uso: %.1f m² junto al paso" % ((v_top - v) * (W - pw))))
    if nb >= 2:
        add("hallway2", "hallway", (x0, v_top, x1, v_top + h2))
        E.append(("hallway", "hallway2", "abierto"))
        widths = _anchos_dormitorios(W, nb, bd)
        bxs = x0
        for j, w in enumerate(widths):
            add("bed%d" % (j + 1), "bedroom", (bxs, v1 - bd, bxs + w, v1),
                "Dormitorio principal" if j == 0 else "Dormitorio %d" % (j + 1))
            E.append(("hallway2", "bed%d" % (j + 1), "puerta"))
            bxs += w
    else:
        add("bed1", "bedroom", (x0, v1 - bd, x1, v1), "Dormitorio")
        E.append(("hallway", "bed1", "puerta"))
    return True


def _plan_fila(x0, v0, x1, v1, nb, lado, warnings, acc=None, prop=None):
    """R5.16b (v2.67): los rectángulos de estancias del esquema «dormitorios en fila sobre la segunda fachada» (25 de 44
    viviendas de la base de tipologías: pasante, esquina y en fila), como _plan_rects: lado 1, la segunda fachada en el
    costado x1 (_fila_esquina; con la fachada en x0, layout_unit hace el plano al revés); lado 0, el borde del pasillo
    común da al aire (_fila_pasante). Devuelve (R, E, vacíos) o None si no entra."""
    prop = prop or ST.DEFAULTS["ventanas"]["proporcion_max"]
    R, E, vacios = {}, [], []

    def add(i, kind, rect, name=None):
        if rect[2] - rect[0] > 0.3 and rect[3] - rect[1] > 0.3:
            R[i] = (kind, rect, name or NAMES[kind])
    if nb < 1:
        return None
    ok = (_fila_esquina if lado else _fila_pasante)(x0, v0, x1, v1, nb, add, E, vacios, acc, prop)
    return (R, E, vacios) if ok else None


def _fila_posible(poly, nb, is_facade):
    """R5.16b (v2.67): la segunda fachada con la que una vivienda puede ir en fila: 1 (el costado x1), -1 (x0), 0 (el
    borde del pasillo común, v0: pasante) o None. La de esquina necesita la fachada principal entera al fondo."""
    if is_facade is None or nb < 1:
        return None
    (x0, v0, x1, v1), _ = _main_rect(poly)
    fondo = _luz(is_facade, (x0, v1), (x1, v1))
    if fondo < 0.75:
        return None
    if _luz(is_facade, (x0, v0), (x1, v0)) >= 0.75:
        return 0
    if _luz(is_facade, (x1, v0), (x1, v1)) >= 0.75:
        return 1
    if _luz(is_facade, (x0, v0), (x0, v1)) >= 0.75:
        return -1
    return None


def frente_fila(nb, D, lado, prop=None):
    """R5.16b (v2.67): el frente que pide el esquema en fila para nb dormitorios con fondo D y la segunda fachada
    `lado` (ver _plan_fila), o None si con ese fondo no entra (la fila de dormitorios más la zona de día son más largas
    que D): de esquina, la columna de servicios (el baño y la cocina en L), el pasillo interno y el fondo mínimo de un
    dormitorio; pasante, la cocina en L con su paso al costado (o lo que piden los dormitorios uno al lado del otro)."""
    prop = prop or ST.DEFAULTS["ventanas"]["proporcion_max"]
    if nb < 1:
        return None
    specs = [V["dorm_principal"]] + [V["dorm_secundario"]] * (nb - 1)
    if lado == 0:
        pw = V["pasillo"]["min_side"]                  # como en _fila_pasante: el paso de 0,90 m
        base = max(V["dorm_principal"]["min_side"], V["estar_comedor"]["min_side"],
                   facade_min(nb) - LIV_MIN if nb >= 2 else 0.0)
        for w in sorted({max(base, pw + KITCH_MESADA + KT), max(base, pw + KITCH_LINE + KT)}):    # la cocina en L o en línea
            kd = _fondo_cocina(w - pw, True)           # (la de línea pide más frente y menos fondo)
            need = max(V["estar_comedor"]["min_side"], _wa(V["estar_comedor"]["min_area"], w, 0, 1), w / prop) + kd + \
                _pieza_servicio("bath1", w - pw)[0] + BED_D + (HALL if nb >= 2 else 0.0)
            if D >= need - 1e-6:
                return w
        return None
    sv = max(BATH_W1, KITCH_MESADA + KT)
    w = sv + HALL + BED_D
    dd = max(LIV_MIN, w / prop)
    need = dd + sum(max(sd["min_side"], _wa(sd["min_area"], BED_D, 1)) for sd in specs)
    return w if D >= need - 1e-6 else None



def _main_rect(poly):
    """Rectángulo principal de la unidad (el de mayor área apoyado en el pasillo común) y anexos.
    Los anexos son las partes que quedan fuera: bolsillos laterales o sobre el rectángulo."""
    x0, v0, x1, v1 = G.bbox(poly)
    xs = sorted({round(p[0], 4) for p in poly})
    slabs = []
    for a, b in zip(xs, xs[1:]):
        if b - a < 0.05:
            continue
        sp = G.clip_rect(poly, a, b)
        if not sp:
            slabs.append([a, b, v0])
            continue
        _, s0, _, s1 = G.bbox(sp)
        slabs.append([a, b, s1 if abs(s0 - v0) < 0.05 else v0])
    best = None
    for i in range(len(slabs)):
        top = 1e9
        for j in range(i, len(slabs)):
            if j > i and abs(slabs[j][0] - slabs[j - 1][1]) > 1e-6:
                break
            top = min(top, slabs[j][2])
            A = (slabs[j][1] - slabs[i][0]) * (top - v0)
            if best is None or A > best[0] + 1e-6:
                best = (A, slabs[i][0], slabs[j][1], top)
    if best is None or best[0] <= 0:
        return (x0, v0, x1, v1), []
    _, mx0, mx1, mtop = best
    annex = []
    for p in (G.clip_rect(poly, None, mx0), G.clip_rect(poly, mx1, None), G.clip_rect(poly, mx0, mx1, mtop, None)):
        if p and abs(G.area(p)) > 1.0:
            bx0, by0, bx1, by1 = G.bbox(p)
            if min(bx1 - bx0, by1 - by0) >= 1.0:      # tiras más finas se ignoran (quedan sin uso)
                annex.append(p)
    return (mx0, v0, mx1, mtop), annex


def _main_con_luz(poly, main, annexes, is_facade, paso=0.25):
    """Si solo una parte del fondo del rectángulo principal da a la fachada (un codo, la esquina de un patio), el
    principal se achica a esa parte y lo demás pasa a anexo: las estancias habitables quedan con luz y el resto es
    depósito (R3.2). Si no hay luz en ningún tramo, o el tramo con luz es muy corto, no cambia nada."""
    x0, v0, x1, v1 = main
    n = max(1, int((x1 - x0) / paso))
    xs = [x0 + (x1 - x0) * k / n for k in range(n + 1)]
    luz = [is_facade((xs[k], v1), (xs[k + 1], v1)) for k in range(n)]
    k = 0
    while k < n:                         # tramos oscuros de menos de 1 m (junto a una medianera o un tabique): no cuentan
        if luz[k]:
            k += 1
            continue
        j = k
        while j + 1 < n and not luz[j + 1]:
            j += 1
        if xs[j + 1] - xs[k] < 1.0:
            luz[k:j + 1] = [True] * (j + 1 - k)
        k = j + 1
    if all(luz) or not any(luz):
        return main, annexes
    best, k = None, 0
    while k < n:
        if not luz[k]:
            k += 1
            continue
        j = k
        while j + 1 < n and luz[j + 1]:
            j += 1
        if best is None or xs[j + 1] - xs[k] > best[1] - best[0]:
            best = (xs[k], xs[j + 1])
        k = j + 1
    lx0, lx1 = best
    if lx1 - lx0 < LIV_MIN + BED_W:
        return main, annexes
    extra = [G.clip_rect(poly, x0, lx0, v0, v1) if lx0 > x0 + 0.05 else [],
             G.clip_rect(poly, lx1, x1, v0, v1) if lx1 < x1 - 0.05 else []]
    return (lx0, v0, lx1, v1), annexes + [p for p in extra if p and abs(G.area(p)) > 1.0]


TODO_BIEN = "Dormitorios y estar con fachada; medidas mínimas cumplidas"


def _calidad(checks):
    """Calidad del plano: el porcentaje de sus comprobaciones (sin las informativas) que se cumplen."""
    real = [c for c in checks if not c.get("info")]
    return round(100.0 * sum(1 for c in real if c["ok"]) / len(real)) if real else 100


def superficie_vivienda(res, area_muros, vivienda=None):
    """R10.8: la superficie de la vivienda con muros (ver units.superficie_con_muros) contra la mínima de la norma nacional
    según sus dormitorios (art. 3: vivienda["superficie_min"]; más allá de la lista, el último salto por cada dormitorio);
    el estudio dibujado cuenta como dormitorio (art. 6, presunción de destino). Un monoambiente no tiene el dormitorio y
    el baño independientes (art. 2): se acepta desde el primer valor de la lista (criterio del usuario). Agrega a
    res["checks"] una falla (y quita «medidas mínimas cumplidas») o una línea informativa y recalcula res["score"]. La
    llama layout después de units.unit_rooms: vale igual para todas las variantes del plano."""
    tabla = (vivienda or V).get("superficie_min") or ST.DEFAULTS["vivienda"]["superficie_min"]
    estudios = sum(1 for r in res["rooms"] if r["kind"] == "study")
    n = res["bedrooms"] + estudios
    paso = tabla[-1] - tabla[-2] if len(tabla) > 1 else 0
    minimo = tabla[n] if n < len(tabla) else tabla[-1] + paso * (n - len(tabla) + 1)
    a = round(area_muros, 1)
    falla = a < minimo - 1e-6
    if n == 0:
        msg = ("Monoambiente de %.1f m² con muros: la norma nacional pide dormitorio y baño como locales independientes "
               "(art. 2); se acepta desde %g m² (criterio del usuario)" % (a, minimo)) if falla else \
            ("Monoambiente de %.1f m² con muros: se acepta aunque el dormitorio no sea un local independiente (art. 2, "
             "criterio del usuario)" % a)
    else:
        dorm = ("1 dormitorio" if n == 1 else "%d dormitorios" % n) + (" (contando el estudio, art. 6)" if estudios else "")
        msg = ("Superficie con muros %.1f m² < mínimo %g m² para %s (norma nacional, art. 3)" % (a, minimo, dorm)) \
            if falla else ("Superficie con muros %.1f m² (mínimo %g m² para %s, art. 3)" % (a, minimo, dorm))
    if falla:
        res["checks"] = [c for c in res["checks"] if c["msg"] != TODO_BIEN] + [{"ok": False, "msg": msg}]
    else:
        res["checks"].append({"ok": True, "info": True, "msg": msg})
    res["score"] = _calidad(res["checks"])
    return res


def _faltan(rooms):
    """Programa mínimo (v2.30; norma nacional, arts. 17 y 21): toda vivienda tiene baño y cocina; la cocina dentro del
    hall («Hall / Cocina») cuenta. Lo que falta baja la calidad del plano."""
    out = []
    if not any(r["kind"] == "bath" for r in rooms):
        out.append({"ok": False, "msg": "Sin baño: toda vivienda lleva uno (norma nacional, art. 17)"})
    if not any(r["kind"] == "kitchen" or "Cocina" in r["name"] for r in rooms):
        out.append({"ok": False, "msg": "Sin cocina: toda vivienda lleva una (norma nacional, art. 21)"})
    return out


def _std_for(r, nb, integradas=(), principal="bed1"):
    """Medidas mínimas de la estancia r. integradas (R10.8): las cocinas integradas al estar sin ventana propia, que
    toman las de la norma nacional para ellas (art. 27: de 3 a 5 m², lado 1,40) en lugar de las de una cocina (art. 21).
    principal (R5.12): el id del dormitorio principal."""
    k, i = r["kind"], r["id"]                          # (R5.8a: las de la norma, VN, libres: se comparan con la medida libre)
    if k == "bedroom":
        return VN["dorm_principal"] if (i == principal) else VN["dorm_secundario"]
    if k == "kitchen" and i in integradas:
        return VN.get("cocina_integrada") or ST.DEFAULTS["vivienda"]["cocina_integrada"]
    return {"living": VN["estar_comedor"], "kitchen": VN["cocina"], "laundry": VN["lavadero"], "study": VN["estudio"],
            "hallway": VN["pasillo"], "hall": VN["hall"], "vestidor": VN["vestidor"],
            "bath": VN["bano"] if i == "bath1" else VN["bano_aux"]}.get(k)


def layout_unit(poly, nb, is_facade=None, vivienda=None, equip=None, accesible=False, ediciones=None, ventanas=None,
                entrada=None, vestidor=False, punta=None, acceso=None, puerta_lateral=None):
    """Distribuye una unidad. poly en el marco de la unidad. Devuelve dict con estancias, puertas, grafo, equipamiento y
    comprobaciones. is_facade(p, q): opcional, dice si el segmento p-q (marco de la unidad) está sobre la fachada.
    accesible: puertas de dormitorios y baño de DOOR_ACC, el baño abre hacia afuera y se equipa para silla de ruedas.
    ediciones (R5.7): [(k, {"op": "pared", "p", "a"} | {"op": "puerta", "p", "entre"?, "a"?, "ancho"?, "abre"?})] en el
    marco de la unidad, en orden; el resultado trae en "ediciones" las k aplicadas y en "paredes" los tabiques interiores.
    R5.12 (v2.70), estancias editables, también en ediciones y en orden con las paredes: {"op": "nombre", "p", "nombre"},
    {"op": "tipo", "p", "tipo": dormitorio | estudio | depósito | lavadero | comedor | principal | secundario},
    {"op": "quitar", "p"} (el dormitorio se une al contiguo) y {"op": "unir", "p", "a"} (dos dormitorios contiguos), con
    p (y a) dentro de la estancia; se aplican después de _plan_rects y antes de puertas, ventanas y equipamiento. La cama
    doble y el placard siguen al dormitorio principal ("principal": true en su estancia; tras quitar o unir, el más
    grande, salvo que el usuario lo haya fijado con tipo); "bedrooms" cuenta los dormitorios reales si cambiaron; lo que
    no se puede aplicar va en "avisos_estancias" (y como línea informativa) y el plano queda como estaba.
    ventanas (R5.5): medidas de standards["ventanas"]; el resultado trae "ventanas" [{room, p, q, n, ancho, alto, area,
    minimo}] (p-q sobre la fachada, n hacia afuera).
    R5.3: una vivienda con fachada al fondo y en un costado (de esquina o de extremo) la usa: el estar va a la esquina o,
    si el frente no alcanza, el último dormitorio va a ese costado (ver _segunda_fachada); el plano se hace al revés
    cuando hace falta y se devuelve en el marco de la vivienda.
    entrada (R3.7): (lo, hi) del borde v0 sobre el que sigue el pasillo común (se cortó donde ya no hacía falta); si la
    puerta de entrada no cae ahí, el hall va al extremo de ese lado (plano derecho o al revés).
    vestidor (R5.10): el dormitorio principal lleva vestidor, si entra (ver _vestidor).
    punta (R3.7b): (lo, hi) del borde v0 junto a una punta libre del pasillo común (la vivienda es la del extremo): si
    la puerta de entrada no cae ahí, se prueba el plano con el hall en ese extremo (derecho o al revés) y se usa si no
    empeora (calidad y estancias del programa), así el pasillo termina en la última puerta; a diferencia de entrada,
    no obliga ni avisa.
    acceso (R5.13, v2.68): x del borde v0 donde el usuario quiere la puerta de entrada (el acceso a mano): el plano va
    con la entrada en la más cercana de las tres posiciones que sabe armar —la punta x0 (hall_x0), la de siempre (junto
    a la zona de noche, o la del esquema en fila) y la punta x1 (el plano al revés)—; con entrada, el acceso tiene que
    caer en ese tramo, y si el plano con la entrada en la punta pierde cocina, dormitorios, estar o baño se avisa y se
    ignora. El resultado trae "acceso" = {x: la puerta de entrada, posicion: x0 | medio | x1, aplicado, motivo?}; los
    demás cambios a mano (ediciones) siguen valiendo (ver con_acceso).
    puerta_lateral (R11.4, v2.72): -1 | 1, la vivienda con fachada lateral del pasillo lateral entre medianeras: el
    pasillo común da al costado x0 (-1) o x1 (1) del marco, no a v0. El hall va a esa esquina (hall_x0, con el plano
    derecho o al revés) y la puerta de entrada se pone en el borde lateral del hall; entrada, punta, acceso y el esquema
    en fila no aplican (un acceso a mano se avisa y se ignora)."""
    equip = equip or ST.DEFAULTS["equipamiento"]
    configure(vivienda or ST.DEFAULTS["vivienda"], equip, accesible)
    poly = G.ensure_ccw(poly)
    if puerta_lateral is not None:                     # R11.4: el hall en la esquina del pasillo común, en el costado
        res = _plano_lateral(poly, nb, is_facade, equip, accesible, ediciones, ventanas, vestidor, puerta_lateral > 0)
        if acceso is not None:
            res["checks"].append({"ok": True, "info": True, "msg": "Acceso a mano: la entrada de una vivienda con fachada "
                                  "lateral va en el costado, junto al hall; el plano queda como estaba"})
            res["acceso"] = {"x": None, "x_medio": None, "posicion": None, "aplicado": False,
                             "motivo": "la entrada va en el costado, junto al hall"}
        res["checks"].append({"ok": True, "info": True, "msg": "Fachada lateral: la entrada por el costado, en el hall; "
                              "el estar y los dormitorios, sobre la fachada lateral"})
        res["segunda_fachada"] = None
        return res
    espejar, lateral, lado = _segunda_fachada(poly, nb, is_facade)
    lat_posible = lateral

    def plano(espejar, lateral, ediciones, hall_x0=False):
        if not espejar:
            return _distribuir(poly, nb, is_facade, equip, accesible, ediciones, ventanas, lateral, hall_x0, vestidor)
        bx0, _, bx1, _ = G.bbox(poly)
        m = lambda p: (bx0 + bx1 - p[0], p[1])
        fac = lambda p, q: is_facade(m(p), m(q)) if is_facade else None
        if hasattr(is_facade, "ventana"):
            fac.ventana = lambda p, q: is_facade.ventana(m(q), m(p))     # la estancia sigue a la izquierda
        ed = [(k, dict(e, p=m(e["p"]), a=m(e["a"]) if e.get("a") else None)) for k, e in (ediciones or [])]
        return _espejar(_distribuir([m(p) for p in poly][::-1], nb, fac if is_facade else None, equip, accesible, ed,
                                    ventanas, lateral, hall_x0, vestidor), m)
    programa = _programa
    esencial = lambda r: [min(n, 1) if i == 0 else n for i, n in enumerate(programa(r)) if i != 3]   # un baño, cocina,
                                                                                                    # dormitorios y estar
    def dorm_lateral(con, sin):
        """R5.3: el plano con el último dormitorio al costado vale si ese dormitorio llega a su mínimo y no pierde
        estancias (el baño 2, solo con hasta 2 dormitorios: criterio del usuario)."""
        lat = next((r for r in con["rooms"] if r["id"] == "bed%d" % nb), None)
        pc, ps = programa(con), programa(sin)
        return bool(lat and lat["area"] >= V["dorm_secundario"]["min_area"] - 1e-6 and
                    pc[0] >= (1 if nb <= 2 else max(1, ps[0])) and all(a >= b for a, b in zip(pc[1:], ps[1:])))
    elegido = None                                     # se comparan sin los cambios a mano: la elección no depende
    if lateral:                                        # de ellos. El dormitorio al costado, solo si el plano mejora y
        con, sin = plano(espejar, True, None), plano(lado == 1, False, None)   # no pierde estancias
        if dorm_lateral(con, sin) and con["score"] > sin["score"]:
            elegido = con
        else:
            espejar, lateral, elegido = lado == 1, False, sin
    if espejar and not lateral:                        # el estar a la esquina, si el plano al revés no es peor ni
        elegido = elegido or plano(True, False, None)  # pierde estancias (en una vivienda irregular, el rectángulo
        recto = plano(False, False, None)              # principal puede cambiar)
        if elegido["score"] < recto["score"] or any(a < b for a, b in zip(programa(elegido), programa(recto))):
            espejar, elegido = False, recto
    hall_x0 = False
    puntas = []

    def extremos():
        """R3.7 y R5.13: los planos con el hall en una punta, (plano, espejar, lateral, hall_x0): derecho (x0), al revés
        (x1) y, si la fachada lateral lo permite, con el último dormitorio al costado (R5.3, mismo criterio); se arman
        una sola vez, sin los cambios a mano."""
        if not puntas:
            cands = [(e_, False, True) for e_ in (False, True)]
            if lat_posible:
                cands.append((lado == -1, True, True))
            hechos = {}
            for e_, l_, h_ in cands:
                r_ = hechos[(e_, l_)] = plano(e_, l_, None, h_)
                if l_ and not dorm_lateral(r_, hechos[(e_, False)]):
                    continue                           # el dormitorio al costado, con el mismo criterio (R5.3)
                puntas.append((r_, e_, l_, h_))
        return puntas
    if entrada is not None and not _entra(elegido or plano(espejar, lateral, None), entrada):
        # R3.7: el pasillo común solo sigue sobre una parte del borde: el hall (y la entrada) a ese extremo, con el plano
        # derecho (x0) o al revés (x1); el mejor de los que cumplen
        mejor = None
        for r_, e_, l_, h_ in extremos():
            if _entra(r_, entrada) and (mejor is None or r_["score"] > mejor[0]["score"]):
                mejor = (r_, e_, l_, h_)
        if mejor:
            elegido, espejar, lateral, hall_x0 = mejor
        else:
            elegido = None
    if punta is not None and entrada is None and not hall_x0:
        base = elegido if elegido is not None else plano(espejar, lateral, None)
        if not _entra(base, punta):                    # R3.7b: el hall en la punta, si el plano no empeora
            mejor = None
            for e_ in (False, True):
                r_ = plano(e_, False, None, True)
                if _entra(r_, punta) and r_["score"] >= base["score"] and \
                        all(a >= b for a, b in zip(programa(r_), programa(base))) and \
                        (mejor is None or r_["score"] > mejor[0]["score"]):
                    mejor = (r_, e_)
            if mejor:
                elegido, espejar, lateral, hall_x0 = mejor[0], mejor[1], False, True

    def con_acceso(res, base):
        """R5.13 (v2.68): el acceso a mano. Entre las tres posiciones de la entrada que el plano sabe armar —la punta x0
        (hall_x0, derecho), la de siempre (junto a la zona de noche, o la del esquema en fila) y la punta x1 (hall_x0 con
        el plano al revés)— elige la que deja la puerta de entrada más cerca de acceso; por punta, el plano de más calidad
        entre el derecho y el del dormitorio al costado (extremos). res: el plano de siempre, con los cambios a mano;
        base: el mismo sin ellos (la elección no depende de ellos, como lo demás). Devuelve (plano, espejar, lateral): el
        mismo res si la más cercana es la de siempre, o si el pedido no vale —fuera del tramo de entrada (R3.7), o un
        plano que pierde cocina, dormitorios, estar o baño (esencial)—, que se avisa y se ignora. El plano trae "acceso"
        = {x, x_medio (la puerta de la posición de siempre: la web la usa para decir a cuál va), posicion, aplicado,
        motivo?}."""
        px, motivo = _x_entrada(base), None
        if px is None:
            motivo = "la vivienda no tiene puerta de entrada"
        elif entrada is not None and not (entrada[0] - 0.05 <= acceso <= entrada[1] + 0.05):
            motivo = "la entrada pedida no da al pasillo común"
        if motivo is None:
            opciones = [("medio", base, espejar, lateral)]
            for r_, e_, l_, h_ in extremos():
                k = "x1" if e_ else "x0"
                if _x_entrada(r_) is None:
                    continue
                i = next((j for j, o in enumerate(opciones) if o[0] == k), None)
                if i is None:
                    opciones.append((k, r_, e_, l_))
                elif r_["score"] > opciones[i][1]["score"]:
                    opciones[i] = (k, r_, e_, l_)
            donde, cand, e_, l_ = min(opciones, key=lambda o: abs(_x_entrada(o[1]) - acceso))   # a igual distancia,
            if donde == "medio":                                                                # la de siempre
                res["acceso"] = {"x": _x_entrada(res), "x_medio": px, "posicion": "medio", "aplicado": True}
                return res, espejar, lateral
            if entrada is not None and not _entra(cand, entrada):
                motivo = "la entrada pedida no da al pasillo común"
            elif any(a < b for a, b in zip(esencial(cand), esencial(base))):
                motivo = "con la entrada en la punta %s el plano pierde cocina, dormitorios, estar o baño" % donde
            else:
                out = cand if not ediciones else plano(e_, l_, ediciones, True)
                out["checks"].append({"ok": True, "info": True, "msg": "Acceso a mano: la puerta de entrada en la punta "
                                      "%s (plano %s)" % (donde, "al revés" if e_ else "derecho")})
                out["acceso"] = {"x": _x_entrada(out), "x_medio": px, "posicion": donde, "aplicado": True}
                return out, e_, l_
        res["checks"].append({"ok": True, "info": True, "msg": "Acceso a mano: %s; el plano queda como estaba" % motivo})
        res["acceso"] = {"x": px, "x_medio": px, "posicion": None, "aplicado": False, "motivo": motivo}
        return res, espejar, lateral
    # R5.16b (v2.67): con una segunda fachada (el costado, o el borde del pasillo común al aire: pasante) el esquema en
    # fila (_plan_fila) compite con el plano lado a lado: va si tiene más calidad y no pierde estancias del programa
    # (se comparan sin los cambios a mano; con entrada, solo si su puerta cae ahí)
    fila = _fila_posible(poly, nb, is_facade)
    fijo = None                                        # R5.13: el plano que el acceso a mano eligió en vez del esquema en fila
    if fila is not None:
        def plano_fila(ed, espejo=False, ent=None):
            if fila >= 0 and not espejo:
                return _distribuir(poly, nb, is_facade, equip, accesible, ed, ventanas, fila=fila, entrada=ent)
            bx0, _, bx1, _ = G.bbox(poly)
            m = lambda p: (bx0 + bx1 - p[0], p[1])
            fac = lambda p, q: is_facade(m(p), m(q))
            if hasattr(is_facade, "ventana"):
                fac.ventana = lambda p, q: is_facade.ventana(m(q), m(p))
            ed_ = [(k, dict(e, p=m(e["p"]), a=m(e["a"]) if e.get("a") else None)) for k, e in (ed or [])]
            ent_ = (bx0 + bx1 - ent[1], bx0 + bx1 - ent[0]) if ent is not None else None
            r_ = _distribuir([m(p) for p in poly][::-1], nb, fac, equip, accesible, ed_, ventanas,
                             fila=1 if fila < 0 else fila, entrada=ent_)     # (al revés: la lateral queda en x1)
            return _espejar(r_, m) if r_ is not None else None
        pruebas = [(False, None)]
        if fila == 0 and entrada is not None:          # pasante: la puerta donde llega el pasillo común (junto al paso
            mid = (entrada[0] + entrada[1]) / 2         # o en el medio del tramo) y el paso de cualquiera de los dos
            ents = [entrada] + ([(mid - ENTRY / 2, mid + ENTRY / 2)] if entrada[1] - entrada[0] > ENTRY + 0.1 else [])
            pruebas = [(esp, e) for e in ents for esp in (False, True)]     # lados: el mejor plano que da al pasillo
        cand, modo = None, pruebas[0]
        for esp, e in pruebas:
            r = plano_fila(None, esp, e)
            if r is not None and (entrada is None or _entra(r, entrada)) and (cand is None or r["score"] > cand["score"]):
                cand, modo = r, (esp, e)
        base = elegido if elegido is not None else plano(espejar, lateral, None, hall_x0)
        if cand is not None and cand["score"] > base["score"] and \
                all(a >= b for a, b in zip(esencial(cand), esencial(base))):
            # mejor calidad sin perder cocina, dormitorios, estar ni el baño; el segundo baño o el lavadero pueden no
            # entrar en la columna de servicios (se avisa)
            res = cand if not ediciones else plano_fila(ediciones, *modo)
            if res is not None and acceso is not None:  # R5.13: la entrada en una punta manda sobre el esquema en fila
                fijo, espejar, lateral = con_acceso(res, cand)
                if fijo is res:
                    fijo = None
            if res is not None and fijo is None:
                if vestidor:
                    res["checks"].append({"ok": True, "info": True, "msg": "Vestidor: no se dibuja en el esquema en fila"})
                for i, nombre in ((0, "el segundo baño"), (3, "el lavadero")):
                    if programa(cand)[i] < programa(base)[i]:
                        res["checks"].append({"ok": True, "info": True, "msg": "Esquema en fila: no entra %s" % nombre})
                res["checks"].append({"ok": True, "info": True, "msg": "Segunda fachada: dormitorios en fila sobre " + (
                    "la fachada lateral" if fila else "la fachada del fondo; el estar, sobre el borde del pasillo (pasante)")})
                res["segunda_fachada"] = "fila"
                return res
    if fijo is not None:
        res = fijo
    else:
        res = elegido if elegido is not None and not ediciones else plano(espejar, lateral, ediciones, hall_x0)
        if entrada is not None and not _entra(res, entrada):
            res["checks"].append({"ok": False, "msg": "La puerta de entrada no da al pasillo común"})
            res["score"] = _calidad(res["checks"])
        if acceso is not None:                         # R5.13: la entrada donde la pidió el usuario, si vale
            base = elegido if elegido is not None else (res if not ediciones else plano(espejar, lateral, None, hall_x0))
            res, espejar, lateral = con_acceso(res, base)
    if vestidor and any(r["id"] == "vest" for r in res["rooms"]):
        # R5.10: el vestidor, solo si el plano no empeora (calidad y estancias); si no, sin él y con aviso
        sin = layout_unit(poly, nb, is_facade, vivienda, equip, accesible, ediciones, ventanas, entrada, punta=punta,
                          acceso=acceso, puerta_lateral=puerta_lateral)
        if res["score"] < sin["score"] or any(a < b for a, b in zip(programa(res), programa(sin))):
            antes = {c["msg"] for c in sin["checks"] if not c["ok"]}
            nuevos = [c["msg"].replace("Vestidor: ", "", 1) for c in res["checks"] if not c["ok"] and c["msg"] not in antes]
            sin["checks"].append({"ok": True, "info": True, "msg": "Vestidor: no se agrega porque empeora el plano" + (
                " (%s)" % "; ".join(nuevos) if nuevos else "")})
            return sin
    usa = "dormitorio" if lateral else ("estar" if lado == -1 or espejar else None)
    if usa:
        res["checks"].append({"ok": True, "info": True, "msg": "Fachada lateral: " + (
            "Dormitorio %d al costado, con su ventana a esa fachada" % nb if lateral else
            "el estar en la esquina, con luz por dos fachadas")})
    res["segunda_fachada"] = usa
    return res


def _plano_lateral(poly, nb, is_facade, equip, accesible, ediciones, ventanas, vestidor, al_reves):
    """R11.4: el plano de una vivienda con fachada lateral: el de siempre con el hall en x0 (hall_x0) y la puerta de
    entrada en el borde lateral del hall (_plano(..., puerta_lateral=True)); con al_reves, el plano espejado (la puerta
    en x1). Sin esquema en fila ni dormitorio al costado: la segunda fachada (si la hay, en v0) la usan las ventanas."""
    if not al_reves:
        return _distribuir(poly, nb, is_facade, equip, accesible, ediciones, ventanas, False, True, vestidor,
                           puerta_lateral=True)
    bx0, _, bx1, _ = G.bbox(poly)
    m = lambda p: (bx0 + bx1 - p[0], p[1])
    fac = lambda p, q: is_facade(m(p), m(q)) if is_facade else None
    if hasattr(is_facade, "ventana"):
        fac.ventana = lambda p, q: is_facade.ventana(m(q), m(p))
    ed = [(k, dict(e, p=m(e["p"]), a=m(e["a"]) if e.get("a") else None)) for k, e in (ediciones or [])]
    return _espejar(_distribuir([m(p) for p in poly][::-1], nb, fac if is_facade else None, equip, accesible, ed,
                                ventanas, False, True, vestidor, puerta_lateral=True), m)


def _x_entrada(res):
    """R5.13: la x del medio de la puerta de entrada del plano (sobre el borde v0); None si no la tiene."""
    d = next((d for d in res["doors"] if d.get("entry")), None)
    return (d["p"][0] + d["q"][0]) / 2.0 if d else None


def _entra(res, entrada, tol=0.05):
    """R3.7: la puerta de entrada del plano cae dentro de entrada = (lo, hi) del borde v0 (sin plano, no hay qué
    comprobar)."""
    d = next((d for d in res["doors"] if d.get("entry")), None)
    if d is None:
        return True
    xs = (d["p"][0], d["q"][0])
    return min(xs) >= entrada[0] - tol and max(xs) <= entrada[1] + tol


def _segunda_fachada(poly, nb, is_facade):
    """R5.3: (espejar, lateral, lado) para una vivienda con fachada al fondo y en un solo costado (lado: -1 el de x0,
    1 el de x1; 0 si no hay o están los dos). El plano pone el estar en x0 y la zona de noche en x1: si el frente
    alcanza, el estar va al costado con fachada (espejar si es x1); si no alcanza y hay fondo para un dormitorio entre
    el pasillo común y el interno, la zona de noche va a ese costado (espejar si es x0) y el último dormitorio, ahí."""
    if is_facade is None or nb < 1:
        return False, False, 0
    (x0, v0, x1, v1), annexes = _main_rect(poly)
    (x0, v0, x1, v1), _ = _main_con_luz(poly, (x0, v0, x1, v1), annexes, is_facade)
    if _luz(is_facade, (x0, v1), (x1, v1)) < 0.95:        # el fondo, todo fachada: el plano al revés no deja
        return False, False, 0                             # un dormitorio sin luz
    izq, der = _luz(is_facade, (x0, v0), (x0, v1)) >= 0.75, _luz(is_facade, (x1, v0), (x1, v1)) >= 0.75
    if izq == der:
        return False, False, 0
    lado = -1 if izq else 1
    W = x1 - x0
    corto = W - _frente_noche(W, nb)[1] < LIV_MIN
    entra = _frente_noche(W, nb, True)[0] >= V["dorm_principal"]["min_side"] + \
        V["dorm_secundario"]["min_side"] * (nb - 2) - 1e-6     # el baño y el lavadero los comprueba layout_unit
    lateral = corto and entra and nb >= 2 and (v1 - v0) - HALL - BED_D >= 3.0
    return (lado == -1) if lateral else (lado == 1), lateral, lado


def _luz(is_facade, p, q, paso=0.25):
    """Fracción del segmento p-q que da a la fachada."""
    n = max(1, int(round(((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2) ** 0.5 / paso)))
    pt = lambda k: (p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n)
    return sum(1 for k in range(n) if is_facade(pt(k), pt(k + 1))) / float(n)


def _espejar(res, m):
    """R5.3: devuelve al marco de la vivienda un plano hecho al revés (m: la simetría x -> x0 + x1 - x)."""
    for r in res["rooms"]:
        r["poly"] = [m(p) for p in r["poly"]][::-1]
        if r.get("libre") and r["libre"].get("rect"):  # R5.8a: el rectángulo libre, al revés también
            a, b, c, d_ = r["libre"]["rect"]
            r["libre"]["rect"] = (m((c, b))[0], b, m((a, b))[0], d_)
    for d in res["doors"]:                             # la bisagra sigue en p; una hoja vertical abre hacia el otro x
        d["p"], d["q"] = m(d["p"]), m(d["q"])
        if d["vertical"]:
            d["into"] = -d["into"]
    for q in res["equipamiento"]:
        q["poly"] = [m(p) for p in q["poly"]][::-1]
        q["lines"] = [[m(p) for p in ln] for ln in q["lines"]]
    res["paredes"] = [(m(a), m(b)) for a, b in res["paredes"]]
    for w in res["ventanas"]:                          # la estancia, a la izquierda de p-q
        w["p"], w["q"], w["n"] = m(w["q"]), m(w["p"]), (-w["n"][0], w["n"][1])
    for n in res["graph"]["nodes"]:
        n["pos"] = m(n["pos"])
    res["sin_uso"] = [[m(p) for p in pl][::-1] for pl in res["sin_uso"]]
    return res


def _libres(rooms, R, E, poly, tol=0.02):
    """R5.8a (v2.73): el rectángulo libre de cada estancia: el rectángulo al eje menos T2 por cada lado interior —el que
    no está sobre el contorno de la vivienda (su punto medio queda dentro del polígono, lejos del borde) y no está abierto
    a otra estancia en todo su largo (una conexión "abierto" de E: la cocina con el estar, el hall con la cocina, la boca
    del pasillo interno, el vestidor con su dormitorio)—; los lados sobre el contorno (fachada, patio, medianera, vecina,
    pasillo común, núcleo) ya tienen su muro fuera del polígono y no descuentan nada. Cada estancia recibe r["libre"] =
    {rect, poly (el libre recortado por la vivienda, como su poly), w, d, area} y su "area" pasa a ser la libre (la ficha
    y las comprobaciones la usan). Con TAB = 0 nada cambia."""
    abiertos = {}
    for a, b, t in E:
        if t == "abierto" and a in R and b in R:
            seg = _shared(R[a][1], R[b][1])
            if seg:
                abiertos.setdefault(a, []).append(seg)
                abiertos.setdefault(b, []).append(seg)
    n = len(poly)
    borde = lambda m: min(_dist_seg(m, poly[j], poly[(j + 1) % n]) for j in range(n))
    for r in rooms:
        x0, v0, x1, v1 = r["rect"]
        des = []
        for m, eje, c in (((x0, (v0 + v1) / 2), 0, x0), ((x1, (v0 + v1) / 2), 0, x1),
                          (((x0 + x1) / 2, v0), 1, v0), (((x0 + x1) / 2, v1), 1, v1)):
            interior = T2 > 0 and borde(m) > tol and G.point_in_poly(m, poly)
            if interior:                               # abierto en (casi) todo su largo: sin tabique
                L = (v1 - v0) if eje == 0 else (x1 - x0)
                abierto = sum(_largo(s) for s in abiertos.get(r["id"], ())
                              if abs(s[0][eje] - c) < 1e-6 and abs(s[1][eje] - c) < 1e-6)
                interior = abierto < L - 0.10
            des.append(T2 if interior else 0.0)
        lr = (x0 + des[0], v0 + des[2], x1 - des[1], v1 - des[3])
        if r["id"].startswith("annex"):
            pl = G.clip_rect(poly, lr[0] - 0.01, lr[2] + 0.01, lr[1] - 0.01, lr[3] + 0.01)
        else:
            pl = G.clip_rect(poly, lr[0], lr[2], lr[1], lr[3])
        area = abs(G.area(pl)) if pl else r["area"]
        r["libre"] = {"rect": lr, "poly": pl or r["poly"], "w": lr[2] - lr[0], "d": lr[3] - lr[1], "area": area}
        r["area"] = area


def _programa(res):
    """Estancias del programa de un plano: baños, cocinas, dormitorios, lavaderos y estares."""
    return [sum(1 for r in res["rooms"] if r["kind"] == k or (k == "kitchen" and "Cocina" in r["name"]))
            for k in ("bath", "kitchen", "bedroom", "laundry", "living")]


def _distribuir(poly, nb, is_facade, equip, accesible, ediciones, ventanas, lateral=False, hall_x0=False, vestidor=False,
                fila=None, entrada=None, puerta_lateral=False):
    """El plano de layout_unit (poly antihorario, medidas ya configuradas). R5.11 (revisión): si un muro oblicuo o un
    entrante recorta el rectángulo principal, la banda de servicios va solo si el plano no empeora: si sin ella tiene más
    calidad o más estancias del programa, va el plano sin banda (como en v2.41). Se comparan sin los cambios a mano.
    fila (R5.16b, v2.67): el esquema en fila con esa segunda fachada (None si no entra)."""
    if fila is not None:
        res = _plano(poly, nb, is_facade, equip, accesible, ediciones, ventanas, False, False, False, True, fila, entrada)
        if res is not None:
            res.pop("_banda", None)
        return res
    pl = lambda ed, con: _plano(poly, nb, is_facade, equip, accesible, ed, ventanas, lateral, hall_x0, vestidor, con,
                                puerta_lateral=puerta_lateral)
    res = pl(ediciones, True)
    if not res.pop("_banda"):
        return res
    con = pl(None, True) if ediciones else res
    sin = pl(None, False)
    if sin["score"] > con["score"] or any(a < b for a, b in zip(_programa(con), _programa(sin))):
        res = pl(ediciones, False) if ediciones else sin
    res.pop("_banda", None)
    return res


def _plano(poly, nb, is_facade, equip, accesible, ediciones, ventanas, lateral=False, hall_x0=False, vestidor=False,
           con_banda=True, fila=None, entrada=None, puerta_lateral=False):
    """El plano de _distribuir, con la banda de servicios (R5.11) o sin ella. Trae "_banda": si la usa y un muro oblicuo
    o un entrante recorta el rectángulo principal. fila (R5.16b, v2.67): el esquema en fila con esa segunda fachada
    (_plan_fila) en vez de _plan_rects; None si no entra."""
    (x0, v0, x1, v1), annexes = _main_rect(poly)
    if is_facade is not None:
        (x0, v0, x1, v1), annexes = _main_con_luz(poly, (x0, v0, x1, v1), annexes, is_facade)
    warnings = []
    S_v = ventanas or ST.DEFAULTS["ventanas"]
    prop = S_v.get("proporcion_max", ST.DEFAULTS["ventanas"]["proporcion_max"])     # R10.8: art. 14

    def luz_cocina(rect):
        """R10.9: la cocina rect tiene un tramo de fachada en el que entra su ventana (la misma prueba de _ventanas)."""
        pk = G.clip_rect(poly, rect[0], rect[2], rect[1], rect[3])
        return bool(pk) and any(_entra_ventana(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5, S_v)
                                for a, b, _ in _tramos_fachada(G.ensure_ccw(pk), poly, is_facade, v1))
    acc = [a + TAB for a in equip["bano_accesible"]] if accesible else None    # (R5.8a: al eje, con sus tabiques)
    if fila is None:
        R, E, vacios = _plan_rects(x0, v0, x1, v1, nb, warnings, acc, lateral,
                                   hall_x0, vestidor, lambda r: G.strip_area(poly, r[0], r[2], r[1], r[3]), prop,
                                   lambda r: G.clip_rect(poly, r[0], r[2], r[1], r[3]), S_v, con_banda,
                                   luz_cocina if is_facade is not None else None)
    else:
        rv = _plan_fila(x0, v0, x1, v1, nb, fila, warnings, acc, prop)
        if rv is None:
            return None
        R, E, vacios = rv
    usa_banda = any(b == "laundry" and a in ("kitchen", "hall") for a, b, _ in E) and \
        G.strip_area(poly, x0, x1, v0, v1) < (x1 - x0) * (v1 - v0) - 0.01     # (el de la banda: desde la cocina o el hall)
    vacios = [(G.clip_rect(poly, r[0], r[2], r[1], r[3]), msg) for r, msg in vacios]
    anexados = []

    def anexar():
        """Anexos (bolsillos de la unidad): estudio si tiene fachada (también oblicua, como una ochava); sin ella, depósito
        si no pasa de su máximo y, si pasa, C: queda sin uso, con aviso (v2.33). Una sola vez: después de los tabiques
        movidos o, desde R5.12, antes de la primera estancia editada (un estudio puede pasar a dormitorio)."""
        if anexados:
            return
        anexados.append(True)
        dep = V["deposito"]
        for n_, ap in enumerate(annexes):
            r = G.bbox(ap)
            if is_facade is None:
                fac = abs(r[3] - v1) < 0.05 and (r[3] - r[1]) >= 3.0
            else:
                fac = min(r[2] - r[0], r[3] - r[1]) >= V["estudio"]["min_side"] - 1e-6 and any(
                    ((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2) ** 0.5 >= 1.5
                    for p, q, _ in _tramos_fachada(G.ensure_ccw(ap), poly, is_facade, v1))
            if not fac and abs(G.area(ap)) > dep["max_area"] + 0.5:
                vacios.append((ap, "Sin uso: %.1f m² sin luz natural en un rincón de la vivienda (más que un depósito de "
                                   "%.0f m²)" % (abs(G.area(ap)), dep["max_area"])))
                continue
            aid = "annex%d" % (n_ + 1)
            R[aid] = ("study" if fac else "storage", r, "Estudio" if fac else "Depósito")
            best, bl = None, 0.0
            for i, (k, rr, nm) in R.items():
                if i == aid or k in ("bath", "laundry"):
                    continue
                seg = _shared(rr, r)
                if seg:
                    L = ((seg[1][0] - seg[0][0]) ** 2 + (seg[1][1] - seg[0][1]) ** 2) ** 0.5
                    if L > bl:
                        best, bl = i, L
            if best:
                E.append((best, aid, "puerta"))
    # R5.7 y R5.12: los cambios a mano, en orden: tabiques movidos (pared) y estancias editadas (nombre, tipo, quitar,
    # unir); est: el dormitorio principal (la cama doble y el placard lo siguen; sin cambios, bed1), si el usuario lo fijó,
    # si cambió la cantidad de dormitorios y las estancias con nombre propio. Un cambio que no se puede aplicar se avisa
    hechas, avisos_est = [], []
    est = {"principal": "bed1", "fijado": False, "cambiado": False, "nombres": set()}
    for k, e in (ediciones or []):
        op = e.get("op")
        if op == "pared":
            if e.get("a"):
                Rs = {i: v for i, v in R.items() if not i.startswith("annex")}   # el borde de un anexo no se mueve
                if _mover_pared(Rs, e):
                    R.update(Rs)
                    hechas.append(k)
        elif op in OPS_ESTANCIA:
            anexar()
            hecha, aviso = OPS_ESTANCIA[op](R, E, e, est)
            if hecha:
                hechas.append(k)
            if aviso:
                avisos_est.append(aviso)
    # conexiones abiertas de la zona de día: entre estancias de día que comparten borde
    day = [i for i, (k, r, n) in R.items() if k in DAY]
    have = {(a, b) for a, b, t in E} | {(b, a) for a, b, t in E}
    for i in range(len(day)):
        for j in range(i + 1, len(day)):
            a, b = day[i], day[j]
            if (a, b) in have or (R[a][0] == "hallway" and R[b][0] == "hallway"):
                continue
            seg = _shared(R[a][1], R[b][1])
            if seg and ((seg[1][0] - seg[0][0]) ** 2 + (seg[1][1] - seg[0][1]) ** 2) ** 0.5 >= MIN_SHARE["abierto"]:
                E.append((a, b, "abierto"))
    anexar()                                           # (sin estancias editadas, después de las conexiones: como antes)
    rooms, ids = [], {}
    for i, (kind, rect, name) in R.items():
        p = G.clip_rect(poly, rect[0], rect[2], rect[1], rect[3]) if not i.startswith("annex") else \
            G.clip_rect(poly, rect[0] - 0.01, rect[2] + 0.01, rect[1] - 0.01, rect[3] + 0.01)
        if p and abs(G.area(p)) > 1.0:
            ids[i] = len(rooms)
            rooms.append({"id": i, "name": name, "kind": kind, "poly": p, "area": abs(G.area(p)), "rect": rect})
    _libres(rooms, R, E, poly)                         # R5.8a: el rectángulo libre de cada estancia ("area" pasa a ser la libre)
    libre = {r["id"]: r["libre"]["rect"] for r in rooms}
    sala = lambda r: dict(r, rect=r["libre"]["rect"], poly=r["libre"]["poly"])   # la estancia libre, para el equipamiento
    snap = T2 + 0.01                                   # las puertas (al eje) caen a T2 del borde libre: EQ las lleva a él
    principal = est["principal"]
    if principal in ids:
        rooms[ids[principal]]["principal"] = True        # R5.12: la cama doble y el placard van en él
    nb_real = sum(1 for r in rooms if r["kind"] == "bedroom")      # R5.12: con dormitorios quitados, unidos o nuevos, la
    nb_eff = nb_real if est["cambiado"] else nb                    # vivienda cuenta los reales (sin cambios, los del mix)

    def en_fachada(rect):
        """Tramos de las paredes de la estancia sobre la fachada (con ventana): ahí no van el placard ni el rack de TV."""
        rx0, rv0, rx1, rv1 = rect
        out = []
        for p, q, borde in (((rx0, rv1), (rx1, rv1), abs(rv1 - v1) < 0.05), ((rx0, rv0), (rx0, rv1), abs(rx0 - x0) < 0.05),
                            ((rx1, rv0), (rx1, rv1), abs(rx1 - x1) < 0.05),
                            ((rx0, rv0), (rx1, rv0), abs(rv0 - v0) < 0.05 and is_facade is not None)):   # (v2.67: pasante)
            if not borde or (is_facade is None and p[1] != q[1]):
                continue
            if is_facade is None:
                out.append((p, q))
                continue
            n = max(1, int(round(((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2) ** 0.5)))    # de a 1 m
            pt = lambda k: (p[0] + (q[0] - p[0]) * k / n, p[1] + (q[1] - p[1]) * k / n)
            tramos, tramo = [], None
            for k in range(n):
                if is_facade(pt(k), pt(k + 1)):
                    tramo = (tramo[0] if tramo else pt(k), pt(k + 1))
                elif tramo:
                    tramos.append(tramo)
                    tramo = None
            if tramo:
                tramos.append(tramo)
            corto = lambda t: p[1] != q[1] and abs(t[1][1] - t[0][1]) < 1.0    # junto a la esquina de la fachada: no es ventana
            out += [t for t in tramos if not corto(t)]
        return out
    fachadas = {r["id"]: en_fachada(libre[r["id"]]) for r in rooms if r["kind"] in ("bedroom", "living", "dining")}
    # R10.8: las cocinas integradas a la zona de día (abiertas a ella) sin ventana propia (Trazo todavía no les pone):
    # norma nacional, art. 27. De un «Hall / Cocina» cuenta solo la parte de la cocina (R5.8a: superficies libres)
    abiertas = {x for a, b, t in E if t == "abierto" for x in (a, b)}
    integradas = {r["id"]: r["area"] if r["kind"] == "kitchen" else
                  max(0.0, r["area"] - (HALL_W - T2) * r["libre"]["d"])   # (el hall, HALL_W al eje con su medio tabique:
                  for r in rooms if (r["kind"] == "kitchen" or "Cocina" in r["name"]) and r["id"] in abiertas}   # lo que midió el plano)
    vent, sin_luz = _ventanas(rooms, poly, is_facade, v1, S_v, integradas)   # R5.5 (R10.9: la cocina con fachada,
    con_ventana = {w["room"] for w in vent}                                   # con la suya; las demás, con extractor)
    integradas = {i: a for i, a in integradas.items() if i not in con_ventana}
    for r in rooms:
        if r["kind"] == "kitchen" or "Cocina" in r["name"]:
            r["ventilacion"] = "ventana" if r["id"] in con_ventana else "extractor"

    def abiertos(i):
        """Los bordes de la estancia i abiertos a otra (las aberturas de la zona de día), como los usa EQ."""
        out = []
        for a_, b_, t_ in E:
            if t_ == "abierto" and i in (a_, b_) and a_ in ids and b_ in ids:
                sg = _shared(rooms[ids[a_]]["rect"], rooms[ids[b_]]["rect"])
                if sg:
                    out.append((sg[0], sg[1], b_ if a_ == i else a_))
        return {i: out}
    # conexiones y puertas
    doors, edges = [], []
    for a, b, typ in E:
        if a not in ids or b not in ids or typ == "muro":      # (muro, v2.67: dos estancias de día sin abertura)
            continue
        seg = _shared(rooms[ids[a]]["rect"], rooms[ids[b]]["rect"])
        L = 0.0 if not seg else ((seg[1][0] - seg[0][0]) ** 2 + (seg[1][1] - seg[0][1]) ** 2) ** 0.5
        rb = rooms[ids[b]]
        ancho = DOOR_ACC if accesible and (rb["kind"] == "bedroom" or b == "bath1") else DOOR
        if typ == "puerta":                            # R5.8a: la puerta entra en el tramo libre del borde (sin los
            L -= TAB                                   # medios tabiques perpendiculares de sus dos puntas)
        ok = L >= (ancho + 0.1 if typ == "puerta" else MIN_SHARE[typ]) - 1e-6     # un borde de 0,8999… m es de 0,90 m
        edges.append({"a": a, "b": b, "type": typ, "ok": ok})
        if ok and typ == "puerta":
            m = ((seg[0][0] + seg[1][0]) / 2, (seg[0][1] + seg[1][1]) / 2)
            vertical = abs(seg[0][0] - seg[1][0]) < 1e-6
            d = ancho / 2
            hoja = lambda m: ((m[0], m[1] - d), (m[0], m[1] + d)) if vertical else ((m[0] - d, m[1]), (m[0] + d, m[1]))
            desde, hacia = (b, a) if accesible and b == "bath1" else (a, b)     # el baño accesible abre hacia afuera
            if rb["kind"] in ("bath", "laundry", "bedroom", "kitchen") and L > ancho + 0.3:   # la puerta donde entran artefactos
                # y muebles (v2.67: también la cocina cerrada de la pasante en fila, con su puerta desde el paso)
                k = 1 if vertical else 0                     # la puerta se corre a lo largo del borde
                lo, hi = sorted((seg[0][k], seg[1][k]))
                lo, hi = lo + T2, hi - T2                    # (R5.8a: el tramo libre)
                notas, cands = {}, [m[k], lo + d + 0.1, hi - d - 0.1]      # al medio o junto a una esquina
                ent = next((x for x in doors if x["b"] == a), None) if R[a][0] == "vestidor" else None
                if ent:                                      # R5.10: el baño en suite, junto a la entrada del vestidor (sus
                    em = ((ent["p"][0] + ent["q"][0]) / 2, (ent["p"][1] + ent["q"][1]) / 2)     # paredes, para los estantes)
                    cands.sort(key=lambda c: (m[0] - em[0]) ** 2 + (c - em[1]) ** 2 if vertical else
                               (c - em[0]) ** 2 + (m[1] - em[1]) ** 2)
                for c in cands:
                    pq = hoja((m[0], c) if vertical else (c, m[1]))
                    pu = [{"p": pq[0], "q": pq[1], "a": desde, "b": hacia, "ancho": ancho}]
                    _, falta, info = EQ.resolver(sala(rb), pu, {}, equip, fachadas.get(b, ()), nb, acc=accesible, snap=snap)
                    notas[c] = 2 * len(falta) + len(info)    # un toilette (sin ducha) es peor que el baño completo
                    if R[a][0] == "kitchen":                 # R5.11: el lavadero desde la cocina: donde entra también
                        notas[c] += 2 * len(EQ.resolver(sala(rooms[ids[a]]), pu, abiertos(a), equip, (), nb,
                                                        snap=snap)[1])                                  # su mesada
                    if not notas[c]:
                        break
                c = min(notas, key=lambda c: (notas[c], c != cands[0]))
                m = (m[0], c) if vertical else (c, m[1])
            p, q = hoja(m)
            # la hoja abre hacia la estancia «hacia»
            c = G.centroid(rooms[ids[hacia]]["poly"])
            sw = ((c[0] - m[0]) > 0) if vertical else ((c[1] - m[1]) > 0)
            doors.append({"p": p, "q": q, "into": 1 if sw else -1, "vertical": vertical, "a": desde, "b": hacia,
                          "ancho": ancho})
    # puerta de entrada desde el pasillo común, en el hall (R5.16b, v2.67: en una pasante en fila no hay hall y la puerta
    # da al estar, que está sobre ese borde)
    entrada_id = "hall" if "hall" in ids else next((i for i in ("living", "hall") if fila == 0 and i in ids and
                                                     any(abs(p[1] - v0) < 1e-6 for p in rooms[ids[i]]["poly"])), None)
    if entrada_id is not None and puerta_lateral:      # R11.4: en el borde lateral del hall (x0), que da al pasillo común
        r = rooms[ids[entrada_id]]["rect"]
        borde = [p[1] for p in rooms[ids[entrada_id]]["poly"] if abs(p[0] - r[0]) < 1e-6]
        lo, hi = (min(borde), max(borde)) if borde else (r[1], r[3])
        if TAB > 0:                                    # R5.8a: dentro del tramo libre del hall (sin el medio tabique)
            lo, hi = max(lo, libre[entrada_id][1]), min(hi, libre[entrada_id][3])
        mv = (lo + hi) / 2 if hi - lo < ENTRY else max(lo + ENTRY / 2, min(hi - ENTRY / 2, (lo + hi) / 2))
        doors.append({"p": (r[0], mv - ENTRY / 2), "q": (r[0], mv + ENTRY / 2), "into": 1, "vertical": True,
                      "a": "exterior", "b": entrada_id, "entry": True, "ancho": ENTRY})
    elif entrada_id is not None:
        r = rooms[ids[entrada_id]]["rect"]
        mx = r[0] + min(HALL_W, r[2] - r[0]) / 2 if hall_x0 else (r[0] + r[2]) / 2     # R3.7: junto a x0
        if entrada_id == "living":                     # (pasante en fila: junto al paso, en x1, o donde llega el
            mx = r[2] - ENTRY / 2 - 0.1                # pasillo común si lo dice entrada)
            if entrada is not None and min(entrada[1], r[2]) - max(entrada[0], r[0]) >= ENTRY - 1e-6:
                mx = max(max(entrada[0], r[0]) + ENTRY / 2, min(min(entrada[1], r[2]) - ENTRY / 2, mx))
        borde = [p[0] for p in rooms[ids[entrada_id]]["poly"] if abs(p[1] - v0) < 1e-6]     # R10.8: dentro de su borde
        if borde:                                                                     # real (un muro oblicuo lo acorta)
            lo, hi = min(borde), max(borde)
            if TAB > 0:                                # R5.8a: dentro del tramo libre del hall (sin el medio tabique)
                lo, hi = max(lo, libre[entrada_id][0]), min(hi, libre[entrada_id][2])
            mx = (lo + hi) / 2 if hi - lo < ENTRY else max(lo + ENTRY / 2, min(hi - ENTRY / 2, mx))
        doors.append({"p": (mx - ENTRY / 2, v0), "q": (mx + ENTRY / 2, v0), "into": 1, "vertical": False,
                      "a": "exterior", "b": entrada_id, "entry": True, "ancho": ENTRY})
    for k, e in (ediciones or []):                     # R5.7: puertas corridas, de otro ancho o que abren al revés
        if e.get("op") == "puerta" and _editar_puerta(doors, lambda i: rooms[ids[i]]["rect"], e, v0):
            hechas.append(k)
    # comprobaciones
    checks = []
    adj = {i: set() for i in ids}
    for e in edges:
        if e["ok"]:
            adj[e["a"]].add(e["b"])
            adj[e["b"]].add(e["a"])
    start = entrada_id if entrada_id is not None else next(iter(ids), None)
    v1 = max(v1, G.bbox(poly)[3])
    seen, stack = set(), [start] if start else []
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        stack.extend(adj[n] - seen)
    for e in edges:
        if not e["ok"]:
            checks.append({"ok": False, "msg": "%s no conecta con %s (%s)" % (
                rooms[ids[e["a"]]]["name"], rooms[ids[e["b"]]]["name"], e["type"])})
    unreached = [rooms[ids[i]]["name"] for i in ids if i not in seen]
    if entrada_id is None:                             # R5.11: sin hall (un muro oblicuo se lo comió) no hay puerta de
        checks.append({"ok": False, "msg": "Sin puerta de entrada: el hall no entra junto al pasillo común"})   # entrada
    checks.append({"ok": not unreached, "msg": "Todas las estancias se alcanzan desde la entrada" if not unreached
                   else "Sin acceso desde la entrada: " + ", ".join(unreached)})
    below, chicas, oscuras = [], set(), set()          # chicas: ya avisadas por su medida (no se suma lo que no entra)
    con_v = {w["room"] for w in vent} | {c["room"] for c in sin_luz}     # con fachada (el comedor interior, sin ella)
    for r in rooms:
        if r["kind"] in ("bedroom", "living", "study"):
            rx0, rv0, rx1, rv1 = r["rect"]
            if is_facade and r["id"].startswith("annex"):     # un anexo con un muro oblicuo (una ochava): por su contorno
                fac = bool(_tramos_fachada(r["poly"], poly, is_facade, v1))
            elif is_facade:
                fac = any(is_facade(p, q) for p, q in (((rx0, rv1), (rx1, rv1)), ((rx0, rv0), (rx0, rv1)),
                                                       ((rx1, rv0), (rx1, rv1)), ((rx0, rv0), (rx1, rv0))) if
                          ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5 >= 1.0)     # (v2.67: también v0, pasante)
            else:
                fac = abs(rv1 - v1) < 0.05
            if not fac:
                checks.append({"ok": False, "msg": "%s sin fachada (sin luz natural)" % r["name"]})
                oscuras.add(r["id"])
        w = min(r["libre"]["w"], r["libre"]["d"])        # R5.8a: los lados y las superficies, libres, contra la norma
        sd = _std_for(r, nb, integradas, principal)
        if r["id"] in integradas and integradas[r["id"]] > _ci()["max_area"] + 1e-6:     # R10.8: art. 27
            checks.append({"ok": False, "msg": "Cocina integrada sin ventana de %.1f m²%s: la norma nacional admite de %g a "
                                               "%g m² (art. 27); más grande, con ventana propia (art. 24)" % (
                                                   integradas[r["id"]], "" if r["kind"] == "kitchen" else " (en el hall)",
                                                   _ci()["min_area"], _ci()["max_area"])})
        if sd:
            ms = sd.get("min_side")
            if ms and w + 1e-6 < ms:
                checks.append({"ok": False, "msg": "%s: lado %.2f m < mínimo %.2f m" % (r["name"], w, ms)})
                chicas.add(r["id"])
            ma = sd.get("min_area")
            if ma and r["area"] + 1e-6 < ma:
                checks.append({"ok": False, "msg": "%s: %.1f m² < mínimo %.1f m²" % (r["name"], r["area"], ma)})
                chicas.add(r["id"])
            ta = sd.get("typ_area")
            if r["kind"] == "living":
                ta = V["estar_por_dorms"][min(nb_eff, len(V["estar_por_dorms"]) - 1)]
            if ta and r["area"] < 0.9 * ta and not (ma and r["area"] < ma):
                below.append("%s %.1f de %.0f m²" % (r["name"], r["area"], ta))
        elif w + 1e-6 < MIN_W.get(r["kind"], 0):
            checks.append({"ok": False, "msg": "%s: ancho %.2f m < mínimo %.2f m" % (r["name"], w, MIN_W[r["kind"]])})
            chicas.add(r["id"])
        if r["kind"] in ("bedroom", "living", "dining", "study") and r["id"] not in chicas and r["id"] not in oscuras \
                and (r["kind"] != "dining" or r["id"] in con_v):   # el comedor interior, con el estar (abajo)
            corto, largo = sorted((r["libre"]["w"], r["libre"]["d"]))
            if largo > prop * corto + 1e-6:            # R10.8: art. 14 (si no se avisó ya por su medida o su fachada)
                checks.append({"ok": False, "msg": "%s: %.2f m de profundidad, más de %g veces su lado menor (%.2f m) "
                                                   "(norma nacional, art. 14)" % (r["name"], largo, prop, corto)})
    for d in [r for r in rooms if r["kind"] == "dining" and r["id"] not in con_v and r["id"] not in chicas]:
        est = next((r for r in rooms if r["kind"] == "living" and r["id"] not in chicas and r["id"] not in oscuras and
                    _shared(r["rect"], d["rect"])), None)
        if est:                                        # R10.8: el comedor interior, con el estar que lo ilumina (art. 14)
            le, ld = libre[est["id"]], libre[d["id"]]  # (R5.8a: con las medidas libres)
            prof = max(le[3], ld[3]) - min(le[1], ld[1])
            ancho = min(le[2] - le[0], ld[2] - ld[0])
            if prof > prop * ancho + 1e-6:
                checks.append({"ok": False, "msg": "%s y comedor: %.2f m de profundidad desde la ventana, más de %g veces "
                                                   "su ancho (%.2f m) (norma nacional, art. 14)" % (
                                                       est["name"], prof, prop, ancho)})
    aberturas = {}                                     # bordes abiertos entre estancias de día: ahí no va un artefacto
    for e in edges:
        if e["type"] == "abierto" and e["ok"]:
            seg = _shared(rooms[ids[e["a"]]]["rect"], rooms[ids[e["b"]]]["rect"])
            for i, otra in ((e["a"], e["b"]), (e["b"], e["a"])):
                aberturas.setdefault(i, []).append((seg[0], seg[1], otra))
    checks += [{"ok": False, "msg": c["msg"]} for c in sin_luz           # R5.5: vano mínimo (no en una estancia ya
               if c["room"] not in oscuras and c["room"] not in chicas]       # avisada por su fachada o su medida)
    equipo, faltan = EQ.equipar([sala(r) for r in rooms], doors, aberturas, equip, nb_eff, fachadas, chicas, accesible,
                                ("bed1",) if "vest" in ids else (), principal, snap=snap)   # F5: artefactos y muebles, en
    checks += faltan                                   # el rectángulo libre (R5.8a); R5.10: con vestidor, el principal sin
                                                       # placard; R5.12: la cama doble en principal
    for a in avisos_est:                               # R5.12: lo que no se pudo aplicar (layout lo copia a los avisos)
        checks.append({"ok": True, "info": True, "msg": "Estancia a mano: " + a})
    for w in warnings:
        if isinstance(w, tuple):
            checks.append({"ok": True, "info": True, "msg": w[1]})
        else:
            checks.append({"ok": False, "msg": w})
    lleno = lambda p: bool(p) and abs(G.area(p)) >= 0.3
    sin_uso = [p for p, msg in vacios if lleno(p)]     # C (v2.33): lo que queda sin uso, con aviso: uno por grupo (un trozo
    grupos = []                                        # con aviso y los que lo siguen con ""), aunque su primer trozo
    for p, msg in vacios:                              # quede vacío (R5.11: si no, se dibujaba sin aviso)
        if msg or not grupos:
            grupos.append([msg, False])
        grupos[-1][1] = grupos[-1][1] or lleno(p)
    checks += [{"ok": False, "msg": msg} for msg, hay in grupos if msg and hay]
    checks += _faltan(rooms)
    if all(c["ok"] for c in checks):
        checks.append({"ok": True, "msg": TODO_BIEN})
    if below:
        checks.append({"ok": True, "info": True, "msg": "Por debajo de la medida típica: " + "; ".join(below)})
    rng = V["rango_vivienda"][min(nb_eff, len(V["rango_vivienda"]) - 1)]
    tot = abs(G.area(poly))
    if tot < rng[0] or tot > rng[1]:
        checks.append({"ok": True, "info": True, "msg": "Superficie %.0f m² fuera del rango de referencia ANV para %d dorm. (%d-%d m²)" % (tot, nb_eff, rng[0], rng[1])})
    nodes = [{"id": r["id"], "name": r["name"], "kind": r["kind"], "pos": G.centroid(r["poly"])} for r in rooms]
    muros = [((c, lo), (c, hi)) if eje == 0 else ((lo, c), (hi, c))     # tabiques interiores (se arrastran en la web);
             for eje, c, lo, hi in paredes({r["id"]: (r["kind"], r["rect"], r["name"]) for r in rooms   # el borde de
                                            if not r["id"].startswith("annex")})]                     # un anexo no se mueve
    score = _calidad(checks)
    for r in rooms:
        del r["rect"]
        r["libre"].pop("poly", None)                   # R5.8a: queda {rect, w, d, area} (units quita rect)
    return {"rooms": rooms, "doors": doors, "graph": {"nodes": nodes, "edges": edges}, "equipamiento": equipo,
            "checks": checks, "score": score, "bedrooms": nb_eff, "facade": round(x1 - x0, 2),
            "facade_min": round(facade_min(nb), 2), "accesible": bool(accesible), "paredes": muros,
            "ediciones": sorted(hechas), "ventanas": vent, "sin_uso": sin_uso, "_banda": usa_banda,
            "avisos_estancias": avisos_est}
