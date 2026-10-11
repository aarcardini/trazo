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
    """Barra larga con las dos medianeras largas y sin patios: unidades cerca del m² objetivo, nunca gigantes."""
    fp = [[0,0],[60,0],[60,16],[0,16]]
    meds = [{"a":[0,0],"b":[60,0],"retiro":0},{"a":[60,16],"b":[0,16],"retiro":0}]
    r = run(fp, medianeras=meds, patios_mode="manual")       # sin patios (en automático se abren patios)
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


def test_patios():
    """Patios (v2.4): automáticos en predios entre medianeras profundos, y manuales; cada bloque con su núcleo."""
    from engine import geometry as G
    meds = lambda w, d: [{"a":[w,0],"b":[w,d],"retiro":0},{"a":[0,d],"b":[0,0],"retiro":0}]
    # el ejemplo pedido: lote 10 × 40 entre medianeras -> bloque al frente y al fondo, patio de 3 m, un núcleo en cada uno
    fp = [[0,0],[10,0],[10,40],[0,40]]
    r = run(fp, medianeras=meds(10, 40))
    m = r["metrics"]
    assert m["blocks"] == 2 and len(r["patios"]) == 1 and not r.get("dark_zones"), m
    assert abs(m["patio_area"] - 30) < 0.5 and m["gfa"] < 400 * m["stories"], m      # 10 × 3 m, que no se construye
    for b in r["blocks"]:
        assert sum(G.point_in_poly(c["center"], b["footprint"]) for c in r["cores"]) == 1, "un núcleo por bloque"
        assert any(G.point_in_poly(G.centroid(u["poly"]), b["footprint"]) for u in r["units"]), "viviendas en cada bloque"
    assert not [c for u in r["units"] for c in u["checks"] if not c["ok"] and "sin fachada" in c["msg"]], \
        "las viviendas que dan al patio tienen luz"
    assert run(fp, medianeras=meds(10, 40), patios_mode="manual").get("dark_zones"), "sin patios vuelve la zona sin luz"
    # el lote de 10 × 28 no es tan profundo: sigue sin patio
    assert not run([[0,0],[10,0],[10,28],[0,28]], medianeras=meds(10, 28))["patios"]
    # 16 × 60: tres bloques con su núcleo y planos sin observaciones
    r = run([[0,0],[60,0],[60,16],[0,16]], h=18, medianeras=[{"a":[0,0],"b":[60,0],"retiro":0},{"a":[60,16],"b":[0,16],"retiro":0}])
    assert r["metrics"]["blocks"] == 3 and r["metrics"]["core_count"] == 3 and r["metrics"]["plan_score"] == 100, r["metrics"]
    # patio manual angosto (2 m): avisa y sus caras no iluminan
    r = run(fp, medianeras=meds(10, 40), patios_mode="manual", patios=[[[-1,19],[11,19],[11,21],[-1,21]]])
    assert any("no ilumina" in w for w in r["warnings"]), r["warnings"]
    assert any("sin fachada" in c["msg"] for u in r["units"] for c in u["checks"] if not c["ok"])
    # patio manual que parte una barra, con núcleos manuales: cada núcleo va a su bloque y conserva su índice
    r = run([[0,0],[60,0],[60,16],[0,16]], patios_mode="manual", patios=[[[28,-1],[32,-1],[32,17],[28,17]]],
            cores_mode="manual", cores=[[50, 8], [10, 8]])
    assert r["metrics"]["blocks"] == 2 and sorted(c["spec"] for c in r["cores"]) == [0, 1], r["cores"]
    # patio interior girado respecto de la masa: todavía no se resuelve; avisa y no se usa (ver test_patios_interiores)
    r = run([[0,0],[40,0],[40,40],[0,40]], patios_mode="manual", patios=[[[20,14],[26,20],[20,26],[14,20]]])
    assert any("rodeado de edificio" in w for w in r["warnings"]) and not r["patios"]
    # geometría: banda que parte, muesca (U), patio no convexo
    R = lambda x0, y0, x1, y1: [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    assert [round(G.area(o)) for o, _ in G.subtract(R(0, 0, 10, 40), [R(-1, 18, 11, 21)])[0]] == [190, 180]
    (u, h), = G.subtract(R(0, 0, 12, 30), [R(9, 10, 13, 18)])[0]
    assert len(u) == 8 and not h and round(G.area(u)) == 336
    (l, _), = G.subtract(R(0, 0, 20, 30), [[(-1, 10), (12, 10), (12, 14), (8, 14), (8, 21), (-1, 21)]])[0]
    assert round(G.area(l)) == 496

if __name__ == "__main__":
    test_patios(); print("OK14")


def test_patios_interiores():
    """Patios rodeados de edificio (v2.6, R1.3): el bloque es un anillo dividido en alas alrededor del patio, con un
    pasillo que da la vuelta, viviendas con luz hacia el patio y solo los núcleos que pide la evacuación."""
    import math
    from engine import geometry as G
    from engine import layout as L
    R = lambda x0, y0, x1, y1: [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    sin_fachada = lambda r: [c for u in r["units"] for c in u["checks"] if not c["ok"] and "sin fachada" in c["msg"]]
    # 40 × 30 con patio central de 14 × 8 (ejemplo «patio_central»): cuatro alas, dos núcleos, todo con luz
    r = run(R(0, 0, 40, 30), patios_mode="manual", patios=[R(13, 11, 27, 19)])
    m = r["metrics"]
    assert m["blocks"] == 1 and m["wings"] == 4 and m["core_count"] == 2, m
    assert abs(m["patio_area"] - 112) < 0.5 and abs(m["gfa"] - (1200 - 112) * m["stories"]) < 1, m
    b, = r["blocks"]
    assert len(b["holes"]) == 1 and len(b["plate_holes"]) == 1, b
    patio = r["patios"][0]
    assert not any(G.point_in_poly(G.centroid(u["poly"]), patio) for u in r["units"]), "nada dentro del patio"
    # (v2.33: las dos viviendas de 10 m de fondo avisan lo que les queda sin uso junto al pasillo común)
    assert not sin_fachada(r) and m["egress_max"] <= 30 and m["efficiency"] > 65 and m["plan_score"] >= 80, m
    for lado in ((13, 15), (27, 15), (20, 11), (20, 19)):     # el pasillo da la vuelta: bordea los cuatro lados
        assert min(L._dist_to_boundary(lado, c) for c in r["corridors"]) < 1.0, lado
    # la misma masa girada y en coordenadas UTM (como llega de un plano georreferenciado) da lo mismo:
    # el centro de un polígono ya no pierde precisión con coordenadas grandes (antes el patio no se reconocía)
    ang, o = 0.5, (580000.0, 6140000.0)
    utm = lambda pl: [[o[0] + x * math.cos(ang) - y * math.sin(ang), o[1] + x * math.sin(ang) + y * math.cos(ang)] for x, y in pl]
    ru = run(utm(R(0, 0, 40, 30)), patios_mode="manual", patios=[utm(R(13, 11, 27, 19))])
    mu = ru["metrics"]
    assert (mu["blocks"], mu["wings"], mu["core_count"], len(ru["units"])) == (1, 4, 2, len(r["units"])), mu
    assert abs(mu["efficiency"] - m["efficiency"]) < 0.5 and abs(mu["patio_area"] - 112) < 0.5, mu
    c, e = G.centroid(utm(R(0.35, 0.35, 19.2, 4.13))), utm([[9.775, 2.24]])[0]       # antes: 5 m de error
    assert math.hypot(c[0] - e[0], c[1] - e[1]) < 1e-6 and abs(G.area(utm(R(0.35, 0.35, 19.2, 4.13))) - 71.253) < 1e-3, c
    # entre medianeras 30 × 45 con patio de 12 × 17 (U cerrada): viviendas a los cuatro lados del patio, con luz
    meds = [{"a": [30, 0], "b": [30, 45], "retiro": 0}, {"a": [0, 45], "b": [0, 0], "retiro": 0}]
    r = run(R(0, 0, 30, 45), medianeras=meds, patios_mode="manual", patios=[R(9, 14, 21, 31)])
    m = r["metrics"]
    fallas = {c["msg"] for u in r["units"] for c in u["checks"] if not c.get("ok") and not c.get("info")}
    assert m["core_count"] == 2 and not m.get("between"), m
    assert fallas <= {"Sin cocina: toda vivienda lleva una (norma nacional, art. 21)"}, fallas   # luz y medidas, bien
    assert not any("Zona central" in w for w in r["warnings"]), r["warnings"]     # las esquinas sin luz sí se marcan
    medios = lambda pl: [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(pl, pl[1:] + pl[:1])]
    al_patio = [u for u in r["units"] if min(L._dist_to_boundary(p, R(9, 14, 21, 31)) for p in medios(u["poly"])) < 0.6]
    lados = {("O" if G.centroid(u["poly"])[0] < 9 else "E" if G.centroid(u["poly"])[0] > 21 else
              "S" if G.centroid(u["poly"])[1] < 14 else "N") for u in al_patio}
    assert lados == {"N", "S", "E", "O"}, lados
    # claustro de alas profundas (40 × 40, patio 10 × 10): las esquinas interiores no llevan viviendas a oscuras
    r = run(R(0, 0, 40, 40), patios_mode="manual", patios=[R(15, 15, 25, 25)])
    assert r["units"] and not sin_fachada(r) and r["metrics"]["core_count"] == 2, r["metrics"]
    # alas de menos de 5 m alrededor del patio: avisa y no lo usa; un patio en L en una masa ortogonal sí se usa
    r = run(R(0, 0, 20, 14), patios_mode="manual", patios=[R(3, 3, 17, 11)])
    assert any("menos de 5 m" in w for w in r["warnings"]) and not r["patios"], r["warnings"]
    r = run(R(0, 0, 50, 40), patios_mode="manual", patios=[[[15, 12], [35, 12], [35, 18], [21, 18], [21, 28], [15, 28]]])
    assert r["metrics"]["blocks"] == 1 and r["units"] and not any("Patio" in w for w in r["warnings"]), r["warnings"]
    # patio interior angosto (2 m): avisa y sus caras cuentan como medianera
    r = run(R(0, 0, 40, 30), patios_mode="manual", patios=[R(19, 11, 21, 19)])
    assert any("no ilumina" in w for w in r["warnings"]) and sin_fachada(r), r["warnings"]
    # núcleos manuales en el anillo: quedan donde se pidieron; las polilíneas no se usan y lo avisa
    r = run(R(0, 0, 40, 30), patios_mode="manual", patios=[R(13, 11, 27, 19)], cores_mode="manual",
            cores=[[13, 5], [27, 25]], centerlines=[[[0, 5], [40, 5]]])
    assert sorted(c["spec"] for c in r["cores"]) == [0, 1] and len(r["cores"]) == 2, r["cores"]
    assert any("polilíneas" in w for w in r["warnings"]) and r["units"], r["warnings"]

if __name__ == "__main__":
    test_patios_interiores(); print("OK15")


def test_modulos():
    """R2.1: el motor está repartido en módulos (massing, circulation, units, patios); layout reexporta sus funciones
    y el servidor los recarga en orden cuando cambia un archivo (sin reiniciar)."""
    import server
    from engine import layout, massing, circulation, units, patios
    assert layout.decompose_wings is massing.decompose_wings and layout.split_blocks is patios.split_blocks
    assert layout.generate_circulation is circulation.generate_circulation and layout.unit_rooms is units.unit_rooms
    server._loaded[0] = 0                                  # como si hubiera cambiado un archivo del motor
    lay, _ = server.engine()
    r = lay.generate({"footprint": [[0, 0], [60, 0], [60, 16], [0, 16]], "height": 15, "stage": "plans"})
    assert len(r["units"]) == 8 and lay.split_blocks is patios.split_blocks, len(r["units"])

if __name__ == "__main__":
    test_modulos(); print("OK16")


def test_geometria_robusta():
    """R2.2: un recorte que separa una figura cóncava da varias partes: sin puentes de ancho cero entre ellas (antes
    Sutherland-Hodgman las dejaba unidas: viviendas, pasillos y manzanas con forma de dos piezas)."""
    from engine import geometry as G, masterplan as MP, standards as ST
    U = [(0, 0), (30, 0), (30, 20), (20, 20), (20, 8), (10, 8), (10, 20), (0, 20)]
    assert len(G.union_parts([G.clip_rect(U, None, None, 10, None)])) == 2       # el recorte de siempre: con puente
    partes = G.clip_rect_parts(U, None, None, 10, None)
    assert len(partes) == 2 and sorted(round(abs(G.area(p))) for p in partes) == [100, 100], partes
    assert len(G.clip_halfplane_parts(U, 0, 1, 10)) == 2 and round(abs(G.area(G.largest_part(partes[0])))) == 100
    assert G.clip_rect_parts(U, None, None, None, 5) == [G.clip_rect(U, None, None, None, 5)]   # una parte: igual
    una = lambda p: len(G.split_parts(p)) == 1
    # masa con una muesca en V y un pasillo dibujado que la cruza: el pasillo queda en dos partes, viviendas enteras
    fp = [[0, 0], [75.21, 0], [75.21, 32.37], [55.71, 32.37], [48.26, 4.62], [40.81, 32.37], [0, 32.37]]
    r = run(fp, centerlines=[[[1, 9.71], [74.21, 9.71]]])
    assert r["units"] and all(una(u["poly"]) for u in r["units"]) and all(una(c) for c in r["corridors"])
    # predio en C con damero: cada manzana y cada lote es una sola figura
    pr = [[0, 0], [267.27, 0], [267.27, 59.79], [80.18, 59.79], [80.18, 139.52], [267.27, 139.52], [267.27, 199.31],
          [0, 199.31]]
    m = MP.generate({"predio": pr, "streets": MP.damero(pr, ST.merged(None)["masterplan"])})
    assert all(una(b["poly"]) for b in m["blocks"]) and all(una(l["poly"]) for l in m["lots"]), len(m["blocks"])

if __name__ == "__main__":
    test_geometria_robusta(); print("OK17")


def test_sin_restos():
    """R3.1: un pasillo dibujado que termina antes de la fachada ya no deja una franja suelta entre el núcleo de la
    punta y el borde: el núcleo se apoya contra la fachada y la vivienda del otro lado crece (sin pasar la evacuación)."""
    from engine import geometry as G
    from engine import layout as L
    r = run([[0, 0], [60, 0], [60, 16], [0, 16]], centerlines=[[[3, 8], [57.5, 8]]])
    for arriba in (True, False):                   # a cada lado del pasillo, viviendas y núcleos de fachada a fachada
        bb = [G.bbox(p) for p in [u["poly"] for u in r["units"]] + [c["poly"] for c in r["cores"]]]
        bb = [b for b in bb if (b[1] + b[3]) / 2 > 8] if arriba else [b for b in bb if (b[1] + b[3]) / 2 < 8]
        assert min(b[0] for b in bb) < 0.4 and max(b[2] for b in bb) > 59.6, bb
    m, m0 = r["metrics"], run([[0, 0], [60, 0], [60, 16], [0, 16]])["metrics"]
    assert m["efficiency"] >= m0["efficiency"] - 0.1 and m["egress_max"] <= L.DEFAULT_PARAMS["egress_multi"], (m, m0)
    # el ejemplo «L con polilínea»: de 49,6 a menos de 25 m² sin usar
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "L_polilinea.json"), encoding="utf-8"))
    m = run(s["footprint"], centerlines=s["centerlines"])["metrics"]
    assert m["unused_area"] < 25 and m["efficiency"] > 72, m
    # si detrás del núcleo hay un bolsillo, la franja y el bolsillo ya forman una vivienda: el núcleo no se mueve
    fp = [[0, 0], [21.21, 0], [21.21, 23.5], [14.85, 23.5], [14.85, 9.4], [6.36, 9.4], [6.36, 23.5], [0, 23.5]]
    r = run(fp, h=6, centerlines=[[[1.06, 7.05], [19.09, 7.05]]],
            medianeras=[{"a": [21.21, 0], "b": [21.21, 23.5], "retiro": 3}, {"a": [0, 23.5], "b": [0, 0], "retiro": 0}])
    assert sorted(round(u["area"]) for u in r["units"]) == [36, 76, 88], [round(u["area"]) for u in r["units"]]

if __name__ == "__main__":
    test_sin_restos(); print("OK18")


