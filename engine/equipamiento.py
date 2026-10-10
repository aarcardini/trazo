"""Equipamiento de la vivienda (F5): artefactos de baño, cocina y lavadero y muebles de dormitorios, estar y comedor,
dentro de las estancias de plans.py.

Marco de la vivienda (el de plans.py): x a lo largo de la fachada, v en profundidad; cada estancia es un rectángulo
(x0, v0, x1, v1). Un artefacto ocupa un módulo apoyado contra una pared maciza de su estancia (no contra un borde abierto a
otra estancia ni sobre una puerta), no pisa el barrido de las puertas ni a otro artefacto, y deja libre delante su paso.
Los muebles son módulos compuestos: la cama con sus mesas de luz y el paso a los lados y al pie, el sofá frente al rack de
TV, la mesa con el lugar de las sillas. No van delante de las aberturas al hall, al pasillo ni a la cocina; el placard y el
rack no van contra una ventana; y desde cada puerta o abertura se llega a todos (_alcanza).
Las medidas vienen de standards.DEFAULTS["equipamiento"] (editables en la web). Lo que no entra se avisa en la ficha.
"""
import itertools
import math

from . import geometry as G

TOL = 1e-6
NOMBRES = {"inodoro": "Inodoro", "bide": "Bidé", "lavatorio": "Lavatorio", "ducha": "Ducha", "heladera": "Heladera",
           "mesada": "Mesada", "bacha_cocina": "Bacha", "cocina_horno": "Cocina y horno", "lavarropas": "Lavarropas",
           "pileta_lavar": "Pileta", "cama_doble": "Cama doble", "cama_individual": "Cama individual",
           "mesita": "Mesa de luz", "placard": "Placard", "mesa": "Mesa", "silla": "Silla", "sofa": "Sofá",
           "butaca": "Butaca", "rack_tv": "Rack de TV", "ducha_nivel": "Ducha a nivel", "giro": "Círculo de giro"}
MUEBLES = ("dormitorio", "estar", "comedor")
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
    """Rectángulo de la franja [t, t+w] a lo largo de la pared, entre n0 y n1 de la pared hacia adentro (las paredes son
    paralelas a los ejes: dos esquinas opuestas alcanzan)."""
    (ax, av), (dx, dv), (nx, nv), _ = lado
    xa, va = ax + dx * t + nx * n0, av + dv * t + nv * n0
    xb, vb = ax + dx * (t + w) + nx * n1, av + dv * (t + w) + nv * n1
    return (min(xa, xb), min(va, vb), max(xa, xb), max(va, vb))


def _choca(a, b):
    return a[0] < b[2] - TOL and b[0] < a[2] - TOL and a[1] < b[3] - TOL and b[1] < a[3] - TOL


class _Estancia(tuple):
    """El rectángulo (x0, v0, x1, v1) de una estancia. forma: su contorno real cuando un muro oblicuo la recorta (los
    artefactos tienen que quedar dentro de él); None si es el rectángulo entero. fuera: cajas de lo que queda del
    rectángulo fuera de la forma (solo cerca de ellas hace falta mirar la forma)."""
    forma = None
    fuera = ()


def _estancia(w, d, forma=None):
    r = _Estancia((0.0, 0.0, w, d))
    if forma:
        r.forma = list(forma)
        partes = G.subtract([(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)], [r.forma])[0]
        r.fuera = [(min(x for x, _ in e), min(y for _, y in e), max(x for x, _ in e), max(y for _, y in e)) for e, _ in partes]
    return r


def _cerca(p, r, h=0.0):
    """¿El punto p está a menos de h de lo que queda fuera de la forma (donde hay que mirar la forma de cerca)?"""
    return any(b[0] - h - TOL < p[0] < b[2] + h + TOL and b[1] - h - TOL < p[1] < b[3] + h + TOL for b in r.fuera)


def _en_poligono(p, f, tol=1e-4):
    """¿El punto p está dentro del polígono f o sobre su borde?"""
    x, y = p
    adentro = False
    for (x1, y1), (x2, y2) in zip(f, f[1:] + f[:1]):
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        k = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / L2)) if L2 > 0 else 0.0
        if math.hypot(x - x1 - k * dx, y - y1 - k * dy) <= tol:
            return True
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * dx / dy:
            adentro = not adentro
    return adentro


def _dentro(a, r):
    """¿La caja a está dentro de la estancia r: de su rectángulo y, si la recorta un muro oblicuo, de su contorno?"""
    if a[0] < r[0] - TOL or a[1] < r[1] - TOL or a[2] > r[2] + TOL or a[3] > r[3] + TOL:
        return False
    f = getattr(r, "forma", None)
    if f is None or not any(_choca(a, b) for b in r.fuera):
        return True
    return all(_en_poligono(p, f) for p in ((a[0], a[1]), (a[2], a[1]), (a[2], a[3]), (a[0], a[3]))) and \
        not any(a[0] + 1e-4 < x < a[2] - 1e-4 and a[1] + 1e-4 < y < a[3] - 1e-4 for x, y in f)


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
    if kind == "ducha_nivel":                                                    # con asiento rebatible contra la pared
        return [[(0.0, 0.0), (w, d)], [(w, 0.0), (0.0, d)], _elipse(w / 2, d / 2, 0.04, 0.04, 8),
                _rect(w - 0.45, 0.02, w - 0.05, 0.40)]
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
    if kind in ("cama_doble", "cama_individual"):
        k = 2 if kind == "cama_doble" else 1
        a = (w - 0.10 * (k + 1)) / k
        return [_rect(0.10 + j * (a + 0.10), 0.06, 0.10 + j * (a + 0.10) + a, 0.36) for j in range(k)] + \
            [[(0.0, 0.55), (w, 0.55)], [(w - 0.30, 0.55), (w, 0.85)]]          # almohadas y la sábana doblada
    if kind == "mesita":
        return [_elipse(w / 2, d / 2, min(w, d) * 0.22, min(w, d) * 0.22, 12)]
    if kind == "placard":
        k = max(1, int((w - 0.10) / 0.25))
        return [[(0.05, d / 2), (w - 0.05, d / 2)]] + [[(s - 0.06, d / 2 - 0.20), (s + 0.06, d / 2 + 0.20)]       # barral y perchas
                                                     for s in (0.05 + (j + 0.5) * (w - 0.10) / k for j in range(k))]
    if kind == "silla":
        return [[(0.0, 0.08), (w, 0.08)]]
    if kind in ("sofa", "butaca"):
        b, a = min(0.20, d * 0.25), min(0.18, w * 0.2)                         # respaldo y brazos
        return [_rect(0.0, 0.0, w, b), _rect(0.0, 0.0, a, d), _rect(w - a, 0.0, w, d)] + \
            ([[(w / 2, b), (w / 2, d)]] if kind == "sofa" else [])
    if kind == "rack_tv":
        return [_rect(0.25, 0.08, w - 0.25, 0.14)]                              # la pantalla
    return []


