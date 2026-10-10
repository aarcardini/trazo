"""Modo Masterplan: predio -> calles (calzada + veredas) -> manzanas (con ochavas) -> lotes -> construcciones.

Modelo (v1):
- Las calles son tramos rectos (las polilíneas se toman tramo a tramo). Un tramo parte una manzana solo si la
  atraviesa de lado a lado: los quiebres deben hacerse en un cruce con otra calle o en el borde del predio.
  Los cruces en T funcionan naturalmente (el ramal termina en el eje de la calle principal).
- Los bordes del predio marcados como «calle existente» cuentan como frente (sin ocupar suelo del predio).
- Lotes: cada manzana se divide en una o dos filas según su fondo; cada fila en lotes por frente con un mix.
- Construcción por lote: retiros frontal / lateral / fondo y FOS; altura = pisos x altura de piso.
"""
import math
from . import geometry as G
from . import standards as ST


def _seg_frame(a, b):
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    return ang, L


def _segments(streets, S):
    """Tramos rectos de todas las calles con su perfil."""
    out = []
    for k, st in enumerate(streets or []):
        pts = [tuple(p) for p in st.get("pts", [])]
        cz = float(st.get("calzada") or S["calzada"])
        vd = float(st.get("vereda") if st.get("vereda") is not None else S["vereda"])
        for a, b in zip(pts, pts[1:]):
            ang, L = _seg_frame(a, b)
            if L < 0.5:
                continue
            out.append({"street": k, "a": a, "b": b, "ang": ang, "L": L, "calzada": cz, "vereda": vd,
                        "half": cz / 2.0 + vd})
    return out


def _spans(piece, sg, ext=0.6):
    """El tramo atraviesa la pieza de lado a lado (cubre por completo algún intervalo de la recta)."""
    loc = G.to_local(piece, sg["a"], sg["ang"])
    hit = False
    for x0, x1 in G.line_intervals(loc, 0.0):
        if x1 - x0 < 0.05:
            continue
        if x0 >= -ext and x1 <= sg["L"] + ext:
            return True, True
        if x1 > -ext and x0 < sg["L"] + ext:
            hit = True
    return False, hit


def _split(pieces, sg, warnings):
    out = []
    n = (-math.sin(sg["ang"]), math.cos(sg["ang"]))
    d = n[0] * sg["a"][0] + n[1] * sg["a"][1]
    h = sg["half"]
    for pc in pieces:
        full, hit = _spans(pc, sg)
        if not full:
            if hit:
                warnings.append("Calle %d: un tramo termina dentro de una manzana (calle sin salida o quiebre a mitad "
                                "de manzana); dibuja cada tramo hasta un cruce o hasta el borde del predio" % (sg["street"] + 1))
            out.append(pc)
            continue
        for nx, ny, dd in ((n[0], n[1], d + h), (-n[0], -n[1], -d + h)):
            for p in G.clip_halfplane_parts(pc, nx, ny, dd):     # en un predio cóncavo, una calle puede dejar varias
                p = G.clean(p)
                if len(p) >= 3 and abs(G.area(p)) > 1.0:
                    out.append(G.ensure_ccw(p))
    return out


def _band(sg, half, predio):
    """Rectángulo de la calle (o de su calzada) recortado al predio."""
    L = sg["L"]
    rect = [(0, -half), (L, -half), (L, half), (0, half)]
    w = G.to_world(rect, sg["a"], sg["ang"])
    p = list(predio)
    for i in range(4):
        a, b = w[i], w[(i + 1) % 4]
        nx, ny = -(b[1] - a[1]), (b[0] - a[0])
        Ln = math.hypot(nx, ny) or 1.0
        nx, ny = nx / Ln, ny / Ln
        if nx * (w[(i + 2) % 4][0] - a[0]) + ny * (w[(i + 2) % 4][1] - a[1]) < 0:
            nx, ny = -nx, -ny
        p = G.clip_halfplane(p, nx, ny, nx * a[0] + ny * a[1])
        if len(p) < 3:
            return []
    return G.clean(p) if abs(G.area(p)) > 0.5 else []


