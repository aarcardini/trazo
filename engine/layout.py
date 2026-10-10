"""Motor de generación: masa -> planta -> pasillo/núcleos -> mix de unidades -> planos de unidad.

Inspirado en el flujo público de Finch 101 (Massing Studio, Generate Corridors and Core,
Generate Unit Mix around Corridor, Unit Plans). Es una implementación propia y simplificada.
"""
import math
from . import geometry as G
from . import plans as P
from . import standards as ST
from . import programs as PR

VERSION = "2.6"

DEFAULT_PARAMS = {
    # Masa
    "floor_height": 3.0,
    "outer_wall": 0.35,
    "stories": None,            # lista opcional [{program, height}]
    # Pasillo / núcleos
    "centerline": None,         # (compatibilidad) [[x,y],[x,y]]
    "centerlines": None,        # lista de polilíneas [[[x,y],...],...] en coordenadas de mundo; None = automático
    "cores_mode": "auto",       # auto | manual
    "cores": None,              # núcleos manuales: [[x,y],...] (posición en mundo, el motor los ajusta al pasillo)
    "corridor_width": 2.0,
    "core_width": 5.0,
    "core_depth": 7.0,          # incluye el pasillo (como en Finch)
    "core_count": 2,
    "auto_cores": True,
    "core_side": "alternate",   # alternate | left | right
    "egress_single": 18.0,
    "egress_multi": 30.0,
    # Mix
    "unit_mix": [{"name": "2 dorm", "area": 75, "percent": 50, "dorms": 2},
                 {"name": "3 dorm", "area": 95, "percent": 50, "dorms": 3}],
    "min_unit_width": 5.0,
    "party_wall": 0.30,
    "max_unit_depth": 14.0,
    "unit_width_target_min": 4.0,
    "loading": "auto",          # auto | double | single (pasillo central o pasillo de borde)
    "core_auto": True,          # núcleo dimensionado a partir de escalera + ascensores (standards)
    "standards": None,          # valores que sobrescriben engine/standards.py
    "medianeras": None,         # [{"a":[x,y],"b":[x,y],"retiro":m}] bordes del predio contra linderos
    "patios_mode": "auto",      # auto (patios en predios entre medianeras demasiado profundos) | manual
    "patios": None,             # patios manuales: [[[x,y],...],...] en coordenadas de mundo
}


def merge_params(p):
    out = dict(DEFAULT_PARAMS)
    out.update({k: v for k, v in (p or {}).items() if v is not None or k in ("stories", "centerline", "centerlines", "cores", "medianeras", "patios")})
    return out


# ---------------------------------------------------------------- masa
def _inward(a, b):
    L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    return -(b[1] - a[1]) / L, (b[0] - a[0]) / L


def apply_setbacks(fp, meds):
    """Retira la huella r metros de cada medianera con retiro > 0 (corta por una paralela al lindero)."""
    for m in meds or []:
        r = float(m.get("retiro") or 0)
        if r <= 0:
            continue
        a, b = m["a"], m["b"]
        nx, ny = _inward(a, b)
        c = G.centroid(fp)
        if nx * (c[0] - a[0]) + ny * (c[1] - a[1]) < 0:      # la normal debe apuntar hacia el edificio
            nx, ny = -nx, -ny
        cut = G.clip_halfplane(fp, nx, ny, nx * a[0] + ny * a[1] + r)
        if len(cut) >= 3 and abs(G.area(cut)) > 1.0:
            fp = G.ensure_ccw(G.clean(cut))
    return fp


def make_blind(meds, min_retiro):
    """Función que dice si un punto está sobre una medianera ciega (sin ventanas)."""
    segs = []
    for m in meds or []:
        r = float(m.get("retiro") or 0)
        if r >= min_retiro:
            continue
        segs.append((m["a"], m["b"], r))
    if not segs:
        return None

    def blind(pt):
        for a, b, r in segs:
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy) or 1.0
            t = ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dy) / L
            d = abs((pt[0] - a[0]) * dy - (pt[1] - a[1]) * dx) / L
            if -0.5 <= t <= L + 0.5 and d <= r + 0.7:
                return True
        return False
    return blind


def build_massing(footprint, height, params):
    fp = G.ensure_ccw(G.clean([tuple(p) for p in footprint]))
    fp = apply_setbacks(fp, params.get("medianeras"))
    fh = params["floor_height"]
    stories = params.get("stories")
    if not stories:
        n = max(1, int(round(height / fh)))
        stories = [{"program": "Residential", "height": fh} for _ in range(n)]
    z = 0.0
    out = []
    for i, s in enumerate(stories):
        h = float(s.get("height") or fh)
        out.append({"index": i, "program": s.get("program", "Residential"), "height": h, "z": round(z, 3)})
        z += h
    plate = G.inset(fp, params["outer_wall"]) if params["outer_wall"] > 0 else fp
    plate = G.ensure_ccw(G.clean(plate))
    return fp, plate, out



# ---------------------------------------------------------------- alas (descomposición rectilínea)
def _dominant_angle(poly):
    best, ang = 0.0, 0.0
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L > best:
            best, ang = L, math.atan2(b[1] - a[1], b[0] - a[0])
    return ang % (math.pi / 2)


def _is_rectilinear(loc, tol=1e-3):
    n = len(loc)
    for i in range(n):
        a, b = loc[i], loc[(i + 1) % n]
        if abs(a[0] - b[0]) > tol and abs(a[1] - b[1]) > tol:
            return False
    return True


def _slabs(loc, vertical, holes=()):
    """Rectángulos de la descomposición por franjas (vertical u horizontal), fusionando iguales.
    Con huecos (patios interiores), las franjas también se cortan en sus bordes."""
    pts = [(p[1], p[0]) for p in loc] if vertical else list(loc)
    hs = [[(p[1], p[0]) for p in h] if vertical else list(h) for h in holes]
    # ahora las franjas son horizontales sobre pts: cortes en y
    ys = sorted({round(p[1], 6) for p in pts + [q for h in hs for q in h]})
    slabs = []
    for y0, y1 in zip(ys, ys[1:]):
        if y1 - y0 < 1e-6:
            continue
        ivs = G.line_intervals_multi([pts] + hs, (y0 + y1) / 2.0) if hs else G.line_intervals(pts, (y0 + y1) / 2.0)
        slabs.append([y0, y1, [(round(a, 6), round(b, 6)) for a, b in ivs]])
    merged = []
    for sl in slabs:
        if merged and merged[-1][2] == sl[2] and abs(merged[-1][1] - sl[0]) < 1e-6:
            merged[-1][1] = sl[1]
        else:
            merged.append(sl)
    rects = []
    for y0, y1, ivs in merged:
        for a, b in ivs:
            r = [(a, y0), (b, y0), (b, y1), (a, y1)]
            rects.append([(p[1], p[0]) for p in r] if vertical else r)
    return rects


def decompose_wings(plate, min_side=5.0, holes=None, blind=None):
    """Divide una planta ortogonal en rectángulos (alas). Devuelve (ángulo, [polígonos mundo]) o None.
    holes: patios interiores (la planta es un anillo); tienen que ser ortogonales en el mismo marco.
    blind: en un anillo, las alas a lo largo de una medianera ciega puntúan menos (sus viviendas no tienen luz)."""
    th = _dominant_angle(plate)
    loc = G.ensure_ccw([G.rotate(p, -th) for p in plate])
    hl = [[G.rotate(p, -th) for p in h] for h in (holes or [])]
    if not _is_rectilinear(loc) or not all(_is_rectilinear(h) for h in hl):
        return None
    best = None
    for vertical in (True, False):
        rects = _slabs(loc, vertical, hl)
        rects = [r for r in rects if min(G.bbox(r)[2] - G.bbox(r)[0], G.bbox(r)[3] - G.bbox(r)[1]) >= min_side]
        if not rects:
            continue
        score = sum(max(G.bbox(r)[2] - G.bbox(r)[0], G.bbox(r)[3] - G.bbox(r)[1]) for r in rects) - 8.0 * len(rects)
        if hl and blind:
            score -= sum(_lado_ciego(r, th, blind) for r in rects)
        if best is None or score > best[0]:
            best = (score, rects)
    if best is None:
        return None
    return th, [[G.rotate(p, th) for p in r] for r in best[1]]


def _lado_ciego(r, th, blind):
    """Largo de un ala (rectángulo en el marco girado th) si uno de sus lados largos es medianera ciega, si no 0."""
    x0, y0, x1, y1 = G.bbox(r)
    if x1 - x0 >= y1 - y0:
        lados = [((x0 + x1) / 2, y0), ((x0 + x1) / 2, y1)]
    else:
        lados = [(x0, (y0 + y1) / 2), (x1, (y0 + y1) / 2)]
    return max(x1 - x0, y1 - y0) if any(blind(G.rotate(p, th)) for p in lados) else 0.0


# ---------------------------------------------------------------- pasillo y núcleos
def pick_frame(plate, params):
    """Devuelve (origen, ángulo, x_a, x_b) del eje del pasillo en coordenadas de mundo."""
    cl = params.get("centerline")
    if cl and len(cl) >= 2:
        a, b = cl[0], cl[-1]
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        return (a[0], a[1]), ang, 0.0, L
    ang = G.min_area_rect_angle(plate)
    loc = [G.rotate(p, -ang) for p in plate]
    x0, y0, x1, y1 = G.bbox(loc)
    cy = (y0 + y1) / 2.0
    best = max(G.line_intervals(loc, cy), key=lambda t: t[1] - t[0])
    o = G.rotate((best[0], cy), ang)
    return o, ang, 0.0, best[1] - best[0]