def _marco(ld, t, n=0.0):
    """Esquina en el punto t de la pared ld (corrida n hacia adentro), dirección de la pared y normal hacia adentro."""
    (ax, av), (dx, dv), (nx, nv), _ = ld
    return (ax + dx * t + nx * n, av + dv * t + nv * n), (dx, dv), (nx, nv)


def _pieza(kind, o, es, en, w, d, room):
    """El artefacto o mueble en el marco de la vivienda: contorno y dibujo. o: esquina de atrás; es, en: direcciones a lo
    largo y hacia el frente; w, d: largo y fondo."""
    m = lambda s, n: (round(o[0] + es[0] * s + en[0] * n, 4), round(o[1] + es[1] * s + en[1] * n, 4))
    if kind == "giro":                                                          # el círculo (w es el diámetro)
        return {"kind": kind, "name": NOMBRES[kind], "room": room, "lines": [],
                "poly": [m(s, n) for s, n in _elipse(w / 2, d / 2, w / 2, d / 2, 32)[:-1]]}
    return {"kind": kind, "name": NOMBRES[kind], "room": room,
            "poly": [m(0.0, 0.0), m(w, 0.0), m(w, d), m(0.0, d)],
            "lines": [[m(s, n) for s, n in ln] for ln in _dibujo(kind, w, d)]}


# ---------------------------------------------------------------- colocación
def _paredes(r, aberturas, puertas):
    """Paredes de r con sus tramos libres (sin bordes abiertos ni puertas) y las zonas que las puertas dejan libres."""
    lados, zonas = _lados(r), []
    ocup = [[] for _ in lados]
    for ab in aberturas:
        for i, ld in enumerate(lados):
            tr = _en_lado(ab[0], ab[1], ld)
            if tr:
                ocup[i].append(tr)
    for p, q, ancho, adentro in puertas:
        for i, ld in enumerate(lados):
            tr = _en_lado(p, q, ld)
            if tr:
                ocup[i].append(tr)
                prof = ancho if adentro else 0.60      # barrido de la hoja, o el paso para cruzar la puerta
                zonas.append(_caja(ld, tr[0], tr[1] - tr[0], 0.0, prof))
    f = getattr(r, "forma", None)
    if f:                                             # un muro oblicuo: la pared del rectángulo que queda fuera no sirve
        for ld, oc in zip(lados, ocup):
            (ax, av), (dx, dv), (nx, nv), L = ld
            n = max(1, int(round(L / 0.05)))
            for k in range(n + 1):
                t = L * k / n
                pts = [(ax + dx * t + nx * m, av + dv * t + nv * m) for m in (0.0, 0.70)]
                if any(_cerca(q, r) and not _en_poligono(q, f) for q in pts):
                    oc.append((t - L / n, t + L / n))
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
        if largo + TOL < nec or not _dentro(frente, r) or not _dentro(caja, r) or any(_choca(caja, z) for z in zonas):
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
    k = rm["kind"]
    if k == "kitchen" or (k == "hall" and "Cocina" in rm["name"]):
        return "cocina"
    return {"bath": "bath", "laundry": "laundry", "bedroom": "dormitorio", "living": "estar", "dining": "comedor"}.get(k)


def resolver(rm, puertas, aberturas, S, fachada=(), nb=1, mesa=True, ids=None, acc=False):
    """Equipamiento de una estancia (con memoria: estancias iguales se resuelven una vez). puertas: [{p, q, a, b, ancho}];
    aberturas: {id: [(p, q[, id de la otra estancia])]}; fachada: tramos de pared con ventana [(p, q)]; nb: dormitorios
    (los asientos de la mesa); mesa: si el estar lleva la mesa del comedor; ids: estancias que se amueblan juntas (el
    estar y el comedor); acc: vivienda accesible (el baño principal, para silla de ruedas). Devuelve (piezas en el marco
    de la estancia trasladada al origen, lo que no entra, avisos)."""
    ids = tuple(ids or (rm["id"],))
    x0, v0, x1, v1 = rm["rect"]
    rel = lambda pt: (round(pt[0] - x0, 4), round(pt[1] - v0, 4))
    pts = tuple(sorted((rel(d["p"]), rel(d["q"]), round(d["ancho"], 3), d["b"] in ids)
                       for d in puertas if d["a"] in ids or d["b"] in ids))
    abre = tuple(sorted((rel(ab[0]), rel(ab[1]), ab[2] if len(ab) > 2 else "")
                        for i in ids for ab in aberturas.get(i, []) if len(ab) < 3 or ab[2] not in ids))
    forma = None
    if rm.get("poly") and abs(_area(rm["poly"])) < (x1 - x0) * (v1 - v0) - 0.01:     # un muro oblicuo la recorta
        forma = tuple(rel(p) for p in rm["poly"])
    tipo = _tipo(rm)
    mueble = tipo in MUEBLES
    clave = (tipo, rm["id"] in ("bath1", "bed1"), round(x1 - x0, 4), round(v1 - v0, 4), pts, abre, forma,
             tuple(sorted((rel(p), rel(q)) for p, q in fachada)) if mueble else (),
             nb if tipo in ("estar", "comedor") else None, mesa if tipo == "estar" else None,
             bool(acc) and tipo == "bath" and rm["id"] == "bath1",
             tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in S.items())))
    if clave not in _memo:
        if len(_memo) > 4000:
            _memo.clear()
        r = _estancia(x1 - x0, v1 - v0, forma)
        _memo[clave] = _equipar_estancia(tipo, clave[1], r, pts, abre, S, clave[7], nb, mesa, clave[10])
    return _memo[clave]


def _area(pl):
    return sum(pl[i - 1][0] * pl[i][1] - pl[i][0] * pl[i - 1][1] for i in range(len(pl))) / 2


def _contiguos(a, b):
    """¿Los rectángulos a y b comparten un lado entero (el comedor y el estar de una misma franja)?"""
    return abs(a[0] - b[0]) < 0.05 and abs(a[2] - b[2]) < 0.05 and (abs(a[3] - b[1]) < 0.05 or abs(b[3] - a[1]) < 0.05)