def _dist_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy or 1.0
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def _street_facing(p, q, segs, frontage_edges):
    """¿El borde p-q de una manzana da a una calle (nueva o existente)?"""
    m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
    for sg in segs:
        ang, a = sg["ang"], sg["a"]
        lx, ly = G.to_local([m], a, ang)[0]
        if -sg["half"] - 1 <= lx <= sg["L"] + sg["half"] + 1 and abs(abs(ly) - sg["half"]) < 0.35:
            return True
    for a, b in frontage_edges:
        if _dist_seg(m, a, b) < 0.35:
            return True
    return False


def _chamfer(poly, segs, frontage_edges, c):
    """Ochavas: corta las esquinas convexas donde los dos lados dan a calle."""
    if c <= 0:
        return poly
    poly = G.ensure_ccw(poly)
    n = len(poly)
    flags = [_street_facing(poly[i], poly[(i + 1) % n], segs, frontage_edges) for i in range(n)]
    out = poly
    for i in range(n):
        prev_e, next_e = flags[i - 1], flags[i]
        if not (prev_e and next_e):
            continue
        v = poly[i]
        a, b = poly[i - 1], poly[(i + 1) % n]
        cross = (v[0] - a[0]) * (b[1] - v[1]) - (v[1] - a[1]) * (b[0] - v[0])
        if cross <= 0:                       # esquina cóncava
            continue
        u1 = ((a[0] - v[0]), (a[1] - v[1]))
        u2 = ((b[0] - v[0]), (b[1] - v[1]))
        l1, l2 = math.hypot(*u1), math.hypot(*u2)
        if l1 < 2 * c or l2 < 2 * c:
            continue
        p1 = (v[0] + u1[0] / l1 * c, v[1] + u1[1] / l1 * c)
        p2 = (v[0] + u2[0] / l2 * c, v[1] + u2[1] / l2 * c)
        nx, ny = -(p2[1] - p1[1]), (p2[0] - p1[0])
        cx, cy = G.centroid(poly)
        if nx * (cx - p1[0]) + ny * (cy - p1[1]) < 0:
            nx, ny = -nx, -ny
        out = G.largest_part(G.clip_halfplane(out, nx, ny, nx * p1[0] + ny * p1[1]))
    return G.ensure_ccw(G.clean(out))


def damero(predio, S, angle=None):
    """Trazado automático en damero: calles paralelas a los lados principales del predio."""
    poly = G.ensure_ccw(G.clean([tuple(p) for p in predio]))
    if angle is None:
        best, angle = 0.0, 0.0
        for i in range(len(poly)):
            a, b = poly[i], poly[(i + 1) % len(poly)]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L > best:
                best, angle = L, math.atan2(b[1] - a[1], b[0] - a[0])
    loc = G.to_local(poly, (0.0, 0.0), angle)
    x0, y0, x1, y1 = G.bbox(loc)
    W, Lm = S["manzana"]
    sw = S["calzada"] + 2 * S["vereda"]
    streets = []
    x = x0 + Lm + sw / 2
    while x < x1 - Lm * 0.4:
        streets.append([(x, y0 - 2), (x, y1 + 2)])
        x += Lm + sw
    y = y0 + W + sw / 2
    while y < y1 - W * 0.4:
        streets.append([(x0 - 2, y), (x1 + 2, y)])
        y += W + sw
    return [{"pts": [list(p) for p in G.to_world(s, (0.0, 0.0), angle)], "calzada": S["calzada"],
             "vereda": S["vereda"]} for s in streets]


