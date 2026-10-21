"""Viviendas: tramos laterales libres, reparto del mix en unidades, métricas del mix y planos de cada unidad
(engine/plans.py). Parte del motor (ver engine/layout.py)."""
import math
from . import geometry as G
from . import plans as P
from . import standards as ST
from .massing import _dist_to_boundary
from .circulation import ancho_de


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


def _bisect_f(f, x0, xmax, target):
    """x1 tal que f(x1) = target (f creciente desde x0), o None si no se llega."""
    lo, hi = x0, xmax
    if f(hi) < target:
        return None
    for _ in range(50):
        mid = (lo + hi) / 2.0
        if f(mid) < target:
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


def _y_puerta(pc, params):
    """Distancia del eje del pasillo común a la puerta de una vivienda: el borde del pasillo o, con galería (R3.8), el
    borde de la planta, del otro lado del muro exterior."""
    return ancho_de(pc, params) / 2 + (params["outer_wall"] if pc.get("galeria") else 0.0)


def _segments(loc, circ, params):
    """Regiones laterales (local) entre núcleos, a cada lado del pasillo.
    El bolsillo que queda detrás de un núcleo se suma al tramo vecino para no desperdiciar planta."""
    cw = ancho_de(circ, params)                         # R10.8: el ancho del pasillo de este tramo
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


def _perfil(region):
    """R5.16b: superficie de la franja entre dos x, rápida y exacta: el ancho transversal w(x) de un polígono es lineal
    entre los x de sus vértices (cada tramo es un trapecio), así los cortes del reparto se resuelven sin bisecar la
    geometría. Devuelve (area(x0, x1), corte(x0, a): el x1 con area(x0, x1) = a, o None si la franja no llega)."""
    xs = sorted(set(p[0] for p in region))
    T = [(p[1], p[0]) for p in region]                       # traspuesto: line_intervals corta por x
    ancho = lambda x: sum(b - a for a, b in G.line_intervals(T, x))
    tramos = []                                              # (x0, x1, w(x0), w(x1)) de cada tramo
    for a, b in zip(xs, xs[1:]):
        if b - a < 1e-9:
            continue
        q1, q3 = ancho(a + (b - a) / 4), ancho(a + 3 * (b - a) / 4)    # dos puntos interiores: w lineal entre ellos
        tramos.append((a, b, 1.5 * q1 - 0.5 * q3, 1.5 * q3 - 0.5 * q1))

    def area(x0, x1):
        s = 0.0
        for a, b, w0, w1 in tramos:
            lo, hi = max(a, x0), min(b, x1)
            if hi - lo <= 0:
                continue
            wl = w0 + (w1 - w0) * (lo - a) / (b - a)
            wh = w0 + (w1 - w0) * (hi - a) / (b - a)
            s += (wl + wh) / 2 * (hi - lo)
        return s

    def corte(x0, obj):
        rem = obj
        for a, b, w0, w1 in tramos:
            if b <= x0:
                continue
            lo = max(a, x0)
            wl = w0 + (w1 - w0) * (lo - a) / (b - a)
            s = (w1 - w0) / (b - a)
            entero = (wl + w1) / 2 * (b - lo)
            if entero < rem - 1e-9:
                rem -= entero
                continue
            if rem <= 0:
                return lo
            if abs(s) < 1e-12:
                return lo + (rem / wl if wl > 1e-12 else 0.0)
            return lo + (-wl + math.sqrt(max(0.0, wl * wl + 2 * s * rem))) / s
        return None
    return area, corte


def _dorms_de(m):
    """Dormitorios de un tipo del mix: los suyos o, sin «dorms», los que le tocan por su superficie."""
    return int(m["dorms"]) if m.get("dorms") is not None else P.bedrooms_for(m["area"])


