"""Geometría 2D pura (sin dependencias): polígonos simples, recortes y utilidades."""
import math

EPS = 1e-9


def area(poly):
    """Área con signo (positiva si es antihoraria). Se calcula desde el primer vértice: así es precisa también con
    coordenadas grandes (UTM), donde los productos x·y pierden decimales."""
    if not poly:
        return 0.0
    ox, oy = poly[0]
    s = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i][0] - ox, poly[i][1] - oy
        x2, y2 = poly[(i + 1) % n][0] - ox, poly[(i + 1) % n][1] - oy
        s += x1 * y2 - x2 * y1
    return s / 2.0


def ensure_ccw(poly):
    return list(poly) if area(poly) >= 0 else list(reversed(poly))


def clean(poly, tol=1e-7):
    """Quita vértices duplicados y colineales."""
    pts = []
    for p in poly:
        if not pts or math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) > tol:
            pts.append(tuple(p))
    if len(pts) > 1 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) <= tol:
        pts.pop()
    changed = True
    while changed and len(pts) > 3:
        changed = False
        n = len(pts)
        for i in range(n):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
            cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            if abs(cr) < 1e-9:
                pts.pop(i)
                changed = True
                break
    return pts


def centroid(poly):
    a = area(poly)
    if abs(a) < EPS:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    ox, oy = poly[0]                     # desde el primer vértice: preciso con coordenadas UTM
    cx = cy = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i][0] - ox, poly[i][1] - oy
        x2, y2 = poly[(i + 1) % n][0] - ox, poly[(i + 1) % n][1] - oy
        f = x1 * y2 - x2 * y1
        cx += (x1 + x2) * f
        cy += (y1 + y2) * f
    return (ox + cx / (6 * a), oy + cy / (6 * a))


def bbox(poly):
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def rotate(p, ang, origin=(0.0, 0.0)):
    c, s = math.cos(ang), math.sin(ang)
    x, y = p[0] - origin[0], p[1] - origin[1]
    return (x * c - y * s + origin[0], x * s + y * c + origin[1])


def to_local(poly, origin, ang):
    c, s = math.cos(-ang), math.sin(-ang)
    out = []
    for x, y in poly:
        dx, dy = x - origin[0], y - origin[1]
        out.append((dx * c - dy * s, dx * s + dy * c))
    return out


def to_world(poly, origin, ang):
    c, s = math.cos(ang), math.sin(ang)
    return [(x * c - y * s + origin[0], x * s + y * c + origin[1]) for x, y in poly]


def clip_halfplane(poly, nx, ny, d):
    """Conserva la parte con nx*x + ny*y >= d (Sutherland-Hodgman)."""
    out = []
    n = len(poly)
    if n == 0:
        return out
    for i in range(n):
        a = poly[i]
        b = poly[(i + 1) % n]
        da = nx * a[0] + ny * a[1] - d
        db = nx * b[0] + ny * b[1] - d
        if da >= 0:
            out.append(a)
        if (da >= 0) != (db >= 0):
            t = da / (da - db)
            out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
    return out


def clip_rect(poly, x0=None, x1=None, y0=None, y1=None):
    p = list(poly)
    if x0 is not None:
        p = clip_halfplane(p, 1, 0, x0)
    if x1 is not None:
        p = clip_halfplane(p, -1, 0, -x1)
    if y0 is not None:
        p = clip_halfplane(p, 0, 1, y0)
    if y1 is not None:
        p = clip_halfplane(p, 0, -1, -y1)
    if len(p) < 3 or abs(area(p)) < 1e-6:
        return []
    return clean(p)


def strip_area(poly, x0, x1, y0=None, y1=None):
    p = clip_rect(poly, x0, x1, y0, y1)
    return abs(area(p)) if p else 0.0


def inset(poly, dist):
    """Desfase interior por mitras (válido para polígonos simples no muy degenerados)."""
    poly = ensure_ccw(clean(poly))
    n = len(poly)
    lines = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        nx, ny = -dy / L, dx / L  # normal hacia el interior (CCW)
        lines.append(((a[0] + nx * dist, a[1] + ny * dist), (dx / L, dy / L)))
    out = []
    for i in range(n):
        p1, d1 = lines[i - 1]
        p2, d2 = lines[i]
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-9:
            out.append(p2)
            continue
        t = ((p2[0] - p1[0]) * d2[1] - (p2[1] - p1[1]) * d2[0]) / den
        out.append((p1[0] + t * d1[0], p1[1] + t * d1[1]))
    return out


