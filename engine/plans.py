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

HALL = 1.1            # ancho del pasillo interno
DOOR = 0.8            # ancho de puerta
LIV_MIN = 3.4         # frente mínimo del estar
BED_MAIN = 3.2        # frente dormitorio principal
BED_W = 2.8           # frente dormitorio secundario
BED_D = 3.0           # fondo mínimo de un dormitorio detrás del pasillo interno
MIN_W = {"bedroom": 2.6, "living": 3.0, "dining": 2.4, "bath": 1.5, "hallway": 0.9, "kitchen": 1.6, "hall": 1.1,
         "laundry": 1.0, "storage": 0.8, "study": 2.2}
DAY = ("hall", "kitchen", "dining", "living", "hallway")     # se conectan en abierto si comparten borde
BATH_W1, BATH_W2, HALL_W, KITCH_D = 1.7, 1.2, 1.4, 2.9
V = ST.DEFAULTS["vivienda"]


def configure(vivienda):
    """Ajusta las medidas de proyecto a partir de la tabla de estándares (standards.py / web)."""
    global HALL, LIV_MIN, BED_MAIN, BED_W, BATH_W1, BATH_W2, HALL_W, KITCH_D, V
    V = vivienda
    HALL = max(V["pasillo"]["min_side"], V["pasillo"]["typ_side"])
    BED_MAIN = max(V["dorm_principal"]["min_side"], V["dorm_principal"]["typ"][0])
    BED_W = max(V["dorm_secundario"]["min_side"], V["dorm_secundario"]["typ"][0])
    LIV_MIN = max(V["estar_comedor"]["min_side"], 0.95 * V["estar_comedor"]["typ"][0])
    BATH_W1 = max(V["bano"]["min_side"], V["bano"]["typ"][0])
    BATH_W2 = max(V["bano_aux"]["min_side"], V["bano_aux"]["typ"][0])
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


def _plan_rects(x0, v0, x1, v1, nb, warnings):
    """Rectángulos de estancias y conexiones con puerta (las abiertas de la zona de día se deducen después)."""
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
        add("bath1", "bath", (x0, v0, x0 + bw, v0 + kd))
        add("kitchen", "kitchen", (x0 + bw, v0, x1 - hw, v0 + kd))
        add("hall", "hall", (x1 - hw, v0, x1, v0 + kd))
        add("living", "living", (x0, v0 + kd, x1, v1), "Estar-Dormitorio")
        E.append(("living", "bath1", "puerta"))
        return R, E

    # ---- reparto del frente entre día y noche
    need = BED_MAIN + BED_W * (nb - 1)
    if W - need >= LIV_MIN:
        Wn = need
        extra = (W - need) - 6.0                       # estar de más de 6 m: repartir a dormitorios
        if extra > 0:
            Wn += min(extra, 0.8 * nb)
    else:
        Wn = max(0.0, W - max(3.0, W * 0.38))
        hard = 3.0 + V["dorm_principal"]["min_side"] + V["dorm_secundario"]["min_side"] * (nb - 1)
        if W >= hard:
            warnings.append(("info", "Frente de %.1f m: estar y dormitorios ajustados por debajo del frente típico (%.1f m)" %
                             (W, facade_min(nb))))
        else:
            warnings.append("Frente de %.1f m insuficiente para estar + %d dormitorio(s) (mín. %.1f m)" %
                            (W, nb, hard))
    xs = x1 - Wn                                       # inicio de la zona de noche
    bedD = max(3.0, min(4.5, D - HALL - 2.4))
    widths = [BED_MAIN] + [BED_W] * (nb - 1)
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
        nbaths = 2 if nb >= 2 and Wn >= BATH_W1 + BATH_W2 + 1.0 else 1
        for j in range(nbaths):
            bw = BATH_W1 if j == 0 else BATH_W2
            add("bath%d" % (j + 1), "bath", (bx, bv0, min(x1, bx + bw), hv0), "Baño" if j == 0 else "Baño 2")
            E.append(("hallway", "bath%d" % (j + 1), "puerta"))
            bx += bw
        if x1 - bx > 1.0:
            lw = min(x1 - bx, max(V["lavadero"]["min_side"], V["lavadero"]["typ_area"] / max(hv0 - bv0, 0.5)))
            if x1 - bx - lw < 0.8:
                lw = x1 - bx
            add("laundry", "laundry", (bx, bv0, bx + lw, hv0), "Lavadero")
            E.append(("hallway", "laundry", "puerta"))
            if x1 - bx - lw >= 0.8:
                add("closet", "storage", (bx + lw, bv0, x1, hv0), "Placard")
                E.append(("hallway", "closet", "puerta"))
        if bv0 - v0 >= 1.0:
            add("storage", "storage", (xs, v0, x1, bv0))
            E.append(("hall", "storage", "puerta"))
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
    specs = [V["dorm_principal"]] + [V["dorm_secundario"]] * (nb - 1)
    mw = [max(sp["min_side"], sp["min_area"] / max(bedD, 0.1) + 0.02) for sp in specs]
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


def _std_for(r, nb):
    k, i = r["kind"], r["id"]
    if k == "bedroom":
        return V["dorm_principal"] if (i == "bed1") else V["dorm_secundario"]
    return {"living": V["estar_comedor"], "kitchen": V["cocina"], "laundry": V["lavadero"], "study": V["estudio"],
            "hallway": V["pasillo"], "hall": V["hall"],
            "bath": V["bano"] if i == "bath1" else V["bano_aux"]}.get(k)


