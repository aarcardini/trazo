#! python 3
# -*- coding: utf-8 -*-
"""Puente Rhino 8 <-> Trazo.

Ejecuta este archivo en Rhino 8 con el comando:   _RunPythonScript   (selecciona este archivo)
o ábrelo en _ScriptEditor y pulsa Run.

  Enviar       : toma un sólido cerrado, extrae la huella y la altura y la manda a la web.
  Recibir      : dibuja en Rhino lo que generaste en la web (capas Trazo::Footprint y Trazo::L00, L01…).
                 Si ya hay un resultado anterior, pregunta si reemplazarlo.
  Diagnostico  : muestra la versión de Rhino, las unidades del archivo, las capas de Trazo y el estado del servidor.

Requiere que el servidor esté corriendo:  py server.py (Windows)  /  python3 server.py (Mac)
"""
import json
import math
import socket
import sys
import traceback
import urllib.error
import urllib.request

import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System.Drawing as SD
from System.Collections.Generic import List

SERVER = "http://127.0.0.1:8765"


# ------------------------------------------------------------------ mensajes
class TrazoError(Exception):
    """Fallo con un mensaje para el usuario: qué pasó y qué hacer."""


def arrancar():
    """Cómo arrancar el servidor en este sistema."""
    cmd = "python3 server.py" if sys.platform == "darwin" else "py server.py"
    return ("abre una terminal en la carpeta de Trazo, escribe «%s» y deja esa ventana abierta; "
            "después vuelve a ejecutar este script" % cmd)


def _error_conexion(e):
    motivo = getattr(e, "reason", e)
    if isinstance(motivo, socket.timeout) or "timed out" in str(motivo):
        return ("Trazo no respondió a tiempo (%s). Si estaba calculando algo grande, espera y vuelve a intentarlo; "
                "si no, ciérralo con Ctrl+C en su ventana y arráncalo de nuevo." % SERVER)
    return "No hay conexión con Trazo (%s): el servidor no está corriendo. Para arrancarlo, %s." % (SERVER, arrancar())


def _error_http(e):
    try:
        detalle = json.loads(e.read().decode("utf-8")).get("error") or ""
    except Exception:
        detalle = ""
    if e.code == 404:
        return ("En %s responde un servidor que no reconoce la petición (error 404): ¿es otra versión de Trazo u otro "
                "programa? Ciérralo; para arrancar el Trazo de esta carpeta, %s." % (SERVER, arrancar()))
    return ("El servidor de Trazo respondió con un error (%d%s). Copia este mensaje y lo que muestre la ventana del "
            "servidor y pégalos en la sesión de Claude Code." % (e.code, ": " + detalle if detalle else ""))


TIPOS = {1: "un punto", 4: "una curva", 8: "una superficie", 16: "una polisuperficie", 32: "una malla",
         4096: "un bloque", 262144: "un objeto SubD", 1073741824: "una extrusión"}
COMO_SOLIDO = {
    4: "Si es el contorno de la planta, extrúyelo como sólido: _ExtrudeCrv con «Sólido=Sí».",
    8: "Extrúyela como sólido: _ExtrudeSrf con «Sólido=Sí».",
    32: "Conviértela en polisuperficie con _MeshToNURB, o dibuja la masa como una extrusión.",
    4096: "Explota el bloque con _Explode (o entra con _BlockEdit) y selecciona la masa.",
    262144: "Conviértelo en polisuperficie con _ToNURBS.",
}
VALIDOS = (8, 16, 1073741824)        # superficie cerrada, polisuperficie, extrusión
SIN_BASE = ("No encontré una cara inferior plana y horizontal. La masa tiene que apoyar sobre una base plana y "
            "horizontal, como una extrusión vertical: si está abierta abajo, ciérrala con _Cap; si está inclinada, "
            "enderézala con _Rotate3D.")


def objeto_no_valido(tipo):
    """Mensaje para un objeto que no sirve como masa."""
    return ("Seleccionaste %s, y la masa tiene que ser un sólido cerrado (polisuperficie o extrusión) con la base "
            "plana. %s" % (TIPOS.get(tipo, "un objeto que no es un sólido"),
                           COMO_SOLIDO.get(tipo, "Dibuja la masa como una extrusión cerrada (_ExtrudeCrv con «Sólido=Sí»).")))