def equipar(rooms, puertas, aberturas, S, nb, fachadas=None, chicas=(), acc=False):
    """Artefactos y muebles de la vivienda. rooms: [{id, kind, name, rect[, poly]}]; puertas: [{p, q, a, b, ancho}] (la
    hoja abre hacia b); aberturas: {id: [(p, q[, id de la otra estancia])]} bordes abiertos a otra estancia; fachadas:
    {id: [(p, q)]} tramos de pared con ventana; chicas: estancias ya avisadas por no llegar a su medida mínima (se equipan
    igual, pero no se avisa además lo que no entra); acc: vivienda accesible. El comedor y el estar contiguos se amueblan
    juntos. Devuelve (piezas, comprobaciones)."""
    fachadas = fachadas or {}
    piezas, checks = [], []
    por_id = {rm["id"]: rm for rm in rooms}
    est, com = por_id.get("living"), por_id.get("dining")
    junto = bool(est and com and _contiguos(com["rect"], est["rect"]))
    for rm in rooms:
        tipo = _tipo(rm)
        if not tipo or (junto and rm is com):
            continue
        sala, ids, nombre = rm, (rm["id"],), {}
        if junto and rm is est:
            a, b = est["rect"], com["rect"]
            sala = dict(est, rect=(min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])), poly=None)
            if est.get("poly") and com.get("poly"):
                partes = G.union_parts([est["poly"], com["poly"]])
                sala["poly"] = max((e for e, _ in partes), key=lambda e: abs(_area(e))) if partes else None
            ids, nombre = ("living", "dining"), {"mesa": com["name"]}
        x0, v0 = sala["rect"][0], sala["rect"][1]
        hechas, faltan, info = resolver(sala, puertas, aberturas, S, [s for i in ids for s in fachadas.get(i, [])], nb,
                                        junto or com is None, ids, acc)
        for k, o, es, en, w, d in hechas:
            pz = _pieza(k, (o[0] + x0, o[1] + v0), es, en, w, d, rm["id"])
            if junto and rm is est:                       # cada mueble, en la estancia donde cae su centro
                c = (sum(p[0] for p in pz["poly"]) / 4, sum(p[1] for p in pz["poly"]) / 4)
                r = com["rect"]
                pz["room"] = "dining" if r[0] - TOL <= c[0] <= r[2] + TOL and r[1] - TOL <= c[1] <= r[3] + TOL else "living"
            piezas.append(pz)
        for lista, ok in ((faltan, False), (info, True)):
            for x in lista:
                que, txt = x if isinstance(x, tuple) else (None, x)
                if (com["id"] if que == "mesa" and junto and rm is est else rm["id"]) in chicas:
                    continue
                msg = "%s: %s%s" % (nombre.get(que, sala["name"]), "" if ok else "no entra ", txt)
                checks.append({"ok": True, "info": True, "msg": msg} if ok else {"ok": False, "msg": msg})
    return piezas, checks


def _equipar_estancia(tipo, principal, r, puertas, aberturas, S, fachada=(), nb=1, mesa=True, acc=False):
    """Una estancia en su propio origen (para reusar el resultado en estancias iguales). Devuelve (piezas
    [(kind, esquina, dirección, frente, largo, fondo)], lo que no entra, avisos)."""
    libres, zonas = _paredes(r, aberturas, [(p, q, ancho, adentro) for p, q, ancho, adentro in puertas])
    if tipo in MUEBLES:
        return _amueblar(tipo, principal, r, libres, zonas, puertas, aberturas, S, fachada, nb, mesa)
    if acc:
        hechas = _bano_accesible(r, libres, zonas, [(p, q) for p, q, _, _ in puertas], S)
        if hechas:
            return hechas, [], []
        acc = "el baño accesible (círculo de giro de %.2f m, inodoro con %.2f m de transferencia al costado y ducha a " \
              "nivel)" % (S["giro"], S["transferencia"])
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
        if isinstance(acc, str):                      # vivienda accesible: queda el baño común y el aviso
            txt = [acc] + txt
    elif tipo == "cocina":
        hechas, txt = _cocina(r, libres, zonas, S)
        return [(k,) + _marco(ld, t) + (w, d) for k, ld, t, w, d in hechas], txt, info
    else:
        puestos, fal = _lavadero(r, libres, zonas, puerta, S)
        txt = ["%s (%.2f × %.2f m)" % ("el lavarropas" if k == "lavarropas" else "la pileta", S[k][0], S[k][1]) for k in fal]
    return [(o[0],) + _marco(o[1], o[2]) + (o[3], o[4]) for o in puestos], txt, info


# ---------------------------------------------------------------- muebles (F5, segunda parte)
DECOR = ("silla",)          # se dibujan, pero no ocupan lugar: van en el paso de la mesa, que queda libre
_GIRO = {   # rectángulo (s0, n0, s1, n1) del módulo -> esquina de atrás, direcciones a lo largo y al frente, largo, fondo
    "n+": lambda s0, n0, s1, n1: ((s0, n0), (1, 0), (0, 1), s1 - s0, n1 - n0),       # el respaldo del lado de n0
    "n-": lambda s0, n0, s1, n1: ((s1, n1), (-1, 0), (0, -1), s1 - s0, n1 - n0),     # del lado de n1
    "s+": lambda s0, n0, s1, n1: ((s0, n1), (0, -1), (1, 0), n1 - n0, s1 - s0),      # del lado de s0
    "s-": lambda s0, n0, s1, n1: ((s1, n0), (0, 1), (-1, 0), n1 - n0, s1 - s0)}      # del lado de s1


def _plantilla(cuerpos, pasos, apoyo=None, uso=None):
    """Módulo compuesto en coordenadas propias (s a lo largo de la pared, n hacia adentro): cuerpos
    [(kind, s0, n0, s1, n1, giro)], pasos libres [(s0, n0, s1, n1)], el tramo apoyo (s0, s1) que va contra una pared
    maciza (None: suelto, como la mesa) y los lugares de uso a los que se tiene que llegar (por defecto, los pasos)."""
    rects = [c[1:5] for c in cuerpos] + list(pasos)
    return {"cuerpos": cuerpos, "pasos": pasos, "apoyo": apoyo, "uso": pasos if uso is None else uso,
            "s0": min(x[0] for x in rects), "n0": min(x[1] for x in rects),
            "s1": max(x[2] for x in rects), "n1": max(x[3] for x in rects)}


def _ubicar(pl, ld, t, n=0.0):
    """El módulo pl en la estancia: en el punto t de la pared ld, corrido n hacia adentro. Solo las cajas de sus cuerpos
    sólidos, sus pasos y sus lugares de uso; el dibujo se arma al final (_dibujar), con lo elegido."""
    caja = lambda s0, n0, s1, n1: _caja(ld, t + s0, s1 - s0, n + n0, n + n1)
    pasos = [caja(*x) for x in pl["pasos"]]
    return {"solidos": [caja(*c[1:5]) for c in pl["cuerpos"] if c[0] not in DECOR], "pasos": pasos,
            "uso": pasos if pl["uso"] is pl["pasos"] else [caja(*x) for x in pl["uso"]], "pl": pl, "ld": ld, "t": t, "n": n}