def generate_unit_mix(circ, params, state=None):
    """Reparte el mix en viviendas a lo largo de cada franja lateral de la pieza (_segments). R5.16b (v2.62), reparto por
    el frente que pide el plano:
    - Cada vivienda recibe al menos el frente que pide su plano, plans.frente_min(dormitorios, fondo de la franja):
      el estar y los dormitorios en la fachada (facade_min) y, en una franja poco profunda, el hall, el baño y la cocina
      en fila. Su ancho es el mayor entre ese frente y el que da su superficie objetivo (× el ajuste k de la franja) con
      el fondo que la vivienda aprovecha, min(fondo de la franja, plans.fondo_sin_tira()); k es el que hace que las
      viviendas llenen la franja justo (cuando ningún frente manda, k = superficie de la franja / suma de objetivos,
      como antes). Si el frente manda, la vivienda queda más grande que su objetivo (lo muestra el fit del mix): nunca
      más angosta.
    - Un tipo que en esa franja, con su frente mínimo y el fondo entero, pasaría de 1,35 veces su superficie objetivo
      no es apto para la franja: el reparto (por los porcentajes del mix, con el estado compartido entre piezas) elige
      entre los aptos y, si ninguno lo es (una franja de 16 m de fondo), el que menos se pasa; el plano deja la tira
      (fondo_sin_tira) sin uso, con aviso.
    - La cantidad de viviendas es la que mejor ajusta las superficies a sus objetivos (como antes: la que da la
      superficie media del mix, una más o una menos) entre las que caben con sus frentes mínimos; si ni una cabe
      (la franja entera es más corta que el frente), va una sola con lo que hay.
    Los tabiques entre vecinas (party_wall) se descuentan del frente de cada una."""
    loc = circ["loc_plate"]
    cw, pw = ancho_de(circ, params), params["party_wall"]
    mix = [m for m in params["unit_mix"] if m.get("percent", 0) > 0 and m.get("area", 0) > 0]
    tot = sum(m["percent"] for m in mix) or 1.0
    for m in mix:
        m["_p"] = m["percent"] / tot
    segs = _segments(loc, circ, params)
    frentes = extremos_al_frente(circ, params)              # R3.7
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
        area_r, corte_r = _perfil(region)
        D_seg = A_seg / length                                  # fondo medio de la franja
        D_util = min(D_seg, P.fondo_sin_tira())                 # el fondo que el plano aprovecha entero
        fmin = {m["name"]: P.frente_min(_dorms_de(m), D_seg) for m in mix}     # el frente que pide cada tipo
        caben = [m for m in mix if fmin[m["name"]] <= length + 1e-6] or [min(mix, key=lambda m: fmin[m["name"]])]
        aptos = [m for m in caben if fmin[m["name"]] * D_seg <= 1.35 * m["area"] + 1e-6] or \
            [min(caben, key=lambda m: fmin[m["name"]] * D_seg / m["area"])]
        menor = min(fmin[m["name"]] for m in aptos)

        def plan(n, ext, puro=True):
            """Los n tipos siguientes del mix (los aptos para esta franja, por su cuota); con ext (R3.7), el de menos
            dormitorios va a la punta de la vivienda al frente. Sin puro: si el tipo que toca por cuota no cabe con su
            frente en lo que queda de franja para esta vivienda y las que siguen, va el de más cuota entre los aptos
            que caben o, si ninguno, entre los demás tipos que caben (ver elegir)."""
            pl, cnt, usado = dict(placed), n_placed, 0.0
            seq = []
            sitio = lambda i, usado: length - (n - 1) * pw - usado - (n - i - 1) * menor
            for i in range(n):
                cuota = lambda t: t["_p"] * (cnt + 1) - pl[t["name"]]
                m = max(aptos, key=cuota)
                if not puro and fmin[m["name"]] > sitio(i, usado) + 1e-6:
                    posibles = [t for t in aptos if fmin[t["name"]] <= sitio(i, usado) + 1e-6] or \
                        [t for t in caben if fmin[t["name"]] <= sitio(i, usado) + 1e-6]
                    if posibles:
                        m = max(posibles, key=cuota)
                seq.append(m)
                pl[m["name"]] += 1
                cnt += 1
                usado += fmin[m["name"]]
            return ordenar(seq, ext)

        def ordenar(seq, ext):
            """Con ext (R3.7), el tipo de menos dormitorios va a la punta de la vivienda al frente."""
            if ext and len(seq) > 1:
                j = min(range(len(seq)), key=lambda i: (_dorms_de(seq[i]), i if ext[0] == 0 else -i))
                otras = seq[:j] + seq[j + 1:]
                seq = otras + [seq[j]] if ext[0] == 1 else [seq[j]] + otras
            return seq

        def minimo(idx, n, m, ext):
            """Ancho mínimo del tramo [x, x1) de la vivienda idx: su frente más sus medios tabiques (la de la punta al
            frente, R3.7, no: su largo lo miden fondo_frente y fondo_sin_tira)."""
            if ext and idx == (n - 1 if ext[0] == 1 else 0):
                return 0.0
            return fmin[m["name"]] + (pw / 2 if idx > 0 else 0.0) + (pw / 2 if idx < n - 1 else 0.0)

        def cortes(seq, k, ext, corte=None):
            """[(xs0, xe)] de cada vivienda (superficie objetivo × k, sin bajar de su frente mínimo; la última, hasta el
            final); con ext = (e, franja), la de la punta e suma la franja del pasillo; corte: el tabique de esa vivienda
            en un lugar fijo y las demás se reparten lo que queda. Devuelve también el exceso (hasta dónde llegaría la
            última vivienda libre con su superficie × k, menos donde termina: > 0, no entran; < 0, sobra franja), si
            algún frente mínimo mandó y la superficie de la franja del pasillo que suma la vivienda al frente."""
            n = len(seq)
            out, x, forzado, banda = [], xmin, False, 0.0
            fijo = (n - 2 if ext[0] == 1 else 0) if corte is not None else None    # el corte fijo: su x1
            libre = n - 2 if (corte is not None and ext[0] == 1) else n - 1          # la última vivienda libre
            exceso = 0.0
            for idx, m in enumerate(seq):
                last = idx == n - 1
                al_frente = ext and idx == (n - 1 if ext[0] == 1 else 0)
                x_ini = x + (pw / 2 if idx > 0 else 0.0)
                if al_frente:                              # la franja del pasillo, desde su tabique hasta su x1
                    area_de = lambda t, x_=x, xi=x_ini: area_r(x_, t) + G.strip_area(ext[1], xi, t - (0.0 if last else pw / 2))
                else:
                    area_de = lambda t, x_=x: area_r(x_, t)
                nat = _bisect_f(area_de, x, xmax, m["area"] * k) if al_frente else corte_r(x, m["area"] * k)
                if nat is None:                            # no llega: hasta dónde llegaría con el fondo útil
                    nat = xmax + (m["area"] * k - area_de(xmax)) / max(D_util, 0.5)
                piso = x + minimo(idx, n, m, ext)
                if piso > nat + 1e-9:
                    nat, forzado = piso, True
                if idx == fijo:
                    x1 = corte
                elif last:
                    x1 = xmax
                else:
                    x1 = min(nat, xmax)
                if idx == libre:
                    exceso = nat - x1
                out.append((x_ini, x1 - (0.0 if last else pw / 2)))
                if al_frente:
                    banda = G.strip_area(ext[1], out[-1][0], out[-1][1])
                x = x1
            return out, exceso, forzado, banda

        def ajuste(seq, ext, corte=None):
            """k de la franja: con el que las viviendas (superficie objetivo × k) la llenan justo. Si ningún frente
            mínimo manda, k = superficie / suma de objetivos (con la franja del pasillo de la vivienda al frente, R3.7,
            por iteración); si alguno manda, los demás se achican hasta que todo entra (bisección); None si ni con sus
            frentes mínimos caben."""
            if corte is not None:
                libres = seq[:-1] if ext[0] == 1 else seq[1:]
                A = area_r(xmin, corte) if ext[0] == 1 else area_r(corte, xmax)
                S = sum(m["area"] for m in libres) or 1.0
                k = A / S
                forzado = cortes(seq, k, ext, corte)[2]
            else:
                S = sum(m["area"] for m in seq)
                extra, k = 0.0, A_seg / S
                for _ in range(12 if ext else 1):
                    k = (A_seg + extra) / S
                    _, _, forzado, banda = cortes(seq, k, ext)
                    if not ext or abs(banda - extra) < 0.01:
                        break
                    extra = banda
            if not forzado:
                return k
            if cortes(seq, 0.0, ext, corte)[1] > 1e-6:
                return None
            lo, hi = 0.0, k
            for _ in range(50):
                mid = (lo + hi) / 2.0
                if cortes(seq, mid, ext, corte)[1] > 0:
                    hi = mid
                else:
                    lo = mid
            return lo

        def elegir(ext, corte=None):
            """(seq, k, cortes): la cantidad de viviendas que mejor ajusta las superficies a sus objetivos (la de la
            superficie media, una más o una menos, como antes) entre las que caben con sus frentes mínimos siguiendo
            la cuota del mix (si no caben, se baja). Si así alguna vivienda pasa de 1,35 veces su objetivo (la misma
            tolerancia de los tipos aptos: en una franja corta, una sola de 100 m² para un tipo de 62), se prueba
            cambiar una de ellas por un tipo más grande que quepa (lo que sobra de franja lo aprovecha ese tipo) y una
            vivienda más con algún tipo cambiado por otro que cabe (plan sin puro), y se toma lo que ajusta mejor. Si
            ni una cabe con su frente, va una sola con lo que hay."""
            n0 = max(1, int(round(A_seg / avg)))

            def probar(seq):
                k = ajuste(seq, ext, corte)
                if k is None:
                    return None
                cuts = cortes(seq, k, ext, corte)[0]
                razones = [max(1e-9, area_r(a, b) + (G.strip_area(ext[1], a, b) if ext and i == (
                    len(seq) - 1 if ext[0] == 1 else 0) else 0.0)) / D_seg * D_util / m["area"]
                           for i, ((a, b), m) in enumerate(zip(cuts, seq))]
                return (sum(abs(math.log(r_)) for r_ in razones) / len(seq), seq, k, cuts, max(razones))

            best, vistos, n, mas = None, 0, min(n_max, n0 + 1), None
            while n >= 1 and vistos < 3:
                c = probar(plan(n, ext))
                if c:
                    if vistos == 0 and n < n_max:
                        mas = probar(plan(n + 1, ext, False))       # una más, con algún tipo cambiado
                    best = c if best is None or c[0] < best[0] else best
                    vistos += 1
                n -= 1
            if best is None:                                   # ni una cabe con su frente: una sola con lo que hay
                seq = plan(1, ext)
                k = A_seg / seq[0]["area"]
                return seq, k, cortes(seq, k, ext, corte)[0]
            if best[4] > 1.35 + 1e-6:                          # alguna se pasa: un tipo más grande en su lugar
                seq = best[1]
                for j, m in enumerate(seq):
                    for t in caben:
                        if t["area"] > m["area"] + 1e-6:
                            c = probar(ordenar(seq[:j] + [t] + seq[j + 1:], ext))
                            if c and (mas is None or c[0] < mas[0]):
                                mas = c
                if mas and mas[0] < best[0]:
                    best = mas
            return best[1], best[2], best[3]

        # R3.7: en una punta libre de un pasillo de borde, la última vivienda suma la franja del pasillo (llega a todo el
        # ancho y el pasillo termina en su puerta): el reparto la cuenta para que las viviendas queden parejas. Esa
        # vivienda es la de menos dormitorios del tramo (su frente es el ancho de la planta) y su fondo no pasa del que
        # el plano aprovecha entero (P.fondo_sin_tira): lo demás va a las otras
        ext = None
        if side > 0:
            for e, (xe_, banda) in frentes.items():
                if (seg["x1"] >= xe_ - 0.05) if e == 1 else (seg["x0"] <= xe_ + 0.05):
                    ext = (e, banda)
        corte = None
        for _ in range(3):
            seq, k, cuts = elegir(ext, corte)
            if not ext:
                break
            a_, b_ = cuts[-1] if ext[0] == 1 else cuts[0]
            if b_ - a_ < fondo_frente() or (b_ - a_ > P.fondo_sin_tira() and len(seq) == 1):
                ext, corte = None, None                      # no da para una vivienda al frente: reparto de siempre
                continue
            if b_ - a_ > P.fondo_sin_tira() and corte is None:   # la del frente, con el fondo que el plano aprovecha
                corte = xmax - P.fondo_sin_tira() - pw / 2 if ext[0] == 1 else xmin + P.fondo_sin_tira() + pw / 2
                continue
            break
        L_min = P.HALL_W + 0.3                           # R3.7: lo que la última necesita del pasillo que queda
        for pt in circ.get("puntas", []):
            if pt["lado"] != side or len(cuts) < 2:
                continue
            if pt["e"] == 1 and cuts[-1][1] > pt["s0"] and pt["s0"] - cuts[-1][0] < L_min:
                c = pt["s0"] - L_min
                if c - pw - cuts[-2][0] >= max(0.5 * params["min_unit_width"], fmin[seq[-2]["name"]]):
                    cuts[-2], cuts[-1] = (cuts[-2][0], c - pw), (c, cuts[-1][1])
            elif pt["e"] == 0 and cuts[0][0] < pt["s1"] and cuts[0][1] - pt["s1"] < L_min:
                c = pt["s1"] + L_min
                if cuts[1][1] - (c + pw) >= max(0.5 * params["min_unit_width"], fmin[seq[1]["name"]]):
                    cuts[0], cuts[1] = (cuts[0][0], c), (c + pw, cuts[1][1])
        for m in seq:
            placed[m["name"]] += 1
            n_placed += 1
        state["n"] = n_placed
        for (xs0, xe), m in zip(cuts, seq):
            poly = G.largest_part(G.clip_rect(region, xs0, xe))      # una unidad es una sola figura
            if poly:
                a_ = abs(G.area(poly))
                w = xe - xs0
                units.append({"type": m["name"], "target": m["area"], "area": a_, "width": w,
                              "side": side, "x0": xs0, "x1": xe, "poly_local": poly, "_region": region})
                if w < params["min_unit_width"]:
                    warnings.append("Unidad con ancho %.2f m < mínimo %.2f m" % (w, params["min_unit_width"]))   # con 1 decimal, 4.98 < 5 se leía «5.0 < 5.0»
    # puertas, evacuación y profundidad
    for i, u in enumerate(units):
        xd = (u["x0"] + u["x1"]) / 2.0
        yd = _y_puerta(circ, params) * u["side"]
        u["door_local"] = (xd, yd)
        u["egress"] = 0.0
        ys = [p[1] for p in u["poly_local"]]
        u["depth"] = (max(ys) - min(ys))
        if u["depth"] > params["max_unit_depth"] + 0.5:
            warnings.append("Unidad %s de %.0f m² tiene profundidad %.1f m (> %.1f m): poca luz natural" %
                            (u["type"], u["area"], u["depth"], params["max_unit_depth"]))
    return units, warnings