def core_positions(xa, xb, n, cw):
    if n <= 1:
        return [(xa + xb) / 2.0]
    half = cw / 2.0
    xs0, xs1 = xa + half, xb - half
    if xs1 <= xs0:
        return [(xa + xb) / 2.0]
    return [xs0 + (xs1 - xs0) * i / (n - 1) for i in range(n)]


def side_for(i, mode):
    if mode == "left":
        return 1
    if mode == "right":
        return -1
    return 1 if i % 2 == 0 else -1


def _frame_for_poly(poly, ang):
    loc0 = G.to_local(poly, (0.0, 0.0), ang)
    x0, y0, x1, y1 = G.bbox(loc0)
    origin = G.to_world([(x0, (y0 + y1) / 2.0)], (0.0, 0.0), ang)[0]
    return origin, ang, 0.0, x1 - x0


def _make_piece(poly, origin, ang, xa, xb):
    return {"poly": poly, "origin": origin, "angle": ang, "xa": xa, "xb": xb,
            "loc_plate": G.to_local(poly, origin, ang), "cores": [], "junctions": [],
            "extra_blocks": {1: [], -1: []}, "corridor_ext": [], "free": [True, True]}


def _avg_unit_area(params):
    mix = [m for m in params["unit_mix"] if m.get("percent", 0) > 0 and m.get("area", 0) > 0] or params["unit_mix"]
    tot = sum(m["percent"] for m in mix) or 1.0
    return sum(m["percent"] / tot * m["area"] for m in mix) or 75.0


def _choose_single(short, params):
    mode = params.get("loading", "auto")
    if mode == "single":
        return True
    if mode == "double":
        return False
    cw, pw = params["corridor_width"], params["party_wall"]
    avg = _avg_unit_area(params)
    d2 = max(1.0, (short - cw) / 2.0 - pw)
    d1 = max(1.0, short - cw - pw)
    # frente necesario para estar + dormitorios con ventana (media ponderada del mix)
    mix = [m for m in params["unit_mix"] if m.get("percent", 0) > 0 and m.get("area", 0) > 0]
    tot = sum(m["percent"] for m in mix) or 1.0
    need = sum(m["percent"] / tot * P.facade_min(int(m["dorms"]) if m.get("dorms") is not None
                                                  else P.bedrooms_for(m["area"])) for m in mix) if mix else 0
    ok2, ok1 = avg / d2 >= need, avg / d1 >= need
    if ok2 != ok1:
        return ok1
    return abs(math.log(avg / d1 ** 2)) < abs(math.log(avg / d2 ** 2))


def _ring_single(short, largo, puente, params):
    """Ala de un anillo alrededor de un patio: ¿pasillo de borde? Con pasillo central cada vivienda tiene la mitad
    del fondo, y en un ala corta que une otras dos el frente lo limita su largo. Pasillo de borde si con pasillo
    central no entra un dormitorio; en un ala que une, la opción con viviendas más cercanas a la superficie del mix."""
    if params.get("loading", "auto") != "auto":
        return params["loading"] == "single"
    cw, pw = params["corridor_width"], params["party_wall"]
    d2 = (short - cw) / 2.0 - pw
    d1 = min(short - cw - pw, params["max_unit_depth"])
    if d2 < P.fondo_min():
        return True
    if puente:
        avg = _avg_unit_area(params)
        return abs(math.log(largo * d1 / avg)) < abs(math.log(largo * d2 / avg))
    return _choose_single(short, params)


def _single_frame(poly, ang, params, centre):
    """Marco con el pasillo pegado a un borde del ala (el más cercano al centro de la planta)."""
    cw = params["corridor_width"]
    best = None
    for a in (ang, ang + math.pi):
        loc0 = G.to_local(poly, (0.0, 0.0), a)
        x0, y0, x1, y1 = G.bbox(loc0)
        origin = G.to_world([(x0, y0 + cw / 2.0)], (0.0, 0.0), a)[0]
        mid = G.to_world([((x1 - x0) / 2.0, 0.0)], origin, a)[0]
        dist = math.hypot(mid[0] - centre[0], mid[1] - centre[1])
        bl = params.get("_blind")
        if bl and bl(G.to_world([((x0 + x1) / 2.0, y0)], (0.0, 0.0), a)[0]):
            dist -= 1e6                                  # pasillo contra la medianera: libera la fachada
        if best is None or dist < best[0] - 1e-6:
            best = (dist, origin, a, 0.0, x1 - x0)
    return best[1:]


def _bridge_axis(poly, polys, th, holes, params):
    """En un anillo alrededor de un patio: eje (0 = x, 1 = y del marco th) en el que el ala une otras dos por sus lados
    opuestos, o None. Solo un ala que da al patio y no más ancha que un ala con pasillo central. Su pasillo va de una
    a la otra, así el pasillo da la vuelta al patio."""
    r = G.bbox([G.rotate(p, -th) for p in poly])
    otros = [G.bbox([G.rotate(p, -th) for p in q]) for q in polys if q is not poly]
    hb = [G.bbox([G.rotate(p, -th) for p in h]) for h in holes]
    ancho_max = 2 * params["max_unit_depth"] + params["corridor_width"] + params["party_wall"]

    def toca(axis, at):
        a0, a1 = (r[1], r[3]) if axis == 0 else (r[0], r[2])
        for o in otros:
            lo, hi = (o[0], o[2]) if axis == 0 else (o[1], o[3])
            b0, b1 = (o[1], o[3]) if axis == 0 else (o[0], o[2])
            if (abs(hi - at) < 1e-6 or abs(lo - at) < 1e-6) and min(a1, b1) - max(a0, b0) > 1.0:
                return True
        return False
    for axis in (0, 1):
        lo, hi = (r[0], r[2]) if axis == 0 else (r[1], r[3])
        c0, c1 = (r[1], r[3]) if axis == 0 else (r[0], r[2])        # sus lados a lo largo del pasillo
        al_patio = any(abs(c - (h[1] if axis == 0 else h[0])) < 0.05 or abs(c - (h[3] if axis == 0 else h[2])) < 0.05
                       for h in hb for c in (c0, c1))
        if al_patio and c1 - c0 <= ancho_max and toca(axis, lo) and toca(axis, hi):
            return axis
    return None


def build_pieces(plate, params):
    if params.get("centerlines") or params.get("centerline"):
        up = build_user_pieces(plate, params)
        if up:
            return up
    holes = params.get("_huecos")
    dec = decompose_wings(plate, holes=holes, blind=params.get("_blind"))
    if not dec:
        o, a, xa, xb = pick_frame(plate, params)
        pc = _make_piece(plate, o, a, xa, xb)
        loc = pc["loc_plate"]
        x0_, y0_, x1_, y1_ = G.bbox(loc)
        if _choose_single(y1_ - y0_, params) or (params.get("_blind") and (
                params["_blind"](G.to_world([((x0_ + x1_) / 2, y0_)], o, a)[0]) !=
                params["_blind"](G.to_world([((x0_ + x1_) / 2, y1_)], o, a)[0]))):
            o, a, xa, xb = _single_frame(plate, a, params, G.centroid(plate))
            pc = _make_piece(plate, o, a, xa, xb)
            pc["single"] = True
        return [pc]
    th, polys = dec
    centre = G.centroid(plate)
    pieces = []
    bl = params.get("_blind")
    for poly in polys:
        x0, y0, x1, y1 = G.bbox([G.rotate(p, -th) for p in poly])
        ang = th if (x1 - x0) >= (y1 - y0) else th + math.pi / 2
        short = min(x1 - x0, y1 - y0)
        puente = _bridge_axis(poly, polys, th, holes, params) if holes else None
        if puente is not None:
            ang = th if puente == 0 else th + math.pi / 2
            short = (y1 - y0) if puente == 0 else (x1 - x0)
        largo = ((x1 - x0) + (y1 - y0)) - short                 # a lo largo del pasillo
        lb = [False, False]
        if bl:
            l0 = G.to_local(poly, (0.0, 0.0), ang)
            a0, b0, a1, b1 = G.bbox(l0)
            lb = [bl(G.to_world([((a0 + a1) / 2, b0)], (0.0, 0.0), ang)[0]),
                  bl(G.to_world([((a0 + a1) / 2, b1)], (0.0, 0.0), ang)[0])]
        if all(lb) and len(polys) == 1:
            # predio entre medianeras: pasillo transversal en el medio, viviendas hacia los dos frentes
            pc = _make_piece(poly, *_frame_for_poly(poly, ang + math.pi / 2))
            pc["between"] = True
            pieces.append(pc)
            continue
        if any(lb) and not all(lb):
            pc = _make_piece(poly, *_single_frame(poly, ang, params, centre))
            pc["single"] = True
            pieces.append(pc)
            continue
        if _ring_single(short, largo, puente is not None, params) if holes else _choose_single(short, params):
            pc = _make_piece(poly, *_single_frame(poly, ang, params, centre))
            pc["single"] = True
        else:
            pc = _make_piece(poly, *_frame_for_poly(poly, ang))
        pieces.append(pc)
    return pieces