def _dibujar(col):
    """Los muebles de una ubicación: [(kind, esquina de atrás, dirección a lo largo, hacia el frente, largo, fondo)]."""
    (ax, av), (dx, dv), (nx, nv), _ = col["ld"]
    t, n = col["t"], col["n"]
    P = lambda s, m: (ax + dx * (t + s) + nx * (n + m), av + dv * (t + s) + nv * (n + m))
    V = lambda a, b: (dx * a + nx * b, dv * a + nv * b)
    out = []
    for k, s0, n0, s1, n1, giro in col["pl"]["cuerpos"]:
        o, es, en, w, d = _GIRO[giro](s0, n0, s1, n1)
        out.append((k, P(*o), V(*es), V(*en), w, d))
    return out


def _solidos(col):
    return col["solidos"]


def _cabe(col, r, zonas):
    """¿Entra el módulo ubicado en la estancia vacía, sin pisar las zonas que dejan libres puertas y aberturas?"""
    return all(_dentro(c, r) and not any(_choca(c, z) for z in zonas) for c in _solidos(col)) and \
        all(_dentro(x, r) for x in col["pasos"])


def _junto(col, cuerpos, pasos):
    """¿Entra junto a lo ya puesto? Sus cuerpos no pisan cuerpos ni pasos; sus pasos no pisan cuerpos."""
    sol = _solidos(col)
    return not any(_choca(c, o) for c in sol for o in cuerpos) and not any(_choca(c, o) for c in sol for o in pasos) \
        and not any(_choca(x, o) for x in col["pasos"] for o in cuerpos)


def _menos(tramos, quitar):
    """Los tramos [(a, b)] sin los de quitar."""
    out = []
    for a, b in tramos:
        for c, d in _libres(b - a, [(max(c - a, 0.0), min(d - a, b - a)) for c, d in quitar if d > a + TOL and c < b - TOL]):
            out.append((a + c, a + d))
    return out


def _en_paredes(pl, libres, paso=0.10):
    """Posiciones (i, pared, t) del módulo pl con su apoyo dentro de un tramo libre de pared (y centrado, si se puede)."""
    a0, a1 = pl["apoyo"]
    for i, (ld, tramos) in enumerate(libres):
        L = ld[3]
        for a, b in tramos:
            lo, hi = max(a - a0, -pl["s0"]), min(b - a1, L - pl["s1"])
            if hi < lo - TOL:
                continue
            ts = {round(lo, 4), round(hi, 4)} | {round(lo + k * paso, 4) for k in range(int((hi - lo) / paso) + 1)}
            c = (L - pl["s0"] - pl["s1"]) / 2
            if lo - TOL <= c <= hi + TOL:
                ts.add(round(c, 4))
            for t in sorted(ts):
                yield i, ld, t


def _sueltos(pl, r, paso=0.10):
    """Posiciones (pared, t, n) de un módulo suelto (la mesa), en los dos sentidos."""
    lados = _lados(r)
    for ld, E in ((lados[0], r[3] - r[1]), (lados[1], r[2] - r[0])):
        tl, th, nl, nh = -pl["s0"], ld[3] - pl["s1"], -pl["n0"], E - pl["n1"]
        if th < tl - TOL or nh < nl - TOL:
            continue
        ts = sorted({round(tl, 4), round(th, 4)} | {round(tl + k * paso, 4) for k in range(int((th - tl) / paso) + 1)})
        ns = sorted({round(nl, 4), round(nh, 4)} | {round(nl + k * paso, 4) for k in range(int((nh - nl) / paso) + 1)})
        for t in ts:
            for n in ns:
                yield ld, t, n


def _rango(a, b, o, gg, n):
    """Índices de las celdas (de lado gg, desde o) con el centro entre a y b."""
    return max(0, int(math.floor((a - o) / gg - 0.5 + 1e-9)) + 1), min(n - 1, int(math.ceil((b - o) / gg - 0.5 - 1e-9)) - 1)


def _grilla(r, h, g):
    """Grilla de la estancia vacía: (nx, ny, gx, gy, celdas transitables), las que quedan a h o más de las paredes y, si
    un muro oblicuo la recorta, dentro de su contorno y a h o más de él. Se guarda en r para las próximas consultas."""
    memo = getattr(r, "__dict__", {})
    if ("_grilla", h, g) in memo:
        return memo[("_grilla", h, g)]
    x0, v0, x1, v1 = r
    nx, ny = max(1, int(math.ceil((x1 - x0) / g - 1e-9))), max(1, int(math.ceil((v1 - v0) / g - 1e-9)))
    gx, gy = (x1 - x0) / nx, (v1 - v0) / ny
    base = bytearray(nx * ny)
    i0, i1 = _rango(x0 + h - 1e-6, x1 - h + 1e-6, x0, gx, nx)
    j0, j1 = _rango(v0 + h - 1e-6, v1 - h + 1e-6, v0, gy, ny)
    for j in range(j0, j1 + 1):
        if i1 >= i0:
            base[j * nx + i0:j * nx + i1 + 1] = b"\x01" * (i1 - i0 + 1)
    f = getattr(r, "forma", None)
    if f:                                             # cerca del muro oblicuo: dentro de la forma y a h o más de él
        lados = [(a, b) for a, b in zip(f, f[1:] + f[:1]) if abs(a[0] - b[0]) > 1e-6 and abs(a[1] - b[1]) > 1e-6]
        for b in r.fuera:
            fi0, fi1 = _rango(b[0] - h, b[2] + h, x0, gx, nx)
            fj0, fj1 = _rango(b[1] - h, b[3] + h, v0, gy, ny)
            for j in range(max(j0, fj0), min(j1, fj1) + 1):
                y = v0 + (j + 0.5) * gy
                for i in range(max(i0, fi0), min(i1, fi1) + 1):
                    x = x0 + (i + 0.5) * gx
                    if base[j * nx + i] and (not _en_poligono((x, y), f, 0.0) or
                                             any(_dist_seg((x, y), a, c) < h - 1e-6 for a, c in lados)):
                        base[j * nx + i] = 0
    res = (nx, ny, gx, gy, bytes(base))
    if hasattr(r, "__dict__"):
        r.__dict__[("_grilla", h, g)] = res
    return res


def _dist_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    k = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2)) if L2 > 0 else 0.0
    return math.hypot(p[0] - a[0] - k * dx, p[1] - a[1] - k * dy)


