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
V = ST.DEFAULTS["vivienda"]


def _cama_placard(eq):
    """Dormitorio principal con su cama doble y el placard (criterio del usuario, v2.29): (ancho con el placard al costado
    de la cama, fondo con el placard al pie). Con las medidas por defecto, 3,20 y 3,10 m."""
    return (2 * eq["paso_cama"] + eq["cama_doble"][0] + eq["placard_fondo"],
            eq["cama_doble"][1] + eq["paso_cama"] + eq["placard_fondo"])


CAMA_PLACARD = _cama_placard(ST.DEFAULTS["equipamiento"])
CAMA_FONDO = 2.5      # R5.10: el principal sin placard (con vestidor), la cama doble y su paso al pie (ídem)


def configure(vivienda, equip=None, accesible=False):
    """Ajusta las medidas de proyecto a partir de la tabla de estándares (standards.py / web). accesible: el baño
    principal toma el ancho del baño accesible."""
    global HALL, LIV_MIN, BED_MAIN, BED_W, BATH_W1, BATH_W2, HALL_W, KITCH_D, LAV_W, BATH2_D, V, DOOR, ENTRY, DOOR_ACC
    global CAMA_PLACARD, CAMA_FONDO, BATH_MIN, BATH_MIN_D, BATH_FULL, FR_MIN, FR_MAX, KITCH_LINE, KITCH_L, KITCH_MESADA
    global KITCH_FRENTE
    V = vivienda
    eq = equip or ST.DEFAULTS["equipamiento"]
    CAMA_PLACARD = _cama_placard(eq)
    CAMA_FONDO = eq["cama_doble"][1] + eq["paso_cama"]
    DOOR, ENTRY, DOOR_ACC = eq["puerta_interior"], eq["puerta_entrada"], eq["puerta_accesible"]
    MIN_SHARE["puerta"] = DOOR + 0.1
    HALL = max(V["pasillo"]["min_side"], V["pasillo"]["typ_side"])
    BED_MAIN = max(V["dorm_principal"]["min_side"], V["dorm_principal"]["typ"][0])
    BED_W = max(V["dorm_secundario"]["min_side"], V["dorm_secundario"]["typ"][0])
    LIV_MIN = max(V["estar_comedor"]["min_side"], 0.95 * V["estar_comedor"]["typ"][0])
    inodoro = eq["inodoro"][1] + eq["paso_bano"]           # un baño angosto: el inodoro contra la pared larga y su paso
    BATH_W1 = max(V["bano"]["min_side"], V["bano"]["typ"][0], inodoro, eq["bano_accesible"][0] if accesible else 0.0)
    BATH_W2 = max(V["bano_aux"]["min_side"], V["bano_aux"]["typ"][0], inodoro)
    LAV_W = max(V["lavadero"]["min_side"], eq["lavarropas"][1] + eq["paso_lavadero"])
    BATH2_D = eq["inodoro"][1] + eq["paso_bano"] + eq["lavatorio"][0]   # fondo mínimo de un segundo baño (al menos toilette)
    HALL_W = max(V["hall"]["min_side"], V["hall"]["typ"][0])
    KITCH_D = V["cocina"]["typ"][1]
    BATH_MIN = max(V["bano"]["min_side"], inodoro)
    BATH_MIN_D = max(V["bano"]["min_side"], eq["ducha"][1] + eq["paso_bano"])
    BATH_FULL = (eq["ducha"][0] + eq["inodoro"][0], eq["ducha"][1] + eq["inodoro"][0] + eq["lavatorio"][0])
    FR_MIN, FR_MAX = V["franja_servicios"]["min_side"], V["franja_servicios"]["max_side"]
    KITCH_LINE = eq["heladera"][0] + eq["bacha_cocina"] + eq["mesada_trabajo"] + eq["cocina_horno"]
    KITCH_L = eq["mesada_fondo"] + eq["paso_cocina"] + eq["heladera"][1]
    KITCH_MESADA = eq["bacha_cocina"] + eq["mesada_trabajo"] + eq["cocina_horno"]
    KITCH_FRENTE = eq["mesada_fondo"] + eq["paso_cocina"]
MIN_SHARE = {"puerta": DOOR + 0.1, "abierto": 0.85}
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


def facade_min(nb):
    """Frente mínimo de fachada para estar + dormitorios con ventana."""
    return 4.0 if nb == 0 else LIV_MIN + BED_MAIN + BED_W * (nb - 1)


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


def _mover_pared(R, e, minimo=0.6):
    """R5.7: mueve el tabique que pasa por e["p"] hasta e["a"] (marco de la vivienda): corre el lado de todas las
    estancias que se apoyan en él; cada una conserva al menos `minimo`. Devuelve si se aplicó."""
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
        r = rect(d["b"])
        seg = ((r[0], v0), (r[2], v0))
    else:
        seg = _shared(rect(d["a"]), rect(d["b"]))
    if not seg:
        return False
    k = 1 if d["vertical"] else 0
    lo, hi = sorted((seg[0][k], seg[1][k]))
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