def _lots_for_block(block, segs, frontage_edges, S, mix, state):
    """Lotes por frente. Devuelve lista de lotes (polígono, frente, fondo, esquina) en coordenadas de mundo."""
    n = len(block)
    edges = [(block[i], block[(i + 1) % n]) for i in range(n)]
    st_edges = [(p, q) for p, q in edges if _street_facing(p, q, segs, frontage_edges)]
    if not st_edges:
        return [], ["Manzana sin frente a calle: no se lotea"]
    p, q = max(st_edges, key=lambda e: math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1]))
    ang = math.atan2(q[1] - p[1], q[0] - p[0])
    loc = G.to_local(block, (0.0, 0.0), ang)
    x0, y0, x1, y1 = G.bbox(loc)
    D = y1 - y0

    # clasifica los bordes con calle según su dirección respecto del frente principal (tolera bordes inclinados)
    bottom = top = end_left = end_right = False
    for a, b in st_edges:
        la, lb = G.to_local([a, b], (0.0, 0.0), ang)
        dx, dy = lb[0] - la[0], lb[1] - la[1]
        L = math.hypot(dx, dy) or 1.0
        my, mx = (la[1] + lb[1]) / 2, (la[0] + lb[0]) / 2
        if abs(dy) / L < 0.42:                      # paralelo al frente (±25°)
            if my < y0 + D / 2:
                bottom = True
            else:
                top = True
        elif abs(dx) / L < 0.42:                    # perpendicular: extremo de manzana (esquina)
            if mx < (x0 + x1) / 2:
                end_left = True
            else:
                end_right = True
    if bottom and top and D >= 2 * S["fondo_min"]:
        rows = [(y0, y0 + D / 2, "bottom"), (y0 + D / 2, y1, "top")]
    elif top and not bottom:
        rows = [(y0, y1, "top")]
    else:
        rows = [(y0, y1, "bottom")]
    tot = sum(m["percent"] for m in mix) or 1.0
    avg_w = sum(m["percent"] / tot * m["frente"] for m in mix)
    lots = []
    for ra, rb, face, row in [(ra, rb, f, r) for ra, rb, f in rows for r in G.clip_rect_parts(loc, None, None, ra, rb)]:
        if not row:                                         # manzana cóncava: cada parte de la fila por separado
            continue
        rx0, _, rx1, _ = G.bbox(row)
        Lr = rx1 - rx0
        # cantidad de lotes: la mayor que entra sin bajar los frentes del mix (los lotes nunca se achican)
        seq, placed, cnt = [], dict(state["placed"]), state["n"]
        used = 0.0
        while True:
            m = max(mix, key=lambda t: t["percent"] / tot * (cnt + 1) - placed[t["name"]])
            if used + m["frente"] > Lr + 1e-6 and seq:
                break
            seq.append(m)
            placed[m["name"]] += 1
            cnt += 1
            used += m["frente"]
            if used > Lr:
                break
        for m in seq:
            state["placed"][m["name"]] += 1
            state["n"] += 1
        sc = Lr / sum(m["frente"] for m in seq)
        cuts, x = [rx0], rx0
        for m in seq[:-1]:
            x += m["frente"] * sc
            cuts.append(x)
        cuts.append(rx1)
        types = [m["name"] for m in seq]
        # lotes de borde que no llegan al área mínima (bordes inclinados): se funden con el vecino
        while len(types) > 1:
            areas = [abs(G.area(G.clip_rect(row, cuts[i], cuts[i + 1]) or [(0, 0)] * 3)) for i in range(len(types))]
            bad = [i for i, a in enumerate(areas) if a + 1e-6 < S["lote_area_min"]]
            if not bad:
                break
            i = bad[0]
            j = i - 1 if i > 0 and (i == len(types) - 1 or areas[i - 1] <= areas[i + 1]) else i + 1
            state["placed"][types[i]] -= 1
            state["n"] -= 1
            del types[i]
            del cuts[max(i, j)]
        for i, t in enumerate(types):
            x, xe = cuts[i], cuts[i + 1]
            lp = G.largest_part(G.clip_rect(row, x, xe))
            if lp and abs(G.area(lp)) > 5:
                corner = (i == 0 and end_left) or (i == len(types) - 1 and end_right)
                lots.append({"type": t, "local": lp, "ang": ang, "x0": x, "x1": xe, "ya": ra, "yb": rb,
                             "face": face, "frente": xe - x, "fondo": rb - ra, "corner": corner,
                             "corner_side": ("left" if i == 0 and end_left else "right" if corner else None)})
    return lots, []