def layout_unit(poly, nb, is_facade=None, vivienda=None):
    """Distribuye una unidad. poly en el marco de la unidad. Devuelve dict con estancias, puertas, grafo y comprobaciones.
    is_facade(p, q): opcional, dice si el segmento p-q (marco de la unidad) está sobre la fachada del edificio."""
    configure(vivienda or ST.DEFAULTS["vivienda"])
    poly = G.ensure_ccw(poly)
    (x0, v0, x1, v1), annexes = _main_rect(poly)
    if is_facade is not None:
        (x0, v0, x1, v1), annexes = _main_con_luz(poly, (x0, v0, x1, v1), annexes, is_facade)
    warnings = []
    R, E = _plan_rects(x0, v0, x1, v1, nb, warnings)
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
    # conexiones y puertas
    doors, edges = [], []
    for a, b, typ in E:
        if a not in ids or b not in ids:
            continue
        seg = _shared(rooms[ids[a]]["rect"], rooms[ids[b]]["rect"])
        L = 0.0 if not seg else ((seg[1][0] - seg[0][0]) ** 2 + (seg[1][1] - seg[0][1]) ** 2) ** 0.5
        ok = L >= MIN_SHARE[typ] - 1e-6                 # un borde de 0,8999… m es de 0,90 m
        edges.append({"a": a, "b": b, "type": typ, "ok": ok})
        if ok and typ == "puerta":
            m = ((seg[0][0] + seg[1][0]) / 2, (seg[0][1] + seg[1][1]) / 2)
            vertical = abs(seg[0][0] - seg[1][0]) < 1e-6
            d = DOOR / 2
            p, q = ((m[0], m[1] - d), (m[0], m[1] + d)) if vertical else ((m[0] - d, m[1]), (m[0] + d, m[1]))
            # la hoja abre hacia la estancia b
            c = G.centroid(rooms[ids[b]]["poly"])
            sw = ((c[0] - m[0]) > 0) if vertical else ((c[1] - m[1]) > 0)
            doors.append({"p": p, "q": q, "into": 1 if sw else -1, "vertical": vertical, "a": a, "b": b})
    # puerta de entrada desde el pasillo común, en el hall
    if "hall" in ids:
        r = rooms[ids["hall"]]["rect"]
        mx = (r[0] + r[2]) / 2
        doors.append({"p": (mx - 0.45, v0), "q": (mx + 0.45, v0), "into": 1, "vertical": False,
                      "a": "exterior", "b": "hall", "entry": True})
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
    below = []
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
        w = min(r["rect"][2] - r["rect"][0], r["rect"][3] - r["rect"][1])
        sd = _std_for(r, nb)
        if sd:
            ms = sd.get("min_side")
            if ms and w + 1e-6 < ms:
                checks.append({"ok": False, "msg": "%s: lado %.2f m < mínimo %.2f m" % (r["name"], w, ms)})
            ma = sd.get("min_area")
            if ma and r["area"] + 1e-6 < ma:
                checks.append({"ok": False, "msg": "%s: %.1f m² < mínimo %.1f m²" % (r["name"], r["area"], ma)})
            ta = sd.get("typ_area")
            if r["kind"] == "living":
                ta = V["estar_por_dorms"][min(nb, len(V["estar_por_dorms"]) - 1)]
            if ta and r["area"] < 0.9 * ta and not (ma and r["area"] < ma):
                below.append("%s %.1f de %.0f m²" % (r["name"], r["area"], ta))
        elif w + 1e-6 < MIN_W.get(r["kind"], 0):
            checks.append({"ok": False, "msg": "%s: ancho %.1f m < mínimo %.1f m" % (r["name"], w, MIN_W[r["kind"]])})
    for w in warnings:
        if isinstance(w, tuple):
            checks.append({"ok": True, "info": True, "msg": w[1]})
        else:
            checks.append({"ok": False, "msg": w})
    if all(c["ok"] for c in checks):
        checks.append({"ok": True, "msg": "Dormitorios y estar con fachada; medidas mínimas cumplidas"})
    if below:
        checks.append({"ok": True, "info": True, "msg": "Por debajo de la medida típica: " + "; ".join(below)})
    rng = V["rango_vivienda"][min(nb, len(V["rango_vivienda"]) - 1)]
    tot = abs(G.area(poly))
    if tot < rng[0] or tot > rng[1]:
        checks.append({"ok": True, "info": True, "msg": "Superficie %.0f m² fuera del rango de referencia ANV para %d dorm. (%d-%d m²)" % (tot, nb, rng[0], rng[1])})
    nodes = [{"id": r["id"], "name": r["name"], "kind": r["kind"], "pos": G.centroid(r["poly"])} for r in rooms]
    real = [c for c in checks if not c.get("info")]
    score = round(100.0 * sum(1 for c in real if c["ok"]) / len(real)) if real else 100
    for r in rooms:
        del r["rect"]
    return {"rooms": rooms, "doors": doors, "graph": {"nodes": nodes, "edges": edges},
            "checks": checks, "score": score, "bedrooms": nb, "facade": round(x1 - x0, 2),
            "facade_min": round(facade_min(nb), 2)}