def test_codos():
    """R3.2: en el codo de una L el núcleo va a la esquina interior, que no tiene luz, y la esquina exterior queda para
    las viviendas; ninguna vivienda queda con estancias a oscuras y lo que no recibe luz se marca «Sin luz natural»."""
    from engine import geometry as G, plans as P
    oscuras = lambda r: [u["id"] for u in r["units"] if any(not c["ok"] and "sin fachada" in c["msg"] for c in u["checks"])]
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "L.json"), encoding="utf-8"))
    r = run(s["footprint"])
    m = r["metrics"]
    assert not oscuras(r) and m["unused_area"] < 1 and m["efficiency"] >= 71.5 and m["egress_max"] <= 18, m
    assert any(8 < c["center"][0] < 16 and 7 < c["center"][1] < 14 for c in r["cores"]), [c["center"] for c in r["cores"]]
    # U y T: ninguna vivienda a oscuras; las esquinas sin luz se marcan y se avisan (con núcleos de 2 ascensores, que no
    # entran en la esquina interior)
    U = [[0, 0], [60, 0], [60, 45], [44, 45], [44, 16], [16, 16], [16, 45], [0, 45]]
    for fp in (U, [[0, 0], [70, 0], [70, 16], [43, 16], [43, 45], [27, 45], [27, 16], [0, 16]]):
        r = run(fp, ascensores="2")
        assert r["units"] and not oscuras(r) and r["metrics"].get("dark_area", 0) > 10, r["metrics"]
        assert any("Esquinas sin luz" in w for w in r["warnings"]), r["warnings"]
    # con un ascensor por núcleo (R10.7), en la U los núcleos entran en las dos esquinas interiores: no queda esquina a
    # oscuras y entran más viviendas
    r = run(U)
    assert r["units"] and not oscuras(r) and not r["metrics"].get("dark_area"), r["metrics"]
    assert all(c["ascensores"] == 1 for c in r["cores"]) and len(r["units"]) > len(run(U, ascensores="2")["units"])
    # un lote en trapecio con medianeras en los lados largos no se vacía: contra una medianera no se bloquea
    fp = [[0, 0], [47.5, 20.1], [15.2, 70.1], [-18.1, 56.0]]
    r = run(fp, h=6, medianeras=[{"a": fp[1], "b": fp[2], "retiro": 0}, {"a": fp[3], "b": fp[0], "retiro": 0}])
    assert len(r["units"]) > 4, len(r["units"])
    # el plano de una vivienda con parte del fondo sin luz: estancias habitables con luz y el resto (v2.33: si pasa de
    # un depósito de 4 m²), sin uso y con aviso
    res = P.layout_unit([(0, 0), (12, 0), (12, 8), (0, 8)], 2, lambda p, q: min(p[0], q[0]) >= 3.0)
    assert min(G.bbox(rm["poly"])[0] for rm in res["rooms"]) >= 2.95, [(rm["name"], G.bbox(rm["poly"])) for rm in res["rooms"]]
    assert len(res["sin_uso"]) == 1 and G.bbox(res["sin_uso"][0])[2] <= 3.05 and abs(G.area(res["sin_uso"][0])) > 20
    assert any(not c["ok"] and c["msg"].startswith("Sin uso: 24.0 m² sin luz natural") for c in res["checks"]), res["checks"]
    assert not [c for c in res["checks"] if not c["ok"] and "sin fachada" in c["msg"]], res["checks"]

if __name__ == "__main__":
    test_codos(); print("OK19")


def test_cruces():
    """R3.3: pasillos dibujados sin solapes. Dos líneas que se cruzan en X, una T que pasa de largo, el codo de una
    polilínea en una planta ancha, una U de ramas cercanas, tres líneas por un mismo punto y una línea corta que cruza
    otra: ninguna vivienda pisa a otra, a un pasillo o a un núcleo, y los núcleos no se pisan entre sí."""
    from engine import geometry as G, circulation as C, layout as LY
    caja = lambda p: G.bbox([tuple(q) for q in p])
    toca = lambda a, b: a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
    pisa = lambda a, b: sum(abs(G.area(o)) for o in G.subtract(a, [b])[1][0]) if toca(caja(a), caja(b)) else 0.0

    def solapes(r):
        us, cs = [u["poly"] for u in r["units"]], [c["poly"] for c in r["cores"]]
        return (round(sum(pisa(a, b) for i, a in enumerate(us) for b in us[i + 1:]), 1),
                round(sum(pisa(a, b) for a in us for b in r["corridors"] + cs), 1),
                round(sum(pisa(a, b) for i, a in enumerate(cs) for b in cs[i + 1:]), 1))
    # planta en cruz con dos líneas que se cruzan en el centro: viviendas en las cuatro alas, sin solapes
    cruz = [[20, 0], [36, 0], [36, 20], [56, 20], [56, 36], [36, 36], [36, 56], [20, 56], [20, 36], [0, 36], [0, 20],
            [20, 20]]
    lineas = [[[28, 1], [28, 55]], [[1, 28], [55, 28]]]
    r = run(cruz, centerlines=lineas)
    assert solapes(r) == (0, 0, 0), solapes(r)
    cen = [G.centroid([tuple(q) for q in u["poly"]]) for u in r["units"]]
    for ala in (lambda p: p[0] < 20, lambda p: p[0] > 36, lambda p: p[1] < 20, lambda p: p[1] > 36):
        assert any(ala(p) for p in cen), cen
    # la otra línea se corta en el cruce: cada mitad se une a la que sigue de largo, en los dos sentidos
    pcs = C.build_user_pieces(cruz, LY.merge_params({"centerlines": lineas}))
    assert len(pcs) == 3 and sum(1 for j in pcs[0]["junctions"] if j.get("llega")) == 2, \
        [(len(pcs), pc["junctions"]) for pc in pcs]
    # una T que pasa 2 m del otro lado es la misma T: sin un resto de pasillo del otro lado
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "T_dos_lineas.json"), encoding="utf-8"))
    r1 = run(s["footprint"], centerlines=s["centerlines"])
    r2 = run(s["footprint"], centerlines=[s["centerlines"][0], [[30, 8], [30, 48]]])
    assert [u["poly"] for u in r1["units"]] == [u["poly"] for u in r2["units"]]
    assert min(caja(c)[1] for c in r2["corridors"]) >= 9 - 0.01, [caja(c) for c in r2["corridors"]]
    # codo de una polilínea en una L ancha, U de ramas cercanas, tres líneas por un punto, línea corta que cruza
    casos = [([[0, 0], [70, 0], [70, 20], [20, 20], [20, 60], [0, 60]], [[[10, 58], [10, 10], [68, 10]]]),
             ([[0, 0], [40, 0], [40, 40], [0, 40]], [[[10, 1], [10, 24], [30, 24], [30, 1]]]),
             ([[0, 0], [83.5, 0], [83.5, 35.6], [0, 35.6]], [[[20.9, 1], [20.9, 21.3], [62.6, 21.3], [62.6, 1]],
                                                             [[1, 10.7], [82.5, 10.7]]]),
             ([[0, 0], [60, 0], [60, 60], [0, 60]], [[[1, 30], [59, 30]], [[30, 1], [30, 59]], [[3, 3], [57, 57]]]),
             ([[0, 0], [77, 0], [77, 17], [18.8, 17], [18.8, 68.4], [0, 68.4]],
              [[[9.4, 67.4], [9.4, 8], [76, 8]], [[47.8, 1], [47.8, 15]]])]
    for fp, ls in casos:
        r = run(fp, centerlines=ls)
        assert r["units"] and solapes(r) == (0, 0, 0), (ls, solapes(r))
    # en el codo y en la U, ya las franjas de viviendas de cada tramo se reparten la planta (sin recortes al final)
    params = LY.merge_params({})
    c = params["corridor_width"] / 2 + params["party_wall"] / 2
    for fp, ls in casos[:2]:
        pcs = C.build_user_pieces(fp, LY.merge_params({"centerlines": ls}))
        fr = [G.to_world(G.clip_rect(pc["side_region"][sd], None, None, c, None) if sd > 0 else
                         G.clip_rect(pc["side_region"][sd], None, None, None, -c), pc["origin"], pc["angle"])
              for pc in pcs for sd in (1, -1) if pc["side_region"].get(sd)]
        assert sum(pisa(a, b) for i, a in enumerate(fr) for b in fr[i + 1:] if a and b) < 0.5, ls
    # cruce oblicuo: el pasillo que llega solo bloquea la franja de viviendas que atraviesa, no toda su proyección
    fp, ls = [[0, 0], [70, 0], [70, 50], [0, 50]], [[[2, 25], [68, 25]], [[15, 2], [60, 47]]]
    r = run(fp, centerlines=ls)
    assert solapes(r) == (0, 0, 0), solapes(r)
    pcs = C.build_user_pieces(fp, LY.merge_params({"centerlines": ls}))
    assert all(b - a < 20 for sd in (1, -1) for a, b in pcs[0]["extra_blocks"][sd]), pcs[0]["extra_blocks"]
    # tres líneas por un punto: las otras dos se unen a la que pasa de largo (la diagonal), no entre sí
    pcs = C.build_user_pieces(casos[3][0], LY.merge_params({"centerlines": casos[3][1]}))
    tronco = [pc for pc in pcs if pc["free"] == [True, True]]
    assert len(tronco) == 1 and sum(1 for j in tronco[0]["junctions"] if j.get("llega")) == 4, \
        [(pc["free"], pc["junctions"]) for pc in pcs]
    # el bolsillo detrás de un núcleo no se suma a la vivienda vecina si ahí llega otro pasillo
    from engine import units as UN
    rect = [(0, -15), (30, -15), (30, 15), (0, 15)]
    circ = {"side_region": {1: rect, -1: rect}, "cores": [{"side": 1, "box": (10, -1, 15, 6)}],
            "extra_blocks": {1: [(12, 14)], -1: []}, "loc_plate": rect, "xa": 0, "xb": 30}
    segs = UN._segments(rect, circ, {"corridor_width": 2.0, "party_wall": 0.3})
    assert all(G.bbox(sg["region"])[2] <= 10.05 or G.bbox(sg["region"])[0] >= 14.95 for sg in segs if sg["side"] > 0), \
        [G.bbox(sg["region"]) for sg in segs]

if __name__ == "__main__":
    test_cruces(); print("OK20")


def test_lavadero():
    """Corrección (v2.11): un lavadero de 0,90 m (el mínimo para su puerta) quedaba «sin acceso» cuando el cálculo daba
    0,8999… m, según dónde estuviera la vivienda: 1 de cada 10 viviendas con puntaje 0 sin motivo."""
    from engine import plans as P
    for x0 in (0.0, 9.95, 14.39):
        res = P.layout_unit([(x0, 0), (x0 + 9.15, 0), (x0 + 9.15, 8.5), (x0, 8.5)], 2, None, P.V)
        assert not [c for c in res["checks"] if not c["ok"]], (x0, [c["msg"] for c in res["checks"] if not c["ok"]])
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "T_dos_lineas.json"), encoding="utf-8"))
    # con núcleos de 2 ascensores, como cuando se escribió la prueba: con 1 (R10.7) entran 2 viviendas más por planta y
    # el mix arma viviendas de 3 dormitorios de menos frente, que bajan la calidad por sus dormitorios, no por el lavadero
    for asc in ("2", "auto"):
        r = run(s["footprint"], centerlines=s["centerlines"], ascensores=asc)
        assert not [u["id"] for u in r["units"] if any("Lavadero" in c["msg"] and not c["ok"] for c in u["checks"])]
    # (v2.33: la vivienda de 3 dormitorios de 114 m² avisa la franja sin luz que le sobra aun con suite y baños grandes)
    assert run(s["footprint"], centerlines=s["centerlines"], ascensores="2")["metrics"]["plan_score"] >= 55

if __name__ == "__main__":
    test_lavadero(); print("OK21")


def test_no_ortogonales():
    """R3.4: una planta no ortogonal se divide en alas, cada una con su propio eje: una barra con quiebre, una L con
    ochava, el tallo oblicuo de una T. Las plantas convexas (un trapecio) siguen con un solo pasillo y una estrella no
    se parte en puntas."""
    import math
    from engine import geometry as G, circulation as C, layout as LY, massing as M
    caja = lambda p: G.bbox([tuple(q) for q in p])
    toca = lambda a, b: a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
    pisa = lambda a, b: sum(abs(G.area(o)) for o in G.subtract(a, [b])[1][0]) if toca(caja(a), caja(b)) else 0.0
    oscuras = lambda r: [u["id"] for u in r["units"] if any(not c["ok"] and "sin fachada" in c["msg"] for c in u["checks"])]
    muestra = lambda n: json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", n), encoding="utf-8"))
    for nombre, efic in (("quiebre_45.json", 72), ("L_ochava.json", 70)):
        s = muestra(nombre)
        r = run(s["footprint"])
        m = r["metrics"]
        assert m["wings"] == 2 and m["efficiency"] >= efic and not oscuras(r), (nombre, m["wings"], m["efficiency"], oscuras(r))
        assert not [w for w in r["warnings"] if "servido" in w], r["warnings"]
        sol = sum(pisa(u["poly"], o) for u in r["units"] for o in r["corridors"] + [c["poly"] for c in r["cores"]])
        assert sol < 0.05, (nombre, sol)
        areas = [abs(G.area([tuple(p) for p in c["poly"]])) for c in r["cores"]]
        assert min(areas) >= 0.9 * max(areas), (nombre, areas)          # núcleos enteros, no recortados por el inglete
    # la planta real (con el muro descontado) también da dos alas: sin escalones de redondeo al girarla
    import random
    azar = random.Random(3)
    for _ in range(60):                                  # quiebres al azar, girados y en coordenadas UTM
        a, w, t = azar.uniform(20, 70), azar.uniform(13, 20), azar.uniform(0, 3)
        h = w / 2 * math.tan(math.radians(a) / 2)
        e = (math.cos(math.radians(a)), math.sin(math.radians(a)))
        L1, L2 = azar.uniform(25, 50), azar.uniform(25, 50)
        q = [[0, -w / 2], [L1 + h, -w / 2], [L1 + L2 * e[0] + w / 2 * e[1], L2 * e[1] - w / 2 * e[0]],
             [L1 + L2 * e[0] - w / 2 * e[1], L2 * e[1] + w / 2 * e[0]], [L1 - h, w / 2], [0, w / 2]]
        o = azar.choice([(0, 0), (580000.0, 6140000.0)])
        q = [[o[0] + x * math.cos(t) - y * math.sin(t), o[1] + x * math.sin(t) + y * math.cos(t)] for x, y in q]
        plate = run(q, h=3)["blocks"][0]["plate"]
        alas = M.descomponer_alas(plate)
        assert alas and len(alas) == 2 and sum(abs(G.area(p)) for p, _ in alas) >= 0.99 * abs(G.area(plate)), (q, alas)
    # T con el tallo a 60°: el pasillo del tallo va a lo largo del tallo
    t = math.radians(60)
    fp = [[0, 0], [60, 0], [60, 16], [38, 16], [38 - 30 * math.cos(t), 16 + 30 * math.sin(t)],
          [38 - 30 * math.cos(t) - 16 / math.sin(t), 16 + 30 * math.sin(t)], [38 - 16 / math.sin(t), 16], [0, 16]]
    pcs = C.build_pieces(fp, LY.merge_params({}))
    angs = sorted(round(math.degrees(pc["angle"]) % 180) for pc in pcs)
    assert angs == [0, 120], angs
    r = run(fp)
    assert r["metrics"]["efficiency"] > 60 and not oscuras(r), (r["metrics"]["efficiency"], oscuras(r))
    sol = sum(pisa(u["poly"], o) for u in r["units"] for o in r["corridors"] + [c["poly"] for c in r["cores"]])
    assert sol < 0.05, sol                               # el conector oblicuo no pasa del otro borde del pasillo
    # convexas: un solo pasillo, como antes; una estrella no se parte en puntas
    for fp in ([[0, 0], [60, 0], [52, 18], [6, 18]], [[0, 0], [50, 5], [45, 40], [15, 32], [-5, 20]],
               [[0, 0], [60, 4], [54, 40], [18, 32], [-6, 20]]):
        assert run(fp)["metrics"]["wings"] == 1, fp
    estrella = [[(30 if k % 2 == 0 else 14) * math.cos(k * math.pi / 10), (30 if k % 2 == 0 else 14) * math.sin(k * math.pi / 10)]
                for k in range(20)]
    assert M.descomponer_alas(estrella) is None
    aleta = [[0, 0], [60, 0], [60, 16], [40, 16], [30, 31], [20, 16], [0, 16]]       # barra con una punta en triángulo
    assert len(M.descomponer_alas(aleta) or []) <= 1, M.descomponer_alas(aleta)       # la punta no es un ala
    # web: las cotas van en la dirección del rectángulo más chico que contiene la planta, no en la de un ala girada
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    cuerpo = html.split("function domAngle(poly){", 1)[1].split("\nfunction ", 1)[0]
    assert "Math.max(...xs)-Math.min(...xs)" in cuerpo and "Math.max(...ys)-Math.min(...ys)" in cuerpo, cuerpo[:200]

if __name__ == "__main__":
    test_no_ortogonales(); print("OK22")


def test_nucleos_editables():
    """R3.5: un núcleo manual puede tener medidas propias y girar 90° (la escalera sube a lo largo del pasillo: núcleo
    más ancho y menos profundo). Los núcleos dados como punto siguen igual. La web los edita con un clic."""
    from engine import geometry as G, standards as ST, layout as LY
    S = ST.merged(None)["nucleo"]
    sw, sl, _ = ST.stair_box(S, 3.0)
    w90, d90 = ST.core_size(S, 3.0, 1, 2.0, giro=90)
    w0, d0 = ST.core_size(S, 3.0, 1, 2.0)
    assert w90 > w0 and d90 < d0 and abs(w90 - (sl + S["ascensor_ducto"][0] + S["muro"] + S["ducto_instalaciones"] + S["muro"])) < 0.01
    barra = [[0, 0], [60, 0], [60, 16], [0, 16]]
    puntos = run(barra, cores_mode="manual", cores=[[10, 8], [50, 8]])
    mixtos = run(barra, cores_mode="manual", cores=[[10, 8], {"p": [50, 8]}])
    assert [c["poly"] for c in puntos["cores"]] == [c["poly"] for c in mixtos["cores"]]      # {"p": ...} = punto
    r = run(barra, cores_mode="manual", cores=[{"p": [10, 9], "frente": 4, "fondo": 6}, {"p": [50, 7], "giro": 90}])
    c0, c1 = sorted(r["cores"], key=lambda c: c["spec"])
    assert (c0["giro"], c0["frente"], c0["fondo"]) == (0, 4.0, 6.0), c0           # el fondo elegido se respeta
    assert c1["giro"] == 90 and abs(c1["frente"] - w90) < 0.01, c1
    st = next(p for p in c1["parts"] if p["kind"] == "stair")
    x0, y0, x1, y1 = G.bbox([tuple(p) for p in st["poly"]])
    assert x1 - x0 > y1 - y0 and abs((x1 - x0) - sl) < 0.05, (x1 - x0, y1 - y0)   # la escalera, a lo largo del pasillo
    assert not [u for u in r["units"] for c in r["cores"]
                if sum(abs(G.area(o)) for o in G.subtract(u["poly"], [c["poly"]])[1][0]) > 0.05]
    # en un edificio con dos bloques (patio), cada núcleo con medidas propias va a su bloque
    r = run([[0, 0], [70, 0], [70, 16], [0, 16]], patios_mode="manual", patios=[[[30, 0], [40, 0], [40, 16], [30, 16]]],
            cores_mode="manual", cores=[{"p": [10, 8], "giro": 90}, [60, 8]])
    assert len(r["cores"]) == 2 and sorted(c["giro"] for c in r["cores"]) == [0, 90], r["cores"]
    # web: clic en un núcleo abre su ficha; la masa recibida conserva los núcleos con medidas propias
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    for s in ("'data-core'", "function corePanel", "function aplicarNucleo", 'id="nGiro"', "closest('[data-core]')",
              "coresManual=(m.cores||[]).map(p=>Array.isArray(p)?[p[0],p[1]]:"):
        assert s in html, s