def _link(pieces, i, e, nb, params):
    """Une el extremo e (0=xa, 1=xb) de la pieza i con el pasillo de la pieza nb (conector + bloqueo)."""
    cw, pw = params["corridor_width"], params["party_wall"]
    pc, q = pieces[i], pieces[nb]
    xe, sgn = (pc["xa"], -1) if e == 0 else (pc["xb"], 1)
    pc["free"][e] = False
    E = G.to_world([(xe, 0.0)], pc["origin"], pc["angle"])[0]
    P = G.to_local([E], q["origin"], q["angle"])[0]
    d = G.rotate((sgn, 0.0), pc["angle"] - q["angle"])
    if abs(d[1]) < 0.2:       # ejes paralelos: unión directa
        pc["junctions"].append({"x": xe, "nb": nb, "nbx": P[0]})
        return
    t = max(0.0, -P[1] / d[1])
    ext_len = t + cw / 2.0
    if sgn < 0:
        box = [(xe - ext_len, -cw / 2), (xe, -cw / 2), (xe, cw / 2), (xe - ext_len, cw / 2)]
    else:
        box = [(xe, -cw / 2), (xe + ext_len, -cw / 2), (xe + ext_len, cw / 2), (xe, cw / 2)]
    world_box = G.to_world(box, pc["origin"], pc["angle"])
    pc["corridor_ext"].append(world_box)
    qb = G.to_local(world_box, q["origin"], q["angle"])
    bx0, by0, bx1, by1 = G.bbox(qb)
    side = 1 if (by0 + by1) / 2 > 0 else -1
    protrusion = max(by1 - cw / 2, -cw / 2 - by0, 0.0)
    if protrusion > 0.6:      # el conector invade la zona de unidades; si no, vive dentro del pasillo
        q["extra_blocks"][side].append((bx0 - pw / 2, bx1 + pw / 2))
    pc["junctions"].append({"x": xe, "nb": nb, "nbx": P[0] + d[0] * t})


def _connect(pieces, plate, params):
    """Alas automáticas: detecta extremos libres/uniones y crea los conectores de pasillo."""
    for i, pc in enumerate(pieces):
        for e, (xe, sgn) in enumerate(((pc["xa"], -1), (pc["xb"], 1))):
            probe = G.to_world([(xe + sgn * 0.8, 0.0)], pc["origin"], pc["angle"])[0]
            nb = next((j for j, q in enumerate(pieces) if j != i and G.point_in_poly(probe, q["poly"])), None)
            if nb is not None:
                _link(pieces, i, e, nb, params)
                if params.get("_huecos"):            # anillo: la unión sirve en los dos sentidos (el pasillo da la vuelta)
                    j = pc["junctions"][-1]
                    pieces[nb]["junctions"].append({"x": j["nbx"], "nb": i, "nbx": j["x"]})


def _ring_corners(pieces, plate, params):
    """Anillo: las viviendas van donde su fondo da a una fachada o al patio. Donde el fondo de la franja de viviendas
    no tiene luz (esquinas interiores del patio, o un ala descartada por angosta), no se ponen viviendas: queda sin
    usar (las unidades de esquina llegan con la mejora de codos)."""
    bordes = [plate] + list(params.get("_huecos") or [])
    bl, pw, paso = params.get("_blind"), params["party_wall"], 0.25
    for q in pieces:
        _, qy0, _, qy1 = G.bbox(q["loc_plate"])
        n = max(1, int((q["xb"] - q["xa"]) / paso))
        xs = [q["xa"] + (q["xb"] - q["xa"]) * k / n for k in range(n + 1)]
        for sd, yf in ((1, qy1 - 0.05), (-1, qy0 + 0.05)):
            ws = G.to_world([(x, yf) for x in xs], q["origin"], q["angle"])
            luz = [min(_dist_to_boundary(w, b) for b in bordes) <= 0.4 and not (bl and bl(w)) for w in ws]
            k = 0
            while k <= n:
                if luz[k]:
                    k += 1
                    continue
                j = k
                while j < n and not luz[j + 1]:
                    j += 1
                if xs[j] - xs[k] >= 1.0:
                    q["extra_blocks"][sd].append((xs[k] - pw / 2, xs[j] + pw / 2))
                k = j + 1


