"""Equipamiento de la vivienda (F5): artefactos de baño, cocina y lavadero dentro de las estancias de plans.py.

Marco de la vivienda (el de plans.py): x a lo largo de la fachada, v en profundidad; cada estancia es un rectángulo
(x0, v0, x1, v1). Un artefacto ocupa un módulo apoyado contra una pared maciza de su estancia (no contra un borde abierto a
otra estancia ni sobre una puerta), no pisa el barrido de las puertas ni a otro artefacto, y deja libre delante su paso.
Las medidas vienen de standards.DEFAULTS["equipamiento"] (editables en la web). Lo que no entra se avisa en la ficha.
"""
import itertools
import math

TOL = 1e-6
NOMBRES = {"inodoro": "Inodoro", "bide": "Bidé", "lavatorio": "Lavatorio", "ducha": "Ducha", "heladera": "Heladera",
           "mesada": "Mesada", "bacha_cocina": "Bacha", "cocina_horno": "Cocina y horno", "lavarropas": "Lavarropas",
           "pileta_lavar": "Pileta"}
_memo = {}


# ---------------------------------------------------------------- geometría de paredes y módulos
def _lados(r):
    """Las cuatro paredes de un rectángulo, en sentido antihorario: (inicio, dirección, normal hacia adentro, largo)."""
    x0, v0, x1, v1 = r
    return [((x0, v0), (1, 0), (0, 1), x1 - x0), ((x1, v0), (0, 1), (-1, 0), v1 - v0),
            ((x1, v1), (-1, 0), (0, -1), x1 - x0), ((x0, v1), (0, -1), (1, 0), v1 - v0)]


def _en_lado(p, q, lado, tol=0.03):
    """Tramo [a, b] de la pared que ocupa el segmento p-q, si está sobre ella."""
    (ax, av), (dx, dv), _, L = lado
    t = lambda pt: (pt[0] - ax) * dx + (pt[1] - av) * dv
    perp = lambda pt: abs((pt[0] - ax) * dv - (pt[1] - av) * dx)
    if perp(p) > tol or perp(q) > tol:
        return None
    a, b = sorted((t(p), t(q)))
    a, b = max(a, 0.0), min(b, L)
    return (a, b) if b - a > TOL else None


def _libres(L, ocupados):
    """Tramos libres de [0, L] sin los ocupados."""
    out, x = [], 0.0
    for a, b in sorted(ocupados):
        if a > x + TOL:
            out.append((x, a))
        x = max(x, b)
    if L > x + TOL:
        out.append((x, L))
    return out


def _caja(lado, t, w, n0, n1):
    """Rectángulo de la franja [t, t+w] a lo largo de la pared, entre n0 y n1 de la pared hacia adentro."""
    (ax, av), (dx, dv), (nx, nv), _ = lado
    pts = [(ax + dx * s + nx * n, av + dv * s + nv * n) for s in (t, t + w) for n in (n0, n1)]
    xs, vs = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(vs), max(xs), max(vs))


def _choca(a, b):
    return a[0] < b[2] - TOL and b[0] < a[2] - TOL and a[1] < b[3] - TOL and b[1] < a[3] - TOL


def _dentro(a, r):
    return a[0] >= r[0] - TOL and a[1] >= r[1] - TOL and a[2] <= r[2] + TOL and a[3] <= r[3] + TOL


def _centro(c):
    return ((c[0] + c[2]) / 2, (c[1] + c[3]) / 2)


def _dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


# ---------------------------------------------------------------- símbolos (coordenadas del módulo: s a lo largo, n hacia adentro)
def _elipse(cs, cn, rs, rn, k=16):
    return [(cs + rs * math.cos(2 * math.pi * i / k), cn + rn * math.sin(2 * math.pi * i / k)) for i in range(k + 1)]


def _rect(s0, n0, s1, n1):
    return [(s0, n0), (s1, n0), (s1, n1), (s0, n1), (s0, n0)]