def _ventanas(rooms, borde, is_facade, v1, S, cocinas=0.0):
    """R5.5: una ventana por estancia habitable, centrada en su tramo de fachada (primero el del fondo, después el más
    largo), del ancho típico o del que pide el vano mínimo (S["iluminacion"] de su superficie), sin pasar de la mocheta;
    si no alcanza, otra en el tramo siguiente. R5.3: en una esquina, también una (típica) en la otra fachada. El comedor
    sin fachada se ilumina por el estar: su superficie se suma a la del estar. R10.8 (norma nacional, art. 27): cocinas,
    la superficie de las cocinas integradas sin ventana, también se suma a la del estar, y su vano no baja de
    cocina_integrada["vano_min"]. Devuelve (ventanas en el marco de la vivienda, comprobaciones con la estancia en
    "room")."""
    largo = lambda t: ((t[1][0] - t[0][0]) ** 2 + (t[1][1] - t[0][1]) ** 2) ** 0.5
    habit = [r for r in rooms if r["kind"] in ("bedroom", "living", "dining", "study")]
    tramos = {r["id"]: sorted(_tramos_fachada(r["poly"], borde, is_facade, v1),     # primero la fachada del fondo
                              key=lambda t: (t[2][1] < 0.7, -largo(t))) for r in habit}
    comedor = [r for r in habit if r["kind"] == "dining" and not tramos[r["id"]]]
    out, checks = [], []
    for r in habit:
        if r in comedor:                               # el comedor interior se ilumina por el estar
            continue
        estar = r["kind"] == "living"
        area = r["area"] + (sum(c["area"] for c in comedor) + cocinas if estar else 0.0)
        req = S["iluminacion"] * area
        if estar and cocinas:                          # R10.8: el vano del estar con la cocina integrada (art. 27)
            req = max(req, _ci()["vano_min"])
        tip = S["ancho_estar"] if r["kind"] in ("living", "dining") else S["ancho_dormitorio"]
        hecho, n_, usadas = 0.0, 0, []
        for a, b, n in tramos[r["id"]]:
            L = largo((a, b))
            if L - 2 * S["mocheta"] < 0.5 * S["ancho_dormitorio"]:
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
            de = [] if not estar else ["el estar"] + (["el comedor"] if comedor else []) + (["la cocina"] if cocinas else [])
            de = " de " + ", ".join(de[:-1]) + " y " + de[-1] if len(de) > 1 else ""
            checks.append({"ok": False, "room": r["id"], "msg": "%s: ventana%s de %.2f m² < %.2f m² (%.0f %% de la "
                           "superficie%s)" % (r["name"], "s" if n_ > 1 else "", hecho, req, 100 * S["iluminacion"],
                                              de.replace(" de el ", " del ", 1) + (
                                                  ", %g m² como mínimo: norma nacional, art. 27" % _ci()["vano_min"]
                                                  if estar and cocinas else ""))})
    return out, checks


def _frente_noche(W, nb, lateral=False):
    """Frente de la zona de noche y el que pide: los dormitorios al fondo (R5.3, lateral: menos el último, que va al
    costado). Si el frente no alcanza para el estar, se ajusta."""
    need = BED_MAIN + BED_W * (nb - 2 if lateral else nb - 1)
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
    return max(minimo, sd["typ_area"] / d)