if __name__ == "__main__":
    test_nucleos_editables(); print("OK23")


def test_evacuacion():
    """R3.6: desde la puerta de cada vivienda se mide el recorrido hasta el núcleo más cercano y el fondo de saco (el
    tramo con una sola salida hasta un núcleo o hasta un punto desde el que se puede salir en dos direcciones). Las
    viviendas que no cumplen se avisan una por una y la planta resalta los tramos de pasillo fuera de norma."""
    from engine import layout as LY, circulation as C
    barra = [[0, 0], [90, 0], [90, 18], [0, 18]]
    r = run(barra)                                       # dos núcleos en las puntas: todo con dos salidas
    assert all(u["egress_status"] == "ok" for u in r["units"]) and not r["evacuacion"]["saco"], r["evacuacion"]
    assert all(u["saco"] == 0 for u in r["units"] if 10 < u["door"][0] < 80)
    # un solo núcleo en una punta: fondo de saco en todo el pasillo; lejos del núcleo, recorrido largo
    r = run(barra, cores_mode="manual", cores=[[8, 9]])
    est = {u["id"]: (u["egress_status"], u["egress"], u["saco"]) for u in r["units"]}
    assert all(s == eg for _, eg, s in est.values()), est                     # una sola salida: todo es fondo de saco
    assert all(st == ("ok" if eg <= 18 else "saco" if eg <= 30 else "fail") for st, eg, _ in est.values()), est
    assert r["evacuacion"]["saco"] and r["evacuacion"]["recorrido"], r["evacuacion"]
    assert any(w.startswith("Evacuación:") for w in r["warnings"]) and any(w.startswith("Fondo de saco:") for w in r["warnings"])
    # anillo alrededor de un patio con un solo núcleo: se sale en dos direcciones (no es fondo de saco)
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "patio_central.json"), encoding="utf-8"))
    nucleo = run(s["footprint"], patios_mode="manual", patios=s["patios"])["cores"][0]["center"]
    r = run(s["footprint"], patios_mode="manual", patios=s["patios"], cores_mode="manual", cores=[nucleo])
    sacos = [u["saco"] for u in r["units"]]                # sobre el anillo, 0; en las puntas, hasta la esquina del anillo
    assert sum(1 for x in sacos if x == 0) >= 4 and max(sacos) < 10, sacos
    assert all(u["egress_status"] == ("fail" if u["egress"] > 30 else "ok") for u in r["units"]), r["units"]
    # T con núcleos solo en el pasillo principal: el ramal es un fondo de saco hasta el empalme
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "T_dos_lineas.json"), encoding="utf-8"))
    r = run(s["footprint"], centerlines=s["centerlines"], cores_mode="manual", cores=[[3, 10], [57, 10]])
    ramal = [u for u in r["units"] if u["door"][1] > 20]
    tronco = [u for u in r["units"] if u["door"][1] < 20]
    assert ramal and all(abs(u["saco"] - (u["door"][1] - 10)) < 1.5 for u in ramal), [(u["id"], u["door"], u["saco"]) for u in ramal]
    assert tronco and all(u["saco"] == 0 for u in tronco), [(u["id"], u["saco"]) for u in tronco]
    # el recorrido es el mismo que el de egress_at (la evacuación del pasillo que ya usaba el motor)
    params = LY.merge_params({"centerlines": s["centerlines"], "cores_mode": "manual", "cores": [[3, 10], [57, 10]]})
    params.update(core_width=r["metrics"]["core"]["width"], core_depth=r["metrics"]["core"]["depth"] + params["corridor_width"])
    pieces = C.generate_circulation([tuple(p) for p in r["blocks"][0]["plate"]], params)
    from engine import evacuacion as EV
    red = EV.analizar(pieces)
    for i, pc in enumerate(pieces):
        for t in (0.1, 0.5, 0.9):
            x = pc["xa"] + (pc["xb"] - pc["xa"]) * t
            assert abs(EV.recorrido(red, i, x) - C.egress_at(pieces, i, x)) < 1e-6, (i, x)
    # web: casilla «Evacuación», colores por estado y nombres de las reglas
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    for t in ('id="showEvac"', "const EVAC=", "result.evacuacion", "Fondo de saco máx.", "Recorrido máx. a un núcleo"):
        assert t in html, t

if __name__ == "__main__":
    test_evacuacion(); print("OK24")


def test_nucleos_sin_pisarse():
    """Corrección (v2.15): dos núcleos no se pisan. En plantas con varias alas (por ejemplo, una T con un patio) dos
    puntas cercanas ponían cada una su núcleo, encimados; ahora el segundo se corre hasta no pisar al primero o, si no
    entra, el primero sirve a las dos. Con núcleos manuales encimados, se avisa."""
    from engine import geometry as G
    W, H = 66.49, 53.09
    T = [[0, 0], [W, 0], [W, H * .4], [W * .65, H * .4], [W * .65, H], [W * .35, H], [W * .35, H * .4], [0, H * .4]]
    patio = [[31.76, 24.66], [48.39, 24.66], [48.39, 40.58], [31.76, 40.58]]
    r = run(T, patios_mode="manual", patios=[patio])
    cs = [c["poly"] for c in r["cores"]]
    pisa = sum(abs(G.area(o)) for i, a in enumerate(cs) for b in cs[i + 1:] for o in G.subtract(a, [b])[1][0])
    assert r["units"] and pisa < 0.1, (pisa, len(cs))
    assert not [u for u in r["units"] if u["egress_status"] != "ok"], [(u["id"], u["egress"], u["saco"]) for u in r["units"]]
    # núcleos manuales encimados: quedan donde los puso el usuario, con un aviso
    r = run([[0, 0], [40, 0], [40, 16], [0, 16]], cores_mode="manual", cores=[[18, 8], [21, 8]])
    assert any("se superpone con otro" in w for w in r["warnings"]), r["warnings"]

if __name__ == "__main__":
    test_nucleos_sin_pisarse(); print("OK25")


def test_proyectos():
    """R4.1: «Guardar proyecto» guarda el pedido que la web le hace al motor (/api/generate) más nombre, versión y
    fecha, con solo las medidas cambiadas: el motor lo lee tal cual y da la misma planta. «Abrir proyecto» devuelve cada
    parámetro simple a su control (mismo id) y los demás (líneas, núcleos, mix, medidas…) uno por uno."""
    import copy, re
    from engine import layout as LY, standards as ST
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "L_polilinea.json"), encoding="utf-8"))
    std = copy.deepcopy(ST.DEFAULTS)            # la web manda todas las medidas: las de /api/standards con las cambiadas
    std["nucleo"]["escalera_ancho"] = 1.4       # una medida cambiada: escalera más ancha
    params = {"corridor_width": 1.8, "core_count": 2, "centerlines": s["centerlines"], "cores_mode": "manual",
              "cores": [{"p": [8, 25], "giro": 90}, [40, 7]], "standards": std,
              "unit_mix": [{"name": "1 dorm", "area": 50, "percent": 40, "dorms": 1}, {"name": "2 dorm", "area": 75, "percent": 60, "dorms": 2}]}
    web = {"footprint": s["footprint"], "height": s["height"], "stage": "plans", "params": params}
    proyecto = dict(copy.deepcopy(web), trazo="proyecto", formato=1, version_motor=LY.VERSION,
                    guardado="2026-10-10T12:00:00.000Z", name="Prueba")
    proyecto["params"]["standards"] = {"nucleo": {"escalera_ancho": 1.4}}     # el archivo guarda solo lo cambiado
    a = generate(copy.deepcopy(web))
    b = generate(json.loads(json.dumps(proyecto)))
    assert a["units"] and json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    c = generate(dict(copy.deepcopy(web), params=dict(params, standards=None)))
    assert json.dumps(a["cores"], sort_keys=True) != json.dumps(c["cores"], sort_keys=True)   # la medida cambiada cuenta
    # web: botones, archivo y que cada parámetro que se guarda se pueda restaurar
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    for t in ('id="archivoProyecto"', "function guardarProyecto", "function abrirProyecto", "trazo:'proyecto'", "showSaveFilePicker"):
        assert t in html, t
    cuerpo = lambda f: html.split(f, 1)[1].split("\nfunction ", 1)[0].split("\nasync function ", 1)[0]
    assert "params()" in cuerpo("function proyecto(){") and "medidasCambiadas()" in cuerpo("function proyecto(){")
    abrir = cuerpo("function abrirProyecto(")
    obj = cuerpo("function params(){").split("return ", 1)[1]
    claves = re.findall(r"[{,](\w+):", obj)
    assert len(claves) > 20 and "core_auto" in claves, claves
    for k in claves:      # un parámetro nuevo se lee de un control con su mismo id o tiene su línea en abrirProyecto
        if re.search(r"[{,]%s:(g\('%s'\)|\$\('%s'\))" % (k, k, k), obj):
            assert re.search(r'<(input|select)[^>]*\bid="%s"' % k, html), k
        else:
            assert re.search(r"\bP\.%s\b" % k, abrir), k

if __name__ == "__main__":
    test_proyectos(); print("OK26")


def test_deshacer():
    """R4.2: deshacer y rehacer (↶ ↷, Ctrl/Cmd+Z, Ctrl/Cmd+Shift+Z y Ctrl+Y) para polilíneas, núcleos, medianeras y
    patios: cada lugar que los cambia guarda antes el estado; otra masa, un proyecto o «Nuevo» empiezan sin historia.
    Corrección: «Quitar núcleo» en modo automático quita el núcleo tocado (antes pasaba a manual y no lo quitaba).
    (El comportamiento se comprobó en navegador; esta prueba evita que un cambio nuevo quede sin deshacer.)"""
    import re
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    for t in ('id="btnUndo"', 'id="btnRedo"', "function deshacer", "function rehacer", "function recordar", "function olvidarHistoria"):
        assert t in html, t
    js = html.split("<script>", 1)[1].split("</script>", 1)[0]
    exentas = ("function volverA", "function setMass", "async function nuevo", "function ensureManual", "function ensurePatiosManual")
    bloques = re.compile(r"\nfunction |\nasync function |addEventListener\(|onclick=\"|onchange=\"")
    cambio = re.compile(r"\b(centerlines|coresManual|medianeras|patios|ediciones|interiores)(\[[^\]]*\])*(\.retiro)?(=(?![=>])|\.(push|pop|splice)\()|\bpl\.splice\(|\bpl\[drag\.vi\]=")
    sin, n = [], 0
    for m in cambio.finditer(js):
        linea = js[js.rfind("\n", 0, m.start()) + 1:m.start()]
        if linea.startswith("let "):
            continue                                                  # declaración inicial
        ini = max([0] + [b.start() for b in bloques.finditer(js, 0, m.start())])
        bloque = js[ini:m.start()].lstrip("\n")
        n += 1
        if not bloque.startswith(exentas) and "recordar(" not in bloque:
            sin.append(js[m.start() - 60:m.end() + 20])
    assert n >= 15 and not sin, (n, sin)
    for f in ("function setMass(", "async function nuevo("):              # otra masa: la historia se olvida
        assert "olvidarHistoria()" in js.split(f, 1)[1].split("\nfunction ", 1)[0].split("\nasync function ", 1)[0], f
    teclas = js.split("window.addEventListener('keydown'", 1)[1].split("\n/*", 1)[0]
    assert "e.ctrlKey||e.metaKey" in teclas and "deshacer()" in teclas and "rehacer()" in teclas and "k==='y'" in teclas
    assert "best[1].spec!=null?best[1].spec:result.cores.indexOf(best[1])" in js     # corrección de «Quitar núcleo»

if __name__ == "__main__":
    test_deshacer(); print("OK27")


def test_arrastrar_nucleos():
    """R4.3: un núcleo se arrastra en la planta. Al soltarlo, la web pasa a modo manual con el centro del núcleo corrido
    lo que se arrastró; el motor lo ajusta al pasillo más cercano, del lado donde quedó (si cruza el pasillo, cambia de
    lado). Los demás núcleos no se mueven, y arrastrar se puede deshacer."""
    barra = [[0, 0], [60, 0], [60, 16], [0, 16]]
    orden = lambda r: sorted(r["cores"], key=lambda c: c["spec"])
    c0 = orden(run(barra, cores_mode="manual", cores=[[15, 9], [45, 9]]))
    (x, y), otro = c0[0]["center"], c0[1]["center"]
    c1 = orden(run(barra, cores_mode="manual", cores=[[x + 6, y + 0.4], otro]))       # arrastrado 6 m a lo largo
    assert abs(c1[0]["center"][0] - (x + 6)) < 0.6 and c1[0]["side"] == c0[0]["side"], (c0[0], c1[0])
    assert abs(c1[0]["center"][1] - y) < 0.05, "se ajusta al pasillo: no se corre de costado"
    assert c1[1]["center"] == otro and c1[1]["side"] == c0[1]["side"]                  # el otro, igual
    c2 = orden(run(barra, cores_mode="manual", cores=[[x, 16 - y], otro]))            # arrastrado al otro lado del pasillo
    assert c2[0]["side"] == -c0[0]["side"], (c0[0]["side"], c2[0]["side"])
    # web: se toma del núcleo, se ve dónde queda y al soltar se registra para deshacer, pasa a manual y recalcula
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    js = html.split("<script>", 1)[1]
    assert "dragCore={i:+tc.getAttribute('data-core')" in js
    assert "dragCore&&dragCore.moved" in js.split("function drawOverlay(){", 1)[1].split("\nfunction ", 1)[0]
    suelta = js.split("svg.addEventListener('pointerup',e=>{ if(!dragCore) return;", 1)[1].split("\nsvg.addEventListener(", 1)[0].split("\nwindow.", 1)[0]
    for t in ("if(!g.moved) return", "svg._skipClick=true", "recordar('mover núcleo')", "ensureManual()", "k.center[0]+g.d[0]", "runCirc()"):
        assert t in suelta, t

if __name__ == "__main__":
    test_arrastrar_nucleos(); print("OK28")


def test_variantes():
    """R4.5: «Guardar como variante» guarda la solución actual (como un proyecto) con sus métricas, y la tabla las
    compara (unidades, NSA, eficiencia, match, circulación, sin usar, núcleos, evacuación, planos). Las métricas que lee
    la web existen en el resultado del motor; las variantes van en el archivo del proyecto y «Nuevo» las borra."""
    import re
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "L.json"), encoding="utf-8"))
    r = run(s["footprint"], s["height"])
    m = r["metrics"]
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    js = html.split("<script>", 1)[1]
    cuerpo = lambda f: js.split(f, 1)[1].split("\nfunction ", 1)[0].split("\nasync function ", 1)[0].split("\nconst ", 1)[0]
    res = cuerpo("function resumen(")
    claves, de_mix = set(re.findall(r"\bm\.(\w+)", res)) - {"mix"}, set(re.findall(r"\bmx\.(\w+)", res))
    assert len(claves) >= 6 and len(de_mix) >= 2, (claves, de_mix)
    for k in claves:
        assert m.get(k) is not None, k                  # la tabla no queda con «–» por una métrica que no existe
    for k in de_mix:
        assert m["mix"].get(k) is not None, k
    assert r["units"] and all("egress_status" in u for u in r["units"]) and "egress_status" in res
    assert "p.variantes=variantes" in cuerpo("function archivoProyecto(")       # se guardan con el proyecto
    assert "variantes=Array.isArray(p.variantes)" in cuerpo("function abrirProyecto(")
    assert "variantes=[]" in cuerpo("async function nuevo(")
    assert "{variante:true}" in cuerpo("function abrirVariante(")             # abrir una variante no cambia la lista

if __name__ == "__main__":
    test_variantes(); print("OK29")


def test_aviso_ancho():
    """Corrección (v2.19.1): el aviso de ancho mínimo muestra dos decimales. Con uno, una vivienda de 4,98 m avisaba
    «Unidad con ancho 5.0 m < mínimo 5.0 m», que parecía un error; ahora dice «4.98 m < mínimo 5.00 m»."""
    import re
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "L.json"), encoding="utf-8"))
    r = run(s["footprint"], s["height"], loading="single")
    avisos = [re.search(r"Unidad con ancho (\d+\.\d\d) m < mínimo (\d+\.\d\d) m", w) for w in r["warnings"] if "Unidad con ancho" in w]
    assert avisos and all(a and float(a.group(1)) < float(a.group(2)) for a in avisos), r["warnings"]
    angostas = [u for u in r["units"] if u["width"] < 5.0]
    assert angostas and "%.2f" % min(u["width"] for u in angostas) in " ".join(r["warnings"])

