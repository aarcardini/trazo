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
    assert not sin_fachada(r) and m["egress_max"] <= 30 and m["efficiency"] > 65 and m["plan_score"] >= 85, m
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
    assert m["core_count"] == 2 and m["plan_score"] == 100 and not r.get("dark_zones") and not m.get("between"), m
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