def _dibujo(kind, w, d):
    if kind == "inodoro":
        ow = min(w, 0.40)
        s0 = (w - ow) / 2
        return [_rect(s0, 0.0, s0 + ow, 0.18), _elipse(w / 2, 0.18 + (d - 0.18) / 2, ow / 2 * 0.95, (d - 0.18) / 2 * 0.9)]
    if kind == "bide":
        ow = min(w, 0.38)
        return [_elipse(w / 2, d / 2 + 0.03, ow / 2, d / 2 * 0.8), _elipse(w / 2, 0.14, 0.03, 0.03, 8)]
    if kind == "lavatorio":
        return [_elipse(w / 2, d / 2, w * 0.3, d * 0.32)]
    if kind == "ducha":
        return [[(0.0, 0.0), (w, d)], [(w, 0.0), (0.0, d)], _elipse(w / 2, d / 2, 0.04, 0.04, 8)]
    if kind == "heladera":
        return [[(0.0, d), (w, 0.0)]]
    if kind == "bacha_cocina":
        return [_rect(0.08, 0.08, w - 0.08, d - 0.12)]
    if kind == "cocina_horno":
        r = min(w, d) * 0.14
        return [_elipse(w * a, d * b, r, r, 12) for a in (0.28, 0.72) for b in (0.3, 0.7)]
    if kind == "lavarropas":
        return [_elipse(w / 2, d / 2, min(w, d) * 0.36, min(w, d) * 0.36)]
    if kind == "pileta_lavar":
        return [_rect(0.06, 0.06, w - 0.06, d - 0.08)]
    return []


def _pieza(kind, lado, t, w, d, room):
    """El artefacto en el marco de la vivienda: contorno y dibujo."""
    (ax, av), (dx, dv), (nx, nv), _ = lado
    m = lambda s, n: (round(ax + dx * (t + s) + nx * n, 4), round(av + dv * (t + s) + nv * n, 4))
    return {"kind": kind, "name": NOMBRES[kind], "room": room,
            "poly": [m(0.0, 0.0), m(w, 0.0), m(w, d), m(0.0, d)],
            "lines": [[m(s, n) for s, n in ln] for ln in _dibujo(kind, w, d)]}


# ---------------------------------------------------------------- colocación
def _paredes(r, aberturas, puertas):
    """Paredes de r con sus tramos libres (sin bordes abiertos ni puertas) y las zonas que las puertas dejan libres."""
    lados, zonas = _lados(r), []
    ocup = [[] for _ in lados]
    for p, q in aberturas:
        for i, ld in enumerate(lados):
            tr = _en_lado(p, q, ld)
            if tr:
                ocup[i].append(tr)
    for p, q, ancho, adentro in puertas:
        for i, ld in enumerate(lados):
            tr = _en_lado(p, q, ld)
            if tr:
                ocup[i].append(tr)
                prof = ancho if adentro else 0.60      # barrido de la hoja, o el paso para cruzar la puerta
                zonas.append(_caja(ld, tr[0], tr[1] - tr[0], 0.0, prof))
    return [(ld, _libres(ld[3], oc)) for ld, oc in zip(lados, ocup)], zonas


def _candidatos(libres, w, paso=0.10):
    for i, (ld, tramos) in enumerate(libres):
        for a, b in tramos:
            if b - a + TOL < w:
                continue
            ts = {round(a, 4), round(b - w, 4)} | {round(a + k * paso, 4) for k in range(int((b - w - a) / paso) + 1)}
            for t in sorted(ts):
                yield i, ld, t


def _colocar(r, libres, zonas, modulos, preferir, previos=()):
    """Coloca en orden los módulos (kind, w, d, paso) contra las paredes libres de r, cada uno donde preferir() da menos,
    sin pisar los previos ni su paso. Devuelve los colocados [(kind, lado, t, w, d, caja, frente)] y los que no entraron."""
    puestos, faltan = list(previos), []
    for kind, w, d, paso in modulos:
        mejor = None
        for i, ld, t in _candidatos(libres, w):
            caja = _caja(ld, t, w, 0.0, d)
            frente = _caja(ld, t, w, d, d + paso)
            if not (_dentro(caja, r) and _dentro(frente, r)):
                continue
            if any(_choca(caja, z) for z in zonas) or any(_choca(caja, o[5]) or _choca(caja, o[6]) or _choca(frente, o[5])
                                                          for o in puestos):
                continue
            pr = preferir(kind, caja, puestos)
            if mejor is None or pr < mejor[0] - 1e-9:
                mejor = (pr, (kind, ld, t, w, d, caja, frente))
        if mejor:
            puestos.append(mejor[1])
        else:
            faltan.append(kind)
    return puestos[len(previos):], faltan


def _medida(m):
    return "%.2f × %.2f m" % (m[1], m[2])