def _alcanza(r, cuerpos, accesos, usos, h=0.25, g=0.10):
    """¿Se llega desde las puertas y aberturas (segmentos sobre el borde de r) a todos los lugares de uso sin pisar los
    cuerpos? Grilla de g: una celda es transitable si su centro queda a h o más de las paredes y de los cuerpos (un paso
    de unos 2 h); todos los accesos tienen que quedar comunicados entre sí."""
    if not accesos:
        return True
    x0, v0, x1, v1 = r
    nx, ny, gx, gy, base = _grilla(r, h, g)
    rango = _rango
    libre = bytearray(base)
    for a0, b0, a1, b1 in cuerpos:
        i0, i1 = rango(a0 - h + 1e-6, a1 + h - 1e-6, x0, gx, nx)
        j0, j1 = rango(b0 - h + 1e-6, b1 + h - 1e-6, v0, gy, ny)
        if i1 >= i0:
            for j in range(j0, j1 + 1):
                libre[j * nx + i0:j * nx + i1 + 1] = bytes(i1 - i0 + 1)

    def celdas(p, q):
        """Celdas transitables junto al acceso p-q, del lado de adentro."""
        vert = abs(p[0] - q[0]) < 1e-6
        a, b = sorted((p[1], q[1]) if vert else (p[0], q[0]))
        if b - a > 0.4:
            a, b = a + 0.1, b - 0.1
        e, (lo, hi) = (p[0], (x0, x1)) if vert else (p[1], (v0, v1))
        c0, c1 = (e, e + h + 1.5 * g) if e - lo < hi - e else (e - h - 1.5 * g, e)
        (i0, i1), (j0, j1) = (rango(c0, c1, x0, gx, nx), rango(a, b, v0, gy, ny)) if vert else \
            (rango(a, b, x0, gx, nx), rango(c0, c1, v0, gy, ny))
        return [j * nx + i for j in range(j0, j1 + 1) for i in range(i0, i1 + 1) if libre[j * nx + i]]
    semillas = [celdas(p, q) for p, q in accesos]
    visto = bytearray(nx * ny)
    pila = list(semillas[0])
    for k in pila:
        visto[k] = 1
    while pila:
        k = pila.pop()
        i = k % nx
        for kk in (k - 1 if i > 0 else -1, k + 1 if i < nx - 1 else -1, k - nx, k + nx):
            if 0 <= kk < nx * ny and libre[kk] and not visto[kk]:
                visto[kk] = 1
                pila.append(kk)
    if not all(any(visto[k] for k in s) for s in semillas[1:]):
        return False
    for a0, b0, a1, b1 in usos:
        i0, i1 = rango(a0 - 1e-6, a1 + 1e-6, x0, gx, nx)
        j0, j1 = rango(b0 - 1e-6, b1 + 1e-6, v0, gy, ny)
        if not any(visto[j * nx + i] for j in range(j0, j1 + 1) for i in range(i0, i1 + 1)):
            return False
    return True


def _combinar(r, accesos, listas, anchos=(12, 5, 3), tope=30, salto=0.35, final=None):
    """La primera combinación, una ubicación de cada lista (ordenadas de la preferida a la peor), que entra sin pisarse y
    desde la que se llega a todo (y que cumple final(elegidas), si se da). anchos: cuántas ubicaciones válidas se prueban
    en cada nivel; tope: cuántas veces se comprueba el recorrido; tras una ubicación que no sirve se saltean las casi
    iguales (a menos de `salto` en la misma pared). Devuelve las ubicaciones elegidas o None."""
    pruebas = [0]

    def rec(k, cuerpos, pasos, usos, elegidos):
        if k == len(listas):
            pruebas[0] += 1
            return elegidos if _alcanza(r, cuerpos, accesos, usos) and (final is None or final(elegidos)) else None
        vistas, malas = 0, []
        for col in listas[k]:
            if pruebas[0] >= tope:
                return None
            if any(m["pl"] is col["pl"] and m["ld"] is col["ld"] and abs(m["t"] - col["t"]) < salto and
                   abs(m["n"] - col["n"]) < salto for m in malas) or not _junto(col, cuerpos, pasos):
                continue
            res = rec(k + 1, cuerpos + _solidos(col), pasos + col["pasos"], usos + col["uso"], elegidos + [col])
            if res is not None:
                return res
            malas.append(col)
            vistas += 1
            if vistas >= anchos[min(k, len(anchos) - 1)]:
                return None
        return None
    return rec(0, [], [], [], [])


def _primero(r, accesos, intentos):
    """El primer intento que entra. intentos: [(listas, faltan, info)], cada lista una función que da las ubicaciones
    ordenadas; el último intento (sin listas) siempre vale. Devuelve (ubicaciones, faltan, info)."""
    for listas, faltan, info in intentos:
        if not listas:
            return [], faltan, info
        ls = [f() for f in listas]
        if all(ls):
            res = _combinar(r, accesos, ls)
            if res is not None:
                return res, faltan, info
    return [], [], []


def _lista(fn):
    """Una lista de ubicaciones que se calcula la primera vez que se pide."""
    hecho = []

    def f():
        if not hecho:
            hecho.append(fn())
        return hecho[0]
    return f


def _ordenar(cands):
    return [c for _, c in sorted(cands, key=lambda x: x[0])]


class _Perezosa:
    """Ubicaciones en orden de preferencia que se arman (y se descartan si no entran en la estancia vacía) recién cuando
    se recorren: la búsqueda casi siempre usa solo las primeras. crudas: [(preferencia, plantilla, pared, t, n)]."""

    def __init__(self, crudas, r, zonas):
        self.crudas, self.r, self.zonas = sorted(crudas, key=lambda x: x[0]), r, zonas
        self.hechas, self.i = [], 0

    def __iter__(self):
        k = 0
        while True:
            while k >= len(self.hechas) and self.i < len(self.crudas):
                _, pl, ld, t, n = self.crudas[self.i]
                self.i += 1
                col = _ubicar(pl, ld, t, n)
                if _cabe(col, self.r, self.zonas):
                    self.hechas.append(col)
            if k >= len(self.hechas):
                return
            yield self.hechas[k]
            k += 1

    def __bool__(self):
        return any(True for _ in self)


