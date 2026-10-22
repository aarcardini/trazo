"""Núcleo de circulación vertical (escalera + ascensores + palier) y programas no residenciales:
oficinas / comercio (hall de acceso, batería de baños y planta libre) y estacionamiento (plazas y calles).
"""
import math
from . import geometry as G
from . import standards as ST


# ---------------------------------------------------------------- núcleo
def core_parts(box, side, cw, S, floor_h, n_elev, giro=0):
    """Piezas del núcleo en el marco local de la pieza.
    box = (x0, y0, x1, y1) del núcleo (incluye el tramo de pasillo); side = lado del pasillo (+1 / -1).
    v = profundidad desde el borde del pasillo; u = a lo largo del pasillo desde x0.
    giro 0: la escalera sube perpendicular al pasillo; giro 90: a lo largo del pasillo (R3.5)."""
    x0, y0, x1, y1 = box
    Dc = (y1 - cw / 2) if side > 0 else (-cw / 2 - y0)
    Wc = x1 - x0

    def P(u0, v0, u1, v1):
        u0, u1 = max(0.0, u0), min(Wc, u1)
        v0, v1 = max(0.0, v0), min(Dc, v1)
        if u1 - u0 < 0.05 or v1 - v0 < 0.05:
            return None
        if side > 0:
            return [(x0 + u0, cw / 2 + v0), (x0 + u1, cw / 2 + v0), (x0 + u1, cw / 2 + v1), (x0 + u0, cw / 2 + v1)]
        return [(x0 + u0, -cw / 2 - v1), (x0 + u1, -cw / 2 - v1), (x0 + u1, -cw / 2 - v0), (x0 + u0, -cw / 2 - v0)]

    def L(u0, v0, u1, v1):
        f = (lambda u, v: (x0 + u, cw / 2 + v)) if side > 0 else (lambda u, v: (x0 + u, -cw / 2 - v))
        return [f(u0, v0), f(u1, v1)]

    parts = []
    sw, sl, risers = ST.stair_box(S, floor_h, n_elev > 0)
    m, n, ojo, h = S["muro"], ST.ancho_escalera(S, n_elev > 0), S["ojo"], S["huella"]
    gira = giro == 90
    sl_eff = min(sl, Wc if gira else Dc)
    # escalera en coordenadas (a = a lo largo de los tramos, b = a través): con giro 90, a = u; si no, a = v
    Pe = (lambda a0, b0, a1, b1: P(a0, b0, a1, b1)) if gira else (lambda a0, b0, a1, b1: P(b0, a0, b1, a1))
    Le = (lambda a0, b0, a1, b1: L(a0, b0, a1, b1)) if gira else (lambda a0, b0, a1, b1: L(b0, a0, b1, a1))
    p = Pe(0, 0, sl_eff, sw)
    if p:
        lines = []
        per = int(math.ceil(risers / 2.0))
        va, vb = m + n, sl_eff - m - n                      # tramo entre meseta (pasillo) y descanso (fondo)
        k = 0
        v = va
        while v <= vb + 1e-6 and k <= per:
            lines.append(Le(v, m, v, m + n))                     # tramo 1
            lines.append(Le(v, m + n + ojo, v, m + 2 * n + ojo))  # tramo 2
            v += h
            k += 1
        lines.append(Le(va, m + n + ojo / 2, vb, m + n + ojo / 2))   # ojo de la escalera
        parts.append({"kind": "stair", "name": "Escalera (%d contrahuellas, ancho %.2f m)" % (risers, n),
                      "poly": p, "lines": lines})
        if sl > (Wc if gira else Dc) + 0.05:
            parts[-1]["name"] += " — el núcleo es angosto para la escalera" if gira else \
                " — el núcleo es poco profundo para la escalera"
    ew, ed = S["ascensor_ducto"]
    cwid, cdep = S["ascensor_cabina"]
    u0 = sl_eff if gira else sw                          # los ascensores van al lado de la escalera
    u = u0
    if n_elev:
        pal = P(u0, 0, u0 + n_elev * (ew + m), S["palier"])
        if pal:
            parts.append({"kind": "landing", "name": "Palier de ascensores", "poly": pal, "lines": []})
        for i in range(n_elev):
            ue = u0 + i * (ew + m)
            sp = P(ue, S["palier"], ue + ew, S["palier"] + ed)
            if sp:
                cu0, cv0 = ue + (ew - cwid) / 2, S["palier"] + (ed - cdep) / 2
                parts.append({"kind": "elevator", "name": "Ascensor %d (cabina %.2f x %.2f)" % (i + 1, cwid, cdep),
                              "poly": sp, "lines": [L(cu0, cv0, cu0 + cwid, cv0 + cdep), L(cu0 + cwid, cv0, cu0, cv0 + cdep)]})
        u = u0 + n_elev * (ew + m)
        dp = P(u, 0, u + S["ducto_instalaciones"], Dc)
        if dp:
            parts.append({"kind": "duct", "name": "Ducto de instalaciones", "poly": dp, "lines": []})
        u += S["ducto_instalaciones"] + m
    if Wc - u > 0.6:
        rp = P(u, 0, Wc, Dc)
        if rp:
            parts.append({"kind": "service", "name": "Depósito / instalaciones", "poly": rp, "lines": []})
    if n_elev:
        rp = P(u0, S["palier"] + ed, u0 + n_elev * (ew + m), Dc)
        if rp and abs(G.area(rp)) > 1.0:
            parts.append({"kind": "service", "name": "Sala de máquinas / depósito", "poly": rp, "lines": []})
    return parts