UNIDADES = {"Millimeters": "milímetros", "Centimeters": "centímetros", "Meters": "metros", "Kilometers": "kilómetros",
            "Inches": "pulgadas", "Feet": "pies", "None": "sin unidades (se toman como metros)"}


def unidades():
    """Unidades del archivo de Rhino, en español."""
    n = str(sc.doc.ModelUnitSystem)
    return UNIDADES.get(n, n)


def revisar_medidas(largo, ancho, alto, unidades_):
    """Avisos si las medidas en metros no parecen de un edificio (casi siempre, unidades mal puestas)."""
    f = lambda v: ("%.3f" if v < 1 else "%.1f") % v
    txt = "%s × %s m en planta y %s m de alto" % (f(largo), f(ancho), f(alto))
    if max(largo, ancho) < 3 or alto < 2:
        problema = "La masa es muy pequeña: %s." % txt
    elif max(largo, ancho) > 1000 or alto > 500:
        problema = "La masa es enorme: %s." % txt
    else:
        return []
    return [problema, "El archivo está en %s. Si dibujaste pensando en otra unidad, corrígelo con _Units "
                      "(Trazo convierte todo a metros)." % unidades_]


def origen_resultado(res, mass):
    """Aviso si el resultado no corresponde a la última masa enviada desde Rhino (por ejemplo, un ejemplo de la web)."""
    if not mass.get("footprint"):
        return ("El resultado no viene de una masa de Rhino (es un ejemplo de la web o algo dibujado allí): "
                "se dibuja en sus coordenadas, cerca del origen.")
    xs = [p[0] for p in mass["footprint"]]
    ys = [p[1] for p in mass["footprint"]]
    fp = res.get("footprint") or []
    if fp and all(min(xs) - 1 <= x <= max(xs) + 1 and min(ys) - 1 <= y <= max(ys) + 1 for x, y in fp):
        return None
    return ("El resultado no coincide con la última masa enviada desde Rhino («%s»): ¿elegiste otro ejemplo en la "
            "web? Se dibuja igual, en sus coordenadas." % mass.get("name", ""))


# ------------------------------------------------------------------ utilidades
def meters_per_unit():
    k = Rhino.RhinoMath.UnitScale(sc.doc.ModelUnitSystem, Rhino.UnitSystem.Meters)
    return k if k and k > 0 else 1.0


def http(method, path, payload=None, timeout=20):
    """Llama al servidor de Trazo. Si falla, lanza TrazoError con un mensaje que explica qué hacer."""
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(SERVER + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise TrazoError(_error_http(e))
    except (urllib.error.URLError, OSError) as e:
        raise TrazoError(_error_conexion(e))
    try:
        return json.loads(body)
    except ValueError:
        raise TrazoError("En %s responde un programa que no es Trazo: ciérralo. Para arrancar Trazo, %s."
                         % (SERVER, arrancar()))


def _area(pts):
    return abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))) / 2.0


def bottom_outline(brep, tol):
    """Contorno exterior de las caras horizontales inferiores del sólido: (curva, z, nº de partes de la base)."""
    bb = brep.GetBoundingBox(True)
    z0 = bb.Min.Z
    loops = List[Rhino.Geometry.Curve]()
    for f in brep.Faces:
        n = f.NormalAt(f.Domain(0).Mid, f.Domain(1).Mid)
        nz = -n.Z if f.OrientationIsReversed else n.Z
        fb = f.GetBoundingBox(True)
        if nz < -0.99 and abs(fb.Max.Z - z0) < tol * 10 and abs(fb.Min.Z - z0) < tol * 10:
            c = f.OuterLoop.To3dCurve()
            if c:
                loops.Add(c)
    if loops.Count == 0:
        return None, z0, 0
    joined = [c for c in (Rhino.Geometry.Curve.JoinCurves(loops, tol) or []) if c.IsClosed]
    if not joined:
        return None, z0, 0

    def area(c):
        a = Rhino.Geometry.AreaMassProperties.Compute(c)
        return a.Area if a else 0.0
    return max(joined, key=area), z0, len(joined)


