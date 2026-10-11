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
V = ST.DEFAULTS["vivienda"]


def _cama_placard(eq):
    """Dormitorio principal con su cama doble y el placard (criterio del usuario, v2.29): (ancho con el placard al costado
    de la cama, fondo con el placard al pie). Con las medidas por defecto, 3,20 y 3,10 m."""
    return (2 * eq["paso_cama"] + eq["cama_doble"][0] + eq["placard_fondo"],
            eq["cama_doble"][1] + eq["paso_cama"] + eq["placard_fondo"])


CAMA_PLACARD = _cama_placard(ST.DEFAULTS["equipamiento"])


def configure(vivienda, equip=None, accesible=False):
    """Ajusta las medidas de proyecto a partir de la tabla de estándares (standards.py / web). accesible: el baño
    principal toma el ancho del baño accesible."""
    global HALL, LIV_MIN, BED_MAIN, BED_W, BATH_W1, BATH_W2, HALL_W, KITCH_D, LAV_W, BATH2_D, V, DOOR, ENTRY, DOOR_ACC
    global CAMA_PLACARD
    V = vivienda
    eq = equip or ST.DEFAULTS["equipamiento"]
    CAMA_PLACARD = _cama_placard(eq)
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
MIN_SHARE = {"puerta": DOOR + 0.1, "abierto": 0.85}
NAMES = {"hall": "Hall", "kitchen": "Cocina", "living": "Estar-Comedor", "dining": "Comedor", "hallway": "Pasillo",
         "bath": "Baño", "bedroom": "Dormitorio", "laundry": "Lavadero", "storage": "Depósito / Placard",
         "study": "Estudio"}


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


def _ventanas(rooms, borde, is_facade, v1, S):
    """R5.5: una ventana por estancia habitable, centrada en su tramo de fachada (primero el del fondo, después el más
    largo), del ancho típico o del que pide el vano mínimo (S["iluminacion"] de su superficie), sin pasar de la mocheta;
    si no alcanza, otra en el tramo siguiente. R5.3: en una esquina, también una (típica) en la otra fachada. El comedor
    sin fachada se ilumina por el estar: su superficie se suma a la del estar. Devuelve (ventanas en el marco de la
    vivienda, comprobaciones con la estancia en "room")."""
    largo = lambda t: ((t[1][0] - t[0][0]) ** 2 + (t[1][1] - t[0][1]) ** 2) ** 0.5
    habit = [r for r in rooms if r["kind"] in ("bedroom", "living", "dining", "study")]
    tramos = {r["id"]: sorted(_tramos_fachada(r["poly"], borde, is_facade, v1),     # primero la fachada del fondo
                              key=lambda t: (t[2][1] < 0.7, -largo(t))) for r in habit}
    comedor = [r for r in habit if r["kind"] == "dining" and not tramos[r["id"]]]
    out, checks = [], []
    for r in habit:
        if r in comedor:                               # el comedor interior se ilumina por el estar
            continue
        area = r["area"] + (sum(c["area"] for c in comedor) if r["kind"] == "living" else 0.0)
        req = S["iluminacion"] * area
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
            checks.append({"ok": False, "room": r["id"], "msg": "%s: ventana%s de %.2f m² < %.2f m² (%.0f %% de la "
                           "superficie%s)" % (r["name"], "s" if n_ > 1 else "", hecho, req, 100 * S["iluminacion"],
                                              " del estar y el comedor" if r["kind"] == "living" and comedor else "")})
    return out, checks


def _frente_noche(W, nb, lateral=False):
    """Frente de la zona de noche y el que pide: los dormitorios al fondo (R5.3, lateral: menos el último, que va al
    costado). Si el frente no alcanza para el estar, se ajusta."""
    need = BED_MAIN + BED_W * (nb - 2 if lateral else nb - 1)
    if W - need >= LIV_MIN:
        return need + min(max((W - need) - 6.0, 0.0), 0.8 * nb), need    # estar de más de 6 m: a los dormitorios
    return max(0.0, W - max(3.0, W * 0.38)), need