if __name__ == "__main__":
    test_aviso_ancho(); print("OK30")


def test_editar_viviendas():
    """R4.4: el usuario edita las viviendas con cambios en orden (puntos de mundo, en params.unit_edits): mueve el
    tabique entre dos vecinas, las une o divide una en dos. Las demás no cambian, los planos, la evacuación y las
    métricas se recalculan, y un cambio que ya no entra (la planta cambió) se avisa. La web arrastra los tabiques."""
    import math
    barra = [[0, 0], [60, 0], [60, 16], [0, 16]]
    base = run(barra)
    U = {u["id"]: u for u in base["units"]}
    t = base["tabiques"][0]
    a, b = U[t["a"]], U[t["b"]]
    largo = math.hypot(t["seg"][1][0] - t["seg"][0][0], t["seg"][1][1] - t["seg"][0][1])
    assert t["a"] != t["b"] and abs(math.hypot(*t["dir"]) - 1) < 1e-6 and largo > 3, t
    mid = [(t["seg"][0][0] + t["seg"][1][0]) / 2, (t["seg"][0][1] + t["seg"][1][1]) / 2]
    hacia = lambda d: [mid[0] + d * t["dir"][0], mid[1] + d * t["dir"][1]]
    # mover el tabique 2 m: una crece, la otra achica, las demás igual; conservan el tipo y se rehacen los planos
    r = run(barra, unit_edits=[{"op": "tabique", "p": mid, "a": hacia(2)}])
    R = {u["id"]: u for u in r["units"]}
    assert abs(R[t["a"]]["width"] - (a["width"] + 2)) < 0.02 and abs(R[t["b"]]["width"] - (b["width"] - 2)) < 0.02
    assert R[t["a"]].get("editada") and abs(R[t["a"]]["area"] + R[t["b"]]["area"] - a["area"] - b["area"]) < 0.1
    assert all(R[k]["poly"] == U[k]["poly"] for k in U if k not in (t["a"], t["b"]))
    assert R[t["a"]]["type"] == a["type"] and R[t["a"]]["rooms"] and not any("no se pudieron" in w for w in r["warnings"])
    r = run(barra, unit_edits=[{"op": "tabique", "p": mid, "a": hacia(100)}])          # no deja una vivienda sin ancho
    assert min(u["width"] for u in r["units"]) >= 0.5 * 5.0 - 0.01
    # unir: una sola vivienda con el ancho de las dos y el tabique
    r = run(barra, unit_edits=[{"op": "fusionar", "p": mid}])
    m = next(u for u in r["units"] if u["id"] == t["a"])
    assert len(r["units"]) == len(base["units"]) - 1 and abs(m["width"] - (a["width"] + 0.3 + b["width"])) < 0.02
    # dividir: dos partes; la primera conserva el número; un tipo del mix solo si la superficie se le parece
    c = [sum(p[0] for p in a["poly"]) / len(a["poly"]), sum(p[1] for p in a["poly"]) / len(a["poly"])]
    r = run(barra, unit_edits=[{"op": "dividir", "p": c}])
    p1, p2 = [u for u in r["units"] if u.get("editada")]
    assert len(r["units"]) == len(base["units"]) + 1 and p1["id"] == t["a"] and abs(p1["width"] + 0.3 + p2["width"] - a["width"]) < 0.02
    assert p1["area"] < 0.65 * 75 and p1["type"] == ("%d dorm" % p1["bedrooms"] if p1["bedrooms"] else "Monoambiente"), p1["type"]
    assert r["metrics"]["mix"]["match_score"] < base["metrics"]["mix"]["match_score"]   # el mix se aleja del objetivo
    # en orden: dividir y después mover el tabique nuevo
    tn = next(x for x in r["tabiques"] if (x["a"], x["b"]) == (p1["id"], p2["id"]))
    mn = [(tn["seg"][0][0] + tn["seg"][1][0]) / 2, (tn["seg"][0][1] + tn["seg"][1][1]) / 2]
    r2 = run(barra, unit_edits=[{"op": "dividir", "p": c}, {"op": "tabique", "p": mn, "a": [mn[0] + tn["dir"][0], mn[1] + tn["dir"][1]]}])
    q1 = next(u for u in r2["units"] if u["id"] == p1["id"])
    assert abs(q1["width"] - (p1["width"] + 1)) < 0.02 and not any("no se pudieron" in w for w in r2["warnings"])
    # un cambio que ya no entra se avisa y no cambia nada
    r = run(barra, unit_edits=[{"op": "dividir", "p": [500, 500]}])
    assert any("1 cambio(s) de viviendas no se pudieron aplicar" in w for w in r["warnings"]) and len(r["units"]) == len(base["units"])
    # edificio con patio (dos bloques): el cambio en el segundo bloque también se aplica
    larga = [[0, 0], [90, 0], [90, 16], [0, 16]]
    pat = dict(patios_mode="manual", patios=[[[40, 0], [48, 0], [48, 16], [40, 16]]])
    rb = run(larga, **pat)
    t2 = max(rb["tabiques"], key=lambda x: x["seg"][0][0])                            # el tabique más a la derecha
    m2 = [(t2["seg"][0][0] + t2["seg"][1][0]) / 2, (t2["seg"][0][1] + t2["seg"][1][1]) / 2]
    assert m2[0] > 48
    r = run(larga, unit_edits=[{"op": "fusionar", "p": m2}], **pat)
    assert len(r["units"]) == len(rb["units"]) - 1 and not any("no se pudieron" in w for w in r["warnings"])
    # web: tabiques que se arrastran, dividir y unir en la ficha, descartar, y todo se puede deshacer
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    js = html.split("<script>", 1)[1]
    for s_ in ("unit_edits:ediciones.length?ediciones:null", "function dividirVivienda", "function unirViviendas",
               "function descartarEdiciones", "'data-tab':k", "op:'tabique'", "op:'fusionar'", "op:'dividir'", "dragTab={k:"):
        assert s_ in js, s_
    assert "ediciones" in js.split("function foto(){", 1)[1].split("\n", 1)[0]

if __name__ == "__main__":
    test_editar_viviendas(); print("OK31")


def test_equipamiento():
    """F5 (R5.6, primera parte): artefactos de baños, cocina y lavadero dentro de sus estancias, contra paredes macizas,
    sin pisarse ni pisar el barrido de las puertas. Las puertas interiores miden 0,70 y la de entrada 0,90 (editables).
    Lo que no entra se avisa; un segundo baño sin lugar para la ducha queda como toilette. Con un muro oblicuo, todo queda
    dentro del contorno real de la estancia. Va también al DXF."""
    import math
    from engine import geometry as G, equipamiento as EQ, standards as ST, dxf
    S = ST.merged(None)["equipamiento"]
    barra = [[0, 0], [60, 0], [60, 16], [0, 16]]
    r = run(barra)
    u = r["units"][0]
    rooms = {x["id"]: x for x in u["rooms"]}
    de = lambda rid: {q["kind"] for q in u["equipamiento"] if q["room"] == rid}
    assert {"ducha", "inodoro", "lavatorio", "bide"} <= de("bath1") and {"ducha", "inodoro", "lavatorio"} <= de("bath2")
    assert {"heladera", "mesada", "bacha_cocina", "cocina_horno"} <= de("kitchen") and {"lavarropas", "pileta_lavar"} <= de("laundry")
    adentro = lambda a, b: sum(abs(G.area(o)) for o in G.subtract(a, [b])[1][0])
    for q in u["equipamiento"]:
        assert abs(G.area(q["poly"])) - adentro(q["poly"], rooms[q["room"]]["poly"]) < 0.01, q    # dentro de su estancia
    piezas = [q for q in u["equipamiento"] if q["kind"] != "mesada"]                       # bacha y cocina van sobre la mesada
    for i, a in enumerate(piezas):
        for b in piezas[i + 1:]:
            assert adentro(a["poly"], b["poly"]) < 0.01, (a["kind"], b["kind"])
    largos = sorted(round(math.hypot(d["q"][0] - d["p"][0], d["q"][1] - d["p"][1]), 2) for d in u["doors"])
    assert set(largos) == {0.7, 0.9} and largos.count(0.9) == 1, largos                      # interiores 0,70; entrada 0,90
    for x in r["units"]:                                                                       # cada puerta, en el borde de su estancia
        for d in x["doors"]:
            pl = next((y["poly"] for y in x["rooms"] if y["id"] == d["b"]), None)
            m = ((d["p"][0] + d["q"][0]) / 2, (d["p"][1] + d["q"][1]) / 2)
            if pl:
                lejos = min(math.hypot(m[0] - (a[0] + (b[0] - a[0]) * t), m[1] - (a[1] + (b[1] - a[1]) * t))
                            for a, b in zip(pl, pl[1:] + pl[:1]) for t in [i / 200 for i in range(201)])
                assert lejos < 0.03, (x["id"], d["b"], lejos)
    for d in u["doors"]:                                                                       # el barrido de la hoja, libre
        if d["b"] in ("bath1", "bath2", "laundry"):
            p, q = d["p"], d["q"]
            c = G.centroid(rooms[d["b"]]["poly"])
            n = (-(q[1] - p[1]), q[0] - p[0])
            if (c[0] - p[0]) * n[0] + (c[1] - p[1]) * n[1] < 0:
                n = (-n[0], -n[1])
            barrido = [p, q, (q[0] + n[0], q[1] + n[1]), (p[0] + n[0], p[1] + n[1])]
            assert all(adentro(x["poly"], barrido) < 0.01 for x in u["equipamiento"] if x["room"] == d["b"]), d["b"]
    puerta = [{"p": (0.1, 0.0), "q": (0.8, 0.0), "a": "hallway", "b": "bath1", "ancho": 0.7}]    # puerta junto a una esquina
    pz, _ = EQ.equipar([{"id": "bath1", "kind": "bath", "name": "Baño", "rect": (0.0, 0.0, 2.4, 1.7)}], puerta, {}, S, 2)
    assert {"ducha", "inodoro", "lavatorio"} <= {q["kind"] for q in pz}
    assert all(adentro(q["poly"], [(0.1, 0.0), (0.8, 0.0), (0.8, 0.7), (0.1, 0.7)]) < 0.01 for q in pz), pz   # ni en el barrido
    r8 = run(barra, standards={"equipamiento": {"puerta_interior": 0.8}})                      # la medida de la web manda
    assert 0.8 in {round(math.hypot(d["q"][0] - d["p"][0], d["q"][1] - d["p"][1]), 2) for d in r8["units"][0]["doors"]}
    # cocina abierta al estar y al hall (bordes de arriba y de la derecha): la mesada va contra las paredes macizas
    abierta = {"kitchen": [((3.2, 0.0), (3.2, 2.6)), ((0.0, 2.6), (3.2, 2.6))]}
    pz, ch = EQ.equipar([{"id": "kitchen", "kind": "kitchen", "name": "Cocina", "rect": (0.0, 0.0, 3.2, 2.6)}], [], abierta, S, 2)
    assert not ch and {q["kind"] for q in pz} >= {"heladera", "mesada", "bacha_cocina", "cocina_horno"}
    for q in pz:
        xs, vs = [p[0] for p in q["poly"]], [p[1] for p in q["poly"]]
        assert min(xs) < 1e-6 or min(vs) < 1e-6, q                                             # apoyada en una pared maciza
        assert max(xs) < 3.2 - 0.85 or max(vs) < 2.6 - 0.85, q                                 # con paso hacia lo abierto
    chica = lambda h: EQ.equipar([{"id": "kitchen", "kind": "kitchen", "name": "Cocina", "rect": (0.0, 0.0, 2.4, h)}], [],
                                 {"kitchen": [((2.4, 0.0), (2.4, h)), ((0.0, h), (2.4, h))]}, S, 2)
    pz, ch = chica(2.0)                                     # 2,40 × 2,00: la mesada en una pared y la heladera en la otra (L)
    assert not ch and {"heladera", "mesada"} <= {q["kind"] for q in pz}
    pz, ch = chica(1.9)                                     # 2,40 × 1,90: la heladera ya no entra
    assert [c["msg"] for c in ch] == ["Cocina: no entra la heladera (0.70 × 0.70 m)"] and "mesada" in {q["kind"] for q in pz}
    # segundo baño chico: sin ducha, queda como toilette (aviso informativo, no falla)
    puerta = [{"p": (0.3, 2.1), "q": (1.0, 2.1), "a": "hallway", "b": "bath2", "ancho": 0.7}]
    pz, ch = EQ.equipar([{"id": "bath2", "kind": "bath", "name": "Baño 2", "rect": (0.0, 0.0, 1.3, 2.1)}], puerta, {}, S, 2)
    assert {q["kind"] for q in pz} == {"inodoro", "lavatorio"} and len(ch) == 1 and ch[0]["ok"] and "toilette" in ch[0]["msg"], ch
    # un muro oblicuo recorta el estar y la cocina (como en «quiebre 45°»): todo queda dentro del contorno real
    from engine import plans as P
    res = P.layout_unit([(2.68, 0.0), (14.11, 0.0), (14.11, 6.5), (0.0, 6.5)], 3)
    salas = {x["id"]: x["poly"] for x in res["rooms"]}
    assert abs(G.area(salas["kitchen"])) < 2.5 * 2.6, salas["kitchen"]                         # la cocina es un trapecio
    for q in res["equipamiento"]:
        fuera = sum(abs(G.area(e)) - sum(abs(G.area(h)) for h in hs) for e, hs in G.subtract(q["poly"], [salas[q["room"]]])[0])
        assert fuera < 1e-3, (q["kind"], q["room"], fuera)
    # su pared maciza es corta: no entra la mesada (v2.33: con la franja de servicios a medida, la cocina queda además
    # por debajo de su mínimo, y entonces se avisa eso)
    assert any(not c["ok"] and c["msg"].startswith("Cocina:") for c in res["checks"]), res["checks"]
    # DXF y web
    assert "Trazo_L00_Equipamiento" in dxf.result_to_dxf(r)
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    for t in ('id="showEquip"', "function drawEquip", "'vivienda','equipamiento'", "puerta_interior:'Puerta interior (m)'"):
        assert t in html, t

if __name__ == "__main__":
    test_equipamiento(); print("OK32")