def curve_to_points(curve, tol):
    pl = None
    try:                                  # parámetro de salida: (ok, polilínea[, parámetros]) según el Python de Rhino
        r = curve.TryGetPolyline()
        pl = r[1] if r[0] else None
    except Exception:
        pl = None
    if pl is None:
        pc = curve.ToPolyline(tol, 0.01, 0.0, 0.0)
        pl = pc.ToPolyline() if pc else None
    if pl is None:
        return None
    pts = [pl[i] for i in range(pl.Count)]
    if len(pts) > 1 and pts[0].DistanceTo(pts[-1]) < tol:
        pts.pop()
    return pts


# ------------------------------------------------------------------ enviar masa
def nucleo(punto, nombre):
    """Un núcleo de la capa Trazo::Cores: el punto y, si el objeto se llama «ascensores=2», sus ascensores (R10.7)."""
    nm = (nombre or "").lower().replace(" ", "")
    if "ascensores=" in nm:
        try:
            return {"p": punto, "ascensores": max(0, int(float(nm.split("ascensores=")[1].split(";")[0])))}
        except ValueError:
            pass
    return punto


def anchos_de_linea(pts, nombre):
    """R10.8: una polilínea de la capa Trazo::Centerline llamada «ancho=1.4» (o «ancho=1,4») pide ese ancho de pasillo
    para todos sus tramos: [{"seg": [a, b], "ancho": 1.4}] (puntos en metros). Sin ese nombre, [] (el ancho general)."""
    nm = (nombre or "").lower().replace(" ", "")
    if "ancho=" not in nm:
        return []
    try:
        a = float(nm.split("ancho=")[1].split(";")[0].replace(",", "."))
    except ValueError:
        return []
    return [{"seg": [p, q], "ancho": a} for p, q in zip(pts, pts[1:])
            if math.hypot(q[0] - p[0], q[1] - p[1]) > 0.05] if a > 0 else []      # el motor une los vértices a 5 cm o menos