def _plan_rects(x0, v0, x1, v1, nb, warnings, acc=None, lateral=False):
    """Rectángulos de estancias y conexiones con puerta (las abiertas de la zona de día se deducen después). acc: frente
    y fondo del baño de una vivienda accesible (None si no lo es). lateral (R5.3): el costado x1 es fachada y el frente
    no alcanza: el último dormitorio va a ese costado, entre el pasillo común y el pasillo interno."""
    W, D = x1 - x0, v1 - v0
    R = {}          # id -> (kind, rect, name)
    E = []          # (id_a, id_b, tipo)

    def add(i, kind, rect, name=None):
        if rect[2] - rect[0] > 0.3 and rect[3] - rect[1] > 0.3:
            R[i] = (kind, rect, name or NAMES[kind])

    if nb == 0:     # monoambiente
        kd = min(2.4, D * 0.4)
        bw = min(2.0, W * 0.35)
        hw = min(1.4, max(1.1, W * 0.2))
        if acc and W - acc[0] - hw >= 1.6:             # baño accesible, si la cocina sigue entrando
            bw, kd = acc[0], max(kd, min(acc[1], D - 3.5))
        add("bath1", "bath", (x0, v0, x0 + bw, v0 + kd))
        add("kitchen", "kitchen", (x0 + bw, v0, x1 - hw, v0 + kd))
        add("hall", "hall", (x1 - hw, v0, x1, v0 + kd))
        add("living", "living", (x0, v0 + kd, x1, v1), "Estar-Dormitorio")
        E.append(("living", "bath1", "puerta"))
        return R, E

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
    bedD = max(3.0, min(4.5, D - HALL - (BED_D if lateral else 2.4)))
    widths = [BED_MAIN] + [BED_W] * (nf - 1)
    k = Wn / sum(widths)
    widths = [w * k for w in widths]
    inner = D - HALL - bedD
    deep = inner >= 1.8
    hw = HALL_W

    if deep:
        # zona de noche (de fachada hacia el pasillo común): dormitorios | pasillo | baños | depósito
        hv0, hv1 = v1 - bedD - HALL, v1 - bedD
        add("hallway", "hallway", (xs, hv0, x1, hv1))
        ib = min(inner, 2.8)
        bv0 = hv0 - ib
        bx = xs
        xb = x1 - ws                                   # R5.3: el dormitorio lateral, en el extremo
        nbaths = 2 if nb >= 2 and xb - xs >= BATH_W1 + BATH_W2 + 1.0 and ib + 1e-6 >= BATH2_D else 1
        for j in range(nbaths):
            bw = BATH_W1 if j == 0 else BATH_W2
            add("bath%d" % (j + 1), "bath", (bx, bv0, min(xb, bx + bw), hv0), "Baño" if j == 0 else "Baño 2")
            E.append(("hallway", "bath%d" % (j + 1), "puerta"))
            bx += bw
        if xb - bx > 1.0:
            lw = min(xb - bx, max(LAV_W, V["lavadero"]["typ_area"] / max(hv0 - bv0, 0.5)))
            if xb - bx - lw < 0.8:
                lw = xb - bx
            add("laundry", "laundry", (bx, bv0, bx + lw, hv0), "Lavadero")
            E.append(("hallway", "laundry", "puerta"))
            if xb - bx - lw >= 0.8:
                add("closet", "storage", (bx + lw, bv0, xb, hv0), "Placard")
                E.append(("hallway", "closet", "puerta"))
        if bv0 - v0 >= 1.0:
            add("storage", "storage", (xs, v0, xb, bv0))
            E.append(("hall", "storage", "puerta"))
        if lateral:
            add("bed%d" % nb, "bedroom", (xb, v0, x1, hv0), "Dormitorio %d" % nb)
            E.append(("hallway", "bed%d" % nb, "puerta"))
        kd = max(1.8, min(KITCH_D, hv0 - v0))
    else:
        # unidad poco profunda: pasillo interno junto al pasillo común, dormitorios detrás
        hv0, hv1 = v0, v0 + HALL
        add("hallway", "hallway", (xs, hv0, x1, hv1))
        bedD = D - HALL
        if bedD < BED_D:
            warnings.append("Fondo de %.1f m escaso para dormitorios (mín. %.1f m)" % (D, fondo_min()))
        kd = min(2.6, max(1.8, D * 0.4))

    # que cada dormitorio alcance su área mínima con el fondo disponible (si el frente lo permite)
    specs = [V["dorm_principal"]] + [V["dorm_secundario"]] * (nf - 1)
    mw = [max(sp["min_side"], sp["min_area"] / max(bedD, 0.1) + 0.02) for sp in specs]
    if bedD < CAMA_PLACARD[1] - 1e-6 and sum(mw[1:]) + max(mw[0], CAMA_PLACARD[0]) <= Wn + 1e-6:
        mw[0] = max(mw[0], CAMA_PLACARD[0])     # y el principal, el ancho de su cama doble con el placard al costado
    if sum(mw) <= Wn + 1e-6:
        widths = [max(w, m_) for w, m_ in zip(widths, mw)]
        over = sum(widths) - Wn
        slack = [w - m_ for w, m_ in zip(widths, mw)]
        if over > 1e-6 and sum(slack) > 0:
            widths = [w - over * s_ / sum(slack) for w, s_ in zip(widths, slack)]
    bxs = xs
    for j, w in enumerate(widths):
        add("bed%d" % (j + 1), "bedroom", (bxs, v1 - bedD, bxs + w, v1),
            "Dormitorio principal" if j == 0 and nb > 1 else ("Dormitorio %d" % (j + 1) if nb > 1 else "Dormitorio"))
        E.append(("hallway", "bed%d" % (j + 1), "puerta"))
        bxs += w

    # ---- zona de día: hall junto a la zona de noche, cocina, comedor/estar a fachada
    if deep:
        if xs - x0 - hw >= 1.8:
            add("kitchen", "kitchen", (x0, v0, xs - hw, v0 + kd))
            add("hall", "hall", (xs - hw, v0, xs, v0 + kd))
        else:
            add("hall", "hall", (x0, v0, xs, v0 + kd), "Hall / Cocina")
    else:
        bw = BATH_W1
        if xs - x0 - hw - bw >= 1.8:
            add("kitchen", "kitchen", (x0, v0, xs - hw - bw, v0 + kd))
            add("bath1", "bath", (xs - hw - bw, v0, xs - hw, v0 + kd), "Baño")
        else:
            add("bath1", "bath", (x0, v0, xs - hw, v0 + kd), "Baño")
        add("hall", "hall", (xs - hw, v0, xs, v0 + kd))
        E.append(("hall", "bath1", "puerta"))
    lv0 = v0 + kd
    sp = v1 - 5.0
    if deep:                                            # el estar debe abarcar la boca del pasillo interno
        sp = min(sp, hv0)
    if v1 - lv0 > 7.0 and sp - lv0 >= 2.4:             # estar muy profundo: comedor interior + estar a fachada
        add("dining", "dining", (x0, lv0, xs, sp))
        add("living", "living", (x0, sp, xs, v1), "Estar")
    else:
        add("living", "living", (x0, lv0, xs, v1))
    return R, E


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