# ---------------------------------------------------------------- pasillo sin puntas muertas (R3.7)
def fondo_frente():
    """Largo mínimo (a lo largo del pasillo) de una vivienda al frente: su fondo, desde la punta del pasillo."""
    return P.fondo_min() + 0.5


def extremos_al_frente(pc, params):
    """R3.7: puntas del pasillo de la pieza pc que pueden terminar en una vivienda «al frente», que ocupa todo el ancho
    de la planta en esa punta: punta libre (sin unión) que llega a la fachada, con el pasillo apoyado en el borde de la
    planta (del otro lado no hay viviendas). Devuelve {e: (x de la punta, franja)}: franja, la del pasillo con el medio
    tabique hacia las viviendas, de todo el largo (marco de la pieza)."""
    if pc.get("between") or pc.get("puntas") or pc.get("galeria") or not pc.get("corridor_local"):
        return {}                                      # R3.8: la banda de una galería está fuera de la planta
    cw, pw = ancho_de(pc, params), params["party_wall"]
    loc = pc["loc_plate"]
    planta = pc.get("_planta") or G.to_world(loc, pc["origin"], pc["angle"])
    huecos = params.get("_huecos") or []
    en_planta = lambda x, y: (lambda w: G.point_in_poly(w, planta) and not any(G.point_in_poly(w, h) for h in huecos))(
        G.to_world([(x, y)], pc["origin"], pc["angle"])[0])
    n = max(2, int(pc["xb"] - pc["xa"]))
    if any(en_planta(pc["xa"] + (pc["xb"] - pc["xa"]) * k / n, -cw / 2 - 0.3) for k in range(n + 1)):
        return {}                                      # del otro lado del pasillo hay planta (otra ala, viviendas)
    out = {}
    for e, xe in ((0, pc["xa"]), (1, pc["xb"])):
        if pc["free"][e] and not en_planta(xe - 0.2 if e == 0 else xe + 0.2, 0.0):
            banda = G.clip_rect(loc, None, None, -cw / 2, cw / 2 + pw / 2)
            if banda:
                out[e] = (xe, banda)
    return out