def _bano(r, libres, zonas, puerta, S, con_bide):
    """Ducha, inodoro y lavatorio (y bidé si entra) en el baño. La ducha va primero: de pared a pared en una pared corta
    (lo habitual en un baño angosto) o en su módulo; se entra a ella por el paso de los demás artefactos."""
    paso, (dw, dd) = S["paso_bano"], S["ducha"]
    mod = {k: (k, S[k][0], S[k][1], paso) for k in ("inodoro", "lavatorio", "bide")}

    def preferir(kind, caja, puestos):
        c = _centro(caja)
        if kind == "bide":
            ino = [o for o in puestos if o[0] == "inodoro"]
            return _dist(c, _centro(ino[0][5])) if ino else 0.0
        if kind == "lavatorio":
            return _dist(c, puerta)                    # el lavatorio, cerca de la puerta
        return -_dist(c, puerta)                       # ducha e inodoro, lejos de la puerta
    variantes = [([(ld, tr)], ("ducha", ld[3], dd, 0.0)) for ld, tr in libres          # de pared a pared
                 if ld[3] <= 1.9 * dw and any(a < TOL and b > ld[3] - TOL for a, b in tr)]
    variantes.append((libres, ("ducha", dw, dd, 0.0)))
    mejor = None
    for lib_d, mod_d in variantes:
        ducha, f = _colocar(r, lib_d, zonas, [mod_d], preferir)
        for orden in itertools.permutations(("inodoro", "lavatorio")):
            puestos, faltan = _colocar(r, libres, zonas, [mod[k] for k in orden], preferir, ducha)
            faltan = f + faltan
            if not faltan:
                puestos = ducha + puestos
                if con_bide:                          # el bidé, si entra (no es obligatorio)
                    puestos += _colocar(r, libres, zonas, [mod["bide"]], preferir, puestos)[0]
                return puestos, []
            if mejor is None or len(faltan) < len(mejor[1]):
                mejor = (ducha + puestos, faltan)
    return mejor[0], [mod.get(k) or ("ducha", dw, dd) for k in mejor[1]]


def _cocina(r, libres, zonas, S):
    """Mesada corrida contra una pared maciza: heladera, bacha, mesada de trabajo y cocina-horno, con el paso delante.
    Si no entra en línea, la heladera va en otra pared (en L)."""
    f, paso = S["mesada_fondo"], S["paso_cocina"]
    hw, hd = S["heladera"]
    bw, cw, tw = S["bacha_cocina"], S["cocina_horno"], S["mesada_trabajo"]
    tramos = sorted(((b - a, i, ld, a, b) for i, (ld, tr) in enumerate(libres) for a, b in tr), reverse=True)

    def corrida(ld, a, b, con_heladera):
        """Piezas de la mesada en el tramo [a, b] de la pared, o None si no entra."""
        largo = b - a
        nec = (hw if con_heladera else 0.0) + bw + tw + cw
        caja = _caja(ld, a, largo, 0.0, max(f, hd if con_heladera else f))
        frente = _caja(ld, a, largo, f, f + paso)
        if largo + TOL < nec or not _dentro(frente, r) or any(_choca(caja, z) for z in zonas):
            return None
        sobra = largo - nec
        t = a
        out = []
        if con_heladera:
            out.append(("heladera", t, hw, hd))
            t += hw
        out.append(("mesada", t, b - t, f))            # la mesada va de la heladera al final del tramo
        t += min(0.30, sobra / 3)
        out.append(("bacha_cocina", t, bw, f))
        t += bw + tw + sobra / 3
        out.append(("cocina_horno", t, cw, f))
        return out
    for _, i, ld, a, b in tramos:                     # en línea, en el tramo más largo que alcance
        pz = corrida(ld, a, b, True)
        if pz:
            return [(k, ld, t, w, d) for k, t, w, d in pz], []
    for _, i, ld, a, b in tramos:                     # en L: la mesada en un tramo y la heladera en otro
        pz = corrida(ld, a, b, False)
        if not pz:
            continue
        caja = _caja(ld, a, b - a, 0.0, f)
        resto = [(l2, [tr for tr in trs]) for j, (l2, trs) in enumerate(libres) if j != i]
        hel, falta = _colocar(r, resto, zonas + [caja, _caja(ld, a, b - a, f, f + paso)], [("heladera", hw, hd, paso)],
                              lambda k, c, p: 0.0)
        if not falta:
            o = hel[0]
            return [(k, ld, t, w, d) for k, t, w, d in pz] + [(o[0], o[1], o[2], o[3], o[4])], []
    for _, i, ld, a, b in tramos:                     # la mesada sola: falta la heladera
        pz = corrida(ld, a, b, False)
        if pz:
            return [(k, ld, t, w, d) for k, t, w, d in pz], ["la heladera (%.2f × %.2f m)" % (hw, hd)]
    return [], ["la mesada con bacha y cocina (%.2f m en línea, con %.2f m de paso delante)" % (bw + tw + cw, paso)]


def _lavadero(r, libres, zonas, puerta, S):
    paso = S["paso_lavadero"]
    pref = lambda k, c, p: -_dist(_centro(c), puerta)
    puestos, faltan = _colocar(r, libres, zonas, [("lavarropas",) + tuple(S["lavarropas"]) + (paso,),
                                                  ("pileta_lavar",) + tuple(S["pileta_lavar"]) + (paso,)], pref)
    return puestos, [("lavarropas" if k == "lavarropas" else "pileta_lavar") for k in faltan]


