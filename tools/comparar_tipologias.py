#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comparación plano por plano del motor contra la base de tipologías (R5.16b, segunda parte).

Uso:  python tools/comparar_tipologias.py [carpeta] [--solo-alta]

Para cada vivienda de `data/tipologias/` (un DXF `U_…` por vivienda; con `--solo-alta`, solo las de precisión alta) arma
su contorno en el marco que espera `plans.layout_unit` (x a lo largo de la fachada, v = profundidad desde el pasillo
común: el lado de la entrada real pasa a ser v = 0, girando el dibujo si la entrada no está abajo), construye
`is_facade` con los tramos de `Trazo_Fachada` del DXF (y `is_facade.ventana`, la prueba estricta, con los mismos
tramos: donde hay fachada dibujada hay aire) y llama a `plans.layout_unit` con los dormitorios de la tipología, las
medidas de `standards.merged({})` y la entrada real (`entrada=(lo, hi)`, el tramo de la puerta con medio metro a cada
lado); si el motor no puede poner ahí su puerta, se queda con su plano libre y lo anota (`entrada_aceptada`).

Por vivienda compara: las estancias del motor contra las reales por grupo (estar, cocina, dormitorios, baños…: cantidad
y superficie), qué locales habitables tocan la fachada en cada uno, el esquema (dónde quedan la zona de día y la de
noche respecto del pasillo común y de las fachadas), el frente que el motor pediría (`plans.frente_min`) contra el
real, la calidad del plano del motor con sus avisos (agrupados en fallas: frente, luz, mínimos, programa, acceso,
fondo, sin uso, equipamiento…) y la superficie sin uso. Resume por tipología y por esquema real. Escribe
`comparacion.json` y `COMPARACION.md` en la carpeta.

Esquemas reales (por los datos, con los tramos de fachada y qué local toca cada uno):
- «lado a lado»: una sola fachada y el estar y todos los dormitorios (o la zona de dormir) la tocan, uno al lado del
  otro (el modelo del motor);
- «en fila»: una sola fachada, pero algún local habitable queda detrás de otro (sin fachada propia; en un ambiente
  abierto toma la luz del que la toca);
- «pasante»: dos fachadas opuestas (calle y contrafrente o patio): el estar en una y los dormitorios en la otra;
- «esquina»: dos fachadas perpendiculares (la principal y una lateral);
- «dúplex»: una vivienda en varios niveles (un archivo por nivel; no se compara con el motor, que hace un solo nivel).