def _camas(S, principal):
    """Grupos de variantes de cama, del preferido al menos: (variantes [(plantilla, lados cerrados)], camas, mesas de luz).
    La doble lleva mesa de luz y paso de cada lado y paso al pie; dos individuales, una mesa de luz y el paso entre ellas;
    una individual, el paso de un lado (el otro, contra la pared)."""
    p, (mw, md) = S["paso_cama"], S["mesita"]
    if principal:
        bw, bl = S["cama_doble"]
        W = p + bw + p
        out = []
        for mesas in (True, False):
            cs = [("cama_doble", p, 0.0, p + bw, bl, "n+")]
            if mesas:
                cs += [("mesita", p - mw, 0.0, p, md, "n+"), ("mesita", p + bw, 0.0, p + bw + mw, md, "n+")]
            n0 = md if mesas else 0.0
            pl = _plantilla(cs, [(0.0, n0, p, bl), (p + bw, n0, W, bl), (0.0, bl, W, bl + p)],
                            apoyo=(p - mw, p + bw + mw) if mesas else (p, p + bw), uso=[(0.0, n0, p, bl), (p + bw, n0, W, bl)])
            out.append(([(pl, ())], 1, mesas))
        return out
    bw, bl = S["cama_individual"]
    dos = []
    for extra in (0.0, 0.2, 0.4, 0.6):
        gap = max(p, mw) + extra
        W, m0 = bw + gap + bw, bw + (gap - mw) / 2
        cs = [("cama_individual", 0.0, 0.0, bw, bl, "n+"), ("mesita", m0, 0.0, m0 + mw, md, "n+"),
              ("cama_individual", bw + gap, 0.0, W, bl, "n+")]
        pasos = [(bw, md, bw + gap, bl), (bw, bl, bw + gap, bl + p)]      # el paso entre las camas sigue al pie
        dos.append((_plantilla(cs, pasos, apoyo=(0.0, W), uso=pasos[:1]), (0.0, W)))
    una = []
    for lado in (1, -1):
        if lado > 0:
            cs = [("cama_individual", 0.0, 0.0, bw, bl, "n+"), ("mesita", bw, 0.0, bw + mw, md, "n+")]
            pasos, cerrado = [(bw, md, bw + p, bl)], 0.0
        else:
            cs = [("mesita", p - mw, 0.0, p, md, "n+"), ("cama_individual", p, 0.0, p + bw, bl, "n+")]
            pasos, cerrado = [(0.0, md, p, bl)], p + bw
        una.append((_plantilla(cs, pasos, apoyo=(min(c[1] for c in cs), max(c[3] for c in cs))), (cerrado,)))
    return [(dos, 2, True), (una, 1, True)]


def _amueblar(tipo, principal, r, libres, zonas, puertas, aberturas, S, fachada, nb, mesa):
    """Muebles de un dormitorio, del estar (con la mesa del comedor si va ahí) o del comedor."""
    lados = _lados(r)
    fach = [[tr for tr in (_en_lado(p, q, ld) for p, q in fachada) if tr] for ld in lados]
    sin_ventana = [(ld, _menos(tr, fach[i])) for i, (ld, tr) in enumerate(libres)]
    con_puerta = [any(_en_lado(p, q, ld) for p, q, _, _ in puertas) for ld in lados]
    zonas, entrada, cocina = list(zonas), None, None
    for p, q, otro in aberturas:
        m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        if otro in ("hall", "hallway", "kitchen"):          # delante de las aberturas de paso no va ningún mueble
            for ld in lados:
                tr = _en_lado(p, q, ld)
                if tr:
                    zonas.append(_caja(ld, tr[0], tr[1] - tr[0], 0.0, S["paso_estar"]))
        if otro == "kitchen" and cocina is None:
            cocina = m
        if otro in ("hall", "kitchen") and entrada is None:
            entrada = m
    accesos = [(p, q) for p, q, _, _ in puertas] + [(p, q) for p, q, _ in aberturas]
    if entrada is None:
        entrada = ((accesos[0][0][0] + accesos[0][1][0]) / 2, (accesos[0][0][1] + accesos[0][1][1]) / 2) if accesos \
            else _centro(r)
    if tipo == "dormitorio":
        cols, faltan, info = _dormitorio(r, libres, sin_ventana, zonas, accesos, entrada, fach, con_puerta, S, principal)
    else:
        cols, faltan, info = _estar(tipo, r, libres, sin_ventana, zonas, accesos, entrada, cocina or entrada, fach, S, nb,
                                    mesa)
    return [pz for col in cols for pz in _dibujar(col)], faltan, info


def _dormitorio(r, libres, sin_ventana, zonas, accesos, puerta, fach, con_puerta, S, principal):
    """Cama (doble en el principal; dos individuales o una en los demás) con mesas de luz y paso, y placard. La cabecera,
    mejor contra una pared sin ventana ni puerta; el placard, contra una pared sin ventana, cerca de la puerta."""
    p, f = S["paso_cama"], S["placard_fondo"]
    largo = S["placard_largo"][0 if principal else 1]
    largos = [largo] + [round(largo - 0.3 * k, 2) for k in range(1, 20) if largo - 0.3 * k >= 0.9 - TOL]

    def camas(variantes):
        out = []
        for pl, cerrados in variantes:
            a0, a1 = pl["apoyo"]
            for i, ld, t in _en_paredes(pl, libres):
                s0, s1 = t + a0, t + a1
                v = 3.0 if any(min(b, s1) - max(a, s0) > 0.05 for a, b in fach[i]) else 0.0     # la cabecera bajo la ventana
                v += 1.0 if con_puerta[i] else 0.0
                for c in cerrados:                         # las individuales, contra la pared del costado
                    v += 0.5 * min(abs(t + c), abs(ld[3] - t - c))
                if not cerrados:                           # la doble, centrada en su pared
                    v += 0.3 * abs((s0 + s1) / 2 - ld[3] / 2) / max(ld[3], 1.0)
                out.append((v, pl, ld, t, 0.0))
        return _Perezosa(out, r, zonas)

    def placards(L):
        pl = _plantilla([("placard", 0.0, 0.0, L, f, "n+")], [(0.0, f, L, f + p)], apoyo=(0.0, L))
        return _Perezosa([(_dist(_centro(_caja(ld, t, L, 0.0, f)), puerta), pl, ld, t, 0.0)
                          for i, ld, t in _en_paredes(pl, sin_ventana)], r, zonas)
    grupos = [(_lista(lambda v=v: camas(v)), n) for v, n, _ in _camas(S, principal)]
    pls = {L: _lista(lambda L=L: placards(L)) for L in largos}
    if principal:
        bw, bl = S["cama_doble"]
        sin_cama = ("cama", "la cama doble (%.2f × %.2f m con %.2f m de paso a los lados y al pie)" % (bw, bl, p))
    else:
        bw, bl = S["cama_individual"]
        sin_cama = ("cama", "la cama individual (%.2f × %.2f m con %.2f m de paso al costado)" % (bw, bl, p))
    una = [] if principal else ["entra una sola cama individual"]
    corto = lambda L: [] if L == largo else ["placard de %.2f m (no entra el de %.2f m)" % (L, largo)]
    sin_placard = ("placard", "el placard (%.2f × %.2f m con %.2f m de paso delante)" % (largos[-1], f, p))
    intentos = []
    for g, (cama, n) in enumerate(grupos):
        extra = una if n == 1 and g > 0 else []
        intentos += [([cama, pls[L]], [], extra + corto(L)) for L in largos]
    intentos += [([cama], [sin_placard], una if n == 1 and g > 0 else []) for g, (cama, n) in enumerate(grupos)]
    intentos += [([pls[L]], [sin_cama], corto(L)) for L in largos]
    intentos.append(([], [sin_cama, sin_placard], []))
    return _primero(r, accesos, intentos)


