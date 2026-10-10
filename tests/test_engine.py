import sys, os, json
sys.dont_write_bytecode = True   # sin __pycache__: tras revertir un cambio, nunca se prueba bytecode viejo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine.layout import generate

def run(fp, h=15, **p):
    return generate({"footprint": fp, "height": h, "stage": "plans", "params": p})

def test_bar():
    r = run([[0,0],[60,0],[60,16],[0,16]])
    m = r["metrics"]
    print(json.dumps(m, indent=1)); print(r["warnings"])
    assert m["mix"]["count"] >= 8
    assert m["mix"]["match_score"] >= 70
    for u in r["units"]:
        assert u["rooms"], u["id"]
        assert abs(sum(x["area"] for x in u["rooms"]) - u["area"]) < u["area"]*0.12, (u["id"], u["area"], sum(x["area"] for x in u["rooms"]))

def test_L():
    r = run([[0,0],[50,0],[50,14],[16,14],[16,40],[0,40]])
    print(r["metrics"], r["warnings"])
    assert r["units"]

def test_L_serves_most():
    r = run([[0,0],[50,0],[50,14],[16,14],[16,40],[0,40]])
    m = r["metrics"]
    assert m["wings"] == 2 and m["efficiency"] > 55, m
    assert m["egress_max"] <= 30, m
    assert not [w for w in r["warnings"] if "servido" in w], r["warnings"]

def test_U_T_and_diagonal():
    U = [[0,0],[60,0],[60,40],[44,40],[44,16],[16,16],[16,40],[0,40]]
    T = [[0,20],[60,20],[60,36],[38,36],[38,56],[22,56],[22,36],[0,36]]
    for name, fp in (("U", U), ("T", T)):
        r = run(fp)
        print(name, r["metrics"]["wings"], r["metrics"]["efficiency"], r["warnings"][:2])
        assert r["units"], name
    # no ortogonal: debe caer al modo de pasillo único sin romperse
    D = [[0,0],[50,0],[58,12],[8,12]]
    r = run(D); assert r["units"]

if __name__ == "__main__":
    test_bar(); test_L(); test_L_serves_most(); test_U_T_and_diagonal(); print("OK")


def test_polyline_and_manual_cores():
    L = [[0,0],[50,0],[50,14],[16,14],[16,40],[0,40]]
    p = {"centerlines": [[[8,38],[8,7],[46,7]]]}
    r = run(L, **p)
    m = r["metrics"]
    print("polilinea", m["efficiency"], m["unused_area"], m["egress_max"], r["warnings"][:2])
    assert m["wings"] == 2 and m["efficiency"] > 45 and r["units"]
    # núcleos manuales
    r2 = run(L, cores_mode="manual", cores=[[8, 36], [30, 7], [47, 7]], **p)
    assert len(r2["cores"]) == 3 and all(c["spec"] is not None for c in r2["cores"])
    # dos polilíneas en T sobre una barra
    r3 = run([[0,0],[60,0],[60,40],[0,40]], centerlines=[[[0,10],[60,10]],[[30,10],[30,40]]])
    print("T", r3["metrics"]["wings"], r3["metrics"]["efficiency"], r3["warnings"][:2])
    assert r3["units"]

if __name__ == "__main__":
    test_polyline_and_manual_cores(); print("OK2")


def test_unit_plans_graph():
    """Cada unidad tiene hall, estar y los dormitorios de su tipo, y todo se alcanza desde la entrada."""
    r = run([[0,0],[60,0],[60,16],[0,16]])
    assert r["metrics"]["plan_score"] == 100, r["metrics"].get("plan_score")
    for u in r["units"]:
        kinds = [x["kind"] for x in u["rooms"]]
        assert "hall" in kinds and "living" in kinds, (u["id"], kinds)
        assert kinds.count("bedroom") == u["bedrooms"], (u["id"], kinds)
        assert any(d.get("entry") for d in u["doors"]), u["id"]
        assert all(e["ok"] for e in u["graph"]["edges"]), (u["id"], u["graph"]["edges"])
    # monoambiente
    from engine import plans as P
    res = P.layout_unit([(0,0),(6,0),(6,6.5),(0,6.5)], 0)
    assert any(c["ok"] and "alcanzan" in c["msg"] for c in res["checks"]), res["checks"]
    # frente insuficiente: debe avisar
    res = P.layout_unit([(0,0),(6,0),(6,12),(0,12)], 3)
    assert any((not c["ok"]) and "Frente" in c["msg"] for c in res["checks"])

if __name__ == "__main__":
    test_unit_plans_graph(); print("OK3")


