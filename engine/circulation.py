"""Pasillo y núcleos: piezas (tramos de pasillo con su marco local), uniones, núcleos, evacuación y el caso entre
medianeras. Parte del motor (ver engine/layout.py)."""
import math
from . import geometry as G
from . import plans as P
from .massing import _dist_point_segment, _dist_to_boundary, decompose_wings


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


BOLSILLO = 4.5     # fondo detrás de un núcleo por debajo del cual no cabe una unidad útil: el núcleo llega a la fachada


def _punta(pc, e, x, side, params):
    """Núcleo en una punta libre (R3.1). Si entre el núcleo y el borde de la planta queda una franja demasiado chica
    para una vivienda (por ejemplo, una polilínea que termina antes de la fachada), el núcleo se apoya contra el borde:
    esa franja ya no queda suelta y la vivienda del otro lado del núcleo crece en su lugar. Solo si el núcleo llega a la
    fachada: si detrás le queda un bolsillo, la franja y el bolsillo ya forman una vivienda."""
    cw, pw, d, half = params["corridor_width"], params["party_wall"], params["core_depth"], params["core_width"] / 2.0
    y0, y1 = (-cw / 2, -cw / 2 + d) if side > 0 else (cw / 2 - d, cw / 2)
    banda = G.clip_rect(pc["loc_plate"], None, None, y0, y1)
    detras = G.clip_rect(pc["loc_plate"], x - half, x + half)
    if not banda or not detras:
        return x
    ys = [p[1] for p in detras]
    if (max(ys) - y1 if side > 0 else y0 - min(ys)) >= BOLSILLO:
        return x
    bx0, _, bx1, _ = G.bbox(banda)
    resto = bx1 - (x + half) if e == 1 else (x - half) - bx0
    if resto <= 0.05:
        return x
    franja = G.clip_rect(pc["loc_plate"], x + half if e == 1 else None, None if e == 1 else x - half,
                         cw / 2 + pw / 2 if side > 0 else None, None if side > 0 else -cw / 2 - pw / 2)
    mix = [m["area"] for m in params["unit_mix"] if m.get("percent", 0) > 0 and m.get("area", 0) > 0] or [1e9]
    if resto < 0.6 * params["min_unit_width"] or abs(G.area(franja or [(0, 0)] * 3)) < 0.4 * min(mix):
        return x + resto if e == 1 else x - resto
    return x


def _add_core(pc, x, side, params):
    cw, w, d = params["corridor_width"], params["core_width"], params["core_depth"]
    if side > 0:
        box = (x - w / 2, -cw / 2, x + w / 2, -cw / 2 + d)
    else:
        box = (x - w / 2, cw / 2 - d, x + w / 2, cw / 2)
    strip = G.clip_rect(pc["loc_plate"], box[0], box[2])
    if strip:
        ys = [p[1] for p in strip]
        pocket = BOLSILLO
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
                pc["cores"][-1]["punta"] = e

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
    # R3.1: un núcleo de punta que deja una franja suelta hasta la fachada se apoya contra ella, si la evacuación
    # sigue dentro del máximo (si no, queda donde estaba)
    for pc in pieces:
        for k, c in enumerate(pc["cores"]):
            if c.get("punta") is None:
                continue
            x2 = _punta(pc, c["punta"], c["x"], c["side"], params)
            if abs(x2 - c["x"]) < 1e-9:
                continue
            _add_core(pc, x2, c["side"], params)
            pc["cores"][k] = pc["cores"].pop()
            if worst()[0] > max(params["egress_multi"], v):
                pc["cores"][k] = c
    return pieces
