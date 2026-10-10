"""Masa: huella con retiros (medianeras), plantas por nivel y descomposición de la planta en alas rectangulares
(también con patios interiores). Parte del motor (ver engine/layout.py)."""
import math
from . import geometry as G


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
        cut = G.largest_part(G.clip_halfplane(fp, nx, ny, nx * a[0] + ny * a[1] + r))
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


def _dist_point_segment(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def _dist_to_boundary(pt, poly):
    return min(_dist_point_segment(pt, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))