def test_muebles():
    """F5 (R5.6, segunda parte): muebles. Dormitorio principal: cama doble con mesas de luz, paso a los lados y al pie, y
    placard; los demás, dos camas individuales (o una, con aviso informativo); estar: sofá frente al rack de TV; mesa con 4
    asientos y 2 más por cada dormitorio después del primero (monoambiente: 2, con la cama doble). Nada se pisa ni pisa el
    barrido de las puertas o el paso delante de las aberturas; placard y rack no van contra la ventana; desde las puertas
    se llega a todo. Lo que no entra se avisa, salvo en una estancia que ya no llega a su medida mínima."""
    from engine import geometry as G, plans as P, equipamiento as EQ, standards as ST, dxf
    rect = lambda w, d: [(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)]
    tipos = lambda res, rid=None: sorted(q["kind"] for q in res["equipamiento"] if rid is None or q["room"] == rid)
    sillas = lambda res: tipos(res).count("silla")
    caja = lambda pl: (min(p[0] for p in pl), min(p[1] for p in pl), max(p[0] for p in pl), max(p[1] for p in pl))
    choca = lambda a, b, h=0.0: a[0] < b[2] + h - 1e-6 and b[0] < a[2] + h - 1e-6 and a[1] < b[3] + h - 1e-6 and b[1] < a[3] + h - 1e-6
    # 1. dos dormitorios en 9,5 × 8: todo entra
    res = P.layout_unit(rect(9.5, 8.0), 2)
    assert tipos(res, "bed1") == ["cama_doble", "mesita", "mesita", "placard"], tipos(res, "bed1")
    assert tipos(res, "bed2") == ["cama_individual", "cama_individual", "mesita", "placard"], tipos(res, "bed2")
    assert {"sofa", "rack_tv", "mesa"} <= set(tipos(res, "living")) and sillas(res) == 6, tipos(res, "living")
    assert all(c["ok"] for c in res["checks"]), res["checks"]
    salas = {x["id"]: x["poly"] for x in res["rooms"]}
    cuerpos = [q for q in res["equipamiento"] if q["kind"] not in ("silla", "bacha_cocina", "cocina_horno")]
    for q in res["equipamiento"]:                                      # dentro de su estancia
        fuera = sum(abs(G.area(e)) - sum(abs(G.area(h)) for h in hs) for e, hs in G.subtract(q["poly"], [salas[q["room"]]])[0])
        assert fuera < 1e-3, (q["kind"], q["room"], fuera)
    for i, a in enumerate(cuerpos):                                    # sin pisarse (las sillas van en su lugar libre)
        for b in cuerpos[i + 1:]:
            assert not choca(caja(a["poly"]), caja(b["poly"])), (a["kind"], b["kind"])
    for s in (q for q in res["equipamiento"] if q["kind"] == "silla"):
        assert not any(choca(caja(s["poly"]), caja(b["poly"])) for b in cuerpos), s
    cama = caja(next(q["poly"] for q in res["equipamiento"] if q["kind"] == "cama_doble"))
    for b in cuerpos:                                                  # 0,60 libres a los lados y al pie de la cama
        if b["kind"] not in ("cama_doble", "mesita") and b["room"] == "bed1":
            assert not choca(cama, caja(b["poly"]), 0.59), b["kind"]
    for d in res["doors"]:                                             # el barrido de cada puerta, libre
        if d.get("entry") or d["b"] not in salas:
            continue
        (px, py), (qx, qy) = d["p"], d["q"]
        c = G.centroid(salas[d["b"]])
        n = (-(qy - py), qx - px)
        if (c[0] - px) * n[0] + (c[1] - py) * n[1] < 0:
            n = (-n[0], -n[1])
        barrido = caja([(px, py), (qx, qy), (qx + n[0], qy + n[1]), (px + n[0], py + n[1])])
        assert not any(choca(barrido, caja(b["poly"])) for b in cuerpos if b["room"] == d["b"]), d["b"]
    contra_ventana = lambda c, v1: abs(c[3] - v1) < 0.01 and c[2] - c[0] > 0.61     # a lo largo de la fachada (v = v1)
    for q in res["equipamiento"]:                                      # placard y rack: no contra la ventana
        if q["kind"] in ("placard", "rack_tv"):
            assert not contra_ventana(caja(q["poly"]), 8.0), q
    cocina = caja(salas["kitchen"])[3]                                 # delante de la cocina y el hall: 0,90 libres
    for q in res["equipamiento"]:
        if q["room"] == "living" and q["kind"] in ("sofa", "rack_tv", "mesa", "butaca"):
            assert caja(q["poly"])[1] >= cocina + 0.9 - 1e-6, q
    # 2. asientos según los dormitorios; monoambiente con cama doble; estar y comedor separados
    assert sillas(P.layout_unit(rect(7.0, 8.0), 1)) == 4 and sillas(P.layout_unit(rect(12.5, 8.5), 3)) == 8
    mono = P.layout_unit(rect(6.5, 6.5), 0)
    assert sillas(mono) == 2 and {"cama_doble", "mesita", "mesa", "sofa", "rack_tv"} <= set(tipos(mono)), tipos(mono)
    hondo = P.layout_unit(rect(9.5, 11.0), 2)
    assert "dining" in {x["id"] for x in hondo["rooms"]} and {"mesa", "silla"} <= set(tipos(hondo, "dining"))
    assert {"sofa", "rack_tv"} <= set(tipos(hondo, "living")), tipos(hondo)
    # 3. lo que no entra: estar chico, una sola cama, mesa para 2 en un dormitorio; estancia ya avisada por su medida
    S = ST.merged(None)["equipamiento"]
    abre = lambda w: {"living": [((0.0, 0.0), (w - 1.4, 0.0), "kitchen"), ((w - 1.4, 0.0), (w, 0.0), "hall"),
                                 ((w, 0.0), (w, 1.0), "hallway")]}
    estar = lambda w, d, nb: EQ.equipar([{"id": "living", "kind": "living", "name": "Estar-Comedor", "rect": (0.0, 0.0, w, d)}],
                                        [], abre(w), S, nb, {"living": [((0.0, d), (w, d))]})
    pz, ch = estar(3.43, 4.1, 2)
    assert [c["msg"] for c in ch] == ["Estar-Comedor: no entra la mesa para 6 (entra una para 4)"], ch
    pz, ch = estar(3.43, 4.1, 3)
    assert [c["msg"] for c in ch] == ["Estar-Comedor: no entra la mesa para 8 (entra una para 4)"], ch
    pz, ch = estar(3.0, 3.8, 1)
    assert [(c["ok"], c["msg"]) for c in ch] == [(True, "Estar-Comedor: mesa para 2 (para 4 no hay lugar)")], ch
    puerta = [{"p": (0.75, 0.0), "q": (1.45, 0.0), "a": "hallway", "b": "bed2", "ancho": 0.7}]
    pz, ch = EQ.equipar([{"id": "bed2", "kind": "bedroom", "name": "Dormitorio 2", "rect": (0.0, 0.0, 2.2, 4.0)}], puerta, {},
                        S, 2, {"bed2": [((0.0, 4.0), (2.2, 4.0))]})
    assert [q["kind"] for q in pz].count("cama_individual") == 1 and [c["msg"] for c in ch] == \
        ["Dormitorio 2: entra una sola cama individual"] and ch[0]["ok"], (pz, ch)
    angosta = P.layout_unit(rect(6.6, 13.5), 3)                        # dormitorios de 1,15 m: ya se avisa su lado
    msgs = [c["msg"] for c in angosta["checks"]]
    assert any("Dormitorio 2: lado" in m for m in msgs) and not any(m.startswith("Dormitorio 2: no entra") for m in msgs), msgs
    # 4. un dormitorio principal angosto (2,60 × 3,60): el placard se achica antes que ir contra la ventana; la cama
    # conserva su paso; con la puerta en la esquina, nada en su barrido
    dorm = lambda w, d, x: EQ.equipar([{"id": "bed1", "kind": "bedroom", "name": "Dormitorio", "rect": (0.0, 0.0, w, d)}],
                                      [{"p": (x, 0.0), "q": (x + 0.7, 0.0), "a": "hallway", "b": "bed1", "ancho": 0.7}], {},
                                      S, 2, {"bed1": [((0.0, d), (w, d))]})
    pz, ch = dorm(2.6, 3.6, 0.95)
    assert [c["msg"] for c in ch] == ["Dormitorio: placard de 0.90 m (no entra el de 1.80 m)"], ch
    placard, cama = [caja(next(q["poly"] for q in pz if q["kind"] == k)) for k in ("placard", "cama_doble")]
    assert not contra_ventana(placard, 3.6) and not choca(cama, placard, 0.59), (placard, cama)
    pz, ch = dorm(2.4, 3.0, 0.1)
    assert pz and not any(choca((0.1, 0.0, 0.8, 0.7), caja(q["poly"])) for q in pz), pz
    # 5. recorrido: un mueble que corta el paso entre dos aberturas no vale
    r = EQ._Estancia((0.0, 0.0, 4.0, 3.0))
    accesos = [((0.0, 1.0), (0.0, 2.0)), ((4.0, 1.0), (4.0, 2.0))]
    assert EQ._alcanza(r, [(1.5, 0.5, 2.5, 2.5)], accesos, []) and not EQ._alcanza(r, [(1.5, 0.0, 2.5, 3.0)], accesos, [])
    # 6. las medidas de la web mandan: asientos y largo del placard
    S2 = ST.merged({"equipamiento": {"asientos": [2, 4, 1], "placard_largo": [1.5, 1.2]}})["equipamiento"]
    otra = P.layout_unit(rect(9.5, 8.0), 2, equip=S2)
    assert sillas(otra) == 5, tipos(otra)
    pl = caja(next(q["poly"] for q in otra["equipamiento"] if q["kind"] == "placard" and q["room"] == "bed1"))
    assert abs(max(pl[2] - pl[0], pl[3] - pl[1]) - 1.5) < 1e-6, pl
    # DXF y web
    r = run([[0, 0], [60, 0], [60, 16], [0, 16]])
    assert dxf.result_to_dxf(r).count("Trazo_L00_Equipamiento") > 400
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    for t in ("cama_doble:'Cama doble (ancho × largo, m)'", "asientos:'Asientos: monoambiente", "const STD_LISTA",
              "equipamiento:'Equipamiento y muebles'"):
        assert t in html, t

if __name__ == "__main__":
    test_muebles(); print("OK33")


def test_accesible():
    """F5 (R5.6, tercera parte): vivienda accesible por tipo del mix. Puertas de dormitorios y baño de 0,82 m; la del baño
    abre hacia afuera; el baño lleva ducha a nivel, inodoro con su transferencia al costado, lavatorio y un círculo de
    giro de 1,50 m libre (puede pisar la ducha), sin bidé. Si no entra, se avisa. Solo los tipos marcados."""
    import math
    from engine import geometry as G, plans as P, standards as ST
    rect = lambda w, d: [(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)]
    caja = lambda pl: (min(p[0] for p in pl), min(p[1] for p in pl), max(p[0] for p in pl), max(p[1] for p in pl))
    largo = lambda d: round(math.hypot(d["q"][0] - d["p"][0], d["q"][1] - d["p"][1]), 2)
    for w, d, nb in ((9.5, 8.0, 2), (12.5, 8.5, 3), (9.5, 6.5, 2), (6.0, 7.0, 0)):
        res = P.layout_unit(rect(w, d), nb, accesible=True)
        assert res["accesible"] and not any(not c["ok"] and "Baño" in c["msg"] for c in res["checks"]), res["checks"]
        salas = {x["id"]: x["poly"] for x in res["rooms"]}
        bano = [q for q in res["equipamiento"] if q["room"] == "bath1"]
        assert sorted(q["kind"] for q in bano) == ["ducha_nivel", "giro", "inodoro", "lavatorio"], bano
        giro = next(q for q in bano if q["kind"] == "giro")
        g = caja(giro["poly"])
        c, R = ((g[0] + g[2]) / 2, (g[1] + g[3]) / 2), (g[2] - g[0]) / 2
        b = caja(salas["bath1"])
        assert abs(2 * R - 1.5) < 0.01, R                               # dentro del baño (rectangular)
        assert b[0] - 1e-6 <= c[0] - R and c[0] + R <= b[2] + 1e-6 and b[1] - 1e-6 <= c[1] - R and c[1] + R <= b[3] + 1e-6
        for q in bano:                                                  # el giro, libre (salvo la ducha, a nivel)
            if q["kind"] in ("inodoro", "lavatorio"):
                k = caja(q["poly"])
                assert math.hypot(max(k[0] - c[0], 0, c[0] - k[2]), max(k[1] - c[1], 0, c[1] - k[3])) >= R - 1e-3, q["kind"]
        ino = caja(next(q["poly"] for q in bano if q["kind"] == "inodoro"))
        otros = [caja(q["poly"]) for q in bano if q["kind"] in ("lavatorio", "ducha_nivel")]
        lados = ((ino[0] - 0.8, ino[1], ino[0], ino[3]), (ino[2], ino[1], ino[2] + 0.8, ino[3]),
                 (ino[0], ino[1] - 0.8, ino[2], ino[1]), (ino[0], ino[3], ino[2], ino[3] + 0.8))
        libre = lambda z: b[0] - 1e-6 <= z[0] and z[2] <= b[2] + 1e-6 and b[1] - 1e-6 <= z[1] and z[3] <= b[3] + 1e-6 and \
            not any(z[0] < o[2] - 1e-6 and o[0] < z[2] - 1e-6 and z[1] < o[3] - 1e-6 and o[1] < z[3] - 1e-6 for o in otros)
        assert any(libre(z) for z in lados), (ino, otros)                 # 0,80 libres a un costado del inodoro
        puerta = next(x for x in res["doors"] if "bath1" in (x["a"], x["b"]))
        assert largo(puerta) == 0.82 and puerta["a"] == "bath1", puerta                 # abre hacia afuera (hacia b)
        for x in res["doors"]:
            if x["b"].startswith("bed"):
                assert largo(x) == 0.82, x
            elif x["b"] in ("bath2", "laundry", "closet", "storage"):
                assert largo(x) == 0.70, x
    # un baño de 3,00 × 2,20 con la puerta en la esquina: el lavatorio y la ducha no le quitan la transferencia al inodoro
    from engine import equipamiento as EQ
    S0 = ST.merged(None)["equipamiento"]
    pz, ch = EQ.equipar([{"id": "bath1", "kind": "bath", "name": "Baño", "rect": (0.0, 0.0, 3.0, 2.2)}],
                        [{"p": (0.1, 0.0), "q": (0.92, 0.0), "a": "bath1", "b": "hallway", "ancho": 0.82}], {}, S0, 2, acc=True)
    ino = caja(next(q["poly"] for q in pz if q["kind"] == "inodoro"))
    otros = [caja(q["poly"]) for q in pz if q["kind"] in ("lavatorio", "ducha_nivel")]
    b = (0.0, 0.0, 3.0, 2.2)
    lados = ((ino[0] - 0.8, ino[1], ino[0], ino[3]), (ino[2], ino[1], ino[2] + 0.8, ino[3]),
             (ino[0], ino[1] - 0.8, ino[2], ino[1]), (ino[0], ino[3], ino[2], ino[3] + 0.8))
    assert not ch and "giro" in {q["kind"] for q in pz} and any(libre(z) for z in lados), (pz, ch)
    # una vivienda común no cambia: puertas de 0,70, baño con bidé, sin giro
    comun = P.layout_unit(rect(9.5, 8.0), 2)
    assert not comun["accesible"] and "giro" not in {q["kind"] for q in comun["equipamiento"]}
    assert {largo(x) for x in comun["doors"] if not x.get("entry")} == {0.7}
    # un baño que no llega: se avisa y queda el baño común
    S = ST.merged({"equipamiento": {"giro": 2.4}})["equipamiento"]
    chico = P.layout_unit(rect(9.5, 8.0), 2, equip=S, accesible=True)
    assert any(not c["ok"] and c["msg"].startswith("Baño: no entra el baño accesible (círculo de giro de 2.40 m")
               for c in chico["checks"]), chico["checks"]
    assert {"ducha", "inodoro", "lavatorio"} <= {q["kind"] for q in chico["equipamiento"] if q["room"] == "bath1"}
    # por tipo del mix: solo las viviendas del tipo marcado
    mix = [{"name": "2 dorm", "area": 75, "percent": 50, "dorms": 2, "accesible": True},
           {"name": "3 dorm", "area": 95, "percent": 50, "dorms": 3}]
    r = run([[0, 0], [60, 0], [60, 16], [0, 16]], unit_mix=mix)
    for u in r["units"]:
        acc = u["type"] == "2 dorm"
        assert bool(u.get("accesible")) == acc, u["id"]
        assert ("giro" in {q["kind"] for q in u["equipamiento"]}) == acc, u["id"]
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    for t in ("data-acc=", "mix[${i}].accesible=this.checked", "u.accesible?' · ♿ accesible'", "q.kind==='giro'",
              "puerta_accesible:'Accesible: puertas de dormitorios y baño (m)'"):
        assert t in html, t

if __name__ == "__main__":
    test_accesible(); print("OK34")