def formar_frentes(units, pieces, params):
    """R3.7: en cada punta libre de un pasillo de borde (ver extremos_al_frente), la vivienda del extremo suma la franja
    del pasillo y llega a todo el ancho; el pasillo termina en su puerta, en la punta (pc["tramo"]). La vivienda
    guarda «frente»: {e, x (donde termina el pasillo), a, b (su largo a lo largo del pasillo)}."""
    pw = params["party_wall"]
    for pc in pieces:
        cw = ancho_de(pc, params)
        for e, (xe, banda) in extremos_al_frente(pc, params).items():
            fin = [u for u in units if u.get("_pc") is pc and u["side"] > 0 and
                   ((u["x1"] >= xe - 0.05) if e == 1 else (u["x0"] <= xe + 0.05))]
            if len(fin) != 1:
                continue
            u = fin[0]
            a, b = (u["x0"], xe) if e == 1 else (xe, u["x1"])
            if not fondo_frente() - 1e-6 <= b - a <= P.fondo_sin_tira() + 1.0:
                continue                                   # muy corta, o muy honda (unida a mano): sigue el pasillo
            ys = [q[1] for q in u["poly_local"]]
            poly = G.largest_part(G.clip_rect(pc["loc_plate"], a, b, -cw / 2, max(ys)))
            if not poly or not u["area"] + 0.9 * cw * (b - a) <= abs(G.area(poly)) <= \
                    u["area"] + (cw + pw) * (b - a) + 0.5:
                continue
            if (G.area(poly) > 0) != (G.area(u["poly_local"]) > 0):
                poly = poly[::-1]
            vecina = any(v is not u and v.get("_pc") is pc and v["side"] > 0 and
                         abs((v["x1"] + pw - a) if e == 1 else (b + pw - v["x0"])) < 0.05 for v in units)
            x_pas = (a - pw if vecina else a) if e == 1 else (b + pw if vecina else b)
            u.update({"poly_local": poly, "area": abs(G.area(poly)), "width": max(ys) + cw / 2, "depth": b - a,
                      "door_local": (x_pas, 0.0), "frente": {"e": e, "x": x_pas, "a": a, "b": b}})
            t = pc.setdefault("tramo", [pc["xa"], pc["xb"]])
            t[e] = x_pas


def entradas(units, pieces, params):
    """R3.7: donde el pasillo se cortó después de la última unión (circulation._puntas_tras_cruce), las viviendas del
    otro lado entran por el pasillo que queda: «entrada» = (lo, hi) del borde sobre el pasillo (marco de la pieza) y la
    puerta (door_local) ahí."""
    for pc in pieces:
        for pt in pc.get("puntas", []):
            for u in units:
                if u.get("_pc") is not pc or u["side"] != pt["lado"] or u.get("frente") or \
                        min(u["x1"], pt["s1"]) - max(u["x0"], pt["s0"]) < 0.05:
                    continue
                lo, hi = (u["x0"], pt["s0"]) if pt["e"] == 1 else (pt["s1"], u["x1"])
                u["entrada"] = (lo, hi)
                xd = min(max(u["door_local"][0], lo + P.HALL_W / 2), hi - P.HALL_W / 2) if hi - lo > P.HALL_W else \
                    (lo + hi) / 2.0
                u["door_local"] = (xd, u["door_local"][1])


def puntas_libres(units, pieces, params):
    """R3.7b: en cada punta libre del pasillo común (sin unión, núcleo ni conector en ella, y que no terminó en una
    vivienda al frente ni se cortó tras un cruce), la vivienda del extremo de cada lado anota «punta» = (lo, hi): el
    tramo de su borde sobre el pasillo junto a la punta, del ancho de un hall con su puerta (marco de la pieza).
    plans.layout_unit prueba ahí el hall y lo deja si el plano no empeora: así el pasillo termina en la última puerta
    y no sigue unos metros más sin servir a nadie."""
    S = ST.merged(params.get("standards"))
    largo = max(S["vivienda"]["hall"]["min_side"], S["vivienda"]["hall"]["typ"][0]) + S["equipamiento"]["puerta_entrada"] + 0.3
    for pc in pieces:
        if pc.get("between"):
            continue
        t = pc.get("tramo") or (pc["xa"], pc["xb"])
        for e in (0, 1):
            xe = t[e]
            if not pc["free"][e] or any(pt["e"] == e for pt in pc.get("puntas", [])):
                continue
            if any(c["box"][0] - 0.5 <= xe <= c["box"][2] + 0.5 for c in pc["cores"]):
                continue                                 # un núcleo en la punta: el pasillo llega hasta su puerta
            if any(abs(j["x"] - xe) < 1.0 for j in pc["junctions"]) or \
                    any(c0 - 0.5 <= xe <= c1 + 0.5 for _, c0, c1 in pc.get("conectores", [])):
                continue                                 # ahí llega otro pasillo
            lo, hi = (xe, xe + largo) if e == 0 else (xe - largo, xe)
            for u in units:
                if u.get("_pc") is not pc or u.get("frente") or u.get("entrada") or u.get("punta") or not u["side"]:
                    continue
                if (e == 0 and u["x0"] <= xe + 0.05) or (e == 1 and u["x1"] >= xe - 0.05):
                    u["punta"] = (max(lo, u["x0"]), min(hi, u["x1"]))


# ---------------------------------------------------------------- viviendas editadas (R4.4)
def vecinas(units, params):
    """Pares (a, b) de viviendas vecinas de una misma franja (mismo tramo de pasillo y lado): b sigue a a, del otro
    lado del tabique."""
    pw = params["party_wall"]
    return [(a, b) for a in units for b in units
            if a is not b and a.get("_region") is not None and a.get("_region") is b.get("_region")
            and abs(a["x1"] + pw - b["x0"]) < 0.01]


def _local(u, p):
    pc = u["_pc"]
    return G.to_local([tuple(p)], pc["origin"], pc["angle"])[0]