Solo biblioteca estándar; importa `engine` como `tools/ver_dxf.py`.
"""
import json
import os
import statistics
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
from engine import geometry as G       # noqa: E402
from engine import plans as P          # noqa: E402
from engine import standards as ST     # noqa: E402
from engine import tipologias as T     # noqa: E402

CARPETA = T.CARPETA
TOL_FACHADA = 0.35        # m: un borde «toca» la fachada si sus puntos interiores quedan a menos de esto de un tramo
MARGEN_ENTRADA = 0.50     # m: el pasillo común, a cada lado de la puerta real, para `layout_unit(entrada=)`
LARGO_BORDE = 0.60        # m: un borde más corto no cuenta para la fachada de una estancia
LADOS = ("abajo", "arriba", "izquierda", "derecha")
OPUESTO = {"abajo": "arriba", "arriba": "abajo", "izquierda": "derecha", "derecha": "izquierda"}
# grupo de comparación de cada `kind` (el «Hall / Cocina» del motor cuenta como cocina)
GRUPO = {"living": "estar", "dining": "estar", "sleep": "dormir", "kitchen": "cocina", "bedroom": "dormitorio",
         "bath": "baño", "hall": "hall", "hallway": "pasillo", "laundry": "lavadero", "storage": "depósito",
         "study": "estudio", "vestidor": "vestidor"}
GRUPOS = ("estar", "cocina", "dormitorio", "dormir", "baño", "hall", "pasillo", "lavadero", "depósito", "estudio",
          "vestidor")
ZONA = {"estar": "día", "cocina": "día", "dormitorio": "noche", "dormir": "noche", "estudio": "noche",
        "vestidor": "noche", "baño": "servicios", "hall": "servicios", "pasillo": "servicios",
        "lavadero": "servicios", "depósito": "servicios"}
HABITABLES = ("estar", "dormitorio", "dormir")       # los que deciden el esquema (el estudio es un anexo)
ESQUEMAS = ("lado a lado", "en fila", "pasante", "esquina", "dúplex", "sin fachada")
# fallas del plano del motor, por el texto de sus comprobaciones (la primera que coincide)
FALLAS = (("entrada", ("La puerta de entrada no da",)),
          ("frente", ("Frente de", "insuficiente para estar")),
          ("fondo", ("Fondo de",)),
          ("luz", ("sin fachada", "sin luz", "no entra una ventana", "ventana")),
          ("programa", ("Sin cocina", "Sin baño", "Sin estar", "Sin dormitorio")),
          ("acceso", ("Sin acceso", "no conecta", "Sin puerta de entrada")),
          ("mínimos", ("< mínimo", "mínimo")),
          ("superficie", ("superficie mínima", "art. 3", "art. 2")),
          ("art. 14", ("art. 14",)),
          ("sin uso", ("Sin uso",)),
          ("equipamiento", ("no entra", "no entran")))
GRAVES = ("frente", "fondo", "luz", "programa", "acceso", "mínimos", "superficie")   # con una de estas, no resuelve


# ------------------------------------------------------------------ marco de la vivienda
def _giro(lado):
    """La rotación (sin reflejar) que lleva el lado de la entrada abajo: (x, y) -> (x', y')."""
    return {"abajo": lambda p: (p[0], p[1]), "arriba": lambda p: (-p[0], -p[1]),
            "izquierda": lambda p: (-p[1], p[0]), "derecha": lambda p: (p[1], -p[0])}[lado]


def _lado_normal(a, b, poly):
    """El lado (abajo, arriba, izquierda, derecha) hacia el que mira un tramo de fachada a-b del contorno poly: su
    normal hacia afuera (la que no entra en el polígono), por su componente mayor."""
    L = T._dist(b[0] - a[0], b[1] - a[1])
    if L < 1e-9:
        return None
    n = ((b[1] - a[1]) / L, -(b[0] - a[0]) / L)
    m = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
    if G.point_in_poly((m[0] + n[0] * 0.3, m[1] + n[1] * 0.3), poly):
        n = (-n[0], -n[1])
    if abs(n[0]) >= abs(n[1]):
        return "derecha" if n[0] > 0 else "izquierda"
    return "arriba" if n[1] > 0 else "abajo"


def marco_de(v, datos):
    """El contorno, las estancias, los tramos de fachada (con su rótulo y su lado) y la entrada de la vivienda v (del
    catálogo) en el marco de `layout_unit`: el lado de la entrada abajo y el origen en la esquina inferior izquierda."""
    V = T.ver_dxf()
    lado = (v["entrada"] or {}).get("lado")
    g = _giro(lado or "abajo")
    contorno = [g(tuple(p)) for p in v["contorno"]]
    x0, y0, _, _ = G.bbox(contorno)
    tr = lambda p: (g(p)[0] - x0, g(p)[1] - y0)
    poly = G.ensure_ccw([tr(tuple(p)) for p in v["contorno"]])
    textos = [t for t in datos["textos"] if t["rol"] == "fachada"]
    fachadas = []                                      # (a, b, rotulo, lado)
    for f in datos["formas"]:
        if f["rol"] != "fachada" or f["punto"] or len(f["pts"]) < 2:
            continue
        segs = V._segmentos([f], "fachada")
        rotulo, mejor = None, T.ROTULO_TOL
        for t in textos:
            d = min(T._dist_seg(t["p"], a, b) for a, b in segs)
            if d <= mejor:
                rotulo, mejor = t["texto"], d
        for a, b in segs:
            a, b = tr(a), tr(b)
            fachadas.append((a, b, rotulo, _lado_normal(a, b, poly)))
    medianeras = [(tr(a), tr(b)) for a, b in V._segmentos(datos["formas"], "medianeras")]
    estancias = []
    for e in v["estancias"]:
        pts = [tr(tuple(p)) for p in e["pts"]]
        bx0, by0, bx1, by1 = G.bbox(pts)
        estancias.append({"nombre": e["nombre"], "kind": e["kind"], "grupo": GRUPO.get(e["kind"], "otro"),
                          "area": e["area"], "pts": pts, "rect": (bx0, by0, bx1, by1), "abierto": e["abierto"],
                          "fachada_catalogo": e["fachada"], "ancho": e["ancho"], "fondo": e["fondo"]})
    entrada = None
    if v["entrada"]:
        m = tr(tuple(v["entrada"]["medio"]))
        entrada = (m[0] - v["entrada"]["ancho"] / 2.0, m[0] + v["entrada"]["ancho"] / 2.0)
    bx0, by0, bx1, by1 = G.bbox(poly)
    return {"poly": poly, "fachadas": fachadas, "medianeras": medianeras, "estancias": estancias, "entrada": entrada,
            "lado_entrada": lado, "ancho": bx1 - bx0, "fondo": by1 - by0}


def is_facade_de(fachadas, tol=TOL_FACHADA):
    """La prueba `is_facade(p, q)` de `layout_unit` con los tramos de Trazo_Fachada: los puntos interiores del segmento
    quedan a menos de tol de algún tramo. La estricta (`ventana`) es la misma: los tramos dibujados ya son los que dan
    al aire."""
    segs = [(a, b) for a, b, _, _ in fachadas]

    def f(p, q):
        if not segs:
            return False
        for t in (0.25, 0.5, 0.75):
            m = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
            if min(T._dist_seg(m, a, b) for a, b in segs) > tol:
                return False
        return True
    f.ventana = f
    return f


def lados_de(pts, fachadas, tol=TOL_FACHADA, largo=LARGO_BORDE):
    """Los lados de fachada (abajo, arriba…) que toca una estancia: un borde suyo de `largo` o más con sus puntos
    interiores a menos de tol de un tramo de ese lado."""
    out = []
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        if T._dist(q[0] - p[0], q[1] - p[1]) < largo:
            continue
        ms = [(p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t) for t in (0.25, 0.5, 0.75)]
        for a, b, _, lado in fachadas:
            if lado and lado not in out and all(T._dist_seg(m, a, b) <= tol for m in ms):
                out.append(lado)
    return sorted(out, key=LADOS.index)


# ------------------------------------------------------------------ esquema y zonas
def esquema_de(estancias, nivel=None, nb=1, rotulos=None):
    """(esquema, detalle) de un plano por sus locales habitables y los lados de fachada que tocan (ver el módulo). En un
    monoambiente (nb 0) la cocina cuenta como parte del ambiente único. rotulos: {lado: [rótulos]} de las fachadas:
    dos lados con «Calle» y «Contrafrente» son opuestos aunque un balcón oblicuo los dibuje perpendiculares."""
    if nivel is not None:
        return "dúplex", "nivel %d" % nivel
    grupos = HABITABLES + (("cocina",) if nb == 0 else ())
    hab = [e for e in estancias if e["grupo"] in grupos]
    estar = [e for e in hab if e["grupo"] in ("estar", "cocina")]
    noche = [e for e in hab if e["grupo"] in ("dormitorio", "dormir")]
    lados = []
    for e in hab:
        for l in e["lados"]:
            if l not in lados:
                lados.append(l)
    lados.sort(key=LADOS.index)
    le = sorted({l for e in estar for l in e["lados"]}, key=LADOS.index)
    ln = sorted({l for e in noche for l in e["lados"]}, key=LADOS.index)
    detalle = "estar: %s; dormitorios: %s" % (", ".join(le) or "sin fachada propia", ", ".join(ln) or "sin fachada propia")
    if not lados:
        return "sin fachada", detalle
    if len(lados) == 1:
        propios = [e for e in hab if e["kind"] != "dining"]        # el comedor interior no decide
        return ("lado a lado" if all(e["lados"] for e in propios) else "en fila"), detalle
    if len(lados) == 2 and OPUESTO[lados[0]] == lados[1]:
        return "pasante", detalle
    if rotulos and le and ln and not set(le) & set(ln):
        re_ = {r for l in le for r in rotulos.get(l, ())}
        rn_ = {r for l in ln for r in rotulos.get(l, ())}
        if ("Calle" in re_ and "Contrafrente" in rn_) or ("Contrafrente" in re_ and "Calle" in rn_):
            return "pasante", detalle
    return "esquina", detalle


def _posicion(r, D, tol=0.5):
    """Dónde queda una zona en el fondo de la vivienda: junto al pasillo común (v = 0), al fondo (v = D), de lado a
    lado (las dos) o en el medio."""
    abajo, arriba = r[1] <= tol, r[3] >= D - tol
    return "pasante" if abajo and arriba else "pasillo" if abajo else "fondo" if arriba else "medio"


def zonas_de(estancias, D):
    """Las zonas del plano de una vivienda de fondo D: para día, noche y servicios, su caja (x0, v0, x1, v1), su ancho,
    su fondo y su posición (ver _posicion); la disposición de día y noche («lado a lado»: una junto a la otra a lo
    ancho; «en fila»: una detrás de la otra en el fondo; «mezcladas») y la secuencia de locales desde el pasillo común
    (por el centro de cada uno en v; los que quedan a menos de 1,2 m van juntos con «+»; «|» separa las bandas).
    Devuelve (zonas, orden, secuencia)."""
    out = {}
    for z in ("día", "noche", "servicios"):
        es = [e for e in estancias if ZONA.get(e["grupo"]) == z]
        if not es:
            continue
        r = (min(e["rect"][0] for e in es), min(e["rect"][1] for e in es), max(e["rect"][2] for e in es),
             max(e["rect"][3] for e in es))
        A = sum(e["area"] for e in es) or 1.0
        out[z] = {"rect": r, "ancho": r[2] - r[0], "fondo": r[3] - r[1], "area": sum(e["area"] for e in es),
                  "centro_v": sum(e["area"] * (e["rect"][1] + e["rect"][3]) / 2.0 for e in es) / A,
                  "posicion": _posicion(r, D)}
    disp = None
    if "día" in out and "noche" in out:
        a, b = out["día"]["rect"], out["noche"]["rect"]
        sx = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) / max(1e-6, min(a[2] - a[0], b[2] - b[0]))
        sv = max(0.0, min(a[3], b[3]) - max(a[1], b[1])) / max(1e-6, min(a[3] - a[1], b[3] - b[1]))
        disp = "lado a lado" if sx < 0.3 else "en fila" if sv < 0.3 else "mezcladas"
    orden = ", ".join("%s %s" % (z, {"pasillo": "junto al pasillo", "fondo": "al fondo", "pasante": "de lado a lado",
                                      "medio": "en el medio"}[out[z]["posicion"]])
                      for z in ("día", "noche", "servicios") if z in out)
    if disp:
        orden += "; día y noche %s" % disp
    centro = lambda e: (e["rect"][1] + e["rect"][3]) / 2.0
    bandas, ini = [], None
    for e in sorted(estancias, key=centro):
        if ini is None or centro(e) - ini > 1.2:
            bandas.append([])
            ini = centro(e)
        bandas[-1].append(e["nombre"])
    secuencia = " | ".join(" + ".join(b) for b in bandas)
    return out, orden, secuencia, disp


def _fallas(checks):
    """Las fallas del plano (por categoría, en el orden en que aparecen) y los avisos que las producen."""
    cats, msgs = [], []
    for c in checks:
        if c.get("ok") or c.get("info"):
            continue
        msgs.append(c["msg"])
        cat = next((k for k, claves in FALLAS if any(s in c["msg"] for s in claves)), "otros")
        if cat not in cats:
            cats.append(cat)
    return cats, msgs


# ------------------------------------------------------------------ una vivienda
def _plano_motor(marco, nb, S, entrada):
    res = P.layout_unit(marco["poly"], nb, is_facade_de(marco["fachadas"]), S["vivienda"], S["equipamiento"], False,
                        None, S["ventanas"], entrada)
    return res


def comparar_vivienda(v, datos, S=None):
    """La comparación de una vivienda del catálogo (v) con el plano que hace el motor en su contorno. Devuelve el
    registro de `comparacion.json` (ver el módulo)."""
    S = S or ST.merged({})
    P.configure(S["vivienda"], S["equipamiento"])
    marco = marco_de(v, datos)
    nb = int(v["dormitorios"])
    for e in marco["estancias"]:
        e["lados"] = lados_de(e["pts"], marco["fachadas"])
    fach = {}
    for a, b, rot, lado in marco["fachadas"]:
        k = fach.setdefault(lado or "oblicua", {"lado": lado or "oblicua", "largo": 0.0, "rotulos": [], "habitables": []})
        k["largo"] += T._dist(b[0] - a[0], b[1] - a[1])
        if rot and rot not in k["rotulos"]:
            k["rotulos"].append(rot)
    rotulos = {l: f["rotulos"] for l, f in fach.items()}
    esq_real, det_real = esquema_de(marco["estancias"], v["nivel"], nb, rotulos)
    zr, orden_real, sec_real, disp_real = zonas_de(marco["estancias"], marco["fondo"])
    for e in marco["estancias"]:
        for l in e["lados"]:
            if e["grupo"] in HABITABLES + ("cocina", "estudio") and e["nombre"] not in fach[l]["habitables"]:
                fach[l]["habitables"].append(e["nombre"])
    fachadas = [dict(f, largo=T._r(f["largo"], 2)) for f in sorted(fach.values(), key=lambda f: -f["largo"])]
    real = {"frente": v["frente"], "fondo": v["fondo"], "area_muros": v["area_muros"],
            "superficie_util": v["superficie_util"], "fachadas": fachadas, "esquema": esq_real, "detalle": det_real,
            "orden": orden_real, "secuencia": sec_real, "disposicion": disp_real,
            "zonas": {z: {"ancho": T._r(d["ancho"], 2), "fondo": T._r(d["fondo"], 2), "area": T._r(d["area"], 2),
                          "posicion": d["posicion"]} for z, d in zr.items()},
            "estancias": [{"nombre": e["nombre"], "kind": e["kind"], "grupo": e["grupo"], "area": e["area"],
                           "lados": e["lados"], "abierto": e["abierto"], "fachada": e["fachada_catalogo"],
                           "ancho": e["ancho"], "fondo": e["fondo"]} for e in marco["estancias"]],
            "habitables_con_fachada": sorted(e["nombre"] for e in marco["estancias"]
                                             if e["grupo"] in HABITABLES and e["lados"]),
            "habitables_sin_fachada": sorted(e["nombre"] for e in marco["estancias"]
                                             if e["grupo"] in HABITABLES and not e["lados"])}
    out = {"archivo": v["archivo"], "vivienda_id": v["vivienda_id"], "proyecto": v["proyecto"],
           "tipologia": v["tipologia"], "dormitorios": nb, "precision": v["precision"], "crujia": v["crujia"],
           "nivel": v["nivel"], "marco": {"lado_entrada": marco["lado_entrada"], "ancho": T._r(marco["ancho"], 2),
                                          "fondo": T._r(marco["fondo"], 2), "girado": marco["lado_entrada"] != "abajo"},
           "real": real, "comparable": v["nivel"] is None and bool(marco["fachadas"]),
           "motivo": None if v["nivel"] is None else "dúplex: el motor hace un solo nivel"}
    if not marco["fachadas"]:
        out["motivo"] = "sin Trazo_Fachada"
    # el frente que pide el motor, con el fondo real (y con el de la convención: frente × fondo del catálogo)
    out["motor"] = {"frente_min": T._r(P.frente_min(nb, marco["fondo"]), 2),
                    "frente_min_convencion": T._r(P.frente_min(nb, v["fondo"]), 2),
                    "facade_min": T._r(P.facade_min(nb), 2), "fondo_min": T._r(P.fondo_min(), 2),
                    "fondo_sin_tira": T._r(P.fondo_sin_tira(), 2)}
    out["frente_sobre_min"] = T._r(v["frente"] / out["motor"]["frente_min_convencion"], 2) \
        if out["motor"]["frente_min_convencion"] else None
    if not out["comparable"]:
        return out
    libre = _plano_motor(marco, nb, S, None)
    P.superficie_vivienda(libre, v["area_muros"], S["vivienda"])
    res, aceptada = libre, None
    if marco["entrada"]:
        con = _plano_motor(marco, nb, S, (marco["entrada"][0] - MARGEN_ENTRADA, marco["entrada"][1] + MARGEN_ENTRADA))
        P.superficie_vivienda(con, v["area_muros"], S["vivienda"])
        aceptada = not any(c["msg"].startswith("La puerta de entrada no da") for c in con["checks"] if not c["ok"])
        if aceptada:
            res = con
    rooms = []
    for r in res["rooms"]:
        bx0, by0, bx1, by1 = G.bbox(r["poly"])
        grupo = "cocina" if "Cocina" in r["name"] else GRUPO.get(r["kind"], "otro")
        rooms.append({"nombre": r["name"], "kind": r["kind"], "grupo": grupo, "area": T._r(r["area"], 2),
                      "rect": (bx0, by0, bx1, by1), "lados": lados_de(r["poly"], marco["fachadas"]), "abierto": False})
    esq_m, det_m = esquema_de(rooms, None, nb, rotulos)
    zm, orden_m, sec_m, disp_m = zonas_de(rooms, marco["fondo"])
    fallas, msgs = _fallas(res["checks"])
    puerta = next((d for d in res["doors"] if d.get("entry")), None)
    sin_uso = sum(abs(G.area(p)) for p in res["sin_uso"])
    out["motor"].update({
        "score": res["score"], "score_libre": libre["score"], "entrada_aceptada": aceptada,
        "puerta": T._r((puerta["p"][0] + puerta["q"][0]) / 2.0, 2) if puerta else None,
        "puerta_real": T._r((marco["entrada"][0] + marco["entrada"][1]) / 2.0, 2) if marco["entrada"] else None,
        "fallas": fallas, "avisos": msgs, "resuelve": not any(f in GRAVES for f in fallas),
        "sin_uso": T._r(sin_uso, 2), "facade": res["facade"], "esquema": esq_m, "detalle": det_m, "orden": orden_m,
        "secuencia": sec_m, "disposicion": disp_m,
        "zonas": {z: {"ancho": T._r(d["ancho"], 2), "fondo": T._r(d["fondo"], 2), "area": T._r(d["area"], 2),
                      "posicion": d["posicion"]} for z, d in zm.items()},
        "estancias": [{"nombre": r["nombre"], "kind": r["kind"], "grupo": r["grupo"], "area": r["area"],
                       "lados": r["lados"]} for r in rooms],
        "habitables_con_fachada": sorted(r["nombre"] for r in rooms if r["grupo"] in HABITABLES and r["lados"]),
        "habitables_sin_fachada": sorted(r["nombre"] for r in rooms if r["grupo"] in HABITABLES and not r["lados"])})
    # por grupo: cantidad y superficie, real contra motor
    por_grupo = {}
    for g in GRUPOS:
        er = [e for e in marco["estancias"] if e["grupo"] == g]
        em = [r for r in rooms if r["grupo"] == g]
        if er or em:
            por_grupo[g] = {"real_n": len(er), "real_area": T._r(sum(e["area"] for e in er), 2),
                            "motor_n": len(em), "motor_area": T._r(sum(r["area"] for r in em), 2)}
    out["comparacion"] = {"por_grupo": por_grupo, "esquema_igual": esq_m == esq_real,
                          "fachada": {"real": real["habitables_con_fachada"],
                                      "motor": out["motor"]["habitables_con_fachada"]},
                          "dormitorios_motor": sum(1 for r in rooms if r["grupo"] == "dormitorio"),
                          "sin_uso_motor": T._r(sin_uso, 2)}
    # el mismo plano en el rectángulo envolvente (frente × fondo): separa lo que falla por el contorno irregular (un
    # entrante del núcleo o del hall deja a _main_rect un rectángulo principal angosto y el resto como anexos) de lo
    # que falla por el esquema y el frente
    W, D = marco["ancho"], marco["fondo"]
    rectangular = abs(G.area(marco["poly"])) >= 0.995 * W * D
    if rectangular:
        rect = res
    else:
        caja = dict(marco, poly=[(0.0, 0.0), (W, 0.0), (W, D), (0.0, D)])
        rect = _plano_motor(caja, nb, S, (marco["entrada"][0] - MARGEN_ENTRADA, marco["entrada"][1] + MARGEN_ENTRADA)
                            if aceptada else None)
        P.superficie_vivienda(rect, v["area_muros"], S["vivienda"])
    fr, _ = _fallas(rect["checks"])
    rrooms = []
    for r_ in rect["rooms"]:
        bx0, by0, bx1, by1 = G.bbox(r_["poly"])
        rrooms.append({"nombre": r_["name"], "kind": r_["kind"], "grupo": "cocina" if "Cocina" in r_["name"] else
                       GRUPO.get(r_["kind"], "otro"), "area": r_["area"], "rect": (bx0, by0, bx1, by1),
                       "lados": lados_de(r_["poly"], marco["fachadas"]), "abierto": False})
    out["motor"]["rectangulo"] = {"rectangular": rectangular, "score": rect["score"], "fallas": fr,
                                  "resuelve": not any(f in GRAVES for f in fr), "esquema": esquema_de(rrooms, None, nb, rotulos)[0],
                                  "dormitorios": sum(1 for r_ in rrooms if r_["grupo"] == "dormitorio"),
                                  "sin_uso": T._r(sum(abs(G.area(p)) for p in rect["sin_uso"]), 2)}
    return out


# ------------------------------------------------------------------ la base
def comparar_base(carpeta=CARPETA, solo_alta=False):
    """Compara todas las viviendas de la carpeta (DXF `U_…`). Devuelve {version, archivos, viviendas, resumen}."""
    idx = T.leer_indice(carpeta)
    S = ST.merged({})
    out, avisos = [], []
    for nombre in sorted(os.listdir(carpeta)):
        if not nombre.lower().endswith(".dxf") or not nombre.startswith("U_"):
            continue
        ruta = os.path.join(carpeta, nombre)
        try:
            V, datos, inf = T._cargar(ruta)
            v = T._vivienda(ruta, V, datos, inf, idx.get(nombre))
        except (T.ErrorTipologia, ValueError) as e:
            avisos.append("%s: %s" % (nombre, e))
            continue
        if solo_alta and v["precision"] != "alta":
            continue
        out.append(comparar_vivienda(v, datos, S))
    return {"version": T.version(), "archivos": len(out), "avisos": avisos, "viviendas": out,
            "resumen": resumen(out)}


def _med(vals, n=2):
    """Mediana redondeada a n decimales (con n = 0, un entero); None sin valores."""
    vals = [x for x in vals if x is not None]
    if not vals:
        return None
    return int(round(statistics.median(vals))) if n == 0 else T._r(statistics.median(vals), n)


def _cuenta(vals):
    d = {}
    for x in vals:
        d[x] = d.get(x, 0) + 1
    return dict(sorted(d.items(), key=lambda kv: (-kv[1], str(kv[0]))))


def _unidades(viviendas):
    """Una entrada por vivienda (los niveles de un dúplex, una vez: el primero)."""
    vistos, out = set(), []
    for v in viviendas:
        if v["vivienda_id"] in vistos:
            continue
        vistos.add(v["vivienda_id"])
        out.append(v)
    return out


def _resumen_tipologia(vs):
    comp = [v for v in vs if v["comparable"]]
    fallas = _cuenta(f for v in comp for f in v["motor"]["fallas"])
    return {"n": len(vs), "comparables": len(comp), "precision": _cuenta(v["precision"] for v in vs),
            "frente_real": _med([v["real"]["frente"] for v in vs]), "fondo_real": _med([v["real"]["fondo"] for v in vs]),
            "frente_min_motor": _med([v["motor"]["frente_min_convencion"] for v in vs]),
            "frente_sobre_min": _med([v["frente_sobre_min"] for v in vs]),
            "entran_con_su_frente": sum(1 for v in vs if v["frente_sobre_min"] is not None and v["frente_sobre_min"] >= 1.0),
            "esquemas": _cuenta(v["real"]["esquema"] for v in vs),
            "score": _med([v["motor"]["score"] for v in comp], 0),
            "score_libre": _med([v["motor"]["score_libre"] for v in comp], 0),
            "resuelve": sum(1 for v in comp if v["motor"]["resuelve"]),
            "score_rect": _med([v["motor"]["rectangulo"]["score"] for v in comp], 0),
            "resuelve_rect": sum(1 for v in comp if v["motor"]["rectangulo"]["resuelve"]),
            "irregulares": sum(1 for v in comp if not v["motor"]["rectangulo"]["rectangular"]),
            "entrada_aceptada": sum(1 for v in comp if v["motor"]["entrada_aceptada"]),
            "sin_uso": _med([v["motor"]["sin_uso"] for v in comp]),
            "fallas": fallas,
            "esquema_motor": _cuenta(v["motor"]["esquema"] for v in comp)}


def _resumen_esquema(vs):
    us = _unidades(vs)
    comp = [v for v in vs if v["comparable"]]
    noche = [v["real"]["zonas"]["noche"] for v in vs if "noche" in v["real"]["zonas"]]
    return {"n": len(us), "archivos": len(vs), "tipologias": _cuenta(v["tipologia"] for v in us),
            "precision": _cuenta(v["precision"] for v in us),
            "frente_real": _med([v["real"]["frente"] for v in us]), "fondo_real": _med([v["real"]["fondo"] for v in us]),
            "fachadas_n": _med([len(v["real"]["fachadas"]) for v in us], 0),
            "rotulos": _cuenta(r for v in us for f in v["real"]["fachadas"] for r in f["rotulos"]),
            "detalle": _cuenta(v["real"]["detalle"] for v in us),
            "orden": _cuenta(v["real"]["orden"] for v in vs),
            "posicion_dia": _cuenta(v["real"]["zonas"]["día"]["posicion"] for v in vs if "día" in v["real"]["zonas"]),
            "posicion_noche": _cuenta(z["posicion"] for z in noche),
            "disposicion": _cuenta(v["real"]["disposicion"] for v in vs if v["real"]["disposicion"]),
            "noche_ancho": _med([z["ancho"] for z in noche]), "noche_fondo": _med([z["fondo"] for z in noche]),
            "dia_ancho": _med([v["real"]["zonas"]["día"]["ancho"] for v in vs if "día" in v["real"]["zonas"]]),
            "dia_fondo": _med([v["real"]["zonas"]["día"]["fondo"] for v in vs if "día" in v["real"]["zonas"]]),
            "comparables": len(comp), "score": _med([v["motor"]["score"] for v in comp], 0),
            "resuelve": sum(1 for v in comp if v["motor"]["resuelve"]),
            "score_rect": _med([v["motor"]["rectangulo"]["score"] for v in comp], 0),
            "resuelve_rect": sum(1 for v in comp if v["motor"]["rectangulo"]["resuelve"]),
            "esquema_motor": _cuenta(v["motor"]["esquema"] for v in comp),
            "fallas": _cuenta(f for v in comp for f in v["motor"]["fallas"]),
            "frente_sobre_min": _med([v["frente_sobre_min"] for v in us])}


def _resumen_grupos(comp):
    """Por grupo de estancias: en cuántas viviendas aparece y la superficie mediana por vivienda, real y motor, y
    cuántos locales habitables tocan la fachada."""
    out = {}
    for g in GRUPOS:
        rn = [v["comparacion"]["por_grupo"][g]["real_n"] for v in comp if g in v["comparacion"]["por_grupo"]]
        mn = [v["comparacion"]["por_grupo"][g]["motor_n"] for v in comp if g in v["comparacion"]["por_grupo"]]
        if not rn and not mn:
            continue
        out[g] = {"real_viviendas": sum(1 for n in rn if n), "motor_viviendas": sum(1 for n in mn if n),
                  "real_area": _med([v["comparacion"]["por_grupo"][g]["real_area"] for v in comp
                                     if v["comparacion"]["por_grupo"].get(g, {}).get("real_n")]),
                  "motor_area": _med([v["comparacion"]["por_grupo"][g]["motor_area"] for v in comp
                                      if v["comparacion"]["por_grupo"].get(g, {}).get("motor_n")])}
    fach = {}
    for g in ("estar", "dormitorio", "dormir", "cocina"):
        rt = [e for v in comp for e in v["real"]["estancias"] if e["grupo"] == g]
        mt = [e for v in comp for e in v["motor"]["estancias"] if e["grupo"] == g]
        if rt or mt:
            fach[g] = {"real_n": len(rt), "real_con_fachada": sum(1 for e in rt if e["lados"]),
                       "real_abiertos": sum(1 for e in rt if not e["lados"] and e["abierto"]),
                       "motor_n": len(mt), "motor_con_fachada": sum(1 for e in mt if e["lados"])}
    return out, fach


FRENTES = ("Estar", "Estar-Comedor", "Dormir", "Dormitorio 1", "Dormitorio 2", "Dormitorio 3")


def _frentes(vs):
    """R5.16b (v2.65): el frente (ancho a lo largo de la fachada, en el marco de la convención: la fachada principal
    arriba) de los locales que tocan una fachada, por esquema: lado a lado (el modelo del motor), lado a lado y esquina,
    y todos; y lo que usa el motor (plans: LIV_MIN, BED_MAIN, BED_W y facade_min por dormitorios). Es la fuente de los
    frentes típicos de standards.py («vivienda», typ[0])."""
    out = {}
    for clave, esquemas in (("lado a lado", ("lado a lado",)), ("lado a lado y esquina", ("lado a lado", "esquina")),
                            ("todos", ESQUEMAS)):
        d = {}
        for v in vs:
            if v["real"]["esquema"] not in esquemas:
                continue
            for e in v["real"]["estancias"]:
                if e["nombre"] in FRENTES and e["fachada"] and e.get("ancho") is not None:
                    d.setdefault(e["nombre"], []).append(e["ancho"])
        out[clave] = {k: {"n": len(xs), "mediana": _med(xs), "min": T._r(min(xs), 2), "max": T._r(max(xs), 2)}
                      for k, xs in d.items()}
    S = ST.merged({})
    P.configure(S["vivienda"], S["equipamiento"])
    out["motor"] = {"estar": T._r(P.LIV_MIN, 2), "dorm_principal": T._r(P.BED_MAIN, 2), "dorm_secundario": T._r(P.BED_W, 2),
                    "facade_min": {str(n): T._r(P.facade_min(n), 2) for n in range(5)},
                    "typ": {k: list(S["vivienda"][k]["typ"]) for k in ("estar_comedor", "dorm_principal", "dorm_secundario")}}
    return out


def resumen(viviendas):
    """El resumen de la comparación: por tipología y por esquema real (precisión alta y todas), por grupo de estancias,
    los frentes de los locales en la fachada (`frentes`) y los totales."""
    out = {}
    for clave, vs in (("alta", [v for v in viviendas if v["precision"] == "alta"]), ("todas", viviendas)):
        comp = [v for v in vs if v["comparable"]]
        grupos, fach = _resumen_grupos(comp)
        out[clave] = {"n": len(vs), "viviendas": len(_unidades(vs)), "comparables": len(comp), "frentes": _frentes(vs),
                      "por_tipologia": {t: _resumen_tipologia([v for v in vs if v["tipologia"] == t])
                                        for t in T.TIPOLOGIAS if any(v["tipologia"] == t for v in vs)},
                      "por_esquema": {e: _resumen_esquema([v for v in vs if v["real"]["esquema"] == e])
                                      for e in ESQUEMAS if any(v["real"]["esquema"] == e for v in vs)},
                      "por_grupo": grupos, "fachada": fach,
                      "score": _med([v["motor"]["score"] for v in comp], 0),
                      "resuelve": sum(1 for v in comp if v["motor"]["resuelve"]),
                      "score_rect": _med([v["motor"]["rectangulo"]["score"] for v in comp], 0),
                      "resuelve_rect": sum(1 for v in comp if v["motor"]["rectangulo"]["resuelve"]),
                      "irregulares": sum(1 for v in comp if not v["motor"]["rectangulo"]["rectangular"]),
                      "entran_con_su_frente": sum(1 for v in vs if v["frente_sobre_min"] is not None and
                                                  v["frente_sobre_min"] >= 1.0),
                      "fallas": _cuenta(f for v in comp for f in v["motor"]["fallas"]),
                      "esquema_igual": sum(1 for v in comp if v["comparacion"]["esquema_igual"])}
    return out


# ------------------------------------------------------------------ informe
_f, _tabla = T._f, T._tabla


def _lista(d, n=3, total=None):
    """«a 5, b 3» de un diccionario de cuentas (los n más frecuentes)."""
    items = list(d.items())[:n]
    return ", ".join("%s %d" % (k, c) for k, c in items) if items else "—"


def _fyf(a, b):
    return "%s × %s" % (_f(a), _f(b)) if a is not None and b is not None else "—"


def comparacion_md(cat):
    r = cat["resumen"]
    L = ["# Base de tipologías — el motor contra los planos reales (Trazo v%s)" % cat["version"], ""]
    L.append("Para cada vivienda de la base (`U_…`), `tools/comparar_tipologias.py` pone su contorno en el marco de "
             "`plans.layout_unit` (la entrada real abajo), le da la fachada real (`Trazo_Fachada`) y los dormitorios de "
             "su tipología, y compara lo que dibuja el motor con el plano real. «Frente mínimo» es `plans.frente_min` "
             "(lo que el reparto del mix le daría a esa tipología con ese fondo) y «calidad», la del plano del motor "
             "(100 = todas sus comprobaciones cumplen). «Resuelve» es un plano sin fallas graves (frente, fondo, luz, "
             "programa, acceso, mínimos, superficie); «con su frente», cuántas viviendas reales tienen al menos el frente "
             "que el motor pediría. Los dúplex no se comparan (el motor hace un solo nivel) pero sí se caracterizan. Las "
             "medidas son medianas en metros; las superficies, m². Se leyeron %d archivos." % cat["archivos"])
    L.append("")
    A, Td = r["alta"], r["todas"]
    L.append("**Lectura rápida.** Precisión alta: %d viviendas comparables, calidad mediana del motor %s, resuelve "
             "%d, con el mismo esquema que la base %d, con al menos el frente que el motor pide %d de %d; en el "
             "rectángulo envolvente (sin los entrantes del contorno), calidad %s y resuelve %d. Todas: %d "
             "comparables, calidad mediana %s, resuelve %d (en el rectángulo, %s y %d), con su frente %d de %d. "
             "Esquemas reales (viviendas, los dúplex una vez): %s. Fallas del motor más frecuentes (viviendas "
             "comparables): %s." % (
                 A["comparables"], A["score"], A["resuelve"], A["esquema_igual"], A["entran_con_su_frente"], A["n"],
                 A["score_rect"], A["resuelve_rect"], Td["comparables"], Td["score"], Td["resuelve"], Td["score_rect"],
                 Td["resuelve_rect"], Td["entran_con_su_frente"], Td["n"],
                 _lista({e: d["n"] for e, d in Td["por_esquema"].items()}, 6), _lista(Td["fallas"], 6)))
    L.append("")
    L.append("«En el rectángulo»: el mismo plano del motor en el rectángulo envolvente de la vivienda (frente × fondo, "
             "con la misma fachada): separa lo que falla por el contorno irregular (un entrante del núcleo o del hall "
             "deja al rectángulo principal del motor muy angosto y el resto como anexos) de lo que falla por el esquema "
             "y el frente.")
    L.append("")
    for clave, titulo in (("alta", "precisión alta"), ("todas", "todas las viviendas")):
        R = r[clave]
        L.append("## %s. Por tipología (%s: %d archivos, %d viviendas, %d comparables)" % (
            "1" if clave == "alta" else "3", titulo, R["n"], R["viviendas"], R["comparables"]))
        L.append("")
        filas = []
        for t, d in R["por_tipologia"].items():
            filas.append([t, d["n"], _fyf(d["frente_real"], d["fondo_real"]), _f(d["frente_min_motor"]),
                          _f(d["frente_sobre_min"], 2), "%d de %d" % (d["entran_con_su_frente"], d["n"]),
                          _lista(d["esquemas"], 4), d["comparables"],
                          "—" if d["score"] is None else "%d" % d["score"],
                          "%d de %d" % (d["resuelve"], d["comparables"]) if d["comparables"] else "—",
                          "—" if d["score_rect"] is None else "%d" % d["score_rect"],
                          "%d de %d" % (d["resuelve_rect"], d["comparables"]) if d["comparables"] else "—",
                          _f(d["sin_uso"]), _lista(d["fallas"], 4)])
        L += _tabla(["Tipología", "n", "Frente × fondo real", "Frente mínimo del motor", "Frente real / mínimo",
                     "Con su frente", "Esquemas reales", "Comparables", "Calidad del motor", "Resuelve",
                     "Calidad en el rectángulo", "Resuelve en el rectángulo", "Sin uso (m²)", "Fallas del motor"], filas)
        L.append("## %s. Por esquema real (%s)" % ("2" if clave == "alta" else "4", titulo))
        L.append("")
        L.append("Posición de las zonas: dónde queda la zona de día y la de noche en el fondo de la vivienda (junto al "
                 "pasillo común, al fondo, de lado a lado o en el medio) y si las dos van lado a lado (una junto a la "
                 "otra a lo ancho) o en fila (una detrás de la otra). Zonas: ancho × fondo de la caja de los dormitorios "
                 "y de la del estar, comedor y cocina.")
        L.append("")
        filas = []
        for e, d in R["por_esquema"].items():
            filas.append([e, d["n"], _lista(d["tipologias"], 5), _fyf(d["frente_real"], d["fondo_real"]),
                          "—" if d["fachadas_n"] is None else "%d" % d["fachadas_n"], _lista(d["rotulos"], 3),
                          "día: %s; noche: %s; %s" % (_lista(d["posicion_dia"], 2), _lista(d["posicion_noche"], 2),
                                                      _lista(d["disposicion"], 2)),
                          _fyf(d["noche_ancho"], d["noche_fondo"]), _fyf(d["dia_ancho"], d["dia_fondo"]),
                          _f(d["frente_sobre_min"], 2), d["comparables"],
                          "—" if d["score"] is None else "%d" % d["score"],
                          "%d de %d" % (d["resuelve"], d["comparables"]) if d["comparables"] else "—",
                          "—" if d["score_rect"] is None else "%d" % d["score_rect"],
                          "%d de %d" % (d["resuelve_rect"], d["comparables"]) if d["comparables"] else "—",
                          _lista(d["esquema_motor"], 2), _lista(d["fallas"], 3)])
        L += _tabla(["Esquema real", "Viviendas", "Tipologías", "Frente × fondo", "Fachadas", "Rótulos",
                     "Posición de las zonas", "Zona de noche (ancho × fondo)", "Zona de día (ancho × fondo)",
                     "Frente real / mínimo", "Comparables", "Calidad del motor", "Resuelve", "Calidad en el rectángulo",
                     "Resuelve en el rectángulo", "Esquema del motor", "Fallas del motor"], filas)
    R = r["alta"]
    L.append("## 5. Estancias: la base contra el motor (precisión alta, viviendas comparables)")
    L.append("")
    L.append("Por grupo: en cuántas viviendas aparece y la superficie mediana por vivienda (la suma de sus locales).")
    L.append("")
    filas = [[g, d["real_viviendas"], _f(d["real_area"]), d["motor_viviendas"], _f(d["motor_area"])]
             for g, d in R["por_grupo"].items()]
    L += _tabla(["Grupo", "Viviendas reales", "Superficie real", "Viviendas del motor", "Superficie del motor"], filas)
    L.append("Locales con fachada propia (tocan un tramo de `Trazo_Fachada`); «abiertos»: sin fachada propia, con la "
             "luz del ambiente abierto (el comedor interior de un estar-comedor-cocina).")
    L.append("")
    filas = [[g, d["real_n"], d["real_con_fachada"], d["real_abiertos"], d["motor_n"], d["motor_con_fachada"]]
             for g, d in R["fachada"].items()]
    L += _tabla(["Grupo", "Locales reales", "Con fachada", "Abiertos", "Locales del motor", "Con fachada"], filas)
    L.append("### 5.1 Frentes de los locales en la fachada (todas las viviendas)")
    L.append("")
    F = r["todas"]["frentes"]
    L.append("Ancho de cada local a lo largo de la fachada que toca (mediana, n y rango, en m; en el marco de la "
             "convención, con la fachada principal arriba), por esquema real: «lado a lado» es el modelo del motor (el "
             "estar y los dormitorios uno al lado del otro en la única fachada). Es la fuente de los frentes típicos de "
             "`standards.py` (`vivienda`, `typ[0]`): el motor pide por local %s (estar: el 95 %% de %s), %s (dormitorio "
             "principal) y %s (secundario), y por vivienda %s m de frente para 1, 2 y 3 dormitorios (`plans.facade_min`)."
             % (_f(F["motor"]["estar"], 2), _f(F["motor"]["typ"]["estar_comedor"][0], 2), _f(F["motor"]["dorm_principal"], 2),
                _f(F["motor"]["dorm_secundario"], 2), " / ".join(_f(F["motor"]["facade_min"][k], 2) for k in ("1", "2", "3"))))
    L.append("")
    filas = []
    for local in FRENTES:
        fila = [local]
        for clave in ("lado a lado", "lado a lado y esquina", "todos"):
            d = F[clave].get(local)
            fila.append("%s (n=%d, %s–%s)" % (_f(d["mediana"], 2), d["n"], _f(d["min"], 2), _f(d["max"], 2)) if d else "—")
        if any(c != "—" for c in fila[1:]):
            filas.append(fila)
    L += _tabla(["Local", "Lado a lado", "Lado a lado y esquina", "Todos los esquemas"], filas)
    L.append("## 6. Los esquemas reales, vivienda por vivienda")
    L.append("")
    L.append("Todo en el marco del motor (la entrada real abajo; si no estaba abajo, el dibujo se giró). Fachadas: lado, "
             "rótulo, largo y los locales con luz que la tocan. Secuencia: los locales desde el pasillo común hacia el "
             "fondo (los que quedan a la misma altura van con «+»; «|» separa las bandas). Zonas: ancho × fondo de la "
             "caja de la zona de noche (dormitorios) y de la de día (estar, comedor, cocina) y dónde quedan.")
    L.append("")
    filas = []
    for v in cat["viviendas"]:
        real = v["real"]
        fach = "; ".join("%s%s %s m: %s" % (f["lado"], " (%s)" % ", ".join(f["rotulos"]) if f["rotulos"] else "",
                                            _f(f["largo"]), ", ".join(f["habitables"]) or "ningún local con luz")
                         for f in real["fachadas"])
        zn, zd = real["zonas"].get("noche"), real["zonas"].get("día")
        filas.append([v["archivo"][2:-4], v["tipologia"], v["precision"], _fyf(real["frente"], real["fondo"]),
                      v["marco"]["lado_entrada"] or "— (nivel superior)", len(real["fachadas"]), fach, real["esquema"],
                      real["secuencia"], _fyf(zn["ancho"], zn["fondo"]) if zn else "—",
                      _fyf(zd["ancho"], zd["fondo"]) if zd else "—", real["orden"]])
    L += _tabla(["Vivienda", "Tip.", "Prec.", "Frente × fondo", "Entrada", "Fachadas", "Fachadas: lado (rótulo) largo: "
                 "locales", "Esquema", "Secuencia desde el pasillo común", "Zona de noche", "Zona de día",
                 "Posición de las zonas"], filas)
    L.append("## 7. Plano por plano: el motor contra la base")
    L.append("")
    L.append("«Esquema motor» es el que resulta del plano del motor con la misma regla que la base; «puerta»: el motor "
             "pudo poner su puerta de entrada donde está la real (acepta `entrada`); si no, la calidad es la de su plano "
             "libre. «Real / mín.»: el frente real sobre el que pide `plans.frente_min` con el fondo real.")
    L.append("")
    filas = []
    for v in cat["viviendas"]:
        m = v["motor"]
        real = v["real"]
        if v["comparable"]:
            rc = m["rectangulo"]
            motor = ["%s" % m["esquema"], "%d" % m["score"], "sí" if m["entrada_aceptada"] else "no",
                     ", ".join(m["fallas"]) or "ninguna", _f(m["sin_uso"]),
                     ", ".join("%s %d" % (g, d["motor_n"]) for g, d in v["comparacion"]["por_grupo"].items()
                               if d["motor_n"]), ", ".join(m["habitables_con_fachada"]) or "ninguno",
                     "%d%s" % (rc["score"], "" if rc["rectangular"] else " (%s)" % (", ".join(rc["fallas"]) or "ninguna"))]
        else:
            motor = ["—", "—", "—", v["motivo"] or "—", "—", "—", "—", "—"]
        filas.append([v["archivo"][2:-4], v["tipologia"], v["precision"], _fyf(real["frente"], real["fondo"]),
                      real["esquema"],
                      ", ".join("%s %d" % (g, n) for g, n in _cuenta(e["grupo"] for e in real["estancias"]).items()),
                      ", ".join(real["habitables_con_fachada"]) or "ninguno",
                      _f(m["frente_min_convencion"]), _f(v["frente_sobre_min"], 2)] + motor)
    L += _tabla(["Vivienda", "Tip.", "Prec.", "Frente × fondo", "Esquema real", "Estancias reales",
                 "Con fachada (real)", "Frente mín. motor", "Real / mín.", "Esquema motor", "Calidad", "Puerta",
                 "Fallas", "Sin uso", "Estancias del motor", "Con fachada (motor)",
                 "Calidad en el rectángulo (fallas)"], filas)
    L.append("## 8. Avisos del motor, vivienda por vivienda (precisión alta)")
    L.append("")
    for v in cat["viviendas"]:
        if not v["comparable"] or v["precision"] != "alta":
            continue
        m = v["motor"]
        L.append("- **%s** (%s, %s; el motor: %s): calidad %d%s. %s" % (
            v["archivo"][2:-4], v["tipologia"], v["real"]["esquema"], m["secuencia"], m["score"],
            "" if m["score"] == m["score_libre"] else " (libre: %d)" % m["score_libre"],
            " · ".join(m["avisos"]) if m["avisos"] else "sin avisos"))
    L.append("")
    L.append("---")
    L.append("")
    L.append("_Generado por `python tools/comparar_tipologias.py`; no editar a mano._")
    L.append("")
    return "\n".join(L)


def escribir(cat, carpeta=CARPETA):
    """Escribe `comparacion.json` y `COMPARACION.md` (UTF-8, «\\n»). Devuelve las dos rutas."""
    os.makedirs(carpeta, exist_ok=True)
    ruta_json = os.path.join(carpeta, "comparacion.json")
    with open(ruta_json, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(cat, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    ruta_md = os.path.join(carpeta, "COMPARACION.md")
    with open(ruta_md, "w", encoding="utf-8", newline="\n") as f:
        f.write(comparacion_md(cat))
    return ruta_json, ruta_md


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if len(argv) > 1 and argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 2
    solo_alta = "--solo-alta" in argv
    args = [a for a in argv[1:] if not a.startswith("--")]
    carpeta = args[0] if args else CARPETA
    if not os.path.isdir(carpeta):
        print("No existe la carpeta %s. Uso: python tools/comparar_tipologias.py [carpeta] [--solo-alta]" % carpeta)
        return 2
    cat = comparar_base(carpeta, solo_alta)
    if not cat["archivos"]:
        print("No hay ninguna vivienda (U_….dxf) en %s." % carpeta)
        return 2
    ruta_json, ruta_md = escribir(cat, carpeta)
    R = cat["resumen"]["todas"]
    print("Comparé %d viviendas de %s (%d comparables): calidad mediana del motor %s, resuelve %d, con su frente %d."
          % (cat["archivos"], carpeta, R["comparables"], R["score"], R["resuelve"], R["entran_con_su_frente"]))
    for a in cat["avisos"]:
        print("Aviso: " + a)
    print("Escribí %s y %s." % (ruta_json, ruta_md))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
