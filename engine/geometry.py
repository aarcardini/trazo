"""Geometría 2D pura (sin dependencias): polígonos simples, recortes y utilidades."""
import math

EPS = 1e-9


def area(poly):
    """Área con signo (positiva si es antihoraria)."""
    s = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
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
    cx = cy = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        f = x1 * y2 - x2 * y1
        cx += (x1 + x2) * f
        cy += (y1 + y2) * f
    return (cx / (6 * a), cy / (6 * a))


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