def _tope(clave, d):
    """Ancho máximo de una estancia de la franja de fondo d: hasta ahí la agranda lo que sobra (B, v2.33)."""
    return {"bath1": V["bano"], "suite": V["bano"], "bath2": V["bano_aux"], "laundry": V["lavadero"],
            "storage": V["deposito"]}[clave]["max_area"] / d


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
    mw = [max(sp["min_side"], sp["min_area"] / max(bedD, 0.1) + 0.02) for sp in specs]
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
    return [(linea, KITCH_LINE), (max(linea, KITCH_L), KITCH_MESADA)] + (
        [(max(linea, KITCH_MESADA), KITCH_L), (max(linea, KITCH_LINE), max(KITCH_FRENTE, _ci()["min_side"]))]
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


def _cocina_integrada(w, kd, kd_min=0.0, real=None, angostar=True, costado=True):
    """R10.8 (norma nacional, art. 27; criterio del usuario: Trazo la dibuja así): (ancho, fondo) de la cocina integrada
    sin ventana de ancho w y fondo kd, con cocina_integrada["max_area"] como máximo. Primero pierde fondo (lo gana el
    estar), hasta el que pide su mesada (_fondo_cocina) y no menos de kd_min; si aún pasa, se angosta, con el fondo que
    pida su nuevo ancho, no menos de kd_min y sin pasar de kd (lo que deja va al hall): la más ancha que entre. Si ningún
    acomodo de la mesada entra en el tope y angostar, se angosta con el fondo que ya tiene (sin lado menor que el mínimo);
    si ni así entra (medidas cambiadas), la más chica: la comprobación lo avisa. Una cocina que ya entra no cambia.
    real(ancho, fondo): su superficie dentro de la vivienda, desde su borde fijo (un muro oblicuo puede cortarla).
    costado: la pared del costado es maciza (ver _modos_cocina)."""
    tope = _ci()["max_area"]
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
        mejor = min(mejor, clave(min(w, max(_ci()["min_side"], _hasta(lambda t: real(t, f), 0.0, w, tope))), f))
    return mejor[2], mejor[3]


def _plan_rects(x0, v0, x1, v1, nb, warnings, acc=None, lateral=False, hall_x0=False, vestidor=False, area_de=None,
                prop=None):
    """Rectángulos de estancias, conexiones con puerta (las abiertas de la zona de día se deducen después) y lo que queda
    sin uso [(rect, aviso)]. acc: frente y fondo del baño de una vivienda accesible (None si no lo es). lateral (R5.3): el
    costado x1 es fachada y el frente no alcanza: el último dormitorio va a ese costado, entre el pasillo común y el
    pasillo interno. hall_x0 (R3.7): el hall, y con él la entrada, en el extremo x0 (el pasillo común solo llega ahí);
    la cocina queda entre el hall y la zona de noche. vestidor (R5.10): el dormitorio principal lleva vestidor (ver
    _vestidor). area_de(rect): superficie del rectángulo dentro de la vivienda (R10.8: la cocina, de 5 m² como máximo).
    prop (R10.8, art. 14): el estar, con el comedor interior, de hasta prop veces su ancho (ventanas["proporcion_max"]):
    el fondo que pierde la cocina no lo lleva más allá.
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

    prop = prop or ST.DEFAULTS["ventanas"]["proporcion_max"]
    tope = _ci()["max_area"]

    def cocina(wk, kd, fija, pisos, costado=True):
        """R10.8: la cocina con 5 m² como máximo (_cocina_integrada), probando los fondos mínimos de pisos de a uno, del
        más exigente al menos: el primero con el que su mesada entra en el tope; si con ninguno, el último (y se angosta
        con el fondo que tenga). fija(ancho, fondo): su superficie dentro de la vivienda."""
        pisos = [max(0.0, min(kd, p_)) for p_ in pisos]
        for p_ in pisos[:-1]:
            w_, f_ = _cocina_integrada(wk, kd, p_, fija, False, costado)
            if fija(w_, f_) <= tope + 1e-6:
                return w_, f_
        return _cocina_integrada(wk, kd, pisos[-1], fija, True, costado)

    if nb == 0:     # monoambiente
        kd = min(2.4, D * 0.4)
        bw = min(2.0, W * 0.35)
        hw = min(1.4, max(1.1, W * 0.2))               # v2.41: el hall, con su lado mínimo si la mesada sigue entrando
        hw = max(hw, min(HALL_W, V["hall"]["min_side"], W - bw - KITCH_FRENTE))
        if acc and W - acc[0] - hw >= 1.6:             # baño accesible, si la cocina sigue entrando
            bw, kd = acc[0], max(kd, min(acc[1], D - 3.5))
        # R10.8: la cocina integrada, de 5 m² como máximo (art. 27): la franja de la entrada comparte el fondo con el baño:
        # primero se angosta y el hall se agranda; si no entra, la franja pierde fondo, sin que el baño baje de su mínimo
        # (si un muro oblicuo lo corta o es el accesible, no lo pierde) y, si se puede, sin que el estar-dormitorio pase de
        # prop veces su ancho (art. 14)
        kb = x1 - bw if hall_x0 else x0
        fb = kd if (acc and bw == acc[0]) or real((kb, v0, kb + bw, v0 + kd)) < bw * kd - 1e-6 else \
            max(BATH_MIN_D, V["bano"]["min_area"] / max(bw, 0.1))
        fija = (lambda a, b: real((x1 - bw - a, v0, x1 - bw, v0 + b))) if hall_x0 else \
            (lambda a, b: real((x0 + bw, v0, x0 + bw + a, v0 + b)))
        wk, kd = cocina(W - bw - hw, kd, fija, [kd, max(fb, D - prop * W), fb])
        if hall_x0:                                    # R3.7: la entrada en x0, el baño en el otro extremo
            add("hall", "hall", (x0, v0, x1 - bw - wk, v0 + kd))
            add("kitchen", "kitchen", (x1 - bw - wk, v0, x1 - bw, v0 + kd))
            add("bath1", "bath", (x1 - bw, v0, x1, v0 + kd))
        else:
            add("bath1", "bath", (x0, v0, x0 + bw, v0 + kd))
            add("kitchen", "kitchen", (x0 + bw, v0, x0 + bw + wk, v0 + kd))
            add("hall", "hall", (x0 + bw + wk, v0, x1, v0 + kd))
        add("living", "living", (x0, v0 + kd, x1, v1), "Estar-Dormitorio")
        E.append(("living", "bath1", "puerta"))
        if vestidor:
            warnings.append(("info", "Vestidor: un monoambiente no lo lleva (no tiene dormitorio)"))
        return R, E, vacios

    # ---- reparto del frente entre día y noche
    nf = nb - 1 if lateral else nb                     # dormitorios al fondo (R5.3: el último, al costado)
    ws = BED_W if lateral else 0.0                     # frente del dormitorio lateral
    Wn, need = _frente_noche(W, nb, lateral)
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
    suite = False

    if deep:
        # zona de noche (de fachada hacia el pasillo común): dormitorios | pasillo | franja de servicios | (sobrante)
        hi = min(FR_MAX, D - HALL - BED_D)
        dep = V["deposito"]
        angosta = xs - x0 - hw < KITCH_LINE            # la cocina va en L: la franja no la deja sin su fondo
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
            if con_dep and dep["max_area"] > 0 and libre >= dep["min_side"] - 1e-6 and libre * d >= dep["min_area"] - 1e-6:
                claves, anchos = claves + ["storage"], anchos + [min(libre, dep["max_area"] / d)]
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
        widths = _anchos_dormitorios(Wn, nf, bedD)
        claves, anchos, sobra = franja(claves, xb - xs, d, e == 0.0)
        if not lateral and nb >= 2 and (sobra >= 1.0 - 1e-6 or vestidor):
            # A: el principal, al final del pasillo, en suite (su baño en la franja); el pasillo termina en su puerta y la
            # franja de los demás ya no lleva el segundo baño: se rehace con su fondo (R5.10: con vestidor, la suite
            # aunque no sobre franja, si los dormitorios no pierden fondo: el vestidor va entre el principal y su baño)
            c1 = ["bath1", "laundry"]
            d1 = _fondo_franja(c1, xb - xs - widths[0], min(hi, max(FR_MIN, acc[1] if acc else 0.0, lo_k)), hi, acc)
            bD1, d1, e1 = fondos(d1)
            w1 = _anchos_dormitorios(Wn, nf, bD1)
            xm = x1 - w1[0]
            vs1 = v1 - bD1 - HALL - d1 + min(d1, max(BATH_MIN_D, V["bano"]["typ_area"] / max(w1[0], 0.1)))
            if w1[0] >= BATH_MIN - 1e-6 and w1[0] * min(d1, max(BATH_MIN_D, V["bano"]["max_area"] / w1[0])) >= \
                    V["bano"]["min_area"] - 1e-6 and sum(_ancho(k, d1, acc) for k in c1) <= xm - xs + 1e-6 and \
                    (sobra >= 1.0 - 1e-6 or (bD1 >= bedD - 1e-6 and _medidas_vestidor(w1[0], vs1, v1, v1 - bD1, True)[2])):
                suite, bedD, d, e, widths = True, bD1, d1, e1, w1
                claves, anchos, sobra = franja(c1, xm - xs, d, e == 0.0)
        hv0, hv1 = v1 - bedD - HALL, v1 - bedD
        bv0 = hv0 - d
        if suite:                                      # el baño en suite, hasta su máximo: lo demás, al dormitorio
            wm = widths[0]                             # (R5.10: con vestidor, el típico: lo demás, al vestidor)
            vs = bv0 + min(d, max(BATH_MIN_D, V["bano"]["typ_area" if vestidor else "max_area"] / wm))
            add("hallway", "hallway", (xs, hv0, xm, hv1))
            add("bath2", "bath", (xm, bv0, x1, vs), "Baño en suite")
            E.append(("bed1", "bath2", "puerta"))
            xz = xm
        else:
            add("hallway", "hallway", (xs, hv0, x1, hv1))
            xz = xb
        anchos, sobra = _repartir(claves, anchos, xz - xs, d)
        if sobra < MIN_W["storage"] + 0.1 or sobra * d < 1.0:   # lo poco que queda (no da para una estancia), a la
            j = max(i for i, k in enumerate(claves) if k != "storage" or i == 0)      # última (no al depósito, que no
            anchos[j] += sobra                                                        # pasa de su máximo)
            sobra = 0.0
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
        if bv0 - v0 >= 1.0:                            # muy profunda: entre la franja y el pasillo común, el depósito
            e, lado, fondo = bv0 - v0, 0.0, 0.0        # junto al hall y lo demás, C: sin uso
            if dep["max_area"] > 0 and e >= dep["min_side"]:
                lado = max(dep["min_side"], min(xb - xs, e, dep["max_area"] ** 0.5))
                fondo = min(e, dep["max_area"] / lado)
                add("storage", "storage", (xs, v0, xs + lado, v0 + fondo), "Depósito")
                E.append(("kitchen" if hall_x0 and xs - x0 - hw >= 1.8 else "hall", "storage", "puerta"))
            resto = (xb - xs) * e - lado * fondo
            if resto >= 1.0:
                aviso = "Sin uso: %.1f m² junto al pasillo común: la vivienda tiene %.1f m de fondo" % (resto, D)
                vacios.append(((xs + lado, v0, xb, bv0), aviso))
                if fondo < e - 0.3:
                    vacios.append(((xs, v0 + fondo, xs + lado, bv0), ""))      # el mismo aviso
        if lateral:
            add("bed%d" % nb, "bedroom", (xb, v0, x1, hv0), "Dormitorio %d" % nb)
            E.append(("hallway", "bed%d" % nb, "puerta"))
        kd = max(1.8, min(KITCH_D, hv0 - v0))
        if xs - x0 - hw < KITCH_LINE:                  # la heladera no entra en línea: la cocina, más profunda (en L),
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
    pcom = p14 if comedor(v0 + kd) else max(p14, min(D - 7.0, sp - v0 - 2.4 + 0.01))
    if hall_x0:                                        # la cocina, desde su borde fijo (el de la zona de noche o x0)
        fija = lambda a, b: real((xs - a, v0, xs, v0 + b))
    else:
        fija = lambda a, b: real((x0, v0, x0 + a, v0 + b))
    if deep:
        if xs - x0 - hw >= 1.8:
            puerta = ("kitchen", "storage", "puerta") in E    # el depósito se abre desde la pared del costado de la
            pp = KITCH_L if puerta else 0.0                     # cocina: su puerta, fuera de la mesada
            wk, kd = cocina(xs - x0 - hw, kd, fija, [max(pcom, pp), max(p14, pp), pp], not puerta)
            if hall_x0:                                # R3.7: el hall en x0 y la cocina hacia la zona de noche
                add("kitchen", "kitchen", (xs - wk, v0, xs, v0 + kd))
                add("hall", "hall", (x0, v0, xs - wk, v0 + kd))
            else:
                add("kitchen", "kitchen", (x0, v0, x0 + wk, v0 + kd))
                add("hall", "hall", (x0 + wk, v0, xs, v0 + kd))
        else:                                          # la cocina dentro del hall: cuenta solo su parte (sin el hall)
            kd = _cocina_integrada(xs - x0 - hw, kd, 0.0, lambda a, b: real((x0, v0, xs, v0 + b), hw * b))[1]
            add("hall", "hall", (x0, v0, xs, v0 + kd), "Hall / Cocina")
    else:
        bw = BATH_W1
        wk = xs - x0 - hw - bw                         # la franja de la entrada, con el fondo del baño (no menos de 1,80)
        con_cocina = wk >= 1.8
        if con_cocina:                                 # (R3.7: con el hall en x0, se pasa por ella al pasillo interno)
            wk, kd = cocina(wk, kd, fija, [kd, max(1.8, p14), 1.8], not hall_x0)
        if hall_x0:                                    # R3.7: hall en x0, baño a su lado y la cocina hasta la zona de
            if con_cocina:                             # noche (se pasa por ella al pasillo interno)
                add("hall", "hall", (x0, v0, xs - wk - bw, v0 + kd))
                add("bath1", "bath", (xs - wk - bw, v0, xs - wk, v0 + kd), "Baño")
                add("kitchen", "kitchen", (xs - wk, v0, xs, v0 + kd))
            else:
                add("hall", "hall", (x0, v0, x0 + hw, v0 + kd))
                add("bath1", "bath", (x0 + hw, v0, xs, v0 + kd), "Baño")
        else:
            if con_cocina:
                add("kitchen", "kitchen", (x0, v0, x0 + wk, v0 + kd))
                add("bath1", "bath", (x0 + wk, v0, x0 + wk + bw, v0 + kd), "Baño")
                add("hall", "hall", (x0 + wk + bw, v0, xs, v0 + kd))
            else:
                add("bath1", "bath", (x0, v0, xs - hw, v0 + kd), "Baño")
                add("hall", "hall", (xs - hw, v0, xs, v0 + kd))
        E.append(("hall", "bath1", "puerta"))
    lv0 = v0 + kd
    if comedor(lv0):
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
    queda = max(sd["min_side"], CAMA_FONDO, sd["min_area"] / max(w, 0.1))
    vmin = max(sv["min_side"], sv["min_area"] / max(w, 0.1))
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


def _std_for(r, nb, integradas=()):
    """Medidas mínimas de la estancia r. integradas (R10.8): las cocinas integradas al estar sin ventana propia, que
    toman las de la norma nacional para ellas (art. 27: de 3 a 5 m², lado 1,40) en lugar de las de una cocina (art. 21)."""
    k, i = r["kind"], r["id"]
    if k == "bedroom":
        return V["dorm_principal"] if (i == "bed1") else V["dorm_secundario"]
    if k == "kitchen" and i in integradas:
        return _ci()
    return {"living": V["estar_comedor"], "kitchen": V["cocina"], "laundry": V["lavadero"], "study": V["estudio"],
            "hallway": V["pasillo"], "hall": V["hall"], "vestidor": V["vestidor"],
            "bath": V["bano"] if i == "bath1" else V["bano_aux"]}.get(k)


def layout_unit(poly, nb, is_facade=None, vivienda=None, equip=None, accesible=False, ediciones=None, ventanas=None,
                entrada=None, vestidor=False):
    """Distribuye una unidad. poly en el marco de la unidad. Devuelve dict con estancias, puertas, grafo, equipamiento y
    comprobaciones. is_facade(p, q): opcional, dice si el segmento p-q (marco de la unidad) está sobre la fachada.
    accesible: puertas de dormitorios y baño de DOOR_ACC, el baño abre hacia afuera y se equipa para silla de ruedas.
    ediciones (R5.7): [(k, {"op": "pared", "p", "a"} | {"op": "puerta", "p", "entre"?, "a"?, "ancho"?, "abre"?})] en el
    marco de la unidad, en orden; el resultado trae en "ediciones" las k aplicadas y en "paredes" los tabiques interiores.
    ventanas (R5.5): medidas de standards["ventanas"]; el resultado trae "ventanas" [{room, p, q, n, ancho, alto, area,
    minimo}] (p-q sobre la fachada, n hacia afuera).
    R5.3: una vivienda con fachada al fondo y en un costado (de esquina o de extremo) la usa: el estar va a la esquina o,
    si el frente no alcanza, el último dormitorio va a ese costado (ver _segunda_fachada); el plano se hace al revés
    cuando hace falta y se devuelve en el marco de la vivienda.
    entrada (R3.7): (lo, hi) del borde v0 sobre el que sigue el pasillo común (se cortó donde ya no hacía falta); si la
    puerta de entrada no cae ahí, el hall va al extremo de ese lado (plano derecho o al revés).
    vestidor (R5.10): el dormitorio principal lleva vestidor, si entra (ver _vestidor)."""
    equip = equip or ST.DEFAULTS["equipamiento"]
    configure(vivienda or ST.DEFAULTS["vivienda"], equip, accesible)
    poly = G.ensure_ccw(poly)
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
    programa = lambda res: [sum(1 for r in res["rooms"] if r["kind"] == k or (k == "kitchen" and "Cocina" in r["name"]))
                            for k in ("bath", "kitchen", "bedroom", "laundry", "living")]
    elegido = None                                     # se comparan sin los cambios a mano: la elección no depende
    if lateral:                                        # de ellos. El dormitorio al costado, solo si el plano mejora y
        con, sin = plano(espejar, True, None), plano(lado == 1, False, None)   # no pierde estancias (el baño 2, solo
        lat = next((r for r in con["rooms"] if r["id"] == "bed%d" % nb), None)  # con hasta 2 dormitorios: criterio
        pc, ps = programa(con), programa(sin)                                    # del usuario)
        if lat and lat["area"] >= V["dorm_secundario"]["min_area"] - 1e-6 and con["score"] > sin["score"] and \
                pc[0] >= (1 if nb <= 2 else max(1, ps[0])) and all(a >= b for a, b in zip(pc[1:], ps[1:])):
            elegido = con
        else:
            espejar, lateral, elegido = lado == 1, False, sin
    if espejar and not lateral:                        # el estar a la esquina, si el plano al revés no es peor ni
        elegido = elegido or plano(True, False, None)  # pierde estancias (en una vivienda irregular, el rectángulo
        recto = plano(False, False, None)              # principal puede cambiar)
        if elegido["score"] < recto["score"] or any(a < b for a, b in zip(programa(elegido), programa(recto))):
            espejar, elegido = False, recto
    hall_x0 = False
    if entrada is not None and not _entra(elegido or plano(espejar, lateral, None), entrada):
        # R3.7: el pasillo común solo sigue sobre una parte del borde: el hall (y la entrada) a ese extremo, con el plano
        # derecho (x0) o al revés (x1); el mejor de los que cumplen
        cands = [(e_, False, True) for e_ in (False, True)]
        if lat_posible:
            cands.append((lado == -1, True, True))
        mejor, hechos = None, {}
        for e_, l_, h_ in cands:
            r_ = hechos[(e_, l_)] = plano(e_, l_, None, h_)
            if l_:                                     # el dormitorio al costado, con el mismo criterio (R5.3)
                sin_ = hechos[(e_, False)]
                lat = next((r for r in r_["rooms"] if r["id"] == "bed%d" % nb), None)
                pc, ps = programa(r_), programa(sin_)
                if not (lat and lat["area"] >= V["dorm_secundario"]["min_area"] - 1e-6 and
                        pc[0] >= (1 if nb <= 2 else max(1, ps[0])) and all(a >= b for a, b in zip(pc[1:], ps[1:]))):
                    continue
            if _entra(r_, entrada) and (mejor is None or r_["score"] > mejor[0]["score"]):
                mejor = (r_, e_, l_, h_)
        if mejor:
            elegido, espejar, lateral, hall_x0 = mejor
        else:
            elegido = None
    res = elegido if elegido is not None and not ediciones else plano(espejar, lateral, ediciones, hall_x0)
    if entrada is not None and not _entra(res, entrada):
        res["checks"].append({"ok": False, "msg": "La puerta de entrada no da al pasillo común"})
        res["score"] = _calidad(res["checks"])
    if vestidor and any(r["id"] == "vest" for r in res["rooms"]):
        # R5.10: el vestidor, solo si el plano no empeora (calidad y estancias); si no, sin él y con aviso
        sin = layout_unit(poly, nb, is_facade, vivienda, equip, accesible, ediciones, ventanas, entrada)
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


def _distribuir(poly, nb, is_facade, equip, accesible, ediciones, ventanas, lateral=False, hall_x0=False, vestidor=False):
    """El plano de layout_unit (poly antihorario, medidas ya configuradas)."""
    (x0, v0, x1, v1), annexes = _main_rect(poly)
    if is_facade is not None:
        (x0, v0, x1, v1), annexes = _main_con_luz(poly, (x0, v0, x1, v1), annexes, is_facade)
    warnings = []
    S_v = ventanas or ST.DEFAULTS["ventanas"]
    prop = S_v.get("proporcion_max", ST.DEFAULTS["ventanas"]["proporcion_max"])     # R10.8: art. 14
    R, E, vacios = _plan_rects(x0, v0, x1, v1, nb, warnings, equip["bano_accesible"] if accesible else None, lateral,
                               hall_x0, vestidor, lambda r: G.strip_area(poly, r[0], r[2], r[1], r[3]), prop)
    vacios = [(G.clip_rect(poly, r[0], r[2], r[1], r[3]), msg) for r, msg in vacios]
    hechas = [k for k, e in (ediciones or []) if e.get("op") == "pared" and e.get("a") and _mover_pared(R, e)]
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
    # anexos (bolsillos de la unidad): estudio si tiene fachada (también oblicua, como una ochava); sin ella, depósito si
    # no pasa de su máximo y, si pasa, C: queda sin uso, con aviso (v2.33)
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
    rooms, ids = [], {}
    for i, (kind, rect, name) in R.items():
        p = G.clip_rect(poly, rect[0], rect[2], rect[1], rect[3]) if not i.startswith("annex") else \
            G.clip_rect(poly, rect[0] - 0.01, rect[2] + 0.01, rect[1] - 0.01, rect[3] + 0.01)
        if p and abs(G.area(p)) > 1.0:
            ids[i] = len(rooms)
            rooms.append({"id": i, "name": name, "kind": kind, "poly": p, "area": abs(G.area(p)), "rect": rect})

    def en_fachada(rect):
        """Tramos de las paredes de la estancia sobre la fachada (con ventana): ahí no van el placard ni el rack de TV."""
        rx0, rv0, rx1, rv1 = rect
        out = []
        for p, q, borde in (((rx0, rv1), (rx1, rv1), abs(rv1 - v1) < 0.05), ((rx0, rv0), (rx0, rv1), abs(rx0 - x0) < 0.05),
                            ((rx1, rv0), (rx1, rv1), abs(rx1 - x1) < 0.05)):
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
    fachadas = {r["id"]: en_fachada(r["rect"]) for r in rooms if r["kind"] in ("bedroom", "living", "dining")}
    # R10.8: las cocinas integradas a la zona de día (abiertas a ella) sin ventana propia (Trazo todavía no les pone):
    # norma nacional, art. 27. De un «Hall / Cocina» cuenta solo la parte de la cocina
    abiertas = {x for a, b, t in E if t == "abierto" for x in (a, b)}
    integradas = {r["id"]: r["area"] if r["kind"] == "kitchen" else
                  max(0.0, r["area"] - HALL_W * (r["rect"][3] - r["rect"][1]))
                  for r in rooms if (r["kind"] == "kitchen" or "Cocina" in r["name"]) and r["id"] in abiertas}
    vent, sin_luz = _ventanas(rooms, poly, is_facade, v1, S_v, sum(integradas.values()))   # R5.5
    integradas = {i: a for i, a in integradas.items() if i not in {w["room"] for w in vent}}
    # conexiones y puertas
    doors, edges = [], []
    for a, b, typ in E:
        if a not in ids or b not in ids:
            continue
        seg = _shared(rooms[ids[a]]["rect"], rooms[ids[b]]["rect"])
        L = 0.0 if not seg else ((seg[1][0] - seg[0][0]) ** 2 + (seg[1][1] - seg[0][1]) ** 2) ** 0.5
        rb = rooms[ids[b]]
        ancho = DOOR_ACC if accesible and (rb["kind"] == "bedroom" or b == "bath1") else DOOR
        ok = L >= (ancho + 0.1 if typ == "puerta" else MIN_SHARE[typ]) - 1e-6     # un borde de 0,8999… m es de 0,90 m
        edges.append({"a": a, "b": b, "type": typ, "ok": ok})
        if ok and typ == "puerta":
            m = ((seg[0][0] + seg[1][0]) / 2, (seg[0][1] + seg[1][1]) / 2)
            vertical = abs(seg[0][0] - seg[1][0]) < 1e-6
            d = ancho / 2
            hoja = lambda m: ((m[0], m[1] - d), (m[0], m[1] + d)) if vertical else ((m[0] - d, m[1]), (m[0] + d, m[1]))
            desde, hacia = (b, a) if accesible and b == "bath1" else (a, b)     # el baño accesible abre hacia afuera
            if rb["kind"] in ("bath", "laundry", "bedroom") and L > ancho + 0.3:   # la puerta donde entran artefactos y muebles
                k = 1 if vertical else 0                     # la puerta se corre a lo largo del borde
                lo, hi = sorted((seg[0][k], seg[1][k]))
                notas, cands = {}, [m[k], lo + d + 0.1, hi - d - 0.1]      # al medio o junto a una esquina
                ent = next((x for x in doors if x["b"] == a), None) if R[a][0] == "vestidor" else None
                if ent:                                      # R5.10: el baño en suite, junto a la entrada del vestidor (sus
                    em = ((ent["p"][0] + ent["q"][0]) / 2, (ent["p"][1] + ent["q"][1]) / 2)     # paredes, para los estantes)
                    cands.sort(key=lambda c: (m[0] - em[0]) ** 2 + (c - em[1]) ** 2 if vertical else
                               (c - em[0]) ** 2 + (m[1] - em[1]) ** 2)
                for c in cands:
                    pq = hoja((m[0], c) if vertical else (c, m[1]))
                    _, falta, info = EQ.resolver(rb, [{"p": pq[0], "q": pq[1], "a": desde, "b": hacia, "ancho": ancho}], {},
                                                 equip, fachadas.get(b, ()), nb, acc=accesible)
                    notas[c] = 2 * len(falta) + len(info)    # un toilette (sin ducha) es peor que el baño completo
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
    # puerta de entrada desde el pasillo común, en el hall
    if "hall" in ids:
        r = rooms[ids["hall"]]["rect"]
        mx = r[0] + min(HALL_W, r[2] - r[0]) / 2 if hall_x0 else (r[0] + r[2]) / 2     # R3.7: junto a x0
        doors.append({"p": (mx - ENTRY / 2, v0), "q": (mx + ENTRY / 2, v0), "into": 1, "vertical": False,
                      "a": "exterior", "b": "hall", "entry": True, "ancho": ENTRY})
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
    start = "hall" if "hall" in ids else next(iter(ids), None)
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
                                                       ((rx1, rv0), (rx1, rv1))) if
                          ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5 >= 1.0)
            else:
                fac = abs(rv1 - v1) < 0.05
            if not fac:
                checks.append({"ok": False, "msg": "%s sin fachada (sin luz natural)" % r["name"]})
                oscuras.add(r["id"])
        w = min(r["rect"][2] - r["rect"][0], r["rect"][3] - r["rect"][1])
        sd = _std_for(r, nb, integradas)
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
                ta = V["estar_por_dorms"][min(nb, len(V["estar_por_dorms"]) - 1)]
            if ta and r["area"] < 0.9 * ta and not (ma and r["area"] < ma):
                below.append("%s %.1f de %.0f m²" % (r["name"], r["area"], ta))
        elif w + 1e-6 < MIN_W.get(r["kind"], 0):
            checks.append({"ok": False, "msg": "%s: ancho %.2f m < mínimo %.2f m" % (r["name"], w, MIN_W[r["kind"]])})
            chicas.add(r["id"])
        if r["kind"] in ("bedroom", "living", "dining", "study") and r["id"] not in chicas and r["id"] not in oscuras \
                and (r["kind"] != "dining" or r["id"] in con_v):   # el comedor interior, con el estar (abajo)
            corto, largo = sorted((r["rect"][2] - r["rect"][0], r["rect"][3] - r["rect"][1]))
            if largo > prop * corto + 1e-6:            # R10.8: art. 14 (si no se avisó ya por su medida o su fachada)
                checks.append({"ok": False, "msg": "%s: %.2f m de profundidad, más de %g veces su lado menor (%.2f m) "
                                                   "(norma nacional, art. 14)" % (r["name"], largo, prop, corto)})
    for d in [r for r in rooms if r["kind"] == "dining" and r["id"] not in con_v and r["id"] not in chicas]:
        est = next((r for r in rooms if r["kind"] == "living" and r["id"] not in chicas and r["id"] not in oscuras and
                    _shared(r["rect"], d["rect"])), None)
        if est:                                        # R10.8: el comedor interior, con el estar que lo ilumina (art. 14)
            prof = max(est["rect"][3], d["rect"][3]) - min(est["rect"][1], d["rect"][1])
            ancho = min(est["rect"][2] - est["rect"][0], d["rect"][2] - d["rect"][0])
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
    equipo, faltan = EQ.equipar(rooms, doors, aberturas, equip, nb, fachadas, chicas, accesible,   # F5: artefactos y muebles
                                ("bed1",) if "vest" in ids else ())      # R5.10: con vestidor, el principal sin placard
    checks += faltan
    for w in warnings:
        if isinstance(w, tuple):
            checks.append({"ok": True, "info": True, "msg": w[1]})
        else:
            checks.append({"ok": False, "msg": w})
    sin_uso = [p for p, msg in vacios if p and abs(G.area(p)) >= 0.3]     # C (v2.33): lo que queda sin uso, con aviso
    checks += [{"ok": False, "msg": msg} for p, msg in vacios if msg and p and abs(G.area(p)) >= 0.3]
    checks += _faltan(rooms)
    if all(c["ok"] for c in checks):
        checks.append({"ok": True, "msg": TODO_BIEN})
    if below:
        checks.append({"ok": True, "info": True, "msg": "Por debajo de la medida típica: " + "; ".join(below)})
    rng = V["rango_vivienda"][min(nb, len(V["rango_vivienda"]) - 1)]
    tot = abs(G.area(poly))
    if tot < rng[0] or tot > rng[1]:
        checks.append({"ok": True, "info": True, "msg": "Superficie %.0f m² fuera del rango de referencia ANV para %d dorm. (%d-%d m²)" % (tot, nb, rng[0], rng[1])})
    nodes = [{"id": r["id"], "name": r["name"], "kind": r["kind"], "pos": G.centroid(r["poly"])} for r in rooms]
    muros = [((c, lo), (c, hi)) if eje == 0 else ((lo, c), (hi, c))     # tabiques interiores (se arrastran en la web);
             for eje, c, lo, hi in paredes({r["id"]: (r["kind"], r["rect"], r["name"]) for r in rooms   # el borde de
                                            if not r["id"].startswith("annex")})]                     # un anexo no se mueve
    score = _calidad(checks)
    for r in rooms:
        del r["rect"]
    return {"rooms": rooms, "doors": doors, "graph": {"nodes": nodes, "edges": edges}, "equipamiento": equipo,
            "checks": checks, "score": score, "bedrooms": nb, "facade": round(x1 - x0, 2),
            "facade_min": round(facade_min(nb), 2), "accesible": bool(accesible), "paredes": muros,
            "ediciones": sorted(hechas), "ventanas": vent, "sin_uso": sin_uso}