def _recortar(u, x0, x1, params):
    """La vivienda u pasa a ocupar [x0, x1] de su franja."""
    poly = G.largest_part(G.clip_rect(u["_region"], x0, x1))
    if not poly:
        return False
    ys = [q[1] for q in poly]
    u.update({"x0": x0, "x1": x1, "poly_local": poly, "area": abs(G.area(poly)), "width": x1 - x0,
              "depth": max(ys) - min(ys), "door_local": ((x0 + x1) / 2.0, _y_puerta(u["_pc"], params) * u["side"]),
              "editada": True})
    return True


def _tipo(u, params, conservar=False):
    """Tipo de una vivienda editada: el suyo si la superficie sigue cerca de su objetivo (tabique movido); si no, el
    del mix de superficie más parecida y, si ninguno se parece (±35 %), uno por sus dormitorios («1 dorm», «Monoambiente»)."""
    cerca = lambda t: bool(t) and abs(u["area"] - t) <= 0.35 * t
    if conservar and cerca(u.get("target")):
        return
    mix = [m for m in params["unit_mix"] if m.get("area", 0) > 0]
    m = min(mix, key=lambda t: abs(t["area"] - u["area"])) if mix else None
    if m and cerca(m["area"]):
        u["type"], u["target"] = m["name"], m["area"]
    else:
        nb = P.bedrooms_for(u["area"])
        u["type"], u["target"] = ("%d dorm" % nb if nb else "Monoambiente"), round(u["area"])


def _tabique_en(units, p, params, tol=0.75):
    """Las dos vecinas cuyo tabique pasa a menos de tol del punto p (de mundo), o None."""
    pw, mejor = params["party_wall"], None
    for a, b in vecinas(units, params):
        x, y = _local(a, p)
        ys = [q[1] for q in a["poly_local"] + b["poly_local"]]
        d = abs(x - (a["x1"] + pw / 2))
        if y * a["side"] > 0 and min(ys) - tol <= y <= max(ys) + tol and d <= tol and (mejor is None or d < mejor[0]):
            mejor = (d, a, b)
    return mejor[1:] if mejor else None


def _vivienda_en(units, p):
    """La vivienda que contiene el punto p (de mundo) o, si p cae fuera de la figura (vivienda en L), la de la franja
    que lo cubre a menos de 1 m; None si ninguna."""
    u = next((u for u in units if u.get("_region") is not None and G.point_in_poly(_local(u, p), u["poly_local"])), None)
    if u is None:
        cerca = []
        for v in units:
            x, y = _local(v, p) if v.get("_region") is not None else (None, 0)
            ys = [q[1] for q in v["poly_local"]]
            if x is not None and v["x0"] <= x <= v["x1"] and y * v["side"] > 0:
                cerca.append((max(0.0, min(ys) - y, y - max(ys)), id(v), v))
        u = min(cerca)[2] if cerca and min(cerca)[0] < 1.0 else None
    return u


def _fijos(pieces, nucleos):
    """Lo que ninguna vivienda puede pisar, en el mundo: los pasillos de todas las piezas (con sus conectores) y los
    núcleos."""
    W = lambda pc, pl: G.to_world(pl, pc["origin"], pc["angle"])
    return [W(pc, p) for pc in pieces for p in G.split_parts(pc["corridor_local"])] + \
        [list(e) for pc in pieces for e in pc["corridor_ext"]] + [list(c) for c in nucleos]


def obstaculos(pieces, nucleos):
    """R4.13b: lo que frena una vivienda que se extiende: los pasillos y núcleos (_fijos) y las zonas sin luz (codos y
    la zona central entre medianeras), en el mundo."""
    return _fijos(pieces, nucleos) + [list(d) for pc in pieces for k in ("dark", "codos") for d in pc.get(k, [])]


def _libre(u, units, fijos, params):
    """R4.13b: hasta dónde se puede estirar la vivienda u por cada punta de su franja, en el marco de su pieza:
    {0: x, 1: x}, con x <= x0 (hacia atrás) y x >= x1 (hacia adelante). El tope es lo primero que encuentra en la franja
    (_region, lo que generate_unit_mix repartió: ya sin los núcleos de su lado ni lo bloqueado por otras alas): otra
    vivienda (del otro lado del tabique), un pasillo, un núcleo, una zona sin luz (fijos, de obstaculos) o el fin de la
    franja. Una franja cóncava solo cuenta la parte pegada a la vivienda: _recortar se queda con una sola figura."""
    pc, reg, pw = u["_pc"], u.get("_region"), params["party_wall"]
    out = {0: u["x0"], 1: u["x1"]}
    if reg is None or u.get("frente"):
        return out                                       # al frente (R3.7): ya toma toda la punta del pasillo
    xs = [q[0] for q in reg]
    xmin, xmax = min(xs), max(xs)
    toca = lambda a, b: a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6
    L = lambda poly: G.to_local(poly, pc["origin"], pc["angle"])
    otros = [(L(G.to_world(v["poly_local"], v["_pc"]["origin"], v["_pc"]["angle"])), pw) for v in units if v is not u]
    otros += [(L(f), 0.0) for f in fijos if len(f) >= 3]
    for e, a, b in ((0, xmin, u["x0"]), (1, u["x1"], xmax)):
        if b - a < 1e-6:
            continue
        partes = G.split_parts(G.clip_rect(reg, a, b))
        borde = u["x0"] if e == 0 else u["x1"]              # la parte de la franja pegada a la vivienda
        S = next((q for q in partes if abs((G.bbox(q)[2] if e == 0 else G.bbox(q)[0]) - borde) < 0.01), None)
        if not S:
            continue
        bs = G.bbox(S)
        lim = bs[0] if e == 0 else bs[2]                    # el fin de la franja
        for o, gap in otros:
            if not toca(bs, G.bbox(o)):
                continue
            for q in G.subtract(S, [o])[1][0]:               # las partes del obstáculo dentro del tramo libre
                if abs(G.area(q)) > 0.01:
                    qx = [t[0] for t in q]
                    lim = max(lim, max(qx) + gap) if e == 0 else min(lim, min(qx) - gap)
        out[e] = min(lim, u["x0"]) if e == 0 else max(lim, u["x1"])
    return out


def extensibles(units, fijos, params, minimo=0.3):
    """R4.13b: anota en cada vivienda «extensible» = {"x0": {"largo", "p"}, "x1": {...}} con los lados de su franja donde
    hay planta libre de minimo m o más (ver _libre); p es un punto de mundo dentro de ese vacío (la web lo manda como
    «a» de la operación extender). Sin nada libre, {}."""
    for u in units:
        lib = _libre(u, units, fijos, params)
        u["extensible"] = {}
        for e, lado in ((0, "x0"), (1, "x1")):
            largo = (u["x0"] - lib[0]) if e == 0 else (lib[1] - u["x1"])
            if largo < minimo:
                continue
            x = (u["x0"] - largo / 2.0) if e == 0 else (u["x1"] + largo / 2.0)
            tajada = G.split_parts(G.clip_rect(u["_region"], x - 0.05, x + 0.05))
            if not tajada:
                continue
            cy = G.centroid(max(tajada, key=lambda q: abs(G.area(q))))[1]
            pw_ = G.to_world([(x, cy)], u["_pc"]["origin"], u["_pc"]["angle"])[0]
            u["extensible"][lado] = {"largo": round(largo, 2), "p": [round(pw_[0], 3), round(pw_[1], 3)]}


