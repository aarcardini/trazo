"""Viviendas: tramos laterales libres, reparto del mix en unidades, métricas del mix y planos de cada unidad
(engine/plans.py). Parte del motor (ver engine/layout.py)."""
import math
from . import geometry as G
from . import plans as P
from . import standards as ST
from .massing import _dist_to_boundary


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
        otros = list(circ.get("extra_blocks", {}).get(side, []))
        for c in circ["cores"]:
            if c["side"] == side:
                b = c["box"]
                blocks.append((b[0], b[2]))
                if side > 0:
                    pk = G.clip_rect(loc, b[0], b[2], b[3] + pw / 2, None)
                else:
                    pk = G.clip_rect(loc, b[0], b[2], None, b[1] - pw / 2)
                # sin bolsillo si detrás del núcleo hay otro bloqueo (el pasillo de otra línea que llega, otro núcleo)
                if pk and abs(G.area(pk)) >= 6 and _is_rect(pk) and \
                        not any(o0 < b[2] - 0.05 and o1 > b[0] + 0.05 for o0, o1 in otros):
                    pockets.append((b[0], b[2], pk))
        blocks += otros
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
        for a, b, region in [(a, b, r) for a, b in ivs for r in G.clip_rect_parts(loc, a, b, y0, y1)]:
            if not region or abs(G.area(region)) <= 4:       # un corte que separa la planta da varias franjas
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
            poly = G.largest_part(G.clip_rect(region, xs0, xe))      # una unidad es una sola figura
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


def sin_solapes(units, pieces, nucleos, params):
    """Pasillos dibujados (R3.3): última comprobación. Una vivienda que pisa a otra anterior, un pasillo o un núcleo se
    recorta; si lo que queda es menos de la mitad, no va. Las reglas de uniones, codos y cruces ya evitan casi todos los
    solapes: esto cubre los casos que quedan (por ejemplo, tres líneas que se cruzan en un mismo punto)."""
    if not any(pc.get("user") for pc in pieces):
        return units, []
    cw = params["corridor_width"]
    W = lambda pc, pl: G.to_world(pl, pc["origin"], pc["angle"])
    fijos = [W(pc, p) for pc in pieces for p in G.split_parts(pc["corridor_local"])] + \
        [list(e) for pc in pieces for e in pc["corridor_ext"]] + [list(c) for c in nucleos]
    toca = lambda a, b: a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6
    fijos = [(G.bbox(p), p) for p in fijos if len(p) >= 3]
    out, quitadas, ya = [], 0, []
    for u in units:
        pc = u["_pc"]
        w = W(pc, u["poly_local"])
        bw = G.bbox(w)
        otros = [p for b, p in fijos + ya if toca(bw, b)]
        if otros:
            resto, dentro = G.subtract(w, otros)
            if sum(abs(G.area(o)) for parts in dentro for o in parts) > 0.05:
                partes = [o for o, _ in resto]
                mayor = max(partes, key=lambda o: abs(G.area(o))) if partes else None
                if mayor is None or abs(G.area(mayor)) < 0.5 * abs(G.area(w)):
                    quitadas += 1
                    continue
                loc = G.to_local(mayor, pc["origin"], pc["angle"])
                if (G.area(loc) > 0) != (G.area(u["poly_local"]) > 0):
                    loc = loc[::-1]                     # el mismo sentido de giro que la vivienda original
                x0, _, x1, _ = G.bbox(loc)
                ys = [p[1] for p in loc]
                u.update({"poly_local": loc, "area": abs(G.area(loc)), "x0": x0, "x1": x1, "width": x1 - x0,
                          "depth": max(ys) - min(ys), "door_local": ((x0 + x1) / 2.0, (cw / 2) * u["side"])})
                w = mayor
        ya.append((G.bbox(w), w))
        out.append(u)
    avisos = ["%d vivienda(s) no entran donde se cruzan los pasillos dibujados: revisa las líneas" % quitadas] if quitadas else []
    return out, avisos


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