def send_mass():
    http("GET", "/api/version")          # sin servidor, avisa antes de pedir la masa
    oid = rs.GetObject("Selecciona la masa (sólido cerrado: polisuperficie o extrusión)", preselect=True)
    if not oid:
        return
    tipo = rs.ObjectType(oid)
    obj = rs.coercebrep(oid) if tipo in VALIDOS else None
    if obj is None or (tipo == 8 and not obj.IsSolid):
        raise TrazoError(objeto_no_valido(tipo))
    avisos = []
    if not obj.IsSolid:
        avisos.append("La masa no está cerrada: uso igual su base. Para cerrarla, _Cap.")
    tol = sc.doc.ModelAbsoluteTolerance
    outline, z0, partes = bottom_outline(obj, tol)
    if outline is None:
        raise TrazoError(SIN_BASE)
    if partes > 1:
        avisos.append("La base tiene %d partes separadas: envío solo la mayor (Trazo estudia una masa a la vez)." % partes)
    pts = curve_to_points(outline, tol)
    if not pts or len(pts) < 3:
        raise TrazoError("No pude convertir el contorno de la base en una polilínea. Simplifica la base "
                         "(por ejemplo, _Rebuild o _Convert a líneas) y vuelve a intentarlo.")
    k = meters_per_unit()
    bb = obj.GetBoundingBox(True)
    fp = [[p.X * k, p.Y * k] for p in pts]
    alto = (bb.Max.Z - bb.Min.Z) * k
    largo = max(x for x, _ in fp) - min(x for x, _ in fp)
    ancho = max(y for _, y in fp) - min(y for _, y in fp)
    if alto < 0.1:
        raise TrazoError("La masa no tiene altura (%.2f m): Trazo necesita un volumen. Extruye la base con "
                         "_ExtrudeCrv o _ExtrudeSrf («Sólido=Sí»)." % alto)
    medidas = revisar_medidas(largo, ancho, alto, unidades())
    if medidas:
        for m in medidas:
            print("Trazo: " + m)
        if rs.GetString("¿Enviar igual?", "No", ["Si", "No"]) != "Si":
            print("Trazo: no se envió la masa.")
            return
    payload = {
        "name": rs.ObjectName(oid) or "Masa de Rhino",
        "height": round(alto, 4),
        "origin_z": bb.Min.Z,
        "footprint": fp,
    }
    # polilíneas centrales opcionales: curvas en la capa Trazo::Centerline (cada vértice cuenta)
    # (nombre del objeto «ancho=1.4»: ese ancho de pasillo en todos sus tramos; R10.8)
    if rs.IsLayer("Trazo::Centerline"):
        lines, anchos = [], []
        for cid in rs.ObjectsByLayer("Trazo::Centerline") or []:
            crv = rs.coercecurve(cid)
            if crv is None:
                continue
            cp = curve_to_points(crv, tol)
            if cp and len(cp) >= 2:
                if not crv.IsClosed:
                    cp = cp + [crv.PointAtEnd] if cp[-1].DistanceTo(crv.PointAtEnd) > tol else cp
                lines.append([[q.X * k, q.Y * k] for q in cp])
                anchos += anchos_de_linea(lines[-1], rs.ObjectName(cid))
        if lines:
            payload["centerlines"] = lines
        if anchos:
            payload["anchos_pasillo"] = anchos
    # medianeras opcionales: curvas en la capa Trazo::Medianeras (nombre del objeto "retiro=3" para indicar retiro)
    if rs.IsLayer("Trazo::Medianeras"):
        meds = []
        for cid in rs.ObjectsByLayer("Trazo::Medianeras") or []:
            crv = rs.coercecurve(cid)
            if crv is None:
                continue
            nm = (rs.ObjectName(cid) or "").lower().replace(" ", "")
            ret = 0.0
            if "retiro=" in nm:
                try:
                    ret = float(nm.split("retiro=")[1].split(";")[0])
                except ValueError:
                    ret = 0.0
            cp = curve_to_points(crv, tol) or []
            if not crv.IsClosed and cp and cp[-1].DistanceTo(crv.PointAtEnd) > tol:
                cp = cp + [crv.PointAtEnd]
            for a, b in zip(cp, cp[1:]):
                meds.append({"a": [a.X * k, a.Y * k], "b": [b.X * k, b.Y * k], "retiro": ret})
        if meds:
            payload["medianeras"] = meds
    # patios opcionales: curvas cerradas en la capa Trazo::Patios (patios de aire y luz; separan la masa en bloques)
    if rs.IsLayer("Trazo::Patios"):
        pats = []
        for cid in rs.ObjectsByLayer("Trazo::Patios") or []:
            crv = rs.coercecurve(cid)
            if crv is None:
                continue
            if not crv.IsClosed:
                avisos.append("Una curva de la capa Trazo::Patios no está cerrada y no se usa: ciérrala con _CloseCrv.")
                continue
            cp = curve_to_points(crv, tol)
            if cp and len(cp) >= 3:
                pats.append([[q.X * k, q.Y * k] for q in cp])
        if pats:
            payload["patios"] = pats
    # núcleos manuales opcionales: objetos punto en la capa Trazo::Cores (nombre «ascensores=2» para fijar sus ascensores)
    if rs.IsLayer("Trazo::Cores"):
        ids_c = [pid for pid in (rs.ObjectsByLayer("Trazo::Cores") or []) if rs.IsPoint(pid)]
        if ids_c:
            payload["cores"] = [nucleo([q.X * k, q.Y * k], rs.ObjectName(pid))
                                for pid, q in ((pid, rs.PointCoordinates(pid)) for pid in ids_c)]
    res = http("POST", "/api/mass", payload)
    for a in avisos:
        print("Trazo: aviso: " + a)
    print("Masa enviada (versión %s): huella de %.0f m² (%.1f × %.1f m), %.2f m de alto, archivo en %s; "
          "%d polilínea(s), %d medianera(s), %d patio(s), %d núcleo(s) manual(es), %d tramo(s) de pasillo con ancho "
          "propio. Abre %s" %
          (res.get("version"), _area(fp), largo, ancho, alto, unidades(), len(payload.get("centerlines", [])),
           len(payload.get("medianeras", [])), len(payload.get("patios", [])), len(payload.get("cores", [])),
           len(payload.get("anchos_pasillo", [])), SERVER))


