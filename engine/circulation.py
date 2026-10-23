"""Pasillo y núcleos: piezas (tramos de pasillo con su marco local), uniones, núcleos, evacuación y el caso entre
medianeras. Parte del motor (ver engine/layout.py)."""
import math
from . import geometry as G
from . import plans as P
from .massing import _dist_point_segment, _dist_to_boundary, decompose_wings, descomponer_alas

BOLSILLO = 4.5     # fondo detrás de un núcleo por debajo del cual no cabe una unidad útil (el núcleo llega a la
#   fachada) y largo de un tramo sin luz que todavía puede ser depósito de la vivienda vecina
ANCHO_PEDIDO = (0.80, 8.0)     # R10.8: un ancho de pasillo pedido fuera de este rango se lleva al más cercano


# ---------------------------------------------------------------- ancho del pasillo por tramo (R10.8)
def ancho_de(pc, params):
    """R10.8: ancho del pasillo común de la pieza pc: el que el usuario le dio a ese tramo (params["anchos_pasillo"])
    o el general (params["corridor_width"])."""
    return pc.get("ancho") or params["corridor_width"]


def _pedidos_ancho(params):
    """R10.8: anchos pedidos tramo por tramo, [(k, punto, segmento, ancho)]: k, su lugar en params["anchos_pasillo"];
    cada pedido trae un punto del eje del tramo («p», la web) o un segmento de la polilínea («seg», Rhino)."""
    out = []
    for k, sp in enumerate(params.get("anchos_pasillo") or []):
        try:
            a = min(ANCHO_PEDIDO[1], max(ANCHO_PEDIDO[0], float(sp["ancho"])))
            seg = [(float(sp["seg"][0][0]), float(sp["seg"][0][1])), (float(sp["seg"][1][0]), float(sp["seg"][1][1]))] \
                if sp.get("seg") else None
            p = (float(sp["p"][0]), float(sp["p"][1])) if seg is None else None
        except (TypeError, ValueError, KeyError, IndexError, AttributeError):
            continue
        out.append((k, p, seg, a))
    return out


def _usado(params, k):
    """Anota que el pedido de ancho k se aplicó (layout avisa de los que no)."""
    if params.get("_anchos_usados") is not None:
        params["_anchos_usados"].add(k)


def _ancho_ala(poly, pedidos, params):
    """R10.8, modo automático: (k, ancho) pedido para el pasillo del ala poly (un punto dentro del ala; si hay varios,
    el último) o None."""
    out = None
    for k, p, seg, a in pedidos:
        q = p if p is not None else ((seg[0][0] + seg[1][0]) / 2.0, (seg[0][1] + seg[1][1]) / 2.0)
        if G.point_in_poly(q, poly):
            out = (k, a)
    if out:
        _usado(params, out[0])
    return out


def _con_ancho(params, an):
    """Los parámetros con el ancho del pasillo de un ala (an = (k, ancho) o None)."""
    return dict(params, corridor_width=an[1]) if an else params


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