def _mesa(S, n):
    """Mesa para n con las sillas a los dos lados largos y su lugar libre (paso_silla) delante de cada lado."""
    a, f, ps = S["asiento"], S["mesa_fondo"], S["paso_silla"]
    k1, k2 = (n + 1) // 2, n // 2
    L = max(0.80, k1 * a)
    cw = min(0.42, 0.75 * a, ps - 0.05)
    cs = [("mesa", 0.0, ps, L, ps + f, "n+")]
    for k, n0, giro in ((k1, ps - cw - 0.03, "n+"), (k2, ps + f + 0.03, "n-")):
        for j in range(k):
            c = (j + 0.5) * L / k
            cs.append(("silla", c - cw / 2, n0, c + cw / 2, n0 + cw, giro))
    return _plantilla(cs, [(0.0, 0.0, L, ps), (0.0, ps + f, L, 2 * ps + f)]), L


def _estar(tipo, r, libres, sin_ventana, zonas, accesos, entrada, cocina, fach, S, nb, mesa):
    """Estar: el sofá frente al rack de TV (y butacas, si entran); la mesa del comedor cerca de la cocina, con asientos
    según los dormitorios; en un monoambiente, también la cama doble."""
    (sw, sd), (rw, rd), dtv = S["sofa"], S["rack_tv"], S["distancia_tv"]
    A = S["asientos"]
    req = max(1, int(round(A[0] if nb == 0 else A[1] + A[2] * (nb - 1))))
    menos = list(range(req - 2, 1, -2))

    def tvs():
        """El rack contra una pared maciza sin ventana y el sofá enfrente: contra la pared de enfrente (mejor si no queda
        muy lejos) o suelto, a la distancia de la TV y con paso detrás. Primero, lejos de la entrada."""
        W = max(sw, rw)
        out = []
        for i, (ld, tramos) in enumerate(sin_ventana):
            E = (r[2] - r[0]) if i % 2 else (r[3] - r[1])
            contra = E - rd - sd
            for D, extra, suelto in ((contra, 0.25 * max(0.0, contra - dtv - 1.5), False), (dtv, 0.5, True)):
                if (not suelto and contra < dtv - TOL) or (suelto and contra - dtv < 0.9 - TOL):    # suelto: paso detrás
                    continue
                pl = _plantilla([("rack_tv", (W - rw) / 2, 0.0, (W + rw) / 2, rd, "n+"),
                                 ("sofa", (W - sw) / 2, rd + D, (W + sw) / 2, rd + D + sd, "n-")],
                                [((W - sw) / 2, rd, (W + sw) / 2, rd + D)], apoyo=((W - rw) / 2, (W + rw) / 2))
                z = pl["pasos"][0]
                for _, ld2, t in _en_paredes(pl, [(ld, tramos)]):
                    zona = _centro(_caja(ld2, t + z[0], z[2] - z[0], z[1], z[3]))
                    out.append((extra - 0.5 * _dist(zona, entrada), pl, ld2, t, 0.0))
        return _Perezosa(out, r, zonas)

    def mesas(n):
        pl, L = _mesa(S, n)
        ps, f = S["paso_silla"], S["mesa_fondo"]
        return _Perezosa([(_dist(_centro(_caja(ld, t, L, m + ps, m + ps + f)), cocina), pl, ld, t, m)
                          for ld, t, m in _sueltos(pl, r, 0.15)], r, zonas)
    tv = _lista(tvs)
    ms = {n: _lista(lambda n=n: mesas(n)) for n in [req] + menos}
    sin_tv = ("tv", "el sofá frente al rack de TV (sofá de %.2f m a %.2f m del rack)" % (sw, dtv))
    L_req = _mesa(S, req)[1]
    sin_mesa = ("mesa", "la mesa para %d (%.2f × %.2f m con %.2f m para las sillas)" % (req, L_req, S["mesa_fondo"],
                                                                                    S["paso_silla"]))

    def chica(n):
        """(faltan, info) con una mesa para n en lugar de req: para 1 dormitorio, una mesa más chica es aceptable."""
        if nb == 1:
            return [], [("mesa", "mesa para %d (para %d no hay lugar)" % (n, req))]
        return [("mesa", "la mesa para %d (entra una para %d)" % (req, n))], []
    if tipo == "comedor" or (tipo == "estar" and nb > 0 and mesa):
        mesa_int = [([ms[req]], [], [])] + [([ms[n]], *chica(n)) for n in menos]
        if tipo == "comedor":
            intentos = mesa_int + [([], [sin_mesa], [])]
        else:
            intentos = [([tv, ms[req]], [], [])] + [([tv, ms[n]], *chica(n)) for n in menos] + \
                [(ls, [sin_tv] + fa, inf) for ls, fa, inf in mesa_int] + [([tv], [sin_mesa], []), ([], [sin_tv, sin_mesa], [])]
    elif nb > 0:
        intentos = [([tv], [], []), ([], [sin_tv], [])]
    else:                                                    # monoambiente: cama, mesa para dos y, si entra, la TV
        cama = _lista(lambda: _camas_sueltas(r, libres, zonas, fach, S, entrada))
        sin_cama = ("cama", "la cama doble (%.2f × %.2f m con %.2f m de paso a los lados y al pie)" %
                    (S["cama_doble"][0], S["cama_doble"][1], S["paso_cama"]))
        no_tv = [("tv", "sin lugar para el sofá frente al rack de TV")]
        intentos = [([cama, ms[req], tv], [], []), ([cama, ms[req]], [], no_tv), ([cama, tv], [sin_mesa], []),
                    ([cama], [sin_mesa], no_tv), ([ms[req], tv], [sin_cama], []), ([ms[req]], [sin_cama], no_tv),
                    ([tv], [sin_cama, sin_mesa], []), ([], [sin_cama, sin_mesa], no_tv)]
    cols, faltan, info = _primero(r, accesos, intentos)
    tele = [c for c in cols if c["pl"]["cuerpos"][0][0] == "rack_tv"]
    if tele:
        cols = cols + _butacas(r, libres, zonas, accesos, S, tele[0], cols)
    return cols, faltan, info


def _camas_sueltas(r, libres, zonas, fach, S, entrada):
    """La cama doble de un monoambiente: contra una pared maciza, mejor sin ventana y lejos de la entrada (con mesas de
    luz, si entran)."""
    out = []
    for orden, (variantes, _, _) in enumerate(_camas(S, True)):
        for pl, _ in variantes:
            a0, a1 = pl["apoyo"]
            b0 = pl["cuerpos"][0]
            for i, ld, t in _en_paredes(pl, libres):
                s0, s1 = t + a0, t + a1
                v = 10.0 * orden + (3.0 if any(min(b, s1) - max(a, s0) > 0.05 for a, b in fach[i]) else 0.0)
                cama = _centro(_caja(ld, t + b0[1], b0[3] - b0[1], b0[2], b0[4]))
                out.append((v - 0.5 * _dist(cama, entrada), pl, ld, t, 0.0))
    return _Perezosa(out, r, zonas)