# ------------------------------------------------------------------ recibir resultado
LAYER_COLORS = {
    "Footprint": SD.Color.FromArgb(120, 120, 120),
    "Patios": SD.Color.FromArgb(150, 150, 160),
    "Corridor": SD.Color.FromArgb(150, 160, 175),
    "Cores": SD.Color.FromArgb(26, 157, 91),
    "Units": SD.Color.FromArgb(30, 40, 60),
    "bedroom": SD.Color.FromArgb(80, 130, 230),
    "living": SD.Color.FromArgb(230, 170, 50),
    "kitchen": SD.Color.FromArgb(110, 180, 100),
    "bath": SD.Color.FromArgb(60, 170, 200),
    "vestidor": SD.Color.FromArgb(120, 100, 200),
    "Equipamiento": SD.Color.FromArgb(90, 95, 105),
    "Ventanas": SD.Color.FromArgb(40, 120, 200),
    "SinUso": SD.Color.FromArgb(150, 150, 150),
}


def layer(name, color):
    full = "Trazo::" + name
    if not rs.IsLayer(full):
        rs.AddLayer(full, color)
    return full


def add_poly(points, z, lyr, k, name=None, cerrar=True):
    pl = Rhino.Geometry.Polyline()
    for x, y in points:
        pl.Add(x / k, y / k, z)
    if cerrar:
        pl.Add(pl[0])
    guid = sc.doc.Objects.AddPolyline(pl)
    if guid:
        rs.ObjectLayer(guid, lyr)
        if name:
            rs.ObjectName(guid, name)
    return guid


# Capas de resultado: lo que dibuja Recibir (Trazo::Footprint y los niveles Trazo::L00, L01… con sus subcapas).
# Las capas de entrada (Trazo::Centerline, Trazo::Cores, Trazo::Medianeras, Trazo::Patios) no se tocan nunca.
def es_capa_resultado(ruta):
    partes = (ruta or "").split("::")
    if len(partes) < 2 or partes[0] != "Trazo":
        return False
    p = partes[1]
    return p == "Footprint" or (len(p) >= 2 and p[0] == "L" and p[1:].isdigit())


def resultado_anterior():
    """Lo que dejó un Recibir anterior: (objetos, {índice de capa: ruta}). Incluye los objetos ocultos o bloqueados
    y los de capas apagadas o bloqueadas, para que Reemplazar no deje copias escondidas."""
    capas = {c.Index: c.FullPath for c in sc.doc.Layers if not c.IsDeleted and es_capa_resultado(c.FullPath)}
    if not capas:
        return [], capas
    s = Rhino.DocObjects.ObjectEnumeratorSettings()
    s.HiddenObjects = True
    s.LockedObjects = True
    s.ReferenceObjects = False          # los de un archivo vinculado o de referencia no son de este archivo
    return [o for o in sc.doc.Objects.GetObjectList(s) if o.Attributes.LayerIndex in capas], capas


def donde(objs, capas):
    """«Trazo::Footprint y Trazo::L00…L04»: dónde están los objetos de un resultado."""
    raices = {capas[o.Attributes.LayerIndex].split("::")[1] for o in objs}
    niveles = sorted(r for r in raices if r != "Footprint")
    partes = ["Trazo::Footprint"] if "Footprint" in raices else []
    if niveles:
        partes.append("Trazo::" + (niveles[0] if len(niveles) == 1 else "%s…%s" % (niveles[0], niveles[-1])))
    return " y ".join(partes)


def borrar(objs):
    """Borra los objetos aunque estén ocultos o bloqueados (el usuario eligió Reemplazar). Devuelve los que no pudo."""
    quedan = []
    for o in objs:
        try:
            ok = sc.doc.Objects.Delete(o, True, True)        # silencioso y sin respetar ocultos/bloqueados
        except TypeError:                                     # por si esa variante no existiera
            ok = sc.doc.Objects.Delete(o.Id, True)
        if not ok:
            quedan.append(o)
    return quedan


def quitar_niveles_sobrantes(usados):
    """Tras Reemplazar: borra las capas de nivel que el resultado nuevo no usa y quedaron vacías (por ejemplo, al
    pasar de 10 a 5 pisos), de las subcapas hacia arriba. Si alguna no se puede borrar (la capa actual), queda."""
    objs, capas = resultado_anterior()
    raiz = lambda ruta: ruta.split("::")[1]
    llenos = {raiz(capas[o.Attributes.LayerIndex]) for o in objs}
    for i, ruta in sorted(capas.items(), key=lambda c: -c[1].count("::")):
        if raiz(ruta) not in usados and raiz(ruta) != "Footprint" and raiz(ruta) not in llenos:
            try:
                sc.doc.Layers.Delete(i, True)
            except Exception:
                pass