def editar_unidades(units, edits, params, hechos, fijos=None, fallidos=None):
    """R4.4: aplica en orden los cambios del usuario a las viviendas de un bloque (puntos de mundo):
    {"op": "tabique", "p", "a"} mueve hasta a el tabique que pasa por p; {"op": "fusionar", "p"} une las dos viviendas
    de ese tabique; {"op": "dividir", "p"} parte en dos, en p, la vivienda que contiene p. Cada parte conserva al menos
    la mitad del ancho mínimo. Anota en hechos los índices de los cambios aplicados (los demás se avisan).
    R4.13b: {"op": "extender", "p", "a"?} estira la vivienda que contiene p sobre la planta libre de su franja (ver
    _libre; fijos, de obstaculos: pasillos, núcleos y zonas sin luz) hacia el lado de a (la punta x0 o x1 más cercana a a)
    o, sin a, hacia los dos; conserva el tipo. Con menos de 0,30 m libres no se aplica y la vivienda va a fallidos
    (layout avisa «no hay planta libre al lado de Uxx»)."""
    pw, wmin = params["party_wall"], 0.5 * params["min_unit_width"]
    for k, e in enumerate(edits or []):
        op, p = e.get("op"), e.get("p")
        if k in hechos or not p:
            continue
        if op in ("tabique", "fusionar"):
            par = _tabique_en(units, p, params)
            if not par or (op == "tabique" and not e.get("a")):
                continue
            a, b = par
            if op == "tabique":
                x = min(max(_local(a, e["a"])[0], a["x0"] + wmin + pw / 2), b["x1"] - wmin - pw / 2)
                if x - pw / 2 <= a["x0"] or not (_recortar(a, a["x0"], x - pw / 2, params) and _recortar(b, x + pw / 2, b["x1"], params)):
                    continue
                _tipo(a, params, conservar=True)
                _tipo(b, params, conservar=True)
            else:
                if not _recortar(a, a["x0"], b["x1"], params):
                    continue
                _tipo(a, params)
                units.remove(b)
        elif op == "dividir":
            u = _vivienda_en(units, p)                 # punto fuera de la figura (vivienda en L): la de la franja que lo cubre
            if u is None or u["x1"] - u["x0"] < 2 * wmin + pw:
                continue
            x = min(max(_local(u, p)[0], u["x0"] + wmin + pw / 2), u["x1"] - wmin - pw / 2)
            otra = dict(u)
            if not (_recortar(otra, x + pw / 2, u["x1"], params) and _recortar(u, u["x0"], x - pw / 2, params)):
                continue
            _tipo(u, params)
            _tipo(otra, params)
            units.insert(units.index(u) + 1, otra)
        elif op == "extender":                         # R4.13b
            u = _vivienda_en(units, p)
            if u is None:
                continue
            lib = _libre(u, units, fijos or [], params)
            lados = (0, 1)
            if e.get("a"):                             # hacia el lado de a: la punta más cercana
                ax = _local(u, e["a"])[0]
                lados = (0,) if abs(ax - u["x0"]) < abs(ax - u["x1"]) else (1,)
            x0 = lib[0] if 0 in lados and u["x0"] - lib[0] >= 0.3 else u["x0"]
            x1 = lib[1] if 1 in lados and lib[1] - u["x1"] >= 0.3 else u["x1"]
            if (x0, x1) == (u["x0"], u["x1"]) or not _recortar(u, x0, x1, params):
                if fallidos is not None:
                    fallidos.append(u)
                continue
            _tipo(u, params, conservar=True)
        else:
            continue
        hechos.add(k)


def sin_solapes(units, pieces, nucleos, params):
    """Pasillos dibujados (R3.3): última comprobación. Una vivienda que pisa a otra anterior, un pasillo o un núcleo se
    recorta; si lo que queda es menos de la mitad, no va. Las reglas de uniones, codos y cruces ya evitan casi todos los
    solapes: esto cubre los casos que quedan (por ejemplo, tres líneas que se cruzan en un mismo punto)."""
    if not any(pc.get("user") for pc in pieces):
        return units, []
    W = lambda pc, pl: G.to_world(pl, pc["origin"], pc["angle"])
    toca = lambda a, b: a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6
    fijos = [(G.bbox(p), p) for p in _fijos(pieces, nucleos) if len(p) >= 3]
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
                          "depth": max(ys) - min(ys),
                          "door_local": ((x0 + x1) / 2.0, _y_puerta(pc, params) * u["side"])})
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