def _butacas(r, libres, zonas, accesos, S, tv, puestos):
    """Hasta dos butacas: a los costados del lugar de la TV, mirando hacia él, o de frente contra una de las otras paredes,
    cerca."""
    bw, bd = S["butaca"]
    pl_tv, ld, t, n = tv["pl"], tv["ld"], tv["t"], tv["n"]
    zs0, zn0, zs1, zn1 = pl_tv["pasos"][0]
    m = max(zn0 + bw / 2, zn1 - bw / 2 - 0.10)
    cand = [_ubicar(_plantilla([("butaca", s0, m - bw / 2, s0 + bd, m + bw / 2, giro)], [], uso=[]), ld, t, n)
            for s0, giro in ((zs1 + 0.05, "s-"), (zs0 - 0.05 - bd, "s+"))]
    zona = _centro(tv["pasos"][0])
    pl = _plantilla([("butaca", 0.0, 0.0, bw, bd, "n+")], [(0.0, bd, bw, bd + 0.45)], apoyo=(0.0, bw))
    pared = []
    for _, ld2, t2 in _en_paredes(pl, libres):
        if abs(ld2[1][0] * ld[1][0] + ld2[1][1] * ld[1][1]) > 0.5:      # no junto al rack ni al sofá: en las otras paredes
            continue
        col = _ubicar(pl, ld2, t2)
        c, en = _centro(col["solidos"][0]), ld2[2]
        if _dist(c, zona) <= 2.0 and en[0] * (zona[0] - c[0]) + en[1] * (zona[1] - c[1]) > 0:
            pared.append((_dist(c, zona), col))
    cand += _ordenar(pared)
    cuerpos = [c for col in puestos for c in _solidos(col)]
    pasos = [x for col in puestos for x in col["pasos"]]
    usos = [u for col in puestos for u in col["uso"]]
    out, pruebas = [], 0
    for col in cand:
        if len(out) == 2 or pruebas >= 8:
            break
        if not _cabe(col, r, zonas) or not _junto(col, cuerpos, pasos):
            continue
        pruebas += 1
        if _alcanza(r, cuerpos + _solidos(col), accesos, usos + col["uso"]):
            out.append(col)
            cuerpos, pasos, usos = cuerpos + _solidos(col), pasos + col["pasos"], usos + col["uso"]
    return out


# ---------------------------------------------------------------- vivienda accesible (F5, tercera parte)
def _bano_accesible(r, libres, zonas, accesos, S):
    """Baño para silla de ruedas: ducha a nivel, inodoro con su espacio de transferencia a un costado (y el otro, mejor
    contra la pared, para la barra de apoyo), lavatorio y un círculo de giro libre (puede pisar la ducha, que está a
    nivel del piso). Sin bidé. Devuelve las piezas o None si no entra."""
    p, tr, R = S["paso_bano"], S["transferencia"], S["giro"] / 2
    (dw, dd), (iw, idp), (lw, ld) = S["ducha_nivel"], S["inodoro"], S["lavatorio"]
    puerta = _centro((min(accesos[0][0][0], accesos[0][1][0]), min(accesos[0][0][1], accesos[0][1][1]),
                      max(accesos[0][0][0], accesos[0][1][0]), max(accesos[0][0][1], accesos[0][1][1]))) \
        if accesos else _centro(r)

    def lista(variantes, pref):
        out = []
        for pl, cerrado in variantes:
            for i, ld_, t in _en_paredes(pl, libres):
                b = pl["cuerpos"][0]
                c = _centro(_caja(ld_, t + b[1], b[3] - b[1], b[2], b[4]))
                v = pref(c)
                if cerrado is not None:                # el costado sin transferencia, contra la pared (barra de apoyo)
                    v += 0.5 * min(abs(t + cerrado), abs(ld_[3] - t - cerrado))
                out.append((v, pl, ld_, t, 0.0))
        return _Perezosa(out, r, zonas)
    ducha = _plantilla([("ducha_nivel", 0.0, 0.0, dw, dd, "n+")], [], apoyo=(0.0, dw))
    inodoros = [(_plantilla([("inodoro", 0.0, 0.0, iw, idp, "n+")], [(iw, 0.0, iw + tr, idp + p), (0.0, idp, iw, idp + p)],
                            apoyo=(0.0, iw)), 0.0),
                (_plantilla([("inodoro", tr, 0.0, tr + iw, idp, "n+")], [(0.0, 0.0, tr, idp + p), (tr, idp, tr + iw, idp + p)],
                            apoyo=(tr, tr + iw)), tr + iw)]
    lavatorio = _plantilla([("lavatorio", 0.0, 0.0, lw, ld, "n+")], [(0.0, ld, lw, ld + p)], apoyo=(0.0, lw))
    lejos = lambda c: -_dist(c, puerta)
    listas = [lista([(ducha, None)], lejos), lista(inodoros, lejos), lista([(lavatorio, None)], lambda c: _dist(c, puerta))]
    giro = []

    def entra_giro(elegidos):
        """¿Hay lugar para el círculo de giro? Lo ubica lo más cerca posible del centro del baño."""
        cuerpos = [c for col in elegidos if col["pl"] is not ducha for c in col["solidos"]]
        f = getattr(r, "forma", None)
        lados = [(a, b) for a, b in zip(f, f[1:] + f[:1])] if f else []
        mejor, cx, cy = None, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        k = 0.05
        for i in range(int((r[2] - r[0] - 2 * R) / k + 1e-9) + 1):
            x = r[0] + R + i * k
            for j in range(int((r[3] - r[1] - 2 * R) / k + 1e-9) + 1):
                y = r[1] + R + j * k
                if any(math.hypot(max(b[0] - x, 0.0, x - b[2]), max(b[1] - y, 0.0, y - b[3])) < R - 1e-6 for b in cuerpos):
                    continue
                if f and (not _en_poligono((x, y), f) or any(_dist_seg((x, y), a, b) < R - 1e-6 for a, b in lados)):
                    continue
                d = math.hypot(x - cx, y - cy)
                if mejor is None or d < mejor[0]:
                    mejor = (d, x, y)
        if mejor:
            giro[:] = [mejor[1:]]
        return mejor is not None
    cols = _combinar(r, accesos, listas, final=entra_giro)
    if not cols or not giro:
        return None
    x, y = giro[0]
    return [pz for col in cols for pz in _dibujar(col)] + [("giro", (x - R, y - R), (1, 0), (0, 1), 2 * R, 2 * R)]