# ---------------------------------------------------------------- oficinas / comercio
def free_plan(pieces, plate_area, cores_area, cw, P_):
    """Hall de acceso + batería de baños junto al núcleo; el resto, planta libre.
    pieces: piezas de circulación (con sus núcleos). Devuelve formas en marco local de cada pieza."""
    cores = [(pc, c) for pc in pieces for c in pc["cores"] if c["poly_local"]]
    if not cores:
        return None
    free0 = max(0.0, plate_area - cores_area)
    workers = int(math.ceil(free0 / P_["m2_por_persona"]))
    n_bat = max(1, min(len(cores), int(math.ceil(workers / 100.0))))
    per_bat = int(math.ceil(workers / float(n_bat)))
    women = int(math.ceil(per_bat / 2.0))
    men = per_bat - women
    wc_w = ST.wc_count(women, P_["trabajadores_por_inodoro"])
    wc_m = ST.wc_count(men, P_["trabajadores_por_inodoro"])
    cub_w, cub_d = P_["cubiculo"]
    acc_w, acc_d = P_["bano_accesible"]
    depth = cub_d + P_["zona_lavabos"]
    bw_w = max(2.0, wc_w * cub_w)
    bw_m = max(2.0, wc_m * cub_w)
    bat_w = bw_w + bw_m + acc_w
    shapes = []
    total_bath = 0.0
    total_hall = 0.0
    cw0 = cw
    for k in range(n_bat):
        pc, c = cores[k]
        cw = pc.get("ancho") or cw0                     # R10.8: el ancho del pasillo de ese tramo
        bx0, by0, bx1, by1 = c["box"]
        side = c["side"]
        loc = pc["loc_plate"]
        right = bx1 + bat_w <= pc["xb"] + 1e-6
        ux0 = bx1 if right else bx0 - bat_w
        if side > 0:
            v0, v1 = cw / 2, cw / 2 + depth
        else:
            v0, v1 = -cw / 2 - depth, -cw / 2
        xs = [ux0, ux0 + bw_w, ux0 + bw_w + bw_m, ux0 + bat_w]
        names = [("Baños mujeres (%d inodoros)" % wc_w, "wc"), ("Baños hombres (%d inodoros)" % wc_m, "wc"),
                 ("Baño accesible", "wc_acc")]
        for i, (nm, kd) in enumerate(names):
            p = G.clip_rect(loc, xs[i], xs[i + 1], v0, v1)
            if p:
                shapes.append({"pc": pc, "kind": kd, "name": nm, "poly": p})
                total_bath += abs(G.area(p))
        hx0 = min(bx0, ux0) - P_["hall_extra"]
        hx1 = max(bx1, ux0 + bat_w) + P_["hall_extra"]
        hp = G.clip_rect(loc, hx0, hx1, -cw / 2, cw / 2)
        if hp:
            shapes.append({"pc": pc, "kind": "hall", "name": "Hall de acceso", "poly": hp})
            total_hall += abs(G.area(hp))
    free = max(0.0, plate_area - cores_area - total_bath - total_hall)
    return {"shapes": shapes, "workers": workers, "wc": (wc_w + wc_m + 1) * n_bat, "batteries": n_bat,
            "free_area": round(free, 1), "bath_area": round(total_bath, 1), "hall_area": round(total_hall, 1)}