def test_programs_and_core():
    from engine import standards as ST
    st = [{"program": "Parking", "height": 3.0}, {"program": "Office", "height": 3.3}] + [{"program": "Residential", "height": 3.0}] * 5
    r = run([[0,0],[72,0],[72,17],[0,17]], h=21.3, stories=st)
    core = r["metrics"]["core"]
    assert core["elevators"] >= 1 and core["risers"] >= 17, core
    kinds = {p["kind"] for p in r["cores"][0]["parts"]}
    assert {"stair", "elevator", "landing"} <= kinds, kinds
    L = r["program_layouts"]
    assert L["Parking"]["count"] >= 30, L["Parking"]["count"]
    off = L["Office"]
    assert off["wc"] >= ST.wc_count(off["workers"] // 2) and off["free_area"] > 500, off
    # inodoros según Dec. 406/988 art. 78
    assert ST.wc_count(15) == 1 and ST.wc_count(16) == 2 and ST.wc_count(100) == 7 and ST.wc_count(120) == 8

if __name__ == "__main__":
    test_programs_and_core(); print("OK4")


def test_medianeras():
    fp = [[0,0],[10,0],[10,28],[0,28]]
    meds = [{"a":[10,0],"b":[10,28],"retiro":0},{"a":[0,28],"b":[0,0],"retiro":0}]
    r = run(fp, medianeras=meds)
    assert r["metrics"].get("between") and len(r["cores"]) == 1, r["metrics"]
    assert all(u["facade"] > 9 for u in r["units"]), [u["facade"] for u in r["units"]]   # vivienda al ancho del predio
    # un dormitorio contra una medianera ciega no cuenta como iluminado
    from engine import plans as P
    blind = lambda p, q: not (abs(p[0]) < 1e-6 and abs(q[0]) < 1e-6) and abs(p[1] - 8) < 1e-6 and abs(q[1] - 8) < 1e-6
    res = P.layout_unit([(0,0),(12,0),(12,8),(0,8)], 2, is_facade=lambda p, q: False)
    assert any("sin fachada" in c["msg"] for c in res["checks"])
    # retiro de 3 m: recorta la huella
    r2 = run(fp, medianeras=[{**meds[0], "retiro": 3}, meds[1]])
    assert abs(r2["metrics"]["plate_area"] - (7 - 0.7) * (28 - 0.7)) < 2, r2["metrics"]["plate_area"]

if __name__ == "__main__":
    test_medianeras(); print("OK5")


def test_no_giant_units():
    """Barra larga con las dos medianeras largas: unidades cerca del m² objetivo, nunca gigantes."""
    fp = [[0,0],[60,0],[60,16],[0,16]]
    meds = [{"a":[0,0],"b":[60,0],"retiro":0},{"a":[60,16],"b":[0,16],"retiro":0}]
    r = run(fp, medianeras=meds)
    assert r["units"] and all(u["area"] < 1.4 * u["target"] for u in r["units"]), [(u["area"], u["target"]) for u in r["units"]]
    assert r.get("dark_zones"), "debe marcar la zona sin luz"

if __name__ == "__main__":
    test_no_giant_units(); print("OK6")


def test_masterplan():
    """Modo Masterplan: damero, T, ochavas, lotes mínimos, construcción y usos de manzana."""
    from engine import masterplan as M, standards as ST
    S = ST.merged(None)["masterplan"]
    predio = [[0,0],[260,0],[260,180],[0,180]]
    streets = M.damero(predio, S)
    r = M.generate({"predio": predio, "streets": streets})
    m = r["metrics"]
    assert m["manzanas"] == 4 and m["lotes"] > 40 and m["lotes_obs"] == 0, m
    assert all(l["frente"] >= S["lote_frente_min"] - 1e-6 and l["area"] >= S["lote_area_min"] for l in r["lots"])
    assert 10 < m["calles_pct"] < 25 and m["ochavas_rest"] > 0, m
    assert all(l.get("building") and l["building"]["fos"] <= S["fos"] + 0.5 for l in r["lots"])
    # dos filas de lotes por manzana (fondo ≈ mitad de la manzana)
    assert max(l["fondo"] for l in r["lots"]) < 45
    # manzana verde: sin lotes y cuenta como cesión
    key = r["blocks"][0]["key"]
    r2 = M.generate({"predio": predio, "streets": streets, "block_uses": {key: "verde"}})
    assert r2["metrics"]["verde"] > 0 and r2["metrics"]["lotes"] < m["lotes"]
    # reserva mínima (Ley 18.308 art. 38): avisa sin verde/equipamiento, no avisa con una manzana verde
    assert any("Reserva" in w for w in r["warnings"]) and not any("Reserva" in w for w in r2["warnings"])
    assert r2["metrics"]["reserva_pct"] >= 10
    assert all(l["block"] != r2["blocks"][0]["id"] for l in r2["lots"])
    # predio irregular con calle en T y bordes inclinados: lotes en dos filas, todos cumplen el mínimo
    d = {"predio": [[0,0],[230,-25],[270,150],[25,195]],
         "streets": [{"pts": [[-10,92],[290,92]]}, {"pts": [[130,92],[134,220]]}], "frontage": [0,1,2,3]}
    r3 = M.generate(d)
    assert r3["metrics"]["manzanas"] == 3 and r3["metrics"]["lotes_obs"] == 0, r3["metrics"]
    assert max(l["fondo"] for l in r3["lots"]) < 60
    # sin frente a calle existente ni calles nuevas: no se lotea y avisa
    r4 = M.generate({"predio": predio, "streets": [], "frontage": []})
    assert r4["metrics"]["lotes"] == 0 and r4["warnings"]

if __name__ == "__main__":
    test_masterplan(); print("OK7")


def test_regresion():
    """Las métricas de los ejemplos de samples/ siguen dentro del margen de sus referencias en tests/golden/ (R0.3)."""
    import regresion
    difs = regresion.comparar()
    assert not difs, regresion.mensaje(difs)

if __name__ == "__main__":
    test_regresion(); print("OK8")


def test_masterplan_samples_manzana():
    """Cada ejemplo del Masterplan trae su manzana (la propia o la estándar): al cambiar de ejemplo no se arrastra la anterior."""
    import server
    from engine import standards as ST
    s = server.mp_samples()
    std = list(ST.DEFAULTS["masterplan"]["manzana"])
    assert s["barrio_jardin"]["masterplan"]["manzana"] == [75, 95], s["barrio_jardin"]
    assert s["predio_rectangular"]["masterplan"]["manzana"] == std, s["predio_rectangular"]
    assert s["predio_irregular"]["masterplan"]["manzana"] == std, s["predio_irregular"]

if __name__ == "__main__":
    test_masterplan_samples_manzana(); print("OK9")


def test_puente_rhino():
    """Script de Rhino con Rhino simulado: mensajes claros, diagnóstico y menú (R1.1). Detalle en tests/test_rhino.py."""
    import test_rhino
    test_rhino.todas()

if __name__ == "__main__":
    test_puente_rhino(); print("OK10")


def test_nuevo_en_blanco():
    """«Nuevo» en la web: /api/reset olvida la masa y el resultado del servidor (Rhino ya no recibe uno viejo)."""
    import threading, urllib.request, urllib.error
    import server
    srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d" % srv.server_address[1]

    def api(path, body=None):
        req = urllib.request.Request(url + path, data=None if body is None else json.dumps(body).encode(),
                                     method="GET" if body is None else "POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    try:
        api("/api/mass", {"name": "Masa vieja", "footprint": [[0, 0], [60, 0], [60, 16], [0, 16]], "height": 15})
        api("/api/generate", {"footprint": [[0, 0], [60, 0], [60, 16], [0, 16]], "height": 15, "stage": "massing"})
        antes = api("/api/mass")["version"]
        assert api("/api/result")["result"]
        assert api("/api/reset", {})["ok"]
        m = api("/api/mass")
        assert m["mass"] is None and m["version"] > antes, m       # la web no vuelve a cargar la masa vieja
        assert api("/api/result")["result"] is None
        try:
            api("/api/dxf")
            raise AssertionError("sin resultado, el DXF debía dar 404")
        except urllib.error.HTTPError as e:
            assert e.code == 404
    finally:
        srv.shutdown()
        srv.server_close()

if __name__ == "__main__":
    test_nuevo_en_blanco(); print("OK11")


def test_web_circulacion_no_vuelve_a_masa():
    """Web: cambiar el modo de núcleos, «Auto» o editar polilíneas y núcleos calcula al menos el pasillo (runCirc).
    Antes, con la masa recién recibida de Rhino, volvía a calcular solo la masa y quedaba la axonometría sin pasillo.
    (La comprobación completa se hizo en navegador; esta prueba evita que vuelva el patrón que causaba el error.)"""
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    assert "run(lastStage)" not in html, "los cambios de pasillo y núcleos deben usar runCirc()"
    for f in ("function finishLine", "function undoLine", "function clearLines", "function coresModeChanged"):
        assert "runCirc()" in html.split(f, 1)[1].split("\nfunction ", 1)[0], f

if __name__ == "__main__":
    test_web_circulacion_no_vuelve_a_masa(); print("OK12")


def test_web_cotas_y_escala():
    """Web: la planta dibuja las cotas totales y la escala gráfica, y la casilla «Cotas» las muestra u oculta.
    (El dibujo se comprobó en navegador; esta prueba evita que se pierda la llamada o la casilla.)"""
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    assert 'id="showDims"' in html and "function drawDims" in html and "function cota(" in html
    cuerpo = html.split("function draw(){", 1)[1].split("\nfunction ", 1)[0]
    assert "drawDims(gb)" in cuerpo, "draw() debe dibujar las cotas"

if __name__ == "__main__":
    test_web_cotas_y_escala(); print("OK13")