# ---------------------------------------------------------------- superficie con muros (R10.8)
def superficie_con_muros(polys, bordes, pasillos, nucleos, params, S=None, paso=0.25):
    """R10.8 (norma nacional, art. 3: la superficie de la vivienda se mide con los muros exteriores hasta su cara exterior
    y hasta el eje de los divisorios): cada tramo del contorno (de a unos `paso` m) se corre hacia afuera según lo que
    tiene del otro lado. Fachada (el borde de la planta o de un patio interior) y medianera (criterio del usuario: el muro
    entero): el muro exterior hasta su cara exterior, outer_wall. Otra vivienda: el eje del muro entre las dos,
    party_wall / 2. El pasillo común (a medio muro de la vivienda): el eje de ese muro, party_wall / 4. Un núcleo (su muro
    está dentro de su caja): el eje de ese muro, nucleo["muro"] / 2. Nada cerca (una zona sin luz, un rincón): un
    tabique, party_wall / 2. Con la vecina o el pasillo se mide la separación real (la sonda en que aparecen: pegados,
    a medio muro o a un muro) y se va hasta su mitad; con el núcleo, hasta la mitad de la separación más su muro. Un
    tramo es fachada si está entero sobre el borde de la planta, y los tramos también se cortan donde un vértice de la
    planta cae sobre el contorno (ahí cambia lo que hay del otro lado). En un rincón entrante de la planta (el codo de
    una L, la esquina de un patio), el cuadrado de muro exterior se parte por la bisectriz: cada vivienda cuenta la mitad
    junto a su fachada. polys: contornos de mundo de las viviendas; bordes[i]: los de la planta de la vivienda i
    (exterior y patios interiores); pasillos y núcleos: sus polígonos de mundo. Devuelve las superficies, en orden. Los
    puntos del desfase van desde el primer vértice de la vivienda (precisos con coordenadas UTM)."""
    ow, pw = params["outer_wall"], params["party_wall"]
    muro = (S or ST.merged(params.get("standards")))["nucleo"]["muro"]
    otros = [(G.bbox(p), p, "vivienda", i) for i, p in enumerate(polys) if len(p) >= 3] + \
        [(G.bbox(p), p, "pasillo", None) for p in pasillos if len(p) >= 3] + \
        [(G.bbox(p), p, "nucleo", None) for p in nucleos if len(p) >= 3]
    sondas = (0.05, pw / 2 + 0.05, pw + 0.05)
    lejos = max(sondas[-1], ow + 0.05) + 1e-6
    out = []
    for i, pl in enumerate(polys):
        poly = G.ensure_ccw(G.clean_rel(pl))           # sin quiebres mínimos ni puntas de ancho cero (redondeo)
        if len(poly) < 3:
            out.append(0.0)
            continue
        bx0, by0, bx1, by1 = G.bbox(poly)
        cerca = [o for o in otros if o[3] != i and o[0][0] <= bx1 + lejos and o[0][2] >= bx0 - lejos and
                 o[0][1] <= by1 + lejos and o[0][3] >= by0 - lejos]
        lazos = [(h, b) for h, b in enumerate(bordes[i]) if b and len(b) >= 3]     # h = 0: el contorno exterior
        en_borde = lambda q: any(_dist_to_boundary(q, lz) < 0.05 for _, lz in lazos)
        vert = [v for _, lz in lazos for v in lz if bx0 - 0.1 <= v[0] <= bx1 + 0.1 and by0 - 0.1 <= v[1] <= by1 + 0.1]
        ox, oy = poly[0]
        pts, ds = [], []
        for k in range(len(poly)):
            a, b = poly[k], poly[(k + 1) % len(poly)]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
            nx, ny = uy, -ux                                       # hacia afuera
            n = max(1, int(round(L / paso)))
            # los tramos: de a `paso` y cortados donde un vértice de la planta cae sobre el borde (ahí cambia la fachada)
            ts = sorted(set([j / float(n) for j in range(n)] +
                            [((v[0] - a[0]) * ux + (v[1] - a[1]) * uy) / L for v in vert
                             if abs((v[0] - a[0]) * nx + (v[1] - a[1]) * ny) < 0.05 and
                             0.02 < (v[0] - a[0]) * ux + (v[1] - a[1]) * uy < L - 0.02]))
            pt = lambda t: (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            prev = None
            for j, t0 in enumerate(ts):
                t1 = ts[j + 1] if j + 1 < len(ts) else 1.0
                m = pt((t0 + t1) / 2)
                if en_borde(pt(t0)) and en_borde(m) and en_borde(pt(t1)):
                    d = ow                                         # fachada o medianera (el tramo entero sobre el borde)
                    q = (m[0] + nx * (ow + 0.05), m[1] + ny * (ow + 0.05))
                    if any(o[2] == "pasillo" and o[0][0] <= q[0] <= o[0][2] and o[0][1] <= q[1] <= o[0][3] and
                           G.point_in_poly(q, o[1]) for o in cerca):
                        d = ow / 2                                 # R3.8: la galería detrás del muro: como un pasillo
                else:                                              #   común, hasta el eje de ese muro
                    d = pw / 2                                     # otra vivienda, o nada: un tabique
                    for t in sondas:
                        q = (m[0] + nx * t, m[1] + ny * t)
                        tipo = next((o[2] for o in cerca if o[0][0] <= q[0] <= o[0][2] and o[0][1] <= q[1] <= o[0][3]
                                     and G.point_in_poly(q, o[1])), None)
                        if tipo:                           # la separación: 0, medio muro o un muro (sin muro: 0)
                            hueco = round((t - sondas[0]) / (pw / 2)) * (pw / 2) if pw > 1e-9 else 0.0
                            d = (hueco + muro) / 2 if tipo == "nucleo" else hueco / 2
                            break
                if prev is None or abs(prev - d) > 1e-9:
                    pts.append((a[0] - ox + (b[0] - a[0]) * t0, a[1] - oy + (b[1] - a[1]) * t0))
                    ds.append(d)
                    prev = d
        con = G.desfase(pts, ds)
        out.append(abs(G.area(con)) - _rincones(con, poly, lazos, ow, (ox, oy)))
    return out


def _rincones(con, poly, lazos, ow, o):
    """R10.8: lo que superficie_con_muros quita del polígono con muros con (desde el punto o) de la vivienda poly en los
    rincones entrantes de la planta (lazos: [(h, contorno)], h = 0 el exterior): el cuadrado de muro exterior del rincón
    se parte por la bisectriz y la vivienda que llega por un solo lado no cuenta la mitad del otro (la cuenta la vecina)."""
    ox, oy = o
    rel = [(p[0] - ox, p[1] - oy) for p in poly]
    sobre = lambda q: _dist_to_boundary(q, rel) < 0.03
    quita = 0.0
    for h, lz in lazos:
        lz = G.ensure_ccw([(p[0] - ox, p[1] - oy) for p in lz])
        if h:
            lz = lz[::-1]                                  # un patio: la planta, a la izquierda
        for k in range(len(lz)):
            p0, P_, p2 = lz[k - 1], lz[k], lz[(k + 1) % len(lz)]
            if _dist_to_boundary(P_, rel) > 0.03:
                continue
            l1, l2 = math.hypot(P_[0] - p0[0], P_[1] - p0[1]), math.hypot(p2[0] - P_[0], p2[1] - P_[1])
            if l1 < 1e-9 or l2 < 1e-9:
                continue
            d1 = ((P_[0] - p0[0]) / l1, (P_[1] - p0[1]) / l1)
            d2 = ((p2[0] - P_[0]) / l2, (p2[1] - P_[1]) / l2)
            den = d1[0] * d2[1] - d1[1] * d2[0]
            if den > -1e-6:
                continue                                   # no es un rincón entrante
            q1 = (P_[0] + ow * d1[1], P_[1] - ow * d1[0])  # la cara exterior de cada muro, junto al rincón
            q2 = (P_[0] + ow * d2[1], P_[1] - ow * d2[0])
            t = ((q2[0] - q1[0]) * d2[1] - (q2[1] - q1[1]) * d2[0]) / den
            F = (q1[0] + t * d1[0], q1[1] + t * d1[1])     # la esquina exterior: la bisectriz va de P_ a F
            e = min(0.1, l1 / 2, l2 / 2)
            por1, por2 = sobre((P_[0] - d1[0] * e, P_[1] - d1[1] * e)), sobre((P_[0] + d2[0] * e, P_[1] + d2[1] * e))
            if por1 == por2:
                continue                                   # por los dos lados (o por ninguno): el cuadrado es suyo
            tri = G.ensure_ccw([P_, F, q1] if por1 else [P_, q2, F])     # la mitad del lado que no es suyo
            c = con
            for r in range(3):
                A, B = tri[r], tri[(r + 1) % 3]
                c = G.clip_halfplane(c, -(B[1] - A[1]), B[0] - A[0], -(B[1] - A[1]) * A[0] + (B[0] - A[0]) * A[1])
            quita += abs(G.area(c)) if len(c) >= 3 else 0.0
    return quita


# ---------------------------------------------------------------- planos de unidad
def bedrooms_for(area):
    return P.bedrooms_for(area)


def unit_rooms(u, params, pc=None, plate=None, ediciones=None):
    """Distribuye una unidad (ver engine/plans.py) y devuelve el resultado en el marco local de la pieza. ediciones
    (R5.7): [(k, cambio con puntos de mundo)]; se aplican los que caen en esta vivienda (en "ediciones", las k)."""
    side = u["side"]
    cw = ancho_de(pc or u.get("_pc") or {}, params)    # R10.8: el ancho del pasillo de su tramo
    pw = params["party_wall"]
    galeria = bool((pc or u.get("_pc") or {}).get("galeria"))    # R3.8: el pasillo común está del otro lado del muro
    y_in = cw / 2 + (params["outer_wall"] if galeria else pw / 2)
    fr = u.get("frente")
    if fr:                                     # R3.7: al frente, v desde la punta del pasillo; la puerta, en 0 <= x <= cw
        xh, sg = (fr["a"], 1) if fr["e"] == 1 else (fr["b"], -1)
        ida = lambda pt: (pt[1] + cw / 2, sg * (pt[0] - xh))
        back = lambda pt: (xh + sg * pt[1], pt[0] - cw / 2)
        refleja = sg > 0
        entrada, punta = (0.0, cw), None
    else:
        ida = lambda pt: (pt[0], side * pt[1] - y_in)            # unidad en v>=0, v=0 junto al pasillo
        back = lambda pt: (pt[0], side * (pt[1] + y_in))
        refleja = side < 0
        entrada = u.get("entrada")
        punta = u.get("punta")                 # R3.7b: la vivienda del extremo de una punta libre: la puerta, en la punta
    poly = [ida(p) for p in u["poly_local"]]
    if refleja:
        poly = poly[::-1]
    spec = next((m for m in params["unit_mix"] if m.get("name") == u["type"]), {})
    nb = int(spec["dorms"]) if spec.get("dorms") is not None else P.bedrooms_for(u.get("target") or u["area"])
    is_fac = None
    if pc is not None and plate:
        bl, pd = params.get("_blind"), params.get("_patio_dark")
        bordes = [plate] + list(params.get("_huecos") or [])      # fachada exterior y caras a los patios interiores

        def is_fac(p, q):
            if galeria and abs(p[1]) < 0.05 and abs(q[1]) < 0.05:
                return False                            # R3.8: el borde sobre la galería no es fachada (sin ventanas)
            for t_ in (0.25, 0.5, 0.75):
                m = (p[0] + (q[0] - p[0]) * t_, p[1] + (q[1] - p[1]) * t_)
                w = G.to_world([back(m)], pc["origin"], pc["angle"])[0]
                if min(_dist_to_boundary(w, b) for b in bordes) > 0.4 or (bl and bl(w)) or (pd and pd(w)):
                    return False
            return True
        muro = params["outer_wall"]

        def ventana(p, q):
            """R5.5: p-q (con la estancia a la izquierda) está sobre la fachada y del otro lado del muro hay aire: ni
            planta ni otra ala a menos del espesor del muro (junto a una esquina entrante, el muro sigue hacia la otra)."""
            if galeria and abs(p[1]) < 0.05 and abs(q[1]) < 0.05:
                return False                            # R3.8: sobre la galería no hay ventanas
            L = ((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2) ** 0.5
            n = ((q[1] - p[1]) / L, -(q[0] - p[0]) / L)
            for t_ in (0.25, 0.5, 0.75):
                m = (p[0] + (q[0] - p[0]) * t_, p[1] + (q[1] - p[1]) * t_)
                w = G.to_world([back(m)], pc["origin"], pc["angle"])[0]
                a = G.to_world([back((m[0] + n[0] * (muro + 0.05), m[1] + n[1] * (muro + 0.05)))], pc["origin"],
                               pc["angle"])[0]
                if min(_dist_to_boundary(w, b) for b in bordes) > 0.05 or (bl and bl(w)) or (pd and pd(w)) or \
                        min(_dist_to_boundary(a, b) for b in bordes) < muro + 0.04 or \
                        (G.point_in_poly(a, plate) and not any(G.point_in_poly(a, h) for h in bordes[1:])):
                    return False
            return True
        is_fac.ventana = ventana
    mias = []
    if ediciones and pc is not None:                # R5.7: los cambios cuyo punto cae en esta vivienda, en su marco
        def marco(w):
            return ida(G.to_local([w], pc["origin"], pc["angle"])[0])
        for k, e in ediciones:
            q = marco(e["p"])
            if G.point_in_poly(q, poly) or _dist_to_boundary(q, poly) < 0.05:
                mias.append((k, dict(e, p=q, a=marco(e["a"]) if e.get("a") else None)))
    S = ST.merged(params.get("standards"))
    res = P.layout_unit(poly, nb, is_fac, S["vivienda"], S["equipamiento"], bool(spec.get("accesible")), mias,
                        S["ventanas"], entrada, bool(spec.get("vestidor")), punta=punta)

    def back_poly(pl):
        out = [back(p) for p in pl]
        return out[::-1] if refleja else out
    for r in res["rooms"]:
        r["poly_local"] = back_poly(r.pop("poly"))
    for q in res["equipamiento"]:
        q["poly"] = back_poly(q["poly"])
        q["lines"] = [[back(p) for p in ln] for ln in q["lines"]]
    res["paredes"] = [(back(a), back(b)) for a, b in res["paredes"]]
    t = params["outer_wall"]                        # R5.5: la ventana, en el espesor del muro exterior
    for w in res["ventanas"]:
        p, q, n = w.pop("p"), w.pop("q"), w.pop("n")
        afuera = lambda pt, f: (pt[0] + n[0] * t * f, pt[1] + n[1] * t * f)
        w["poly"] = back_poly([p, q, afuera(q, 1), afuera(p, 1)])
        w["lines"] = [[back(afuera(p, f)), back(afuera(q, f))] for f in (1 / 3.0, 2 / 3.0)]     # el vidrio
        w["seg"] = [back(p), back(q)]
    for d in res["doors"]:
        d["p"], d["q"] = back(d["p"]), back(d["q"])
        d["into"] = d["into"] * (side if not d["vertical"] else 1)
    for n in res["graph"]["nodes"]:
        n["pos"] = back(n["pos"])
    res["sin_uso"] = [back_poly(pl) for pl in res["sin_uso"]]
    return res