def _building(lot, S):
    """Huella edificable del lote: retiros + FOS. Devuelve (polígono local, medianeras locales)."""
    x0, x1, ya, yb = lot["x0"], lot["x1"], lot["ya"], lot["yb"]
    rf, rl = S["retiro_frontal"], S["retiro_lateral"]
    rb = S["retiro_fondo_pct"] / 100.0 * (yb - ya)
    if lot["face"] == "bottom":
        fy0, fy1 = ya + rf, yb - rb
    else:
        fy0, fy1 = ya + rb, yb - rf
    lx0 = x0 + (rf if lot["corner_side"] == "left" else rl)
    lx1 = x1 - (rf if lot["corner_side"] == "right" else rl)
    if fy1 - fy0 < 3 or lx1 - lx0 < 3:
        return None, []
    area_lot = abs(G.area(lot["local"]))
    cap = S["fos"] / 100.0 * area_lot
    fp = G.largest_part(G.clip_rect(lot["local"], lx0, lx1, fy0, fy1))
    if not fp:
        return None, []
    if abs(G.area(fp)) > cap:
        need = cap / max(lx1 - lx0, 0.1)
        if lot["face"] == "bottom":
            fy1 = fy0 + need
        else:
            fy0 = fy1 - need
        fp = G.largest_part(G.clip_rect(lot["local"], lx0, lx1, fy0, fy1))
    meds = []
    if rl <= 0.01:
        if lot["corner_side"] != "left":
            meds.append(((lx0, fy0), (lx0, fy1)))
        if lot["corner_side"] != "right":
            meds.append(((lx1, fy0), (lx1, fy1)))
    return fp, meds


