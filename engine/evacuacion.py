"""Evacuación (R3.6): la red de pasillos como un grafo para medir, desde la puerta de cada vivienda, el recorrido hasta
el núcleo más cercano y el fondo de saco: el tramo con una sola dirección de salida, desde la puerta hasta un núcleo o
hasta un punto desde el que se puede salir en dos direcciones (sin volver a pasar por la puerta). Un anillo alrededor de
un patio da dos direcciones aunque las dos lleguen al mismo núcleo. Parte del motor (ver engine/layout.py)."""
import heapq
from . import geometry as G

INF = float("inf")


def _red(pieces):
    """Nodos: (pieza, x) en el eje de cada pieza (extremos, uniones y núcleos); aristas: tramos de pasillo y uniones."""
    pos = {i: set() for i in range(len(pieces))}
    for i, pc in enumerate(pieces):
        a, b = pc.get("eje", (pc["xa"], pc["xb"]))
        if pc.get("tramo"):                                # R3.7: el pasillo termina en la última puerta
            a, b = max(a, pc["tramo"][0]), min(b, pc["tramo"][1])
        pos[i] |= {a, b}
        pos[i] |= {j["x"] for j in pc["junctions"]}
        pos[i] |= {c["x"] for c in pc["cores"]}
    nodos, idx = [], {}
    for i in pos:
        for x in sorted(pos[i]):
            if idx.get((i, round(x, 6))) is None:
                idx[(i, round(x, 6))] = len(nodos)
                nodos.append((i, x))
    aristas = []                                           # (u, v, largo)
    for i in pos:
        xs = sorted({round(x, 6) for x in pos[i]})
        for x0, x1 in zip(xs, xs[1:]):
            aristas.append((idx[(i, x0)], idx[(i, x1)], x1 - x0))
    vistas = set()
    for i, pc in enumerate(pieces):
        for j in pc["junctions"]:
            u, v = idx.get((i, round(j["x"], 6))), idx.get((j["nb"], round(j["nbx"], 6)))
            if u is not None and v is not None and u != v and frozenset((u, v)) not in vistas:
                vistas.add(frozenset((u, v)))                # la unión en los dos sentidos es un solo tramo
                aristas.append((u, v, 0.0))
    nucleos = {idx[(i, round(c["x"], 6))] for i, pc in enumerate(pieces) for c in pc["cores"]}
    return nodos, aristas, nucleos


def _ady(n, aristas):
    ady = [[] for _ in range(n)]
    for k, (u, v, w) in enumerate(aristas):
        ady[u].append((v, w, k))
        ady[v].append((u, w, k))
    return ady


def _alcanzan(ady, nucleos, sin_nodo=None, sin_arista=None):
    """Nodos desde los que se llega a un núcleo sin pasar por un nodo o por una arista."""
    vis = {c for c in nucleos if c != sin_nodo}
    cola = list(vis)
    while cola:
        u = cola.pop()
        for v, _, k in ady[u]:
            if k != sin_arista and v != sin_nodo and v not in vis:
                vis.add(v)
                cola.append(v)
    return vis


def _dijkstra(ady, fuentes, sin_arista=None, origen=False):
    """Distancia de cada nodo a la fuente más cercana; con origen=True, también cuál es esa fuente."""
    d, o = [INF] * len(ady), [None] * len(ady)
    q = [(0.0, s) for s in fuentes]
    for s in fuentes:
        d[s], o[s] = 0.0, s
    heapq.heapify(q)
    while q:
        dd, u = heapq.heappop(q)
        if dd > d[u]:
            continue
        for v, w, k in ady[u]:
            if k != sin_arista and dd + w < d[v]:
                d[v], o[v] = dd + w, o[u]
                heapq.heappush(q, (d[v], v))
    return (d, o) if origen else d


def analizar(pieces):
    """Recorrido y fondo de saco en la red de pasillos de un bloque. Devuelve un dict con:
    nodos, aristas, rec (recorrido de cada nodo hasta un núcleo), saco_nodo y, por arista, «tramo»: None si desde
    cualquier punto se sale en dos direcciones; (nodo de salida, distancia desde ese nodo hasta un punto con dos
    salidas) si hay una sola; o (None, INF) si no se llega a ningún núcleo."""
    nodos, aristas, nucleos = _red(pieces)
    n = len(nodos)
    ady = _ady(n, aristas)
    rec, origen = _dijkstra(ady, nucleos, origen=True)
    seguros = set(nucleos)                                 # núcleos y nodos con dos direcciones de salida
    for N in range(n):
        if N not in seguros and nucleos:
            r = _alcanzan(ady, nucleos, sin_nodo=N)
            if sum(1 for v, _, k in ady[N] if v in r) >= 2:
                seguros.add(N)
    tramo = []
    for k, (u, v, w) in enumerate(aristas):
        r = _alcanzan(ady, nucleos, sin_arista=k)
        if u in r and v in r:
            tramo.append(None)
        elif u in r or v in r:
            s = u if u in r else v
            tramo.append((s, _dijkstra(ady, seguros, sin_arista=k)[s]))
        else:
            tramo.append((None, INF))
    saco_nodo = []
    for N in range(n):
        if N in seguros:
            saco_nodo.append(0.0)
            continue
        mejor = INF                                        # por la arista que sale de N hacia el otro extremo
        for v, w, k in ady[N]:
            t = tramo[k]
            if t is not None and t[0] is not None and t[0] != N:
                mejor = min(mejor, w + t[1])
        saco_nodo.append(mejor)
    return {"nodos": nodos, "aristas": aristas, "rec": rec, "origen": origen, "tramo": tramo, "saco_nodo": saco_nodo}