def receive_result():
    data = http("GET", "/api/result")
    res = data.get("result")
    if not res:
        raise TrazoError("Todavía no hay un resultado. Genera uno en la web (por ejemplo, «Generar planos») y "
                         "vuelve a elegir Recibir.")
    k = meters_per_unit()          # unidades de Rhino -> metros
    inv = k                        # metros / (metros por unidad) = unidades
    mass = http("GET", "/api/mass").get("mass") or {}
    aviso = origen_resultado(res, mass)
    if aviso:
        print("Trazo: aviso: " + aviso)
    viejos, capas = resultado_anterior()
    modo = "reemplazar"
    if viejos:
        print("Trazo: ya hay un resultado anterior en este archivo: %d objeto(s) en %s." %
              (len(viejos), donde(viejos, capas)))
        print("  Reemplazar: lo borra (también lo oculto o bloqueado) y dibuja el nuevo. Agregar: lo deja y dibuja "
              "el nuevo además. Cancelar: no cambia nada.")
        op = rs.GetString("¿Qué hago con el resultado anterior?", "Reemplazar", ["Reemplazar", "Agregar", "Cancelar"])
        modo = (op or "Cancelar").strip().lower()
        if modo not in ("reemplazar", "agregar"):
            print("Trazo: no recibí nada; el resultado anterior quedó como estaba. Para recibir, vuelve a elegir Recibir.")
            return
    z_origin = mass.get("origin_z", 0.0)
    sc.doc.Views.RedrawEnabled = False
    count, quedan = 0, []
    stories = [s for s in res["stories"] if s["program"] == "Residential"] or res["stories"][:1]
    try:
        add_poly(res["footprint"], z_origin, layer("Footprint", LAYER_COLORS["Footprint"]), inv)
        for s in stories:
            z = z_origin + s["z"] / k
            tag = "L%02d" % s["index"]
            for p in res.get("patios", []):      # en el nivel, no en Trazo::Patios (esa capa es para enviar)
                add_poly(p, z, layer(tag + "::Patios", LAYER_COLORS["Patios"]), inv, "Patio")
            for c in res.get("corridors", []):
                add_poly(c, z, layer(tag + "::Corridor", LAYER_COLORS["Corridor"]), inv)
            for c in res.get("cores", []):
                add_poly(c["poly"], z, layer(tag + "::Cores", LAYER_COLORS["Cores"]), inv)
                count += 1
            for u in res.get("units", []):
                add_poly(u["poly"], z, layer(tag + "::Units", LAYER_COLORS["Units"]), inv,
                         "%s %s %.1fm2" % (u["id"], u["type"], u["area"]))
                count += 1
                for d in u.get("doors", []):
                    ln = sc.doc.Objects.AddLine(Rhino.Geometry.Point3d(d["p"][0] / inv, d["p"][1] / inv, z),
                                                Rhino.Geometry.Point3d(d["q"][0] / inv, d["q"][1] / inv, z))
                    if ln:
                        rs.ObjectLayer(ln, layer(tag + "::Doors", SD.Color.FromArgb(200, 60, 60)))
                for r in u.get("rooms", []):
                    add_poly(r["poly"], z, layer(tag + "::Rooms::" + r["kind"], LAYER_COLORS.get(r["kind"], SD.Color.Gray)),
                             inv, "%s %.1fm2" % (r["name"], r["area"]))
                for q in u.get("equipamiento", []):      # artefactos y muebles (contorno y dibujo)
                    lq = layer(tag + "::Equipamiento", LAYER_COLORS["Equipamiento"])
                    add_poly(q["poly"], z, lq, inv, q["name"])
                    for ln in q.get("lines", []):
                        add_poly(ln, z, lq, inv, cerrar=False)
                for s in u.get("sin_uso", []):           # lo que queda sin uso dentro de la vivienda (v2.33)
                    add_poly(s["poly"], z, layer(tag + "::SinUso", LAYER_COLORS["SinUso"]), inv, "Sin uso %.1fm2" % s["area"])
                for w in u.get("ventanas", []):          # ventanas en el muro exterior (hueco y vidrio)
                    lw = layer(tag + "::Ventanas", LAYER_COLORS["Ventanas"])
                    add_poly(w["poly"], z, lw, inv, "Ventana %.2f x %.2f" % (w["ancho"], w["alto"]))
                    for ln in w.get("lines", []):
                        add_poly(ln, z, lw, inv, cerrar=False)
        if viejos and modo == "reemplazar":      # el anterior se borra después: si algo falla, no se pierde
            quedan = borrar(viejos)
            quitar_niveles_sobrantes({"L%02d" % s["index"] for s in stories})
    finally:
        sc.doc.Views.RedrawEnabled = True
        sc.doc.Views.Redraw()
    print("Trazo: recibido: %d objetos principales en capas Trazo::... (niveles %s)." %
          (count, ", ".join("L%02d" % s["index"] for s in stories)))
    if viejos and modo == "reemplazar":
        print("Trazo: reemplacé el resultado anterior (%d objeto(s) borrados)." % (len(viejos) - len(quedan)))
        if quedan:
            print("Trazo: aviso: no pude borrar %d objeto(s) del resultado anterior: bórralos a mano en %s." %
                  (len(quedan), donde(quedan, capas)))
    elif viejos:
        print("Trazo: el resultado anterior sigue en sus capas (elegiste Agregar).")