def point_in_poly(pt, poly):
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xi > x:
                inside = not inside
    return inside


def line_intervals(poly, y):
    """Intervalos [x0,x1] de la recta horizontal y=const dentro del polígono."""
    xs = []
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    xs.sort()
    return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]


def line_intervals_multi(loops, y):
    """Como line_intervals, para un polígono con huecos dado como lista de contornos (exterior y huecos)."""
    xs = []
    for poly in loops:
        n = len(poly)
        for i in range(n):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % n]
            if (y1 > y) != (y2 > y):
                xs.append(x1 + (y - y1) * (x2 - x1) / (y2 - y1))
    xs.sort()
    return [(xs[i], xs[i + 1]) for i in range(0, len(xs) - 1, 2)]


def min_area_rect_angle(poly):
    """Ángulo (rad) del lado del rectángulo mínimo orientado, alineado con su eje largo."""
    pts = poly
    best = None
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        loc = [rotate(p, -ang) for p in pts]
        x0, y0, x1, y1 = bbox(loc)
        A = (x1 - x0) * (y1 - y0)
        if best is None or A < best[0] - 1e-9:
            best = (A, ang, x1 - x0, y1 - y0)
    _, ang, w, h = best
    if h > w:
        ang += math.pi / 2
    return ang


def pol_to_list(poly):
    return [[round(x, 4), round(y, 4)] for x, y in poly]


# ---------------------------------------------------------------- resta de polígonos (patios)
def _is_convex(poly):
    sgn = 0.0
    n = len(poly)
    for i in range(n):
        a, b, c = poly[i], poly[(i + 1) % n], poly[(i + 2) % n]
        cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cr) > 1e-9:
            if sgn and (cr > 0) != (sgn > 0):
                return False
            sgn = cr
    return True


def _in_tri(p, a, b, c):
    d1 = (p[0] - b[0]) * (a[1] - b[1]) - (a[0] - b[0]) * (p[1] - b[1])
    d2 = (p[0] - c[0]) * (b[1] - c[1]) - (b[0] - c[0]) * (p[1] - c[1])
    d3 = (p[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (p[1] - a[1])
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def triangulate(poly):
    """Triángulos de un polígono simple (corte de orejas)."""
    pts = ensure_ccw(clean(poly))
    out = []
    while len(pts) > 3:
        n = len(pts)
        for i in range(n):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) <= 1e-12:
                continue                                     # vértice reflejo
            if any(_in_tri(p, a, b, c) for p in pts if p not in (a, b, c)):
                continue
            out.append([a, b, c])
            pts.pop(i)
            break
        else:
            return out + [pts]                               # degenerado: se devuelve tal cual
    return out + [pts] if len(pts) == 3 else out


def _simplify(loop, tol=1e-6):
    """Quita vértices repetidos o alineados (distancia a la recta vecina < tol)."""
    pts = list(loop)
    changed = True
    while changed and len(pts) > 3:
        changed = False
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            L = math.hypot(c[0] - a[0], c[1] - a[1])
            if L < tol or abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / L < tol:
                pts.pop(i)
                changed = True
                break
    return pts


def union_parts(polys):
    """Contornos de la unión de polígonos que no se solapan (piezas de una partición): [(exterior, [huecos])].
    Las aristas compartidas se anulan entre sí, y también los puentes de ancho cero de Sutherland-Hodgman."""
    key = lambda p: (round(p[0], 6) + 0.0, round(p[1], 6) + 0.0)
    edges, verts = [], set()
    for poly in polys:
        q = []
        for p in map(key, poly):
            if not q or p != q[-1]:
                q.append(p)
        if len(q) > 1 and q[0] == q[-1]:
            q.pop()
        if len(q) < 3 or abs(area(q)) < 1e-6:
            continue
        if area(q) < 0:
            q.reverse()
        edges += [(q[i], q[(i + 1) % len(q)]) for i in range(len(q))]
        verts.update(q)
    cnt = {}
    for a, b in edges:                                       # partir aristas en los vértices que caen encima
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        if L2 < 1e-18:
            continue
        mids = []
        for p in verts:
            if p != a and p != b:
                t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2
                if 1e-9 < t < 1 - 1e-9 and abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) < 1e-6 * math.sqrt(L2):
                    mids.append((t, p))
        chain = [a] + [p for _, p in sorted(mids)] + [b]
        for e in zip(chain, chain[1:]):
            cnt[e] = cnt.get(e, 0) + 1
    for (a, b) in list(cnt):                                 # aristas opuestas (compartidas) se anulan
        k = min(cnt[(a, b)], cnt.get((b, a), 0))
        if k:
            cnt[(a, b)] -= k
            cnt[(b, a)] -= k
    nxt = {}
    for (a, b), k in cnt.items():
        if k > 0:
            nxt.setdefault(a, []).extend([b] * k)
    loops = []
    while nxt:
        start = next(iter(nxt))
        prev, cur = start, nxt[start].pop()
        if not nxt[start]:
            del nxt[start]
        loop = [start]
        while cur != start and cur in nxt:
            loop.append(cur)
            back = math.atan2(prev[1] - cur[1], prev[0] - cur[0])
            turn = lambda q: ((back - math.atan2(q[1] - cur[1], q[0] - cur[0])) % (2 * math.pi)) or 2 * math.pi
            nb = min(nxt[cur], key=turn)                     # el giro más a la derecha: la región queda a la izquierda
            nxt[cur].remove(nb)
            if not nxt[cur]:
                del nxt[cur]
            prev, cur = cur, nb
        loop = _simplify(loop)
        if len(loop) >= 3 and abs(area(loop)) > 1e-6:
            loops.append(loop)
    outers = sorted([l for l in loops if area(l) > 0], key=area)
    res = [(o, []) for o in outers]
    for h in (l for l in loops if area(l) < 0):
        for o, hs in res:                                    # el menor exterior que lo contiene
            if point_in_poly(centroid(h), o):
                hs.append(h)
                break
    res.sort(key=lambda r: -area(r[0]))
    return res