def _faltan(rooms):
    """Programa mínimo (v2.30; norma nacional, arts. 17 y 21): toda vivienda tiene baño y cocina; la cocina dentro del
    hall («Hall / Cocina») cuenta. Lo que falta baja la calidad del plano."""
    out = []
    if not any(r["kind"] == "bath" for r in rooms):
        out.append({"ok": False, "msg": "Sin baño: toda vivienda lleva uno (norma nacional, art. 17)"})
    if not any(r["kind"] == "kitchen" or "Cocina" in r["name"] for r in rooms):
        out.append({"ok": False, "msg": "Sin cocina: toda vivienda lleva una (norma nacional, art. 21)"})
    return out


def _std_for(r, nb):
    k, i = r["kind"], r["id"]
    if k == "bedroom":
        return V["dorm_principal"] if (i == "bed1") else V["dorm_secundario"]
    return {"living": V["estar_comedor"], "kitchen": V["cocina"], "laundry": V["lavadero"], "study": V["estudio"],
            "hallway": V["pasillo"], "hall": V["hall"],
            "bath": V["bano"] if i == "bath1" else V["bano_aux"]}.get(k)


def layout_unit(poly, nb, is_facade=None, vivienda=None, equip=None, accesible=False, ediciones=None, ventanas=None):
    """Distribuye una unidad. poly en el marco de la unidad. Devuelve dict con estancias, puertas, grafo, equipamiento y
    comprobaciones. is_facade(p, q): opcional, dice si el segmento p-q (marco de la unidad) está sobre la fachada.
    accesible: puertas de dormitorios y baño de DOOR_ACC, el baño abre hacia afuera y se equipa para silla de ruedas.
    ediciones (R5.7): [(k, {"op": "pared", "p", "a"} | {"op": "puerta", "p", "entre"?, "a"?, "ancho"?, "abre"?})] en el
    marco de la unidad, en orden; el resultado trae en "ediciones" las k aplicadas y en "paredes" los tabiques interiores.
    ventanas (R5.5): medidas de standards["ventanas"]; el resultado trae "ventanas" [{room, p, q, n, ancho, alto, area,
    minimo}] (p-q sobre la fachada, n hacia afuera).
    R5.3: una vivienda con fachada al fondo y en un costado (de esquina o de extremo) la usa: el estar va a la esquina o,
    si el frente no alcanza, el último dormitorio va a ese costado (ver _segunda_fachada); el plano se hace al revés
    cuando hace falta y se devuelve en el marco de la vivienda."""
    equip = equip or ST.DEFAULTS["equipamiento"]
    configure(vivienda or ST.DEFAULTS["vivienda"], equip, accesible)
    poly = G.ensure_ccw(poly)
    espejar, lateral, lado = _segunda_fachada(poly, nb, is_facade)

    def plano(espejar, lateral, ediciones):
        if not espejar:
            return _distribuir(poly, nb, is_facade, equip, accesible, ediciones, ventanas, lateral)
        bx0, _, bx1, _ = G.bbox(poly)
        m = lambda p: (bx0 + bx1 - p[0], p[1])
        fac = lambda p, q: is_facade(m(p), m(q))
        if hasattr(is_facade, "ventana"):
            fac.ventana = lambda p, q: is_facade.ventana(m(q), m(p))     # la estancia sigue a la izquierda
        ed = [(k, dict(e, p=m(e["p"]), a=m(e["a"]) if e.get("a") else None)) for k, e in (ediciones or [])]
        return _espejar(_distribuir([m(p) for p in poly][::-1], nb, fac, equip, accesible, ed, ventanas, lateral), m)
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
    res = elegido if elegido is not None and not ediciones else plano(espejar, lateral, ediciones)
    usa = "dormitorio" if lateral else ("estar" if lado == -1 or espejar else None)
    if usa:
        res["checks"].append({"ok": True, "info": True, "msg": "Fachada lateral: " + (
            "Dormitorio %d al costado, con su ventana a esa fachada" % nb if lateral else
            "el estar en la esquina, con luz por dos fachadas")})
    res["segunda_fachada"] = usa
    return res


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
    return res