# ------------------------------------------------------------------ diagnóstico
def diagnostico():
    """Comando de prueba: versión de Rhino, unidades del archivo, capas de Trazo y estado del servidor."""
    so = "Mac" if sys.platform == "darwin" else "Windows" if sys.platform.startswith("win") else sys.platform
    print("Trazo · diagnóstico")
    print("  Rhino %s en %s, Python %s" % (Rhino.RhinoApp.Version, so, sys.version.split()[0]))
    if globals().get("__file__"):
        print("  Script: %s" % __file__)
    print("  Unidades del archivo: %s (1 unidad = %g m), tolerancia %g" %
          (unidades(), meters_per_unit(), sc.doc.ModelAbsoluteTolerance))
    for capa, para in (("Trazo::Centerline", "polilíneas del pasillo"), ("Trazo::Cores", "puntos de núcleos"),
                       ("Trazo::Medianeras", "líneas de medianeras"), ("Trazo::Patios", "curvas cerradas de patios")):
        n = len(rs.ObjectsByLayer(capa) or []) if rs.IsLayer(capa) else None
        print("  Capa %s: %s" % (capa, "no existe (es opcional: %s)" % para if n is None else "%d objeto(s)" % n))
    viejos, capas = resultado_anterior()
    print("  Resultado dibujado en este archivo: %s" % ("%d objeto(s) en %s (Recibir pregunta si reemplazarlo)" %
                                                       (len(viejos), donde(viejos, capas)) if viejos else "ninguno"))
    try:
        version = http("GET", "/api/version", timeout=5).get("version")
        mass = http("GET", "/api/mass", timeout=5)
        res = http("GET", "/api/result", timeout=5)
    except TrazoError as e:
        print("  Servidor: %s" % e)
        print("Diagnóstico: falta arrancar el servidor de Trazo.")
        return
    print("  Servidor: Trazo v%s conectado en %s" % (version, SERVER))
    m = mass.get("mass") or {}
    print("  Masa en el servidor: %s" % ("«%s» (envío nº %s)" % (m.get("name") or "sin nombre", mass.get("version"))
                                         if m else "ninguna todavía (usa Enviar)"))
    r = res.get("result") or {}
    print("  Resultado en el servidor: %s" % ("etapa «%s», %d unidad(es) por planta" % (r.get("stage"), len(r.get("units") or []))
                                              if r else "ninguno todavía (genera uno en la web)"))
    print("Diagnóstico: todo listo para Enviar y Recibir.")


# ------------------------------------------------------------------ menú
def main():
    try:
        opt = rs.GetString("Trazo", "Enviar", ["Enviar", "Recibir", "Diagnostico"])
        if not opt:
            return
        accion = {"enviar": send_mass, "recibir": receive_result,
                  "diagnostico": diagnostico}.get(opt.strip().lower().replace("ó", "o"))
        if accion is None:
            print("Trazo: no conozco la opción «%s»; elige Enviar, Recibir o Diagnostico." % opt)
            return
        accion()
    except TrazoError as e:
        print("Trazo: %s" % e)
    except Exception:
        print("Trazo: error inesperado. Copia todo este mensaje y pégalo en la sesión de Claude Code:")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