def split_parts(poly):
    """Partes de un recorte. Cuando el corte separa una figura cóncava, Sutherland-Hodgman deja las partes unidas por
    puentes de ancho cero; aquí salen por separado (lista, la mayor primero; [poly] si es una sola)."""
    if not poly or len(poly) < 3:
        return []
    if _is_convex(poly):
        return [poly]
    partes = [o for o, _ in union_parts([poly])]
    return partes if len(partes) > 1 else [poly]


def clip_halfplane_parts(poly, nx, ny, d):
    """Como clip_halfplane, pero si el corte separa la figura devuelve cada parte por separado."""
    return [p for p in split_parts(clip_halfplane(poly, nx, ny, d)) if len(p) >= 3 and abs(area(p)) > 1e-6]


def clip_rect_parts(poly, x0=None, x1=None, y0=None, y1=None):
    """Como clip_rect, pero si el recorte separa la figura devuelve cada parte por separado."""
    return split_parts(clip_rect(poly, x0, x1, y0, y1))


def largest_part(poly):
    """La mayor de las partes de un recorte (para lo que tiene que ser una sola figura: una unidad, un lote)."""
    ps = split_parts(poly)
    return max(ps, key=lambda p: abs(area(p))) if ps else poly


def subtract(poly, cutters):
    """poly menos los polígonos de cutters. Devuelve (partes de poly [(exterior, [huecos])],
    [partes de cada cutter dentro de poly]). Cada cutter se resta en piezas convexas por semiplanos."""
    pieces = [ensure_ccw(clean(poly))]
    inside = []
    for cut in cutters:
        cut = ensure_ccw(clean(cut))
        if len(cut) < 3 or abs(area(cut)) < 1e-6:
            inside.append([])
            continue
        dentro = []
        for cp in ([cut] if _is_convex(cut) else triangulate(cut)):
            new = []
            for P in pieces:
                rest = P
                for i in range(len(cp)):
                    a, b = cp[i], cp[(i + 1) % len(cp)]
                    L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
                    nx, ny = -(b[1] - a[1]) / L, (b[0] - a[0]) / L       # normal hacia adentro del cutter
                    d = nx * a[0] + ny * a[1]
                    fuera = clip_halfplane(rest, -nx, -ny, -d)
                    if len(fuera) >= 3 and abs(area(fuera)) > 1e-6:
                        new.append(fuera)
                    rest = clip_halfplane(rest, nx, ny, d)
                    if len(rest) < 3 or abs(area(rest)) < 1e-6:
                        rest = []
                        break
                if rest:
                    dentro.append(rest)
            pieces = new
        inside.append([o for o, _ in union_parts(dentro)])
    return union_parts(pieces), inside
