#! python 3
# -*- coding: utf-8 -*-
"""Puente Rhino 8 <-> Trazo.

Ejecuta este archivo en Rhino 8 con el comando:   RunPythonScript   (selecciona este archivo)
o ábrelo en _ScriptEditor y pulsa Run.

  Enviar masa    : toma un sólido cerrado, extrae la huella y la altura y la manda a la web.
  Recibir plano  : dibuja en Rhino lo que generaste en la web (capas Trazo::...).

Requiere que el servidor esté corriendo:  python server.py
"""
import json
import urllib.request

import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System.Drawing as SD

SERVER = "http://127.0.0.1:8765"


# ------------------------------------------------------------------ utilidades
def meters_per_unit():
    return Rhino.RhinoMath.UnitScale(sc.doc.ModelUnitSystem, Rhino.UnitSystem.Meters)


def http(method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(SERVER + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def bottom_outline(brep, tol):
    """Contorno exterior de las caras horizontales inferiores del sólido."""
    bb = brep.GetBoundingBox(True)
    z0 = bb.Min.Z
    loops = []
    for f in brep.Faces:
        u = f.Domain(0).Mid
        v = f.Domain(1).Mid
        n = f.NormalAt(u, v)
        if f.OrientationIsReversed:
            n = -n
        fb = f.GetBoundingBox(True)
        if n.Z < -0.99 and abs(fb.Max.Z - z0) < tol * 10 and abs(fb.Min.Z - z0) < tol * 10:
            c = f.OuterLoop.To3dCurve()
            if c:
                loops.append(c)
    if not loops:
        return None, z0
    joined = Rhino.Geometry.Curve.JoinCurves(loops, tol)
    if not joined:
        return None, z0
    def _area(c):
        if not c.IsClosed:
            return 0.0
        a = Rhino.Geometry.AreaMassProperties.Compute(c)
        return a.Area if a else 0.0
    best = max(joined, key=_area)
    return best, z0


def curve_to_points(curve, tol):
    ok, pl = curve.TryGetPolyline()
    if not ok:
        pc = curve.ToPolyline(tol, 0.01, 0.0, 0.0)
        pl = pc.ToPolyline() if pc else None
    if pl is None:
        return None
    pts = [pl[i] for i in range(pl.Count)]
    if len(pts) > 1 and pts[0].DistanceTo(pts[-1]) < tol:
        pts.pop()
    return pts


# ------------------------------------------------------------------ enviar masa
def send_mass():
    oid = rs.GetObject("Selecciona la masa (sólido cerrado)", rs.filter.polysurface | rs.filter.surface | rs.filter.extrusion)
    if not oid:
        return
    obj = rs.coercebrep(oid)
    if obj is None:
        print("El objeto no es un sólido/polisuperficie.")
        return
    tol = sc.doc.ModelAbsoluteTolerance
    outline, z0 = bottom_outline(obj, tol)
    if outline is None:
        print("No encontré una cara inferior horizontal. Usa una masa tipo extrusión.")
        return
    pts = curve_to_points(outline, tol)
    if not pts:
        print("No pude convertir el contorno a polilínea.")
        return
    k = meters_per_unit()
    bb = obj.GetBoundingBox(True)
    payload = {
        "name": rs.ObjectName(oid) or "Masa de Rhino",
        "height": round((bb.Max.Z - bb.Min.Z) * k, 4),
        "origin_z": bb.Min.Z,
        "footprint": [[p.X * k, p.Y * k] for p in pts],
    }
    # polilíneas centrales opcionales: curvas en la capa Trazo::Centerline (cada vértice cuenta)
    if rs.IsLayer("Trazo::Centerline"):
        lines = []
        for cid in rs.ObjectsByLayer("Trazo::Centerline") or []:
            crv = rs.coercecurve(cid)
            if crv is None:
                continue
            cp = curve_to_points(crv, tol)
            if cp and len(cp) >= 2:
                if not crv.IsClosed:
                    cp = cp + [crv.PointAtEnd] if cp[-1].DistanceTo(crv.PointAtEnd) > tol else cp
                lines.append([[q.X * k, q.Y * k] for q in cp])
        if lines:
            payload["centerlines"] = lines
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
    # núcleos manuales opcionales: objetos punto en la capa Trazo::Cores
    if rs.IsLayer("Trazo::Cores"):
        pts_c = [rs.PointCoordinates(pid) for pid in (rs.ObjectsByLayer("Trazo::Cores") or []) if rs.IsPoint(pid)]
        if pts_c:
            payload["cores"] = [[q.X * k, q.Y * k] for q in pts_c]
    res = http("POST", "/api/mass", payload)
    print("Masa enviada (versión %s): %d vértices, altura %.2f m, %d polilínea(s), %d núcleo(s) manual(es). Abre %s" %
          (res.get("version"), len(pts), payload["height"], len(payload.get("centerlines", [])),
           len(payload.get("cores", [])), SERVER))


# ------------------------------------------------------------------ recibir resultado
LAYER_COLORS = {
    "Footprint": SD.Color.FromArgb(120, 120, 120),
    "Corridor": SD.Color.FromArgb(150, 160, 175),
    "Cores": SD.Color.FromArgb(26, 157, 91),
    "Units": SD.Color.FromArgb(30, 40, 60),
    "bedroom": SD.Color.FromArgb(80, 130, 230),
    "living": SD.Color.FromArgb(230, 170, 50),
    "kitchen": SD.Color.FromArgb(110, 180, 100),
    "bath": SD.Color.FromArgb(60, 170, 200),
}


def layer(name, color):
    full = "Trazo::" + name
    if not rs.IsLayer(full):
        rs.AddLayer(full, color)
    return full


def add_poly(points, z, lyr, k, name=None):
    pl = Rhino.Geometry.Polyline()
    for x, y in points:
        pl.Add(x / k, y / k, z)
    pl.Add(pl[0])
    guid = sc.doc.Objects.AddPolyline(pl)
    if guid:
        rs.ObjectLayer(guid, lyr)
        if name:
            rs.ObjectName(guid, name)
    return guid


def receive_result():
    data = http("GET", "/api/result")
    res = data.get("result")
    if not res:
        print("Todavía no hay un resultado. Genera uno en la web primero.")
        return
    k = meters_per_unit()          # unidades de Rhino -> metros
    inv = k                        # metros / (metros por unidad) = unidades
    z_origin = 0.0
    mass = http("GET", "/api/mass").get("mass") or {}
    z_origin = mass.get("origin_z", 0.0)
    sc.doc.Views.RedrawEnabled = False
    count = 0
    add_poly(res["footprint"], z_origin, layer("Footprint", LAYER_COLORS["Footprint"]), inv)
    stories = [s for s in res["stories"] if s["program"] == "Residential"] or res["stories"][:1]
    for s in stories:
        z = z_origin + s["z"] / k
        tag = "L%02d" % s["index"]
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
    sc.doc.Views.RedrawEnabled = True
    sc.doc.Views.Redraw()
    print("Importado: %d objetos principales en capas Trazo::..." % count)


# ------------------------------------------------------------------ menú
def main():
    try:
        http("GET", "/api/mass")
    except Exception as e:
        print("No puedo conectar con %s. ¿Está corriendo 'python server.py'? (%s)" % (SERVER, e))
        return
    opt = rs.GetString("Trazo", "Enviar", ["Enviar", "Recibir"])
    if opt == "Enviar":
        send_mass()
    elif opt == "Recibir":
        receive_result()


if __name__ == "__main__":
    main()
