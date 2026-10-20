#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lector de la base de tipologías (R5.16): lee los DXF de `data/tipologias/` y arma el catálogo para calibrar el motor.

Uso:  python -m engine.tipologias [carpeta]      (o  python engine/tipologias.py [carpeta])

Lee cada DXF de la carpeta (convención de `TIPOLOGIAS.md`: `U_…` una vivienda, `P_…` una planta entera) con
`tools/ver_dxf.py` —que `engine/` no importa como paquete, así que se carga por su ruta: `ver_dxf()`—, cuya `leer` y
`controlar` ya asignan las estancias a su vivienda, deciden si tocan la fachada y leen los metadatos de `Trazo_Datos`, y
escribe en la misma carpeta:

- `catalogo.json`: `{version, archivos, avisos, viviendas, plantas, resumen}`. Una entrada por archivo (los niveles de
  una vivienda en varios niveles son archivos aparte con el mismo `vivienda_id`), con las medidas en metros (3
  decimales) y las superficies en m² (2). Orden y formato fijos (UTF-8, `\\n`, claves ordenadas): el mismo archivo en
  Linux y en Windows.
- `RESUMEN.md`: el resumen legible (medianas por tipología, por estancia y por planta, y la comparación con
  `engine/standards.py` y `REFERENCIAS.md`).

Decisiones:
- `Dormir` (la zona de dormir de un monoambiente) es el `kind` propio «sleep»: no es un dormitorio (no cuenta en
  `dormitorios`) y el motor no lo separa: lo dibuja dentro del «Estar-Dormitorio» (`living`). Para comparar con
  `estar_por_dorms`, el resumen suma estar, comedor y, en el monoambiente, la zona de dormir (`zona_estar`).
- `fachada` es «toca un tramo de `Trazo_Fachada`» y `abierto`, «no lo toca pero está en un ambiente abierto (estar,
  comedor, cocina integrada, dormir) que sí»: la misma regla de `controlar`, aplicada también a las estancias que no
  son habitables (que `controlar` no mira).
- Ancho del pasillo (`ancho_pasillo`): para cada `Trazo_Entrada`, la cuerda de la recta perpendicular a la puerta por su
  punto medio dentro del polígono de `Trazo_Pasillo` que la toca; si la puerta mira a lo largo del pasillo (en su punta,
  en un codo o en un anillo) esa cuerda es el largo y no el ancho, y se toma el menor entre ella y el grosor del pasillo
  junto a la puerta (el mayor círculo que cabe con su centro a 1,50 m de ella).
- `circulacion_pct` y `eficiencia` van en %, como `metrics.circulation_pct` y `metrics.efficiency` del motor.
- El catálogo sale byte a byte igual en cualquier versión de Python y de sistema: las sumas son con `math.fsum` (el
  `sum()` de 3.12 suma con compensación y cambia el último decimal de 3.9 a 3.11), sin `math.hypot` (cambió en 3.10) ni
  trigonometría, y los números del catálogo se redondean al escribirlos.
Solo biblioteca estándar.
"""
import csv
import importlib.util
import json
import math
import os
import re
import statistics
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
from engine import dxf_lector as L   # noqa: E402
from engine import geometry as G     # noqa: E402
from engine import standards as ST   # noqa: E402

CARPETA = os.path.join(RAIZ, "data", "tipologias")
TIPOLOGIAS = ("Mono", "1D", "2D", "3D", "4D")
# REFERENCIAS.md, sección 2 («Propuesta para Trazo»): superficie con muros (m²) y frente × fondo (m) en crujía doble
PROPUESTA = {"Mono": 30.0, "1D": 42.0, "2D": 58.0, "3D": 78.0, "4D": 100.0}
PROPUESTA_FRENTE_FONDO = {"Mono": (5.0, 6.0), "1D": (6.0, 7.0), "2D": (8.0, 7.25), "3D": (10.5, 7.4), "4D": (12.5, 8.0)}
# nombre de la etiqueta de la convención -> `kind` de engine/plans.py (los dormitorios, por prefijo); «sleep» es propio
KIND = {"Hall": "hall", "Estar": "living", "Estar-Comedor": "living", "Comedor": "dining", "Cocina": "kitchen",
        "Cocina integrada": "kitchen", "Pasillo": "hallway", "Dormir": "sleep", "Baño": "bath", "Baño 2": "bath",
        "Baño en suite": "bath", "Toilette": "bath", "Lavadero": "laundry", "Depósito": "storage", "Estudio": "study",
        "Vestidor": "vestidor"}
ESTAR = ("living", "dining")          # lo que suma `zona_estar` (más `sleep` en un monoambiente)
ROTULO_TOL = 0.60                     # m: un rótulo de Trazo_Fachada pertenece al tramo que pasa a menos de esto
NUCLEO_JUNTOS = 0.30                  # m: sin rótulos, dos polígonos de Trazo_Nucleos a menos de esto son un núcleo
GROSOR_RADIO = 1.50                   # m: el grosor del pasillo se mide con círculos centrados a esto de la puerta
GROSOR_PASO = 0.10                    # m: grilla de centros de esos círculos
RECTANGULAR = 0.97                    # una estancia es rectangular si llena esta parte de su caja

_NOMBRE_U = re.compile(r"^U_([^_]+)_([^_]+)_(Mono|\dD)_([\d.]+)x([\d.]+)_(\d+)(?:-N(\d+))?\.dxf$", re.I)
_NOMBRE_P = re.compile(r"^P_([^_]+)_(.+)_([^_]+)\.dxf$", re.I)
_NUCLEO = re.compile(r"^N[uú]cleo\b", re.I)
_NUM = re.compile(r"^\s*(-?\d+(?:[.,]\d+)?)")
_TIPO = re.compile(r"^\s*(Mono|\dD)\b")
_PALABRA = re.compile(r"^\s*([A-Za-zÁÉÍÓÚÑáéíóúñ]+)")
_ANIO = re.compile(r"^\s*(\d{4})\b")

_V = None


class ErrorTipologia(Exception):
    """Un DXF que el lector no puede convertir en una entrada del catálogo (el mensaje dice qué falta)."""


def ver_dxf():
    """El módulo `tools/ver_dxf.py` (no es un paquete: se carga por su ruta, una sola vez)."""
    global _V
    if _V is None:
        spec = importlib.util.spec_from_file_location("ver_dxf", os.path.join(RAIZ, "tools", "ver_dxf.py"))
        _V = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_V)
    return _V


# ------------------------------------------------------------------ números y textos
def _r(x, n=3):
    """Redondeo del catálogo (sin «-0.0»)."""
    return None if x is None else round(x, n) + 0.0


def _pts(pts):
    return [[_r(x), _r(y)] for x, y in pts]


def _numero(texto):
    """El número con que empieza un texto de los metadatos («9.24 (caja de todos los niveles)» -> 9.24)."""
    m = _NUM.match(texto or "")
    return float(m.group(1).replace(",", ".")) if m else None


def _palabra(texto):
    m = _PALABRA.match(texto or "")
    return m.group(1).lower() if m else None


def _dist(dx, dy):
    """Longitud de (dx, dy). No usa math.hypot: su redondeo cambió en Python 3.10 y el catálogo tiene que salir igual en
    todas las versiones (lo mismo vale para sum(), que desde 3.12 suma con compensación: aquí se usa math.fsum)."""
    return math.sqrt(dx * dx + dy * dy)


def _dist_seg(p, a, b):
    """Distancia del punto p al segmento ab."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2))
    return _dist(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))