def _distribuir(poly, nb, is_facade, equip, accesible, ediciones, ventanas, lateral=False):
    """El plano de layout_unit (poly antihorario, medidas ya configuradas)."""
    (x0, v0, x1, v1), annexes = _main_rect(poly)
    if is_facade is not None:
        (x0, v0, x1, v1), annexes = _main_con_luz(poly, (x0, v0, x1, v1), annexes, is_facade)
    warnings = []
    R, E = _plan_rects(x0, v0, x1, v1, nb, warnings, equip["bano_accesible"] if accesible else None, lateral)
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
    # anexos (bolsillos de la unidad): estudio si tiene fachada, depósito si no
    for n_, ap in enumerate(annexes):
        r = G.bbox(ap)
        fac = abs(r[3] - v1) < 0.05 and (r[3] - r[1]) >= 3.0 and (is_facade is None or is_facade((r[0], v1), (r[2], v1)))
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
    vent, sin_luz = _ventanas(rooms, poly, is_facade, v1, ventanas or ST.DEFAULTS["ventanas"])   # R5.5
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
                notas = {}
                for c in (m[k], lo + d + 0.1, hi - d - 0.1):  # al medio o junto a una esquina
                    pq = hoja((m[0], c) if vertical else (c, m[1]))
                    _, falta, info = EQ.resolver(rb, [{"p": pq[0], "q": pq[1], "a": desde, "b": hacia, "ancho": ancho}], {},
                                                 equip, fachadas.get(b, ()), nb, acc=accesible)
                    notas[c] = 2 * len(falta) + len(info)    # un toilette (sin ducha) es peor que el baño completo
                    if not notas[c]:
                        break
                c = min(notas, key=lambda c: (notas[c], c != m[k]))
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
        mx = (r[0] + r[2]) / 2
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
    for r in rooms:
        if r["kind"] in ("bedroom", "living", "study"):
            rx0, rv0, rx1, rv1 = r["rect"]
            if is_facade:
                fac = any(is_facade(p, q) for p, q in (((rx0, rv1), (rx1, rv1)), ((rx0, rv0), (rx0, rv1)),
                                                       ((rx1, rv0), (rx1, rv1))) if
                          ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5 >= 1.0)
            else:
                fac = abs(rv1 - v1) < 0.05
            if not fac:
                checks.append({"ok": False, "msg": "%s sin fachada (sin luz natural)" % r["name"]})
                oscuras.add(r["id"])
        w = min(r["rect"][2] - r["rect"][0], r["rect"][3] - r["rect"][1])
        sd = _std_for(r, nb)
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
    aberturas = {}                                     # bordes abiertos entre estancias de día: ahí no va un artefacto
    for e in edges:
        if e["type"] == "abierto" and e["ok"]:
            seg = _shared(rooms[ids[e["a"]]]["rect"], rooms[ids[e["b"]]]["rect"])
            for i, otra in ((e["a"], e["b"]), (e["b"], e["a"])):
                aberturas.setdefault(i, []).append((seg[0], seg[1], otra))
    checks += [{"ok": False, "msg": c["msg"]} for c in sin_luz           # R5.5: vano mínimo (no en una estancia ya
               if c["room"] not in oscuras and c["room"] not in chicas]       # avisada por su fachada o su medida)
    equipo, faltan = EQ.equipar(rooms, doors, aberturas, equip, nb, fachadas, chicas, accesible)  # F5: artefactos y muebles
    checks += faltan
    for w in warnings:
        if isinstance(w, tuple):
            checks.append({"ok": True, "info": True, "msg": w[1]})
        else:
            checks.append({"ok": False, "msg": w})
    checks += _faltan(rooms)
    if all(c["ok"] for c in checks):
        checks.append({"ok": True, "msg": "Dormitorios y estar con fachada; medidas mínimas cumplidas"})
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
    real = [c for c in checks if not c.get("info")]
    score = round(100.0 * sum(1 for c in real if c["ok"]) / len(real)) if real else 100
    for r in rooms:
        del r["rect"]
    return {"rooms": rooms, "doors": doors, "graph": {"nodes": nodes, "edges": edges}, "equipamiento": equipo,
            "checks": checks, "score": score, "bedrooms": nb, "facade": round(x1 - x0, 2),
            "facade_min": round(facade_min(nb), 2), "accesible": bool(accesible), "paredes": muros,
            "ediciones": sorted(hechas), "ventanas": vent}