def generate(data):
    S = ST.merged((data.get("params") or {}).get("standards"))["masterplan"]
    over = (data.get("params") or {}).get("masterplan") or {}
    for k, v in over.items():
        if v is not None:
            S[k] = v
    predio = G.ensure_ccw(G.clean([tuple(p) for p in data["predio"]]))
    warnings = []
    # bordes del predio que dan a calles existentes
    n = len(predio)
    fr_idx = data.get("frontage")
    if fr_idx is None:
        fr_idx = list(range(n))
    frontage = [(predio[i], predio[(i + 1) % n]) for i in fr_idx if 0 <= i < n]
    segs = _segments(data.get("streets"), S)
    # manzanas
    pieces = [predio]
    for sg in segs:
        pieces = _split(pieces, sg, warnings)
    warnings = list(dict.fromkeys(warnings))
    blocks = [_chamfer(b, segs, frontage, S["ochava"]) for b in pieces]
    blocks = [b for b in blocks if len(b) >= 3 and abs(G.area(b)) > 20]
    uses = data.get("block_uses") or {}
    mix = [m for m in (data.get("lot_mix") or [{"name": "Lote 12 m", "frente": 12, "percent": 50},
                                                  {"name": "Lote 15 m", "frente": 15, "percent": 35},
                                                  {"name": "Lote 20 m", "frente": 20, "percent": 15}])
           if m.get("frente", 0) > 0 and m.get("percent", 0) > 0]
    state = {"placed": {m["name"]: 0 for m in mix}, "n": 0}
    res = {"predio": G.pol_to_list(predio), "streets": [], "blocks": [], "lots": [], "warnings": warnings}
    for sg in segs:
        band = _band(sg, sg["half"], predio)
        cz = _band(sg, sg["calzada"] / 2.0, predio)
        res["streets"].append({"street": sg["street"], "band": G.pol_to_list(band) if band else [],
                               "calzada": G.pol_to_list(cz) if cz else [],
                               "axis": [list(sg["a"]), list(sg["b"])], "width": round(2 * sg["half"], 2)})
    lot_area = built = foot = 0.0
    n_lots = 0
    bad = 0
    for bi, b in enumerate(blocks):
        c = G.centroid(b)
        key = "%d,%d" % (round(c[0]), round(c[1]))
        use = uses.get(key, "lotes")
        blk = {"id": "M%02d" % (bi + 1), "key": key, "use": use, "poly": G.pol_to_list(b),
               "area": round(abs(G.area(b)), 1)}
        res["blocks"].append(blk)
        if use != "lotes" or not mix:
            continue
        lots, w = _lots_for_block(b, segs, frontage, S, mix, state)
        for x in w:
            res["warnings"].append("%s: %s" % (blk["id"], x))
        deep = max([lt["fondo"] for lt in lots] or [0])
        if deep > S.get("fondo_max", 50.0) + 0.5:
            res["warnings"].append("%s: lotes de hasta %.0f m de fondo (más de %.0f m): conviene una calle intermedia "
                                   "o un pasaje" % (blk["id"], deep, S.get("fondo_max", 50.0)))
        for lt in lots:
            n_lots += 1
            ang = lt["ang"]
            W_ = lambda pl: G.pol_to_list(G.to_world(pl, (0.0, 0.0), ang))
            a = abs(G.area(lt["local"]))
            checks = []
            if a + 1e-6 < S["lote_area_min"]:
                checks.append("Área %.0f m² < mínimo %.0f m²" % (a, S["lote_area_min"]))
            if lt["frente"] + 1e-6 < S["lote_frente_min"]:
                checks.append("Frente %.1f m < mínimo %.1f m" % (lt["frente"], S["lote_frente_min"]))
            if checks:
                bad += 1
            fp, meds = _building(lt, S)
            item = {"id": "L%03d" % n_lots, "block": blk["id"], "type": lt["type"], "poly": W_(lt["local"]),
                    "area": round(a, 1), "frente": round(lt["frente"], 2), "fondo": round(lt["fondo"], 2),
                    "corner": lt["corner"], "checks": checks}
            if fp:
                fa = abs(G.area(fp))
                item["building"] = {"poly": W_(fp), "area": round(fa, 1), "pisos": int(S["pisos"]),
                                    "altura": round(S["pisos"] * S["altura_piso"], 2),
                                    "medianeras": [W_(list(m_)) for m_ in meds],
                                    "fos": round(100 * fa / a, 1)}
                foot += fa
                built += fa * S["pisos"]
            lot_area += a
            res["lots"].append(item)
    A = abs(G.area(predio))
    blocks_area = sum(x["area"] for x in res["blocks"])
    green = sum(x["area"] for x in res["blocks"] if x["use"] == "verde")
    equip = sum(x["area"] for x in res["blocks"] if x["use"] == "equipamiento")
    calz = sum(abs(G.area(s["calzada"])) for s in res["streets"] if s["calzada"])
    streets_area = max(0.0, A - blocks_area)
    res["metrics"] = {
        "predio": round(A, 1), "calles": round(streets_area, 1), "calles_pct": round(100 * streets_area / A, 1) if A else 0,
        "calzada_aprox": round(min(calz, streets_area), 1),
        "manzanas": len(res["blocks"]), "manzanas_area": round(blocks_area, 1),
        "verde": round(green, 1), "equipamiento": round(equip, 1),
        "cesiones_pct": round(100 * (green + equip + streets_area) / A, 1) if A else 0,
        "reserva_pct": round(100 * (green + equip) / A, 1) if A else 0,
        "reserva_min_pct": S.get("reserva_min_pct", 10.0),
        "lotes": n_lots, "lotes_area": round(lot_area, 1),
        "lote_medio": round(lot_area / n_lots, 1) if n_lots else 0,
        "lotes_obs": bad, "ocupacion": round(foot, 1), "construible": round(built, 1),
        "viviendas_est": int(built * 0.8 / S["m2_por_vivienda"]) if built else 0,
        "ochavas_rest": round(sum(abs(G.area(p)) for p in pieces) - blocks_area, 1),
    }
    if bad:
        res["warnings"].append("%d lote(s) no cumplen área o frente mínimos" % bad)
    rmin = S.get("reserva_min_pct", 10.0)
    if A and rmin and 100 * (green + equip) / A + 1e-6 < rmin:
        res["warnings"].append("Reserva para espacios libres y equipamiento: %.1f %% del predio, menos del %.0f %% exigido "
                               "(sin contar calles). Marca manzanas como Espacio verde o Equipamiento."
                               % (100 * (green + equip) / A, rmin))
    res["settings"] = S
    return res
