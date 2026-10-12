"""Masa: huella con retiros (medianeras), plantas por nivel y descomposición de la planta en alas rectangulares
(también con patios interiores). Parte del motor (ver engine/layout.py)."""
import math
from . import geometry as G


# ---------------------------------------------------------------- masa
def _inward(a, b):
    L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    return -(b[1] - a[1]) / L, (b[0] - a[0]) / L


def _en_tramo(fp, p, tol=0.1):
    """True si p cae dentro de un borde de la huella: ni en una esquina ni afuera."""
    for i in range(len(fp)):
        a, b = fp[i], fp[(i + 1) % len(fp)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 1e-9:
            continue
        t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L
        if abs((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / L <= tol and tol < t < L - tol:
            return True
    return False


def apply_setbacks(fp, meds):
    """Retira la huella r metros de cada medianera con retiro > 0. La que va de esquina a esquina corta por una paralela
    al lindero; una parcial (R11.6) retira solo a lo largo de su tramo y deja la huella escalonada (del lado de un
    extremo que llega a una esquina, el retiro sigue de largo)."""
    for m in meds or []:
        r = float(m.get("retiro") or 0)
        if r <= 0:
            continue
        a, b = m["a"], m["b"]
        nx, ny = _inward(a, b)
        c = G.centroid(fp)
        if nx * (c[0] - a[0]) + ny * (c[1] - a[1]) < 0:      # la normal debe apuntar hacia el edificio
            nx, ny = -nx, -ny
        ia, ib = _en_tramo(fp, a), _en_tramo(fp, b)
        if not (ia or ib):
            cut = G.largest_part(G.clip_halfplane(fp, nx, ny, nx * a[0] + ny * a[1] + r))
        else:                                                 # la franja de la medianera, hasta r hacia adentro
            L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
            ux, uy, lejos = (b[0] - a[0]) / L, (b[1] - a[1]) / L, 1e4
            t0, t1 = (0.0 if ia else -lejos), (L if ib else L + lejos)
            P = lambda t, s: (a[0] + ux * t + nx * s, a[1] + uy * t + ny * s)
            partes, _ = G.subtract(fp, [[P(t0, -lejos), P(t1, -lejos), P(t1, r), P(t0, r)]])
            cut = max((ext for ext, _ in partes), key=lambda q: abs(G.area(q)), default=[])
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


def decompose_wings(plate, min_side=5.0, holes=None, blind=None, candidatos=False):
    """Divide una planta ortogonal en rectángulos (alas). Devuelve (ángulo, [polígonos mundo]) o None.
    holes: patios interiores (la planta es un anillo); tienen que ser ortogonales en el mismo marco.
    blind: en un anillo, las alas a lo largo de una medianera ciega puntúan menos (sus viviendas no tienen luz).
    candidatos: devuelve las dos direcciones de corte que dejan alas, [(puntaje, ángulo, [polígonos])], de mejor a
    peor (o [] si no hay ninguna): circulation.build_pieces se queda con la que deja los pasillos unidos entre sí."""
    th = _dominant_angle(plate)
    loc = G.ensure_ccw([G.rotate(p, -th) for p in plate])
    hl = [[G.rotate(p, -th) for p in h] for h in (holes or [])]
    if not _is_rectilinear(loc) or not all(_is_rectilinear(h) for h in hl):
        return [] if candidatos else None
    opciones = []
    for vertical in (True, False):
        rects = _slabs(loc, vertical, hl)
        rects = [r for r in rects if min(G.bbox(r)[2] - G.bbox(r)[0], G.bbox(r)[3] - G.bbox(r)[1]) >= min_side]
        if not rects:
            continue
        score = sum(max(G.bbox(r)[2] - G.bbox(r)[0], G.bbox(r)[3] - G.bbox(r)[1]) for r in rects) - 8.0 * len(rects)
        if hl and blind:
            score -= sum(_lado_ciego(r, th, blind) for r in rects)
        opciones.append((score, th, [[G.rotate(p, th) for p in r] for r in rects]))
    opciones.sort(key=lambda o: -o[0])                  # estable: a igual puntaje, primero el corte vertical
    if candidatos:
        return opciones
    return (opciones[0][1], opciones[0][2]) if opciones else None


def _dir90(a, b):
    return math.atan2(b[1] - a[1], b[0] - a[0]) % (math.pi / 2)


def _dist90(a, b):
    d = abs(a - b) % (math.pi / 2)
    return min(d, math.pi / 2 - d)


def _rectificar(loc, tol=1e-6):
    """Polígono ortogonal que contiene a loc: cada borde inclinado se cambia por el escalón de afuera."""
    out = []
    n = len(loc)
    for i in range(n):
        a, b = loc[i], loc[(i + 1) % n]
        out.append(a)
        if abs(a[0] - b[0]) > tol and abs(a[1] - b[1]) > tol:
            c = (b[0], a[1])
            m = ((a[0] + b[0] + c[0]) / 3.0, (a[1] + b[1] + c[1]) / 3.0)
            out.append(c if not G.point_in_poly(m, loc) else (a[0], b[1]))
    return G.clean(out)


def _ajustar(loc, tol=1e-3):
    """Coordenadas que difieren menos de tol (un milímetro) pasan a ser iguales: sin escalones de redondeo al girar
    la planta a su marco."""
    def mapa(vals):
        m, grupo = {}, []
        for v in sorted(set(vals)):
            if grupo and v - grupo[-1] > tol:
                for w in grupo:
                    m[w] = grupo[0]
                grupo = []
            grupo.append(v)
        for w in grupo:
            m[w] = grupo[0]
        return m
    mx, my = mapa([p[0] for p in loc]), mapa([p[1] for p in loc])
    return G.clean([(mx[p[0]], my[p[1]]) for p in loc])


def _alas_en_marco(part, th, min_side):
    """Alas de una parte de la planta en el marco th: se rectifica (bordes inclinados por fuera), se divide en
    rectángulos como una planta ortogonal y cada rectángulo se recorta con la parte real."""
    loc = G.ensure_ccw([G.rotate(p, -th) for p in part])
    rl = _rectificar(_ajustar(loc))
    best = None
    for vertical in (True, False):
        rects = [r for r in _slabs(rl, vertical)
                 if min(G.bbox(r)[2] - G.bbox(r)[0], G.bbox(r)[3] - G.bbox(r)[1]) >= min_side]
        alas = []
        for r in rects:
            x0, y0, x1, y1 = G.bbox(r)
            q = G.largest_part(G.clip_rect(loc, x0, x1, y0, y1))
            if not q or abs(G.area(q)) < 10.0 or len(G.clean(q, 1e-6)) < 4:
                continue                                 # una punta en triángulo no es un ala
            alas.append((q, abs(G.area(q)) / ((x1 - x0) * (y1 - y0))))
        if not alas:
            continue
        # como en una planta ortogonal (alas largas, pocas), más la superficie de las alas casi llenas: así no gana
        # una división que deja afuera una franja, ni una que mete una punta dentro de un ala
        score = sum(max(G.bbox(q)[2] - G.bbox(q)[0], G.bbox(q)[3] - G.bbox(q)[1]) for q, _ in alas) - 8.0 * len(alas) \
            + sum(abs(G.area(q)) for q, f in alas if f >= 0.85) / 10.0
        if best is None or score > best[0]:
            best = (score, [q for q, _ in alas])
    return [[G.rotate(p, th) for p in q] for q in best[1]] if best else []


def _pureza(poly, cortes):
    """(ángulo, fracción, largo total) de la dirección dominante (módulo 90°) de los bordes de poly, sin contar las
    cuerdas de corte (cortes: conjunto de bordes, como pares de puntos redondeados)."""
    n = len(poly)
    grupos, tot = [], 0.0
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if _clave(a, b) in cortes:
            continue
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        ang = _dir90(a, b)
        tot += L
        g = next((g for g in grupos if _dist90(g[0], ang) < math.radians(3)), None)
        if g:
            g[1] += L
            if L > g[2]:
                g[0], g[2] = ang, L                      # el ángulo del grupo es el de su borde más largo
        else:
            grupos.append([ang, L, L])
    if not grupos or tot <= 0:
        return 0.0, 0.0, 0.0
    g = max(grupos, key=lambda g: g[1])
    return g[0], g[1] / tot, tot


def _clave(a, b):
    k = lambda p: (round(p[0], 4), round(p[1], 4))
    return frozenset((k(a), k(b)))


def _paralelos(poly, cortes, th, min_side):
    """¿Tiene la parte dos bordes largos paralelos en la dirección th (los lados de un ala)?"""
    n = len(poly)
    dirs = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        if _clave(a, b) in cortes or math.hypot(b[0] - a[0], b[1] - a[1]) < min_side:
            continue
        if _dist90(_dir90(a, b), th) < math.radians(3):
            dirs.append(math.atan2(b[1] - a[1], b[0] - a[0]) % math.pi)
    return any(min(abs(u - v) % math.pi, math.pi - abs(u - v) % math.pi) < math.radians(3)
               for i, u in enumerate(dirs) for v in dirs[i + 1:])


def _partir(poly, cortes, min_side, prof=0):
    """Divide la planta por cuerdas desde un vértice entrante mientras las partes queden con distinta dirección
    dominante y cada una más «pura» (más borde en una sola dirección): un ala girada, el tallo oblicuo de una T.
    Devuelve [(parte, ángulo)]."""
    th, pur, _ = _pureza(poly, cortes)
    n = len(poly)
    if pur >= 0.9 or prof > 4 or n < 5:
        return [(poly, th)]
    cruz = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    reflex = [i for i in range(n) if cruz(poly[i - 1], poly[i], poly[(i + 1) % n]) < -1e-9]
    best = None
    for r in reflex:
        for v in range(n):
            if v in (r, (r - 1) % n, (r + 1) % n):
                continue
            a, b = poly[r], poly[v]
            m = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
            if not G.point_in_poly(m, poly):
                continue
            cruza = False
            for j in range(n):
                if j in (r, (r - 1) % n, v, (v - 1) % n):
                    continue
                tu = G.seg_intersection(a, b, poly[j], poly[(j + 1) % n])
                if tu and 1e-6 < tu[0] < 1 - 1e-6:
                    cruza = True
                    break
            if cruza:
                continue
            p1 = [poly[(r + k) % n] for k in range((v - r) % n + 1)]
            p2 = [poly[(v + k) % n] for k in range((r - v) % n + 1)]
            if min(abs(G.area(p1)), abs(G.area(p2))) < 4 * min_side * min_side:
                continue
            c2 = cortes | {_clave(a, b)}
            t1, u1, l1 = _pureza(p1, c2)
            t2, u2, l2 = _pureza(p2, c2)
            if _dist90(t1, t2) < math.radians(3):
                continue                                 # mismo marco: lo resuelve la división ortogonal
            if not (_paralelos(p1, c2, t1, min_side) and _paralelos(p2, c2, t2, min_side)):
                continue                                 # cada parte, un ala: dos lados largos paralelos (no una punta)
            peso = (u1 * l1 + u2 * l2) / ((l1 + l2) or 1.0)
            if best is None or peso > best[0]:
                best = (peso, p1, p2, c2)
    if best is None or best[0] < pur + 0.05:
        return [(poly, th)]
    return _partir(best[1], best[3], min_side, prof + 1) + _partir(best[2], best[3], min_side, prof + 1)


def descomponer_alas(plate, min_side=5.0):
    """Planta no ortogonal (R3.4): [(polígono del ala, ángulo de su marco)] o None.
    Un brazo con otra dirección (un ala girada, el tallo oblicuo de una T) se separa por una cuerda desde un vértice
    entrante, y cada parte se divide en alas en su propio marco: se rectifica (los bordes inclinados por fuera, como
    una ochava) y se recorta con la planta real. Una planta convexa no se divide (un solo pasillo, como antes)."""
    poly = G.ensure_ccw(G.clean([tuple(p) for p in plate]))
    n = len(poly)
    cruz = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    if n < 5 or not any(cruz(poly[i - 1], poly[i], poly[(i + 1) % n]) < -1e-9 for i in range(n)):
        return None
    partes = _partir(poly, frozenset(), min_side)
    alas = [(q, th) for p, th in partes for q in _alas_en_marco(p, th, min_side)]
    if not alas or sum(abs(G.area(q)) for q, _ in alas) < 0.85 * abs(G.area(poly)):
        return None
    return alas


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