def test_editar_interior():
    """R5.7: editar la vivienda por dentro. Un tabique interior se arrastra: las estancias que se apoyan en él se agrandan
    o se achican (cada una conserva al menos 0,60 m). Una puerta se corre a lo largo de su pared, cambia de ancho o abre
    hacia el otro lado; se la reconoce por las dos estancias que une, así sigue valiendo si después se mueve un tabique.
    Los cambios van en params.room_edits con puntos de mundo, en orden, y se aplican en la vivienda donde caen; lo que
    no se puede aplicar se avisa. La web arrastra los tabiques y las puertas de la vivienda elegida."""
    import math
    from engine import plans as P
    rect = lambda w, d: [(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)]
    caja = lambda pl: (min(p[0] for p in pl), min(p[1] for p in pl), max(p[0] for p in pl), max(p[1] for p in pl))
    mitad = lambda a, b: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    cajas = lambda res: {r["id"]: caja(r["poly"]) for r in res["rooms"]}
    plano = lambda *ed: P.layout_unit(rect(9.5, 8.0), 2, ediciones=list(enumerate(ed)))
    base = plano()
    B = cajas(base)
    assert base["paredes"] and base["ediciones"] == []
    # un tabique vertical: las estancias de un lado crecen 0,30 m, las del otro se achican 0,30 m y las demás no cambian
    a, b = next((a, b) for a, b in base["paredes"] if abs(a[0] - b[0]) < 1e-6)
    c, lo, hi = a[0], min(a[1], b[1]), max(a[1], b[1])
    junto = lambda k: {i for i, r in B.items() if abs(r[k] - c) < 1e-6 and r[3] > lo + 0.01 and r[1] < hi - 0.01}
    izq, der = junto(2), junto(0)
    assert izq and der and min(B[i][2] - B[i][0] for i in der) > 1.0, (izq, der)
    m = mitad(a, b)
    res = plano({"op": "pared", "p": m, "a": (m[0] + 0.3, m[1])})
    R = cajas(res)
    assert res["ediciones"] == [0] and set(R) == set(B)
    for i in B:
        dx0, dx1 = (0.3 if i in der else 0.0), (0.3 if i in izq else 0.0)
        assert abs(R[i][0] - B[i][0] - dx0) < 1e-6 and abs(R[i][2] - B[i][2] - dx1) < 1e-6 and R[i][1::2] == B[i][1::2], i
    assert abs(sum(r["area"] for r in res["rooms"]) - sum(r["area"] for r in base["rooms"])) < 1e-6
    # hasta el final: la estancia más angosta de ese lado queda con 0,60 m; lejos de un tabique no cambia nada
    R = cajas(plano({"op": "pared", "p": m, "a": (m[0] + 100, m[1])}))
    assert abs(min(R[i][2] - R[i][0] for i in der) - 0.6) < 1e-6
    # el tabique sigue por las estancias que se apoyan en él, aunque entre ellas quede un hueco
    Rh = {"A": ("bedroom", (0.0, 0.0, 3.0, 5.0), "A"), "B": ("bath", (3.0, 0.0, 5.0, 3.0), "B"), "C": ("bath", (3.0, 4.0, 5.0, 5.0), "C")}
    assert P._mover_pared(Rh, {"p": (3.0, 1.5), "a": (3.5, 1.5)})
    assert [Rh[i][1] for i in "ABC"] == [(0.0, 0.0, 3.5, 5.0), (3.5, 0.0, 5.0, 3.0), (3.5, 4.0, 5.0, 5.0)], Rh
    lejos = plano({"op": "pared", "p": (-5.0, -5.0), "a": (-4.0, -5.0)})
    assert lejos["ediciones"] == [] and cajas(lejos) == B
    # la puerta del dormitorio 2: se corre (sin pasarse del borde), cambia de ancho y abre hacia el otro lado
    puerta = lambda res, x: next(d for d in res["doors"] if x in (d["a"], d["b"]))
    largo = lambda d: math.hypot(d["q"][0] - d["p"][0], d["q"][1] - d["p"][1])
    d0 = puerta(base, "bed2")
    otra = d0["a"]
    k = 1 if d0["vertical"] else 0
    e0, e1 = sorted(x[k] for x in P._shared(B[otra], B["bed2"]))
    m0 = mitad(d0["p"], d0["q"])
    hacia = lambda t: (m0[0], t) if k else (t, m0[1])
    t = e0 + 0.35 + 0.05 + 0.2
    d1 = puerta(plano({"op": "puerta", "p": m0, "a": hacia(t)}), "bed2")
    assert abs(mitad(d1["p"], d1["q"])[k] - t) < 1e-6 and abs(largo(d1) - largo(d0)) < 1e-6
    d1 = puerta(plano({"op": "puerta", "p": m0, "a": hacia(e1 + 5)}), "bed2")
    assert abs(max(d1["p"][k], d1["q"][k]) - (e1 - 0.05)) < 1e-6           # contra el final del borde
    d2 = puerta(plano({"op": "puerta", "p": m0, "ancho": 0.9}), "bed2")
    assert abs(largo(d2) - 0.9) < 1e-6 and abs(mitad(d2["p"], d2["q"])[k] - m0[k]) < 1e-6
    d3 = puerta(plano({"op": "puerta", "p": m0, "abre": True}), "bed2")
    assert (d3["a"], d3["b"], d3["into"]) == ("bed2", otra, -d0["into"]), d3
    # por sus estancias, aunque el punto ya no caiga sobre ella; la de entrada se corre por el hall y no se invierte
    d4 = puerta(plano({"op": "puerta", "p": (-50.0, -50.0), "entre": ["bed2", otra], "ancho": 0.9}), "bed2")
    assert abs(largo(d4) - 0.9) < 1e-6
    en = next(d for d in base["doors"] if d.get("entry"))
    me = mitad(en["p"], en["q"])
    r = plano({"op": "puerta", "p": me, "a": (me[0] + 3.0, me[1]), "abre": True})
    en2 = next(d for d in r["doors"] if d.get("entry"))
    h = B["hall"]
    assert en2["a"] == "exterior" and en2["p"][1] == en2["q"][1] == en["p"][1] and r["ediciones"] == [0]
    assert abs(mitad(en2["p"], en2["q"])[0] - max(h[0] + largo(en) / 2 + 0.05, min(h[2] - largo(en) / 2 - 0.05, me[0] + 3.0))) < 1e-6
    # en orden: la puerta corrida y después el tabique que achica el dormitorio 2; la puerta sigue corrida
    lado = next((a, b) for a, b in base["paredes"] if abs(a[0] - b[0]) < 1e-6 and abs(a[0] - B["bed2"][0]) < 1e-6)
    ml = mitad(*lado)
    r = plano({"op": "puerta", "p": m0, "entre": ["bed2", otra], "a": hacia(t)}, {"op": "pared", "p": ml, "a": (ml[0] + 0.5, ml[1])})
    d5 = puerta(r, "bed2")
    assert r["ediciones"] == [0, 1] and abs(mitad(d5["p"], d5["q"])[k] - max(t, B["bed2"][0] + 0.5 + 0.4)) < 1e-6
    # vivienda con un anexo (bolsillo al fondo, un depósito de 4 m²: v2.33): todos los tabiques que se ofrecen se pueden
    # mover; el borde del anexo, no
    L = [(0.0, 0.0), (9.5, 0.0), (9.5, 8.0), (2.0, 8.0), (2.0, 10.0), (0.0, 10.0)]
    r = P.layout_unit(L, 2)
    assert any(x["id"].startswith("annex") for x in r["rooms"]) and r["paredes"]
    for a, b in r["paredes"]:
        mm, ver = mitad(a, b), abs(a[0] - b[0]) < 1e-6
        mov = [P.layout_unit(L, 2, ediciones=[(0, {"op": "pared", "p": mm, "a": (mm[0] + s, mm[1]) if ver else (mm[0], mm[1] + s)})])
               ["ediciones"] for s in (0.2, -0.2)]
        assert [0] in mov, (a, b)
    # en el edificio, con puntos de mundo: solo cambia la vivienda donde cae el cambio
    barra = [[0, 0], [60, 0], [60, 16], [0, 16]]
    base = run(barra)
    u = base["units"][2]
    assert all(abs(math.hypot(*w["dir"]) - 1) < 1e-6 for w in u["paredes"])
    w = u["paredes"][0]
    mw = list(mitad(*w["seg"]))
    r = run(barra, room_edits=[{"op": "pared", "p": mw, "a": [mw[0] + 0.3 * w["dir"][0], mw[1] + 0.3 * w["dir"][1]]}])
    U = {x["id"]: x for x in r["units"]}
    assert U[u["id"]].get("editada_dentro") and not any("dentro de las viviendas" in x for x in r["warnings"])
    antes, ahora = {x["id"]: x["area"] for x in u["rooms"]}, {x["id"]: x["area"] for x in U[u["id"]]["rooms"]}
    assert max(abs(ahora[i] - antes[i]) for i in antes) > 0.3 * 0.9 and abs(sum(ahora.values()) - sum(antes.values())) < 0.3
    otras = lambda r: all(x["rooms"] == y["rooms"] and x["doors"] == y["doors"] and not y.get("editada_dentro")
                          for x, y in zip(base["units"], r["units"]) if x["id"] != u["id"])
    assert otras(r)
    dw = next(d for d in u["doors"] if not d.get("entry"))
    md = list(mitad(dw["p"], dw["q"]))
    r = run(barra, room_edits=[{"op": "puerta", "p": md, "entre": [dw["a"], dw["b"]], "ancho": 0.9}])
    dn = next(d for d in r["units"][2]["doors"] if {d["a"], d["b"]} == {dw["a"], dw["b"]})
    assert abs(largo(dn) - 0.9) < 0.01 and otras(r) and not any("dentro de las viviendas" in x for x in r["warnings"])
    r = run(barra, room_edits=[{"op": "pared", "p": [500, 500], "a": [501, 500]}])
    assert any(x.startswith("1 cambio(s) dentro de las viviendas no se pudieron aplicar") for x in r["warnings"]), r["warnings"]
    # web: tabiques interiores y puertas que se arrastran, la ficha con las puertas, descartar, proyecto y deshacer
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    js = html.split("<script>", 1)[1]
    for s_ in ("room_edits:interiores.length?interiores:null", "'data-pared':k", "'data-puerta':k", "function puertasPanel",
               "function editarInterior", "function descartarInteriores", "entre:[d.a,d.b]", "op.entre=[d.a,d.b]",
               "interiores=(m.room_edits||[])", "room_edits:P.room_edits", "dragIn={u:selUnit"):
        assert s_ in js, s_
    assert "interiores" in js.split("function foto(){", 1)[1].split("\n", 1)[0]

if __name__ == "__main__":
    test_editar_interior(); print("OK35")

def test_ventanas():
    """R5.5: una ventana por estancia habitable (dormitorios, estar, comedor y estudio con fachada), centrada en su
    tramo de fachada (primero el fondo), del ancho típico o del que pida el vano mínimo (10 % de la superficie, con
    1,20 m de alto), a 0,20 m de las esquinas; si no alcanza, otra en el tramo siguiente o un aviso. El comedor interior
    se ilumina por el estar. La ventana va en el muro exterior, donde del otro lado hay aire (no junto a una esquina
    entrante), y se dibuja en la web, en Rhino (Trazo::L00::Ventanas) y en el DXF."""
    import math
    from engine import plans as P, standards as ST, dxf as DXF
    rect = lambda w, d: [(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)]
    caja = lambda pl: (min(p[0] for p in pl), min(p[1] for p in pl), max(p[0] for p in pl), max(p[1] for p in pl))
    S = ST.DEFAULTS["ventanas"]
    por = lambda res: {i: [w for w in res["ventanas"] if w["room"] == i] for i in {w["room"] for w in res["ventanas"]}}
    malos = lambda res: [c["msg"] for c in res["checks"] if not c["ok"]]
    # 9,50 × 8,00 con 2 dormitorios: una en cada dormitorio y otra en el estar, en el fondo; ninguna en baños o cocina
    res = P.layout_unit(rect(9.5, 8.0), 2)
    R, V = {r["id"]: r for r in res["rooms"]}, por(res)
    assert set(V) == {"bed1", "bed2", "living"}, V.keys()
    for i, (w,) in V.items():
        b = caja(R[i]["poly"])
        assert w["p"][1] == w["q"][1] == 8.0 and w["n"] == (0.0, 1.0), w                  # en la fachada, hacia afuera
        x0, x1 = sorted((w["p"][0], w["q"][0]))
        assert abs((x0 + x1) / 2 - (b[0] + b[2]) / 2) < 1e-6 and x0 >= b[0] + S["mocheta"] - 1e-6 and x1 <= b[2] - S["mocheta"] + 1e-6
        tip = S["ancho_estar"] if i == "living" else S["ancho_dormitorio"]
        assert abs(w["ancho"] - max(tip, S["iluminacion"] * R[i]["area"] / S["alto"])) < 0.01 and w["alto"] == S["alto"]
        assert abs(w["minimo"] - S["iluminacion"] * R[i]["area"]) < 0.01 and w["area"] >= w["minimo"] - 0.01
    assert not any("ventana" in m for m in malos(res))
    # un estar grande pide una ventana más ancha que la típica
    w, = por(P.layout_unit(rect(6.0, 7.0), 0))["living"]
    assert w["ancho"] > S["ancho_estar"] + 0.1 and abs(w["area"] - w["minimo"]) < 0.01, w
    # comedor interior: no lleva ventana; la del estar ilumina los dos
    res = P.layout_unit(rect(9.5, 12.0), 2)
    R, V = {r["id"]: r for r in res["rooms"]}, por(res)
    assert "dining" in R and "dining" not in V and abs(V["living"][0]["minimo"] - S["iluminacion"] * (R["living"]["area"] + R["dining"]["area"])) < 0.01
    # en una esquina: primero el fondo; si no alcanza, otra en la fachada lateral
    esquina = lambda p, q: (abs(p[1] - 12) < 0.05 and abs(q[1] - 12) < 0.05) or (abs(p[0]) < 0.05 and abs(q[0]) < 0.05)
    res = P.layout_unit(rect(9.5, 12.0), 2, is_facade=esquina, ventanas=dict(S, iluminacion=0.25))
    est = por(res)["living"]
    assert [w["n"] for w in est] == [(0.0, 1.0), (-1.0, -0.0)] and sum(w["area"] for w in est) >= est[0]["minimo"] - 0.01, est
    # si no alcanza: aviso con lo que falta; si no entra ninguna, otro aviso (no en una estancia ya avisada)
    res = P.layout_unit(rect(9.5, 8.0), 2, ventanas=dict(S, iluminacion=0.5))
    assert any(m.startswith("Dormitorio principal: ventana de 3.36 m² < 7.20 m² (50 % de la superficie)") for m in malos(res)), malos(res)
    fondo = lambda p, q: abs(p[1] - 8) < 0.05 and abs(q[1] - 8) < 0.05            # con fachada, pero la ventana
    fondo.ventana = lambda p, q: fondo(p, q) and (max(p[0], q[0]) <= 6.0 or min(p[0], q[0]) >= 8.4)   # solo da 1,1 m
    res = P.layout_unit(rect(9.5, 8.0), 2, is_facade=fondo)
    assert "bed2" not in por(res) and any(m.startswith("Dormitorio 2: no entra una ventana en su fachada") for m in malos(res)), malos(res)
    nada = P.layout_unit(rect(12, 8), 2, is_facade=lambda p, q: False)
    assert not nada["ventanas"] and not any("ventana" in m for m in malos(nada))       # ya dice «sin fachada»
    # en el edificio: en el muro exterior (de la planta a la huella), sobre el borde de su estancia
    def borde(p, pl):
        d = 1e9
        for i in range(len(pl)):
            a, b = pl[i], pl[(i + 1) % len(pl)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
            d = min(d, math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy))
        return d
    barra = [[0, 0], [60, 0], [60, 16], [0, 16]]
    for muro in (0.35, 0.5):
        r = run(barra, outer_wall=muro)
        n = 0
        for u in r["units"]:
            R = {x["id"]: x for x in u["rooms"]}
            for w in u["ventanas"]:
                d = sorted(borde(p, barra) for p in w["poly"])
                assert d[0] < 1e-6 and d[1] < 1e-6 and abs(d[2] - muro) < 1e-6 and abs(d[3] - muro) < 1e-6, d
                assert max(borde(p, R[w["room"]]["poly"]) for p in w["seg"]) < 0.01 and len(w["lines"]) == 2
                n += 1
        assert n >= 3 * len(r["units"]), n
    # en una L, junto a la esquina entrante, la ventana no entra en el muro de la otra ala (v2.33: el estudio de la ochava
    # tiene su ventana en el muro oblicuo, con un error de redondeo de centésimas de milímetro)
    L = [[4, 0], [50, 0], [50, 16], [16, 16], [16, 40], [0, 40], [0, 4]]
    r = run(L)
    for u in r["units"]:
        for w in u["ventanas"]:
            d = sorted(borde(p, L) for p in w["poly"])
            assert d[0] < 1e-4 and d[1] < 1e-4 and abs(d[2] - 0.35) < 1e-4 and abs(d[3] - 0.35) < 1e-4, (u["id"], w["room"], d)
    assert any(w["room"].startswith("annex") for u in r["units"] for w in u["ventanas"])
    # medidas de la web: más bajas, más anchas
    r = run(barra, standards={"ventanas": {"alto": 1.0}})
    w = next(w for w in r["units"][0]["ventanas"] if w["room"] == "living")
    assert w["alto"] == 1.0 and w["ancho"] >= S["ancho_estar"]
    dxf = DXF.result_to_dxf(r)                       # cada ventana: su hueco (cerrado) y dos líneas de vidrio
    nv = sum(len(u["ventanas"]) for u in r["units"])
    assert dxf.count("POLYLINE\n8\nTrazo_L00_Ventanas\n66\n1\n70\n1\n") == nv and \
        dxf.count("POLYLINE\n8\nTrazo_L00_Ventanas\n66\n1\n70\n0\n") == 2 * nv, nv
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    for t in ("function drawWindows", "drawWindows(gb,u)", "'equipamiento','ventanas','nucleo'", "ventanas:'Ventanas'",
              "iluminacion:'Vano mínimo / superficie del local'", "function ventanasDe", "${ventanasDe(u)}"):
        assert t in html, t

if __name__ == "__main__":
    test_ventanas(); print("OK36")

