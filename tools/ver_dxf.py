#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vista y control de un DXF de la base de tipologías (convención de `TIPOLOGIAS.md`).

Uso:  python tools/ver_dxf.py plano.dxf [salida.svg]

Escribe un SVG para mirar el plano (una capa por color, las etiquetas de las estancias con su superficie, la entrada,
las ventanas, el norte y una escala) e imprime el informe de control: capas encontradas, unidades y estancias con su
superficie, etiquetas que faltan o no están en la lista, entradas, fachadas y metadatos. Termina con 1 si hay errores
(lo que la lista de control de la convención no admite) y 0 si solo hay avisos. Solo biblioteca estándar; la geometría
la lee `engine/dxf_lector.py` (LINE, polilíneas, arcos, círculos, bloques), y los textos (TEXT y MTEXT) se leen aquí.
"""
import html
import math
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
from engine import dxf_lector as L   # noqa: E402
from engine import geometry as G     # noqa: E402

CAPAS = ("datos", "norte", "unidad", "estancias", "puertas", "entrada", "ventanas", "fachada", "medianeras",
         "muros", "equipamiento", "terreno", "patios", "pasillo", "nucleos", "cotas")
ALIAS = {"unidades": "unidad", "estancia": "estancias", "puerta": "puertas", "entradas": "entrada", "ventana": "ventanas",
         "medianera": "medianeras", "muro": "muros", "patio": "patios", "pasillos": "pasillo", "nucleo": "nucleos",
         "dato": "datos", "cota": "cotas", "footprint": "terreno"}
CERRADAS = ("unidad", "estancias", "terreno", "patios", "pasillo", "nucleos")     # capas de polilíneas cerradas
_CAPA = re.compile(r"^trazo[ _:-]+([a-z]+)(?![a-z0-9])")
ETIQUETA = re.compile(r"^(Hall|Estar|Comedor|Estar-Comedor|Cocina|Cocina integrada|Pasillo|Dormitorio \d+|Baño|Baño \d+"
                      r"|Baño en suite|Toilette|Lavadero|Depósito|Estudio|Vestidor|Balcón|Terraza|Patio)$")
HABITABLE = re.compile(r"^(Estar|Comedor|Estar-Comedor|Dormitorio \d+|Estudio)$")
TIPOLOGIA = re.compile(r"^(Mono|\dD)\s+([\d]+(?:[.,]\d+)?)")
CLAVES = ("fuente", "ciudad", "tipo", "tipologia", "frente", "fondo", "superficie_muros", "precision")
TOL_BORDE = 0.30       # m: una entrada «está» sobre el contorno si su medio queda a menos de esto
TOL_FACHADA = 0.35     # m: una estancia «toca» la fachada si uno de sus lados queda a menos de esto (el muro)


# ------------------------------------------------------------------ lectura
def rol(capa):
    """Rol de una capa de la convención (`Trazo_Estancias` -> «estancias»), o None si no es de Trazo."""
    m = _CAPA.match(capa.strip().lower())
    if not m:
        return None
    r = ALIAS.get(m.group(1), m.group(1))
    return r if r in CAPAS else None


def _limpiar_mtext(t):
    t = re.sub(r"\\[A-Za-z][^;\\]*;", "", t)         # códigos de formato: \fArial|b0;, \H2.5;, \C1;
    t = t.replace("\\P", " ").replace("{", "").replace("}", "")
    return " ".join(t.split())


def _textos(texto):
    """[(capa, texto, (x, y), alto)] de los TEXT y MTEXT del espacio modelo, en unidades del dibujo."""
    out, seccion, rec = [], None, None

    def cerrar(rec):
        tipo, pares = rec
        if seccion != "ENTITIES" or tipo not in ("TEXT", "MTEXT") or L._v(pares, 67) == "1":
            return
        t = "".join(v for c, v in pares if c == 3) + L._v(pares, 1, "")
        t = _limpiar_mtext(t) if tipo == "MTEXT" else " ".join(t.split())
        if t:
            out.append((L._v(pares, 8, "0"), t, (L._f(pares, 10), L._f(pares, 20)), L._f(pares, 40, 0.25)))

    for c, v in L._pares(texto):
        if c == 0:
            if rec is not None:
                cerrar(rec)
            rec = [v, []]
            if v == "ENDSEC":
                seccion = None
        elif rec is not None:
            if rec[0] == "SECTION" and c == 2 and not rec[1]:
                seccion = v
            rec[1].append((c, v))
    if rec is not None:
        cerrar(rec)
    return out


def leer(texto):
    """El dibujo en metros: {escala, insunits, formas: [{rol, capa, pts, cerrada, punto}], textos: [{rol, capa, texto,
    p, alto}], otras_capas: [...]}."""
    d = L._Dibujo()
    d.leer(texto)
    esc = L.UNIDADES[d.insunits][1] if d.insunits in L.UNIDADES else 1.0
    formas, textos, otras = [], [], set()
    for f in d.modelo:
        r = rol(f.capa)
        if r is None:
            otras.add(f.capa)
            continue
        formas.append({"rol": r, "capa": f.capa, "pts": [(x * esc, y * esc) for x, y in f.pts],
                       "cerrada": bool(f.cerrada), "punto": f.tipo == "punto"})
    for capa, t, (x, y), alto in _textos(texto):
        r = rol(capa)
        if r is None:
            otras.add(capa)
            continue
        textos.append({"rol": r, "capa": capa, "texto": t, "p": (x * esc, y * esc), "alto": alto * esc})
    return {"escala": esc, "insunits": d.insunits, "formas": formas, "textos": textos, "otras_capas": sorted(otras)}


# ------------------------------------------------------------------ geometría de apoyo
def _dist_seg(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / l2))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def _dist_contorno(p, poly):
    return min(_dist_seg(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def _segmentos(formas, r):
    """Los tramos (a, b) de las formas abiertas y cerradas de un rol (líneas y polilíneas)."""
    segs = []
    for f in formas:
        if f["rol"] != r or f["punto"] or len(f["pts"]) < 2:
            continue
        pts = f["pts"]
        n = len(pts) if f["cerrada"] else len(pts) - 1
        segs.extend((pts[i], pts[(i + 1) % len(pts)]) for i in range(n))
    return segs


def _toca(poly, segs, tol):
    """Un lado del polígono queda a menos de tol de alguno de los tramos (fachada, medianera)."""
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        for s in segs:
            if min(_dist_seg(a, *s), _dist_seg(b, *s), _dist_seg(m, *s)) <= tol:
                return True
            if min(_dist_seg(s[0], a, b), _dist_seg(s[1], a, b)) <= tol:
                return True
    return False


def _texto_en(textos, r, poly):
    """El texto del rol r cuyo punto cae dentro del polígono (el primero), o None."""
    for t in textos:
        if t["rol"] == r and G.point_in_poly(t["p"], poly):
            return t
    return None


def _num_es(v):
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def fmt(x, dec=1):
    return ("%.*f" % (dec, x)).replace(".", ",")


# ------------------------------------------------------------------ control
def controlar(datos):
    """El informe: tipo, unidades, estancias, entradas, datos, errores y avisos."""
    formas, textos = datos["formas"], datos["textos"]
    capas = {}
    for f in formas:
        capas[f["rol"]] = capas.get(f["rol"], 0) + 1
    for t in textos:
        capas[t["rol"]] = capas.get(t["rol"], 0) + 1
    errores, avisos = [], []
    tipo = "planta" if any(r in capas for r in ("terreno", "pasillo", "nucleos")) else "unidad"
    if datos["insunits"] not in L.UNIDADES:
        avisos.append("el DXF no dice sus unidades ($INSUNITS): se supone metros")
    for r in CERRADAS:
        n = sum(1 for f in formas if f["rol"] == r and not f["cerrada"] and not f["punto"])
        if n:
            errores.append("%d polilínea%s abierta%s en Trazo_%s" % (n, "s" if n > 1 else "", "s" if n > 1 else "",
                                                                   r.capitalize()))
    unidades = []
    for f in formas:
        if f["rol"] == "unidad" and f["cerrada"] and len(f["pts"]) >= 3:
            u = {"pts": f["pts"], "area": abs(G.area(f["pts"])), "etiqueta": None, "tipologia": None, "m2": None,
                 "estancias": [], "entradas": 0}
            t = _texto_en(textos, "unidad", f["pts"])
            if t:
                u["etiqueta"] = t["texto"]
                m = TIPOLOGIA.match(t["texto"])
                if m:
                    u["tipologia"], u["m2"] = m.group(1), _num_es(m.group(2))
            unidades.append(u)
    if not unidades:
        (errores if tipo == "unidad" else avisos).append("no hay ninguna vivienda cerrada en Trazo_Unidad")
    for k, u in enumerate(unidades, 1):
        if u["etiqueta"] is None:
            avisos.append("la vivienda %d no tiene etiqueta («2D 58.3») en Trazo_Unidad" % k)
        elif u["tipologia"] is None:
            avisos.append("la etiqueta «%s» de la vivienda %d no es «Mono», «1D», «2D»… seguida de los m²" % (u["etiqueta"], k))
        elif u["m2"] and abs(u["m2"] - u["area"]) > 0.03 * u["area"]:
            avisos.append("la vivienda %d dice %s m² y mide %s" % (k, fmt(u["m2"]), fmt(u["area"])))
    estancias = []
    fach = _segmentos(formas, "fachada")
    for f in formas:
        if f["rol"] != "estancias" or not f["cerrada"] or len(f["pts"]) < 3:
            continue
        c = G.centroid(f["pts"])
        t = _texto_en(textos, "estancias", f["pts"])
        e = {"pts": f["pts"], "area": abs(G.area(f["pts"])), "nombre": t["texto"] if t else None, "c": c,
             "unidad": None, "habitable": False, "fachada": None}
        for k, u in enumerate(unidades):
            if G.point_in_poly(c, u["pts"]):
                e["unidad"] = k
                u["estancias"].append(e)
                break
        if e["nombre"] is None:
            errores.append("estancia de %s m² en (%s, %s) sin etiqueta" % (fmt(e["area"]), fmt(c[0], 2), fmt(c[1], 2)))
        elif not ETIQUETA.match(e["nombre"]):
            errores.append("la etiqueta «%s» no está en la lista de la convención" % e["nombre"])
        else:
            e["habitable"] = bool(HABITABLE.match(e["nombre"]))
        if unidades and e["unidad"] is None:
            errores.append("la estancia «%s» no está dentro de ninguna vivienda" % (e["nombre"] or "?"))
        if e["habitable"]:
            e["fachada"] = _toca(f["pts"], fach, TOL_FACHADA) if fach else None
            if e["fachada"] is False:
                avisos.append("«%s» no toca ninguna fachada (Trazo_Fachada)" % e["nombre"])
        estancias.append(e)
    if estancias and not fach:
        avisos.append("no hay Trazo_Fachada: no se puede comprobar la luz de las estancias")
    for i in range(len(estancias)):
        for j in range(i + 1, len(estancias)):
            a, b = estancias[i], estancias[j]
            if G.point_in_poly(a["c"], b["pts"]) or G.point_in_poly(b["c"], a["pts"]):
                errores.append("«%s» y «%s» se superponen" % (a["nombre"] or "?", b["nombre"] or "?"))
    for k, u in enumerate(unidades, 1):
        if u["estancias"]:
            s = sum(e["area"] for e in u["estancias"])
            if s > 1.02 * u["area"]:
                errores.append("las estancias de la vivienda %d suman %s m², más que su contorno (%s)" % (k, fmt(s), fmt(u["area"])))
            elif s < 0.6 * u["area"]:
                avisos.append("las estancias de la vivienda %d suman %s m² de %s: falta más de un tercio" % (k, fmt(s), fmt(u["area"])))
            dorms = sum(1 for e in u["estancias"] if e["nombre"] and e["nombre"].startswith("Dormitorio"))
            if u["tipologia"] and u["tipologia"] != ("Mono" if dorms == 0 else "%dD" % dorms):
                avisos.append("la vivienda %d está etiquetada «%s» y tiene %d dormitorio%s" % (k, u["tipologia"], dorms, "" if dorms == 1 else "s"))
    entradas = [f for f in formas if f["rol"] == "entrada" and not f["punto"] and len(f["pts"]) >= 2]
    for f in entradas:
        a, b = f["pts"][0], f["pts"][-1]
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        for u in unidades:
            if _dist_contorno(m, u["pts"]) <= TOL_BORDE:
                u["entradas"] += 1
    for k, u in enumerate(unidades, 1):
        if u["entradas"] == 0:
            (errores if tipo == "unidad" else avisos).append("la vivienda %d no tiene entrada (Trazo_Entrada sobre su contorno)" % k)
        elif u["entradas"] > 1:
            avisos.append("la vivienda %d tiene %d entradas" % (k, u["entradas"]))
    meta = {}
    for t in textos:
        if t["rol"] == "datos" and ":" in t["texto"]:
            k, v = t["texto"].split(":", 1)
            meta[k.strip().lower()] = v.strip()
    faltan = [k for k in CLAVES if k not in meta]
    if faltan:
        avisos.append("faltan datos en Trazo_Datos: " + ", ".join(faltan))
    if tipo == "unidad" and len(unidades) == 1 and _num_es(meta.get("superficie_muros", "")) is not None:
        sm = _num_es(meta["superficie_muros"])
        if abs(sm - unidades[0]["area"]) > 0.02 * unidades[0]["area"]:
            errores.append("superficie_muros dice %s m² y el contorno mide %s (más del 2 %%)" % (fmt(sm), fmt(unidades[0]["area"])))
    norte = None
    for f in formas:
        if f["rol"] == "norte" and len(f["pts"]) >= 2:
            a, b = f["pts"][0], f["pts"][-1]
            norte = math.degrees(math.atan2(-(b[0] - a[0]), b[1] - a[1])) % 360     # antihorario desde +Y
            break
    if norte is None:
        avisos.append("sin norte (una línea en Trazo_Norte)")
    largo_fachada = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in fach)
    return {"tipo": tipo, "escala": datos["escala"], "capas": capas, "otras_capas": datos["otras_capas"],
            "unidades": unidades, "estancias": estancias, "entradas": len(entradas),
            "puertas": sum(1 for f in formas if f["rol"] == "puertas"),
            "ventanas": sum(1 for f in formas if f["rol"] == "ventanas"), "fachada": largo_fachada,
            "datos": meta, "norte": norte, "errores": errores, "avisos": avisos}


def informe_txt(nombre, inf):
    """El informe en líneas de texto."""
    lineas = ["%s: %s en metros%s; capas Trazo: %s%s" % (
        nombre, inf["tipo"], "" if inf["escala"] == 1.0 else " (escala %g)" % inf["escala"],
        ", ".join("%s (%d)" % (k, v) for k, v in sorted(inf["capas"].items())) or "ninguna",
        ("; otras capas: " + ", ".join(inf["otras_capas"])) if inf["otras_capas"] else "")]
    for k, u in enumerate(inf["unidades"], 1):
        lineas.append("Vivienda %d: %s m²%s; entradas: %d; estancias: %d" % (
            k, fmt(u["area"]), (" (etiqueta «%s»)" % u["etiqueta"]) if u["etiqueta"] else "", u["entradas"], len(u["estancias"])))
        for e in u["estancias"]:
            lineas.append("  %s %s m²%s" % (e["nombre"] or "(sin etiqueta)", fmt(e["area"]),
                                           " (fachada)" if e["fachada"] else (" (sin fachada)" if e["fachada"] is False else "")))
    sueltas = [e for e in inf["estancias"] if e["unidad"] is None]
    if sueltas:
        lineas.append("Estancias fuera de las viviendas: " + ", ".join("%s %s m²" % (e["nombre"] or "?", fmt(e["area"])) for e in sueltas))
    lineas.append("Puertas: %d; ventanas: %d; fachada: %s m; norte: %s" % (
        inf["puertas"], inf["ventanas"], fmt(inf["fachada"]), ("%s°" % fmt(inf["norte"], 0)) if inf["norte"] is not None else "no"))
    if inf["datos"]:
        lineas.append("Datos: " + "; ".join("%s: %s" % (k, v) for k, v in inf["datos"].items()))
    lineas.append("Errores: " + ("; ".join(inf["errores"]) if inf["errores"] else "ninguno"))
    lineas.append("Avisos: " + ("; ".join(inf["avisos"]) if inf["avisos"] else "ninguno"))
    return lineas


# ------------------------------------------------------------------ SVG
RELLENO = {"Dormitorio": "#dbe9ff", "Estar": "#fff1c2", "Comedor": "#fff1c2", "Estar-Comedor": "#fff1c2",
           "Cocina": "#ffd9b3", "Cocina integrada": "#ffd9b3", "Baño": "#d8f5e3", "Baño en suite": "#d8f5e3",
           "Toilette": "#d8f5e3", "Hall": "#eeeeee", "Pasillo": "#eeeeee", "Lavadero": "#e8dcf5", "Depósito": "#e8dcf5",
           "Vestidor": "#e8dcf5", "Estudio": "#dbe9ff", "Balcón": "#e3f2d9", "Terraza": "#e3f2d9", "Patio": "#e3f2d9"}
ESTILO = {"terreno": "fill:none;stroke:#333;stroke-width:3", "patios": "fill:#e3f2d9;stroke:#6a9a4a;stroke-width:1",
          "pasillo": "fill:#dddddd;stroke:#888;stroke-width:1", "nucleos": "fill:#9a9a9a;stroke:#444;stroke-width:1",
          "unidad": "fill:none;stroke:#1a1a1a;stroke-width:2.2", "muros": "fill:#444;stroke:none",
          "fachada": "fill:none;stroke:#e8a000;stroke-width:4", "medianeras": "fill:none;stroke:#000;stroke-width:4",
          "ventanas": "fill:none;stroke:#1f6fd0;stroke-width:3", "puertas": "fill:none;stroke:#d04020;stroke-width:2",
          "entrada": "fill:none;stroke:#d04020;stroke-width:5", "equipamiento": "fill:none;stroke:#777;stroke-width:0.8",
          "norte": "fill:none;stroke:#c00;stroke-width:2", "cotas": "fill:none;stroke:#bbb;stroke-width:0.6"}
ORDEN = ("terreno", "patios", "pasillo", "nucleos", "unidad", "estancias", "muros", "fachada", "medianeras", "ventanas",
         "puertas", "entrada", "equipamiento", "cotas", "norte")


def svg(datos, inf, ancho=1000, titulo=""):
    """El plano como SVG: capas con color, etiquetas, datos, leyenda y escala."""
    pts = [p for f in datos["formas"] for p in f["pts"]]
    if not pts:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="60"><text x="10" y="35">DXF sin figuras de Trazo</text></svg>'
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    x1, y1 = max(p[0] for p in pts), max(p[1] for p in pts)
    panel, arriba, abajo, margen = 300, 34, 44, 0.8
    w, h = max(x1 - x0, 1.0) + 2 * margen, max(y1 - y0, 1.0) + 2 * margen
    s = (ancho - panel) / w
    alto = int(h * s + arriba + abajo)
    X = lambda x: (x - x0 + margen) * s
    Y = lambda y: arriba + (y1 + margen - y) * s
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
           'font-family="Helvetica, Arial, sans-serif">' % (ancho, alto, ancho, alto),
           '<rect width="100%" height="100%" fill="#fff"/>',
           '<text x="10" y="22" font-size="15" font-weight="bold">%s</text>' % html.escape(titulo or "")]

    def camino(ptsl, cerrada):
        d = "M " + " L ".join("%.1f %.1f" % (X(x), Y(y)) for x, y in ptsl)
        return d + (" Z" if cerrada else "")

    por_rol = {}
    for f in datos["formas"]:
        por_rol.setdefault(f["rol"], []).append(f)
    for r in ORDEN:
        for f in por_rol.get(r, []):
            if f["punto"] or len(f["pts"]) < 2:
                continue
            if r == "estancias":
                nombre = next((e["nombre"] for e in inf["estancias"] if e["pts"] is f["pts"]), None)
                base = (nombre or "").split(" ")[0] if nombre else ""
                relleno = RELLENO.get(nombre or "", RELLENO.get(base, "#ffffff"))
                estilo = "fill:%s;stroke:#555;stroke-width:1" % relleno
            else:
                estilo = ESTILO[r]
            out.append('<path d="%s" style="%s"/>' % (camino(f["pts"], f["cerrada"]), estilo))
    for e in inf["estancias"]:                        # etiquetas de las estancias, en su centro
        cx, cy = e["c"]
        texto = (e["nombre"] or "¿?") + " " + fmt(e["area"]) + " m²"
        out.append('<text x="%.1f" y="%.1f" font-size="11" text-anchor="middle" fill="%s">%s</text>'
                   % (X(cx), Y(cy) + 4, "#a00" if not e["nombre"] else "#222", html.escape(texto)))
    for k, u in enumerate(inf["unidades"], 1):        # etiqueta de la vivienda, arriba de su contorno
        bx = G.bbox(u["pts"])
        out.append('<text x="%.1f" y="%.1f" font-size="12" font-weight="bold" text-anchor="middle">%s</text>'
                   % (X((bx[0] + bx[2]) / 2), Y(bx[3]) - 4, html.escape((u["etiqueta"] or "Vivienda %d" % k) + " · %s m²" % fmt(u["area"]))))
    for f in por_rol.get("norte", []):                # flecha del norte
        if len(f["pts"]) >= 2:
            b = f["pts"][-1]
            out.append('<text x="%.1f" y="%.1f" font-size="12" fill="#c00" text-anchor="middle">N</text>' % (X(b[0]), Y(b[1]) - 6))
    px, py = ancho - panel + 12, arriba + 6            # panel de datos
    out.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#f7f7f7" stroke="#ccc"/>' % (px - 6, py - 6, panel - 18, alto - arriba - abajo))
    y = py + 12
    out.append('<text x="%d" y="%d" font-size="12" font-weight="bold">Datos</text>' % (px, y))
    for k, v in inf["datos"].items():
        y += 15
        out.append('<text x="%d" y="%d" font-size="11">%s</text>' % (px, y, html.escape(("%s: %s" % (k, v))[:48])))
    y += 22
    out.append('<text x="%d" y="%d" font-size="12" font-weight="bold">Control</text>' % (px, y))
    for linea, color in [(e, "#a00") for e in inf["errores"]] + [(a, "#865") for a in inf["avisos"]]:
        for trozo in [linea[i:i + 46] for i in range(0, len(linea), 46)][:3]:
            y += 14
            out.append('<text x="%d" y="%d" font-size="10" fill="%s">%s</text>' % (px, y, color, html.escape(trozo)))
    if not inf["errores"] and not inf["avisos"]:
        y += 14
        out.append('<text x="%d" y="%d" font-size="11" fill="#2a7">Sin errores ni avisos</text>' % (px, y))
    y += 22
    out.append('<text x="%d" y="%d" font-size="12" font-weight="bold">Capas</text>' % (px, y))
    for r in ORDEN:
        if r in inf["capas"] and r in ESTILO:
            y += 14
            out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" style="%s"/><text x="%d" y="%d" font-size="10">Trazo_%s (%d)</text>'
                       % (px, y - 4, px + 24, y - 4, ESTILO[r], px + 30, y, r.capitalize(), inf["capas"][r]))
    largo = 5.0 if w > 12 else 1.0                      # escala gráfica
    ex, ey = 12, alto - 16
    out.append('<line x1="%d" y1="%d" x2="%.1f" y2="%d" stroke="#000" stroke-width="3"/>'
               '<text x="%d" y="%d" font-size="11">%s m</text>' % (ex, ey, ex + largo * s, ey, ex, ey - 6, fmt(largo, 0)))
    out.append("</svg>")
    return "\n".join(out)


# ------------------------------------------------------------------ programa
def procesar(ruta_dxf, ruta_svg=None, ancho=1000):
    """Lee el DXF, escribe el SVG (junto al DXF si no se da otra ruta) y devuelve (informe, líneas de texto, ruta_svg)."""
    with open(ruta_dxf, "rb") as f:
        crudo = f.read()
    try:
        texto = crudo.decode("utf-8")
    except UnicodeDecodeError:
        texto = crudo.decode("cp1252", errors="replace")
    datos = leer(texto)
    inf = controlar(datos)
    nombre = os.path.basename(ruta_dxf)
    ruta_svg = ruta_svg or os.path.splitext(ruta_dxf)[0] + ".svg"
    with open(ruta_svg, "w", encoding="utf-8") as f:
        f.write(svg(datos, inf, ancho, titulo="%s · %s" % (nombre, inf["tipo"])))
    return inf, informe_txt(nombre, inf), ruta_svg


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 2
    try:
        inf, lineas, ruta_svg = procesar(argv[1], argv[2] if len(argv) > 2 else None)
    except L.ErrorDxf as e:
        print("No se pudo leer el DXF: %s" % e)
        return 2
    for l in lineas:
        print(l)
    print("SVG: " + ruta_svg)
    return 1 if inf["errores"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