def _dist_point_segment(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def _clip_sr(pc, fn):
    """Aplica una función de recorte a las regiones de unidades de ambos lados de una pieza."""
    for sd in (1, -1):
        r = pc["side_region"].get(sd)
        pc["side_region"][sd] = fn(r) if r else []


def build_user_pieces(plate, params):
    """Una pieza por tramo de cada polilínea dibujada. La planta se reparte entre tramos:
    en giros de ~90° con cortes ortogonales (el tramo anterior se queda con el codo interior),
    en otros ángulos con la bisectriz."""
    cw, pw = params["corridor_width"], params["party_wall"]
    D = params["max_unit_depth"]
    c = cw / 2 + pw / 2
    cls = params.get("centerlines") or ([params["centerline"]] if params.get("centerline") else [])
    pieces, chains = [], []
    for pl in cls:
        pts = []
        for p in pl:
            p = (float(p[0]), float(p[1]))
            if not pts or math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) > 0.05:
                pts.append(p)
        if len(pts) < 2:
            continue
        n = len(pts) - 1
        idxs = []
        for k in range(n):
            a, b = pts[k], pts[k + 1]
            ang = math.atan2(b[1] - a[1], b[0] - a[0])
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            full = G.to_local(plate, a, ang)
            base = G.clip_rect(full, None, None, -(cw / 2 + pw + D), cw / 2 + pw + D)
            if not base:
                continue
            sr = {1: list(base), -1: list(base)}
            ortho_next = None
            if k < n - 1:   # vértice final (x=L)
                v = G.rotate((pts[k + 2][0] - b[0], pts[k + 2][1] - b[1]), -ang)
                Lv = math.hypot(*v) or 1.0
                ux_, uy_ = v[0] / Lv, v[1] / Lv
                if abs(ux_) < 0.15 and abs(uy_) > 0.95:        # giro ~90°
                    sB = 1 if uy_ > 0 else -1
                    sr[sB] = G.clip_rect(sr[sB], None, L - c, None, None)
                    ortho_next = sB
                else:
                    nx, ny = -1 - ux_, -uy_
                    if math.hypot(nx, ny) > 1e-6:
                        for sd in (1, -1):
                            sr[sd] = G.clip_halfplane(sr[sd], nx, ny, nx * L) if sr[sd] else []
                        sr = {sd: (G.clean(r) if len(r) >= 3 else []) for sd, r in sr.items()}
            if k > 0:       # vértice inicial (x=0)
                w = G.rotate((pts[k - 1][0] - a[0], pts[k - 1][1] - a[1]), -ang)
                Lw = math.hypot(*w) or 1.0
                wx_, wy_ = w[0] / Lw, w[1] / Lw
                prev_pc = pieces[idxs[-1]] if idxs else None
                if abs(wx_) < 0.15 and abs(wy_) > 0.95 and prev_pc is not None:
                    inner = 1 if wy_ > 0 else -1
                    outer = -inner
                    start_in = c
                    ts = prev_pc.get("turn_side")
                    # fondo típico del lado interior del tramo anterior (mediana a lo largo del tramo)
                    depths = []
                    Lp = prev_pc["xb"]
                    if ts and Lp > 2 * c + 1:
                        for t in range(1, 8):
                            xs_ = c + (Lp - 2 * c) * t / 8.0
                            slab = G.clip_rect(prev_pc["full"], xs_ - 0.05, xs_ + 0.05, c, c + D) if ts > 0 else \
                                G.clip_rect(prev_pc["full"], xs_ - 0.05, xs_ + 0.05, -(c + D), -c)
                            if slab:
                                ys_ = [abs(p[1]) for p in slab]
                                depths.append(max(ys_))
                    if depths:
                        depths.sort()
                        start_in = max(c, depths[len(depths) // 2] + pw / 2)
                    sr[inner] = G.clip_rect(sr[inner], start_in, None, None, None)
                    sr[outer] = G.clip_rect(sr[outer], c, None, None, None)
                else:
                    nx, ny = 1 - wx_, -wy_
                    if math.hypot(nx, ny) > 1e-6:
                        for sd in (1, -1):
                            sr[sd] = G.clip_halfplane(sr[sd], nx, ny, 0.0) if sr[sd] else []
                        sr = {sd: (G.clean(r) if len(r) >= 3 else []) for sd, r in sr.items()}
            pc = _make_piece(G.to_world(base, a, ang), a, ang, 0.0, L)
            pc["loc_plate"] = base
            pc["full"] = full
            pc["side_region"] = sr
            pc["turn_side"] = ortho_next
            pc["user"] = True
            xa_c = -cw / 2 if k > 0 else 0.0
            xb_c = L + cw / 2 if k < n - 1 else L
            pc["corridor_local"] = G.clip_rect(full, xa_c, xb_c, -cw / 2, cw / 2)
            pieces.append(pc)
            idxs.append(len(pieces) - 1)
        for u, v in zip(idxs, idxs[1:]):     # tramos consecutivos: unión directa
            pieces[u]["free"][1] = False
            pieces[v]["free"][0] = False
            pieces[u]["junctions"].append({"x": pieces[u]["xb"], "nb": v, "nbx": 0.0})
            pieces[v]["junctions"].append({"x": 0.0, "nb": u, "nbx": pieces[u]["xb"]})
        chains.append(idxs)
    # extremos libres que tocan el pasillo de otra polilínea (empalme en T)
    chain_of = {i: ci for ci, idxs in enumerate(chains) for i in idxs}
    for i, pc in enumerate(pieces):
        for e in (0, 1):
            if not pc["free"][e]:
                continue
            xe = pc["xa"] if e == 0 else pc["xb"]
            E = G.to_world([(xe, 0.0)], pc["origin"], pc["angle"])[0]
            best = None
            for j, q in enumerate(pieces):
                if j == i or chain_of.get(j) == chain_of.get(i):
                    continue
                A = q["origin"]
                B = G.to_world([(q["xb"], 0.0)], q["origin"], q["angle"])[0]
                dd = _dist_point_segment(E, A, B)
                if dd < cw + 2.5 and (best is None or dd < best[0]):
                    best = (dd, j)
            if best:
                _link(pieces, i, e, best[1], params)
                _stem_vs_trunk(pieces, i, e, best[1], params)
    _split_parallel(pieces, chain_of, params)
    return pieces


def _stem_vs_trunk(pieces, i, e, j, params):
    """Empalme en T: el tronco (j) reserva el pasillo del ramal y la franja de unidades hasta D;
    el ramal (i) solo recibe unidades más allá de esa franja."""
    cw, pw, D = params["corridor_width"], params["party_wall"], params["max_unit_depth"]
    stem, trunk = pieces[i], pieces[j]
    xf = stem["xb"] if e == 0 else stem["xa"]
    F = G.to_world([(xf, 0.0)], stem["origin"], stem["angle"])[0]
    sb = 1 if G.to_local([F], trunk["origin"], trunk["angle"])[0][1] > 0 else -1
    cor_w = G.to_world(stem["corridor_local"], stem["origin"], stem["angle"]) if stem.get("corridor_local") else []
    if cor_w:
        bx0, by0, bx1, by1 = G.bbox(G.to_local(cor_w, trunk["origin"], trunk["angle"]))
        trunk["extra_blocks"][sb].append((bx0 - pw / 2, bx1 + pw / 2))
    th = cw / 2 + pw + D

    def fn(r):
        tw = G.to_local(G.to_world(r, stem["origin"], stem["angle"]), trunk["origin"], trunk["angle"])
        tw = G.clip_rect(tw, None, None, th, None) if sb > 0 else G.clip_rect(tw, None, None, None, -th)
        return G.to_local(G.to_world(tw, trunk["origin"], trunk["angle"]), stem["origin"], stem["angle"]) if tw else []
    _clip_sr(stem, fn)


def _split_parallel(pieces, chain_of, params):
    """Pasillos paralelos de distintas líneas: la planta entre ambos se reparte por la línea media."""
    cw, pw, D = params["corridor_width"], params["party_wall"], params["max_unit_depth"]
    for i, pc in enumerate(pieces):
        for j, q in enumerate(pieces):
            if i == j or chain_of.get(i) == chain_of.get(j) or not pc.get("side_region"):
                continue
            if abs(math.sin(pc["angle"] - q["angle"])) > 0.03 or math.cos(pc["angle"] - q["angle"]) == 0:
                continue
            A = G.to_local([q["origin"]], pc["origin"], pc["angle"])[0]
            Bq = G.to_local(G.to_world([(q["xb"], 0.0)], q["origin"], q["angle"]), pc["origin"], pc["angle"])[0]
            ov = min(pc["xb"], max(A[0], Bq[0])) - max(pc["xa"], min(A[0], Bq[0]))
            yo = (A[1] + Bq[1]) / 2.0
            if ov < 1.0 or abs(yo) > 2 * (cw / 2 + pw + D) or abs(yo) < cw:
                continue
            cut = yo / 2.0
            _clip_sr(pc, (lambda r: G.clip_rect(r, None, None, None, cut - pw / 2)) if yo > 0 else
                     (lambda r: G.clip_rect(r, None, None, cut + pw / 2, None)))


def egress_at(pieces, i, x, depth=3):
    pc = pieces[i]
    best = min((abs(x - c["x"]) for c in pc["cores"]), default=1e9)
    if depth > 0:
        for j in pc["junctions"]:
            best = min(best, abs(x - j["x"]) + egress_at(pieces, j["nb"], j["nbx"], depth - 1))
    return best


def _add_core(pc, x, side, params):
    cw, w, d = params["corridor_width"], params["core_width"], params["core_depth"]
    if side > 0:
        box = (x - w / 2, -cw / 2, x + w / 2, -cw / 2 + d)
    else:
        box = (x - w / 2, cw / 2 - d, x + w / 2, cw / 2)
    strip = G.clip_rect(pc["loc_plate"], box[0], box[2])
    if strip:
        ys = [p[1] for p in strip]
        pocket = 4.5      # detrás del núcleo no cabe una unidad útil: el núcleo llega hasta la fachada
        if side > 0 and 0 < max(ys) - box[3] < pocket:
            box = (box[0], box[1], box[2], max(ys))
        if side < 0 and 0 < box[1] - min(ys) < pocket:
            box = (box[0], min(ys), box[2], box[3])
    pc["cores"].append({"x": x, "side": side, "box": box,
                        "poly_local": G.clip_rect(pc["loc_plate"], box[0], box[2], box[1], box[3])})


def _propagate_core_blocks(pieces, params):
    """Un núcleo de una pieza que invade la región de unidades de otra pieza la bloquea allí."""
    pw = params["party_wall"]
    for i, pc in enumerate(pieces):
        for c in pc["cores"]:
            if not c["poly_local"]:
                continue
            cw_ = G.to_world(c["poly_local"], pc["origin"], pc["angle"])
            for j, q in enumerate(pieces):
                if j == i or not q.get("side_region"):
                    continue
                ql = G.to_local(cw_, q["origin"], q["angle"])
                bx0, by0, bx1, by1 = G.bbox(ql)
                for sd in (1, -1):
                    reg = q["side_region"].get(sd)
                    if not reg:
                        continue
                    ov = G.clip_rect(reg, bx0, bx1, max(by0, 0.0), by1) if sd > 0 else \
                        G.clip_rect(reg, bx0, bx1, by0, min(by1, 0.0))
                    if ov and abs(G.area(ov)) > 2.0:
                        q["extra_blocks"][sd].append((bx0 - pw / 2, bx1 + pw / 2))


def generate_circulation(plate, params):
    pieces = _generate_circulation(plate, params)
    _propagate_core_blocks(pieces, params)
    return pieces


def is_between(plate, params):
    """Predio entre medianeras: planta rectangular con los dos lados largos ciegos."""
    bl = params.get("_blind")
    if not bl or params.get("centerlines") or params.get("centerline") or params.get("_huecos"):
        return False
    dec = decompose_wings(plate)
    if not dec or len(dec[1]) != 1:
        return False
    th, (poly,) = dec
    x0, y0, x1, y1 = G.bbox([G.rotate(p, -th) for p in poly])
    ang = th if (x1 - x0) >= (y1 - y0) else th + math.pi / 2
    a0, b0, a1, b1 = G.bbox(G.to_local(poly, (0.0, 0.0), ang))
    return bl(G.to_world([((a0 + a1) / 2, b0)], (0.0, 0.0), ang)[0]) and \
        bl(G.to_world([((a0 + a1) / 2, b1)], (0.0, 0.0), ang)[0])


def _between_depth(params):
    """Fondo de las viviendas hacia cada frente entre medianeras: el que da el m² objetivo con el frente mínimo
    para sus dormitorios."""
    mix_ = [m for m in params["unit_mix"] if m.get("percent", 0) > 0 and m.get("area", 0) > 0]
    tot_ = sum(m["percent"] for m in mix_) or 1.0
    avg_a = sum(m["percent"] / tot_ * m["area"] for m in mix_) if mix_ else 75.0
    avg_f = sum(m["percent"] / tot_ * P.facade_min(int(m["dorms"]) if m.get("dorms") is not None
                                                    else P.bedrooms_for(m["area"])) for m in mix_) if mix_ else 9.4
    return max(7.5, min(params["max_unit_depth"], 1.15 * avg_a / max(avg_f, 1.0)))


def _generate_circulation(plate, params):
    pieces = build_pieces(plate, params)
    cw = params["corridor_width"]
    if len(pieces) == 1 and pieces[0].get("between"):
        # franja central: núcleo contra una medianera + hall; una vivienda hacia cada frente
        pc = pieces[0]
        pc["corridor_local"] = G.clip_rect(pc["loc_plate"], pc["xa"], pc["xb"], -cw / 2, cw / 2)
        w = params["core_width"]
        box = (pc["xa"], -cw / 2, pc["xa"] + w, cw / 2)
        pc["cores"].append({"x": pc["xa"] + w / 2, "side": 0, "box": box, "between": True,
                            "poly_local": G.clip_rect(pc["loc_plate"], box[0], box[2], box[1], box[3])})
        # predio largo: solo los frentes tienen luz -> viviendas de fondo máx. D en cada frente,
        # pasillo contra la medianera hasta ellas y zona central sin luz (requiere patios)
        loc = pc["loc_plate"]
        _, ly0, _, ly1 = G.bbox(loc)
        D = _between_depth(params)
        cwc = params.get("_cw_base", 2.0)
        pc["side_region"] = {1: loc, -1: loc}
        pc["dark"] = []
        pc["egress_extra"] = {1: 0.0, -1: 0.0}
        for sd in (1, -1):
            far = ly1 if sd > 0 else -ly0
            if far - cw / 2 <= D + 1.5:
                continue
            u0 = far - D                                   # inicio de la franja de viviendas (desde el eje)
            t0 = u0 - cwc                                  # pasillo transversal delante de las viviendas
            rng = lambda a, b: (a, b) if sd > 0 else (-b, -a)
            ya, yb = rng(u0, far)
            pc["side_region"][sd] = G.clip_rect(loc, None, None, ya, yb)
            ta, tb = rng(t0, u0)
            la, lb = rng(cw / 2, t0)
            trans = G.clip_rect(loc, None, None, ta, tb)
            longi = G.clip_rect(loc, pc["xb"] - cwc, pc["xb"], la, lb)
            for cp in (trans, longi):
                if cp:
                    pc["corridor_ext"].append(G.to_world(cp, pc["origin"], pc["angle"]))
            dz = G.clip_rect(loc, None, pc["xb"] - cwc, la, lb)
            if dz and abs(G.area(dz)) > 1:
                pc["dark"].append(G.to_world(dz, pc["origin"], pc["angle"]))
            pc["egress_extra"][sd] = t0 - cw / 2
        return pieces
    user = any(pc.get("user") for pc in pieces)
    for pc in pieces:
        if "corridor_local" not in pc:
            pc["corridor_local"] = G.clip_rect(pc["loc_plate"], pc["xa"], pc["xb"], -cw / 2, cw / 2)
    if not user:
        _connect(pieces, plate, params)
    if params.get("_huecos") and not user:
        _ring_corners(pieces, plate, params)
    counter = [0]

    def next_side():
        s = side_for(counter[0], params["core_side"])
        counter[0] += 1
        return s

    half = params["core_width"] / 2.0
    if params.get("cores_mode") == "manual":
        for idx, spec in enumerate(params.get("cores") or []):
            wx, wy = float(spec[0]), float(spec[1])
            best = None
            for i, pc in enumerate(pieces):
                lx, ly = G.to_local([(wx, wy)], pc["origin"], pc["angle"])[0]
                dx = max(pc["xa"] - lx, 0.0, lx - pc["xb"])
                dist = math.hypot(dx, ly)
                if best is None or dist < best[0]:
                    best = (dist, i, lx, ly)
            if best is None:
                continue
            _, i, lx, ly = best
            pc = pieces[i]
            if pc["xb"] - pc["xa"] >= 2 * half:
                lx = min(max(lx, pc["xa"] + half), pc["xb"] - half)
            else:
                lx = (pc["xa"] + pc["xb"]) / 2.0
            side = 1 if pc.get("single") else (1 if ly >= 0 else -1) if abs(ly) > 0.3 else next_side()
            _add_core(pc, lx, side, params)
            pc["cores"][-1]["spec"] = idx
        return pieces
    ring = bool(params.get("_huecos"))
    for pc in pieces:               # un núcleo en cada extremo libre
        for e, free in enumerate(pc["free"]):
            if free:
                xe = pc["xa"] if e == 0 else pc["xb"]
                if ring and pc["junctions"] and \
                        min(abs(xe - j["x"]) for j in pc["junctions"]) <= params["egress_single"]:
                    continue        # punta corta de un pasillo que da la vuelta al patio: se sale hacia los dos lados
                x = pc["xa"] + half if e == 0 else pc["xb"] - half
                if pc["xb"] - pc["xa"] < 2 * half:
                    x = (pc["xa"] + pc["xb"]) / 2.0
                _add_core(pc, x, 1 if pc.get("single") else next_side(), params)

    def worst():
        w = (-1.0, None, None)
        for i, pc in enumerate(pieces):
            if pc["xb"] - pc["xa"] < 1:
                continue
            n = max(2, int((pc["xb"] - pc["xa"]) / 1.0))
            for k in range(n + 1):
                x = pc["xa"] + (pc["xb"] - pc["xa"]) * k / n
                v = egress_at(pieces, i, x)
                if v > w[0]:
                    w = (v, i, x)
        return w

    total = lambda: sum(len(pc["cores"]) for pc in pieces)
    guard = 0
    while guard < 10:
        guard += 1
        v, i, x = worst()
        need_count = total() < int(params["core_count"])
        need_egress = params.get("auto_cores") and v > params["egress_multi"]
        if not (need_count or need_egress) or total() >= 8 or i is None:
            break
        pc = pieces[i]
        x = min(max(x, pc["xa"] + half), pc["xb"] - half) if pc["xb"] - pc["xa"] >= 2 * half else (pc["xa"] + pc["xb"]) / 2
        _add_core(pc, x, 1 if pc.get("single") else next_side(), params)
    return pieces


# ---------------------------------------------------------------- mix de unidades
def _bisect_x(poly, x0, y0, y1, target, xmax, dir_=1):
    """x1 tal que area(poly ∩ [x0,x1]x[y0,y1]) = target."""
    lo, hi = x0, xmax
    if G.strip_area(poly, x0, hi, y0, y1) < target:
        return None
    for _ in range(50):
        mid = (lo + hi) / 2.0
        if G.strip_area(poly, x0, mid, y0, y1) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _chain_union(rects):
    """Unión de rectángulos contiguos (ordenados por x) que comparten bordes verticales."""
    pts = []
    for r in rects:
        pts += [(r[0], r[1]), (r[2], r[1])]
    for r in reversed(rects):
        pts += [(r[2], r[3]), (r[0], r[3])]
    return G.clean(pts)


def _is_rect(poly, tol=0.02):
    x0, y0, x1, y1 = G.bbox(poly)
    A = (x1 - x0) * (y1 - y0)
    return A > 0 and abs(abs(G.area(poly)) - A) / A < tol


def _segments(loc, circ, params):
    """Regiones laterales (local) entre núcleos, a cada lado del pasillo.
    El bolsillo que queda detrás de un núcleo se suma al tramo vecino para no desperdiciar planta."""
    cw = params["corridor_width"]
    pw = params["party_wall"]
    segs = []
    for side in (1, -1):
        loc = circ["side_region"].get(side, []) if circ.get("side_region") else circ["loc_plate"]
        if not loc:
            continue
        if circ.get("side_region"):
            bx0_, _, bx1_, _ = G.bbox(loc)
            xa, xb = bx0_, bx1_
        else:
            xa, xb = circ["xa"], circ["xb"]
        if side > 0:
            y0, y1 = cw / 2 + pw / 2, None
        else:
            y0, y1 = None, -cw / 2 - pw / 2
        blocks = []
        pockets = []
        for c in circ["cores"]:
            if c["side"] == side:
                b = c["box"]
                blocks.append((b[0], b[2]))
                if side > 0:
                    pk = G.clip_rect(loc, b[0], b[2], b[3] + pw / 2, None)
                else:
                    pk = G.clip_rect(loc, b[0], b[2], None, b[1] - pw / 2)
                if pk and abs(G.area(pk)) >= 6 and _is_rect(pk):
                    pockets.append((b[0], b[2], pk))
        blocks += list(circ.get("extra_blocks", {}).get(side, []))
        blocks.sort()
        cur = xa
        ivs = []
        for b0, b1 in blocks:
            if b0 > cur:
                ivs.append((cur, b0))
            cur = max(cur, b1)
        if cur < xb:
            ivs.append((cur, xb))
        used = set()
        for a, b in ivs:
            region = G.clip_rect(loc, a, b, y0, y1)
            if not region or abs(G.area(region)) <= 4:
                continue
            if _is_rect(region):
                r = G.bbox(region)
                parts = [r]
                for k, (px0, px1, pk) in enumerate(pockets):   # bolsillo a la derecha
                    q = G.bbox(pk)
                    if k not in used and abs(px0 - r[2]) < 0.05:
                        used.add(k)
                        parts.append(q)
                        break
                for k, (px0, px1, pk) in enumerate(pockets):   # bolsillo a la izquierda
                    q = G.bbox(pk)
                    if k not in used and abs(px1 - r[0]) < 0.05:
                        used.add(k)
                        parts.insert(0, q)
                        break
                if len(parts) > 1:
                    region = _chain_union(parts)
            segs.append({"side": side, "x0": a, "x1": b, "region": region})
    return segs


def generate_unit_mix(circ, params, state=None):
    loc = circ["loc_plate"]
    cw, pw = params["corridor_width"], params["party_wall"]
    mix = [m for m in params["unit_mix"] if m.get("percent", 0) > 0 and m.get("area", 0) > 0]
    tot = sum(m["percent"] for m in mix) or 1.0
    for m in mix:
        m["_p"] = m["percent"] / tot
    segs = _segments(loc, circ, params)
    state = state if state is not None else {}
    placed = state.setdefault("placed", {m["name"]: 0 for m in mix})
    n_placed = state.get("n", 0)
    units = []
    warnings = []
    for seg in segs:
        side = seg["side"]
        region = seg["region"]
        xs = [p[0] for p in region]
        xmin, xmax = min(xs), max(xs)
        A_seg = abs(G.area(region))
        length = xmax - xmin
        if length < 0.6 * params["min_unit_width"] or A_seg < 0.4 * min(m_["area"] for m_ in mix):
            continue
        avg = sum(m["_p"] * m["area"] for m in mix)
        n_max = max(1, int(length // max(params["min_unit_width"], 1.0)))
        n0 = max(1, int(round(A_seg / avg)))

        def plan(n):
            pl, cnt = dict(placed), n_placed
            seq = []
            for _ in range(n):
                m = max(mix, key=lambda t: t["_p"] * (cnt + 1) - pl[t["name"]])
                seq.append(m)
                pl[m["name"]] += 1
                cnt += 1
            return seq

        best = None
        cands = sorted({min(max(1, n), n_max) for n in (n0 - 1, n0, n0 + 1)})
        for n in cands:
            seq = plan(n)
            k = A_seg / sum(m["area"] for m in seq)
            sc = abs(math.log(k))
            if best is None or sc < best[0]:
                best = (sc, seq, k)
        if best is None:
            seq = plan(1)
            best = (0, seq, A_seg / seq[0]["area"])
        _, seq, k = best
        for m in seq:
            placed[m["name"]] += 1
            n_placed += 1
        state["n"] = n_placed
        x = xmin
        for idx, m in enumerate(seq):
            last = idx == len(seq) - 1
            x1 = xmax if last else (_bisect_x(region, x, None, None, m["area"] * k, xmax) or xmax)
            xe = x1 - (0 if last else pw / 2)
            xs0 = x + (pw / 2 if idx > 0 else 0)
            poly = G.clip_rect(region, xs0, xe)
            if poly:
                a_ = abs(G.area(poly))
                w = xe - xs0
                units.append({"type": m["name"], "target": m["area"], "area": a_, "width": w,
                              "side": side, "x0": xs0, "x1": xe, "poly_local": poly})
                if w < params["min_unit_width"]:
                    warnings.append("Unidad con ancho %.1f m < mínimo %.1f m" % (w, params["min_unit_width"]))
            x = x1
    # puertas, evacuación y profundidad
    for i, u in enumerate(units):
        xd = (u["x0"] + u["x1"]) / 2.0
        yd = (cw / 2) * u["side"]
        u["door_local"] = (xd, yd)
        u["egress"] = 0.0
        ys = [p[1] for p in u["poly_local"]]
        u["depth"] = (max(ys) - min(ys))
        if u["depth"] > params["max_unit_depth"] + 0.5:
            warnings.append("Unidad %s de %.0f m² tiene profundidad %.1f m (> %.1f m): poca luz natural" %
                            (u["type"], u["area"], u["depth"], params["max_unit_depth"]))
    return units, warnings


def metrics_mix(units, params):
    mix = [m for m in params["unit_mix"] if m.get("percent", 0) > 0]
    tot = sum(m["percent"] for m in mix) or 1.0
    n = len(units)
    if not n:
        return {"count": 0, "match_score": 0, "fit_m2": 0, "unique_units": 0, "nsa": 0, "by_type": {}}
    by = {}
    for u in units:
        d = by.setdefault(u["type"], {"count": 0, "area": 0.0})
        d["count"] += 1
        d["area"] += u["area"]
    dev = 0.0
    for m in mix:
        actual = by.get(m["name"], {"count": 0})["count"] / n * 100.0
        dev += abs(actual - m["percent"] / tot * 100.0)
    fit = sum(abs(u["area"] - u["target"]) for u in units) / n
    uniq = len({(u["type"], round(u["area"], 0), round(u["width"], 1)) for u in units})
    return {"count": n, "match_score": round(100 - dev / 2.0, 1), "fit_m2": round(fit, 1),
            "unique_units": uniq, "nsa": round(sum(u["area"] for u in units), 1),
            "by_type": {k: {"count": v["count"], "avg_area": round(v["area"] / v["count"], 1)} for k, v in by.items()}}


# ---------------------------------------------------------------- planos de unidad
def bedrooms_for(area):
    return P.bedrooms_for(area)


def _dist_to_boundary(pt, poly):
    return min(_dist_point_segment(pt, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def unit_rooms(u, params, pc=None, plate=None):
    """Distribuye una unidad (ver engine/plans.py) y devuelve el resultado en el marco local de la pieza."""
    side = u["side"]
    cw = params["corridor_width"]
    pw = params["party_wall"]
    y_in = cw / 2 + pw / 2
    poly = [(x, side * y - y_in) for x, y in u["poly_local"]]   # unidad en v>=0, v=0 junto al pasillo
    if side < 0:
        poly = poly[::-1]
    spec = next((m for m in params["unit_mix"] if m.get("name") == u["type"]), {})
    nb = int(spec["dorms"]) if spec.get("dorms") is not None else P.bedrooms_for(u.get("target") or u["area"])
    back = lambda pt: (pt[0], side * (pt[1] + y_in))
    is_fac = None
    if pc is not None and plate:
        bl, pd = params.get("_blind"), params.get("_patio_dark")
        bordes = [plate] + list(params.get("_huecos") or [])      # fachada exterior y caras a los patios interiores

        def is_fac(p, q):
            for t_ in (0.25, 0.5, 0.75):
                m = (p[0] + (q[0] - p[0]) * t_, p[1] + (q[1] - p[1]) * t_)
                w = G.to_world([back(m)], pc["origin"], pc["angle"])[0]
                if min(_dist_to_boundary(w, b) for b in bordes) > 0.4 or (bl and bl(w)) or (pd and pd(w)):
                    return False
            return True
    res = P.layout_unit(poly, nb, is_fac, ST.merged(params.get("standards"))["vivienda"])

    def back_poly(pl):
        out = [back(p) for p in pl]
        return out[::-1] if side < 0 else out
    for r in res["rooms"]:
        r["poly_local"] = back_poly(r.pop("poly"))
    for d in res["doors"]:
        d["p"], d["q"] = back(d["p"]), back(d["q"])
        d["into"] = d["into"] * (side if not d["vertical"] else 1)
    for n in res["graph"]["nodes"]:
        n["pos"] = back(n["pos"])
    return res


# ---------------------------------------------------------------- patios y bloques
def auto_patios(fp, plate, params, ancho):
    """Patios automáticos: un predio entre medianeras demasiado profundo para que llegue la luz a todo se divide en
    bloques iguales separados por patios de `ancho` m (cada bloque con su núcleo y una vivienda hacia cada lado)."""
    if not is_between(plate, params):
        return []
    th, (poly,) = decompose_wings(plate)
    x0, y0, x1, y1 = G.bbox([G.rotate(p, -th) for p in poly])
    ang = th if (x1 - x0) >= (y1 - y0) else th + math.pi / 2       # a lo largo de las medianeras
    u0, v0, u1, v1 = G.bbox(G.to_local(fp, (0.0, 0.0), ang))
    cw, D, muro = params["corridor_width"], _between_depth(params), params["outer_wall"]
    franja = max(cw, params["core_depth"] - cw)              # núcleo + hall en el medio de cada bloque
    lleno = 2 * (D + 1.5) + franja + 2 * muro                # fondo que se ilumina entero desde sus dos frentes
    L = u1 - u0
    if L <= 2 * (D + cw + 1.0) + franja + 2 * muro:          # sin patio quedaría a lo sumo 1 m sin luz
        return []
    n = max(2, int(math.ceil((L + ancho) / (lleno + ancho))))
    B = (L - (n - 1) * ancho) / n
    out = []
    for k in range(1, n):
        a = u0 + k * B + (k - 1) * ancho
        out.append(G.to_world([(a, v0 - 1), (a + ancho, v0 - 1), (a + ancho, v1 + 1), (a, v1 + 1)], (0.0, 0.0), ang))
    return out


def _anillo(b, hs, muro):
    """Planta de un bloque (huella b con patios interiores hs): el muro exterior hacia afuera y hacia cada patio."""
    pl = G.inset(b, muro) if muro > 0 else b
    ph = [G.ensure_ccw(G.clean(G.inset(G.ensure_ccw(h), -muro) if muro > 0 else G.ensure_ccw(h))) for h in hs]
    return G.ensure_ccw(G.clean(pl)), ph


def split_blocks(fp, patios, params, warnings):
    """Huella menos patios -> (bloques, plantas, patios dentro de la huella). Cada bloque y cada planta es
    (exterior, [huecos]): un patio rodeado de edificio deja un hueco y el bloque es un anillo alrededor del patio."""
    muro = params["outer_wall"]
    usar = list(range(len(patios)))
    while True:
        partes, dentro = G.subtract(fp, [patios[i] for i in usar])
        fuera = [k for k, d in zip(usar, dentro) if not d]
        for k in fuera:
            warnings.append("Patio %d: queda fuera de la masa y no se usa" % (k + 1))
        malos = []
        for b, hs in partes:                 # un anillo tiene que poder dividirse en alas ortogonales
            if hs:
                pl, ph = _anillo(G.ensure_ccw(G.clean(b)), hs, muro)
                if decompose_wings(pl, holes=ph) is None:
                    th = _dominant_angle(pl)
                    orto = all(_is_rectilinear([G.rotate(p, -th) for p in l]) for l in [pl] + ph)
                    for k, d in zip(usar, dentro):       # los patios de este anillo: sus vértices están en un hueco
                        if d and any(_dist_to_boundary(q, h) < 1e-3 for pp in d for q in pp for h in hs):
                            malos.append(k)
                            warnings.append(("Patio %d: deja alas de menos de 5 m a su alrededor; no se usa" if orto else
                                             "Patio %d: está rodeado de edificio en una masa que no es ortogonal (o el "
                                             "patio está girado respecto de la masa); todavía no se puede usar") % (k + 1))
        if not fuera and not malos:
            break
        usar = [k for k in usar if k not in fuera and k not in malos]
    bloques, plantas = [], []
    for b, hs in partes:
        b = G.ensure_ccw(G.clean(b))
        pl, ph = _anillo(b, hs, muro)
        if len(pl) < 3 or G.area(pl) - sum(abs(G.area(h)) for h in ph) < 10.0:
            warnings.append("Un bloque de %.0f m² queda demasiado chico o angosto entre patios: no se usa" % abs(G.area(b)))
            continue
        bloques.append((b, [G.ensure_ccw(G.clean(h)) for h in hs]))
        plantas.append((pl, ph))
    return bloques, plantas, [pp for d in dentro for pp in d]


def make_patio_dark(partes, ancho_min, muro, warnings):
    """Función que dice si un punto de la planta da a un patio más angosto que ancho_min (sus caras no iluminan)."""
    angostos = []
    for p in partes:
        a = G.min_area_rect_angle(p)
        x0, y0, x1, y1 = G.bbox([G.rotate(q, -a) for q in p])
        w = min(x1 - x0, y1 - y0)
        if w + 1e-6 < ancho_min:
            angostos.append(p)
            warnings.append("Patio de %.1f m de ancho: menos de %.1f m, no ilumina (sus caras cuentan como medianera)"
                            % (w, ancho_min))
    if not angostos:
        return None
    return lambda pt: any(G.point_in_poly(pt, p) or _dist_to_boundary(pt, p) <= muro + 0.5 for p in angostos)


def _block_of(pt, bloques):
    for i, b in enumerate(bloques):
        if G.point_in_poly(pt, b):
            return i
    return min(range(len(bloques)), key=lambda i: _dist_to_boundary(pt, bloques[i]))


def _block_of_line(line, bloques):
    """Bloque donde está la mayor parte de una polilínea (por sus vértices y puntos medios)."""
    pts = list(line) + [((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0) for a, b in zip(line, line[1:])]
    votos = [_block_of(p, bloques) for p in pts]
    return max(set(votos), key=votos.count)


# ---------------------------------------------------------------- orquestación
def generate(data):
    params = merge_params(data.get("params"))
    S0 = ST.merged(params.get("standards"))
    params["_blind"] = make_blind(params.get("medianeras"), S0["predio"]["retiro_ventanas"])
    stage = data.get("stage", "plans")
    footprint = data["footprint"]
    height = float(data.get("height") or params["floor_height"] * 5)
    fp, plate, stories = build_massing(footprint, height, params)
    res = {"stage": stage, "footprint": G.pol_to_list(fp), "stories": stories, "warnings": []}
    meds = params.get("medianeras") or []
    rmin = S0["predio"]["retiro_ventanas"]
    res["medianeras"] = [{"a": m["a"], "b": m["b"], "retiro": float(m.get("retiro") or 0),
                          "ventanas": float(m.get("retiro") or 0) >= rmin} for m in meds]
    for m in res["medianeras"]:
        if 0 < m["retiro"] < rmin:
            res["warnings"].append("Retiro de %.1f m en medianera: menor a %.1f m, sigue sin admitir ventanas" % (m["retiro"], rmin))
    # ---- núcleo real: escalera + ascensores según altura y unidades servidas
    S = ST.merged(params.get("standards"))
    cw = params["corridor_width"]
    hs = [round(s_["height"], 2) for s_ in stories]
    floor_h = max(set(hs), key=hs.count)                  # altura de piso más frecuente
    for s_ in stories:
        if s_["height"] > floor_h + 0.01:
            res["warnings"].append("Nivel %d (%.2f m) más alto que la planta tipo: su escalera necesita %d contrahuellas" %
                                   (s_["index"], s_["height"], ST.stair_box(ST.merged(params.get("standards"))["nucleo"], s_["height"])[2]))
    top_h = stories[-1]["z"]
    n_res_lv = sum(1 for s_ in stories if s_["program"] == "Residential")
    units_est = abs(G.area(plate)) * 0.72 / max(_avg_unit_area(params), 1.0) * n_res_lv
    n_elev = ST.elevators_needed(S["nucleo"], len(stories), top_h, units_est)
    if params.get("core_auto", True):
        params["core_width"], params["core_depth"] = ST.core_size(S["nucleo"], floor_h, n_elev, cw)
    sw_, sl_, risers_ = ST.stair_box(S["nucleo"], floor_h)
    stype = ("común" if top_h <= 12 else "protegida (EP)" if top_h <= 30 else "presurizada (PFP)")
    core_m = {"elevators": n_elev, "width": params["core_width"],
              "depth": round(params["core_depth"] - cw, 2), "stair_type": stype,
              "stair_box": [round(sw_, 2), round(sl_, 2)], "risers": risers_,
              "riser_h": round(floor_h / risers_, 3), "top_level": round(top_h, 2)}
    # ---- patios: la huella menos los patios da uno o más bloques, cada uno con su planta, su pasillo y su núcleo
    ancho_patio = S0["predio"]["patio_min"]
    auto = params.get("patios_mode", "auto") != "manual"
    patios = auto_patios(fp, plate, params, ancho_patio) if auto else \
        [p for p in (params.get("patios") or []) if len(p) >= 3]
    if patios:
        bloques, plantas, partes = split_blocks(fp, patios, params, res["warnings"])
        params["_patio_dark"] = make_patio_dark(partes, ancho_patio, params["outer_wall"], res["warnings"])
    else:
        bloques, plantas, partes = [(fp, [])], [(plate, [])], []
    neta = lambda bh: abs(G.area(bh[0])) - sum(abs(G.area(h)) for h in bh[1])     # sin los patios interiores
    gfa_plate = sum(neta(p) for p in plantas)
    fp_area = sum(neta(b) for b in bloques)
    res["plate"] = G.pol_to_list(plantas[0][0] if plantas else plate)
    res["blocks"] = []
    for (b, hb), (p, hp) in zip(bloques, plantas):
        res["blocks"].append({"footprint": G.pol_to_list(b), "plate": G.pol_to_list(p)})
        if hb:                                               # anillo alrededor de patios interiores
            res["blocks"][-1].update(holes=[G.pol_to_list(h) for h in hb], plate_holes=[G.pol_to_list(h) for h in hp])
    huellas = [b for b, _ in bloques]
    res["patios"] = [G.pol_to_list(p) for p in partes]
    res["patios_auto"] = auto
    res["metrics"] = {"plate_area": round(gfa_plate, 1), "gfa": round(fp_area * len(stories), 1), "stories": len(stories)}
    if partes:
        res["metrics"]["blocks"] = len(bloques)
        res["metrics"]["patio_area"] = round(sum(abs(G.area(p)) for p in partes), 1)
    progs = {}
    for st in stories:
        d = progs.setdefault(st["program"], {"stories": 0, "gfa": 0.0, "nia": 0.0, "nsa": 0.0, "levels": []})
        d["stories"] += 1
        d["gfa"] += fp_area
        d["nia"] += gfa_plate
        d["levels"].append(st["index"])
    for d in progs.values():
        d["gfa"], d["nia"] = round(d["gfa"], 1), round(d["nia"], 1)
    res["metrics"]["programs"] = progs
    res["metrics"]["core"] = core_m
    if stage == "massing" or not plantas:
        return res
    W = lambda pc, pl: G.pol_to_list(G.to_world(pl, pc["origin"], pc["angle"]))
    manual = params.get("cores_mode") == "manual"
    res["corridors"], res["cores"], res["dark_zones"] = [], [], []
    bloques_pc = []                                          # por bloque: (piezas, parámetros, planta, núcleos)
    emax = 0.0
    for bi, (pl_b, ph_b) in enumerate(plantas):
        pb = dict(params)
        mapa = None
        if len(plantas) > 1:
            pb["core_count"] = 1                             # cada bloque, al menos un núcleo propio
            if manual:
                mapa = [k for k, c in enumerate(params.get("cores") or []) if _block_of(c, huellas) == bi]
                pb["cores"] = [params["cores"][k] for k in mapa]
            if params.get("centerlines"):
                pb["centerlines"] = [l for l in params["centerlines"] if _block_of_line(l, huellas) == bi] or None
        if ph_b:                                             # anillo: alas alrededor del patio y pasillo que da la vuelta
            pb["_huecos"] = ph_b
            if pb.get("centerlines") or pb.get("centerline"):
                res["warnings"].append("Bloque %d: con un patio interior, el pasillo se traza solo alrededor del patio; "
                                       "las polilíneas dibujadas todavía no se usan ahí" % (bi + 1))
                pb["centerlines"] = pb["centerline"] = None
        if is_between(pl_b, pb) and not manual:
            pb["_cw_base"] = pb["corridor_width"]
            pb["corridor_width"] = max(pb["corridor_width"], pb["core_depth"] - pb["corridor_width"])
            res["metrics"]["between"] = True
        cw_b = pb["corridor_width"]
        pieces = generate_circulation(pl_b, pb)
        if "frame" not in res:
            p0 = pieces[0]
            res["frame"] = {"origin": [round(p0["origin"][0], 4), round(p0["origin"][1], 4)],
                            "angle": round(p0["angle"], 6), "xa": p0["xa"], "xb": p0["xb"]}
        cpolys = []
        for pc in pieces:
            if pc["corridor_local"]:
                res["corridors"].append(W(pc, pc["corridor_local"]))
            for ext in pc["corridor_ext"]:
                res["corridors"].append(G.pol_to_list(ext))
            for c in pc["cores"]:
                if c["poly_local"]:
                    cen = G.to_world([G.centroid(c["poly_local"])], pc["origin"], pc["angle"])[0]
                    if c.get("between"):
                        parts = PR.core_parts(c["box"], 1, -(c["box"][3] - c["box"][1]), S["nucleo"], floor_h, n_elev)
                    else:
                        parts = PR.core_parts(c["box"], c["side"], cw_b, S["nucleo"], floor_h, n_elev)
                    spec = c.get("spec")
                    if mapa is not None and spec is not None:
                        spec = mapa[spec]
                    res["cores"].append({"poly": W(pc, c["poly_local"]), "x": round(c["x"], 3), "side": c["side"],
                                         "center": [round(cen[0], 3), round(cen[1], 3)], "spec": spec,
                                         "parts": [{"kind": p_["kind"], "name": p_["name"], "poly": W(pc, p_["poly"]),
                                                    "lines": [W(pc, ln) for ln in p_["lines"]]} for p_ in parts]})
                    cpolys.append(res["cores"][-1]["poly"])
        if len(plantas) > 1 and not cpolys:
            res["warnings"].append("El bloque %d no tiene núcleo: añade uno (en modo manual cada bloque necesita el suyo)" % (bi + 1))
        res["dark_zones"] += [G.pol_to_list(d_) for pc in pieces for d_ in pc.get("dark", [])]
        for i, pc in enumerate(pieces):
            n = max(2, int((pc["xb"] - pc["xa"])))
            for k in range(n + 1):
                emax = max(emax, egress_at(pieces, i, pc["xa"] + (pc["xb"] - pc["xa"]) * k / n))
        pb["_neta"] = neta((pl_b, ph_b))
        bloques_pc.append((pieces, pb, pl_b, cpolys))
    res["metrics"]["wings"] = sum(len(b[0]) for b in bloques_pc)
    if res["dark_zones"]:
        dz_area = sum(abs(G.area(d_)) for d_ in res["dark_zones"])
        res["warnings"].append("Zona central sin luz natural (%.0f m² por planta): entre medianeras solo los frentes "
                               "iluminan; hacen falta patios de aire y luz" % dz_area)
        res["metrics"]["dark_area"] = round(dz_area, 1)
    res["metrics"]["core_count"] = len(res["cores"])
    res["metrics"]["egress_max"] = round(emax, 1)
    if emax > params["egress_multi"]:
        res["warnings"].append("Hay puntos del pasillo a %.1f m de un núcleo (> %.0f m permitidos)" %
                               (emax, params["egress_multi"]))
    # ---- programas no residenciales (misma posición de núcleos en todos los niveles)
    layouts = {}
    for prog in sorted({s_["program"] for s_ in stories}):
        if prog in ("Office", "Retail", "Amenities"):
            P_ = S["oficinas"] if prog == "Office" else S["comercial"]
            acc = None
            for pieces, pb, pl_b, cpolys in bloques_pc:
                fp_ = PR.free_plan(pieces, pb["_neta"], sum(abs(G.area(c)) for c in cpolys), pb["corridor_width"], P_)
                if fp_:
                    if acc is None:
                        acc = {"kind": "free", "workers": 0, "wc": 0, "free_area": 0.0, "bath_area": 0.0,
                               "hall_area": 0.0, "shapes": []}
                    for k in ("workers", "wc", "free_area", "bath_area", "hall_area"):
                        acc[k] += fp_[k]
                    acc["shapes"] += [{"kind": sh["kind"], "name": sh["name"], "poly": W(sh["pc"], sh["poly"])}
                                      for sh in fp_["shapes"]]
            if acc:
                layouts[prog] = acc
                d = res["metrics"]["programs"].get(prog)
                if d:
                    d["free_area"] = round(acc["free_area"] * d["stories"], 1)
                    d["workers"] = acc["workers"] * d["stories"]
        elif prog == "Parking":
            acc = {"kind": "parking", "count": 0, "stalls": [], "aisles": []}
            for pieces, pb, pl_b, cpolys in bloques_pc:
                huecos = pb.get("_huecos") or []
                pk = PR.parking(pl_b, cpolys + huecos, S["estacionamiento"])      # sin plazas en los patios
                acc["count"] += pk["count"]
                acc["stalls"] += [G.pol_to_list(p_) for p_ in pk["stalls"]]
                acc["aisles"] += [G.pol_to_list(o) for p_ in pk["aisles"]
                                  for o, _ in (G.subtract(p_, huecos)[0] if huecos else [(p_, [])])]
            layouts[prog] = acc
            d = res["metrics"]["programs"].get(prog)
            if d:
                d["stalls"] = acc["count"] * d["stories"]
    res["program_layouts"] = layouts
    if stage == "corridor":
        return res
    state = {}
    units = []
    for pieces, pb, pl_b, _ in bloques_pc:
        for i, pc in enumerate(pieces):
            us, warns = generate_unit_mix(pc, pb, state)
            res["warnings"] += warns
            for u in us:
                u["_pc"], u["_pb"], u["_plate"] = pc, pb, pl_b
                u["egress"] = egress_at(pieces, i, (u["x0"] + u["x1"]) / 2.0) + pc.get("egress_extra", {}).get(u["side"], 0.0)
            units += us
    for i, u in enumerate(units):
        u["id"] = "U%02d" % (i + 1)
        if u["target"] and abs(u["area"] - u["target"]) > 0.35 * u["target"]:
            res["warnings"].append("%s mide %.0f m² y el objetivo de «%s» es %.0f m²: la geometría no permite ajustarlo" %
                                   (u["id"], u["area"], u["type"], u["target"]))
    mm = metrics_mix(units, params)
    res["metrics"].update({"mix": mm})
    served = sum(u["area"] for u in units)
    res["metrics"]["efficiency"] = round(served / gfa_plate * 100, 1) if gfa_plate else 0
    res["units"] = []
    for u in units:
        pc = u["_pc"]
        eg = u["egress"]
        status = "ok" if eg <= params["egress_single"] else ("multi" if eg <= params["egress_multi"] else "fail")
        item = {"id": u["id"], "type": u["type"], "area": round(u["area"], 1), "target": u["target"],
                "width": round(u["width"], 2), "depth": round(u["depth"], 2), "egress": round(eg, 1),
                "egress_status": status, "poly": W(pc, u["poly_local"]),
                "door": [round(v, 3) for v in G.to_world([u["door_local"]], pc["origin"], pc["angle"])[0]]}
        if stage == "plans":
            pl = unit_rooms(u, u["_pb"], pc, u["_plate"])
            Wp = lambda pt, pc=pc: [round(v, 3) for v in G.to_world([pt], pc["origin"], pc["angle"])[0]]
            item["bedrooms"] = pl["bedrooms"]
            item["rooms"] = [{"id": r["id"], "name": r["name"], "kind": r["kind"], "area": round(r["area"], 1),
                              "poly": W(pc, r["poly_local"])} for r in pl["rooms"]]
            item["doors"] = [{"p": Wp(d["p"]), "q": Wp(d["q"]), "entry": bool(d.get("entry")),
                              "a": d["a"], "b": d["b"]} for d in pl["doors"]]
            item["graph"] = {"nodes": [{"id": n["id"], "name": n["name"], "kind": n["kind"], "pos": Wp(n["pos"])}
                                       for n in pl["graph"]["nodes"]], "edges": pl["graph"]["edges"]}
            item["checks"] = pl["checks"]
            item["plan_score"] = pl["score"]
            item["facade"], item["facade_min"] = pl["facade"], pl["facade_min"]
        res["units"].append(item)
    if stage == "plans" and res["units"]:
        res["metrics"]["plan_score"] = round(sum(u["plan_score"] for u in res["units"]) / len(res["units"]))
        bad = [u["id"] for u in res["units"] if u["plan_score"] < 100]
        if bad:
            res["warnings"].append("Planos con observaciones en: %s (clic en la unidad para ver el detalle)" % ", ".join(bad[:10]))
    _A = lambda ps: sum(abs(G.area(p)) for p in ps)
    used = _A(res["corridors"]) + _A([c["poly"] for c in res["cores"]]) + _A([u["poly"] for u in res["units"]])
    res["metrics"]["unused_area"] = round(max(0.0, gfa_plate - used - res["metrics"].get("dark_area", 0.0)), 1)
    res["metrics"]["circulation_pct"] = round((_A(res["corridors"]) + _A([c["poly"] for c in res["cores"]])) / gfa_plate * 100, 1) if gfa_plate else 0
    n_res = sum(1 for s_ in stories if s_["program"] == "Residential")
    if "Residential" in res["metrics"]["programs"]:
        res["metrics"]["programs"]["Residential"]["nsa"] = round(mm["nsa"] * n_res, 1)
    res["metrics"]["nsa_total"] = round(mm["nsa"] * n_res, 1)
    res["metrics"]["efficiency_total"] = round(res["metrics"]["nsa_total"] / res["metrics"]["gfa"] * 100, 1) \
        if res["metrics"]["gfa"] else 0
    res["metrics"]["units_total"] = mm["count"] * n_res
    served_ratio = served / gfa_plate if gfa_plate else 0
    if served_ratio < 0.55:
        res["warnings"].append("Solo el %.0f%% de la planta está servido por el pasillo. "
                               "Dibuja una línea central que cubra mejor la planta." % (served_ratio * 100))
    return res