def _sobre(red, i, x):
    """Arista del eje de la pieza i que contiene x (k, nodo a la izquierda, a la derecha) o el nodo más cercano."""
    nodos, aristas = red["nodos"], red["aristas"]
    sobre = sorted((nx, k) for k, (ni, nx) in enumerate(nodos) if ni == i)
    if not sobre:
        return None, None
    izq = [t for t in sobre if t[0] <= x + 1e-9]
    der = [t for t in sobre if t[0] >= x - 1e-9]
    if izq and der:
        a, b = izq[-1][1], der[0][1]
        if a == b:
            return None, a
        k = next((k for k, (u, v, w) in enumerate(aristas) if {u, v} == {a, b} and w > 0), None)
        return k, (a, b)
    return None, (izq[-1][1] if izq else der[0][1])


def recorrido(red, i, x):
    """Distancia por el pasillo desde el punto x del eje de la pieza i hasta el núcleo más cercano."""
    k, ab = _sobre(red, i, x)
    if ab is None:
        return INF
    nodos, rec = red["nodos"], red["rec"]
    ns = ab if isinstance(ab, tuple) else (ab,)
    return min(rec[N] + abs(x - nodos[N][1]) for N in ns)


def nucleo(red, i, x):
    """(pieza, x) del núcleo más cercano por el pasillo desde el punto x del eje de la pieza i, o None (R10.7: las
    viviendas que sirve cada núcleo)."""
    k, ab = _sobre(red, i, x)
    if ab is None:
        return None
    nodos, rec = red["nodos"], red["rec"]
    N = min(ab if isinstance(ab, tuple) else (ab,), key=lambda N: rec[N] + abs(x - nodos[N][1]))
    return nodos[red["origen"][N]] if rec[N] < INF else None


def saco(red, i, x):
    """Fondo de saco desde el punto x del eje de la pieza i (0 si se puede salir en dos direcciones)."""
    k, ab = _sobre(red, i, x)
    if ab is None:
        return INF
    nodos = red["nodos"]
    if k is None:                                           # sobre un nodo o más allá del extremo del eje
        N = ab[0] if isinstance(ab, tuple) else ab
        return abs(x - nodos[N][1]) + red["saco_nodo"][N]
    t = red["tramo"][k]
    if t is None:
        return 0.0
    s, d = t
    return INF if s is None else abs(x - nodos[s][1]) + d


def tramos(pieces, red, limite, que):
    """Tramos del eje del pasillo (en mundo) donde el recorrido (que="recorrido") o el fondo de saco (que="saco")
    supera el límite: [[p, q], ...]."""
    nodos, aristas = red["nodos"], red["aristas"]
    out = []
    for k, (u, v, w) in enumerate(aristas):
        (iu, xu), (iv, xv) = nodos[u], nodos[v]
        if iu != iv or w <= 0:
            continue
        if que == "recorrido":                              # t desde u: min(du + t, dv + w - t) > límite
            du, dv = red["rec"][u], red["rec"][v]
            t0 = max(0.0, limite - du) if du != INF else 0.0
            t1 = min(w, w - (limite - dv)) if dv != INF else w
        else:                                               # t desde u: t_salida + d > límite
            t = red["tramo"][k]
            if t is None:
                continue
            s_, d = t
            if s_ is None:
                t0, t1 = 0.0, w
            elif s_ == u:
                t0, t1 = max(0.0, limite - d), w
            else:
                t0, t1 = 0.0, w - max(0.0, limite - d)
        if t1 - t0 > 0.05:
            sg = 1.0 if xv >= xu else -1.0
            pc = pieces[iu]
            out.append(G.pol_to_list(G.to_world([(xu + sg * t0, 0.0), (xu + sg * t1, 0.0)], pc["origin"], pc["angle"])))
    return out
