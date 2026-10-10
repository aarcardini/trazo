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
    assert m["core_count"] == 2 and m["plan_score"] == 100 and not m.get("between"), m
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
    # U y T: ninguna vivienda a oscuras; las esquinas sin luz se marcan y se avisan
    for fp in ([[0, 0], [60, 0], [60, 45], [44, 45], [44, 16], [16, 16], [16, 45], [0, 45]],
               [[0, 0], [70, 0], [70, 16], [43, 16], [43, 45], [27, 45], [27, 16], [0, 16]]):
        r = run(fp)
        assert r["units"] and not oscuras(r) and r["metrics"].get("dark_area", 0) > 10, r["metrics"]
        assert any("Esquinas sin luz" in w for w in r["warnings"]), r["warnings"]
    # un lote en trapecio con medianeras en los lados largos no se vacía: contra una medianera no se bloquea
    fp = [[0, 0], [47.5, 20.1], [15.2, 70.1], [-18.1, 56.0]]
    r = run(fp, h=6, medianeras=[{"a": fp[1], "b": fp[2], "retiro": 0}, {"a": fp[3], "b": fp[0], "retiro": 0}])
    assert len(r["units"]) > 4, len(r["units"])
    # el plano de una vivienda con parte del fondo sin luz: estancias habitables con luz y el resto, depósito
    res = P.layout_unit([(0, 0), (12, 0), (12, 8), (0, 8)], 2, lambda p, q: min(p[0], q[0]) >= 3.0)
    dep = [rm for rm in res["rooms"] if rm["name"] == "Depósito"]
    assert dep and max(G.bbox(d["poly"])[2] for d in dep) <= 3.05, [(rm["name"], G.bbox(rm["poly"])) for rm in res["rooms"]]
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
    r = run(s["footprint"], centerlines=s["centerlines"])
    assert not [u["id"] for u in r["units"] if any("Lavadero" in c["msg"] and not c["ok"] for c in u["checks"])]
    assert r["metrics"]["plan_score"] >= 60, r["metrics"]["plan_score"]

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
    cambio = re.compile(r"\b(centerlines|coresManual|medianeras|patios)(\[[^\]]*\])*(\.retiro)?(=(?![=>])|\.(push|pop|splice)\()|\bpl\.splice\(|\bpl\[drag\.vi\]=")
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