# ---------------------------------------------------------------- estacionamiento
def _dominant(poly):
    best, ang = 0.0, 0.0
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L > best:
            best, ang = L, math.atan2(b[1] - a[1], b[0] - a[0])
    return ang


def _overlaps(rect_poly, polys):
    for q in polys:
        x0, y0, x1, y1 = G.bbox(rect_poly)
        p = G.clip_rect(q, x0, x1, y0, y1)
        if p and abs(G.area(p)) > 0.05:
            return True
    return False


def _parking_in_frame(plate, cores_w, ang, Pk):
    sw, sl = Pk["plaza"]
    aw = Pk["calle"]
    loc = G.to_local(plate, (0.0, 0.0), ang)
    cl = [G.to_local(c, (0.0, 0.0), ang) for c in cores_w]
    x0, y0, x1, y1 = G.bbox(loc)
    stalls, aisles = [], []
    cross = G.clip_rect(loc, x0, x0 + aw)                    # calle transversal que une las calles
    if cross:
        aisles.append(cross)
    y = y0
    rows = []
    while y + sl + aw <= y1 + 1e-6:
        if y + 2 * sl + aw <= y1 + 1e-6:
            rows += [(y, y + sl), (y + sl + aw, y + 2 * sl + aw)]
            aisles_y = (y + sl, y + sl + aw)
            y += 2 * sl + aw
        else:
            rows.append((y, y + sl))
            aisles_y = (y + sl, y + sl + aw)
            y += sl + aw
        a = G.clip_rect(loc, x0, x1, aisles_y[0], aisles_y[1])
        if a:
            aisles.append(a)
    inset = 0.02
    for (ra, rb) in rows:
        x = x0 + aw
        while x + sw <= x1 + 1e-6:
            r = [(x, ra), (x + sw, ra), (x + sw, rb), (x, rb)]
            inside = all(G.point_in_poly((px + (inset if px == x else -inset), py + (inset if py == ra else -inset)), loc)
                         for px, py in r)
            if inside and not _overlaps(r, cl):
                stalls.append(r)
            x += sw
    back = lambda pl: G.to_world(pl, (0.0, 0.0), ang)
    return [back(s) for s in stalls], [back(a) for a in aisles]


def parking(plate, cores_w, Pk):
    """Plazas de estacionamiento en peine con calles paralelas y una calle transversal de conexión.
    Prueba las dos orientaciones principales y se queda con la que da más plazas."""
    ang = _dominant(plate)
    best = None
    for a in (ang, ang + math.pi / 2):
        st, ai = _parking_in_frame(plate, cores_w, a, Pk)
        if best is None or len(st) > len(best[0]):
            best = (st, ai)
    stalls, aisles = best
    return {"stalls": stalls, "aisles": aisles, "count": len(stalls)}