def _dist_contorno(p, poly):
    """Distancia del punto p al contorno del polígono."""
    return min(_dist_seg(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def _largo(pts, cerrada=False):
    n = len(pts) if cerrada else len(pts) - 1
    return math.fsum(_dist(pts[(i + 1) % len(pts)][0] - pts[i][0], pts[(i + 1) % len(pts)][1] - pts[i][1])
                     for i in range(max(n, 0)))


def kind_de(nombre):
    """El `kind` de engine/plans.py de una estancia según su etiqueta (None sin etiqueta, «otro» si no es de la lista)."""
    if nombre is None:
        return None
    return "bedroom" if nombre.startswith("Dormitorio") else KIND.get(nombre, "otro")


def leer_indice(carpeta=CARPETA):
    """`indice.csv` como {archivo: fila} (UTF-8, «;»), o {} si la carpeta no lo tiene."""
    ruta = os.path.join(carpeta, "indice.csv")
    if not os.path.isfile(ruta):
        return {}
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        return {r["archivo"]: r for r in csv.DictReader(f, delimiter=";")}


# ------------------------------------------------------------------ lectura de un DXF
def _cargar(ruta):
    """(ver_dxf, datos, informe de control) de un DXF."""
    V = ver_dxf()
    datos = V.leer(V.texto_del_archivo(ruta))
    return V, datos, V.controlar(datos, os.path.basename(ruta))


def _ficha(meta, fila, partes):
    """ciudad, proyecto, año, fuente y observaciones: la línea del índice (corta y limpia) y, si falta, los metadatos;
    `partes` = (ciudad, proyecto) del nombre del archivo, último recurso."""
    fila = fila or {}
    pick = lambda k: (fila.get(k) or "").strip() or (meta.get(k) or "").strip() or None
    m = _ANIO.match(pick("anio") or "")
    return {"ciudad": pick("ciudad") or partes[0], "proyecto": pick("proyecto") or partes[1],
            "anio": int(m.group(1)) if m else None, "fuente": pick("fuente"),
            "observaciones": pick("observaciones") or ""}


def _luz(V, datos, inf):
    """{id(estancia): (fachada, abierto)} para todas las estancias del archivo: toca un tramo de Trazo_Fachada, o no lo
    toca pero está en un ambiente abierto que sí (la regla de `controlar`, también para las que no son habitables)."""
    fach = V._segmentos(datos["formas"], "fachada")
    ests = inf["estancias"]
    con_luz = V._ambientes_con_luz(ests, fach) if fach else set()
    out = {}
    for i, e in enumerate(ests):
        propia = bool(fach) and V._toca(e["pts"], fach, V.TOL_FACHADA)
        out[id(e)] = (propia, (not propia) and i in con_luz)
    return out


def _estancia(e, luz, completa=True):
    """La estancia del catálogo: nombre, kind, área; con `completa`, también su caja (ancho a lo largo de x, fondo a lo
    largo de y), contorno y luz."""
    out = {"nombre": e["nombre"], "kind": kind_de(e["nombre"]), "area": _r(e["area"], 2)}
    if completa:
        x0, y0, x1, y1 = G.bbox(e["pts"])
        propia, abierto = luz[id(e)]
        out.update({"ancho": _r(x1 - x0), "fondo": _r(y1 - y0), "rect": [_r(x0), _r(y0), _r(x1), _r(y1)],
                    "rectangular": e["area"] >= RECTANGULAR * (x1 - x0) * (y1 - y0), "pts": _pts(e["pts"]),
                    "fachada": propia, "abierto": abierto})
    return out


def _entrada_en(V, datos, contorno):
    """{medio, ancho, lado} de la Trazo_Entrada cuyo medio cae sobre el contorno (a menos de V.TOL_BORDE), o None.
    `lado` es el borde de la caja del contorno más cercano a la puerta (abajo, arriba, izquierda, derecha)."""
    mejor = None
    for f in datos["formas"]:
        if f["rol"] != "entrada" or f["punto"] or len(f["pts"]) < 2:
            continue
        a, b = f["pts"][0], f["pts"][-1]
        m = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
        d = _dist_contorno(m, contorno)
        if d <= V.TOL_BORDE and (mejor is None or d < mejor[0]):
            mejor = (d, m, _dist(b[0] - a[0], b[1] - a[1]))
    if mejor is None:
        return None
    _, m, ancho = mejor
    x0, y0, x1, y1 = G.bbox(contorno)
    lados = (("abajo", m[1] - y0), ("arriba", y1 - m[1]), ("izquierda", m[0] - x0), ("derecha", x1 - m[0]))
    return {"medio": [_r(m[0]), _r(m[1])], "ancho": _r(ancho), "lado": min(lados, key=lambda t: t[1])[0]}


def _fachadas(V, datos):
    """[{largo, rotulo}]: los tramos de Trazo_Fachada con el rótulo (Calle, Contrafrente, Patio) que pasa a menos de
    ROTULO_TOL de ellos (None: las fachadas laterales, sin rótulo)."""
    textos = [t for t in datos["textos"] if t["rol"] == "fachada"]
    out = []
    for f in datos["formas"]:
        if f["rol"] != "fachada" or f["punto"] or len(f["pts"]) < 2:
            continue
        segs = V._segmentos([f], "fachada")
        rotulo, mejor = None, ROTULO_TOL
        for t in textos:
            d = min(_dist_seg(t["p"], a, b) for a, b in segs)
            if d <= mejor:
                rotulo, mejor = t["texto"], d
        out.append({"largo": _r(_largo(f["pts"], f["cerrada"])), "rotulo": rotulo})
    return out


def _nombre_u(nombre):
    """{ciudad, proyecto, num} del nombre de un archivo `U_<ciudad>_<proyecto>_<tipologia>_<frente>x<fondo>_<nn>[-N<n>].dxf`
    (None si el nombre no sigue la convención)."""
    m = _NOMBRE_U.match(nombre)
    return {"ciudad": m.group(1), "proyecto": m.group(2), "num": int(m.group(6))} if m else None


def vivienda_de(ruta, indice=None):
    """La vivienda de un DXF de una unidad (`U_…` o suelto, como `tests/dxf/tipologia_2d.dxf`): ver el catálogo en
    `leer_base`. `indice`: la fila de `indice.csv` de este archivo, si hay."""
    V, datos, inf = _cargar(ruta)
    return _vivienda(ruta, V, datos, inf, indice)


leer_vivienda = vivienda_de


def _vivienda(ruta, V, datos, inf, fila):
    nombre = os.path.basename(ruta)
    meta = inf["datos"]
    if len(inf["unidades"]) != 1:
        raise ErrorTipologia("hay %d viviendas cerradas en Trazo_Unidad y un archivo de unidad lleva una sola"
                             % len(inf["unidades"]))
    u = inf["unidades"][0]
    luz = _luz(V, datos, inf)
    ests = [_estancia(e, luz) for e in u["estancias"]]
    dorms_dibujados = sum(1 for e in ests if e["kind"] == "bedroom")
    m = _TIPO.match(meta.get("tipologia", "")) or _TIPO.match(u["etiqueta"] or "")
    tipologia = m.group(1) if m else ("Mono" if dorms_dibujados == 0 else "%dD" % dorms_dibujados)
    dorms = _numero(meta.get("dormitorios"))
    if dorms is None:
        dorms = 0 if tipologia == "Mono" else int(tipologia[0])
    x0, y0, x1, y1 = G.bbox(u["pts"])
    frente, fondo = _numero(meta.get("frente")), _numero(meta.get("fondo"))
    nu = _nombre_u(nombre)
    partes = (nu["ciudad"], nu["proyecto"]) if nu else (None, None)
    if nu:
        vid = "%s_%02d" % (nu["proyecto"], nu["num"])
    else:
        vid = re.sub(r"-N\d+$", "", os.path.splitext(nombre)[0])
    ficha = _ficha(meta, fila, partes)
    ventanas = [f for f in datos["formas"] if f["rol"] == "ventanas" and not f["punto"] and len(f["pts"]) >= 2]
    out = {"archivo": nombre, "vivienda_id": vid, "nivel": inf["nivel"], "tipologia": tipologia, "dormitorios": int(dorms),
           "crujia": _palabra(meta.get("crujia")) or _palabra((fila or {}).get("crujia")),
           "precision": _palabra(meta.get("precision")) or _palabra((fila or {}).get("precision")),
           "frente": _r(frente if frente is not None else x1 - x0), "fondo": _r(fondo if fondo is not None else y1 - y0),
           "area_muros": _r(u["area"], 2), "superficie_util": _r(math.fsum(e["area"] for e in u["estancias"]), 2),
           "contorno": _pts(u["pts"]), "entrada": _entrada_en(V, datos, u["pts"]), "estancias": ests,
           "puertas": inf["puertas"], "ventanas": {"n": len(ventanas), "largo": _r(math.fsum(_largo(f["pts"]) for f in ventanas))},
           "fachadas": _fachadas(V, datos),
           "medianeras": _r(math.fsum(_largo(f["pts"], f["cerrada"]) for f in datos["formas"]
                                if f["rol"] == "medianeras" and not f["punto"] and len(f["pts"]) >= 2)),
           "exteriores": [{"nombre": r["nombre"], "area": _r(r["area"], 2)} for r in inf["recintos"]],
           "norte": _r(inf["norte"], 1) if inf["norte"] is not None else None}
    out.update(ficha)
    return out


# ------------------------------------------------------------------ plantas
def _poligonos(datos, rol):
    return [f["pts"] for f in datos["formas"] if f["rol"] == rol and f["cerrada"] and not f["punto"] and len(f["pts"]) >= 3]


def _dist_poligonos(a, b):
    """Distancia mínima entre los contornos de dos polígonos."""
    return min(_dist_contorno(p, q) for p, q in [(p, b) for p in a] + [(p, a) for p in b])


def _nucleos(datos, polis):
    """Los núcleos de la planta: un núcleo que el palier parte va en dos polígonos y se rotula una sola vez (y a veces el
    rótulo queda fuera), así que cada polígono va al rótulo «Nucleo n» más cercano; sin rótulos, los polígonos a menos de
    NUCLEO_JUNTOS son un núcleo. [{nombre, area (de todas sus partes), ancho, fondo (caja), partes, pts (la mayor parte)}]"""
    if not polis:
        return []
    rotulos = [t for t in datos["textos"] if t["rol"] == "nucleos" and _NUCLEO.match(t["texto"])]
    if rotulos:
        grupos = {}
        for p in polis:
            k = min(range(len(rotulos)), key=lambda i: 0.0 if G.point_in_poly(rotulos[i]["p"], p)
                    else _dist_contorno(rotulos[i]["p"], p))
            grupos.setdefault(k, []).append(p)
        orden = [(rotulos[k]["texto"], ps) for k, ps in sorted(grupos.items())]
    else:
        padre = list(range(len(polis)))

        def raiz(i):
            while padre[i] != i:
                i = padre[i]
            return i
        for i in range(len(polis)):
            for j in range(i + 1, len(polis)):
                if _dist_poligonos(polis[i], polis[j]) <= NUCLEO_JUNTOS:
                    padre[raiz(j)] = raiz(i)
        grupos = {}
        for i, p in enumerate(polis):
            grupos.setdefault(raiz(i), []).append(p)
        orden = [("Nucleo %d" % (k + 1), ps) for k, ps in enumerate(grupos[r] for r in sorted(grupos))]
    out = []
    for nombre, ps in orden:
        todos = [q for p in ps for q in p]
        x0, y0, x1, y1 = G.bbox(todos)
        mayor = max(ps, key=lambda p: abs(G.area(p)))
        out.append({"nombre": nombre, "area": _r(math.fsum(abs(G.area(p)) for p in ps), 2), "ancho": _r(x1 - x0),
                    "fondo": _r(y1 - y0), "partes": len(ps), "pts": _pts(mayor)})
    return out


def _cuerda(poly, p, d, tol):
    """La cuerda (s0, s1) de la recta p + s·d (d unitaria) dentro del polígono que contiene s = 0 (o pasa a menos de tol);
    la más larga si hay varias, o None. Cruces de la recta con los lados, sin trigonometría (el mismo resultado en todas
    las plataformas)."""
    nx, ny = -d[1], d[0]
    ts = []
    for i in range(len(poly)):
        ax, ay = poly[i][0] - p[0], poly[i][1] - p[1]
        bx, by = poly[(i + 1) % len(poly)][0] - p[0], poly[(i + 1) % len(poly)][1] - p[1]
        ha, hb = ax * nx + ay * ny, bx * nx + by * ny
        if (ha > 0) != (hb > 0):
            ta, tb = ax * d[0] + ay * d[1], bx * d[0] + by * d[1]
            ts.append(ta + (0.0 - ha) * (tb - ta) / (hb - ha))
    ts.sort()
    mejor = None
    for k in range(0, len(ts) - 1, 2):
        lo, hi = ts[k], ts[k + 1]
        dist = 0.0 if lo <= 0.0 <= hi else min(abs(lo), abs(hi))
        if dist <= tol and (mejor is None or hi - lo > mejor[1] - mejor[0]):
            mejor = (lo, hi)
    return mejor


def _grosor(poly, centro, radio, paso):
    """Diámetro del mayor círculo que cabe en el polígono con su centro a `radio` m o menos de `centro`: una grilla de
    `paso` m y, desde el mejor centro, tres afinados de 5 × 5 puntos con pasos cada vez más chicos."""
    k = int(radio / paso)
    mejor, q0 = -1.0, centro
    for i in range(-k, k + 1):
        for j in range(-k, k + 1):
            q = (centro[0] + i * paso, centro[1] + j * paso)
            if i * i + j * j <= k * k and G.point_in_poly(q, poly):
                d = _dist_contorno(q, poly)
                if d > mejor:
                    mejor, q0 = d, q
    if mejor < 0:
        return 0.0
    for fino in (paso / 2.0, paso / 10.0, paso / 50.0):
        base = q0
        for i in range(-2, 3):
            for j in range(-2, 3):
                q = (base[0] + i * fino, base[1] + j * fino)
                if G.point_in_poly(q, poly):
                    d = _dist_contorno(q, poly)
                    if d > mejor:
                        mejor, q0 = d, q
    return 2.0 * mejor


def ancho_pasillo_en(pasillos, medio, direccion, tol=0.30, radio=GROSOR_RADIO, paso=GROSOR_PASO):
    """Ancho del pasillo frente a una puerta de entrada (R5.16). `medio` y `direccion` (unitaria, a lo largo de la hoja)
    son los de la puerta; `pasillos`, los polígonos de Trazo_Pasillo. La cuerda de la recta perpendicular a la puerta por
    su punto medio dentro del polígono que la toca (a menos de `tol` del muro) es el ancho cuando la puerta da de costado
    a un pasillo recto; si da a lo largo (en su punta, en un codo, en un anillo) la cuerda es el largo del tramo, así que
    se toma el menor entre ella y el grosor del pasillo junto a la puerta (`_grosor`: el mayor círculo que cabe con su
    centro a `radio` m de ella). None si ningún pasillo toca la puerta."""
    n = (-direccion[1], direccion[0])
    mejor = None
    for P in pasillos:
        c = _cuerda(P, medio, n, tol)
        if c and (mejor is None or c[1] - c[0] > mejor[0][1] - mejor[0][0]):
            mejor = (c, P)
    if mejor is None:
        return None
    (lo, hi), P = mejor
    return min(hi - lo, _grosor(P, medio, radio, paso))


def _estad(vals, n=2):
    """{min, mediana, max} de los valores (None si no hay)."""
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    return {"min": _r(min(vals), n), "mediana": _r(statistics.median(vals), n), "max": _r(max(vals), n)}


def planta_de(ruta, indice=None):
    """La planta de un DXF de planta entera (`P_…`): ver el catálogo en `leer_base`."""
    V, datos, inf = _cargar(ruta)
    return _planta(ruta, V, datos, inf, indice)


def _planta(ruta, V, datos, inf, fila):
    nombre = os.path.basename(ruta)
    meta = inf["datos"]
    terrenos = _poligonos(datos, "terreno")
    if not terrenos:
        raise ErrorTipologia("no hay ninguna figura cerrada en Trazo_Terreno")
    terreno = max(terrenos, key=lambda p: abs(G.area(p)))
    patios = _poligonos(datos, "patios")
    partes, _ = G.subtract(terreno, patios)
    planta = math.fsum(abs(G.area(o)) - math.fsum(abs(G.area(h)) for h in hs) for o, hs in partes)
    pasillos = _poligonos(datos, "pasillo")
    polis_nucleos = _poligonos(datos, "nucleos")
    nucleos = _nucleos(datos, polis_nucleos)
    viviendas = []
    for u in inf["unidades"]:
        ests = [_estancia(e, None, completa=False) for e in u["estancias"]]
        tipologia = u["tipologia"]
        if tipologia is not None:
            dorms = 0 if tipologia == "Mono" else int(tipologia[0])
        else:
            dorms = sum(1 for e in ests if e["kind"] == "bedroom")
        x0, y0, x1, y1 = G.bbox(u["pts"])
        viviendas.append({"etiqueta": u["etiqueta"], "tipologia": tipologia, "dormitorios": dorms,
                          "area": _r(u["area"], 2), "frente": _r(x1 - x0), "fondo": _r(y1 - y0), "pts": _pts(u["pts"]),
                          "entrada": _entrada_en(V, datos, u["pts"]), "estancias": ests})
    anchos = []
    for f in datos["formas"]:
        if f["rol"] != "entrada" or f["punto"] or len(f["pts"]) < 2:
            continue
        a, b = f["pts"][0], f["pts"][-1]
        largo = _dist(b[0] - a[0], b[1] - a[1])
        if largo < 1e-6:
            continue
        w = ancho_pasillo_en(pasillos, ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0), ((b[0] - a[0]) / largo, (b[1] - a[1]) / largo))
        if w is not None:
            anchos.append(w)
    area_viv = math.fsum(u["area"] for u in inf["unidades"])
    area_pas = math.fsum(abs(G.area(p)) for p in pasillos)
    area_nuc = math.fsum(abs(G.area(p)) for p in polis_nucleos)
    ancho = None
    if anchos:
        ancho = _estad(anchos, 3)
        ancho.update({"n": len(anchos), "valores": sorted(_r(a) for a in anchos)})
    mediana = statistics.median(anchos) if anchos else None
    metricas = {"con_palier": bool(pasillos), "viviendas": len(viviendas), "nucleos": len(nucleos),
                "viviendas_por_nucleo": _r(len(viviendas) / float(len(nucleos)), 2) if nucleos else None,
                "area_viviendas": _r(area_viv, 2), "area_pasillos": _r(area_pas, 2), "area_nucleos": _r(area_nuc, 2),
                "circulacion_pct": _r((area_pas + area_nuc) / planta * 100.0, 1) if planta > 0 else None,
                "eficiencia": _r(area_viv / planta * 100.0, 1) if planta > 0 else None,
                "ancho_pasillo": ancho,
                "largo_pasillo_por_vivienda": _r(area_pas / mediana / len(viviendas), 2) if mediana and viviendas else None}
    otros = []
    for r in inf["recintos"]:
        dentro = G.point_in_poly(r["c"], terreno) and not any(G.point_in_poly(r["c"], p) for p in patios)
        otros.append({"nombre": r["nombre"], "area": _r(r["area"], 2), "dentro": bool(dentro)})
    m = _NOMBRE_P.match(nombre)
    ficha = _ficha(meta, fila, (m.group(1), m.group(2)) if m else (None, None))
    out = {"archivo": nombre, "nivel": m.group(3) if m else None,
           "crujia": _palabra(meta.get("crujia")) or _palabra((fila or {}).get("crujia")),
           "precision": _palabra(meta.get("precision")) or _palabra((fila or {}).get("precision")),
           "terreno": {"area": _r(abs(G.area(terreno)), 2), "pts": _pts(terreno)},
           "patios": [{"area": _r(abs(G.area(p)), 2), "pts": _pts(p)} for p in patios], "planta": _r(planta, 2),
           "pasillos": [{"area": _r(abs(G.area(p)), 2), "pts": _pts(p)} for p in pasillos], "nucleos": nucleos,
           "viviendas": viviendas, "otros": otros, "norte": _r(inf["norte"], 1) if inf["norte"] is not None else None,
           "metricas": metricas}
    out.update(ficha)
    return out


# ------------------------------------------------------------------ la base
def version():
    from engine import layout
    return layout.VERSION


def leer_base(carpeta=CARPETA):
    """Lee todos los DXF de la carpeta (por defecto `data/tipologias/` del repositorio) y arma el catálogo:
    {version, archivos (cuántos DXF), avisos [texto], viviendas, plantas, resumen}. Una vivienda por archivo `U_…`, una
    planta por archivo `P_…` (otro nombre: según el contenido); un archivo que no se puede leer se avisa y se salta."""
    carpeta = os.fspath(carpeta)
    indice = leer_indice(carpeta)
    archivos = sorted(f for f in os.listdir(carpeta) if f.lower().endswith(".dxf"))
    viviendas, plantas, avisos = [], [], []
    for nombre in archivos:
        ruta = os.path.join(carpeta, nombre)
        try:
            V, datos, inf = _cargar(ruta)
            for e in inf["errores"]:
                avisos.append("%s: %s" % (nombre, e))
            prefijo = nombre[:2].upper()
            planta = prefijo == "P_" or (prefijo != "U_" and inf["tipo"] == "planta")
            if planta:
                plantas.append(_planta(ruta, V, datos, inf, indice.get(nombre)))
            else:
                viviendas.append(_vivienda(ruta, V, datos, inf, indice.get(nombre)))
        except (L.ErrorDxf, ErrorTipologia) as e:
            avisos.append("%s: %s" % (nombre, e))
    catalogo = {"version": version(), "archivos": len(archivos), "avisos": avisos, "viviendas": viviendas,
                "plantas": plantas}
    catalogo["resumen"] = resumen(viviendas, plantas)
    return catalogo


# ------------------------------------------------------------------ resumen
def _unidades(viviendas):
    """Una entrada por vivienda: los niveles de una vivienda en varios niveles (mismo `vivienda_id`) cuentan una vez,
    con la suma de sus superficies; el frente, el fondo, la tipología y la precisión son los del primer nivel."""
    grupos = {}
    for v in viviendas:
        grupos.setdefault(v["vivienda_id"], []).append(v)
    out = []
    for vid in sorted(grupos):
        niv = sorted(grupos[vid], key=lambda v: (v["nivel"] or 0, v["archivo"]))
        p = niv[0]
        ests = [e for v in niv for e in v["estancias"]]
        zona = math.fsum(e["area"] for e in ests if e["kind"] in ESTAR or (e["kind"] == "sleep" and p["tipologia"] == "Mono"))
        out.append({"id": vid, "tipologia": p["tipologia"], "dormitorios": p["dormitorios"], "precision": p["precision"],
                    "niveles": len(niv), "area_muros": math.fsum(v["area_muros"] for v in niv),
                    "superficie_util": math.fsum(v["superficie_util"] for v in niv), "frente": p["frente"], "fondo": p["fondo"],
                    "zona_estar": zona, "estancias": ests})
    return out


def _mediana(vals, n=3):
    vals = [v for v in vals if v is not None]
    return _r(statistics.median(vals), n) if vals else None


def _por_estancia(ests):
    """{nombre: {n, area {min, mediana, max}, ancho {mediana}, fondo {mediana}}}: el ancho y el fondo (la caja) de las
    estancias rectangulares, o de todas si ninguna lo es."""
    por = {}
    for e in ests:
        if e["nombre"]:
            por.setdefault(e["nombre"], []).append(e)
    out = {}
    for nombre in sorted(por):
        es = por[nombre]
        rect = [e for e in es if e["rectangular"]] or es
        out[nombre] = {"n": len(es), "area": _estad([e["area"] for e in es], 2),
                       "ancho": {"mediana": _mediana([e["ancho"] for e in rect])},
                       "fondo": {"mediana": _mediana([e["fondo"] for e in rect])}}
    return out


def resumen(viviendas, plantas):
    """El resumen del catálogo: por tipología (viviendas y estancias), plantas y comparación con engine/standards.py."""
    unidades = _unidades(viviendas)
    claves = list(TIPOLOGIAS) + sorted({u["tipologia"] for u in unidades} - set(TIPOLOGIAS))
    por = {}
    for t in claves:
        us = [u for u in unidades if u["tipologia"] == t]
        if not us:
            por[t] = {"n": 0}
            continue
        prec = {}
        for u in us:
            prec[u["precision"] or "sin dato"] = prec.get(u["precision"] or "sin dato", 0) + 1
        por[t] = {"n": len(us), "area_muros": _estad([u["area_muros"] for u in us], 2),
                  "superficie_util": _estad([u["superficie_util"] for u in us], 2),
                  "frente": _estad([u["frente"] for u in us], 3), "fondo": _estad([u["fondo"] for u in us], 3),
                  "zona_estar": _estad([u["zona_estar"] for u in us], 2),
                  "estancias": _por_estancia([e for u in us for e in u["estancias"]]), "precision": prec}
    con = [p for p in plantas if p["metricas"]["con_palier"]]
    anchos = [a for p in con for a in ((p["metricas"]["ancho_pasillo"] or {}).get("valores") or [])]
    nucs = [n for p in plantas for n in p["nucleos"]]
    ancho_pas = _estad(anchos, 3)
    if ancho_pas:
        ancho_pas["n"] = len(anchos)
    pl = {"n": len(plantas), "con_palier": len(con), "ancho_pasillo": ancho_pas,
          "viviendas_por_nucleo": _estad([p["metricas"]["viviendas_por_nucleo"] for p in con], 2),
          "circulacion_pct": _estad([p["metricas"]["circulacion_pct"] for p in con], 1),
          "eficiencia": _estad([p["metricas"]["eficiencia"] for p in con], 1),
          "nucleo": {"n": len(nucs), "ancho": _mediana([n["ancho"] for n in nucs]),
                     "fondo": _mediana([n["fondo"] for n in nucs]), "area": _mediana([n["area"] for n in nucs], 2),
                     "lado_mayor": _mediana([max(n["ancho"], n["fondo"]) for n in nucs]),
                     "lado_menor": _mediana([min(n["ancho"], n["fondo"]) for n in nucs])}}
    return {"viviendas": {"n": len(unidades), "archivos": len(viviendas)}, "por_tipologia": por, "plantas": pl,
            "comparacion": _comparacion(unidades, por, pl)}


# estancia de la convención -> estancia de standards.py (vivienda.<clave>)
ESTANDAR = (("Dormitorio 1", "dorm_principal"), ("Dormitorio 2", "dorm_secundario"), ("Dormitorio 3", "dorm_secundario"),
            ("Cocina", "cocina"), ("Cocina integrada", "cocina_integrada"), ("Baño", "bano"), ("Baño en suite", "bano"),
            ("Toilette", "bano_aux"), ("Lavadero", "lavadero"), ("Hall", "hall"), ("Estudio", "estudio"),
            ("Vestidor", "vestidor"), ("Depósito", "deposito"))


def _tipico(clave):
    """Lo que standards.py dice de una estancia: área típica (la de `typ_area` o frente × fondo de `typ`), `typ`
    [frente, fondo], mínimo y tope (`max_area`) en m²."""
    s = ST.DEFAULTS["vivienda"][clave]
    typ = s.get("typ")
    area = s.get("typ_area", _r(typ[0] * typ[1], 2) if typ else None)
    return {"clave": "vivienda." + clave, "tipico_area": area, "tipico": list(typ) if typ else None,
            "minimo_area": s.get("min_area"), "tope_area": s.get("max_area")}


def _nucleo_motor(giro):
    """El núcleo que arma el motor con un ascensor (giro 0: la escalera sube perpendicular al pasillo; giro 90: a lo largo),
    con los parámetros por defecto de `engine/layout.py`: la caja de `standards.core_size` (de `circulation._add_core`:
    incluye el tramo de pasillo, de -cw/2 a d) partida en sus piezas con `programs.core_parts`. `*_sin_palier` suma las
    piezas que no son el palier de los ascensores (escalera, ascensor, ducto y el depósito o la sala de máquinas que
    sobran): lo que la base rotula en `Trazo_Nucleos`; `*_con_palier` es la caja de `core_size` sin el tramo de pasillo."""
    from engine import layout
    from engine import programs as PR
    N, h, cw = ST.DEFAULTS["nucleo"], layout.DEFAULT_PARAMS["floor_height"], layout.DEFAULT_PARAMS["corridor_width"]
    w, d = ST.core_size(N, h, 1, cw, giro=giro)
    partes = PR.core_parts((0.0, -cw / 2.0, w, -cw / 2.0 + d), 1, cw, N, h, 1, giro)
    sin = [q for q in partes if q["kind"] != "landing"]
    x0, y0, x1, y1 = G.bbox([c for q in sin for c in q["poly"]])
    return {"area_sin_palier": _r(math.fsum(abs(G.area(q["poly"])) for q in sin), 2),
            "caja_sin_palier": [_r(x1 - x0), _r(y1 - y0)],
            "area_con_palier": _r(w * (d - cw), 2), "caja_con_palier": [_r(w), _r(d - cw)]}


def _comparacion(unidades, por, pl):
    """La medida de la base junto a engine/standards.py, engine/layout.py (parámetros por defecto) y REFERENCIAS.md."""
    from engine import layout
    V = ST.DEFAULTS["vivienda"]
    mix = {m.get("dorms"): m.get("area") for m in layout.DEFAULT_PARAMS["unit_mix"]}
    viv = []
    for i, t in enumerate(TIPOLOGIAS):
        p = por.get(t) or {"n": 0}
        fila = {"tipologia": t, "n": p["n"], "medida": p["area_muros"]["mediana"] if p["n"] else None,
                "superficie_min": V["superficie_min"][i], "rango_anv": list(V["rango_vivienda"][i]),
                "referencias": PROPUESTA[t], "mix_motor": mix.get(i),
                "frente": p["frente"]["mediana"] if p["n"] else None, "fondo": p["fondo"]["mediana"] if p["n"] else None,
                "referencias_frente_fondo": list(PROPUESTA_FRENTE_FONDO[t])}
        viv.append(fila)
    todas = _por_estancia([e for u in unidades for e in u["estancias"]])
    est = []
    for nombre, clave in ESTANDAR:
        d = todas.get(nombre)
        fila = {"estancia": nombre, "n": d["n"] if d else 0, "area": d["area"]["mediana"] if d else None,
                "ancho": d["ancho"]["mediana"] if d else None, "fondo": d["fondo"]["mediana"] if d else None}
        fila.update(_tipico(clave))
        est.append(fila)
    zona = []
    for i, t in enumerate(TIPOLOGIAS):
        p = por.get(t) or {"n": 0}
        zona.append({"tipologia": t, "n": p["n"], "medida": p["zona_estar"]["mediana"] if p["n"] else None,
                     "estar_por_dorms": V["estar_por_dorms"][i], "tipico_area": V["estar_comedor"]["typ_area"]})
    N = ST.DEFAULTS["nucleo"]
    nuc = pl["nucleo"]
    frentes = [u["frente"] for u in unidades]
    fondos = [u["fondo"] for u in unidades]
    minimo = layout.DEFAULT_PARAMS["min_unit_width"]
    plantas = {"ancho_pasillo": {"motor": layout.DEFAULT_PARAMS["corridor_width"], "norma": list(N["pasillo_comun"]),
                                 "medida": pl["ancho_pasillo"]},
               "nucleo": {"motor": {"ascensores": 1, "giro_0": _nucleo_motor(0), "giro_90": _nucleo_motor(90)},
                          "medida": {"area": nuc["area"], "lado_mayor": nuc["lado_mayor"], "lado_menor": nuc["lado_menor"]}},
               "frente_minimo": {"clave": "min_unit_width", "motor": minimo, "medida": _r(min(frentes)) if frentes else None,
                                 "bajo_el_minimo": sum(1 for f in frentes if f < minimo), "viviendas": len(frentes)},
               "fondo_maximo": {"clave": "max_unit_depth", "motor": layout.DEFAULT_PARAMS["max_unit_depth"],
                                "medida": _r(max(fondos)) if fondos else None}}
    return {"viviendas": viv, "estancias": est, "zona_estar": zona, "plantas": plantas}


# ------------------------------------------------------------------ RESUMEN.md
ORDEN_ESTANCIAS = ("Hall", "Estar", "Comedor", "Estar-Comedor", "Cocina", "Cocina integrada", "Pasillo", "Dormitorio 1",
                   "Dormitorio 2", "Dormitorio 3", "Dormitorio 4", "Dormir", "Baño", "Baño 2", "Baño en suite", "Toilette",
                   "Lavadero", "Depósito", "Estudio", "Vestidor")


def _f(x, dec=1):
    """Número con coma decimal («—» si falta)."""
    return "—" if x is None else ("%.*f" % (dec, x)).replace(".", ",")


def _g(x):
    """Un número redondo sin ceros de más (5; 7,25), para las propuestas y los típicos."""
    return "—" if x is None else ("%g" % x).replace(".", ",")


def _rango(d, dec=1):
    """«mediana (mín–máx)», o solo la mediana si los tres son iguales."""
    if not d:
        return "—"
    if _f(d["min"], dec) == _f(d["mediana"], dec) == _f(d["max"], dec):
        return _f(d["mediana"], dec)
    return "%s (%s–%s)" % (_f(d["mediana"], dec), _f(d["min"], dec), _f(d["max"], dec))


def _dif(medida, ref):
    """Diferencia de la medida con la referencia, en % de la referencia («+12 %»)."""
    if medida is None or not ref:
        return "—"
    x = (medida - ref) / float(ref) * 100.0
    return "0 %" if abs(x) < 0.5 else "%+.0f %%" % x


def _tabla(cabecera, filas):
    cel = lambda c: str(c).replace("|", "\\|")
    return (["| " + " | ".join(cabecera) + " |", "|" + "|".join("---" for _ in cabecera) + "|"] +
            ["| " + " | ".join(cel(c) for c in f) + " |" for f in filas] + [""])


def _caja(d, dec=1):
    return "%s × %s" % (_f(d["ancho"], dec), _f(d["fondo"], dec)) if d and d.get("ancho") is not None else "—"


def resumen_md(cat):
    """El RESUMEN.md del catálogo (texto con «\\n», en español)."""
    res = cat["resumen"]
    por, pl, cmp_ = res["por_tipologia"], res["plantas"], res["comparacion"]
    L_ = ["# Base de tipologías — resumen (Trazo v%s)" % cat["version"], "",
          "Se leyeron %d archivos de `data/tipologias/`: %d viviendas (%d distintas: las de varios niveles cuentan una vez, "
          "con la suma de sus niveles) y %d plantas enteras. Las superficies son m² con muros (el contorno de la vivienda "
          "por el eje de los muros divisorios y la cara exterior de la fachada) y las medidas, metros; cada celda con "
          "rango da la mediana y, entre paréntesis, el mínimo y el máximo. El ancho y el fondo de una estancia son los de "
          "su caja alineada con los ejes del dibujo (ancho a lo largo de la fachada), de las estancias rectangulares." % (
              cat["archivos"], res["viviendas"]["archivos"], res["viviendas"]["n"], pl["n"]), ""]
    if cat["avisos"]:
        L_ += ["Avisos de la lectura: " + "; ".join(cat["avisos"]) + ".", ""]
    # 1. viviendas
    L_ += ["## 1. Viviendas por tipología", ""]
    filas = []
    for t in por:
        d = por[t]
        if not d["n"]:
            filas.append([t, 0, "—", "—", "—", "—", "—"])
            continue
        filas.append([t, d["n"], _rango(d["area_muros"]), _f(d["superficie_util"]["mediana"]), _f(d["frente"]["mediana"]),
                      _f(d["fondo"]["mediana"]), ", ".join("%s %d" % (k, v) for k, v in sorted(d["precision"].items()))])
    L_ += _tabla(["Tipología", "n", "Superficie con muros (m²)", "Superficie útil mediana (m²)", "Frente mediano (m)",
                  "Fondo mediano (m)", "Precisión"], filas)
    # 2. estancias
    L_ += ["## 2. Estancias por tipología", "",
           "Cada celda: superficie mediana en m² (ancho × fondo medianos en m) y cantidad de estancias medidas (n). "
           "Con pocas, la mediana es casi un dato suelto.", ""]
    nombres = {n for d in por.values() if d["n"] for n in d["estancias"]}
    orden = [n for n in ORDEN_ESTANCIAS if n in nombres] + sorted(nombres - set(ORDEN_ESTANCIAS))
    filas = []
    for n in orden:
        fila = [n]
        for t in TIPOLOGIAS:
            e = (por.get(t) or {}).get("estancias", {}).get(n)
            fila.append("%s (%s) n=%d" % (_f(e["area"]["mediana"]), _caja({"ancho": e["ancho"]["mediana"], "fondo": e["fondo"]["mediana"]}),
                                          e["n"]) if e else "—")
        filas.append(fila)
    L_ += _tabla(["Estancia"] + list(TIPOLOGIAS), filas)
    # 3. plantas
    L_ += ["## 3. Plantas", "",
           "Circulación = (pasillos + núcleos) / planta; eficiencia = viviendas / planta, con planta = terreno menos patios. "
           "El ancho del pasillo es el que hay frente a cada puerta de entrada. Un piso sin palier (los niveles "
           "superiores de un dúplex) no tiene pasillo.", ""]
    filas = []
    for p in cat["plantas"]:
        m = p["metricas"]
        filas.append([p["proyecto"], p["nivel"], m["viviendas"], m["nucleos"], _f(m["viviendas_por_nucleo"]),
                      _f((m["ancho_pasillo"] or {}).get("mediana"), 2), _f(m["circulacion_pct"]) if m["con_palier"] else "—",
                      _f(m["eficiencia"]), _f(p["planta"])])
    filas.append(["**Mediana** (con palier)", "", "", "", _f((pl["viviendas_por_nucleo"] or {}).get("mediana")),
                  _f((pl["ancho_pasillo"] or {}).get("mediana"), 2), _f((pl["circulacion_pct"] or {}).get("mediana")),
                  _f((pl["eficiencia"] or {}).get("mediana")), ""])
    L_ += _tabla(["Proyecto", "Nivel", "Viviendas", "Núcleos", "Viviendas por núcleo", "Ancho de pasillo mediano (m)",
                  "Circulación (%)", "Eficiencia (%)", "Planta (m²)"], filas)
    nu = pl["nucleo"]
    L_ += ["Núcleo (escalera + ascensor + ductos, sin el palier, que va en el pasillo): %d medidos, de %s m² como mediana y una caja de %s × %s m (lado mayor × lado menor). "
           "Ancho de pasillo de todas las puertas: %s m (%d puertas). Hay %d plantas con palier de %d; cada nivel cuenta "
           "una vez, aunque dos niveles de un proyecto sean casi iguales." % (
               nu["n"], _f(nu["area"]), _f(nu["lado_mayor"]), _f(nu["lado_menor"]), _rango(pl["ancho_pasillo"], 2),
               (pl["ancho_pasillo"] or {}).get("n", 0), pl["con_palier"], pl["n"]), ""]
    # 4. comparación
    L_ += ["## 4. Comparación con `standards.py` y `REFERENCIAS.md`", "", "### 4.1 Superficie de la vivienda", "",
           "Medida: mediana de la superficie con muros. «Norma» es `vivienda.superficie_min` (norma nacional, art. 3) y «ANV», "
           "`vivienda.rango_vivienda`; «Propuesta» es la de `REFERENCIAS.md` (sección 2); «Mix del motor» es el área del "
           "tipo con esos dormitorios en `DEFAULT_PARAMS[\"unit_mix\"]`. `standards.py` no tiene un típico por tipología.", ""]
    filas = []
    for c in cmp_["viviendas"]:
        filas.append([c["tipologia"], c["n"], _f(c["medida"]), _f(c["superficie_min"], 0),
                      "%s–%s" % (_f(c["rango_anv"][0], 0), _f(c["rango_anv"][1], 0)), _f(c["referencias"], 0),
                      _f(c["mix_motor"], 0), _dif(c["medida"], c["referencias"]),
                      "%s × %s" % (_f(c["frente"]), _f(c["fondo"])),
                      "%s × %s" % (_g(c["referencias_frente_fondo"][0]), _g(c["referencias_frente_fondo"][1]))])
    L_ += _tabla(["Tipología", "n", "Medida (m²)", "Norma (m²)", "ANV (m²)", "Propuesta (m²)", "Mix del motor (m²)",
                  "Medida / propuesta", "Frente × fondo medido (m)", "Frente × fondo propuesto (m)"], filas)
    L_ += ["### 4.2 Estancias", "",
           "Medida: mediana de todas las tipologías juntas. Típico y mínimo, de `engine/standards.py` (`vivienda.<clave>`): el "
           "área de `typ_area` (o frente × fondo de `typ`), `typ` como frente × fondo y `min_area`; «Tope» es `max_area` (la "
           "cocina integrada se dibuja con 5 m² como máximo).", ""]
    filas = []
    for c in cmp_["estancias"]:
        if not c["n"]:
            continue
        filas.append([c["estancia"], c["n"], _f(c["area"]), _f(c["tipico_area"]), _dif(c["area"], c["tipico_area"]),
                      _f(c["minimo_area"]), _f(c["tope_area"]), _caja(c),
                      "%s × %s" % (_g(c["tipico"][0]), _g(c["tipico"][1])) if c["tipico"] else "—", c["clave"]])
    L_ += _tabla(["Estancia", "n", "Medida (m²)", "Típico (m²)", "Medida / típico", "Mínimo (m²)", "Tope (m²)",
                  "Medida ancho × fondo (m)", "Típico frente × fondo (m)", "Clave"], filas)
    L_ += ["### 4.3 Estar-comedor", "",
           "Estar + comedor (y, en el monoambiente, la zona de dormir: el motor la dibuja dentro del «Estar-Dormitorio») por "
           "vivienda, comparado con `vivienda.estar_por_dorms`.", ""]
    filas = [[c["tipologia"], c["n"], _f(c["medida"]), _f(c["estar_por_dorms"]), _dif(c["medida"], c["estar_por_dorms"])]
             for c in cmp_["zona_estar"]]
    L_ += _tabla(["Tipología", "n", "Medida (m²)", "`estar_por_dorms` (m²)", "Medida / motor"], filas)
    pp = cmp_["plantas"]
    L_ += ["### 4.4 Plantas y parámetros del motor", "",
           "Parámetros por defecto de `engine/layout.py`. El núcleo del motor es el de un ascensor y 3,0 m de piso: la caja de "
           "`standards.core_size` partida en sus piezas con `programs.core_parts`, con la escalera perpendicular al pasillo "
           "(giro 0) o a lo largo (giro 90).", ""]
    n0, n90, mm = pp["nucleo"]["motor"]["giro_0"], pp["nucleo"]["motor"]["giro_90"], pp["nucleo"]["medida"]
    fm = pp["frente_minimo"]
    caja = lambda c: "%s × %s" % (_f(c[0]), _f(c[1]))
    filas = [["Ancho del pasillo común (m)", "%s (`corridor_width`); norma %s" % (
                  _f(pp["ancho_pasillo"]["motor"]), " / ".join(_f(a) for a in pp["ancho_pasillo"]["norma"])),
              _rango(pp["ancho_pasillo"]["medida"], 2)],
             ["Núcleo del motor sin palier (escalera + ascensor + ductos), superficie (m²)",
              "%s con giro 0; %s con giro 90" % (_f(n0["area_sin_palier"]), _f(n90["area_sin_palier"])), _f(mm["area"])],
             ["Núcleo del motor con palier (`core_size`), superficie (m²)",
              "%s con giro 0; %s con giro 90" % (_f(n0["area_con_palier"]), _f(n90["area_con_palier"])),
              "— (el palier está en `Trazo_Pasillo`)"],
             ["Caja del núcleo sin palier (m)", "%s con giro 0; %s con giro 90" % (caja(n0["caja_sin_palier"]), caja(n90["caja_sin_palier"])),
              "%s (lado mayor × lado menor)" % caja([mm["lado_mayor"], mm["lado_menor"]])],
             ["Frente mínimo de la vivienda (m)", "%s (`%s`)" % (_f(fm["motor"]), fm["clave"]),
              "%s; %d de %d viviendas están por debajo" % (_f(fm["medida"], 2), fm["bajo_el_minimo"], fm["viviendas"])],
             ["Fondo máximo de la vivienda (m)", "%s (`%s`)" % (_f(pp["fondo_maximo"]["motor"]), pp["fondo_maximo"]["clave"]),
              _f(pp["fondo_maximo"]["medida"], 2)],
             ["Viviendas por núcleo", "—", _rango(pl["viviendas_por_nucleo"])],
             ["Circulación (%)", "—", _rango(pl["circulacion_pct"])], ["Eficiencia (%)", "—", _rango(pl["eficiencia"])]]
    L_ += _tabla(["Medida", "Motor", "Base de tipologías"], filas)
    L_ += ["Sobre el núcleo: `Trazo_Nucleos` es escalera + ascensores + ductos y el palier de los ascensores va en "
           "`Trazo_Pasillo`, así que la circulación medida (%s %%) sí incluye el palier y el núcleo del motor se compara sin "
           "él. La base pone la escalera a lo largo del pasillo, como el giro 90 del motor: su caja (%s) se parece más a la "
           "del giro 90 (%s) que a la del giro 0 (%s)." % (_f((pl["circulacion_pct"] or {}).get("mediana"), 0),
                                                         caja([mm["lado_mayor"], mm["lado_menor"]]), caja(n90["caja_sin_palier"]),
                                                         caja(n0["caja_sin_palier"])), ""]
    L_ += ["---", "", "_Generado por `python -m engine.tipologias`; no editar a mano._", ""]
    return "\n".join(L_)


# ------------------------------------------------------------------ salida
def escribir(catalogo, carpeta=CARPETA):
    """Escribe `catalogo.json` y `RESUMEN.md` en la carpeta (UTF-8, saltos de línea «\\n»: iguales en Linux y Windows).
    Devuelve las dos rutas."""
    os.makedirs(carpeta, exist_ok=True)
    ruta_json = os.path.join(carpeta, "catalogo.json")
    with open(ruta_json, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(catalogo, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    ruta_md = os.path.join(carpeta, "RESUMEN.md")
    with open(ruta_md, "w", encoding="utf-8", newline="\n") as f:
        f.write(resumen_md(catalogo))
    return ruta_json, ruta_md


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if len(argv) > 1 and argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 2
    carpeta = argv[1] if len(argv) > 1 else CARPETA
    if not os.path.isdir(carpeta):
        print("No existe la carpeta %s. Uso: python -m engine.tipologias [carpeta]" % carpeta)
        return 2
    cat = leer_base(carpeta)
    if not cat["archivos"]:
        print("No hay ningún DXF en %s." % carpeta)
        return 2
    ruta_json, ruta_md = escribir(cat, carpeta)
    print("Leí %d archivos de %s: %d viviendas y %d plantas." % (cat["archivos"], carpeta, len(cat["viviendas"]),
                                                                  len(cat["plantas"])))
    for a in cat["avisos"]:
        print("Aviso: " + a)
    print("Escribí %s y %s." % (ruta_json, ruta_md))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