def _tipo(rm):
    if rm["kind"] == "kitchen" or (rm["kind"] == "hall" and "Cocina" in rm["name"]):
        return "cocina"
    return rm["kind"] if rm["kind"] in ("bath", "laundry") else None


def resolver(rm, puertas, aberturas, S):
    """Artefactos de una estancia (con memoria: estancias iguales se resuelven una vez). Devuelve (piezas en el marco
    de la estancia trasladada al origen, textos de lo que no entra)."""
    x0, v0, x1, v1 = rm["rect"]
    rel = lambda pt: (round(pt[0] - x0, 4), round(pt[1] - v0, 4))
    pts = tuple(sorted((rel(d["p"]), rel(d["q"]), round(d["ancho"], 3), d["b"] == rm["id"])
                       for d in puertas if rm["id"] in (d["a"], d["b"])))
    abre = tuple(sorted((rel(p), rel(q)) for p, q in aberturas.get(rm["id"], [])))
    clave = (_tipo(rm), rm["id"] == "bath1", round(x1 - x0, 4), round(v1 - v0, 4), pts, abre,
             tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in S.items())))
    if clave not in _memo:
        if len(_memo) > 4000:
            _memo.clear()
        _memo[clave] = _equipar_estancia(clave[0], clave[1], (0.0, 0.0, x1 - x0, v1 - v0), pts, abre, S)
    return _memo[clave]


def equipar(rooms, puertas, aberturas, S, nb):
    """Artefactos de baños, cocina y lavadero. rooms: [{id, kind, name, rect}]; puertas: [{p, q, a, b, ancho}] (la hoja
    abre hacia b); aberturas: {id: [(p, q)]} bordes abiertos a otra estancia. Devuelve (piezas, comprobaciones)."""
    piezas, checks = [], []
    for rm in rooms:
        if not _tipo(rm):
            continue
        name, (x0, v0, _, _) = rm["name"], rm["rect"]
        hechas, faltan, info = resolver(rm, puertas, aberturas, S)
        mover = lambda pt: (round(pt[0] + x0, 4), round(pt[1] + v0, 4))
        for k, ld, t, w, d in hechas:
            pz = _pieza(k, ld, t, w, d, rm["id"])
            pz["poly"] = [mover(p) for p in pz["poly"]]
            pz["lines"] = [[mover(p) for p in ln] for ln in pz["lines"]]
            piezas.append(pz)
        for txt in faltan:
            checks.append({"ok": False, "msg": "%s: no entra %s" % (name, txt)})
        for txt in info:
            checks.append({"ok": True, "info": True, "msg": "%s: %s" % (name, txt)})
    return piezas, checks


def _equipar_estancia(tipo, principal, r, puertas, aberturas, S):
    """Una estancia en su propio origen (para reusar el resultado en estancias iguales)."""
    libres, zonas = _paredes(r, aberturas, [(p, q, ancho, adentro) for p, q, ancho, adentro in puertas])
    puerta = _centro((min(puertas[0][0][0], puertas[0][1][0]), min(puertas[0][0][1], puertas[0][1][1]),
                      max(puertas[0][0][0], puertas[0][1][0]), max(puertas[0][0][1], puertas[0][1][1]))) \
        if puertas else _centro(r)
    info = []
    if tipo == "bath":
        puestos, faltan = _bano(r, libres, zonas, puerta, S, principal)
        if faltan and not principal:                  # un segundo baño donde no entra todo: toilette (sin ducha)
            paso = S["paso_bano"]
            tl, f2 = _colocar(r, libres, zonas, [("inodoro",) + tuple(S["inodoro"]) + (paso,),
                                                 ("lavatorio",) + tuple(S["lavatorio"]) + (paso,)],
                              lambda k, c, p: _dist(_centro(c), puerta) * (1 if k == "lavatorio" else -1))
            if not f2:
                puestos, faltan = tl, []
                info.append("sin lugar para la ducha: queda como toilette (inodoro y lavatorio)")
        txt = ["%s (%s)" % ({"ducha": "la ducha", "inodoro": "el inodoro", "lavatorio": "el lavatorio"}[m[0]], _medida(m))
               for m in faltan]
    elif tipo == "cocina":
        hechas, txt = _cocina(r, libres, zonas, S)
        return hechas, txt, info
    else:
        puestos, fal = _lavadero(r, libres, zonas, puerta, S)
        txt = ["%s (%.2f × %.2f m)" % ("el lavarropas" if k == "lavarropas" else "la pileta", S[k][0], S[k][1]) for k in fal]
    return [(o[0], o[1], o[2], o[3], o[4]) for o in puestos], txt, info