def test_segunda_fachada():
    """R5.3: una vivienda con fachada al fondo y en un costado (de esquina o de extremo) la usa. Si el frente alcanza, el
    estar va a la esquina (el plano se hace al revés si el costado es el otro) y lleva ventana en las dos fachadas; si el
    frente no alcanza para todos los dormitorios al fondo, el último va al costado, entre el pasillo común y el interno,
    con su ventana a esa fachada, solo si el plano mejora y no pierde estancias. El segundo baño puede perderse solo con
    hasta 2 dormitorios (criterio del usuario, v2.28): con 3 o más, el plano conserva sus dos baños. Sin fachada lateral,
    con las dos o con el fondo en parte ciego, no cambia nada. Los cambios a mano siguen valiendo."""
    import math
    from engine import plans as P
    rect = lambda w, d: [(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)]
    caja = lambda pl: (min(p[0] for p in pl), min(p[1] for p in pl), max(p[0] for p in pl), max(p[1] for p in pl))

    def luz(W, D, izq=False, der=False, fondo=(0.0, 1e9)):
        def f(p, q):
            if abs(p[1] - D) < 0.05 and abs(q[1] - D) < 0.05:
                return fondo[0] - 1e-6 <= min(p[0], q[0]) and max(p[0], q[0]) <= fondo[1] + 1e-6
            return (izq and abs(p[0]) < 0.05 and abs(q[0]) < 0.05) or (der and abs(p[0] - W) < 0.05 and abs(q[0] - W) < 0.05)
        return f
    R = lambda res: {r["id"]: caja(r["poly"]) for r in res["rooms"]}
    info = lambda res: [c["msg"] for c in res["checks"] if c.get("info") and c["msg"].startswith("Fachada lateral")]
    # 2 dormitorios, fachada a la derecha: el estar va a esa esquina (al revés), con ventana al fondo y al costado
    W, D = 11.7, 6.5
    sin = P.layout_unit(rect(W, D), 2, luz(W, D))
    for der, borde in ((True, W), (False, 0.0)):
        res = P.layout_unit(rect(W, D), 2, luz(W, D, izq=not der, der=der))
        est = R(res)["living"]
        assert res["segunda_fachada"] == "estar" and info(res) == ["Fachada lateral: el estar en la esquina, con luz por dos fachadas"]
        assert abs(est[3] - D) < 1e-6 and abs((est[2] if der else est[0]) - borde) < 1e-6, est
        assert sorted(w["n"] for w in res["ventanas"] if w["room"] == "living") == sorted([(0.0, 1.0), (1.0 if der else -1.0, 0.0)])
        assert res["score"] == sin["score"] and sorted(r["kind"] for r in res["rooms"]) == sorted(r["kind"] for r in sin["rooms"])
    corta = P.layout_unit(rect(W, 5.5), 2, luz(W, 5.5, der=True))     # poco fondo: el baño junto al hall (puerta vertical)
    verticales = [d for d in corta["doors"] if d["vertical"]]
    assert corta["segunda_fachada"] == "estar" and verticales
    for d in verticales:                                       # la hoja abre hacia su estancia, también al revés
        b = R(corta)[d["b"]]
        assert (((b[0] + b[2]) / 2 - d["p"][0]) > 0) == (d["into"] > 0), d
    # sin fachada lateral, con las dos o con parte del fondo ciega: no cambia
    assert sin["segunda_fachada"] is None and not info(sin)
    for w_, f in ((W, luz(W, D, True, True)), (9.0, luz(9.0, D, der=True, fondo=(0.0, 6.0)))):
        res = P.layout_unit(rect(w_, D), 2, f)
        assert res["segunda_fachada"] is None and abs(R(res)["living"][0]) < 1e-6, R(res)["living"]
    # 4 dormitorios en 12,00 m de frente: al fondo no entran; el cuarto va al costado, con su ventana, y quedan dos baños
    W, D = 12.0, 9.0
    sin = P.layout_unit(rect(W, D), 4, luz(W, D))
    assert any(c["msg"].startswith("Dormitorio 4: lado") for c in sin["checks"] if not c["ok"])     # angostos
    for der in (True, False):
        res = P.layout_unit(rect(W, D), 4, luz(W, D, izq=not der, der=der))
        b4, pas = R(res)["bed4"], R(res)["hallway"]
        assert res["segunda_fachada"] == "dormitorio" and info(res) == ["Fachada lateral: Dormitorio 4 al costado, con su ventana a esa fachada"]
        assert abs(b4[1]) < 1e-6 and abs(b4[3] - pas[1]) < 1e-6 and abs((b4[2] if der else b4[0]) - (W if der else 0.0)) < 1e-6, b4
        assert [w["n"] for w in res["ventanas"] if w["room"] == "bed4"] == [(1.0 if der else -1.0, 0.0)]
        assert res["score"] > sin["score"] and not any("Dormitorio" in c["msg"] for c in res["checks"] if not c["ok"])
        k = [r["kind"] for r in res["rooms"]]
        assert k.count("bedroom") == 4 and k.count("bath") == 2 and "laundry" in k and "kitchen" in k, k
    # con 3 o más dormitorios, el dormitorio al costado no deja la vivienda con un solo baño: en 9,10 m (3 dormitorios)
    # el plano sigue con los dormitorios al fondo y sus dos baños; en 10,70 m (4), desde v2.33 la franja de servicios a
    # medida deja los dos baños también con el cuarto al costado, y entonces va ahí (el plano mejora)
    for nb, W, D, lat in ((3, 9.1, 8.5, False), (4, 10.7, 7.0, True)):
        res = P.layout_unit(rect(W, D), nb, luz(W, D, der=True))
        assert (res["segunda_fachada"] == "dormitorio") == lat and "bed%d" % nb in R(res), (nb, res["segunda_fachada"])
        assert [r["kind"] for r in res["rooms"]].count("bath") == 2, nb
    # 2 dormitorios en 9,30 m: al fondo ya entran; el estar va a la esquina y quedan los dos baños
    res = P.layout_unit(rect(9.3, 8.5), 2, luz(9.3, 8.5, der=True))
    assert res["segunda_fachada"] == "estar" and [r["kind"] for r in res["rooms"]].count("bath") == 2
    # en el edificio: las viviendas de los extremos de la barra; un cambio a mano en una dada vuelta sigue valiendo
    barra = [[0, 0], [60, 0], [60, 16], [0, 16]]
    r = run(barra)
    ext = [u for u in r["units"] if any(c["msg"].startswith("Fachada lateral") for c in u["checks"] if c.get("info"))]
    punta = [u for u in r["units"] if min(p[0] for p in u["poly"]) < 0.4 or max(p[0] for p in u["poly"]) > 59.6]
    assert ext and [u["id"] for u in ext] == [u["id"] for u in punta], ([u["id"] for u in ext], [u["id"] for u in punta])
    for u in ext:
        est = next(x for x in u["rooms"] if x["kind"] == "living")
        b = caja(est["poly"])
        assert min(b[0], 60 - b[2]) < 0.4, (u["id"], b)                                     # el estar, en el extremo
        assert len([w for w in u["ventanas"] if w["room"] == "living"]) == 2
    for u in ext:                                     # (una de las dos se hizo al revés)
        w = next(w for w in u["paredes"] if abs(w["dir"][0]) > 0.9)          # un tabique que se mueve a lo largo
        m = [(w["seg"][0][0] + w["seg"][1][0]) / 2, (w["seg"][0][1] + w["seg"][1][1]) / 2]
        r2 = run(barra, room_edits=[{"op": "pared", "p": m, "a": [m[0] + 0.3 * w["dir"][0], m[1] + 0.3 * w["dir"][1]]}])
        u2 = next(x for x in r2["units"] if x["id"] == u["id"])
        assert u2.get("editada_dentro") and not any("dentro de las viviendas" in x for x in r2["warnings"]), u["id"]
        mid = lambda t: [(t["seg"][0][0] + t["seg"][1][0]) / 2, (t["seg"][0][1] + t["seg"][1][1]) / 2]
        nuevo = [m[0] + 0.3 * w["dir"][0], m[1] + 0.3 * w["dir"][1]]       # el tabique que se arrastró está 0,30 más allá
        assert any(math.hypot(mid(t)[0] - nuevo[0], mid(t)[1] - nuevo[1]) < 0.05 for t in u2["paredes"]), u["id"]
        assert not any(math.hypot(mid(t)[0] - m[0], mid(t)[1] - m[1]) < 0.05 for t in u2["paredes"]), u["id"]

if __name__ == "__main__":
    test_segunda_fachada(); print("OK37")


def test_normativa_nacional():
    """v2.27: mínimos de la vivienda de la Normativa Nacional de Edificación, Higiene de la Vivienda (Congreso de
    Intendentes, MVOTMA y SAU, 2016). Las comprobaciones de cada plano los usan: un dormitorio principal de 2,55 m de lado
    ya no cumple (art. 8 b: 2,60 m) y uno de 9,2 m² sí (8,5 m²); un dormitorio adicional de 6,8 m² no cumple (art. 8 c:
    7 m²). La web guarda en el navegador solo las medidas cambiadas; en lo guardado antes de v2.27 (o en un proyecto
    anterior), un mínimo con su valor viejo pasa al nuevo y uno elegido a mano se respeta (STD_ANTES)."""
    import copy
    import re
    from engine import plans as P, standards as ST
    V = ST.DEFAULTS["vivienda"]
    nac = {"dorm_principal": (8.5, 2.60), "dorm_secundario": (7.0, 2.00), "estar_comedor": (10.0, 2.60),
           "estudio": (7.0, 2.00), "cocina": (4.0, 1.60), "bano": (3.0, 1.20), "bano_aux": (1.5, 0.80)}
    for k, (area, lado) in nac.items():
        assert (V[k]["min_area"], V[k]["min_side"]) == (area, lado), k
    assert V["pasillo"]["min_side"] == 0.90 and V["hall"]["min_side"] == 1.20
    assert ST.DEFAULTS["ventanas"]["iluminacion"] == 0.10 and ST.DEFAULTS["predio"]["retiro_ventanas"] == 3.0
    # los mínimos de v2.26, para comparar
    viejo = copy.deepcopy(V)
    viejo["dorm_principal"].update(min_area=10.0, min_side=2.50)
    viejo["dorm_secundario"]["min_area"] = 6.5
    rect = [(0.0, 0.0), (9.5, 0.0), (9.5, 8.0), (0.0, 8.0)]          # dormitorios de 3,20 y 2,80 m con 4,50 m de fondo
    corrido = lambda x: {"op": "pared", "p": (6.7, 5.75), "a": (x, 5.75)}          # el tabique entre los dos dormitorios
    menos_fondo = {"op": "pared", "p": (5.0, 3.5), "a": (5.0, 4.6)}                # el de los dormitorios y el pasillo
    def fallas(ed, viv=None):
        res = P.layout_unit(rect, 2, vivienda=viv, ediciones=list(enumerate(ed)))
        assert res["ediciones"] == list(range(len(ed))), res["ediciones"]
        return [c["msg"] for c in res["checks"] if not c.get("ok") and not c.get("info") and "ormitorio" in c["msg"]
                and "no entra" not in c["msg"]]
    assert fallas([]) == []
    assert fallas([corrido(6.05)]) == ["Dormitorio principal: lado 2.55 m < mínimo 2.60 m"]
    assert fallas([corrido(6.05)], viejo) == []
    assert fallas([corrido(6.2), menos_fondo]) == []                                 # 2,70 × 3,40 = 9,2 m²
    assert fallas([corrido(6.2), menos_fondo], viejo) == ["Dormitorio principal: 9.2 m² < mínimo 10.0 m²"]
    assert fallas([corrido(7.5), menos_fondo]) == ["Dormitorio 2: 6.8 m² < mínimo 7.0 m²"]   # 2,00 × 3,40
    assert fallas([corrido(7.5), menos_fondo], viejo) == []
    # web: la tabla de valores viejos nombra mínimos que existen y que cambiaron
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    antes = re.search(r"const STD_ANTES=(\{.*?\}\}\});", html).group(1)
    antes = json.loads(re.sub(r"([{,])(\w+):", r'\1"\2":', antes))
    assert antes == {"vivienda": {"dorm_principal": {"min_area": 10, "min_side": 2.5}, "dorm_secundario": {"min_area": 6.5},
                                  "estar_comedor": {"min_side": 2.5}, "estudio": {"min_area": 6.5},
                                  "bano": {"min_area": 2.4}}}, antes
    for estancia, valores in antes["vivienda"].items():
        for k, v in valores.items():
            assert V[estancia][k] != v, (estancia, k)
    # se guarda solo lo cambiado, y los valores viejos se pasan solo en lo guardado antes de v2.27
    assert "localStorage.setItem('trazo.std',JSON.stringify(Object.assign({_v:2},medidasCambiadas())))" in html
    assert "mezclarStd(STD,sv,viejo?STD_ANTES:null)" in html and "const viejo=!sv._v" in html
    assert "mezclarStd(STD,P.standards||{},verMenor(p.version_motor,'2.27')?STD_ANTES:null)" in html

if __name__ == "__main__":
    test_normativa_nacional(); print("OK38")


def test_dormitorio_placard():
    """v2.29: al repartir el frente entre los dormitorios, el principal conserva el ancho de su cama doble con el placard
    al costado (paso + cama + paso + placard: 3,20 m con las medidas por defecto) cuando el fondo no deja ponerlo al pie
    de la cama, mientras los demás dormitorios lleguen a su mínimo (criterio del usuario). Si el frente no alcanza, los
    demás no bajan de su mínimo y la ficha avisa que el placard no entra. Las medidas salen de «Equipamiento y muebles»."""
    import copy
    from engine import plans as P, standards as ST
    rect = lambda w, d: [(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)]          # dormitorios de 3,00 m de fondo

    def dorms(W, eq=None):
        res = P.layout_unit(rect(W, 4.0), 2, equip=eq)
        R = {r["id"]: r for r in res["rooms"]}
        ancho = lambda i: max(p[0] for p in R[i]["poly"]) - min(p[0] for p in R[i]["poly"])
        placard = any(e["room"] == "bed1" and e.get("name") == "Placard" for e in res["equipamiento"])
        fallas = [c["msg"] for c in res["checks"] if not c.get("ok") and not c.get("info") and "ormitorio" in c["msg"]]
        return ancho("bed1"), R["bed2"]["area"], placard, fallas
    for W in (9.0, 9.4):
        b1, a2, placard, fallas = dorms(W)
        assert abs(b1 - 3.20) < 1e-6 and placard and a2 >= 7.0 - 1e-6 and not fallas, (W, b1, a2, fallas)
    b1, a2, placard, fallas = dorms(8.8)            # no alcanza: el segundo conserva su mínimo y se avisa el placard
    assert b1 < 3.2 and a2 >= 7.0 - 1e-6 and not placard, (b1, a2)
    assert fallas == ["Dormitorio principal: no entra el placard (0.90 × 0.60 m con 0.60 m de paso delante)"], fallas
    eq = copy.deepcopy(ST.DEFAULTS["equipamiento"])
    eq["placard_fondo"] = 0.80
    b1, a2, placard, fallas = dorms(9.6, eq)        # un placard más profundo pide más ancho
    assert abs(b1 - 3.40) < 1e-6 and placard and not fallas, (b1, fallas)

if __name__ == "__main__":
    test_dormitorio_placard(); print("OK39")


def test_bano_cocina():
    """v2.30: toda vivienda lleva baño y cocina (norma nacional, arts. 17 y 21). Si el plano no los tiene, la calidad
    baja y la ficha lo dice; antes, una vivienda chica sin lugar para la cocina podía sacar 100. La cocina dentro del
    hall («Hall / Cocina») cuenta como cocina."""
    from engine import plans as P
    rect = lambda w, d: [(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)]
    res = P.layout_unit(rect(6.8, 5.0), 1)          # poco frente: el baño y el hall no dejan lugar para la cocina
    assert not any(r["kind"] == "kitchen" or "Cocina" in r["name"] for r in res["rooms"])
    fallas = [c["msg"] for c in res["checks"] if not c.get("ok") and not c.get("info")]
    assert fallas == ["Sin cocina: toda vivienda lleva una (norma nacional, art. 21)"] and res["score"] < 100, fallas
    completa = P.layout_unit(rect(9.5, 8.0), 2)
    assert completa["score"] == 100 and not any(c["msg"].startswith("Sin ") for c in completa["checks"])
    piezas = lambda *k: [{"kind": a, "name": b} for a, b in k]
    assert P._faltan(piezas(("bath", "Baño"), ("hall", "Hall / Cocina"))) == []
    assert [c["msg"] for c in P._faltan(piezas(("kitchen", "Cocina")))] == ["Sin baño: toda vivienda lleva uno (norma nacional, art. 17)"]

if __name__ == "__main__":
    test_bano_cocina(); print("OK40")


def test_medianeras_parciales():
    """R11.6 (primera parte, v2.31): una medianera que ocupa solo parte de un borde retira la huella solo a lo largo de
    su tramo; la huella queda escalonada. Antes, una medianera parcial con retiro retiraba el lado entero. La que va de
    esquina a esquina (o más larga) sigue cortando por una paralela al lindero; del lado de un extremo que llega a una
    esquina, el retiro sigue de largo. Sin retiro, la huella no cambia (solo marca el tramo ciego)."""
    from engine import geometry as G, massing as M
    fp = G.ensure_ccw([(0.0, 0.0), (20.0, 0.0), (20.0, 30.0), (0.0, 30.0)])    # predio de 20 × 30, lindero en x = 0
    med = lambda y0, y1, r: {"a": [0, y1], "b": [0, y0], "retiro": r}
    area = lambda meds: abs(G.area(M.apply_setbacks(fp, meds)))
    ancho_en = lambda meds, y: min(p[0] for p in G.clip_rect(M.apply_setbacks(fp, meds), -1, 21, y - 0.01, y + 0.01))
    assert abs(area([med(0, 30, 3)]) - 510) < 1e-6 and abs(area([med(-5, 35, 3)]) - 510) < 1e-6     # el lado entero
    assert abs(area([med(0, 10, 3)]) - 570) < 1e-6                                       # 10 m desde la esquina
    assert abs(ancho_en([med(0, 10, 3)], 5) - 3) < 1e-6 and abs(ancho_en([med(0, 10, 3)], 20)) < 1e-6
    assert abs(area([med(10, 20, 3)]) - 570) < 1e-6                                      # al medio: una muesca
    assert abs(ancho_en([med(10, 20, 3)], 15) - 3) < 1e-6 and abs(ancho_en([med(10, 20, 3)], 5)) < 1e-6
    assert abs(area([med(0, 10, 0)]) - 600) < 1e-6                                       # sin retiro, no cambia
    assert abs(area([med(0, 12, 0), med(12, 30, 3)]) - 546) < 1e-6                       # 0-12 ciega, 12-30 con 3 m
    res = generate({"footprint": [list(p) for p in fp], "height": 9, "params": {"medianeras": [med(0, 10, 3)]}})
    assert abs(abs(G.area(res["footprint"])) - 570) < 1e-6

if __name__ == "__main__":
    test_medianeras_parciales(); print("OK41")


def test_ascensores_por_nucleo():
    """R10.7 (v2.32): cada núcleo lleva los ascensores que piden las viviendas que sirve (las que tienen en él su
    recorrido más corto, por los niveles residenciales): 1 cada 60 y al menos 1 si el edificio necesita ascensor. En
    automático todos los núcleos son iguales (los del más cargado). Desde 10 niveles, el edificio lleva al menos 2 en
    total: el mínimo es por edificio (criterio del usuario). Un núcleo manual puede fijar los suyos y su frente toma las
    medidas de la normativa para esa cantidad; «ascensores» fija la misma cantidad en todos. Antes, la cantidad del
    edificio entero se ponía en cada núcleo (la cruz de 70 viviendas y 4 núcleos llevaba 8)."""
    from engine import standards as ST
    asc = lambda r: [c["ascensores"] for c in r["cores"]]
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "cruz_dos_lineas.json"), encoding="utf-8"))
    r = run(s["footprint"], centerlines=s["centerlines"])
    assert asc(r) == [1, 1, 1, 1] and r["metrics"]["core"]["elevators_total"] == 4, asc(r)
    barra = [[0, 0], [60, 0], [60, 16], [0, 16]]
    assert asc(run(barra, h=30)) == [1, 1]                                  # 10 niveles, 2 núcleos: 2 en el edificio
    uno = run(barra, h=27, cores_mode="manual", cores=[[30, 8]])            # un núcleo para 9 viviendas × 9 niveles
    assert asc(uno) == [2] and len(uno["units"]) * 9 > 60, (asc(uno), len(uno["units"]))
    assert asc(run(barra, h=36, cores_mode="manual", cores=[[30, 8]])) == [2]
    fijo = run(barra, h=36, cores_mode="manual", cores=[{"p": [30, 8], "ascensores": 1}])
    assert asc(fijo) == [1] and any("al menos 2 ascensores y tiene 1" in w for w in fijo["warnings"]), fijo["warnings"]
    mixto = run(barra, cores_mode="manual", cores=[{"p": [10, 8], "ascensores": 3}, [50, 8]])
    tres = ST.core_size(ST.DEFAULTS["nucleo"], 3.0, 3, 2.0)[0]
    assert asc(mixto) == [3, 1] and abs(mixto["cores"][0]["frente"] - tres) < 1e-6 and mixto["metrics"]["core"]["elevators_total"] == 4
    assert sum(1 for p in mixto["cores"][0]["parts"] if p["kind"] == "elevator") == 3
    assert asc(run(barra, ascensores="2")) == [2, 2] and asc(run(barra, h=9)) == [0, 0]    # todos 2; 9 m: sin ascensor
    cero = run(barra, h=36, cores_mode="manual", cores=[{"p": [30, 8], "ascensores": 0}])     # solo escalera
    assert asc(cero) == [0] and any("tiene 0: agrega dos" in w for w in cero["warnings"]), cero["warnings"]
    # la web: un control general y uno en la ficha de cada núcleo
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    assert 'id="ascensores"' in html and "ascensores:$('ascensores').value" in html and 'id="nAsc"' in html
    assert "if(asc!=='auto') nuevo.ascensores=+asc;" in html