def _make_piece(poly, origin, ang, xa, xb, ancho=None):
    pc = {"poly": poly, "origin": origin, "angle": ang, "xa": xa, "xb": xb,
          "loc_plate": G.to_local(poly, origin, ang), "cores": [], "junctions": [],
          "extra_blocks": {1: [], -1: []}, "corridor_ext": [], "free": [True, True]}
    if ancho:                                           # R10.8: (k, ancho) pedido para este tramo
        pc["ancho_k"], pc["ancho"] = ancho
    return pc


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
    central las viviendas quedan con menos fondo del que aprovecha un plano (R5.16b, v2.62: plans.fondo_min() + 0,5,
    el pasillo interno, un dormitorio y el estar con la cocina delante; antes, fondo_min a secas, y con el pasillo de
    1,5 m un ala de 10,3 m daba viviendas de 4,25 m de fondo con el estar bajo su lado mínimo y cuatro esquinas sin
    luz); en un ala que une, la opción con viviendas más cercanas a la superficie media del mix (con el mix Inversor,
    pasillo central en el ala de 12,3 × 8,7 m de patio_central: dos viviendas de 8,7 × 5,1 m en vez de una de
    8,7 × 10,5; con el mix de 75 y 95 m², pasillo de borde, como antes)."""
    if params.get("loading", "auto") != "auto":
        return params["loading"] == "single"
    cw, pw = params["corridor_width"], params["party_wall"]
    d2 = (short - cw) / 2.0 - pw
    d1 = min(short - cw - pw, params["max_unit_depth"])
    if d2 < P.fondo_min() + 0.5:
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
    if params.get("_lateral"):
        return [_pieza_lateral(plate, params)]           # R11.4: el pasillo lateral con patios (plan_lateral)
    holes = params.get("_huecos")
    cands = decompose_wings(plate, holes=holes, blind=params.get("_blind"), candidatos=True)
    dec = (cands[0][1], cands[0][2]) if cands else None
    alas = None
    if not dec and not holes:                           # planta no ortogonal: alas con su propio eje (R3.4)
        alas = descomponer_alas(plate)
        if alas and len(alas) < 2:
            alas = None
    pedidos = _pedidos_ancho(params)                    # R10.8: el ancho de cada ala, antes de elegir su marco
    if not dec and not alas:
        an = _ancho_ala(plate, pedidos, params)
        pa = _con_ancho(params, an)
        o, a, xa, xb = pick_frame(plate, pa)
        pc = _make_piece(plate, o, a, xa, xb, an)
        loc = pc["loc_plate"]
        x0_, y0_, x1_, y1_ = G.bbox(loc)
        if _choose_single(y1_ - y0_, pa) or (params.get("_blind") and (
                params["_blind"](G.to_world([((x0_ + x1_) / 2, y0_)], o, a)[0]) !=
                params["_blind"](G.to_world([((x0_ + x1_) / 2, y1_)], o, a)[0]))):
            o, a, xa, xb = _single_frame(plate, a, pa, G.centroid(plate))
            pc = _make_piece(plate, o, a, xa, xb, an)
            pc["single"] = True
        return _galeria([pc], plate, params)
    if dec and len(cands) > 1:
        # las dos direcciones de corte dejan alas: la que deja los pasillos unidos entre sí (la punta de uno entra en
        # otra ala, como lo ve _connect) y, a igual cantidad de grupos, la de mejor puntaje. Si no, en una planta en C
        # o en U el corte a lo largo deja tres tiras paralelas cuyos pasillos no se tocan: cada uno es una isla con
        # sus dos puntas libres, con un núcleo en cada una (seis núcleos y seis ascensores en una planta de 15 × 30)
        opciones = [_piezas_de([(p, th) for p in polys], plate, holes, pedidos, params) for _, th, polys in cands]
        return _galeria(min(opciones, key=_componentes), plate, params)
    alas = [(p, dec[0]) for p in dec[1]] if dec else alas
    pieces = _piezas_de(alas, plate, holes, pedidos, params)
    if not dec:
        for pc in pieces:                               # el eje termina donde corta el borde del ala (inglete, cuerda)
            ivs = G.line_intervals(pc["loc_plate"], 0.0)
            if ivs:
                pc["eje"] = max(ivs, key=lambda t: t[1] - t[0])
    return _galeria(pieces, plate, params)


def _piezas_de(alas, plate, holes, pedidos, params):
    """Las piezas de una descomposición en alas [(polígono, ángulo)] del modo automático."""
    polys = [p for p, _ in alas]
    centre = G.centroid(plate)
    bl = params.get("_blind")
    pieces = []
    for poly, th in alas:
        an = _ancho_ala(poly, pedidos, params)
        pieces.append(_pieza_ala(poly, th, polys, holes, bl, centre, an, _con_ancho(params, an)))
    return pieces


def _componentes(pieces):
    """Cuántos grupos de pasillos unidos forman las piezas: dos se unen si la punta del pasillo de una entra en el ala
    de la otra (la misma prueba de _connect). Alas vecinas por el lado largo (pasillos paralelos) no se unen."""
    padre = list(range(len(pieces)))

    def raiz(i):
        while padre[i] != i:
            i = padre[i]
        return i
    for i, pc in enumerate(pieces):
        ea, eb = pc.get("eje", (pc["xa"], pc["xb"]))
        for xe, sgn in ((ea, -1), (eb, 1)):
            probe = G.to_world([(xe + sgn * 0.8, 0.0)], pc["origin"], pc["angle"])[0]
            nb = next((j for j, q in enumerate(pieces) if j != i and G.point_in_poly(probe, q["poly"])), None)
            if nb is not None:
                padre[raiz(i)] = raiz(nb)
    return len({raiz(i) for i in range(len(pieces))})


def _pieza_ala(poly, th, polys, holes, bl, centre, an, params):
    """La pieza (tramo de pasillo) de un ala del modo automático: pasillo central, de borde o, entre medianeras,
    transversal. params ya trae el ancho del pasillo de esa ala (R10.8: an = (k, ancho) pedido, o None)."""
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
        # predio entre medianeras: pasillo transversal en el medio, viviendas hacia los dos frentes (la franja del
        # medio es la del núcleo: el ancho pedido es el de los pasillos que llegan a las viviendas)
        pc = _make_piece(poly, *_frame_for_poly(poly, ang + math.pi / 2))
        pc["between"] = True
        if an:
            pc["ancho_k"], pc["ancho_trans"] = an
        return pc
    if any(lb) and not all(lb):
        pc = _make_piece(poly, *_single_frame(poly, ang, params, centre), ancho=an)
        pc["single"] = True
        return pc
    if _ring_single(short, largo, puente is not None, params) if holes else _choose_single(short, params):
        pc = _make_piece(poly, *_single_frame(poly, ang, params, centre), ancho=an)
        pc["single"] = True
        return pc
    return _make_piece(poly, *_frame_for_poly(poly, ang), ancho=an)


# ---------------------------------------------------------------- galería: el pasillo de borde dentro del patio (R3.8)
def _sobre_galeria(pc, y, sgn, plate, params, n=40, frac=1 / 3.0):
    """R3.8: ¿el borde y (local, de xa a xb) de la pieza pc da a un patio con galería (params["_galerias"])? Se prueban
    puntos del otro lado del muro exterior (a outer_wall + 0,05 del borde, hacia sgn): una fracción frac o más (un
    tercio) tiene que caer en un patio con galería y los demás dentro de la planta o en su muro (ahí la banda sigue por
    otra ala, como un pasillo interior de esa ala); ninguno fuera del edificio. El borde tiene que ser recto de punta a
    punta."""
    gals = params.get("_galerias") or []
    loc = pc["loc_plate"]
    x0, _, x1, _ = G.bbox(loc)
    if not gals or x1 - x0 < 1.0 or G.strip_area(loc, x0, x1, min(y, y - sgn * 0.05), max(y, y - sgn * 0.05)) < \
            0.95 * (x1 - x0) * 0.05:
        return False                                    # (la franja de 5 cm hacia adentro de la planta, entera)
    ow = params["outer_wall"]
    ws = G.to_world([(x0 + (x1 - x0) * k / n, y + sgn * (ow + 0.05)) for k in range(n + 1)], pc["origin"], pc["angle"])
    patio = [any(G.point_in_poly(w, g) for g in gals) for w in ws]
    if sum(patio) < frac * (n + 1):
        return False
    return all(p or G.point_in_poly(w, plate) or _dist_to_boundary(w, plate) <= ow + 0.1 for p, w in zip(patio, ws))


def _a_galeria(pc, params):
    """R3.8: corre el pasillo de la pieza pc (de borde) al patio: la banda del ancho del pasillo queda del otro lado del
    muro exterior, pegada al edificio, y toda el ala es de las viviendas. El marco se corre hacia el patio y
    loc_plate/poly se extienden con la banda y el muro, así corridor_local cae en la banda y los núcleos la toman como
    palier. Anota galeria, banda (mundo) y ala (el ala sola, en el marco nuevo: la región de viviendas). Devuelve False
    si el ala no se deja extender."""
    cw, ow = ancho_de(pc, params), params["outer_wall"]
    x0, y0, x1, y1 = G.bbox(pc["loc_plate"])
    o = G.to_world([(x0, y0 - ow - cw / 2)], pc["origin"], pc["angle"])[0]
    ang = pc["angle"]
    L = x1 - x0
    ala = G.to_local(pc["poly"], o, ang)                        # el ala, desde y = cw/2 + ow
    muro = [(0.0, -cw / 2), (L, -cw / 2), (L, cw / 2 + ow), (0.0, cw / 2 + ow)]    # la banda y el muro, hasta el ala
    partes = G.union_parts([ala, muro])
    if len(partes) != 1 or partes[0][1]:
        return False
    ext = partes[0][0]
    if (G.area(ext) > 0) != (G.area(ala) > 0):
        ext = ext[::-1]
    pc.update(origin=o, angle=ang, xa=0.0, xb=L, loc_plate=ext, poly=G.to_world(ext, o, ang), galeria=True, ala=ala,
              banda=G.to_world([(0.0, -cw / 2), (L, -cw / 2), (L, cw / 2), (0.0, cw / 2)], o, ang))
    return True


def _galeria(pieces, plate, params):
    """R3.8 (modo automático, sin patios interiores): cada pieza con pasillo de borde cuyo borde del pasillo da a un patio
    con galería corre su pasillo al patio (_a_galeria). Donde la banda sale del patio y entra en otra ala es un pasillo
    interior de esa ala: sus viviendas se bloquean ahí (_bloquear_banda). Las alas de dos crujías no cambian, y la tira
    con el pasillo contra una medianera tampoco (se descartó: sus viviendas solo tendrían luz por la galería y el plano
    no tiene luz en el fondo)."""
    if not params.get("_galerias") or params.get("_huecos"):
        return pieces
    for pc in pieces:
        if not pc.get("single") or "eje" in pc or pc.get("between") or pc.get("user") or pc.get("lateral"):
            continue
        cw = ancho_de(pc, params)
        _, y0, _, _ = G.bbox(pc["loc_plate"])
        if abs(y0 + cw / 2) > 0.05:
            continue                                        # el pasillo no está pegado al borde y0
        if _sobre_galeria(pc, y0, -1, plate, params):
            _a_galeria(pc, params)
    _bloquear_banda(pieces, params)
    return pieces


def _bloquear_banda(pieces, params):
    """R3.8: la banda de una galería que entra en el ala de otra pieza (sale del patio y cruza el muro) es un pasillo
    interior de esa ala: sus viviendas no van ahí (extra_blocks, y conectores para que un núcleo no la pise)."""
    pw = params["party_wall"]
    for pc in pieces:
        if not pc.get("galeria"):
            continue
        for q in pieces:
            if q is pc:
                continue
            ql = G.to_local(pc["banda"], q["origin"], q["angle"])
            region = q["ala"] if q.get("galeria") else q["loc_plate"]
            bq = G.bbox(ql)
            br = G.bbox(region)
            if bq[0] >= br[2] or br[0] >= bq[2] or bq[1] >= br[3] or br[1] >= bq[3]:
                continue
            cq = ancho_de(q, params)
            for dentro in G.subtract(region, [ql])[1][0]:
                for sd in (1, -1):
                    parte = G.clip_rect(dentro, None, None, cq / 2 + pw / 2, None) if sd > 0 else \
                        G.clip_rect(dentro, None, None, None, -cq / 2 - pw / 2)
                    if not parte or abs(G.area(parte)) < 0.5:
                        continue
                    bx0, _, bx1, _ = G.bbox(parte)
                    q["extra_blocks"][sd].append((bx0 - pw / 2, bx1 + pw / 2))
                    q.setdefault("conectores", []).append((sd, bx0 - pw / 2, bx1 + pw / 2))


def _link(pieces, i, e, nb, params):
    """Une el extremo e (0=xa, 1=xb) de la pieza i con el pasillo de la pieza nb (conector + bloqueo). El conector es
    del ancho del pasillo de i y llega hasta el borde lejano del pasillo de nb (R10.8: cada uno con su ancho)."""
    pw = params["party_wall"]
    pc, q = pieces[i], pieces[nb]
    cw, cq = ancho_de(pc, params), ancho_de(q, params)
    xe, sgn = (pc.get("eje", (pc["xa"], pc["xb"]))[e], -1 if e == 0 else 1)
    pc["free"][e] = False
    E = G.to_world([(xe, 0.0)], pc["origin"], pc["angle"])[0]
    P = G.to_local([E], q["origin"], q["angle"])[0]
    d = G.rotate((sgn, 0.0), pc["angle"] - q["angle"])
    if abs(d[1]) < 0.2:       # ejes paralelos: unión directa
        pc["junctions"].append({"x": xe, "nb": nb, "nbx": P[0]})
        return
    s = -P[1] / d[1]                                     # hasta el eje del otro (negativo: la punta ya lo pasó)
    t = max(0.0, s)
    ext_len = t + cq / 2.0
    if pc.get("galeria") or q.get("galeria"):            # R3.8: dos galerías ya se solapan en la esquina del patio
        if s + cq / 2.0 <= 0.05:                         # la punta está dentro del pasillo del otro, o más allá
            pc["junctions"].append({"x": xe, "nb": nb, "nbx": P[0] + d[0] * t})
            return                                       # unión sin conector
        ext_len = s + cq / 2.0                           # solo hasta el borde lejano del otro pasillo
    if sgn < 0:
        box = [(xe - ext_len, -cw / 2), (xe, -cw / 2), (xe, cw / 2), (xe - ext_len, cw / 2)]
    else:
        box = [(xe, -cw / 2), (xe + ext_len, -cw / 2), (xe + ext_len, cw / 2), (xe, cw / 2)]
    world_box = G.to_world(box, pc["origin"], pc["angle"])
    if "eje" in pc:                                      # alas de una planta no ortogonal (R3.4)
        if t < 0.05:                                     # inglete: los dos pasillos ya se encuentran en el corte
            pc["junctions"].append({"x": xe, "nb": nb, "nbx": P[0]})
            return
        qb_ = G.to_local(world_box, q["origin"], q["angle"])   # un conector oblicuo no pasa del otro borde del pasillo
        qb_ = G.clip_rect(qb_, None, None, -cq / 2, None) if P[1] > 0 else G.clip_rect(qb_, None, None, None, cq / 2)
        world_box = G.to_world(qb_, q["origin"], q["angle"]) if qb_ else world_box
    pc["corridor_ext"].append(world_box)
    pc["prolonga"] = pc.get("prolonga", 0.0) + t         # R10.8: el tramo recto sigue por el conector (art. 35)
    qb = G.to_local(world_box, q["origin"], q["angle"])
    bx0, by0, bx1, by1 = G.bbox(qb)
    side = 1 if (by0 + by1) / 2 > 0 else -1
    protrusion = max(by1 - cq / 2, -cq / 2 - by0, 0.0)
    if protrusion > 0.6:      # el conector invade la zona de unidades; si no, vive dentro del pasillo
        q["extra_blocks"][side].append((bx0 - pw / 2, bx1 + pw / 2))
        q.setdefault("conectores", []).append((side, bx0 - pw / 2, bx1 + pw / 2))
    pc["junctions"].append({"x": xe, "nb": nb, "nbx": P[0] + d[0] * t})


def _connect(pieces, plate, params):
    """Alas automáticas: detecta extremos libres/uniones y crea los conectores de pasillo."""
    for i, pc in enumerate(pieces):
        ea, eb = pc.get("eje", (pc["xa"], pc["xb"]))
        for e, (xe, sgn) in enumerate(((ea, -1), (eb, 1))):
            probe = G.to_world([(xe + sgn * 0.8, 0.0)], pc["origin"], pc["angle"])[0]
            nb = next((j for j, q in enumerate(pieces) if j != i and G.point_in_poly(probe, q["poly"])), None)
            if nb is not None:
                _link(pieces, i, e, nb, params)
                j = pc["junctions"][-1]               # la unión sirve en los dos sentidos (evacuación por la otra ala)
                pieces[nb]["junctions"].append({"x": j["nbx"], "nb": i, "nbx": j["x"], "llega": True})


def _franjas_sin_luz(pieces, plate, params):
    """Codos (R3.2, antes solo anillos): donde el fondo de una franja de viviendas no da a ningún borde del edificio
    (da a otra ala: el codo de una L, una T o una U, las esquinas de un patio, o un ala descartada por angosta), no se
    ponen viviendas. Un tramo de hasta BOLSILLO queda como depósito de la vivienda vecina; uno más largo se anota en
    «oscuros»: ahí puede ir un núcleo (_nucleo_en_codo) y lo que quede se marca sin luz (_zonas_oscuras)."""
    bordes = [plate] + list(params.get("_huecos") or [])
    bl, pw, paso = params.get("_blind"), params["party_wall"], 0.25
    for q in pieces:
        n = max(1, int((q["xb"] - q["xa"]) / paso))
        xs = [q["xa"] + (q["xb"] - q["xa"]) * k / n for k in range(n + 1)]
        tr = [(p[1], p[0]) for p in q["loc_plate"]]               # el ala traspuesta: su borde en cada x
        for sd in (1, -1):
            if sd < 0 and q.get("galeria"):
                continue                                          # R3.8: del lado del patio está la galería, no hay franja
            pts = []
            for x in xs:                                          # el fondo real del ala en x (también si es inclinado)
                ivs = G.line_intervals(tr, x)
                yb = (max(b for _, b in ivs) - 0.05 if sd > 0 else min(a for a, _ in ivs) + 0.05) if ivs else None
                pts.append((x, yb if yb is not None else 0.0))
            # solo los codos: un fondo que no está sobre ningún borde (da a otra ala). Contra una medianera no se bloquea:
            # esas viviendas las marca la ficha, como siempre
            luz = [l or pt[1] == 0.0 for l, pt in zip(_luz(G.to_world(pts, q["origin"], q["angle"]), bordes, None), pts)]
            k = 0
            while k <= n:
                if luz[k]:
                    k += 1
                    continue
                j = k
                while j < n and not luz[j + 1]:
                    j += 1
                if xs[j] - xs[k] >= BOLSILLO:          # un tramo más corto queda como depósito de la vivienda vecina
                    q["extra_blocks"][sd].append((xs[k] - pw / 2, xs[j] + pw / 2))
                    q.setdefault("oscuros", []).append((sd, xs[k], xs[j]))
                k = j + 1


def _luz(ws, bordes, bl):
    """¿Cada punto de mundo está sobre una fachada (borde de la planta o de un patio) que no es medianera ciega?"""
    return [min(_dist_to_boundary(w, b) for b in bordes) <= 0.4 and not (bl and bl(w)) for w in ws]


def _codos(pieces, plate, params):
    """Codos (R3.2): donde un ala llega de costado al pasillo de otra, cada franja de viviendas del ala que llega baja
    hasta el pasillo de la otra si su fondo sigue dando a una fachada (la esquina exterior del codo, o del anillo). Esa
    parte de la otra ala ya no lleva viviendas porque no tiene luz (_franjas_sin_luz); así la esquina pasa a ser parte
    de una vivienda con luz en lugar de quedar vacía."""
    pw, paso = params["party_wall"], 0.25
    bordes = [plate] + list(params.get("_huecos") or [])
    bl = params.get("_blind")
    for pc in pieces:
        if pc.get("between") or pc.get("side_region"):
            continue
        cw = ancho_de(pc, params)
        _, y0b, _, y1b = G.bbox(pc["loc_plate"])
        loc_full = G.to_local(plate, pc["origin"], pc["angle"])
        huecos = [G.to_local(h, pc["origin"], pc["angle"]) for h in (params.get("_huecos") or [])]
        ext = {1: [], -1: []}                                    # esquinas que se suma cada franja
        for j in pc["junctions"]:
            e = 0 if abs(j["x"] - pc["xa"]) < 1e-6 else 1 if abs(j["x"] - pc["xb"]) < 1e-6 else None
            if e is None:
                continue                                        # unión de otra ala sobre esta (anillo): no es extremo
            q = pieces[j["nb"]]
            E = G.to_world([(j["x"], 0.0)], pc["origin"], pc["angle"])[0]
            largo = abs(G.to_local([E], q["origin"], q["angle"])[0][1]) - ancho_de(q, params) / 2 - pw / 2
            if largo < 1.0:
                continue
            xs0, xs1 = (pc["xa"] - largo, pc["xa"]) if e == 0 else (pc["xb"], pc["xb"] + largo)
            lin = cw / 2 + (params["outer_wall"] if pc.get("galeria") else pw / 2)   # R3.8: el muro hacia la galería
            for sd in ((1,) if pc.get("single") else (1, -1)):
                ya, yb = (lin, y1b) if sd > 0 else (y0b, -lin)
                if yb - ya < 2.0:
                    continue
                zona = G.clip_rect(loc_full, xs0, xs1, ya, yb)
                if not zona or abs(G.area(zona)) < 0.95 * (xs1 - xs0) * (yb - ya) or \
                        any(G.clip_rect(h, xs0, xs1, ya, yb) for h in huecos):
                    continue                                    # la esquina no está entera dentro de la planta
                n = max(1, int(largo / paso))
                yf = y1b - 0.05 if sd > 0 else y0b + 0.05
                ws = G.to_world([(xs0 + (xs1 - xs0) * k / n, yf) for k in range(n + 1)], pc["origin"], pc["angle"])
                if sum(_luz(ws, bordes, bl)) < 0.9 * (n + 1):
                    continue                                    # su fondo no da a una fachada: esquina interior
                ext[sd].append(zona)
                zw = G.to_world(zona, pc["origin"], pc["angle"])     # la otra ala no pone viviendas ahí
                bx0, by0, bx1, by1 = G.bbox(G.to_local(zw, q["origin"], q["angle"]))
                q["extra_blocks"][1 if by0 + by1 > 0 else -1].append((bx0 - pw / 2, bx1 + pw / 2))
                q.setdefault("ocupados", []).append((bx0 - pw / 2, bx1 + pw / 2))
        if ext[1] or ext[-1]:                                # el ala más sus esquinas (nunca la planta entera)
            pc["side_region"] = {sd: G.union_parts([pc["loc_plate"]] + ext[sd])[0][0] if ext[sd] else pc["loc_plate"]
                                 for sd in (1, -1)}


def _recortar_galeria(pieces, params):
    """R3.8: en una pieza con galería, la región de viviendas es el ala (desde el borde de la planta, del otro lado del
    muro), con las esquinas que le sumó _codos: sin la banda ni el muro, que loc_plate incluye para el pasillo y los
    núcleos. Del lado del patio no hay viviendas."""
    ow = params["outer_wall"]
    for pc in pieces:
        if not pc.get("galeria"):
            continue
        lim = ancho_de(pc, params) / 2 + ow
        reg = (pc.get("side_region") or {}).get(1) or pc["loc_plate"]
        pc["side_region"] = {1: G.clip_rect(reg, None, None, lim, None), -1: []}


def _clip_sr(pc, fn):
    """Aplica una función de recorte a las regiones de unidades de ambos lados de una pieza."""
    for sd in (1, -1):
        r = pc["side_region"].get(sd)
        pc["side_region"][sd] = fn(r) if r else []


def _largo(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def _tramo(pts, s0, s1):
    """Parte de una polilínea entre las longitudes s0 y s1 medidas desde su inicio."""
    out, s = [], 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L > 0 and s + L >= s0 and s <= s1:
            for t in (max(0.0, (s0 - s) / L), min(1.0, (s1 - s) / L)):
                p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
                if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > 1e-9:
                    out.append(p)
        s += L
    d = lambda p, q: math.hypot(p[0] - q[0], p[1] - q[1])
    res = out[:1]                                    # sin tramos diminutos: un corte junto a un vértice
    for p in out[1:-1]:
        if d(p, res[-1]) > 0.05:
            res.append(p)
    if len(out) >= 2:
        if len(res) > 1 and d(out[-1], res[-1]) <= 0.05:
            res[-1] = out[-1]                        # el extremo exacto (el cruce) manda sobre el vértice
        else:
            res.append(out[-1])
    return res


def _cruces_de(A, B):
    """Cruces entre dos polilíneas como longitudes (sA, sB) desde sus inicios, sin los que caen en un extremo
    (esos son empalmes en T o en L dibujados justo) ni los de ángulo muy agudo."""
    LA, LB = _largo(A), _largo(B)
    out, sa = [], 0.0
    for a, b in zip(A, A[1:]):
        la = math.hypot(b[0] - a[0], b[1] - a[1])
        sb = 0.0
        for c, d in zip(B, B[1:]):
            lb = math.hypot(d[0] - c[0], d[1] - c[1])
            tu = G.seg_intersection(a, b, c, d)
            seno = abs((b[0] - a[0]) * (d[1] - c[1]) - (b[1] - a[1]) * (d[0] - c[0])) / ((la * lb) or 1.0)
            if tu and seno >= 0.2:
                s1, s2 = sa + tu[0] * la, sb + tu[1] * lb
                if 0.05 < s1 < LA - 0.05 and 0.05 < s2 < LB - 0.05 and \
                        all(abs(s1 - p) > 0.05 or abs(s2 - q) > 0.05 for p, q in out):
                    out.append((s1, s2))
            sb += lb
        sa += la
    return out


def _cruces(lineas, params):
    """Cruces en X entre polilíneas distintas. En cada cruce la línea más larga sigue de largo (tronco) y la otra se
    corta en dos que terminan sobre el eje del tronco: cada mitad se une a él como un empalme en T, así ninguna
    vivienda pisa el pasillo ni las viviendas de la otra línea. Si una línea pasa al otro lado menos que la distancia
    de empalme de una T, lo que sobra es del dibujo y se quita (la línea termina en el cruce).
    Devuelve [(índice de la línea dibujada, puntos)]."""
    corto = params["corridor_width"] + 2.5
    largos = [_largo(p) for p in lineas]
    cortes = [[] for _ in lineas]                    # (longitud, None = corte | "antes"/"despues" = se quita)
    for i in range(len(lineas)):
        for j in range(i + 1, len(lineas)):
            for si, sj in _cruces_de(lineas[i], lineas[j]):
                hi, hj = (si, largos[i] - si), (sj, largos[j] - sj)
                ci, cj = sum(h < corto for h in hi), sum(h < corto for h in hj)
                if ci == 0 and cj == 0:
                    if (largos[i], -i) >= (largos[j], -j):
                        cortes[j].append((sj, None))
                    else:
                        cortes[i].append((si, None))
                elif ci == 1 and cj == 0:
                    cortes[i].append((si, "antes" if hi[0] < corto else "despues"))
                elif cj == 1 and ci == 0:
                    cortes[j].append((sj, "antes" if hj[0] < corto else "despues"))
    out = []
    for i, pts in enumerate(lineas):
        if not cortes[i]:
            out.append((i, pts))
            continue
        s0 = max([s for s, q in cortes[i] if q == "antes"], default=0.0)
        s1 = min([s for s, q in cortes[i] if q == "despues"], default=largos[i])
        if s1 - s0 < 0.05:
            s0, s1 = 0.0, largos[i]
        bs = [s0] + sorted(s for s, q in cortes[i] if q is None and s0 + 0.05 < s < s1 - 0.05) + [s1]
        for a, b in zip(bs, bs[1:]):
            parte = _tramo(pts, a, b)
            if len(parte) >= 2 and _largo(parte) > 0.05:
                out.append((i, parte))
    return out


def _sobre(A, B, seg, tol=0.05):
    """¿El segmento A-B va sobre el segmento seg (alineado con él a menos de tol y superpuesto)?"""
    (sx, sy), (ex, ey) = seg
    L = math.hypot(ex - sx, ey - sy)
    if L < tol:
        return False
    ux, uy = (ex - sx) / L, (ey - sy) / L
    off = lambda p: abs((p[0] - sx) * uy - (p[1] - sy) * ux)
    t = lambda p: (p[0] - sx) * ux + (p[1] - sy) * uy
    return off(A) <= tol and off(B) <= tol and min(max(t(A), t(B)), L) - max(min(t(A), t(B)), 0.0) > tol


def _adentro(p, A, B):
    """Cuánto entra la proyección de p en el segmento A-B: la distancia a su extremo más cercano (negativa si cae
    afuera)."""
    L = math.hypot(B[0] - A[0], B[1] - A[1])
    if L < 1e-9:
        return -1.0
    t = ((p[0] - A[0]) * (B[0] - A[0]) + (p[1] - A[1]) * (B[1] - A[1])) / L
    return min(t, L - t)


def _anchos_segmentos(tramos, params, lineas=()):
    """R10.8, polilíneas: {(tramo, segmento): (k, ancho)}. Un pedido con un punto va al segmento más cercano (a 1 m o
    menos; si el punto cae en un empalme o un cruce, al segmento en cuyo medio está); uno con un segmento (Rhino), a
    todos los que van sobre él (las dos mitades de una línea cortada en un cruce). lineas: las polilíneas dibujadas,
    antes de los cruces: un segmento que el motor quitó (lo que sobra de un cruce, uno de 5 cm o menos) no se avisa."""
    segs = [((t, i), pts[i], pts[i + 1]) for t, (_, pts) in enumerate(tramos) for i in range(len(pts) - 1)]
    out = {}
    for k, p, seg, a in _pedidos_ancho(params):
        if p is not None:
            ds = [(_dist_point_segment(p, A, B), key, A, B) for key, A, B in segs]
            d0 = min((d for d, _, _, _ in ds), default=None)
            hits = [min((c for c in ds if c[0] <= d0 + 1e-3), key=lambda c: (-_adentro(p, c[2], c[3]), c[1]))[1]] \
                if d0 is not None and d0 <= 1.0 else []
        else:
            hits = [key for key, A, B in segs if _sobre(A, B, seg)]
            if not hits and (math.hypot(seg[1][0] - seg[0][0], seg[1][1] - seg[0][1]) <= 0.05 or
                             any(_sobre(A, B, seg) for pts in lineas for A, B in zip(pts, pts[1:]))):
                _usado(params, k)      # un segmento dibujado que el motor quitó: no es un ancho perdido
        for key in hits:
            out[key] = (k, a)
    for k, _ in out.values():
        _usado(params, k)          # solo los que quedan: uno que otro pedido pisa en su tramo no se aplica
    return out


def build_user_pieces(plate, params):
    """Una pieza por tramo de cada polilínea dibujada. La planta se reparte entre tramos:
    en giros de ~90° con cortes ortogonales (el tramo anterior se queda con el codo interior),
    en otros ángulos con la bisectriz."""
    pw = params["party_wall"]
    D = params["max_unit_depth"]
    cls = params.get("centerlines") or ([params["centerline"]] if params.get("centerline") else [])
    lineas = []
    for pl in cls:
        pts = []
        for p in pl:
            p = (float(p[0]), float(p[1]))
            if not pts or math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1]) > 0.05:
                pts.append(p)
        if len(pts) >= 2:
            lineas.append(pts)
    pieces, chains = [], []
    tramos = _cruces(lineas, params)
    anchos = _anchos_segmentos(tramos, params, lineas)   # R10.8: el ancho pedido para cada tramo
    for t_, (linea, pts) in enumerate(tramos):
        n = len(pts) - 1
        idxs = []
        ws = [(anchos.get((t_, k)) or (None, params["corridor_width"]))[1] for k in range(n)]
        for k in range(n):
            a, b = pts[k], pts[k + 1]
            cw = ws[k]                                   # el ancho de este tramo, del anterior y del siguiente
            cw_ant, cw_sig = ws[k - 1] if k > 0 else cw, ws[k + 1] if k < n - 1 else cw
            c_ant, c_sig = cw_ant / 2 + pw / 2, cw_sig / 2 + pw / 2     # medio pasillo y medio tabique
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
                    sr[sB] = G.clip_rect(sr[sB], None, L - c_sig, None, None)
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
                    start_in = c_ant
                    ts = prev_pc.get("turn_side")
                    # fondo típico del lado interior del tramo anterior (mediana a lo largo del tramo)
                    depths = []
                    Lp = prev_pc["xb"]
                    if ts and Lp > 2 * c_ant + 1:
                        for t in range(1, 8):
                            xs_ = c_ant + (Lp - 2 * c_ant) * t / 8.0
                            slab = G.clip_rect(prev_pc["full"], xs_ - 0.05, xs_ + 0.05, c_ant, c_ant + D) \
                                if ts > 0 else G.clip_rect(prev_pc["full"], xs_ - 0.05, xs_ + 0.05, -(c_ant + D), -c_ant)
                            if slab:
                                ys_ = [abs(p[1]) for p in slab]
                                depths.append(max(ys_))
                    if depths:
                        depths.sort()
                        start_in = max(c_ant, depths[len(depths) // 2] + pw / 2)
                    zona = G.clip_rect(sr[inner], start_in - pw / 2, None, None, None) if sr[inner] else []
                    sr[inner] = G.clip_rect(sr[inner], start_in, None, None, None)
                    sr[outer] = G.clip_rect(sr[outer], c_ant, None, None, None)
                    prev_sr = prev_pc["side_region"].get(ts) if ts else None
                    if zona and prev_sr:
                        # donde la planta se ensancha en la esquina (la otra ala), la franja interior del tramo anterior
                        # es más honda que ese fondo típico: no pisa la de este tramo
                        zl = G.to_local(G.to_world(zona, a, ang), prev_pc["origin"], prev_pc["angle"])
                        partes = [o for o, _ in G.subtract(prev_sr, [zl])[0]]
                        if abs(G.area(prev_sr)) - sum(abs(G.area(o)) for o in partes) > 0.01:
                            prev_pc["side_region"][ts] = max(partes, key=lambda o: abs(G.area(o))) if partes else []
                else:
                    nx, ny = 1 - wx_, -wy_
                    if math.hypot(nx, ny) > 1e-6:
                        for sd in (1, -1):
                            sr[sd] = G.clip_halfplane(sr[sd], nx, ny, 0.0) if sr[sd] else []
                        sr = {sd: (G.clean(r) if len(r) >= 3 else []) for sd, r in sr.items()}
            pc = _make_piece(G.to_world(base, a, ang), a, ang, 0.0, L, anchos.get((t_, k)))
            pc["loc_plate"] = base
            pc["full"] = full
            pc["side_region"] = sr
            pc["turn_side"] = ortho_next
            pc["user"] = True
            pc["dibujo"] = (a, b)                        # R10.8: el segmento dibujado (tramos rectos del art. 35)
            xa_c = -cw_ant / 2 if k > 0 else 0.0        # el pasillo cubre el codo: hasta el borde del anterior
            xb_c = L + cw_sig / 2 if k < n - 1 else L    # y del siguiente
            pc["corridor_local"] = G.clip_rect(full, xa_c, xb_c, -cw / 2, cw / 2)
            pieces.append(pc)
            idxs.append(len(pieces) - 1)
        for u, v in zip(idxs, idxs[1:]):     # tramos consecutivos: unión directa
            pieces[u]["free"][1] = False
            pieces[v]["free"][0] = False
            pieces[u]["junctions"].append({"x": pieces[u]["xb"], "nb": v, "nbx": 0.0})
            pieces[v]["junctions"].append({"x": 0.0, "nb": u, "nbx": pieces[u]["xb"]})
        chains.append((linea, idxs))
    # extremos libres que tocan el pasillo de otra polilínea (empalme en T); las dos mitades de una línea cortada
    # en un cruce son de la misma línea y no se unen entre sí
    chain_of = {i: ci for ci, idxs in chains for i in idxs}
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
                lx = G.to_local([E], q["origin"], q["angle"])[0][0]
                if not (q["xa"] + 0.05 < lx < q["xb"] - 0.05):
                    dd += 0.01        # a igual distancia, el pasillo que pasa de largo (no el extremo de otro ramal)
                if dd < (ancho_de(pc, params) + ancho_de(q, params)) / 2 + 2.5 and (best is None or dd < best[0]):
                    best = (dd, j)
            if best:
                _link(pieces, i, e, best[1], params)
                j = pc["junctions"][-1]       # la unión sirve en los dos sentidos (evacuación por el ramal)
                pieces[best[1]]["junctions"].append({"x": j["nbx"], "nb": i, "nbx": j["x"], "llega": True})
                _stem_vs_trunk(pieces, i, e, best[1], params)
    _split_parallel(pieces, params)
    return pieces


def _stem_vs_trunk(pieces, i, e, j, params):
    """Empalme en T: el tronco (j) reserva el pasillo del ramal y la franja de unidades hasta D;
    el ramal (i) solo recibe unidades más allá de esa franja."""
    pw, D = params["party_wall"], params["max_unit_depth"]
    stem, trunk = pieces[i], pieces[j]
    cw = ancho_de(trunk, params)                         # la franja del tronco, desde el borde de su pasillo
    xf = stem["xb"] if e == 0 else stem["xa"]
    F = G.to_world([(xf, 0.0)], stem["origin"], stem["angle"])[0]
    sb = 1 if G.to_local([F], trunk["origin"], trunk["angle"])[0][1] > 0 else -1
    cor_w = G.to_world(stem["corridor_local"], stem["origin"], stem["angle"]) if stem.get("corridor_local") else []
    th = cw / 2 + pw + D
    if cor_w:
        cl = G.to_local(cor_w, trunk["origin"], trunk["angle"])
        # solo donde el pasillo del ramal cruza la franja de viviendas del tronco: un ramal oblicuo no bloquea de más
        franja = G.clip_rect(cl, None, None, 0.0, th) if sb > 0 else G.clip_rect(cl, None, None, -th, 0.0)
        bx0, by0, bx1, by1 = G.bbox(franja or cl)
        trunk["extra_blocks"][sb].append((bx0 - pw / 2, bx1 + pw / 2))

    def fn(r):
        tw = G.to_local(G.to_world(r, stem["origin"], stem["angle"]), trunk["origin"], trunk["angle"])
        tw = G.clip_rect(tw, None, None, th, None) if sb > 0 else G.clip_rect(tw, None, None, None, -th)
        return G.to_local(G.to_world(tw, trunk["origin"], trunk["angle"]), stem["origin"], stem["angle"]) if tw else []
    _clip_sr(stem, fn)


def _split_parallel(pieces, params):
    """Pasillos paralelos (de distintas líneas o tramos de una misma línea, como las ramas de una U): la planta entre
    ambos se reparte por la línea media."""
    pw, D = params["party_wall"], params["max_unit_depth"]
    for i, pc in enumerate(pieces):
        for j, q in enumerate(pieces):
            if i == j or not pc.get("side_region"):
                continue
            cp, cq = ancho_de(pc, params), ancho_de(q, params)
            if abs(math.sin(pc["angle"] - q["angle"])) > 0.03 or math.cos(pc["angle"] - q["angle"]) == 0:
                continue
            A = G.to_local([q["origin"]], pc["origin"], pc["angle"])[0]
            Bq = G.to_local(G.to_world([(q["xb"], 0.0)], q["origin"], q["angle"]), pc["origin"], pc["angle"])[0]
            ov = min(pc["xb"], max(A[0], Bq[0])) - max(pc["xa"], min(A[0], Bq[0]))
            yo = (A[1] + Bq[1]) / 2.0
            if ov < 1.0 or abs(yo) > (cp + cq) / 2 + 2 * (pw + D) or abs(yo) < (cp + cq) / 2:
                continue
            cut = yo / 2.0 + (cp - cq) / 4.0 * (1 if yo > 0 else -1)     # la mitad entre los bordes de los dos pasillos
            _clip_sr(pc, (lambda r: G.clip_rect(r, None, None, None, cut - pw / 2)) if yo > 0 else
                     (lambda r: G.clip_rect(r, None, None, cut + pw / 2, None)))


def egress_at(pieces, i, x, depth=3):
    pc = pieces[i]
    best = min((abs(x - c["x"]) for c in pc["cores"]), default=1e9)
    if depth > 0:
        for j in pc["junctions"]:
            best = min(best, abs(x - j["x"]) + egress_at(pieces, j["nb"], j["nbx"], depth - 1))
    return best


def _zonas_oscuras(pieces, params):
    """Las esquinas sin luz que quedaron vacías (sin viviendas, núcleo ni pasillo) se marcan en la planta («Sin luz
    natural») y cuentan aparte en las métricas: no es superficie desperdiciada, es la que no recibe luz."""
    pw = params["party_wall"]
    for pc in pieces:
        cw = ancho_de(pc, params)
        _, qy0, _, qy1 = G.bbox(pc["loc_plate"])
        for sd, a, b in pc.get("oscuros", []):
            if pc.get("single") and sd < 0:
                continue
            tapados = sorted([(c["box"][0], c["box"][2]) for c in pc["cores"] if c["side"] == sd] +
                             [(o0, o1) for o0, o1 in pc.get("ocupados", [])] +
                             [(c0, c1) for s_, c0, c1 in pc.get("conectores", []) if s_ == sd])
            cur, libres = a, []
            for t0, t1 in tapados:
                if t0 > cur:
                    libres.append((cur, min(t0, b)))
                cur = max(cur, t1)
            if cur < b:
                libres.append((cur, b))
            for x0, x1 in libres:
                if x1 - x0 < 1.0:
                    continue
                z = G.clip_rect(pc["loc_plate"], x0, x1, cw / 2 + pw / 2 if sd > 0 else None,
                                None if sd > 0 else -cw / 2 - pw / 2)
                if z and abs(G.area(z)) > 2.0:
                    pc.setdefault("codos", []).append(G.to_world(z, pc["origin"], pc["angle"]))


def _nucleo_en_codo(pc, juntas, params, pieces=None):
    """Lugar para un núcleo en un tramo sin luz junto a una unión (el codo interior de una L o una U), o None: al
    costado del conector del pasillo de la otra ala y fuera de la esquina que ya ocupan sus viviendas."""
    half, pw = params["core_width"] / 2.0, params["party_wall"]
    cw = ancho_de(pc, params)
    cj = lambda j: ancho_de(pieces[j["nb"]], params) if pieces is not None and j.get("nb") is not None else cw
    libre = lambda x: all(x + half <= o0 or x - half >= o1 for o0, o1 in
                          pc.get("ocupados", []) + [(j["x"] - cj(j) / 2 - pw / 2, j["x"] + cj(j) / 2 + pw / 2)
                                                     for j in pc["junctions"] if j.get("llega")])
    d = params["core_depth"] + (cw - params["corridor_width"])     # R10.8: el fondo del núcleo, con este pasillo

    def entra(x, sd):                                    # la caja entera del núcleo dentro de la planta
        y0, y1 = (-cw / 2, -cw / 2 + d) if sd > 0 else (cw / 2 - d, cw / 2)
        c = G.clip_rect(pc["loc_plate"], x - half, x + half, y0, y1)
        return bool(c) and abs(G.area(c)) >= 0.95 * 2 * half * d
    mejor = None
    for sd, a, b in pc.get("oscuros", []):
        if pc.get("single") and sd < 0:
            continue                                     # pasillo de borde: de ese lado no hay franja de viviendas
        for j in juntas:
            for x in (j["x"] + cj(j) / 2 + pw / 2 + half, j["x"] - cj(j) / 2 - pw / 2 - half):
                if a - 0.3 <= x - half and x + half <= b + 0.3 and libre(x) and entra(x, sd) and \
                        (mejor is None or abs(x - j["x"]) < mejor[2]):
                    mejor = (x, sd, abs(x - j["x"]))
    return None if mejor is None or mejor[2] > params["egress_single"] else mejor[:2]


def _punta(pc, e, x, side, params):
    """Núcleo en una punta libre (R3.1). Si entre el núcleo y el borde de la planta queda una franja demasiado chica
    para una vivienda (por ejemplo, una polilínea que termina antes de la fachada), el núcleo se apoya contra el borde:
    esa franja ya no queda suelta y la vivienda del otro lado del núcleo crece en su lugar. Solo si el núcleo llega a la
    fachada: si detrás le queda un bolsillo, la franja y el bolsillo ya forman una vivienda."""
    pw, half, cw = params["party_wall"], params["core_width"] / 2.0, ancho_de(pc, params)
    d = params["core_depth"] + (cw - params["corridor_width"])     # R10.8: el fondo del núcleo, con este pasillo
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


def nucleo_punto(spec):
    """Posición de un núcleo manual: [x, y] o {"p": [x, y], "frente": .., "fondo": .., "giro": 0 | 90} (R3.5)."""
    p = spec.get("p") if isinstance(spec, dict) else spec
    return float(p[0]), float(p[1])


def medidas_nucleo(spec, params):
    """(giro, frente, fondo con el pasillo) de un núcleo manual: sus medidas propias o las de todos los núcleos
    (con giro 90, las del núcleo con la escalera a lo largo del pasillo: params["_core_90"]). Con sus propios
    ascensores (R10.7), las medidas de la normativa para esa cantidad."""
    op = spec if isinstance(spec, dict) else {}
    giro = 90 if str(op.get("giro", 0)) == "90" else 0
    w, d = (params.get("_core_90") or (params["core_depth"] - params["corridor_width"],
                                       params["core_width"] + params["corridor_width"])) if giro == 90 else \
        (params["core_width"], params["core_depth"])
    if op.get("ascensores") is not None and params.get("_tam_nucleo"):
        w, d = params["_tam_nucleo"](max(0, int(op["ascensores"])), giro)
    if op.get("frente"):
        w = max(1.0, float(op["frente"]))
    if op.get("fondo"):
        d = max(1.0, float(op["fondo"])) + params["corridor_width"]
    return giro, w, d


def _add_core(pc, x, side, params, bolsillo=True):
    """Núcleo en x, del lado side. Si detrás queda una franja más chica que BOLSILLO, el núcleo llega hasta la fachada
    (salvo bolsillo=False: un fondo elegido para ese núcleo se respeta y la franja queda para la vivienda vecina)."""
    cw, w = ancho_de(pc, params), params["core_width"]
    d = params["core_depth"] + (cw - params["corridor_width"])     # R10.8: el fondo incluye el pasillo de esta pieza
    if side > 0:
        box = (x - w / 2, -cw / 2, x + w / 2, -cw / 2 + d)
    else:
        box = (x - w / 2, cw / 2 - d, x + w / 2, cw / 2)
    strip = G.clip_rect(pc["loc_plate"], box[0], box[2]) if bolsillo else None
    if strip:
        ys = [p[1] for p in strip]
        pocket = BOLSILLO
        if side > 0 and 0 < max(ys) - box[3] < pocket:
            box = (box[0], box[1], box[2], max(ys))
        if side < 0 and 0 < box[1] - min(ys) < pocket:
            box = (box[0], min(ys), box[2], box[3])
    pc["cores"].append({"x": x, "side": side, "box": box,
                        "poly_local": G.clip_rect(pc["loc_plate"], box[0], box[2], box[1], box[3])})


def _x_que_entra(pc, x, side, params):
    """Alas con inglete o con un extremo inclinado (R3.4): la x más cercana a x donde la caja entera del núcleo entra
    en el ala (si no, un núcleo recortado por el borde no tendría lugar para la escalera)."""
    half, cw = params["core_width"] / 2.0, ancho_de(pc, params)
    d = params["core_depth"] + (cw - params["corridor_width"])     # R10.8: el fondo del núcleo, con este pasillo
    y0, y1 = (-cw / 2, -cw / 2 + d) if side > 0 else (cw / 2 - d, cw / 2)

    def entra(xx):
        c = G.clip_rect(pc["loc_plate"], xx - half, xx + half, y0, y1)
        return bool(c) and abs(G.area(c)) >= 0.98 * 2 * half * d
    if entra(x):
        return x
    for k in range(1, 121):
        for xx in (x - 0.25 * k, x + 0.25 * k):
            if pc["xa"] + half <= xx <= pc["xb"] - half and entra(xx):
                return xx
    return x


def _sin_pisar(pieces, pc, x, side, params, sentido):
    """La x más cercana a x, hacia sentido (+1/-1) y dentro de la pieza, donde un núcleo nuevo no pisa a otro (hasta
    dos frentes de núcleo); None si no hay."""
    half = params["core_width"] / 2.0
    for k in range(0, int(4 * half / 0.25) + 1):
        xx = x + sentido * 0.25 * k
        if not (pc["xa"] + half - 1e-9 <= xx <= pc["xb"] - half + 1e-9):
            break
        if "eje" in pc:
            xx = _x_que_entra(pc, xx, side, params)
        _add_core(pc, xx, side, params)
        pisa = _pisa_nucleo(pieces, pc, pc["cores"][-1]) or _pisa_conector(pc, pc["cores"][-1], params)
        pc["cores"].pop()
        if not pisa:
            return xx
    return None


def _pisa_conector(pc, nuevo, params, solo_anchos=False):
    """R10.8: ¿el núcleo nuevo de la pieza pc pone escalera, ascensor, ducto o sala de máquinas (más de 0,1 m²) sobre el
    conector del pasillo de otra ala que llega de su mismo lado? solo_anchos: solo los más anchos que su pasillo."""
    pw, b, cw = params["party_wall"], nuevo["box"], ancho_de(pc, params)
    cerca = [(c0 + pw / 2, c1 - pw / 2) for s_, c0, c1 in pc.get("conectores", [])
             if s_ == nuevo["side"] and b[0] < c1 - pw / 2 and c0 + pw / 2 < b[2] and
             (not solo_anchos or c1 - c0 - pw > cw + 0.05)]
    if not cerca:
        return False
    if params.get("_partes_nucleo") is None:
        return True
    ps = [p_["poly"] for p_ in params["_partes_nucleo"](b, nuevo["side"], cw)
          if p_["kind"] in ("stair", "elevator", "duct", "service")]
    return any(sum(abs(G.area(q)) for q in (G.clip_rect(p_, x0, x1, None, None) for p_ in ps) if q and len(q) >= 3) > 0.1
               for x0, x1 in cerca)


def _pisa_nucleo(pieces, pc, nuevo):
    """¿El núcleo nuevo de la pieza pc se superpone (más de 0,1 m²) con uno que ya está, de cualquier pieza?"""
    if not nuevo.get("poly_local"):
        return False
    b = G.bbox(nuevo["poly_local"])
    for q in pieces:
        for c in q["cores"]:
            if c is nuevo or not c.get("poly_local"):
                continue
            ol = G.to_local(G.to_world(c["poly_local"], q["origin"], q["angle"]), pc["origin"], pc["angle"])
            o = G.bbox(ol)
            if o[0] >= b[2] or b[0] >= o[2] or o[1] >= b[3] or b[1] >= o[3]:
                continue
            if sum(abs(G.area(p)) for p in G.subtract(nuevo["poly_local"], [ol])[1][0]) > 0.1:
                return True
    return False


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
    for pc in pieces:
        pc["_planta"] = plate                           # la planta del bloque (R3.7: ¿del otro lado del pasillo hay planta?)
    _puntas_tras_cruce(pieces, params)
    return pieces


def _puntas_tras_cruce(pieces, params):
    """R3.7: punta del pasillo de un ala después de su última unión o núcleo (como en una L, donde el pasillo sigue más
    allá del cruce hasta la fachada sin servir a ninguna puerta). Si la franja de viviendas de otra ala llega justo hasta
    ese tramo (de la fachada al pasillo que llega: los codos de R3.2), la franja lo cruza y el pasillo termina en la
    unión (q["tramo"]). Las viviendas del otro lado entran por lo que queda (q["puntas"], ver units.entradas)."""
    pw = params["party_wall"]
    for q in pieces:
        if q.get("user") or q.get("between") or q.get("galeria") or q.get("lateral"):
            continue                                     # R3.8: la banda de una galería está fuera de la planta
        cw = ancho_de(q, params)                         # R10.8: cada pasillo con su ancho
        lin = cw / 2 + pw / 2
        anclas = [(j["x"] - ancho_de(pieces[j["nb"]], params) / 2, j["x"] + ancho_de(pieces[j["nb"]], params) / 2)
                  for j in q["junctions"]] + [(c["box"][0], c["box"][2]) for c in q["cores"]]
        if not anclas:
            continue
        for e in (0, 1):
            t = list(q.get("tramo") or (q["xa"], q["xb"]))
            if not q["free"][e]:
                continue
            s0, s1 = (t[0], min(a for a, _ in anclas)) if e == 0 else (max(b for _, b in anclas), t[1])
            if s1 - s0 < 1.0:
                continue
            for pc in pieces:
                if pc is q or pc.get("user") or pc.get("between") or abs(math.cos(pc["angle"] - q["angle"])) > 0.05:
                    continue
                sr = pc.get("side_region")
                hecho = False
                lin_p = ancho_de(pc, params) / 2 + pw / 2
                for sd in ((1,) if pc.get("single") else (1, -1)):
                    reg = sr.get(sd) if sr else pc["loc_plate"]
                    franja = (G.clip_rect(reg, None, None, lin_p, None) if sd > 0 else
                              G.clip_rect(reg, None, None, None, -lin_p)) if reg else []
                    if not franja:
                        continue
                    bx0, by0, bx1, by1 = G.bbox(G.to_local(G.to_world(franja, pc["origin"], pc["angle"]),
                                                           q["origin"], q["angle"]))
                    lado = 1 if abs(by0 - lin) < 0.05 else -1 if abs(by1 + lin) < 0.05 else 0
                    if not lado or abs(bx0 - s0) > pw + 0.05 or abs(bx1 - s1) > pw + 0.05:
                        continue
                    otro = q.get("side_region", {}).get(-lado) if q.get("side_region") else q["loc_plate"]
                    del_otro = otro and not (q.get("single") and -lado < 0) and G.strip_area(
                        otro, s0, s1, lin if -lado > 0 else None, None if -lado > 0 else -lin) > 1.0
                    borde = (cw / 2 - pw / 2) if del_otro else cw / 2     # cruza hasta el tabique con las del otro lado
                    ya, yb = (-borde, lin) if lado > 0 else (-lin, borde)
                    rect = G.to_local(G.to_world([(bx0, ya), (bx1, ya), (bx1, yb), (bx0, yb)], q["origin"], q["angle"]),
                                      pc["origin"], pc["angle"])
                    partes = G.union_parts([reg, rect])
                    if len(partes) != 1 or partes[0][1]:
                        continue
                    nuevo = partes[0][0]
                    if (G.area(nuevo) > 0) != (G.area(reg) > 0):
                        nuevo = nuevo[::-1]
                    if not sr:
                        pc["side_region"] = sr = {1: pc["loc_plate"], -1: pc["loc_plate"]}
                    sr[sd] = nuevo
                    t[e] = s0 if e == 1 else s1
                    q["tramo"] = t
                    if del_otro:
                        q.setdefault("puntas", []).append({"e": e, "s0": s0, "s1": s1, "lado": -lado})
                    hecho = True
                    break
                if hecho:
                    break


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


# ---------------------------------------------------------------- pasillo lateral con patios (R11.4)
PUERTA_LATERAL = 1.45    # R11.4: hasta dónde entra, desde el fondo de la vivienda, la puerta de una vivienda con fachada
#   lateral (la mitad del fondo máximo de la franja de la entrada, plans.KITCH_D / 2): el planificador mide la evacuación con eso


def _dorms_mix(m):
    return int(m["dorms"]) if m.get("dorms") is not None else P.bedrooms_for(m["area"])


def plan_lateral(fp, plate, params, ancho, minimo=3):
    """R11.4 (v2.72): el esquema «pasillo lateral con patios» de un predio entre medianeras: el pasillo corre de punta a
    punta contra una medianera (el marco de _single_frame) y las viviendas van todas del otro lado, en hilera hacia la
    medianera opuesta, con patios de aire y luz de `ancho` m entre vivienda y vivienda (pegados a la medianera opuesta
    y hasta el borde del pasillo; en la planta, con el muro exterior a cada lado: ancho + 2·outer_wall). Cada vivienda
    tiene una fachada lateral (la calle, el contrafrente o un patio): los «dientes» entre patios llevan a lo sumo dos
    viviendas, nunca tres seguidas sin patio. El núcleo va en la hilera y llega hasta la medianera opuesta; nunca le
    quita la fachada a una vivienda: entre las dos de un diente ([U K U]), junto a una que tiene la suya del otro lado
    ([K U], [U K]) o solo entre dos patios ([K]).
    Cuántas entran: la fachada de cada vivienda es D_u = ancho de la planta − pasillo − medio tabique (fija), así que son
    aptos los tipos del mix con facade_min(dormitorios) ≤ D_u + 0,05; su ancho a lo largo del pasillo es su fondo, w. Con
    n viviendas hacen falta n_patios = ceil(n/2) − 1 patios como mínimo (dos por diente) y el largo del pasillo L reparte
    L = n·w + n_patios·(ancho + 2·outer_wall) + núcleos·core_width + tabiques entre vecinas; se toma el n más grande con
    w ≥ max(fondo_min() + 0,5 —el fondo que aprovecha un plano—, superficie media de los tipos aptos / D_u / 1,35 —la
    misma tolerancia de los tipos aptos del reparto—); con n fijo, entre las hileras posibles (cuántas viviendas y si el
    núcleo va en cada diente) gana la que cumple el fondo de saco (egress_single, desde la puerta: PUERTA_LATERAL hacia
    adentro desde el fondo de cada vivienda, hasta el núcleo más cercano; entre dos núcleos, dos salidas) con un núcleo;
    si ninguna, con dos; después, la de menos patios y la de menor recorrido. Los dientes se reparten en proporción (dos
    viviendas, doble largo; el reparto del mix pone después una o dos en cada uno, units.generate_unit_mix).
    Devuelve (plan, None) o (None, por qué no entra): plan = {origin, angle, L, y1 (el fondo de la planta en el marco),
    D, fachadas [extremo x0, x1], patios (mundo, restados de la huella como los manuales), patios_loc [(x0, x1)] en la
    planta, nucleos [x del centro], dientes [[(x0, x1, "U"|"K")]], n, w}. minimo: viviendas mínimas (3)."""
    if not is_between(plate, params):
        return None, "no es un predio entre medianeras"
    th, (poly,) = decompose_wings(plate)
    x0, y0, x1, y1 = G.bbox([G.rotate(p, -th) for p in poly])
    ang = th if (x1 - x0) >= (y1 - y0) else th + math.pi / 2
    cw, pw, ow = params["corridor_width"], params["party_wall"], params["outer_wall"]
    o, a, _, L = _single_frame(plate, ang, params, G.centroid(plate))
    loc = G.to_local(plate, o, a)
    _, ly0, _, ly1 = G.bbox(loc)
    D = ly1 - cw / 2 - pw / 2                              # la fachada lateral de cada vivienda (fija)
    mix = [m for m in params["unit_mix"] if m.get("percent", 0) > 0 and m.get("area", 0) > 0]
    aptos = [m for m in mix if P.facade_min(_dorms_mix(m)) <= D + 0.05]
    if not aptos:
        return None, "el ancho del lote deja %.1f m de fachada a cada vivienda y el tipo más chico del mix pide %.1f m" % (
            D, min(P.facade_min(_dorms_mix(m)) for m in mix) if mix else P.facade_min(0))
    tot = sum(m["percent"] for m in aptos) or 1.0
    avg = sum(m["percent"] / tot * m["area"] for m in aptos)
    w_min = max(P.fondo_min() + 0.5, avg / D / 1.35)
    bl = params.get("_blind")
    mid = (ly1 - cw / 2) / 2
    fach = [not (bl and bl(G.to_world([(x_, mid)], o, a)[0])) for x_ in (0.0, L)]
    ap, c = ancho + 2 * ow, params["core_width"]
    egress = params["egress_single"]
    patrones = (("U",), ("U", "U"), ("K",), ("K", "U"), ("U", "K"), ("U", "K", "U"))

    def vale(pat, izq, der):
        """El diente pat con fachada a la izquierda (izq) y a la derecha (der): cada vivienda con una fachada propia."""
        for k, e in enumerate(pat):
            if e == "U" and not ((k == 0 and izq) or (k == len(pat) - 1 and der)):
                return False
        return True

    def hileras(t, cores):
        """Todas las hileras de t dientes con cores núcleos: listas de patrones."""
        def rec(k, quedan):
            if k == t:
                if quedan == 0:
                    yield []
                return
            izq, der = (fach[0] if k == 0 else True), (fach[1] if k == t - 1 else True)
            for pat in patrones:
                nk = pat.count("K")
                if nk <= quedan and vale(pat, izq, der):
                    for resto in rec(k + 1, quedan - nk):
                        yield [pat] + resto
        return rec(0, cores)

    def armar(hilera, w):
        """Posiciones de cada hilera con viviendas de ancho w: dientes [(x0, x1, tipo)], patios [(x0, x1)], núcleos [x]."""
        x, dientes, patios, nucleos = 0.0, [], [], []
        for k, pat in enumerate(hilera):
            d = []
            for j, e in enumerate(pat):
                if e == "U":
                    d.append((x, x + w, "U"))
                    x += w + (pw if j + 1 < len(pat) and pat[j + 1] == "U" else 0.0)
                else:
                    d.append((x, x + c, "K"))
                    nucleos.append(x + c / 2)
                    x += c
            dientes.append(d)
            if k + 1 < len(hilera):
                patios.append((x, x + ap))
                x += ap
        return dientes, patios, nucleos

    def saco_max(hilera, dientes, nucleos):
        """El fondo de saco más largo: desde cada puerta (a PUERTA_LATERAL del fondo de la vivienda, el lado opuesto a su
        fachada) hasta el núcleo más cercano; 0 entre dos núcleos."""
        peor = 0.0
        for k, (pat, d) in enumerate(zip(hilera, dientes)):
            izq, der = (fach[0] if k == 0 else True), (fach[1] if k == len(hilera) - 1 else True)
            for j, (u0, u1, e) in enumerate(d):
                if e != "U":
                    continue
                lado = _lado_fachada(pat, j, izq, der)
                puerta = (u1 - PUERTA_LATERAL) if lado < 0 else (u0 + PUERTA_LATERAL)
                if any(n0 <= puerta <= n1 for n0, n1 in zip(nucleos, nucleos[1:])):
                    continue
                peor = max(peor, min(abs(puerta - n_) for n_ in nucleos))
        return peor
    mejor = None
    n_max = int(L // w_min)
    for n in range(n_max, minimo - 1, -1):
        for cores in (1, 2):
            p_min = max(0, int(math.ceil(n / 2.0)) - 1)
            for t in range(p_min + 1, n + 2):              # dientes: al menos los que piden dos viviendas por diente
                for h in hileras(t, cores):
                    if sum(pat.count("U") for pat in h) != n:
                        continue
                    muros = sum(sum(1 for j in range(len(pat) - 1) if pat[j] == "U" and pat[j + 1] == "U") for pat in h)
                    libre = L - (t - 1) * ap - cores * c - muros * pw
                    w = libre / n
                    if w < w_min - 1e-9:
                        continue
                    dientes, patios, nucleos = armar(h, w)
                    sm = saco_max(h, dientes, nucleos)
                    clave = (-n, sm > egress + 1e-6, cores, t, round(sm, 3))
                    if mejor is None or clave < mejor[0]:
                        mejor = (clave, h, w, dientes, patios, nucleos)
        if mejor is not None:
            break
    if mejor is None:
        return None, "el fondo del lote (%.1f m de pasillo) no da para %d viviendas de %.1f m de fondo con sus patios y el " \
                     "núcleo" % (L, minimo, w_min)
    _, h, w, dientes, patios, nucleos = mejor
    W = lambda pts: G.to_world(pts, o, a)
    patios_w = [W([(p0 + ow, cw / 2 + ow), (p1 - ow, cw / 2 + ow), (p1 - ow, ly1 + ow + 1.0), (p0 + ow, ly1 + ow + 1.0)])
                for p0, p1 in patios]                       # en la huella: de ancho `ancho`, hasta el muro del pasillo
    return {"origin": o, "angle": a, "L": L, "y1": ly1, "D": D, "fachadas": fach, "patios": patios_w,
            "patios_loc": patios, "nucleos": nucleos, "dientes": dientes, "hilera": h, "n": sum(pat.count("U") for pat in h),
            "w": w}, None


def _lado_fachada(pat, j, izq, der):
    """R11.4: de qué lado tiene su fachada la vivienda j del diente pat: -1 (x0), 1 (x1) o 0 (las dos: una sola vivienda
    entre dos fachadas). izq/der: si el diente tiene fachada a cada lado. (units.generate_unit_mix decide lo mismo con
    las viviendas reales de cada diente: fachadas_diente.)"""
    f_izq = izq and (j == 0)
    f_der = der and (j == len(pat) - 1)
    if f_izq and f_der:
        return 0
    return -1 if f_izq else 1


def fachadas_diente(pc, x0, x1, tol=0.05):
    """R11.4: qué tiene a cada lado el diente [x0, x1] de la hilera de la pieza lateral pc: "punta" (el frente o el
    contrafrente del lote, si no son medianera), "patio" o None (el núcleo, u otra cosa sin luz). Con eso el reparto sabe
    cuántas viviendas pueden ir en el diente (una por fachada) y de qué lado tiene la suya cada una."""
    pl = pc["lateral"]
    out = []
    for k, x in enumerate((x0, x1)):
        if abs(x - (0.0 if k == 0 else pl["L"])) < tol:
            out.append("punta" if pl["fachadas"][k] else None)
        elif any(abs(x - (p1 if k == 0 else p0)) < tol for p0, p1 in pl["patios_loc"]):
            out.append("patio")
        else:
            out.append(None)
    return out


def _nucleo_lateral(pc, x, params, pieces):
    """R11.4: un núcleo en x (centro) en la hilera de la pieza lateral: del lado de las viviendas, de core_width de frente
    y hasta la medianera opuesta (lo que la escalera y los ascensores no usan es depósito o sala de máquinas:
    programs.core_parts). Se corre lo mínimo para entrar en el pasillo y no pisar otro núcleo; None si no hay lugar."""
    cw, w = ancho_de(pc, params), params["core_width"]
    y1 = pc["lateral"]["y1"]
    xa, xb = pc["xa"] + w / 2, pc["xb"] - w / 2
    if xb < xa:
        return None
    for k in range(0, int(2 * (pc["xb"] - pc["xa"]) / 0.25) + 1):
        for xx in sorted({min(max(x - 0.25 * k, xa), xb), min(max(x + 0.25 * k, xa), xb)}):
            box = (xx - w / 2, -cw / 2, xx + w / 2, y1)
            c = {"x": xx, "side": 1, "box": box, "lateral": True,
                 "poly_local": G.clip_rect(pc["loc_plate"], box[0], box[2], box[1], box[3])}
            if c["poly_local"] and abs(G.area(c["poly_local"])) > 0.9 * w * (y1 + cw / 2) and \
                    not _pisa_nucleo(pieces, pc, c):
                pc["cores"].append(c)
                return xx
    return None


def _nucleos_manuales(pieces, params, next_side=None):
    """Núcleos manuales (cores_mode = manual): cada punto de params["cores"] se ajusta al pasillo más cercano (R3.5 y
    R10.7: con sus medidas, giro y ascensores propios). next_side: el lado para un punto sobre el eje de un pasillo
    central (sin él, alternando)."""
    counter = [0]

    def alterna():
        s_ = side_for(counter[0], params["core_side"])
        counter[0] += 1
        return s_
    next_side = next_side or alterna
    for idx, spec in enumerate(params.get("cores") or []):
        wx, wy = nucleo_punto(spec)
        giro, w, d = medidas_nucleo(spec, params)
        half = w / 2.0
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
        _add_core(pc, lx, side, dict(params, core_width=w, core_depth=d), bolsillo=not (isinstance(spec, dict) and spec.get("fondo")))
        pc["cores"][-1].update({"spec": idx, "giro": giro, "pisa": _pisa_nucleo(pieces, pc, pc["cores"][-1])})
        if isinstance(spec, dict) and spec.get("ascensores") is not None:
            pc["cores"][-1]["ascensores"] = max(0, int(spec["ascensores"]))      # R10.7: propios
    return pieces


def _circulacion_lateral(pieces, params):
    """R11.4: el pasillo lateral: el pasillo de punta a punta contra la medianera, las viviendas del otro lado (la planta
    en peine, con los patios ya restados) y los núcleos del plan (plan_lateral); si aun así algún punto del pasillo queda
    a más de egress_multi de un núcleo y auto_cores, se agregan más (como en cualquier pasillo)."""
    pc = pieces[0]
    cw = ancho_de(pc, params)
    pc["corridor_local"] = G.clip_rect(pc["loc_plate"], pc["xa"], pc["xb"], -cw / 2, cw / 2)
    pc["side_region"] = {1: pc["loc_plate"], -1: []}
    if params.get("cores_mode") == "manual":
        return _nucleos_manuales(pieces, params)
    for x in pc["lateral"]["nucleos"]:
        _nucleo_lateral(pc, x, params, pieces)
    guard = 0
    while params.get("auto_cores") and len(pc["cores"]) < 8 and guard < 10:
        guard += 1
        n = max(2, int(pc["xb"] - pc["xa"]))
        peor = max(((egress_at(pieces, 0, pc["xa"] + (pc["xb"] - pc["xa"]) * k / n), pc["xa"] + (pc["xb"] - pc["xa"]) * k / n)
                    for k in range(n + 1)), key=lambda t: t[0])
        if peor[0] <= params["egress_multi"] or _nucleo_lateral(pc, peor[1], params, pieces) is None:
            break
    return pieces


def _pieza_lateral(plate, params):
    """R11.4: la pieza del pasillo lateral: single, con el marco del plan (params["_lateral"]), las viviendas de un solo
    lado (side_region[1] es la planta en peine: los patios ya están restados) y nada del otro."""
    pl = params["_lateral"]
    pc = _make_piece(plate, pl["origin"], pl["angle"], 0.0, pl["L"], _ancho_ala(plate, _pedidos_ancho(params), params))
    pc["single"] = True
    pc["lateral"] = pl
    return pc


def _generate_circulation(plate, params):
    pieces = build_pieces(plate, params)
    cw = params["corridor_width"]
    if len(pieces) == 1 and pieces[0].get("lateral"):
        return _circulacion_lateral(pieces, params)
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
        # los pasillos que llegan a las viviendas: el ancho pedido para este tramo (R10.8) o el general (sin ensanchar
        # para el núcleo; antes, con núcleos manuales, quedaba fijo en 2.0)
        cwc = pc.get("ancho_trans") or params.get("_cw_base") or params["corridor_width"]
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
            cp = ancho_de(pc, params)
            pc["corridor_local"] = G.clip_rect(pc["loc_plate"], pc["xa"], pc["xb"], -cp / 2, cp / 2)
    if not user:
        _connect(pieces, plate, params)
    if not user:
        _franjas_sin_luz(pieces, plate, params)
        _codos(pieces, plate, params)
        _recortar_galeria(pieces, params)                # R3.8: las viviendas de una galería, solo en el ala
    counter = [0]

    def next_side():
        s = side_for(counter[0], params["core_side"])
        counter[0] += 1
        return s

    half = params["core_width"] / 2.0
    if params.get("cores_mode") == "manual":
        return _nucleos_manuales(pieces, params, next_side)
    ring = bool(params.get("_huecos"))
    for pc in pieces:               # un núcleo en cada extremo libre
        for e, free in enumerate(pc["free"]):
            if free:
                xe = pc["xa"] if e == 0 else pc["xb"]
                cerca = [j for j in pc["junctions"] if abs(xe - j["x"]) <= params["egress_single"]]
                if ring and cerca:
                    continue        # punta corta de un pasillo que da la vuelta al patio: se sale hacia los dos lados
                if cerca:           # punta corta junto a un codo: se sale por la unión; el núcleo va al codo sin luz
                    codo = _nucleo_en_codo(pc, cerca, params, pieces)
                    if codo is not None:
                        _add_core(pc, codo[0], codo[1], params)
                        if _pisa_nucleo(pieces, pc, pc["cores"][-1]):
                            pc["cores"].pop()   # ya hay un núcleo en ese codo
                        continue
                x = pc["xa"] + half if e == 0 else pc["xb"] - half
                if pc["xb"] - pc["xa"] < 2 * half:
                    x = (pc["xa"] + pc["xb"]) / 2.0
                lado = 1 if pc.get("single") else next_side()
                _add_core(pc, _x_que_entra(pc, x, lado, params) if "eje" in pc else x, lado, params)
                if not pc.get("single") and _pisa_conector(pc, pc["cores"][-1], params):
                    pc["cores"].pop()       # R10.8: llega ahí el pasillo de la otra ala: del otro lado
                    lado = -lado
                    _add_core(pc, _x_que_entra(pc, x, lado, params) if "eje" in pc else x, lado, params)
                if _pisa_nucleo(pieces, pc, pc["cores"][-1]) or _pisa_conector(pc, pc["cores"][-1], params):
                    pc["cores"].pop()       # pisa otro núcleo (dos puntas cercanas): se corre hacia adentro, si entra
                    x2 = _sin_pisar(pieces, pc, x, lado, params, 1 if e == 0 else -1)
                    if x2 is None:
                        continue            # no entra: el que está ya sirve a las dos puntas
                    _add_core(pc, x2, lado, params)
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
        oscuro = _nucleo_en_codo(pc, [{"x": x}], dict(params, egress_single=BOLSILLO * 2), pieces)
        if oscuro is not None:      # de preferencia en un tramo sin luz cercano: no le quita fachada a ninguna vivienda
            _add_core(pc, oscuro[0], oscuro[1], params)
            if not _pisa_nucleo(pieces, pc, pc["cores"][-1]):
                continue
            pc["cores"].pop()
        lado = 1 if pc.get("single") else next_side()
        _add_core(pc, _x_que_entra(pc, x, lado, params) if "eje" in pc else x, lado, params)
        if _pisa_nucleo(pieces, pc, pc["cores"][-1]) or _pisa_conector(pc, pc["cores"][-1], params, solo_anchos=True):
            pc["cores"].pop()       # pisa otro núcleo (o el pasillo más ancho de otra ala): del otro lado o más allá
            x2 = None
            for ld in ((lado,) if pc.get("single") else (-lado, lado)):
                for d in (1, -1):
                    x2 = _sin_pisar(pieces, pc, x, ld, params, d)
                    if x2 is not None:
                        _add_core(pc, x2, ld, params)
                        break
                if x2 is not None:
                    break
            if x2 is None:
                break               # no entra sin pisar otro núcleo: no se agregan más
    # R3.1: un núcleo de punta que deja una franja suelta hasta la fachada se apoya contra ella, si la evacuación
    # sigue dentro del máximo (si no, queda donde estaba)
    for pc in pieces:
        for k, c in enumerate(pc["cores"]):
            if c.get("punta") is None:
                continue
            x2 = _punta(pc, c["punta"], c["x"], c["side"], params)
            if "eje" in pc:
                x2 = _x_que_entra(pc, x2, c["side"], params)
            if abs(x2 - c["x"]) < 1e-9:
                continue
            _add_core(pc, x2, c["side"], params)
            pc["cores"][k] = pc["cores"].pop()
            if worst()[0] > max(params["egress_multi"], v) or _pisa_nucleo(pieces, pc, pc["cores"][k]):
                pc["cores"][k] = c
    _zonas_oscuras(pieces, params)
    return pieces
