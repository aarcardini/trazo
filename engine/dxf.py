"""Exportador DXF R12 mínimo (POLYLINE cerradas por capa) para importar en Rhino con _Import."""


def _poly(layer, pts, z=0.0, closed=True):
    s = "0\nPOLYLINE\n8\n%s\n66\n1\n70\n%d\n" % (layer, 1 if closed else 0)
    for x, y in pts:
        s += "0\nVERTEX\n8\n%s\n10\n%.4f\n20\n%.4f\n30\n%.4f\n" % (layer, x, y, z)
    return s + "0\nSEQEND\n8\n%s\n" % layer


def result_to_dxf(res):
    out = "0\nSECTION\n2\nENTITIES\n"
    out += _poly("Trazo_Footprint", res["footprint"])
    for p in res.get("patios", []):
        out += _poly("Trazo_Patios", p)
    stories = res.get("stories", [])
    res_stories = [s for s in stories if s["program"] == "Residential"] or stories[:1]
    for s in res_stories:
        z = s["z"]
        tag = "L%02d" % s["index"]
        for c in res.get("corridors", []):
            out += _poly("Trazo_%s_Corridor" % tag, c, z)
        for c in res.get("cores", []):
            out += _poly("Trazo_%s_Cores" % tag, c["poly"], z)
        for u in res.get("units", []):
            out += _poly("Trazo_%s_Units" % tag, u["poly"], z)
            for r in u.get("rooms", []):
                out += _poly("Trazo_%s_Rooms_%s" % (tag, r["kind"]), r["poly"], z)
            for d in u.get("doors", []):
                out += _poly("Trazo_%s_Doors" % tag, [d["p"], d["q"]], z, closed=False)
            for q in u.get("equipamiento", []):
                out += _poly("Trazo_%s_Equipamiento" % tag, q["poly"], z)
                for ln in q.get("lines", []):
                    out += _poly("Trazo_%s_Equipamiento" % tag, ln, z, closed=False)
            for w in u.get("ventanas", []):
                out += _poly("Trazo_%s_Ventanas" % tag, w["poly"], z)
                for ln in w.get("lines", []):
                    out += _poly("Trazo_%s_Ventanas" % tag, ln, z, closed=False)
    return out + "0\nENDSEC\n0\nEOF\n"