if __name__ == "__main__":
    test_ascensores_por_nucleo(); print("OK42")


def test_sin_placards():
    """v2.33 (criterio del usuario): el placard es el armario del dormitorio, no una estancia. La franja sin luz entre el
    pasillo interno y el pasillo común lleva baños (con ducha), lavadero y un depósito de hasta 4 m² (editable; 0 = sin
    depósito), con el menor fondo con el que entran: los dormitorios ganan fondo. Lo que sobra: A, el principal al final
    del pasillo, en suite; si no se puede, B, baños, lavadero y depósito más grandes (hasta su máximo); si aún sobra, C,
    sin uso y con aviso. El pasillo interno termina en la última puerta. La ochava (fachada oblicua) es un estudio."""
    from engine import plans as P, standards as ST, geometry as G, dxf
    rect = lambda w, d: [(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)]
    fondo = lambda D: (lambda p, q: abs(p[1] - D) < 0.05 and abs(q[1] - D) < 0.05)
    caja = lambda res: {r["id"]: G.bbox(r["poly"]) for r in res["rooms"]}
    con = lambda res, rid: {q["kind"] for q in res["equipamiento"] if q["room"] == rid}
    # 3 dormitorios de 16,27 × 6,50 (U02 de «Esquina en L con ochava», que tenía un placard de 14,6 m²): A, en suite
    res = P.layout_unit(rect(16.27, 6.5), 3, fondo(6.5))
    B = caja(res)
    assert not [r for r in res["rooms"] if "Placard" in r["name"]] and not res["sin_uso"] and res["score"] == 100
    assert abs(B["bed1"][2] - 16.27) < 1e-6 and abs(B["hallway"][2] - B["bed1"][0]) < 1e-6    # el pasillo, hasta su puerta
    suite = next(r for r in res["rooms"] if r["id"] == "bath2")
    assert suite["name"] == "Baño en suite" and suite["area"] <= ST.DEFAULTS["vivienda"]["bano"]["max_area"] + 1e-6
    assert any({d["a"], d["b"]} == {"bed1", "bath2"} for d in res["doors"])
    assert all(B[k][3] - B[k][1] >= 3.6 for k in ("bed2", "bed3")), B          # antes, 3,10 m de fondo
    dep = [r for r in res["rooms"] if r["kind"] == "storage"]
    assert len(dep) == 1 and dep[0]["area"] <= 4.0 + 1e-6 and dep[0]["name"] == "Depósito"
    assert {"ducha", "inodoro", "lavatorio"} <= con(res, "bath1") and {"ducha", "inodoro", "lavatorio"} <= con(res, "bath2")
    # 2 dormitorios de 11,73 × 6,50: sin suite, los dos baños con ducha, depósito y dormitorios de 3,50 m de fondo
    res = P.layout_unit(rect(11.73, 6.5), 2, fondo(6.5))
    B = caja(res)
    assert "bath2" in B and {"ducha", "inodoro"} <= con(res, "bath2") and not any("suite" in r["name"] for r in res["rooms"])
    assert min(B["bed1"][3] - B["bed1"][1], B["bed2"][3] - B["bed2"][1]) >= 3.5 - 1e-6 and res["score"] == 100
    assert 1.0 <= next(r["area"] for r in res["rooms"] if r["kind"] == "storage") <= 4.0 + 1e-6
    # sin depósito (máximo 0): no hay; lo que sobra va a la suite (A)
    V0 = ST.merged({"vivienda": {"deposito": {"max_area": 0}}})["vivienda"]
    res = P.layout_unit(rect(11.73, 6.5), 2, fondo(6.5), V0)
    assert not [r for r in res["rooms"] if r["kind"] == "storage"] and "Baño en suite" in [r["name"] for r in res["rooms"]]
    # muy profunda (10,15 m): el depósito junto al hall y lo que queda junto al pasillo común, C: sin uso, con aviso
    res = P.layout_unit(rect(8.7, 10.15), 2, fondo(10.15))
    dep = next(r for r in res["rooms"] if r["kind"] == "storage")
    assert dep["area"] <= 4.0 + 1e-6 and any({d["a"], d["b"]} == {"hall", "storage"} for d in res["doors"])
    assert len(res["sin_uso"]) == 1 and abs(G.area(res["sin_uso"][0])) > 5
    assert [c["msg"] for c in res["checks"] if not c["ok"]] == ["Sin uso: 6.6 m² junto al pasillo común: la vivienda "
                                                                 "tiene 10.2 m de fondo"], res["checks"]
    # poco profunda (5,50 m): el pasillo junto al pasillo común termina en el último dormitorio, que toma lo que queda
    res = P.layout_unit(rect(13.3, 5.5), 2, fondo(5.5))
    B = caja(res)
    assert abs(B["hallway"][2] - B["bed2"][0]) < 1e-6 and abs(B["bed2"][1]) < 1e-6 and res["score"] == 100, B
    # en los ejemplos: ningún placard; los depósitos de la franja, hasta 4 m² (un bolsillo, hasta 4,5)
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "L_ochava.json"), encoding="utf-8"))
    r = run(s["footprint"], h=s["height"])
    salas = [x for u in r["units"] for x in u["rooms"]]
    assert not [x for x in salas if "Placard" in x["name"]] and all(x["area"] <= 4.5 for x in salas if x["kind"] == "storage")
    u3 = next(u for u in r["units"] if u["id"] == "U03")                       # la ochava: un estudio con su ventana
    est = next(x for x in u3["rooms"] if x["id"].startswith("annex"))
    assert est["name"] == "Estudio" and any(w["room"] == est["id"] for w in u3["ventanas"]) and u3["plan_score"] == 100
    assert r["metrics"]["plan_score"] >= 85                                      # antes, 80
    # una barra de 24 m de crujía (viviendas de 10,50 m de fondo): lo sin uso, también en el DXF y en la web
    r = run([[0, 0], [60, 0], [60, 24], [0, 24]])
    assert any(u["sin_uso"] for u in r["units"]) and "Trazo_L00_SinUso" in dxf.result_to_dxf(r)
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    assert "(u.sin_uso||[]).forEach" in html and "deposito:'Depósito (0 = sin depósito)'" in html and " Sin uso</span>" in html
    rh = open(os.path.join(os.path.dirname(__file__), "..", "rhino", "trazo_rhino.py"), encoding="utf-8").read()
    assert 'u.get("sin_uso", [])' in rh and '"::SinUso"' in rh

if __name__ == "__main__":
    test_sin_placards(); print("OK43")


def test_pasillo_sin_puntas():
    """R3.7 (pedido del usuario): el pasillo común termina en la última puerta. En la punta libre de un pasillo de borde
    (núcleo manual atrás y una sola medianera, como en la captura del predio de 10 x 28), la vivienda del extremo toma
    todo el ancho, entra por la punta del pasillo y las viviendas se reparten parejas. Después de un cruce (las L), la
    franja del ala vecina cruza la punta y la vivienda del otro lado entra por el pasillo que queda."""
    from engine import plans as P
    d = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "entre_medianeras.json"), encoding="utf-8"))
    base = dict(medianeras=[d["medianeras"][1]], cores_mode="manual", cores=[[5, 25]])
    dos = [{"name": "2 dorm", "area": 75, "percent": 100, "dorms": 2}]
    r = run(d["footprint"], h=18, unit_mix=dos, **base)       # antes: el pasillo llegaba a la fachada (y = 0,35)
    (pas,) = r["corridors"]
    y0 = min(p[1] for p in pas)
    assert 9.5 < y0 < 10.5, pas
    u1, u2 = r["units"]
    xs, ys = [p[0] for p in u2["poly"]], [p[1] for p in u2["poly"]]
    assert abs(min(xs) - 0.35) < 1e-6 and abs(max(xs) - 9.65) < 1e-6 and abs(min(ys) - 0.35) < 1e-6   # al frente, todo el ancho
    assert u2.get("al_frente") and not u1.get("al_frente") and abs(max(ys) + 0.3 - y0) < 0.01         # y el tabique
    assert abs(u1["area"] - u2["area"]) < 3 and u1["plan_score"] == 100 and u2["plan_score"] == 100
    ent = next(x for x in u2["doors"] if x["entry"])            # la entrada, en la punta del pasillo
    assert all(0.35 - 1e-6 <= p[0] <= 2.35 + 1e-6 and abs(p[1] - max(ys)) < 0.01 for p in (ent["p"], ent["q"])), ent
    assert max(ys) - min(ys) <= P.fondo_sin_tira() + 1e-6       # no más honda que lo que el plano aprovecha entero
    assert not any("Fondo de saco" in w for w in r["warnings"]) and u2["saco"] < 18 and r["metrics"]["efficiency"] > 67
    # con 3 y 2 dormitorios, al frente va la de menos dormitorios: su frente es el ancho del predio
    r3 = run(d["footprint"], h=18, **base)
    assert [u["type"] for u in r3["units"]] == ["3 dorm", "2 dorm"] and all(u["plan_score"] == 100 for u in r3["units"])
    # la etapa «pasillo y núcleos» ya muestra el pasillo corto
    rc = generate({"footprint": d["footprint"], "height": 18, "stage": "corridor", "params": dict(base, unit_mix=dos)})
    assert rc["corridors"] == r["corridors"]
    # el tabique entre las dos se arrastra (R4.4) y el pasillo lo sigue; unidas a mano, el pasillo vuelve a la fachada
    t = max(ys) + 0.15
    rt = run(d["footprint"], h=18, unit_mix=dos, unit_edits=[{"op": "tabique", "p": [6, t], "a": [6, 8.5]}], **base)
    assert abs(min(p[1] for p in rt["corridors"][0]) - 8.65) < 0.01
    rf = run(d["footprint"], h=18, unit_mix=dos, unit_edits=[{"op": "fusionar", "p": [6, t]}], **base)
    assert len(rf["units"]) == 1 and abs(min(p[1] for p in rf["corridors"][0]) - 0.35) < 0.01
    # en automático las dos puntas llevan núcleo: nada cambia
    ra = run(d["footprint"], h=18, unit_mix=dos, medianeras=[d["medianeras"][1]])
    assert len(ra["cores"]) == 2 and abs(min(p[1] for p in ra["corridors"][0]) - 0.35) < 0.01
    assert not any(u.get("al_frente") for u in ra["units"])
    # el plano con la entrada en un tramo del borde: el hall va a ese extremo (derecho o al revés); si no entra, se avisa
    rect = [(0, 0), (12, 0), (12, 6.5), (0, 6.5)]
    fac = lambda p, q: abs(p[1] - 6.5) < 1e-6 and abs(q[1] - 6.5) < 1e-6
    for tramo in ((0.0, 2.0), (10.0, 12.0)):
        res = P.layout_unit(rect, 2, fac, entrada=tramo)
        e = next(x for x in res["doors"] if x.get("entry"))
        assert tramo[0] - 0.05 <= min(e["p"][0], e["q"][0]) and max(e["p"][0], e["q"][0]) <= tramo[1] + 0.05, (tramo, e)
        assert res["score"] == 100, res["checks"]
    res = P.layout_unit(rect, 2, fac, entrada=(5.0, 5.5))
    assert any(c["msg"] == "La puerta de entrada no da al pasillo común" for c in res["checks"]) and res["score"] < 100
    # la L: el pasillo del ala larga termina en el cruce (antes seguía 6,65 m hasta la fachada oeste); la franja del ala
    # oeste baja hasta el tabique con U03, que entra por el pasillo que queda
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "L.json"), encoding="utf-8"))
    r = run(s["footprint"], h=s["height"])
    ew = max(r["corridors"], key=lambda c: max(p[0] for p in c) - min(p[0] for p in c))
    assert abs(min(p[0] for p in ew) - 7.0) < 0.01, ew
    oeste = next(u for u in r["units"] if max(p[0] for p in u["poly"]) < 7 and min(p[1] for p in u["poly"]) < 7)
    assert abs(min(p[1] for p in oeste["poly"]) - 6.15) < 0.01 and oeste["plan_score"] == 100
    u03 = next(u for u in r["units"] if min(p[0] for p in u["poly"]) < 1 and max(p[1] for p in u["poly"]) < 6)
    e = next(x for x in u03["doors"] if x["entry"])
    assert min(e["p"][0], e["q"][0]) >= 7.0 - 1e-6 and u03["door"][0] >= 7.0 and u03["plan_score"] == 100
    assert r["metrics"]["mix"]["count"] == 10 and r["metrics"]["mix"]["match_score"] == 100     # antes, 9 y 94,4
    # el patio central: en las esquinas del anillo, del otro lado del pasillo hay otra ala: no hay vivienda al frente
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "patio_central.json"), encoding="utf-8"))
    r = run(s["footprint"], h=s["height"], **({"patios_mode": "manual", "patios": s["patios"]} if s.get("patios") else {}))
    assert not any(u.get("al_frente") for u in r["units"])

if __name__ == "__main__":
    test_pasillo_sin_puntas(); print("OK44")


def test_terreno_rectangular():
    """Pedido del usuario: la masa de un terreno rectangular sin Rhino ni AutoCAD («1 · Masa → Terreno rectangular»):
    frente × fondo, qué linderos son medianeras y los retiros. Los linderos sin medianera (y el frente) se descuentan en
    la web; las medianeras van con su retiro y las recorta el motor. El terreno se guarda en el proyecto."""
    import re
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    for i in ("ter_frente", "ter_fondo", "ter_m_i", "ter_m_d", "ter_m_b", "ter_r_i", "ter_r_d", "ter_r_b", "ter_r_f"):
        assert re.search(r'<input[^>]*\bid="%s"' % i, html), i
    cuerpo = lambda f: html.split(f, 1)[1].split("\nfunction ", 1)[0].split("\nasync function ", 1)[0]
    masa = cuerpo("function masaDelTerreno(")
    for t in ("x0=m.i?0:r.i", "x1=W-(m.d?0:r.d)", "y0=r.f", "y1=D-(m.b?0:r.b)", "retiro:r.d", "retiro:r.b", "retiro:r.i"):
        assert t in masa, t
    assert "terrenoRectangular()" in html and "selLabel('__terreno'" in cuerpo("function terrenoRectangular(")
    assert "p.terreno=terreno" in cuerpo("function proyecto(){") and "terreno:p.terreno" in cuerpo("function abrirProyecto(")
    assert "terreno=m.terreno||null" in cuerpo("function setMass(") and "terreno=null" in cuerpo("async function nuevo(")
    assert "lote()" in cuerpo("function drawDims(") and "lote()" in cuerpo("function fit(")
    # lo que arma la web para 10 x 30 con medianeras a los costados, retiro frontal de 3 m y medianera de fondo con
    # retiro de 4 m: la masa va de y = 3 a y = 26 (el motor descuenta los 4 m del fondo)
    fp = [[0, 3], [10, 3], [10, 30], [0, 30]]
    meds = [{"a": [10, 3], "b": [10, 30], "retiro": 0}, {"a": [10, 30], "b": [0, 30], "retiro": 4},
            {"a": [0, 30], "b": [0, 3], "retiro": 0}]
    proyecto = {"trazo": "proyecto", "formato": 1, "name": "Terreno 10 × 30 m", "footprint": fp, "height": 15,
                "stage": "plans", "params": {"medianeras": meds},
                "terreno": {"frente": 10, "fondo": 30, "medianeras": {"i": True, "d": True, "b": True},
                            "retiros": {"i": 0, "d": 0, "b": 4, "f": 3}}}
    r = generate(json.loads(json.dumps(proyecto)))              # el motor no lee el terreno: es solo para la web
    ys = [p[1] for p in r["footprint"]]
    assert abs(min(ys) - 3) < 1e-6 and abs(max(ys) - 26) < 1e-6 and r["units"], r["footprint"]
    assert r["metrics"].get("between")                          # entre medianeras: franja central con el núcleo
    # 20 x 35, lindero izquierdo sin medianera con retiro de 4 m, medianera a la derecha, retiros de 5 m al frente y al
    # fondo (sin medianera): la web ya descuenta los retiros; el motor deja la masa como está
    r = run([[4, 5], [20, 5], [20, 30], [4, 30]], medianeras=[{"a": [20, 5], "b": [20, 30], "retiro": 0}])
    xs, ys = [p[0] for p in r["footprint"]], [p[1] for p in r["footprint"]]
    assert (min(xs), max(xs), min(ys), max(ys)) == (4, 20, 5, 30) and r["units"]

if __name__ == "__main__":
    test_terreno_rectangular(); print("OK45")
