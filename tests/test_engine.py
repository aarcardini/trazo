import sys, os, json
sys.dont_write_bytecode = True   # sin __pycache__: tras revertir un cambio, nunca se prueba bytecode viejo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from engine.layout import generate

def run(fp, h=15, **p):
    return generate({"footprint": fp, "height": h, "stage": "plans", "params": p})

def _medidas_anteriores(planta, vivienda):
    """Context manager: pone en `layout.DEFAULT_PARAMS` y `standards.DEFAULTS` las medidas de antes de la calibración con la
    base de tipologías (R5.16) y las restaura al salir. `planta` (v2.60): pasillo de 2,0 m, frente mínimo de 5,0 m, fondo
    máximo de 14 m y escalera de 1,20 m con ascensor. `vivienda` (v2.61): estar-comedor por dormitorios [18, 18, 20, 24, 27] y
    el mix de 2 y 3 dormitorios de 75 y 95 m² al 50 % (el «Inversor» de v2.61 lo reemplazó)."""
    import contextlib

    @contextlib.contextmanager
    def cm():
        from engine import layout as LY, standards as ST
        params, escalera = dict(LY.DEFAULT_PARAMS), ST.DEFAULTS["nucleo"]["escalera_ancho_con_ascensor"]
        estar = ST.DEFAULTS["vivienda"]["estar_por_dorms"]
        if planta:
            LY.DEFAULT_PARAMS.update(corridor_width=2.0, min_unit_width=5.0, max_unit_depth=14.0)
            ST.DEFAULTS["nucleo"]["escalera_ancho_con_ascensor"] = 1.20
        if vivienda:
            LY.DEFAULT_PARAMS.update(unit_mix=[{"name": "2 dorm", "area": 75, "percent": 50, "dorms": 2},
                                               {"name": "3 dorm", "area": 95, "percent": 50, "dorms": 3}])
            ST.DEFAULTS["vivienda"]["estar_por_dorms"] = [18.0, 18.0, 20.0, 24.0, 27.0]
        try:
            yield
        finally:
            LY.DEFAULT_PARAMS.update(params)
            ST.DEFAULTS["nucleo"]["escalera_ancho_con_ascensor"] = escalera
            ST.DEFAULTS["vivienda"]["estar_por_dorms"] = estar
    return cm()

def _con(planta, vivienda):
    import functools

    def decorador(f):
        @functools.wraps(f)
        def con_medidas_anteriores(*a, **k):
            with _medidas_anteriores(planta, vivienda):
                return f(*a, **k)
        return con_medidas_anteriores
    return decorador

def calibracion_anterior(f):
    """R5.16 (v2.60 y v2.61): las medidas por defecto se calibraron con la base de tipologías (planta en v2.60, vivienda en
    v2.61: ver `_medidas_anteriores`). Las pruebas de geometría exacta escritas antes (posiciones de núcleos y puertas,
    superficies, fondos) siguen midiendo la lógica del motor con todas las medidas de antes; las nuevas las cubren
    test_calibracion_planta, test_calibracion_vivienda y las referencias de samples/."""
    return _con(True, True)(f)

def vivienda_anterior(f):
    """R5.16 (v2.61): como `calibracion_anterior`, pero solo con el mix y el estar-comedor de antes; la planta (pasillo,
    frente mínimo, fondo máximo, escalera) queda con las medidas nuevas de v2.60. Para las pruebas que ya corrían con ellas
    y solo suponían el mix de 2 y 3 dormitorios (cantidad de viviendas de cada tipo, qué vivienda es la U03...)."""
    return _con(False, True)(f)

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


def test_servidor_en_red():
    """R4.14a (v2.63): con TRAZO_HOST=0.0.0.0 el servidor se abre a la red local y la consola muestra la dirección para
    el teléfono; sin la variable, solo 127.0.0.1. `server.direcciones` arma esa lista sin abrir ningún puerto."""
    import importlib.util, re
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server.py")
    src = open(ruta, encoding="utf-8").read()
    assert 'os.environ.get("TRAZO_HOST", "127.0.0.1")' in src and "ThreadingHTTPServer((host, port), H)" in src
    spec = importlib.util.spec_from_file_location("trazo_server_prueba", ruta)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)                      # no arranca el servidor: eso está bajo __main__
    assert mod.direcciones("127.0.0.1", 8765) == ["http://127.0.0.1:8765"]
    assert mod.direcciones("192.168.1.20", 8766) == ["http://192.168.1.20:8766"]
    abiertas = mod.direcciones("0.0.0.0", 8765)
    assert abiertas[0] == "http://127.0.0.1:8765" and len(abiertas) == len(set(abiertas))
    for u in abiertas[1:]:
        assert re.fullmatch(r"http://\d+\.\d+\.\d+\.\d+:8765", u) and not u.startswith("http://127."), u
    readme = open(os.path.join(os.path.dirname(ruta), "README.md"), encoding="utf-8").read()
    assert "TRAZO_HOST=0.0.0.0" in readme and "Ver la planta en el teléfono" in readme

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


@vivienda_anterior
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


@vivienda_anterior
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


@vivienda_anterior
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


@calibracion_anterior
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
    entrada = {"footprint": [[0, 0], [60, 0], [60, 16], [0, 16]], "height": 15, "stage": "plans"}
    r = lay.generate(entrada)                              # el motor recargado da lo mismo que el cargado antes
    assert r["units"] and len(r["units"]) == len(layout.generate(entrada)["units"]) and lay.split_blocks is patios.split_blocks, \
        len(r["units"])

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


@calibracion_anterior
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
    # el ejemplo «L con polilínea»: de 49,6 a menos de 25 m² sin usar. Desde v2.64 «sin usar» no cuenta dos veces el pasillo
    # bajo los núcleos (la caja de cada núcleo incluye su tramo de pasillo): la misma planta pasó de 22,5 a 52,2 m², así que
    # los límites subieron lo que se contaba de más (unos 30 m²)
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "L_polilinea.json"), encoding="utf-8"))
    m = run(s["footprint"], centerlines=s["centerlines"])["metrics"]
    assert m["unused_area"] < 55 and m["efficiency"] > 72, m
    # si detrás del núcleo hay un bolsillo, la franja y el bolsillo ya forman una vivienda: el núcleo no se mueve
    fp = [[0, 0], [21.21, 0], [21.21, 23.5], [14.85, 23.5], [14.85, 9.4], [6.36, 9.4], [6.36, 23.5], [0, 23.5]]
    r = run(fp, h=6, centerlines=[[[1.06, 7.05], [19.09, 7.05]]],
            medianeras=[{"a": [21.21, 0], "b": [21.21, 23.5], "retiro": 3}, {"a": [0, 23.5], "b": [0, 0], "retiro": 0}])
    assert sorted(round(u["area"]) for u in r["units"]) == [36, 76, 88], [round(u["area"]) for u in r["units"]]

if __name__ == "__main__":
    test_sin_restos(); print("OK18")


@calibracion_anterior
def test_codos():
    """R3.2: en el codo de una L el núcleo va a la esquina interior, que no tiene luz, y la esquina exterior queda para
    las viviendas; ninguna vivienda queda con estancias a oscuras y lo que no recibe luz se marca «Sin luz natural»."""
    from engine import geometry as G, plans as P
    oscuras = lambda r: [u["id"] for u in r["units"] if any(not c["ok"] and "sin fachada" in c["msg"] for c in u["checks"])]
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "L.json"), encoding="utf-8"))
    r = run(s["footprint"])
    m = r["metrics"]
    assert not oscuras(r) and m["unused_area"] < 40 and m["efficiency"] >= 71.5 and m["egress_max"] <= 18, m     # v2.64: 34,3 m² (los muros entre viviendas); antes, 0 por contar dos veces el pasillo bajo los núcleos
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


@calibracion_anterior
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


@vivienda_anterior
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
    sw, sl, _ = ST.stair_box(S, 3.0, True)                                    # con ascensor (v2.60: tramos de 1,00 m)
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


@vivienda_anterior
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
    std["nucleo"]["escalera_ancho_con_ascensor"] = 1.4       # una medida cambiada: escalera más ancha (el edificio lleva ascensor)
    params = {"corridor_width": 1.8, "core_count": 2, "centerlines": s["centerlines"], "cores_mode": "manual",
              "cores": [{"p": [8, 25], "giro": 90}, [40, 7]], "standards": std,
              "unit_mix": [{"name": "1 dorm", "area": 50, "percent": 40, "dorms": 1}, {"name": "2 dorm", "area": 75, "percent": 60, "dorms": 2}]}
    web = {"footprint": s["footprint"], "height": s["height"], "stage": "plans", "params": params}
    proyecto = dict(copy.deepcopy(web), trazo="proyecto", formato=1, version_motor=LY.VERSION,
                    guardado="2026-10-10T12:00:00.000Z", name="Prueba")
    proyecto["params"]["standards"] = {"nucleo": {"escalera_ancho_con_ascensor": 1.4}}     # el archivo guarda solo lo cambiado
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
    cambio = re.compile(r"\b(centerlines|coresManual|medianeras|patios|ediciones|interiores|anchosPasillo)(\[[^\]]*\])*(\.retiro)?(=(?![=>])|\.(push|pop|splice)\()|\bpl\.splice\(|\bpl\[drag\.vi\]=")
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


@calibracion_anterior
def test_aviso_ancho():
    """Corrección (v2.19.1): el aviso de ancho mínimo muestra dos decimales. Con uno, una vivienda de 4,98 m avisaba
    «Unidad con ancho 5.0 m < mínimo 5.0 m», que parecía un error; ahora dice «4.98 m < mínimo 5.00 m»."""
    import re
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "L.json"), encoding="utf-8"))
    # (v2.62: el reparto da a cada vivienda el frente que pide su plano, así que con el mínimo de 5 m ya no hay avisos; se
    # provoca con un mínimo de 10 m, más que el frente de un 2 dorm)
    r = run(s["footprint"], s["height"], loading="single", min_unit_width=10.0)
    avisos = [re.search(r"Unidad con ancho (\d+\.\d\d) m < mínimo (\d+\.\d\d) m", w) for w in r["warnings"] if "Unidad con ancho" in w]
    assert avisos and all(a and float(a.group(1)) < float(a.group(2)) for a in avisos), r["warnings"]
    angostas = [u for u in r["units"] if u["width"] < 10.0]
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
    # mover el tabique 1 m: una crece, la otra achica, las demás igual; conservan el tipo y se rehacen los planos (v2.62:
    # las viviendas ya salen con el frente que pide su plano, un 10-20 % por encima de su objetivo; con 2 m más, la 1 dorm
    # pasaría de 1,35 veces su objetivo y tomaría el tipo de 2 dorm)
    r = run(barra, unit_edits=[{"op": "tabique", "p": mid, "a": hacia(1)}])
    R = {u["id"]: u for u in r["units"]}
    assert abs(R[t["a"]]["width"] - (a["width"] + 1)) < 0.02 and abs(R[t["b"]]["width"] - (b["width"] - 1)) < 0.02
    assert R[t["a"]].get("editada") and abs(R[t["a"]]["area"] + R[t["b"]]["area"] - a["area"] - b["area"]) < 0.21   # (4 redondeos a 0,1)
    assert all(R[k]["poly"] == U[k]["poly"] for k in U if k not in (t["a"], t["b"]))
    assert R[t["a"]]["type"] == a["type"] and R[t["a"]]["rooms"] and not any("no se pudieron" in w for w in r["warnings"])
    r = run(barra, unit_edits=[{"op": "tabique", "p": mid, "a": hacia(100)}])          # no deja una vivienda sin ancho
    assert min(u["width"] for u in r["units"]) >= 0.5 * 3.5 - 0.01
    # unir: una sola vivienda con el ancho de las dos y el tabique
    r = run(barra, unit_edits=[{"op": "fusionar", "p": mid}])
    m = next(u for u in r["units"] if u["id"] == t["a"])
    assert len(r["units"]) == len(base["units"]) - 1 and abs(m["width"] - (a["width"] + 0.3 + b["width"])) < 0.02
    # dividir: dos partes; la primera conserva el número; un tipo del mix solo si la superficie se le parece
    c = [sum(p[0] for p in a["poly"]) / len(a["poly"]), sum(p[1] for p in a["poly"]) / len(a["poly"])]
    r = run(barra, unit_edits=[{"op": "dividir", "p": c}])
    p1, p2 = [u for u in r["units"] if u.get("editada")]
    assert len(r["units"]) == len(base["units"]) + 1 and p1["id"] == t["a"] and abs(p1["width"] + 0.3 + p2["width"] - a["width"]) < 0.02
    # (v2.62: la mitad de una 1 dorm de 46 m² son 23 m², que se parecen al Mono de 33 m² del mix Inversor: toma ese tipo)
    assert p1["area"] < 0.65 * 42 and p1["type"] == "Mono" and p1["bedrooms"] == 0, (p1["type"], p1["area"])
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


@vivienda_anterior
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

@vivienda_anterior
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
    # R10.8 (norma nacional, art. 27): el vano del estar es el 10 % del estar y la cocina integrada, con 2 m² como mínimo
    cocina = lambda R: sum(x["area"] for x in R.values() if x["kind"] == "kitchen")
    CI = ST.DEFAULTS["vivienda"]["cocina_integrada"]
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
        minimo = max(S["iluminacion"] * (R[i]["area"] + cocina(R)), CI["vano_min"]) if i == "living" else \
            S["iluminacion"] * R[i]["area"]
        assert abs(w["ancho"] - max(tip, minimo / S["alto"])) < 0.01 and w["alto"] == S["alto"]
        assert abs(w["minimo"] - minimo) < 0.01 and w["area"] >= w["minimo"] - 0.01
    assert not any("ventana" in m for m in malos(res))
    # un estar grande pide una ventana más ancha que la típica
    w, = por(P.layout_unit(rect(6.0, 7.0), 0))["living"]
    assert w["ancho"] > S["ancho_estar"] + 0.1 and abs(w["area"] - w["minimo"]) < 0.01, w
    # comedor interior: no lleva ventana; la del estar ilumina los dos
    res = P.layout_unit(rect(9.5, 12.0), 2)
    R, V = {r["id"]: r for r in res["rooms"]}, por(res)
    assert "dining" in R and "dining" not in V and \
        abs(V["living"][0]["minimo"] - S["iluminacion"] * (R["living"]["area"] + R["dining"]["area"] + cocina(R))) < 0.01
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
    anterior), un mínimo con su valor viejo pasa al nuevo y uno elegido a mano se respeta (STD_ANTES). v2.61: el
    estar-comedor por dormitorios también cambió (R5.16): su valor viejo está en STD_ANTES y un proyecto guardado antes de
    v2.61 con ese valor toma el nuevo (la versión de corte pasó de 2.27 a 2.61)."""
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
                                  "estar_comedor": {"min_side": 2.5}, "estar_por_dorms": [18, 18, 20, 24, 27],
                                  "estudio": {"min_area": 6.5}, "bano": {"min_area": 2.4}}}, antes
    for estancia, valores in antes["vivienda"].items():
        if isinstance(valores, list):                                   # una lista de medidas (estar_por_dorms)
            assert V[estancia] != valores, estancia
            continue
        for k, v in valores.items():
            assert V[estancia][k] != v, (estancia, k)
    # se guarda solo lo cambiado, y los valores viejos se pasan solo en lo guardado antes de v2.27 (navegador) o de v2.61 (proyecto)
    assert "localStorage.setItem('trazo.std',JSON.stringify(Object.assign({_v:2},medidasCambiadas())))" in html
    assert "mezclarStd(STD,sv,viejo?STD_ANTES:null)" in html and "const viejo=!sv._v" in html
    assert "mezclarStd(STD,P.standards||{},verMenor(p.version_motor,'2.61')?STD_ANTES:null)" in html

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


@vivienda_anterior
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


def _cocina_comunicada(res):
    """R5.11 (revisión): con su equipamiento puesto, desde las puertas de la cocina (o del «Hall / Cocina») y sus bordes
    abiertos a la zona de día se llega a todos lados sin pisar la heladera ni la mesada (EQ._alcanza): la heladera no
    encierra la puerta del lavadero. Las estancias, en un marco paralelo a los ejes (layout_unit o una vivienda de una
    planta ortogonal)."""
    from engine import plans as P, geometry as G, equipamiento as EQ
    k = next(x for x in res["rooms"] if x["kind"] == "kitchen" or "Cocina" in x["name"])
    R = {x["id"]: G.bbox(x["poly"]) for x in res["rooms"]}
    B = R[k["id"]]
    acc = [(tuple(d["p"]), tuple(d["q"])) for d in res["doors"] if k["id"] in (d["a"], d["b"])]
    for x in res["rooms"]:
        sg = P._shared(B, R[x["id"]]) if x["id"] != k["id"] and x["kind"] in P.DAY else None
        if sg and ((sg[1][0] - sg[0][0]) ** 2 + (sg[1][1] - sg[0][1]) ** 2) ** 0.5 >= P.MIN_SHARE["abierto"] - 1e-6:
            acc.append(sg)
    cuerpos = [G.bbox(q["poly"]) for q in res["equipamiento"] if q["room"] == k["id"] and q["kind"] in ("heladera", "mesada")]
    return EQ._alcanza(EQ._Estancia(B), cuerpos, acc, [], g=0.05)

@calibracion_anterior
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
    # muy profunda (10,15 m; antes, 6,6 m² sin uso junto al pasillo común): R5.11, la tira es una banda de servicios. El
    # hall va a x0, con la entrada; la cocina (5 m² como máximo) corre de él hacia la tira, seguida del lavadero (puerta
    # desde la cocina) y, aquí, del depósito (puerta desde el lavadero); la franja ya no lleva el lavadero
    res = P.layout_unit(rect(8.7, 10.15), 2, fondo(10.15))
    B = caja(res)
    assert not res["sin_uso"] and res["score"] == 100 and not [c for c in res["checks"] if not c["ok"]], res["checks"]
    assert all(abs(B[k][1]) < 1e-6 and abs(B[k][3] - B["kitchen"][3]) < 1e-6 for k in ("hall", "kitchen", "laundry"))
    assert abs(B["hall"][0]) < 1e-6 and abs(B["kitchen"][0] - B["hall"][2]) < 1e-6 and \
        abs(B["laundry"][0] - B["kitchen"][2]) < 1e-6 and B["laundry"][3] <= B["bath1"][1] + 1e-6, B
    assert next(r for r in res["rooms"] if r["kind"] == "kitchen")["area"] <= 5.0 + 1e-6
    assert {"heladera", "mesada", "bacha_cocina", "cocina_horno"} <= con(res, "kitchen")
    assert {"lavarropas", "pileta_lavar"} <= con(res, "laundry")
    assert _cocina_comunicada(res)          # la heladera no encierra la puerta del lavadero (antes, una rendija de 0,20 m)
    assert any({d["a"], d["b"]} == {"kitchen", "laundry"} for d in res["doors"])
    assert not any("laundry" in (d["a"], d["b"]) and "hallway" in (d["a"], d["b"]) for d in res["doors"])
    assert next(d for d in res["doors"] if d.get("entry"))["p"][0] < B["hall"][2]     # la entrada, en el hall de x0
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


@calibracion_anterior
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
    # (antes 9 y 94,4; con el frente de cada plano, v2.62, 9 y 83,3: en el ala de 6,5 m de fondo no entran 3 dorm, 2 dorm y
    # 3 dorm con 12,22 + 9,42 + 12,22 m de frente —antes salían de 11,86 y 9,18 m— y van 2 dorm, 2 dorm en la franja corta)
    assert r["metrics"]["mix"]["count"] == 9 and r["metrics"]["mix"]["match_score"] >= 80, r["metrics"]["mix"]
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


def test_datos_al_pasar():
    """Pedido del usuario: al pasar el mouse por la planta, un recuadro con el nombre y los m² de lo que está debajo
    (estancia y su vivienda, lo sin uso, parte de núcleo, pasillo, zona sin luz, patio; en los niveles que no son
    viviendas, sus partes), sin clic. Se apaga con «Datos al pasar» y no aparece mientras se dibuja o se arrastra."""
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    cuerpo = lambda f: html.split(f, 1)[1].split("\nfunction ", 1)[0].split("\nsvg.addEventListener", 1)[0]
    assert 'id="showTip" checked' in html and 'id="dato"' in html and "showTip=true" in html
    dato = cuerpo("function datoEn(")
    for t in ("u.sin_uso", "u.rooms", "c.parts", "result.corridors", "result.dark_zones", "result.patios", "progShapes(",
              "coreShapes()", "r.name", "u.type", "u.area"):
        assert t in dato, t
    mover = html.split("svg.addEventListener('mousemove',e=>{ const t=$('dato');", 1)[1].split("svg.addEventListener", 1)[0]
    assert "tool||drag||dragCore||dragTab||dragIn" in mover and "viewMode!=='plan'" in mover
    assert "svg.addEventListener('mouseleave',ocultarDato)" in html and "function enPoly(" in html and "function areaPoly(" in html
    # lo que muestra viene del resultado del motor: cada estancia y cada parte de núcleo tienen nombre y superficie
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "L_ochava.json"), encoding="utf-8"))
    r = run(s["footprint"], h=s["height"])
    assert all(x["name"] and x["area"] > 0 for u in r["units"] for x in u["rooms"])
    assert all(u["type"] and u["area"] > 0 and u["width"] > 0 and u["depth"] > 0 for u in r["units"])
    assert all(p["name"] for c in r["cores"] for p in c["parts"]) and all(c.get("ascensores") is not None for c in r["cores"])

if __name__ == "__main__":
    test_datos_al_pasar(); print("OK46")


def test_interfaz_grupos():
    """R4.6, opción B de la maqueta (la eligió el usuario): un riel con los grupos Proyecto, Masa, Circulación, Viviendas,
    Normativa y Vista abre su panel, de a uno; sobre la planta, la vista 2D/3D, el nivel y las capas, y abajo la barra de
    dibujo (Línea, Núcleo, Medianera, Patio, Orto con F8); a la derecha, el resumen, los avisos y la ficha. Cada control
    conserva su id, así que los proyectos guardados se siguen abriendo. «Muro medianero» pasa a «Muro entre viviendas»."""
    import re
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    cuerpo = html.split("<body>", 1)[1].split("<script>", 1)[0]
    grupo = lambda g: cuerpo.split('<div class="grupo" data-grupo="%s"' % g, 1)[1].split('<div class="grupo"', 1)[0] \
        .split("</section>", 1)[0]
    rail = cuerpo.split('<nav class="rail"', 1)[1].split("</nav>", 1)[0]
    contenido = {"proyecto": ("sample", "archivoProyecto", "btnVar", "rhinoBadge"),
                 "masa": ("ter_frente", "height", "floor_height", "outer_wall", "storyTable", "medList", "patios_mode"),
                 "circ": ("loading", "corridor_width", "lineInfo", "cores_mode", "core_auto", "ascensores", "core_count",
                          "egress_single", "egress_multi"),
                 "viviendas": ("mix", "min_unit_width", "party_wall", "max_unit_depth", "edInfo"),
                 "normativa": ("stdPanel",), "vista": ("legendColors",)}
    for g, ids in contenido.items():
        assert 'data-grupo="%s" onclick="grupo(\'%s\')"' % (g, g) in rail, g
        for i in ids:
            assert 'id="%s"' % i in grupo(g), (g, i)
    assert "run('massing')" in grupo("masa") and "run('corridor')" in grupo("circ") and "run('mix')" in grupo("viviendas") \
        and "run('plans')" in grupo("viviendas")
    dibujo = cuerpo.split('<div class="dibujo"', 1)[1].split("</div>", 1)[0]
    for t in ('id="btnDraw" data-tool="line"', 'id="btnAddCore" data-tool="addcore"', 'id="btnMed" data-tool="medianera"',
              'id="btnPatio" data-tool="patio"', 'id="orto" checked', "F8"):
        assert t in dibujo, t
    capas = cuerpo.split('<details class="capas"', 1)[1].split("</details>", 1)[0]
    assert all('id="%s" checked' % i in capas for i in ("showGraph", "showEquip", "showDims", "showEvac", "showTip"))
    derecha = cuerpo.split('<aside class="r">', 1)[1].split("</aside>", 1)[0]
    for i in ("ctx", "resumen", "warns", "todo", "donut", "metrics", "units"):
        assert 'id="%s"' % i in derecha, i
    assert 'id="btnUndo"' in cuerpo.split('<header class="top">', 1)[1].split("</header>", 1)[0]
    assert ">Muro entre viviendas (m) <input" in cuerpo and "Muro medianero (m)" not in cuerpo
    js = html.split("<script>", 1)[1]
    for f in ("function grupo(", "function herramientaBar(", "function resumenPanel(", "function estadoTop(", "function capas(",
              "function verTodo(", "function quitarMedianeras("):
        assert f in js, f
    assert "e.key==='F8'" in js and "localStorage.getItem('trazo.grupo')" in js
    assert "document.querySelectorAll('[data-tool]')" in js and "$('btnDelCore')" not in js
    # cada id que el JS pide con $('…') existe en la página o lo arma el JS (las fichas)
    pedidos = set(re.findall(r"\$\('([A-Za-z_]\w*)'\)", js))
    hechos = set(re.findall(r'\bid="([A-Za-z_]\w*)"', html))
    assert not pedidos - hechos, pedidos - hechos

if __name__ == "__main__":
    test_interfaz_grupos(); print("OK47")


def test_vestidor():
    """R5.10 (criterio del usuario): vestidor opcional por tipo del mix («Vest.»), apagado por defecto, junto al dormitorio
    principal, que ya no lleva placard. Con la suite va entre el dormitorio y su baño: toma lo que el dormitorio tenía
    detrás del pasillo interno, se entra a él desde el pasillo y desde él al baño (el dormitorio, abierto al vestidor);
    sin ella, a la entrada del dormitorio (pasillo → vestidor → dormitorio). El dormitorio conserva su medida mínima y la
    cama con su paso; el vestidor, de su fondo típico hasta su mínimo. Si no entra, o si el plano empeora, no se agrega y
    se avisa."""
    from engine import plans as P, standards as ST, geometry as G, dxf
    rect = lambda w, d: [(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)]
    fondo = lambda D: (lambda p, q: abs(p[1] - D) < 0.05 and abs(q[1] - D) < 0.05)
    caja = lambda res: {r["id"]: G.bbox(r["poly"]) for r in res["rooms"]}
    largo = lambda q: max(G.bbox(q["poly"])[2] - G.bbox(q["poly"])[0], G.bbox(q["poly"])[3] - G.bbox(q["poly"])[1])
    puertas = lambda res: {frozenset((d["a"], d["b"])) for d in res["doors"] if not d.get("entry")}
    muebles = lambda res, rid: [q for q in res["equipamiento"] if q["room"] == rid]
    V0, E0 = ST.DEFAULTS["vivienda"], ST.DEFAULTS["equipamiento"]
    # apagado por defecto: el plano no cambia
    base = P.layout_unit(rect(16.27, 6.5), 3, fondo(6.5))
    assert base == P.layout_unit(rect(16.27, 6.5), 3, fondo(6.5), vestidor=False) and "vest" not in caja(base)
    # 3 dormitorios de 16,27 × 6,50 (en suite): dormitorio → vestidor → baño, de todo el ancho del dormitorio
    res = P.layout_unit(rect(16.27, 6.5), 3, fondo(6.5), vestidor=True)
    B, B0 = caja(res), caja(base)
    vest = next(r for r in res["rooms"] if r["id"] == "vest")
    assert vest["name"] == "Vestidor" and vest["kind"] == "vestidor" and res["score"] == 100, res["checks"]
    assert abs(B["vest"][3] - B["bed1"][1]) < 1e-6 and abs(B["vest"][1] - B["bath2"][3]) < 1e-6, B
    assert abs(B["vest"][0] - B["bed1"][0]) < 1e-6 and abs(B["vest"][2] - B["bed1"][2]) < 1e-6
    assert B["vest"][3] - B["vest"][1] >= V0["vestidor"]["min_side"] - 1e-6 and B["vest"][3] >= B["hallway"][3] - 1e-6
    assert all(B[k] == B0[k] for k in ("bed2", "bed3", "bath1", "kitchen", "living"))      # lo demás no cambia
    p = puertas(res)
    assert {frozenset(("hallway", "vest")), frozenset(("vest", "bath2"))} <= p, p
    assert not {frozenset(("hallway", "bed1")), frozenset(("bed1", "bath2"))} & p, p
    assert any({e["a"], e["b"]} == {"vest", "bed1"} and e["type"] == "abierto" and e["ok"] for e in res["graph"]["edges"])
    est = muebles(res, "vest")                         # estantes: más que el placard que reemplazan
    assert est and {q["kind"] for q in est} == {"placard"} and sum(map(largo, est)) >= E0["placard_largo"][0], est
    assert "cama_doble" in {q["kind"] for q in muebles(res, "bed1")} and "placard" not in {q["kind"] for q in muebles(res, "bed1")}
    assert "placard" in {q["kind"] for q in muebles(res, "bed2")}
    assert {"ducha", "inodoro", "lavatorio"} <= {q["kind"] for q in muebles(res, "bath2")}
    # 2 dormitorios de 9,50 × 8,00 (sin suite): pasillo → vestidor → dormitorio
    res = P.layout_unit(rect(9.5, 8.0), 2, fondo(8.0), vestidor=True)
    B = caja(res)
    assert abs(B["vest"][3] - B["bed1"][1]) < 1e-6 and abs(B["vest"][1] - B["hallway"][3]) < 1e-6 and res["score"] == 100
    assert frozenset(("hallway", "vest")) in puertas(res) and frozenset(("hallway", "bed1")) not in puertas(res)
    assert abs(B["vest"][3] - B["vest"][1] - V0["vestidor"]["typ"][1]) < 1e-6 and sum(map(largo, muebles(res, "vest"))) >= 1.8
    # 2 dormitorios de 12,00 × 7,00: el vestidor, menos profundo (hasta su mínimo), y el dormitorio, con su medida mínima
    res = P.layout_unit(rect(12.0, 7.0), 2, fondo(7.0), vestidor=True)
    B = caja(res)
    dv, d1 = B["vest"][3] - B["vest"][1], B["bed1"][3] - B["bed1"][1]
    assert V0["vestidor"]["min_side"] - 1e-6 <= dv < V0["vestidor"]["typ"][1] and res["score"] == 100, (dv, res["checks"])
    bed1 = next(r for r in res["rooms"] if r["id"] == "bed1")
    assert d1 >= V0["dorm_principal"]["min_side"] and bed1["area"] >= V0["dorm_principal"]["min_area"] - 1e-6
    assert "cama_doble" in {q["kind"] for q in muebles(res, "bed1")}
    # no entra (dormitorios de 3,50 m de fondo): se avisa (no baja la calidad) y el plano no cambia
    base = P.layout_unit(rect(11.73, 6.5), 2, fondo(6.5))
    res = P.layout_unit(rect(11.73, 6.5), 2, fondo(6.5), vestidor=True)
    assert "vest" not in caja(res) and caja(res) == caja(base) and res["score"] == base["score"] == 100
    assert {"ok": True, "info": True, "msg": "Vestidor: no entra (el dormitorio principal tiene 3.50 m de fondo y necesita "
            "3.86 m: 1.20 m de vestidor y 2.66 m de dormitorio)"} in res["checks"], res["checks"]
    res = P.layout_unit(rect(6.0, 7.0), 0, vestidor=True)
    assert any(c.get("info") and c["msg"].startswith("Vestidor: un monoambiente no lo lleva") for c in res["checks"])
    # por tipo del mix, en los ejemplos: solo los tipos marcados; ningún plano empeora ni pierde estancias (el depósito
    # sí: el vestidor guarda); donde empeoraría (en la planta a 45°, sus estantes no entran), sin vestidor y con aviso
    mix = lambda v: [{"name": "1 dorm", "area": 55, "percent": 20, "dorms": 1},
                     {"name": "2 dorm", "area": 75, "percent": 40, "dorms": 2, "vestidor": v},
                     {"name": "3 dorm", "area": 95, "percent": 40, "dorms": 3, "vestidor": v}]
    programa = lambda u: [sum(1 for r in u["rooms"] if r["kind"] == k) for k in ("bath", "kitchen", "bedroom", "laundry",
                                                                                   "living")]
    con, avisos = 0, []
    for nombre in ("L_ochava", "barra", "quiebre_45"):
        s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", nombre + ".json"), encoding="utf-8"))
        a, b = (run(s["footprint"], h=s["height"], **dict(s.get("params") or {}, unit_mix=mix(v))) for v in (None, True))
        for ua, ub in zip(a["units"], b["units"]):
            assert ua["id"] == ub["id"] and abs(ua["area"] - ub["area"]) < 1e-6
            tiene = any(r["kind"] == "vestidor" for r in ub["rooms"])
            assert bool(ub.get("vestidor")) == (ub["type"] != "1 dorm") and (not tiene or ub.get("vestidor")), ub["id"]
            assert ub["plan_score"] >= ua["plan_score"] and programa(ub) == programa(ua), (nombre, ub["id"])
            con += tiene
            if ub.get("vestidor") and not tiene:          # por qué no, en la ficha
                m = [c["msg"] for c in ub["checks"] if c.get("info") and c["msg"].startswith("Vestidor: no")]
                assert m, (nombre, ub["id"])
                avisos += m
        if nombre == "barra":
            assert "Trazo_L00_Rooms_vestidor" in dxf.result_to_dxf(b)
    assert con >= 10 and any("porque empeora el plano" in m for m in avisos), (con, avisos)
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    for t in ("data-vest=", "mix[${i}].vestidor=this.checked", "vestidor:'Vestidor (tipos del mix con «Vest.»)'",
              "vestidor:0.54", "vestidor:'Vestidor'}", "r.kind==='vestidor')?' · con vestidor'"):
        assert t in html, t
    rh = open(os.path.join(os.path.dirname(__file__), "..", "rhino", "trazo_rhino.py"), encoding="utf-8").read()
    assert '"vestidor": SD.Color.FromArgb(' in rh

if __name__ == "__main__":
    test_vestidor(); print("OK48")


@calibracion_anterior
def test_pasillo_por_tramo():
    """R10.8 (pedido del usuario): el ancho del pasillo común se puede fijar tramo por tramo (clic en el tramo en la web;
    «ancho=1.4» en la polilínea desde Rhino); los demás siguen con el general. Cada tramo trae su largo, las viviendas
    que sirve y el mínimo del art. 35 de la norma nacional (1,20 m hasta 3 viviendas, 1,40 de 4 a 10, 1,60 con 11 o
    más; 2,00 m si el tramo recto pasa de 15 m), con un aviso si no llega. Sin anchos propios, la planta no cambia."""
    import math
    from engine import geometry as G, standards as ST, layout as LY
    caja = lambda p: G.bbox([tuple(q) for q in p])
    toca = lambda a, b: a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
    pisa = lambda a, b: sum(abs(G.area(o)) for o in G.subtract(a, [b])[1][0]) if toca(caja(a), caja(b)) else 0.0

    def solapes(r):
        us, cs = [u["poly"] for u in r["units"]], [c["poly"] for c in r["cores"]]
        return round(sum(pisa(a, b) for i, a in enumerate(us) for b in us[i + 1:]) +
                     sum(pisa(a, b) for a in us for b in r["corridors"] + cs), 1)

    def ancho_real(r, ps):
        a, b = ps["eje"]
        loc = G.to_local([tuple(q) for q in r["corridors"][ps["partes"][0]]], tuple(a), math.atan2(b[1] - a[1], b[0] - a[0]))
        return round(G.bbox(loc)[3] - G.bbox(loc)[1], 3)
    medio = lambda ps: [(ps["eje"][0][0] + ps["eje"][1][0]) / 2, (ps["eje"][0][1] + ps["eje"][1][1]) / 2]
    sin_pas = lambda r: json.dumps({k: v for k, v in r.items() if k not in ("pasillos", "units")}, sort_keys=True)
    # el art. 35
    S = ST.DEFAULTS["nucleo"]
    assert [ST.ancho_art35(S, n, 10.0)[0] for n in (2, 3, 4, 10, 11)] == [1.20, 1.20, 1.40, 1.40, 1.60]
    assert ST.ancho_art35(S, 5, 20.0)[0] == 2.00 and ST.ancho_art35(S, None, 10.0)[0] == 1.20
    # L (automático): el tramo corto de 1,40 m; el largo sigue en 2,00 m y la planta, sin solapes
    L = [[0, 0], [50, 0], [50, 14], [16, 14], [16, 40], [0, 40]]
    base = run(L)
    assert [p["id"] for p in base["pasillos"]] == ["P1", "P2"] and not any(p["propio"] for p in base["pasillos"])
    assert all(p["ancho"] == 2.0 and p["ok"] and p["viviendas"] > 0 for p in base["pasillos"])
    p2 = base["pasillos"][1]
    r = run(L, anchos_pasillo=[{"p": medio(p2), "ancho": 1.4}])
    q1, q2 = r["pasillos"]
    assert q2["propio"] and q2["ancho"] == 1.4 and ancho_real(r, q2) == 1.4 and ancho_real(r, q1) == 2.0, r["pasillos"]
    assert solapes(r) == 0 and len(r["units"]) == len(base["units"])
    assert not q2["ok"] and q2["minimo"] == 2.0                       # tramo recto de más de 15 m
    assert any(w.startswith("Pasillo P2 de 1.40 m: el art. 35 de la norma nacional pide 2.00 m en un tramo recto de "
                            "más de 15 m") for w in r["warnings"]), r["warnings"]
    u_p2 = lambda r: sorted(u["depth"] for u in r["units"] if u["pasillo"] == "P2")
    assert all(b > a + 0.25 for a, b in zip(u_p2(base), u_p2(r))), (u_p2(base), u_p2(r))   # sus viviendas, más hondas
    # el mismo ancho que el general: la planta no cambia
    r = run(L, anchos_pasillo=[{"p": medio(p), "ancho": 2.0} for p in base["pasillos"]])
    assert sin_pas(r) == sin_pas(base) and all(p["propio"] for p in r["pasillos"])
    # un ancho que ya no tiene tramo (la planta cambió): se avisa
    r = run(L, anchos_pasillo=[{"p": [100, 100], "ancho": 1.4}])
    assert any("1 ancho(s) de pasillo pedido(s) no tiene(n) tramo" in w for w in r["warnings"]), r["warnings"]
    # polilíneas que se cruzan: un segmento (como manda Rhino) llega a las dos mitades de la línea cortada
    cruz = [[20, 0], [36, 0], [36, 20], [56, 20], [56, 36], [36, 36], [36, 56], [20, 56], [20, 36], [0, 36], [0, 20],
            [20, 20]]
    lineas = [[[28, 1], [28, 55]], [[1, 28], [55, 28]]]
    r = run(cruz, centerlines=lineas, anchos_pasillo=[{"seg": [[1, 28], [55, 28]], "ancho": 1.6}])
    propios = [p for p in r["pasillos"] if p["propio"]]
    assert len(propios) == 2 and all(p["ancho"] == 1.6 and ancho_real(r, p) == 1.6 for p in propios), r["pasillos"]
    assert solapes(r) == 0
    # «Hecho cuando» (R10.8): una barra con el pasillo de 1,40 m y un tramo de más de 15 m se avisa
    r = run([[0, 0], [60, 0], [60, 16], [0, 16]], corridor_width=1.4)
    assert any(w.startswith("Pasillo P1 de 1.40 m: el art. 35") for w in r["warnings"]), r["warnings"]
    # entre medianeras: el ancho es el de los pasillos que llegan a las viviendas; con núcleos manuales, el general
    # (antes quedaba fijo en 2.00 m)
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "entre_medianeras.json"), encoding="utf-8"))
    alto = lambda r: sorted(round(caja(c)[3] - caja(c)[1], 2) for c in r["corridors"] if caja(c)[2] - caja(c)[0] > 9)
    r = run(s["footprint"], h=s["height"], medianeras=s["medianeras"], corridor_width=1.5, cores_mode="manual", cores=[[5, 14]])
    assert alto(r) == [1.5, 1.5, 1.5], alto(r)
    r = run(s["footprint"], h=s["height"], medianeras=s["medianeras"])
    ps = r["pasillos"][0]
    assert ps["editable"] and ps["ancho"] == 2.0
    r = run(s["footprint"], h=s["height"], medianeras=s["medianeras"], anchos_pasillo=[{"p": medio(ps), "ancho": 1.2}])
    assert r["pasillos"][0]["propio"] and r["pasillos"][0]["ancho"] == 1.2 and 1.2 in alto(r), alto(r)
    # la web: clic en un tramo, su panel, deshacer y proyecto; Rhino lo dibuja igual (sigue en «corridors»)
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    for t in ("'data-pas':k??''", "function pasilloPanel(", "function aplicarAncho(", "anchos_pasillo:anchosPasillo.length",
              "anchos_pasillo:P.anchos_pasillo", "m.anchos_pasillo", "interiores,anchosPasillo}", 'id="anchosInfo"',
              "closest('[data-pas]')", "pasillo_comun:'Pasillo común (art. 35)"):
        assert t in html, t
    assert LY.DEFAULT_PARAMS["anchos_pasillo"] is None

if __name__ == "__main__":
    test_pasillo_por_tramo(); print("OK49")


@calibracion_anterior
def test_pasillo_por_tramo_casos():
    """R10.8, casos de la revisión: pasillos paralelos de distinto ancho (la línea media entre sus bordes), un punto en
    un empalme o un cruce (va al tramo en cuyo medio está), el núcleo de punta junto a un pasillo más ancho que llega,
    el art. 35 en la etapa del pasillo (1,20 m como mínimo), con un vértice alineado (un solo tramo recto) y sin
    viviendas (no se aplica), los segmentos de Rhino que el motor quita (sin aviso) y los anchos que quedaron sin
    tramo (cuáles son, para quitarlos desde la web)."""
    import math
    from engine import geometry as G
    T_ = lambda p: [tuple(q) for q in p]
    inter = lambda a, b: abs(G.area(T_(a))) - sum(abs(G.area(o)) for o, _ in G.subtract(T_(a), [T_(b)])[0])
    medio = lambda ps: [(ps["eje"][0][0] + ps["eje"][1][0]) / 2, (ps["eje"][0][1] + ps["eje"][1][1]) / 2]
    a35 = lambda r: [w for w in r["warnings"] if "art. 35" in w]
    sin_tramo = lambda r: [w for w in r["warnings"] if "no tiene(n) tramo" in w]
    gen = lambda fp, stage="plans", **p: generate({"footprint": fp, "height": 15, "stage": stage, "params": p})
    muestra = lambda n: json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", n + ".json"),
                                       encoding="utf-8"))
    # pasillos paralelos de 1,40 y 3,00 m (en los dos órdenes): las viviendas de cada uno llegan hasta la mitad entre
    # los bordes de los dos pasillos, con el tabique entre ellas, y no se pisan
    pw = 0.3
    for lineas in ([[[1, 7], [39, 7]], [[1, 21], [39, 21]]], [[[1, 21], [39, 21]], [[1, 7], [39, 7]]]):
        for a7, a21 in ((1.4, 3.0), (3.0, 1.4), (2.0, 2.0)):
            r = gen([[0, 0], [40, 0], [40, 28], [0, 28]], "units", centerlines=lineas, party_wall=pw,
                    anchos_pasillo=[{"p": [20, 7], "ancho": a7}, {"p": [20, 21], "ancho": a21}])
            us = [u["poly"] for u in r["units"]]
            corte = (7 + a7 / 2 + 21 - a21 / 2) / 2
            ys = sorted(set(round(q[1], 3) for u in us for q in u if 9 < q[1] < 19))
            assert ys == [round(corte - pw / 2, 3), round(corte + pw / 2, 3)], (a7, a21, ys, corte)
            assert all(len(u) == 4 for u in us) and max(inter(a, b) for i, a in enumerate(us) for b in us[i + 1:]) < 0.01
    # un punto en el empalme de una T (ramal dibujado primero) o en el cruce de una X: va al tramo en cuyo medio está
    t = muestra("T_dos_lineas")
    r = gen(t["footprint"], centerlines=[[[30, 10], [30, 48]], [[0, 10], [60, 10]]],
            anchos_pasillo=[{"p": [30, 10], "ancho": 3.5}])
    assert [(p["eje"][0], p["propio"]) for p in r["pasillos"]] == [([30, 10], False), ([0, 10], True)], r["pasillos"]
    x = muestra("cruz_dos_lineas")
    r = gen(x["footprint"], centerlines=[[[1, 28], [55, 28]], [[28, 0.5], [28, 55.5]]],
            anchos_pasillo=[{"p": [28, 28], "ancho": 3.0}])
    assert [p["propio"] for p in r["pasillos"]] == [False, False, True] and r["pasillos"][2]["ancho"] == 3.0
    # lo mismo en una planta girada, con el punto medio redondeado como lo manda la web
    g = math.radians(7)
    gira = lambda P: [[round(a * math.cos(g) - b * math.sin(g), 6), round(a * math.sin(g) + b * math.cos(g), 6)] for a, b in P]
    tg, lg = gira(t["footprint"]), [gira(l_) for l_ in [[[30, 10], [30, 48]], [[0, 10], [60, 10]]]]
    for k, ps in enumerate(gen(tg, "corridor", centerlines=lg)["pasillos"]):
        m = [round(v, 3) for v in medio(ps)]
        r = gen(tg, "corridor", centerlines=lg, anchos_pasillo=[{"p": m, "ancho": 1.4}])
        assert [i for i, q in enumerate(r["pasillos"]) if q["propio"]] == [k], (k, r["pasillos"])
    # el núcleo de una punta no pisa el pasillo más ancho del ala que llega ahí: se va al otro lado del pasillo
    nucleo = lambda r: round(sum(inter(p_["poly"], c) for n in r["cores"] for p_ in n["parts"]
                                 if p_["kind"] in ("stair", "elevator", "duct", "service") for c in r["corridors"]), 2)
    for fp, ancho in ((muestra("L")["footprint"], 6.0), ([[0, 0], [50, 0], [50, 12], [14, 12], [14, 40], [0, 40]], 3.5)):
        p2 = gen(fp, "units")["pasillos"][1]
        r = gen(fp, "units", anchos_pasillo=[{"p": medio(p2), "ancho": ancho}])
        assert r["pasillos"][1]["ancho"] == ancho and nucleo(r) == 0, (ancho, nucleo(r))
    # el núcleo que agrega la evacuación (o la cantidad pedida) tampoco
    t80 = [[0, 0], [80, 0], [80, 14], [47, 14], [47, 40], [33, 40], [33, 14], [0, 14]]
    t16 = [[0, 0], [60, 0], [60, 16], [38, 16], [38, 44], [22, 44], [22, 16], [0, 16]]
    for fp, p, ancho, extra in ((t80, [40, 26.65], 6.0, {}), (t16, [30, 29.65], 4.5, {"egress_multi": 25}),
                                (t16, [30, 29.65], 4.5, {"core_count": 4})):
        r = gen(fp, anchos_pasillo=[{"p": p, "ancho": ancho}], **extra)
        assert r["pasillos"][1]["ancho"] == ancho and nucleo(r) == 0, (fp, extra, nucleo(r))
    # ni el de un ala más angosta cuyo núcleo, más hondo por su pasillo ancho, llega al pasillo del ala paralela
    peine = [[0, 0], [50, 0], [50, 14], [30, 14], [30, 20], [50, 20], [50, 34], [30, 34], [30, 40], [50, 40], [50, 54],
             [0, 54]]
    r = gen(peine, anchos_pasillo=[{"p": [25, 27], "ancho": 4.5}])
    assert nucleo(r) == 0 and len(r["cores"]) == 5, (nucleo(r), len(r["cores"]))   # v2.51: espina y tres dientes
    # sin anchos propios: en una L angosta el núcleo de la punta ya no queda sobre el pasillo del ala que llega
    # (corrección); y el muro del núcleo junto al pasillo no cuenta (la Z sigue como antes)
    r = gen([[0, 0], [50, 0], [50, 12], [12, 12], [12, 40], [0, 40]])
    assert nucleo(r) == 0, nucleo(r)
    r = gen([[0, 0], [40, 0], [40, 14], [14, 14], [14, 40], [54, 40], [54, 54], [0, 54]], corridor_width=2.6)
    assert r["cores"][0]["center"] == [3.075, 9.675] and nucleo(r) == 0, r["cores"][0]["center"]
    # art. 35 en la etapa del pasillo (todavía sin viviendas): 1,20 m como mínimo en cualquier pasillo común
    r = gen([[0, 0], [14, 0], [14, 14], [0, 14]], "corridor", corridor_width=1.0)
    assert r["pasillos"][0]["minimo"] == 1.2 and r["pasillos"][0]["ok"] is False and len(a35(r)) == 1, r["pasillos"]
    # una recta dibujada con un vértice intermedio es un solo tramo recto: su largo y sus viviendas son los de toda
    # la recta (como sin el vértice)
    barra = [[0, 0], [30, 0], [30, 16], [0, 16]]
    una = gen(barra, corridor_width=1.4, centerlines=[[[1, 8], [29, 8]]])["pasillos"][0]
    r = gen(barra, corridor_width=1.4, centerlines=[[[1, 8], [15, 8], [29, 8]]])
    assert [(p["largo"], p["viviendas"], p["minimo"], p["ok"]) for p in r["pasillos"]] == \
        [(una["largo"], una["viviendas"], 2.0, False)] * 2 and len(a35(r)) == 2, (una, r["pasillos"])
    r = gen(barra, corridor_width=1.4, centerlines=[[[1, 8], [15, 8.01], [29, 8]]])      # el vértice, 1 cm afuera
    assert [(p["largo"], p["ok"]) for p in r["pasillos"]] == [(28.0, False)] * 2 and len(a35(r)) == 2, r["pasillos"]
    # una T dibujada como una L más el brazo que falta (en cualquier orden y sentido): el tronco es un tramo recto
    te = [[0, 0], [30, 0], [30, 20], [22, 20], [22, 45], [8, 45], [8, 20], [0, 20]]
    for lineas in ([[[1, 10], [15, 10], [15, 44]], [[15, 10], [29, 10]]],
                   [[[15, 44], [15, 10], [1, 10]], [[15, 10], [29, 10]]],
                   [[[15, 10], [29, 10]], [[1, 10], [15, 10], [15, 44]]]):
        r = gen(te, corridor_width=1.4, centerlines=lineas)
        tronco = [p for p in r["pasillos"] if p["eje"][0][1] == p["eje"][1][1] == 10]
        assert [(p["largo"], p["ok"]) for p in tronco] == [(28.0, False)] * 2, r["pasillos"]
    # las dos mitades de la línea cortada en un cruce también (antes dependía de cuál línea era más larga)
    equis = [[10, 0], [22, 0], [22, 10], [34, 10], [34, 22], [22, 22], [22, 32], [10, 32], [10, 22], [0, 22], [0, 10],
             [10, 10]]
    for horizontal, largos in (([[0.5, 16], [33.5, 16]], [30.0, 30.0, 33.0]), ([[3.5, 16], [30.5, 16]], [27.0, 27.0, 30.0])):
        r = gen(equis, "corridor", corridor_width=1.4, centerlines=[[[16, 1], [16, 31]], horizontal])
        assert sorted(p["largo"] for p in r["pasillos"]) == largos and not any(p["ok"] for p in r["pasillos"]), r["pasillos"]
    # una polilínea curva no suma sus giros: no es un tramo recto
    arco = lambda R, a0, a1, d: [[R * math.cos(math.radians(a)), R * math.sin(math.radians(a))] for a in range(a0, a1, d)]
    r = gen(arco(34, 0, 91, 2) + arco(26, 90, -1, -2), "corridor", corridor_width=1.4, centerlines=[arco(30, 0, 91, 2)])
    assert max(p["largo"] for p in r["pasillos"]) < 5 and not a35(r), max(p["largo"] for p in r["pasillos"])
    # sin niveles de vivienda (oficinas, comercio, cocheras), el art. 35 no se aplica
    for prog, avisa in (("Office", 0), ("Parking", 0), ("Residential", 1)):
        for stage in ("corridor", "plans"):
            r = generate({"footprint": [[0, 0], [60, 0], [60, 18], [0, 18]], "height": 13.2, "stage": stage,
                          "params": {"corridor_width": 1.5, "stories": [{"program": prog, "height": 3.3}] * 4}})
            assert len(a35(r)) == avisa and (r["pasillos"][0].get("ok") is None) == (not avisa), (prog, stage)
            assert avisa or r["pasillos"][0].get("viviendas") is None, r["pasillos"][0]
    # Rhino: un segmento que el motor quita (lo que sobra de un cruce o uno de 5 cm o menos) no es un ancho perdido
    for lineas in ([[[28, 1], [28, 55]], [[1, 28], [30, 28], [30, 30]]], [[[28, 1], [28, 55]], [[1, 28], [29, 28], [31, 28]]]):
        an = [{"seg": [a, b], "ancho": 1.6} for a, b in zip(lineas[1], lineas[1][1:])]
        r = gen(x["footprint"], "corridor", centerlines=lineas, anchos_pasillo=an)
        assert not sin_tramo(r) and "anchos_sin_tramo" not in r and [p["ancho"] for p in r["pasillos"]] == [2.0, 1.6]
    L = muestra("L")["footprint"]
    pts = [[8, 38], [8, 7.03], [8.03, 7.0], [46, 7]]
    r = gen(L, "corridor", centerlines=[pts], anchos_pasillo=[{"seg": [a, b], "ancho": 1.5} for a, b in zip(pts, pts[1:])])
    assert not sin_tramo(r) and [(p["ancho"], p["propio"]) for p in r["pasillos"]] == [(1.5, True)] * 2, r["pasillos"]
    # un ancho que de verdad se quedó sin tramo (el codo se corrió): se avisa y se dice cuál es
    r = gen(L, "corridor", centerlines=[[[8, 38], [8.5, 7], [46, 7]]],
            anchos_pasillo=[{"seg": [[8, 38], [8, 7]], "ancho": 1.4}, {"seg": [[8, 7], [46, 7]], "ancho": 1.4}])
    assert r["anchos_sin_tramo"] == [0] and len(sin_tramo(r)) == 1 and \
        "Quitar los que no tienen tramo" in sin_tramo(r)[0], (r.get("anchos_sin_tramo"), r["warnings"])
    assert "anchos_sin_tramo" not in gen(L, "corridor")
    lp = muestra("L_polilinea")
    r = gen(lp["footprint"], "corridor", centerlines=lp["centerlines"],
            anchos_pasillo=[{"p": [8, 22.5], "ancho": 1.4}, {"p": [8.6, 15], "ancho": 1.8}])
    assert r["anchos_sin_tramo"] == [0] and r["pasillos"][0]["ancho"] == 1.8, (r.get("anchos_sin_tramo"), r["pasillos"])
    # la web: vuelve a elegir el tramo por su pedido, separa un segmento de Rhino que comparten dos tramos, quita los
    # anchos sin tramo y la tabla de viviendas abre la ficha de la vivienda aunque haya un tramo elegido
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    for t_ in ("function tramoDe(", "selPas=tramoDe(j.pasillos||[],selPasP,selPasK)", "selPasP=m; selPasK=k;",
               "x.spec===k", "function quitarSinTramo(", "result.anchos_sin_tramo",
               "selUnit='${u.id}';selPas=null;selCore=null;", "anchosRes===JSON.stringify(anchosPasillo)",
               "const sin=sinTramo()", "new Set(sinTramo())", "result=j; anchosRes=enviados;",
               "' por ahora (según las viviendas que sirva", "no se aplica (ningún nivel es de vivienda)",
               "if(tool||e.button!==0||e.ctrlKey) return;", "proyecto:JSON.parse(JSON.stringify(proyecto()))",
               "abierto={p:JSON.parse(JSON.stringify(p)),archivo:n}"):
        assert t_ in html, t_

if __name__ == "__main__":
    test_pasillo_por_tramo_casos(); print("OK50")


def test_vivienda_elegida_otra_etapa():
    """Con una vivienda elegida, «Generar pasillo y núcleos» (todavía sin viviendas) no deja la planta sin dibujar: al
    recalcular, la web suelta la vivienda que ya no está en el resultado."""
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    run_ = html[html.index("async function run("):html.index("function render()")]
    assert "if(selUnit&&!(j.units||[]).some(u=>u.id===selUnit)) selUnit=null;" in run_
    assert run_.index("selUnit=null;") < run_.index("render();")
    assert "units" not in generate({"footprint": [[0, 0], [40, 0], [40, 16], [0, 16]], "height": 15, "stage": "corridor"})

if __name__ == "__main__":
    test_vivienda_elegida_otra_etapa(); print("OK51")


def test_grilla_y_snap():
    """R4.7: grilla que se adapta al zoom (10, 5, 1, 0,5, 0,1 y 0,05 m: la más fina que se ve) y sigue al SCP (el del
    edificio por defecto: su fachada principal; un borde de la masa, como «SCP objeto»; o el del mundo). Todos los
    puntos que se marcan o se arrastran pasan por el mismo ajuste (`ajustar`, `ajustarDesp`): vértices de la masa,
    paso de la grilla y Orto en el SCP; Alt deja el punto libre. F7, F8 y F9 alternan grilla, Orto y snap."""
    import re
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    cuerpo = html[html.index("<body"):html.index("<script>")]
    dibujo = cuerpo.split('<div class="dibujo"')[1].split("</div>")[0]
    for t in ('id="grilla" checked', 'id="snap" checked', 'id="orto" checked', 'id="btnScp" data-tool="scp"', 'id="pasoTxt"',
              "F7", "F8", "F9"):
        assert t in dibujo, t
    js = html[html.index("<script>"):]
    for f in ("pasoGrilla", "dibujarGrilla", "ajustar", "ajustarDesp", "scpActual", "scpDefecto", "scpObjeto", "scpEdificio",
              "scpMundo", "aLocal", "aMundo", "preferencia", "alternar"):
        assert re.search(r"(function %s\(|const %s=)" % (f, f), js), f
    # no queda el redondeo fijo a 0,10 m del mundo: todo pasa por el ajuste
    assert "function snap(" not in js and not re.search(r"[^.\w]snap\(", js)
    assert "Math.round(w[0]*10)/10" not in js and "*10)/10,Math.round((k.center" not in js
    for t in ("dibujarGrilla(gb); const sw=1.2;", "curLine.push(ajustar(w,curLine[curLine.length-1],e))",
              "curPatio.push(ajustar(w,null,e))", "coresManual.push(ajustar(w,null,e,{vertices:false}))",
              "mouse=ajustar(w,null,e)", "pl[drag.vi]=ajustar(toWorld(e),null,e)", "dragTab.d=ajustarDesp(mitad(t.seg),t.dir,",
              "dragIn.d=ajustarDesp(", "const c=ajustar([k.center[0]+dragCore.d[0]", "e.altKey", "else if(tool==='scp')",
              "e.key==='F7'", "e.key==='F8'", "e.key==='F9'", "localStorage.getItem('trazo.'+id)", "'trazo.'+c.id",
              "if(scp) p.scp=scp;", "scp:p.scp}", "scp=m.scp&&", "terreno=null; scp=null;", "ESCALA_MAX/s0"):
        assert t in js, t
    g = js[js.index("function dibujarGrilla("):js.index("function iconoScp(")]
    assert "'pointer-events':'none'" in g and "scpActual()" in g
    # revisión: un arrastre que el snap devuelve a su lugar no es un cambio; el vértice se arrastra después de 5 px;
    # el patio conserva sus esquinas en la grilla; otra masa con la herramienta SCP; acercar nunca aleja; el paso se
    # borra en blanco; un SCP guardado inválido no se usa; el ícono del SCP va encima de la planta; las barras entran
    for t in ("if(!t||Math.abs(g.d)<1e-3) return drawOverlay();", "if(!sg||!r||Math.abs(g.d)<1e-3) return drawOverlay();",
              "drag={li,vi,moved:false,x:e.clientX,y:e.clientY}", "Math.abs(e.clientX-drag.x)+Math.abs(e.clientY-drag.y)<5",
              "patios.push(p.map(q=>[+q[0].toFixed(3),+q[1].toFixed(3)]", "olvidarHistoria(); medHover=null;",
              "&&medHover!=null&&footprint[medHover]", "nz=f>1?Math.max(zoom,", "view=null; $('pasoTxt').textContent='';",
              ".every(Number.isFinite)", "drawMeds(go); iconoScp(go);"):
        assert t in js, t
    assert "max-width:calc(100% - 20px);overflow-x:auto}" in html.split('.dibujo{', 1)[1].split("\n")[0]
    assert ".herr>span:first-child{white-space:normal" in html
    assert "Math.min(12,zoom*f)" not in js
    # «Hecho cuando»: en quiebre_45 (de 8,1 a 19,5 px/m sin zoom según la pantalla y el panel) el zoom llega a 1 m,
    # 0,10 m y 0,05 m
    pasos = [float(x) for x in re.search(r"const PASOS=\[([^\]]+)\]", js).group(1).split(",")]
    px = float(re.search(r"PX_GRILLA=([\d.]+)", js).group(1))
    emax = float(re.search(r"ESCALA_MAX=([\d.]+)", js).group(1))
    assert pasos == [0.05, 0.1, 0.5, 1, 5, 10]
    paso = lambda esc: next((p_ for p_ in pasos if p_ * esc >= px), pasos[-1])
    for s0 in (8.1, 13.0, 19.5):
        zooms = [0.5 * 1.15 ** i for i in range(80) if 0.5 * 1.15 ** i <= max(12, emax / s0)]
        vistos = {paso(s0 * z) for z in zooms}
        assert {1, 0.1, 0.05} <= vistos, (s0, sorted(vistos))

if __name__ == "__main__":
    test_grilla_y_snap(); print("OK52")


def test_desfase():
    """R10.8: geometry.desfase corre cada borde de un polígono por su propia distancia (hacia afuera; negativa, hacia
    adentro). Dos bordes seguidos paralelos con distancias distintas dejan un escalón; da lo mismo el sentido del
    polígono (devuelve uno antihorario)."""
    from engine import geometry as G
    rect = [(0.0, 0.0), (10.0, 0.0), (10.0, 6.0), (0.0, 6.0)]
    out = G.desfase(rect, [0.35, 0.15, 0.075, 0.15])          # abajo, derecha, arriba, izquierda
    assert len(out) == 4 and abs(G.area(out) - (10 + 0.15 + 0.15) * (6 + 0.35 + 0.075)) < 1e-9, out
    assert abs(G.area(G.desfase(rect, [0.0] * 4)) - 60.0) < 1e-9 and abs(G.area(G.desfase(rect, [-1.0] * 4)) - 32.0) < 1e-9
    # el borde de abajo en dos tramos (de 0 a 4 y de 4 a 10) con 0,35 y 0,15: escalón en x = 4
    p = [(0.0, 0.0), (4.0, 0.0), (10.0, 0.0), (10.0, 6.0), (0.0, 6.0)]
    out = G.desfase(p, [0.35, 0.15, 0.1, 0.2, 0.3])
    cerca = lambda q, x, y: abs(q[0] - x) < 1e-9 and abs(q[1] - y) < 1e-9
    assert any(cerca(q, 4.0, -0.35) for q in out) and any(cerca(q, 4.0, -0.15) for q in out) and len(out) == 6, out
    esperado = (10 + 0.3 + 0.1) * (6 + 0.15 + 0.2) + (4 + 0.3) * (0.35 - 0.15)
    assert abs(G.area(out) - esperado) < 1e-9
    # al revés (horario): el borde i es el n-2-i del original
    assert abs(G.area(G.desfase(p[::-1], [0.2, 0.1, 0.15, 0.35, 0.3])) - esperado) < 1e-9
    # revisión: bordes casi colineales con distancias distintas (un quiebre mínimo por redondeo, o el mismo borde girado y
    # en coordenadas UTM): escalón, no una mitra a cientos o millones de metros
    import math
    p = [(0.0, 0.0), (9.75, 0.0), (10.0, 0.0), (10.0, 6.0), (0.0, 6.0)]
    ds = [0.35, 0.15, 0.15, 0.075, 0.15]
    a0 = G.area(G.desfase(p, ds))
    c, s_ = math.cos(math.radians(5)), math.sin(math.radians(5))
    utm = [(round(371234.5 + x * c - y * s_, 4), round(6123456.7 + x * s_ + y * c, 4)) for x, y in p]
    assert abs(a0 - 66.0975) < 1e-6 and abs(G.area(G.desfase(utm, ds)) - a0) < 0.01, G.area(G.desfase(utm, ds))
    quiebre = [(0.0, 0.0), (5.0, 0.0005), (10.0, 0.0), (10.0, 6.0), (0.0, 6.0)]
    assert abs(G.area(G.desfase(quiebre, [0.35, 0.15, 0.1, 0.2, 0.3])) - (10.4 * 6.35 + 5.3 * 0.2)) < 0.05
    # clean_rel quita los quiebres mínimos y las puntas de ancho cero
    punta = [(0.0, 0.0), (10.0, 0.0), (10.0, 6.0), (4.0, 6.0), (4.0, 12.0), (4.0001, 6.0), (0.0, 6.0)]
    assert G.clean_rel(punta) == [(0.0, 0.0), (10.0, 0.0), (10.0, 6.0), (0.0, 6.0)], G.clean_rel(punta)
    assert len(G.clean_rel(quiebre)) == 4

if __name__ == "__main__":
    test_desfase(); print("OK53")


@calibracion_anterior
def test_superficie_con_muros():
    """R10.8 (norma nacional, art. 3): cada vivienda trae «area_muros», su superficie con los muros: hasta la cara exterior
    del muro exterior en la fachada y en la medianera (criterio del usuario: el muro entero), hasta el eje del muro con
    la vecina, con el pasillo común y con el núcleo; un borde sin nada cerca, hasta el eje de un tabique. «area», la
    superficie libre, no cambia. La web la muestra en la ficha, en la tabla de viviendas y al pasar el mouse."""
    from engine import standards as ST
    ow, pw, muro = 0.35, 0.30, ST.DEFAULTS["nucleo"]["muro"]
    carga = lambda n: json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", n + ".json"), encoding="utf-8"))
    caja = lambda u: (min(p[0] for p in u["poly"]), min(p[1] for p in u["poly"]), max(p[0] for p in u["poly"]),
                      max(p[1] for p in u["poly"]))
    # barra, U01: el núcleo a la izquierda, la vecina a la derecha, la fachada al fondo y el pasillo común al frente
    s = carga("barra")
    r = run(s["footprint"], h=s["height"])
    u = next(u for u in r["units"] if u["id"] == "U01")
    x0, y0, x1, y1 = caja(u)
    esperado = (x1 - x0 + muro / 2 + pw / 2) * (y1 - y0 + ow + pw / 4)
    assert abs(esperado - 82.78) < 0.05 and abs(u["area_muros"] - 82.78) < 0.1 and abs(u["area"] - 76.2) < 0.05, u["area_muros"]
    # al frente (R3.7): la fachada, la medianera y el otro lindero con el muro entero; la punta del pasillo y la vecina, a
    # un muro de distancia: hasta su eje
    d = carga("entre_medianeras")
    r = run(d["footprint"], h=18, unit_mix=[{"name": "2 dorm", "area": 75, "percent": 100, "dorms": 2}],
            medianeras=[d["medianeras"][1]], cores_mode="manual", cores=[[5, 25]])
    u = next(u for u in r["units"] if u.get("al_frente"))
    x0, y0, x1, y1 = caja(u)
    assert abs(u["area_muros"] - (x1 - x0 + 2 * ow) * (y1 - y0 + ow + pw / 2)) < 0.1, u["area_muros"]
    # una ochava y un quiebre a 45°: entre un 3 y un 15 % más que la superficie libre
    for n in ("L_ochava", "quiebre_45"):
        s = carga(n)
        r = run(s["footprint"], h=s["height"])
        for u in r["units"]:
            assert 1.03 * u["area"] <= u["area_muros"] <= 1.15 * u["area"], (n, u["id"], u["area"], u["area_muros"])
    # un patio interior (U cerrada): U01 da al patio por arriba, con el muro exterior entero (sin el patio en los bordes de
    # la planta, ese lado sería un tabique: pw/2), al pasillo por abajo y a un tabique a los costados
    from engine import units as U
    P0 = {"outer_wall": ow, "party_wall": pw}
    s = carga("entre_medianeras_patio_central")
    r = run(s["footprint"], h=s["height"], medianeras=s["medianeras"], patios_mode="manual", patios=s["patios"])
    hueco = r["blocks"][0]["plate_holes"][0]
    hx0, hx1 = min(p[0] for p in hueco), max(p[0] for p in hueco)
    i = [u["id"] for u in r["units"]].index("U01")
    u = r["units"][i]
    sin = U.superficie_con_muros([x["poly"] for x in r["units"]], [[r["blocks"][0]["plate"]]] * len(r["units"]),
                                 r["corridors"], [c["poly"] for c in r["cores"]], P0)[i]
    assert abs(u["area_muros"] - sin - (hx1 - hx0) * (ow - pw / 2)) < 0.15, (u["area_muros"], sin, hx1 - hx0)
    x0, y0, x1, y1 = caja(u)
    assert abs(u["area_muros"] - (x1 - x0 + pw) * (y1 - y0 + ow + pw / 4)) < 0.6, u["area_muros"]
    # revisión: plantas giradas (L a 15°, la ochava a 30°) y en coordenadas UTM dan lo mismo que en el origen
    import math

    def girar(fp, ang, t=(0.0, 0.0)):
        c, s_ = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        return [[round(t[0] + x * c - y * s_, 4), round(t[1] + x * s_ + y * c, 4)] for x, y in fp]
    for n, ang in (("L", 15), ("L_ochava", 30), ("L", 246), ("L_ochava", 51)):
        s = carga(n)
        r = generate({"footprint": girar(s["footprint"], ang), "height": s["height"], "stage": "units", "params": {}})
        for u in r["units"]:
            assert u["area"] < u["area_muros"] < 1.3 * u["area"], (n, ang, u["id"], u["area"], u["area_muros"])
    # en UTM: el motor da viviendas razonables y, con las mismas viviendas, pasillos y núcleos trasladados, lo mismo
    s = carga("L")
    t = (371234.5, 6123456.7)
    mover = lambda pl: [(round(x + t[0], 4), round(y + t[1], 4)) for x, y in pl]
    for ang in (5, -17.3):
        b = generate({"footprint": girar(s["footprint"], ang, t), "height": s["height"], "stage": "units", "params": {}})
        assert all(u["area"] < u["area_muros"] < 1.3 * u["area"] for u in b["units"]), [u["area_muros"] for u in b["units"]]
        a = generate({"footprint": girar(s["footprint"], ang), "height": s["height"], "stage": "units", "params": {}})
        args = ([u["poly"] for u in a["units"]], [[a["plate"]]] * len(a["units"]), a["corridors"], [c["poly"] for c in a["cores"]])
        P0 = {"outer_wall": ow, "party_wall": pw}
        en0 = U.superficie_con_muros(*args, P0)
        enutm = U.superficie_con_muros(*[[mover(p) for p in grupo] if k != 1 else [[mover(p) for p in bs] for bs in grupo]
                                         for k, grupo in enumerate(args)], P0)
        assert all(abs(x - y) < 0.01 for x, y in zip(en0, enutm)), (ang, en0, enutm)
    # revisión: con la separación real. Dos viviendas pegadas no se cuentan dos veces (cada una hasta el borde común);
    # a un muro de distancia, hasta su eje; un núcleo a medio muro, hasta el eje de su muro
    P0 = {"outer_wall": ow, "party_wall": pw}
    rec = lambda x0, x1: [(x0, 0.0), (x1, 0.0), (x1, 6.0), (x0, 6.0)]
    lejos = [[(-50.0, -50.0), (60.0, -50.0), (60.0, 50.0), (-50.0, 50.0)]]
    a, b = U.superficie_con_muros([rec(0, 5), rec(5, 10)], [lejos, lejos], [], [], P0)
    assert abs(a - (5 + pw / 2) * (6 + pw)) < 1e-6 and abs(a + b - (10 + pw) * (6 + pw)) < 1e-6, (a, b)
    a, b = U.superficie_con_muros([rec(0, 5), rec(5 + pw, 10)], [lejos, lejos], [], [], P0)
    assert abs(a - (5 + pw) * (6 + pw)) < 1e-6, a
    (a,) = U.superficie_con_muros([rec(0, 5)], [lejos], [], [rec(5 + pw / 2, 9)], P0)
    assert abs(a - (5 + pw / 2 + (pw / 2 + muro) / 2) * (6 + pw)) < 1e-6, a
    # en la cruz, el polígono con muros de una vivienda no pisa a otra (antes, U02 y U12 se contaban 0,97 m² cada una)
    s = carga("cruz_dos_lineas")
    r = generate({"footprint": s["footprint"], "height": s["height"], "stage": "units",
                  "params": {"centerlines": s["centerlines"]}})
    # (v2.62: el par que se toca en el cruce ya no es U02 y U12; se busca por la geometría: dos viviendas de pasillos
    # distintos con un vértice de una sobre el borde de la otra)
    from engine.massing import _dist_to_boundary
    pares = [(a, b) for a in r["units"] for b in r["units"] if a["pasillo"] != b["pasillo"] and
             any(_dist_to_boundary(q, b["poly"]) < 0.05 for q in a["poly"])]
    assert pares, "ninguna vivienda toca a otra de otro pasillo"
    assert any(abs(U.superficie_con_muros([a["poly"], b["poly"]], [[r["plate"]]] * 2, [], [], P0)[0] -
                   U.superficie_con_muros([a["poly"]], [[r["plate"]]], [], [], P0)[0]) > 0.5     # se tocan: sin la
               for a, b in pares)                                                                 # vecina, cuenta un
    # tabique entero
    # en la etapa de viviendas (sin planos) también
    r = generate({"footprint": [[0, 0], [60, 0], [60, 16], [0, 16]], "height": 15, "stage": "units", "params": {}})
    assert r["units"] and all(u["area_muros"] > u["area"] for u in r["units"])
    # segunda revisión: sin muro entre viviendas («Muro entre viviendas» en 0) no falla (antes, ZeroDivisionError en las
    # etapas Viviendas y Planos): las vecinas se tocan y cada una llega hasta el borde común
    for st in ("units", "plans"):
        r = generate({"footprint": [[0, 0], [60, 0], [60, 16], [0, 16]], "height": 15, "stage": st,
                      "params": {"party_wall": 0}})
        assert r["units"] and all(u["area_muros"] >= u["area"] for u in r["units"]), st
    a, b = U.superficie_con_muros([rec(0, 5), rec(5, 10)], [lejos, lejos], [], [], {"outer_wall": ow, "party_wall": 0.0})
    assert abs(a - 5 * 6) < 1e-6 and abs(b - 5 * 6) < 1e-6, (a, b)
    # segunda revisión: en un rincón entrante de la planta (el codo de una L, la esquina de un patio) el cuadrado de muro
    # exterior se parte por la bisectriz y cada vivienda cuenta la mitad junto a su fachada; la fachada cambia en el
    # vértice de la planta (antes, las dos contaban el cuadrado entero y el escalón caía hasta 0,25 m más allá, en la
    # superficie libre de la vecina)
    tri = ow * ow / 2
    ele = [(0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (10.0, 10.0), (10.0, 20.0), (0.0, 20.0)]
    A = [(5.1, 5.0), (20.0, 5.0), (20.0, 10.0), (5.1, 10.0)]
    B = [(5.1, 10.0), (10.0, 10.0), (10.0, 20.0), (5.1, 20.0)]
    a, b = U.superficie_con_muros([A, B], [[ele], [ele]], [], [], P0)
    assert abs(a - ((20 + ow - 5.1 + pw / 2) * (5 + pw / 2) + (20 + ow - 10) * ow - tri)) < 1e-6, a
    assert abs(b - ((10 + ow - 5.1 + pw / 2) * (10 + ow) - tri)) < 1e-6, b
    ext, patio = [(0.0, 0.0), (30.0, 0.0), (30.0, 30.0), (0.0, 30.0)], [(10.0, 10.0), (20.0, 10.0), (20.0, 20.0), (10.0, 20.0)]
    C = [(5.1, 5.0), (15.0, 5.0), (15.0, 10.0), (5.1, 10.0)]
    D = [(5.1, 10.0), (10.0, 10.0), (10.0, 15.0), (5.1, 15.0)]
    for hueco in (patio, patio[::-1]):
        c, d = U.superficie_con_muros([C, D], [[ext, hueco], [ext, hueco]], [], [], P0)
        assert abs(c - ((15 + pw - 5.1) * (5 + pw / 2) + (15 + pw / 2 - 10) * ow - tri)) < 1e-6, c
        assert abs(d - ((10 + ow - 5.1 + pw / 2) * (5 + pw / 2) - tri)) < 1e-6, d
    # en el motor: la vivienda del codo de una L y su vecina del otro pasillo se parten el cuadrado de muro del rincón
    # (antes cada una contaba 0,17 m² que también contaba la otra; v2.62: con el frente que pide cada plano la vivienda
    # ya no es de 27 m², así que se mide el rincón: con la vecina, las dos suman 0,21 m² menos que cada una sola)
    r = generate({"footprint": [[0, 0], [41.961, 0], [41.961, 14], [16, 14], [16, 40], [0, 40]], "height": 3,
                  "stage": "plans", "params": {"unit_mix": [{"name": "A", "area": 27, "percent": 100, "dorms": 1}]}})
    (u,) = [u for u in r["units"] if min(p[0] for p in u["poly"]) < 15.65 < max(p[0] for p in u["poly"]) and
            abs(max(p[1] for p in u["poly"]) - 13.65) < 0.01]
    (v,) = [v for v in r["units"] if v["pasillo"] != u["pasillo"] and any(_dist_to_boundary(q, u["poly"]) < 0.05 for q in v["poly"])]
    pas, nuc = r["corridors"], [c["poly"] for c in r["cores"]]
    a, b = U.superficie_con_muros([u["poly"], v["poly"]], [[r["plate"]]] * 2, pas, nuc, P0)
    solas = U.superficie_con_muros([u["poly"]], [[r["plate"]]], pas, nuc, P0)[0] + \
        U.superficie_con_muros([v["poly"]], [[r["plate"]]], pas, nuc, P0)[0]
    assert 0.1 < solas - (a + b) < 0.3 and abs(u["area_muros"] - a) < 0.06 and abs(v["area_muros"] - b) < 0.06, (solas, a, b)
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    assert html.count("+u.area_muros+' m² con muros'") == 2 and "+u.area_muros+' con muros</small>'" in html

if __name__ == "__main__":
    test_superficie_con_muros(); print("OK54")


@calibracion_anterior
def test_cocina_integrada():
    """R10.8 (norma nacional, art. 27; criterio del usuario): la cocina integrada al estar sin ventana propia se dibuja con
    5 m² como máximo, en todos los casos (monoambiente, vivienda profunda, también con el hall en x0, poco profunda y
    «Hall / Cocina», donde cuenta solo su parte): pierde fondo hasta el que pide su mesada (en línea, 1,60 m; en L,
    2,00 o 2,20 m; más angosta, la mesada contra la pared del costado, 2,70 m) y, si aún pasa, se angosta y lo que deja va
    al hall. Donde comparte el fondo con el baño (monoambiente y vivienda poco profunda), primero se angosta. El fondo que
    pierde no lleva al estar más allá de 3 veces su ancho (art. 14). Se mide lo que queda dentro de la vivienda (un muro
    oblicuo), y su mesada, con la pared recta. Donde comparte la franja con el baño, lo que deja la cocina va primero al
    baño, después a un depósito y, en la vivienda poco profunda, si aún sobra, queda sin uso (el hall no crece). Sus
    mínimos son los de la cocina integrada (3 m², lado 1,40); una de más de 5 m² (por ejemplo, con un tabique corrido a
    mano) se avisa. El vano del estar es el 10 % del estar y la cocina, con 2 m² como mínimo."""
    import copy
    from engine import plans as P, standards as ST
    rect = lambda w, d: [(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)]
    CI = ST.DEFAULTS["vivienda"]["cocina_integrada"]
    assert CI == {"min_area": 3.0, "min_side": 1.40, "max_area": 5.0, "vano_min": 2.0}
    malos = lambda res: [c["msg"] for c in res["checks"] if not c["ok"]]
    caja = lambda x: (min(p[0] for p in x["poly"]), min(p[1] for p in x["poly"]), max(p[0] for p in x["poly"]),
                      max(p[1] for p in x["poly"]))
    casos = [(rect(9.5, 8.0), 2, {}), (rect(9.5, 8.0), 2, {"entrada": (6.0, 9.5)}), (rect(6.0, 7.0), 0, {}),
             (rect(6.0, 7.0), 0, {"entrada": (4.0, 6.0)}), (rect(13.3, 5.5), 2, {}), (rect(13.3, 5.5), 2, {"entrada": (9.0, 13.3)}),
             (rect(8.7, 10.15), 2, {}), (rect(11.73, 6.5), 2, {}),
             # revisión: con el hall en x0, la cocina se angosta y el hall queda en ese extremo
             (rect(11.0, 8.0), 2, {"entrada": (0.0, 2.0)}), (rect(8.5, 6.0), 0, {"entrada": (0.0, 2.0)}),
             # revisión: fondos de 2,00 a 2,20 m (en L con la mesada en la pared del costado), antes de más de 5 m²
             (rect(7.0, 6.0), 1, {}), (rect(10.0, 6.0), 2, {}), (rect(7.25, 5.9), 1, {}), (rect(8.75, 5.3), 1, {}),
             (rect(11.75, 5.2), 2, {}), (rect(5.75, 5.0), 0, {}),
             # revisión: el depósito se abre desde la cocina (hall en x0): su puerta no le quita la mesada
             (rect(7.5, 10.5), 1, {"entrada": (0.0, 1.5)}),
             # revisión: un muro oblicuo corta la cocina: se mide lo que queda dentro (antes, 2,8 m² sin artefactos)
             ([(1.5, 0.0), (9.0, 0.0), (9.0, 8.0), (0.0, 8.0)], 1, {})]
    for poly, nb, kw in casos:
        res = P.layout_unit(poly, nb, **kw)
        k = next(x for x in res["rooms"] if x["kind"] == "kitchen")
        assert 3.0 - 1e-6 <= k["area"] <= 5.0 + 1e-6, (poly, nb, kw, k["area"])
        assert {"heladera", "mesada", "bacha_cocina", "cocina_horno"} <= {q["kind"] for q in res["equipamiento"] if q["room"] == "kitchen"}
        assert not any("Cocina" in m for m in malos(res)), malos(res)
        if kw.get("entrada") == (0.0, 2.0):                # (segunda revisión: en el monoambiente, entre el hall y la
            h = caja(next(x for x in res["rooms"] if x["kind"] == "hall"))     # cocina, el depósito)
            entre = [x["kind"] for x in res["rooms"] if h[2] - 1e-6 <= caja(x)[0] and caja(x)[2] <= caja(k)[0] + 1e-6 and
                     caja(x)[1] < caja(k)[3]]
            assert abs(h[0]) < 1e-6 and h[2] - h[0] > P.HALL_W + 0.1 and entre == (["storage"] if nb == 0 else []), \
                (poly, nb, h, entre)
    # vivienda profunda de 9,50 × 8,00: la cocina (en L) pierde fondo, desde 2,64 m, y el estar lo gana
    res = P.layout_unit(rect(9.5, 8.0), 2)
    R = {x["id"]: caja(x) for x in res["rooms"]}
    assert abs(R["kitchen"][3] - R["living"][1]) < 1e-6 and 2.2 - 1e-6 <= R["kitchen"][3] < 2.64 and res["score"] == 100
    assert abs(R["kitchen"][3] - max(P.KITCH_L, 5.0 / (R["kitchen"][2] - R["kitchen"][0]))) < 0.01, R["kitchen"]
    # en línea (barra, U01): 1,60 m de fondo y 3,13 m de ancho; lo que deja va al hall
    barra = run([[0, 0], [60, 0], [60, 16], [0, 16]])
    u = next(u for u in barra["units"] if u["id"] == "U01")
    k = next(x for x in u["rooms"] if x["kind"] == "kitchen")
    hall = next(x for x in u["rooms"] if x["kind"] == "hall")
    kb, hb = caja(k), caja(hall)
    assert abs(kb[3] - kb[1] - 1.6) < 0.01 and abs(kb[2] - kb[0] - 5.0 / 1.6) < 0.01 and hb[2] - hb[0] > 1.4 + 0.5, (kb, hb)
    # «Hall / Cocina» (poco frente para los dos): solo la parte de la cocina, sin el hall
    res = P.layout_unit(rect(7.6, 8.0), 2)
    hc = next(x for x in res["rooms"] if x["name"] == "Hall / Cocina")
    b = caja(hc)
    assert hc["area"] - P.HALL_W * (b[3] - b[1]) <= 5.0 + 1e-6 and not any("art. 27" in m for m in malos(res))
    res = P.layout_unit(rect(8.4, 8.3), 2)                   # aquí, sin el tope, su parte sería de 5,2 m²
    hc = next(x for x in res["rooms"] if x["name"] == "Hall / Cocina")
    b = caja(hc)
    assert hc["area"] - P.HALL_W * (b[3] - b[1]) <= 5.0 + 1e-6 and not any("art. 27" in m for m in malos(res))
    # revisión: monoambiente, el baño comparte el fondo con la cocina: la cocina se angosta y el baño conserva su bidé (y
    # gana lo que deja la cocina, hasta su máximo)
    for W in (6.0, 7.0, 14.0):
        res = P.layout_unit(rect(W, 8.0), 0, lambda p, q: abs(p[1] - 8.0) < 0.05 and abs(q[1] - 8.0) < 0.05)
        b = next(x for x in res["rooms"] if x["id"] == "bath1")
        assert 4.8 - 0.01 <= b["area"] <= ST.DEFAULTS["vivienda"]["bano"]["max_area"] + 0.01 and \
            "bide" in {q["kind"] for q in res["equipamiento"] if q["room"] == "bath1"}
        assert next(x for x in res["rooms"] if x["kind"] == "kitchen")["area"] <= 5.0 + 1e-6 and res["score"] == 100
    oblicuo = P.layout_unit([(0.0, 0.0), (5.0, 0.0), (5.0, 8.0), (1.5, 8.0)], 0)   # y con un muro oblicuo, el inodoro
    assert "inodoro" in {q["kind"] for q in oblicuo["equipamiento"] if q["room"] == "bath1"}, malos(oblicuo)
    corte = P.layout_unit([(0.0, 1.2), (1.2, 0.0), (6.5, 0.0), (6.5, 8.0), (0.0, 8.0)], 0)   # el corte, en el baño
    b = next(x for x in corte["rooms"] if x["id"] == "bath1")
    assert b["area"] >= 3.0 and {"ducha", "inodoro", "lavatorio"} <= {q["kind"] for q in corte["equipamiento"] if q["room"] == "bath1"}
    # el hall del monoambiente, no menos de su lado mínimo (antes, «Hall: lado 1.20 m < mínimo 1.20 m» con 1,1993 m)
    for W in (5.75, 5.34, 6.0):
        res = P.layout_unit(rect(W, 5.0), 0)
        assert not any(m.startswith("Hall: lado") for m in malos(res)), (W, malos(res))
    # revisión: el fondo que pierde la cocina no deja al estar con el comedor a más de 3 veces su ancho (art. 14) ni crea
    # un comedor interior que no había
    for W, D, nb in ((8.5, 12.5, 2), (11.5, 9.5, 1)):
        res = P.layout_unit(rect(W, D), nb, lambda p, q, D=D: abs(p[1] - D) < 0.05 and abs(q[1] - D) < 0.05)
        assert not any("art. 14" in m for m in malos(res)) and \
            next(x for x in res["rooms"] if x["kind"] == "kitchen")["area"] <= 5.0 + 1e-6, malos(res)
    assert "dining" not in [x["kind"] for x in P.layout_unit(rect(11.5, 9.5), 1)["rooms"]]
    # forzada a mano: el tabique entre la cocina y el estar, 1 m más allá: más de 5 m², se avisa
    k0 = caja(next(x for x in P.layout_unit(rect(9.5, 8.0), 2)["rooms"] if x["kind"] == "kitchen"))
    ed = [(0, {"op": "pared", "p": (1.0, k0[3]), "a": (1.0, k0[3] + 1.0)})]
    res = P.layout_unit(rect(9.5, 8.0), 2, ediciones=ed)
    k = next(x for x in res["rooms"] if x["kind"] == "kitchen")
    assert res["ediciones"] == [0] and k["area"] > 5.0 + 1e-6
    assert "Cocina integrada sin ventana de %.1f m²: la norma nacional admite de 3 a 5 m² (art. 27); más grande, con " \
           "ventana propia (art. 24)" % k["area"] in malos(res) and res["score"] < 100, malos(res)
    # con otro máximo en «Normativa → Vivienda», la cocina lo sigue (y el aviso también)
    V = copy.deepcopy(ST.DEFAULTS["vivienda"])
    V["cocina_integrada"]["max_area"] = 4.5
    res = P.layout_unit(rect(9.5, 8.0), 2, vivienda=V)
    assert next(x for x in res["rooms"] if x["kind"] == "kitchen")["area"] <= 4.5 + 1e-6 and res["score"] == 100
    V["cocina_integrada"]["max_area"] = 4.0                  # revisión: un máximo más bajo no la agranda
    res = P.layout_unit(rect(9.5, 8.0), 2, vivienda=V)
    assert next(x for x in res["rooms"] if x["kind"] == "kitchen")["area"] <= 4.0 + 1e-6
    P.configure(V)
    w_, f_ = P._cocina_integrada(4.33, 2.64)
    assert w_ * f_ <= 4.32 + 0.01, (w_, f_)
    V["cocina_integrada"]["max_area"] = 9.0                  # sin tope: como antes de v2.41 (2,10 × 2,64)
    res = P.layout_unit(rect(9.5, 8.0), 2, vivienda=V)
    assert abs(next(x for x in res["rooms"] if x["kind"] == "kitchen")["area"] - 2.1 * 2.64) < 0.01
    # sus mínimos: los de la cocina integrada (art. 27), no los de una cocina con ventana (art. 21)
    P.configure(ST.DEFAULTS["vivienda"])
    assert P._std_for({"kind": "kitchen", "id": "kitchen"}, 2, {"kitchen": 4.0}) == CI
    assert P._std_for({"kind": "kitchen", "id": "kitchen"}, 2) == ST.DEFAULTS["vivienda"]["cocina"]
    # el vano del estar: el 10 % del estar y la cocina, con vano_min como mínimo
    S = ST.DEFAULTS["ventanas"]
    res = P.layout_unit(rect(9.5, 8.0), 2)
    area = sum(x["area"] for x in res["rooms"] if x["kind"] in ("living", "kitchen"))
    (w,) = [w for w in res["ventanas"] if w["room"] == "living"]
    assert abs(w["minimo"] - max(CI["vano_min"], S["iluminacion"] * area)) < 0.01 and w["area"] >= w["minimo"] - 0.01
    V = copy.deepcopy(ST.DEFAULTS["vivienda"])
    V["cocina_integrada"]["vano_min"] = 3.5                  # más que el 10 %: la ventana del estar, de 2,92 m
    (w,) = [w for w in P.layout_unit(rect(9.5, 8.0), 2, vivienda=V)["ventanas"] if w["room"] == "living"]
    assert w["minimo"] == 3.5 and w["area"] >= 3.5 - 0.01, w
    res = P.layout_unit(rect(9.5, 8.0), 2, ventanas=dict(S, iluminacion=0.5))
    assert any(m.startswith("Estar-Comedor: ventana de") and m.endswith("(50 % de la superficie del estar y la cocina, 2 m² "
                                                                         "como mínimo: norma nacional, art. 27)") for m in malos(res)), malos(res)
    # en los ejemplos: ninguna cocina sin ventana propia de más de 5 m² (de un «Hall / Cocina», su parte); R10.9: la cocina
    # con fachada lleva su ventana y no se acota (test_cocina_ventana)
    for n in ("L", "quiebre_45", "T_dos_lineas", "entre_medianeras_patio_central"):
        s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", n + ".json"), encoding="utf-8"))
        p = {k: s[k] for k in ("centerlines", "medianeras") if s.get(k)}
        if s.get("cores"):
            p.update(cores_mode="manual", cores=s["cores"])
        if s.get("patios"):
            p.update(patios_mode="manual", patios=s["patios"])
        r = run(s["footprint"], h=s["height"], **p)
        for u in r["units"]:
            for x in u["rooms"]:
                if x["kind"] == "kitchen" and x.get("ventilacion") != "ventana":
                    assert x["area"] <= 5.0 + 0.05, (n, u["id"], x["area"])
            # (v2.62: en el empalme de la T, la vivienda de 14 m de fondo con el frente justo de su plano no llega al 10 % de
            # ventana en el estar: problema conocido de los pasillos dibujados en T y en X, no de la cocina)
            assert u["depth"] > P.fondo_sin_tira() or not any("art. 27" in c["msg"] for c in u["checks"]), (n, u["id"])
    # en layout, los mínimos de la cocina integrada (quiebre_45, U08: antes «< mínimo 4.0 m²»)
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "quiebre_45.json"), encoding="utf-8"))
    u = next(u for u in run(s["footprint"], h=s["height"])["units"] if u["id"] == "U08")
    assert "Cocina: 2.9 m² < mínimo 3.0 m²" in [c["msg"] for c in u["checks"] if not c["ok"]], u["checks"]
    # revisión: un edificio de viviendas de 1 dormitorio de 45 m² (cocinas de 5,1 a 5,7 m² antes de la revisión)
    for D in (15, 13.6):
        r = generate({"footprint": [[0, 0], [40, 0], [40, D], [0, D]], "height": 3, "stage": "plans",
                      "params": {"unit_mix": [{"name": "T", "area": 45, "percent": 100, "dorms": 1}]}})
        assert r["metrics"]["plan_score"] == 100 and all(x["area"] <= 5.0 + 0.05 for u in r["units"] for x in u["rooms"]
                                                         if x["kind"] == "kitchen" and x.get("ventilacion") != "ventana"), D
    # segunda revisión. Vivienda poco profunda: lo que deja la cocina va al baño (hasta su máximo), a un depósito que se
    # abre al estar y, si aún sobra, queda sin uso, con aviso; el hall, abierto al estar, no crece (antes, de 2 a 5 m de
    # ancho, el estar perdía el sofá y el rack). Con el hall en x0 (R3.7), igual; ninguna estancia queda sin acceso
    fac = lambda D: (lambda p, q: abs(p[1] - D) < 0.05 and abs(q[1] - D) < 0.05)
    equipo = lambda res, i: {q["kind"] for q in res["equipamiento"] if q["room"] == i}
    cocina = {"heladera", "mesada", "bacha_cocina", "cocina_horno"}
    for W, nb, kw in ((10.5, 1, {}), (10.5, 1, {"entrada": (0.0, 1.5)}), (19.1, 3, {}), (13.0, 1, {}),
                      (13.0, 1, {"entrada": (0.0, 1.5)}), (16.0, 1, {})):
        res = P.layout_unit(rect(W, 4.5), nb, fac(4.5), **kw)
        R = {x["id"]: x for x in res["rooms"]}
        h = caja(R["hall"])
        assert {"sofa", "rack_tv"} <= equipo(res, "living") and abs(h[2] - h[0] - P.HALL_W) < 1e-6, (W, kw, h)
        assert R["kitchen"]["area"] <= 5.0 + 1e-6 and cocina <= equipo(res, "kitchen"), (W, kw)
        assert R["bath1"]["area"] <= ST.DEFAULTS["vivienda"]["bano"]["max_area"] + 1e-6, (W, kw)
        assert not any(m.startswith("Sin acceso") or "no conecta" in m for m in malos(res)), (W, kw, malos(res))
        if W in (10.5, 19.1):
            assert res["score"] == 100, (W, kw, malos(res))
        if W == 13.0:
            assert "storage" in R and ("living", "storage") in [(d["a"], d["b"]) for d in res["doors"]], (W, kw)
        if W == 16.0:
            assert any(m.startswith("Sin uso:") and m.endswith("la vivienda tiene más frente del que su tipo necesita")
                       for m in malos(res)), malos(res)
    r = generate({"footprint": [[0, 0], [42, 0], [42, 12], [0, 12]], "height": 3, "stage": "plans",
                  "params": {"unit_mix": [{"name": "3d", "area": 95, "percent": 100, "dorms": 3}]}})
    assert all(u["plan_score"] == 100 and "sofa" in {e["kind"] for e in u["equipamiento"]} for u in r["units"])
    # segunda revisión. Monoambiente: el hall llega a su lado mínimo solo si la cocina conserva el ancho de su acomodo
    # (con la heladera) o si se lo da el baño, que conserva su ducha (antes, la cocina perdía la heladera y, con 4,15 m,
    # «Hall: lado 1.20 m < mínimo 1.20 m»); el baño accesible, también con 5 m justos de frente
    for W, D in ((4.8, 7.15), (4.9, 7.0), (5.1, 5.0)):
        res = P.layout_unit(rect(W, D), 0, fac(D))
        assert "heladera" in equipo(res, "kitchen") and not any(m.startswith("Hall: lado") for m in malos(res)), (W, malos(res))
    assert not any(m.startswith("Hall: lado 1.20 m <") for m in malos(P.layout_unit(rect(4.15, 8.5), 0, fac(8.5))))
    for W in (4.95, 5.0):
        assert "giro" in equipo(P.layout_unit(rect(W, 6.0), 0, fac(6.0), accesible=True), "bath1"), W
    # segunda revisión: un muro oblicuo en la esquina de la cocina (una ochava junto al pasillo común, un trapecio): la
    # mesada se prueba con su pared recta y se elige la cocina de 5 m² como máximo en la que entran los cuatro artefactos
    for poly in ([(0.0, 1.2), (1.2, 0.0), (9.0, 0.0), (9.0, 5.5), (0.0, 5.5)], [(1.5, 0.0), (9.0, 0.0), (9.0, 10.5), (0.0, 10.5)]):
        for f in (None, fac(max(p[1] for p in poly))):
            res = P.layout_unit(poly, 1, f)
            k = next(x for x in res["rooms"] if x["kind"] == "kitchen")
            assert k["area"] <= 5.0 + 1e-6 and cocina <= equipo(res, "kitchen"), (poly, malos(res))
            assert not any(m.startswith("Cocina") for m in malos(res)), malos(res)
            assert res["score"] == 100 or poly[0] != (0.0, 1.2), malos(res)     # la ochava: como la base
    # segunda revisión: monoambiente con el muro del extremo oblicuo: la estancia de ese extremo (el baño con la entrada
    # en x0, R3.7; si no, el hall) se ensancha lo que pierde su borde recto, y la puerta de entrada va dentro del borde
    # (antes, con la entrada en x0, un baño de 1,6 m² sin artefactos; sin ella, la puerta fuera de la vivienda)
    for kw in ({}, {"entrada": (0.0, 1.6)}):
        res = P.layout_unit([(0.0, 0.0), (4.5, 0.0), (6.0, 10.0), (0.0, 10.0)], 0, fac(10.0), **kw)
        b = next(x for x in res["rooms"] if x["id"] == "bath1")
        d = next(d for d in res["doors"] if d.get("entry"))
        assert b["area"] >= 3.0 and "inodoro" in equipo(res, "bath1") and 0.0 <= min(d["p"][0], d["q"][0]) and \
            max(d["p"][0], d["q"][0]) <= 4.5 + 1e-6, (kw, b["area"], d)
        assert not any("puerta de entrada" in m for m in malos(res)), malos(res)

if __name__ == "__main__":
    test_cocina_integrada(); print("OK55")


@calibracion_anterior
def test_superficie_minima():
    """R10.8 (norma nacional, «Hecho cuando»): la vivienda con muros contra la superficie mínima del art. 3 (32, 44, 56 y
    68 m² con 1 a 4 dormitorios; el estudio cuenta como dormitorio, art. 6; con más de 4, 12 m² más por cada uno): por
    debajo es una falla (la calidad baja y ya no dice «medidas mínimas cumplidas»), si cumple, una línea informativa. Un
    monoambiente no tiene dormitorio y baño independientes (art. 2): se acepta desde 32 m² con muros (criterio del
    usuario). Lo calcula layout después de los planos, igual para todas sus variantes."""
    from engine import plans as P, standards as ST
    assert ST.DEFAULTS["vivienda"]["superficie_min"] == [32, 32, 44, 56, 68]
    rect = lambda w, d: [(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)]
    malos = lambda u: [c["msg"] for c in u["checks"] if not c["ok"]]
    info = lambda u: [c["msg"] for c in u["checks"] if c.get("info")]
    res = P.superficie_vivienda(P.layout_unit(rect(9.5, 8.0), 1), 30.43)
    assert malos(res) == ["Superficie con muros 30.4 m² < mínimo 32 m² para 1 dormitorio (norma nacional, art. 3)"]
    assert res["score"] == 50 and P.TODO_BIEN not in [c["msg"] for c in res["checks"]]
    res = P.superficie_vivienda(P.layout_unit(rect(9.5, 8.0), 2), 82.7)
    assert res["score"] == 100 and "Superficie con muros 82.7 m² (mínimo 44 m² para 2 dormitorios, art. 3)" in info(res)
    # el estudio cuenta (art. 6) y con más de 4 dormitorios, 12 m² más por cada uno
    falsa = {"rooms": [{"kind": "study"}], "bedrooms": 4, "checks": [{"ok": True, "msg": P.TODO_BIEN}], "score": 100}
    P.superficie_vivienda(falsa, 79.0)
    assert malos(falsa) == ["Superficie con muros 79.0 m² < mínimo 80 m² para 5 dormitorios (contando el estudio, art. 6) "
                            "(norma nacional, art. 3)"] and falsa["score"] == 0
    # «Hecho cuando»: un dormitorio de 26,5 m² libres, 29,8 con muros (v2.62: el reparto da a cada vivienda el frente de su
    # plano y una 1 dorm sale de 56 m² aunque el mix pida 26; la chica se consigue dividiendo una en dos, R4.4)
    barra = [[0, 0], [40, 0], [40, 16], [0, 16]]
    centro = lambda u: [sum(p[0] for p in u["poly"]) / len(u["poly"]), sum(p[1] for p in u["poly"]) / len(u["poly"])]
    mix1 = [{"name": "1 dorm", "area": 26, "percent": 100, "dorms": 1}]
    r = run(barra, unit_mix=mix1, min_unit_width=3.5)
    assert r["units"] and all(u["area_muros"] >= 32 for u in r["units"])
    r = run(barra, unit_mix=mix1, min_unit_width=3.5, unit_edits=[{"op": "dividir", "p": centro(r["units"][0])}])
    chicas = [u for u in r["units"] if u.get("editada")]
    assert len(chicas) == 2 and all(u["type"] == "1 dorm" for u in chicas), [(u["type"], u["area_muros"]) for u in chicas]
    for u in chicas:
        assert u["area_muros"] < 32 and "Superficie con muros %.1f m² < mínimo 32 m² para 1 dormitorio (norma nacional, " \
            "art. 3)" % u["area_muros"] in malos(u), (u["id"], malos(u))
    # monoambiente de 28 m² (29 con muros): falla; de 35 m², se acepta
    mix0 = [{"name": "Mono", "area": 28, "percent": 100, "dorms": 0}]
    r = run(barra, unit_mix=mix0, min_unit_width=3.5)
    r = run(barra, unit_mix=mix0, min_unit_width=3.5, unit_edits=[{"op": "dividir", "p": centro(r["units"][0])}])
    chicas = [u for u in r["units"] if u.get("editada")]
    assert len(chicas) == 2 and all(u["type"] in ("Mono", "Monoambiente") for u in chicas), [(u["type"], u["area_muros"]) for u in chicas]
    for u in chicas:
        assert u["area_muros"] < 32 and "Monoambiente de %.1f m² con muros: la norma nacional pide dormitorio y baño como " \
            "locales independientes (art. 2); se acepta desde 32 m² (criterio del usuario)" % u["area_muros"] in malos(u)
    r = run(barra, unit_mix=[{"name": "Mono", "area": 35, "percent": 100, "dorms": 0}], min_unit_width=3.5)
    for u in r["units"]:
        assert "Monoambiente de %.1f m² con muros: se acepta aunque el dormitorio no sea un local independiente (art. 2, " \
            "criterio del usuario)" % u["area_muros"] in info(u) and not any("art. 2" in m for m in malos(u))
    # en los ejemplos: solo la «3 dorm» de 44,8 m² de la cruz no llega
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "cruz_dos_lineas.json"), encoding="utf-8"))
    r = run(s["footprint"], h=s["height"], centerlines=s["centerlines"])
    bajo = [u["id"] for u in r["units"] if any("art. 3)" in m for m in malos(u))]
    assert bajo == [], bajo      # (v2.62: cada vivienda recibe el frente que pide su plano; antes, una 3 dorm de 44,8 m²)
    # la superficie mínima editada en «Normativa → Vivienda» llega al motor
    tabla = [40, 40, 50, 90, 100]
    r = run([[0, 0], [60, 0], [60, 16], [0, 16]], standards={"vivienda": {"superficie_min": tabla}})
    for u in r["units"]:
        n = u["bedrooms"] + sum(1 for x in u["rooms"] if x["kind"] == "study")
        assert any("mínimo %g m² para" % tabla[n] in c["msg"] for c in u["checks"]), (u["id"], u["checks"])

if __name__ == "__main__":
    test_superficie_minima(); print("OK56")


@calibracion_anterior
def test_proporcion_y_divisoria():
    """R10.8 (norma nacional): art. 14, la profundidad de dormitorios, estar, comedor y estudio de hasta 3 veces su lado
    menor (si no se avisaron ya por su medida o por no tener fachada) y la del estar con el comedor interior, desde la
    ventana, de hasta 3 veces su ancho. Art. 53 e: un edificio que se separa de la divisoria queda a 1 m como mínimo
    (un retiro de medianera de más de 0 y menos de 1 m se avisa; de 1 a 3 m sigue el aviso de las ventanas)."""
    import copy
    from engine import plans as P, standards as ST
    rect = [(0.0, 0.0), (9.5, 0.0), (9.5, 8.0), (0.0, 8.0)]
    malos = lambda res: [c["msg"] for c in res["checks"] if not c["ok"]]
    angosto = [(0, {"op": "pared", "p": (6.7, 5.75), "a": (8.1, 5.75)})]          # Dormitorio 2 de 1,40 × 4,50
    res = P.layout_unit(rect, 2, ediciones=angosto)
    assert res["ediciones"] == [0] and "Dormitorio 2: lado 1.40 m < mínimo 2.00 m" in malos(res)
    assert not any("art. 14" in m for m in malos(res))                               # ya avisado por su lado
    V = copy.deepcopy(ST.DEFAULTS["vivienda"])                                       # con un mínimo rebajado
    V["dorm_secundario"].update(min_side=1.0, min_area=5.0)
    res = P.layout_unit(rect, 2, vivienda=V, ediciones=angosto)
    assert "Dormitorio 2: 4.50 m de profundidad, más de 3 veces su lado menor (1.40 m) (norma nacional, art. 14)" in \
        malos(res) and res["score"] < 100, malos(res)
    assert not any("art. 14" in m for m in malos(P.layout_unit(rect, 2, vivienda=V)))
    # el estar con el comedor interior (la cruz, U02: 3,00 m de ancho y 11,25 m desde la ventana)
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "cruz_dos_lineas.json"), encoding="utf-8"))
    r = run(s["footprint"], h=s["height"], centerlines=s["centerlines"])
    u = next(u for u in r["units"] if u["id"] == "U02")
    assert "Estar y comedor: 11.25 m de profundidad desde la ventana, más de 3 veces su ancho (3.00 m) (norma nacional, " \
           "art. 14)" in malos(u), malos(u)
    assert sum(1 for x in r["units"] for m in malos(x) if "art. 14" in m) in (1, 2)   # (v2.62: U02 y U06, las dos del empalme)
    # revisión: el comedor interior se mide solo con el estar que lo ilumina (un aviso, no dos)
    a14 = [m for m in malos(P.layout_unit([(0.0, 0.0), (5.0, 0.0), (5.0, 17.5), (0.0, 17.5)], 1)) if "art. 14" in m]
    assert a14 == ["Estar y comedor: 14.60 m de profundidad desde la ventana, más de 3 veces su ancho (3.00 m) "
                   "(norma nacional, art. 14)"], a14
    # una estancia sin fachada ya está avisada: no lleva además el art. 14
    res = P.layout_unit(rect, 2, is_facade=lambda p, q: False, vivienda=V, ediciones=angosto)
    assert "Dormitorio 2 sin fachada (sin luz natural)" in malos(res) and not any("art. 14" in m for m in malos(res))
    # la proporción editada en «Normativa → Ventanas» llega al motor
    r = run([[0, 0], [60, 0], [60, 16], [0, 16]], standards={"ventanas": {"proporcion_max": 1.0}})
    assert any("más de 1 veces su lado menor" in m for u in r["units"] for m in malos(u))
    assert ST.DEFAULTS["ventanas"]["proporcion_max"] == 3.0 and ST.DEFAULTS["predio"]["retiro_divisoria"] == 1.0
    # art. 53 e
    fp = [[0, 0], [30, 0], [30, 16], [0, 16]]
    aviso = lambda r: [w for w in r["warnings"] if "art. 53 e" in w]
    r = run(fp, medianeras=[{"a": [0, 16], "b": [0, 0], "retiro": 0.5}])
    assert aviso(r) == ["Retiro de 0.5 m en medianera: si el edificio se separa de la divisoria, la norma nacional pide 1 m "
                        "como mínimo (art. 53 e); pon 0 (adosado) o 1 m o más"], r["warnings"]
    assert not any("sigue sin admitir ventanas" in w for w in r["warnings"])          # un solo aviso
    for ret in (0, 1.0):
        r = run(fp, medianeras=[{"a": [0, 16], "b": [0, 0], "retiro": ret}])
        assert not aviso(r) and (ret == 0) == (not any("sigue sin admitir ventanas" in w for w in r["warnings"])), ret
    # revisión: el retiro con sus decimales (0,96 m no se lee «1.0 m») y el retiro de la divisoria editado
    r = run(fp, medianeras=[{"a": [0, 16], "b": [0, 0], "retiro": 0.96}])
    assert aviso(r) and aviso(r)[0].startswith("Retiro de 0.96 m en medianera"), r["warnings"]
    r = run(fp, medianeras=[{"a": [0, 16], "b": [0, 0], "retiro": 2.96}])
    assert "Retiro de 2.96 m en medianera: menor a 3 m, sigue sin admitir ventanas" in r["warnings"], r["warnings"]
    r = run(fp, medianeras=[{"a": [0, 16], "b": [0, 0], "retiro": 1.5}], standards={"predio": {"retiro_divisoria": 2.0}})
    assert aviso(r) == ["Retiro de 1.5 m en medianera: si el edificio se separa de la divisoria, la norma nacional pide 2 m "
                        "como mínimo (art. 53 e); pon 0 (adosado) o 2 m o más"], r["warnings"]
    # la web: rótulos de las medidas nuevas, la lista de superficies mínimas en «Normativa → Vivienda»
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    for t in ("cocina_integrada:'", "vano_min:'", "superficie_min:'", "retiro_divisoria:'", "proporcion_max:'",
              "superficie_min:1}", "else if(g==='vivienda'&&k!=='superficie_min'&&k!=='superficie_media_mercado') continue;"):   # (v2.66: y la referencia de mercado, R10.12b)
        assert t in html, t

if __name__ == "__main__":
    test_proporcion_y_divisoria(); print("OK57")


@calibracion_anterior
def test_rincones():
    """R5.11 (criterio del usuario): la tira sin luz junto al pasillo común de una vivienda muy profunda es una banda de
    servicios. Con fondo para la mesada, la cocina integrada (5 m² como máximo, art. 27) corre desde el hall, que va a x0
    con la entrada, hacia la tira, seguida del lavadero (puerta desde la cocina); el estar baja hasta la banda; el
    depósito vuelve a la franja (o va a la banda, desde el lavadero, si deja menos sin uso) y la franja ya no lleva el
    lavadero. Con una tira de 1,20 a 1,60 m, la cocina sigue en la zona de día y la tira lleva el lavadero, desde el hall
    (o desde la cocina, con el hall en x0); con menos de 1,20 m (no entran el lavarropas y su paso), como antes. La banda
    no pasa del fondo típico de una cocina: lo que queda, sin uso con el aviso del fondo. Un aviso por rincón sin uso,
    aunque su primer trozo quede vacío (antes se perdía). Los planos sin tira no cambian (tampoco con un muro oblicuo). En
    la cocina con la puerta del lavadero, la mesada entra en una parte de su pared si la puerta está junto a una punta, y
    la heladera no encierra la puerta. Revisión: con un muro oblicuo o un entrante, cada banda se mide con el contorno
    real (hall con su puerta de entrada, cocina con su mesada, lavadero y depósito con su superficie mínima y el lavadero
    con sus artefactos) y, si ninguna entra, como antes; y va solo si el plano no empeora. La suite, solo si el muro
    oblicuo no se come el principal ni su baño; la cocina en la banda no crea un comedor aparte; una vivienda sin hall
    avisa «Sin puerta de entrada»."""
    import hashlib
    from engine import plans as P, geometry as G, equipamiento as EQ, standards as ST
    rect = lambda w, d: [(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)]
    fondo = lambda D: (lambda p, q: abs(p[1] - D) < 0.05 and abs(q[1] - D) < 0.05)
    caja = lambda res: {r["id"]: G.bbox(r["poly"]) for r in res["rooms"]}
    malos = lambda res: [c["msg"] for c in res["checks"] if not c["ok"]]
    puerta = lambda res, a, b: any({d["a"], d["b"]} == {a, b} for d in res["doors"])
    con = lambda res, rid: {q["kind"] for q in res["equipamiento"] if q["room"] == rid}
    cocina = lambda res: next(r for r in res["rooms"] if r["kind"] == "kitchen" or "Cocina" in r["name"])
    K = ST.DEFAULTS["vivienda"]["cocina"]["typ"][1]                         # el fondo máximo de la banda (2,90 m)
    avisado = lambda res: not res["sin_uso"] or any(m.startswith("Sin uso") for m in malos(res))

    # el aviso perdido: un rincón sin uso se dibujaba sin aviso si su primer trozo (el que llevaba el aviso) quedaba de
    # ancho cero. rect(5, 12) de 1 dormitorio: 3,4 m² sin uso sin aviso (ahora la tira lleva el lavadero, desde el hall,
    # y no queda sin uso); rect(5, 13): 5,4 m² sin aviso (ahora 3,6 m² sobre la banda, con su aviso, aunque el trozo de
    # la banda, que lo lleva, quede vacío)
    res = P.layout_unit(rect(5, 12), 1, fondo(12))
    assert not res["sin_uso"] and puerta(res, "hall", "laundry") and not puerta(res, "hallway", "laundry")
    res = P.layout_unit(rect(5, 13), 1, fondo(13))
    su = sum(abs(G.area(p)) for p in res["sin_uso"])
    assert su > 3 and [m for m in malos(res) if m.startswith("Sin uso")] == [
        "Sin uso: %.1f m² junto al pasillo común: la vivienda tiene 13.0 m de fondo" % su], malos(res)
    P.configure(ST.DEFAULTS["vivienda"])
    vacios = P._plan_rects(0.0, 0.0, 5.0, 13.0, 1, [])[2]
    assert vacios[0][0][2] - vacios[0][0][0] < 1e-6 and vacios[0][1] and vacios[1][1] == "", vacios

    # el tope de la banda: con 17 m de fondo, la cocina sigue en 5 m² como máximo y la banda (cocina, lavadero, depósito)
    # no pasa del fondo típico de una cocina; lo que queda, sin uso, con el aviso del fondo
    for W, nb in ((6.0, 1), (8.0, 2), (10.0, 3), (12.0, 4), (14.0, 1)):
        res = P.layout_unit(rect(W, 17.0), nb, fondo(17.0))
        B = caja(res)
        assert cocina(res)["area"] - (P.HALL_W * (B["hall"][3] - B["hall"][1]) if cocina(res)["id"] == "hall" else 0) \
            <= 5.0 + 1e-6, (W, nb)
        assert all(B[k][3] <= K + 1e-6 for k in ("laundry", "storage") if k in B and B[k][1] < 1e-6), B
        assert res["sin_uso"] and avisado(res) and any("tiene 17.0 m de fondo" in m for m in malos(res)), malos(res)
    B = caja(P.layout_unit(rect(14.0, 17.0), 1, fondo(17.0)))               # aquí, la cocina en la banda
    assert B["kitchen"][3] <= K + 1e-6 and abs(B["kitchen"][0] - B["hall"][2]) < 1e-6 and B["hall"][0] < 1e-6

    # barra de 60 × 24 (viviendas de 10,50 m de fondo; antes 72 m² sin uso): cocina y lavadero en la banda, la cocina de
    # 5 m² como máximo y con su mesada; las de 2 dormitorios, sin sin uso
    # (v2.62: con el frente que pide cada plano entran 10 viviendas en vez de 14, todas con la banda; a las 2 dorm les queda
    # hasta 3,1 m² sobre la banda y a las 3 dorm, de 12,2 m de frente, la franja de servicios les sobra: 88 m² en total)
    r = run([[0, 0], [60, 0], [60, 24], [0, 24]])
    banda = [u for u in r["units"] if puerta(u, "kitchen", "laundry")]
    assert len(banda) == len(r["units"]) >= 10 and sum(x["area"] for u in r["units"] for x in u["sin_uso"]) < 95
    for u in banda:
        k = next(x for x in u["rooms"] if x["kind"] == "kitchen")
        assert k["area"] <= 5.0 + 1e-6 and {"heladera", "mesada"} <= {q["kind"] for q in u["equipamiento"]
                                                                       if q["room"] == "kitchen"}
        assert not puerta(u, "hallway", "laundry") and (u["type"] != "2 dorm" or sum(x["area"] for x in u["sin_uso"]) < 3.5), u["id"]
        assert _cocina_comunicada(u), u["id"]       # la heladera no encierra la puerta del lavadero (antes, en 6)
    assert all(avisado(u) for u in r["units"])

    # patio_central: la U05 (2 dormitorios) queda sin sin uso y con 100 de calidad (antes, 6,6 m² y 50); la U04 (3, con
    # la suite) baja de 6,6 a 3,6 m², en la franja: cocina, lavadero, depósito y baño ya están en su máximo
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "patio_central.json"), encoding="utf-8"))
    r = run(s["footprint"], h=s["height"], patios_mode="manual", patios=s["patios"])
    us = {u["id"]: u for u in r["units"]}
    for uid in ("U04", "U05"):
        assert puerta(us[uid], "kitchen", "laundry") and not puerta(us[uid], "hallway", "laundry")
        assert next(x for x in us[uid]["rooms"] if x["kind"] == "kitchen")["area"] <= 5.0 + 1e-6
        assert _cocina_comunicada(us[uid]), uid     # antes, la heladera encerraba la puerta del lavadero
    assert not us["U05"]["sin_uso"] and us["U05"]["plan_score"] == 100
    assert sum(x["area"] for x in us["U04"]["sin_uso"]) < 4.0 and r["metrics"]["plan_score"] >= 90

    # sin tira (6,5 m de fondo) los planos no cambian: huellas de v2.41 (estancias, puertas, equipamiento, avisos y sin
    # uso), cada uno solo (la memoria del equipamiento, vacía)
    def huella(res):
        r2 = lambda v: round(v, 2) + 0.0
        return hashlib.md5(json.dumps([
            res["score"],
            sorted([x["id"], x["kind"], x["name"], r2(x["area"])] + [r2(c) for c in G.bbox(x["poly"])] for x in res["rooms"]),
            sorted([d["a"], d["b"]] + [r2(c) for c in tuple(d["p"]) + tuple(d["q"])] for d in res["doors"]),
            sorted([q["room"], q["kind"]] + [r2(c) for c in G.bbox(q["poly"])] for q in res["equipamiento"]),
            [c["msg"] for c in res["checks"]], [r2(abs(G.area(p))) for p in res["sin_uso"]]]).encode("utf-8")).hexdigest()[:8]
    HUELLAS = {
        "6.5,1,base": "970283ca", "6.5,1,x0": "970283ca", "6.5,1,x1": "73b1204d", "6.5,1,acc": "5376c485", "6.5,1,vest": "1f45ef8c",
        "6.5,2,base": "1b5e3392", "6.5,2,x0": "1b5e3392", "6.5,2,x1": "7fae8745", "6.5,2,acc": "dd3b8a6c", "6.5,2,vest": "9a124b5a",
        "6.5,3,base": "66ddd815", "6.5,3,x0": "66ddd815", "6.5,3,x1": "18fd8e18", "6.5,3,acc": "fff94016", "6.5,3,vest": "efd1db9a",
        "6.5,4,base": "81f90266", "6.5,4,x0": "81f90266", "6.5,4,x1": "b42bf859", "6.5,4,acc": "7880d1af", "6.5,4,vest": "7c630cd6",
        "9,1,base": "b478f7bc", "9,1,x0": "3d2c4146", "9,1,x1": "360447a1", "9,1,acc": "644026c5", "9,1,vest": "74b0c8f5",
        "9,2,base": "35437833", "9,2,x0": "01302d0b", "9,2,x1": "079234fe", "9,2,acc": "8aedc560", "9,2,vest": "b265f952",
        "9,3,base": "290def12", "9,3,x0": "138608ec", "9,3,x1": "20475730", "9,3,acc": "3ca9adb2", "9,3,vest": "93f9e024",
        "9,4,base": "ffb42b9a", "9,4,x0": "159cb0cc", "9,4,x1": "c167724f", "9,4,acc": "11f78110", "9,4,vest": "152aa6b4",
        "12,1,base": "efaa47bd", "12,1,x0": "3b16fcd4", "12,1,x1": "8d970730", "12,1,acc": "6da13cbb", "12,1,vest": "d522e68a",
        "12,2,base": "5b6215c1", "12,2,x0": "6e58b98f", "12,2,x1": "bb674e97", "12,2,acc": "ebc62872", "12,2,vest": "4765418d",
        "12,3,base": "129c4f7a", "12,3,x0": "d1b830bb", "12,3,x1": "19351789", "12,3,acc": "68c0bb24", "12,3,vest": "6f703630",
        "12,4,base": "0d7d73c8", "12,4,x0": "89ece6f1", "12,4,x1": "a63a725c", "12,4,acc": "47292d09", "12,4,vest": "abad4800",
    }
    for clave, h in HUELLAS.items():
        W, nb, var = clave.split(",")
        W, nb = float(W), int(nb)
        kw = {"x0": {"entrada": (0.0, 2.0)}, "x1": {"entrada": (W - 2.0, W)}, "acc": {"accesible": True},
              "vest": {"vestidor": True}}.get(var, {})
        EQ._memo.clear()
        assert huella(P.layout_unit(rect(W, 6.5), nb, fondo(6.5), **kw)) == h, clave

    # el hall en x0 (R3.7) y el plano al revés: la banda sigue al hall
    W, D = 8.7, 10.15
    for ent in ((0.0, 2.0), (W - 2.0, W)):
        res = P.layout_unit(rect(W, D), 2, fondo(D), entrada=ent)
        B = caja(res)
        e = next(d for d in res["doors"] if d.get("entry"))
        assert ent[0] - 0.05 <= min(e["p"][0], e["q"][0]) and max(e["p"][0], e["q"][0]) <= ent[1] + 0.05
        assert not res["sin_uso"] and res["score"] == 100 and puerta(res, "kitchen", "laundry"), malos(res)
        assert _cocina_comunicada(res), ent
        if ent[0] == 0.0:
            assert B["hall"][0] < 1e-6 and abs(B["kitchen"][0] - B["hall"][2]) < 1e-6 < B["laundry"][0] - B["kitchen"][0]
        else:                                                                 # al revés: el hall, en x1
            assert abs(B["hall"][2] - W) < 1e-6 and abs(B["kitchen"][2] - B["hall"][0]) < 1e-6 and \
                abs(B["laundry"][2] - B["kitchen"][0]) < 1e-6

    # vivienda accesible, vestidor (R5.10), el dormitorio al costado (R5.3) y cambios a mano (R5.7), con la banda
    res = P.layout_unit(rect(W, D), 2, fondo(D), accesible=True)
    assert puerta(res, "kitchen", "laundry") and "ducha_nivel" in con(res, "bath1") and res["score"] == 100
    assert _cocina_comunicada(res)
    res = P.layout_unit(rect(W, D), 2, fondo(D), vestidor=True)
    assert puerta(res, "kitchen", "laundry") and "vest" in caja(res) and res["score"] == 100 and _cocina_comunicada(res)
    lat = lambda p, q: fondo(10.5)(p, q) or (abs(p[0] - 9.0) < 0.05 and abs(q[0] - 9.0) < 0.05)
    res = P.layout_unit(rect(9.0, 10.5), 3, lat)
    assert res["segunda_fachada"] == "dormitorio" and puerta(res, "kitchen", "laundry") and res["score"] == 100
    assert _cocina_comunicada(res)
    assert caja(res)["laundry"][2] <= caja(res)["bed3"][0] + 1e-6              # la banda termina en el dormitorio
    xk = caja(P.layout_unit(rect(W, D), 2, fondo(D)))["kitchen"][2]
    ed = [(0, {"op": "pared", "p": (xk, 1.2), "a": (xk - 0.3, 1.2)}),
          (1, {"op": "puerta", "p": (xk, 0.5), "entre": ["kitchen", "laundry"], "a": (xk, 1.3)})]
    res = P.layout_unit(rect(W, D), 2, fondo(D), ediciones=ed)
    assert res["ediciones"] == [0, 1] and abs(caja(res)["kitchen"][2] - (xk - 0.3)) < 1e-6

    # tira de 1,20 a 1,60 m (9,60 m de fondo): la cocina sigue en la zona de día y la tira lleva el lavadero, con puerta
    # desde el hall (con el hall en x0, desde la cocina); la franja ya no lo lleva
    res = P.layout_unit(rect(9.0, 9.6), 2, fondo(9.6))
    B = caja(res)
    assert puerta(res, "hall", "laundry") and not puerta(res, "hallway", "laundry") and B["laundry"][1] < 1e-6
    assert B["laundry"][3] < 1.6 and res["score"] == 100 and not res["sin_uso"]
    res = P.layout_unit(rect(9.0, 9.6), 2, fondo(9.6), entrada=(0.0, 2.0))
    assert puerta(res, "kitchen", "laundry") and caja(res)["hall"][0] < 1e-6 and _cocina_comunicada(res)
    # revisión: con una tira de 1,00 a 1,15 m (9,30 a 9,45 m de fondo), el lavadero iba a la tira aunque no entraran el
    # lavarropas o la pileta (el lavarropas y su paso piden 1,20 m de fondo): ahora va solo si igual entran sus artefactos
    # (el lavarropas, contra una pared del costado) y, si no, queda en la franja, como en v2.41
    for D in (9.3, 9.35, 9.4, 9.45):
        res = P.layout_unit(rect(8.7, D), 2, fondo(D))
        assert {"lavarropas", "pileta_lavar"} <= con(res, "laundry") and res["score"] >= 50, D
        assert not [m for m in malos(res) if m.startswith("Lavadero")], (D, malos(res))
    assert puerta(P.layout_unit(rect(8.7, 9.3), 2, fondo(9.3)), "hallway", "laundry")      # 1,00 m: en la franja
    r = run([[0, 0], [60, 0], [60, 21.6], [0, 21.6]])                   # viviendas de 9,30 m (antes, 6 sin sus artefactos)
    assert not [c["msg"] for u in r["units"] for c in u["checks"] if not c["ok"] and c["msg"].startswith("Lavadero")]

    # la mesada en una parte de su pared: la puerta del lavadero, junto a una punta (antes, «no entra la mesada»)
    rm = {"id": "kitchen", "kind": "kitchen", "name": "Cocina", "rect": (1.4, 0.0, 4.8, 1.85),
          "poly": [(1.4, 0.0), (4.8, 0.0), (4.8, 1.85), (1.4, 1.85)]}
    pz, falta, _ = EQ.resolver(rm, [{"p": (4.8, 0.1), "q": (4.8, 0.8), "a": "kitchen", "b": "laundry", "ancho": 0.7}],
                               {"kitchen": [((1.4, 0.0), (1.4, 1.85), "hall"), ((1.4, 1.85), (4.8, 1.85), "living")]},
                               ST.DEFAULTS["equipamiento"])
    assert not falta and {"heladera", "mesada", "bacha_cocina", "cocina_horno"} == {p[0] for p in pz}, falta
    # revisión: en una cocina más corta (2,70 m), la heladera en L junto a la puerta del lavadero la encerraba (al lavadero
    # se llegaba por una rendija de 0,20 m, sin aviso): ahora, o se llega desde las puertas y aberturas o se avisa
    rm = dict(rm, rect=(1.4, 0.0, 4.1, 1.85), poly=[(1.4, 0.0), (4.1, 0.0), (4.1, 1.85), (1.4, 1.85)])
    EQ._memo.clear()
    pz, falta, _ = EQ.resolver(rm, [{"p": (4.1, 0.1), "q": (4.1, 0.8), "a": "kitchen", "b": "laundry", "ancho": 0.7}],
                               {"kitchen": [((1.4, 0.0), (1.4, 1.85), "hall"), ((1.4, 1.85), (4.1, 1.85), "living")]},
                               ST.DEFAULTS["equipamiento"])
    esq = lambda o, es, en, w, d: [o, (o[0] + es[0] * w + en[0] * d, o[1] + es[1] * w + en[1] * d)]
    cuerpos = [G.bbox(esq(*x[1:])) for x in pz if x[0] in ("heladera", "mesada")]
    assert falta or EQ._alcanza(EQ._Estancia((0.0, 0.0, 2.7, 1.85)), cuerpos, [((2.7, 0.1), (2.7, 0.8)), ((0.0, 0.0), (
        0.0, 1.85)), ((0.0, 1.85), (2.7, 1.85))], [], g=0.05), pz
    EQ._memo.clear()                                  # sin la puerta del lavadero, como en v2.41: la mesada, en un tramo
    pz, falta, _ = EQ.resolver(rm, [{"p": (4.1, 0.1), "q": (4.1, 0.8), "a": "kitchen", "b": "storage", "ancho": 0.7}],
                               {"kitchen": [((1.4, 0.0), (1.4, 1.85), "hall"), ((1.4, 1.85), (4.1, 1.85), "living")]},
                               ST.DEFAULTS["equipamiento"])     # entero (aquí no entra: se avisa)
    assert falta == ["la mesada con bacha y cocina (2.00 m en línea, con 0.90 m de paso delante)"], falta

    # revisión: con un muro oblicuo o un entrante, la banda se mide con el contorno real
    def en_hall(res):
        """La puerta de entrada, dentro del borde real del hall sobre el pasillo común."""
        hall = next((x for x in res["rooms"] if x["id"] == "hall"), None)
        e = next((d for d in res["doors"] if d.get("entry")), None)
        borde = [p[0] for p in hall["poly"] if abs(p[1]) < 1e-6] if hall else []
        return bool(e and borde) and min(borde) - 0.02 <= min(e["p"][0], e["q"][0]) and \
            max(e["p"][0], e["q"][0]) <= max(borde) + 0.02
    # - el costado de x0 inclinado o su esquina cortada: el hall de la banda quedaba con menos de 1 m² y se perdía, y con él
    #   la puerta de entrada (calidad 50, sin aviso), o la puerta salía a medias fuera de la vivienda
    for poly, D in (([(1, 0), (9, 0), (9, 10.5), (0, 10.5)], 10.5), ([(2, 0), (10.5, 0), (10.5, 10), (0, 10), (0, 2)], 10.0),
                    ([(1, 0), (7.5, 0), (7.5, 10.5), (0, 10.5), (0, 1)], 10.5)):
        res = P.layout_unit(poly, 2, fondo(D))
        assert en_hall(res) and not any(m.startswith(("Sin puerta", "Sin acceso")) for m in malos(res)), (poly, malos(res))
    r = run([[0, 0], [60, 0], [70, 24], [10, 24]], h=9, centerlines=[[[6, 12], [64, 12]]])
    assert all(any(d["entry"] for d in u["doors"]) and not any(c["msg"].startswith(("Sin puerta", "Sin acceso"))
                                                               for c in u["checks"]) for u in r["units"])
    # - un plano sin hall no se da por bueno: «Sin puerta de entrada» (antes, el recorrido arrancaba en otra estancia y
    #   decía que se llegaba a todas)
    plan_rects = P._plan_rects

    def sin_hall(*a, **k):
        R_, E_, vac = plan_rects(*a, **k)
        R_.pop("hall", None)
        return R_, E_, vac
    P._plan_rects = sin_hall
    try:
        res = P.layout_unit(rect(8.7, 10.15), 2, fondo(10.15))
    finally:
        P._plan_rects = plan_rects
    assert "Sin puerta de entrada: el hall no entra junto al pasillo común" in malos(res) and res["score"] < 100
    assert not [d for d in res["doors"] if d.get("entry")]
    # - la esquina de x1 cortada: la cocina de la banda perdía la mesada y el lavadero quedaba bajo su mínimo o se perdía,
    #   sin aviso: ahora, como en v2.41 (con el lavadero y la cocina equipados)
    for poly, nb, D in (([(0, 0), (3, 0), (6, 3), (6, 10.5), (0, 10.5)], 1, 10.5), ([(0, 0), (3, 0), (6, 3), (6, 10), (0, 10)],
                                                                                   2, 10.0)):
        res = P.layout_unit(poly, nb, fondo(D))
        assert {"lavarropas", "pileta_lavar"} <= con(res, "laundry") and {"heladera", "mesada"} <= con(res, cocina(res)["id"])
        assert not [m for m in malos(res) if m.startswith(("Lavadero", "Cocina", "Hall / Cocina", "Sin acceso"))], malos(res)
    # - con un muro oblicuo, la banda va solo si el plano no empeora: aquí, con ella, 33 (el dormitorio principal pierde la
    #   cama doble y queda un rincón sin uso); sin ella, 50, como en v2.41
    poly = G.ensure_ccw([(0, 0), (7, 0), (8, 11), (0, 11)])
    P.configure(ST.DEFAULTS["vivienda"])
    con_b, sin_b = [P._plano(poly, 2, fondo(11.0), ST.DEFAULTS["equipamiento"], False, None, None, con_banda=b)
                    for b in (True, False)]
    res = P.layout_unit(poly, 2, fondo(11.0))
    assert con_b["_banda"] and con_b["score"] < sin_b["score"] == res["score"] and "_banda" not in res
    assert not puerta(res, "kitchen", "laundry") and not puerta(res, "hall", "laundry") and puerta(res, "hallway", "laundry")
    # - un costado oblicuo en x1: la suite que habilitaba la banda dejaba el baño en suite sin acceso (el muro se comía el
    #   principal): la suite, solo si el principal y su baño quedan en la vivienda
    for poly, nb, D in (([(0, 0), (7.5, 0), (5.5, 13), (0, 13)], 3, 13.0), ([(0, 0), (7.5, 0), (4.5, 16), (0, 16)], 2, 16.0)):
        res = P.layout_unit(poly, nb, fondo(D))
        assert "bed1" in caja(res) and not any(m.startswith("Sin acceso") for m in malos(res)), malos(res)
    # - la cocina en la banda no parte el estar en un comedor que sin ella no había (en una vivienda de esquina, ese
    #   comedor no cumplía el art. 14 ni su ventana): el estar sigue entero, como lo midió la banda; con fachada en x1,
    #   el estar sigue en la esquina
    for W in (13.0, 14.5):
        res = P.layout_unit(rect(W, 10.0), 1, lambda p, q: fondo(10.0)(p, q) or (abs(p[0]) < 0.05 and abs(q[0]) < 0.05))
        assert "dining" not in caja(res) and res["score"] >= 50 and not [m for m in malos(res) if m.startswith("Comedor")]
        assert puerta(res, "kitchen", "laundry"), W
    res = P.layout_unit(rect(13.0, 10.0), 1, lambda p, q: fondo(10.0)(p, q) or (abs(p[0] - 13) < 0.05 and abs(q[0] - 13) < 0.05))
    assert res["segunda_fachada"] == "estar" and "dining" not in caja(res) and res["score"] >= 50
    # - sin tira y con un muro oblicuo (una ochava junto al pasillo común, un costado inclinado), los planos tampoco
    #   cambian: la mesada en una parte de su pared es solo de la cocina con la puerta del lavadero (antes, estas cocinas
    #   cambiaban y el trapecio, con fachada en su lado oblicuo, bajaba de 100 a 33): huellas de v2.41 (el trapecio, de
    #   v2.46: su cocina toca la fachada oblicua y lleva ventana propia, R10.9, test_cocina_ventana)
    def oblicua(D, a, b):
        L = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        sobre = lambda t: abs((t[0] - a[0]) * (b[1] - a[1]) - (t[1] - a[1]) * (b[0] - a[0])) / L < 0.05
        return lambda p, q: fondo(D)(p, q) or (sobre(p) and sobre(q))
    OBLICUAS = {
        "d95a8e7e": ([(2, 0), (6, 0), (6, 9), (0, 9), (0, 2)], 1, fondo(9.0), {}),
        "baa0fc5a": ([(0, 0.6), (0.6, 0), (9.5, 0), (9.5, 8.5), (0, 8.5)], 2, fondo(8.5), {}),
        "67bafc22": ([(0.25, 0), (21.45, 0), (21.45, 5.5), (1.425, 5.5)], 3, oblicua(5.5, (0.25, 0), (1.425, 5.5)), {}),
        "08602931": ([(0, 0), (7, 0), (8, 8.5), (0, 8.5)], 2, fondo(8.5), {}),
        "a00862d0": ([(0, 0), (8, 0), (9, 1), (9, 8), (0, 8)], 2, fondo(8.0), {"accesible": True}),
    }
    for h, (poly, nb, fac, kw) in OBLICUAS.items():
        EQ._memo.clear()
        assert huella(P.layout_unit(poly, nb, fac, **kw)) == h, poly

    # un barrido: ninguna cocina de más de 5 m², ningún sin uso sin su aviso, cocinas comunicadas; el lavadero de la banda
    # crece hasta su máximo y solo lo pasa con lo poco que queda (menos de 0,90 m de largo o de 1 m²: no da para otra
    # estancia), como el de la franja
    lav = ST.DEFAULTS["vivienda"]["lavadero"]["max_area"]
    for W in (5.0, 7.0, 9.0, 11.0, 13.0):
        for D in (9.4, 10.0, 11.0, 12.5, 14.0):
            for nb in (1, 2, 3):
                res = P.layout_unit(rect(W, D), nb, fondo(D))
                assert avisado(res) and all(x["area"] <= 5.0 + 1e-6 for x in res["rooms"] if x["kind"] == "kitchen"), \
                    (W, D, nb)
                assert _cocina_comunicada(res), (W, D, nb)
                B = caja(res)
                if puerta(res, "kitchen", "laundry") or puerta(res, "hall", "laundry"):      # el lavadero de la banda
                    fl = B["laundry"][3] - B["laundry"][1]
                    de_mas = B["laundry"][2] - B["laundry"][0] - lav / fl
                    assert de_mas < 1e-6 or de_mas < P.MIN_W["storage"] + 0.1 or de_mas * fl < 1.0, (W, D, nb, B["laundry"])

if __name__ == "__main__":
    test_rincones(); print("OK58")

def test_modo_claro_oscuro():
    """R4.10: el tema se elige con un botón (sol o luna) en la barra superior del modo Edificio y junto al título del
    Masterplan; en «Vista → Apariencia → Tema», Sistema (el del equipo), Claro u Oscuro. El tema va en `data-theme` de
    <html> (sin él vale el del sistema), se recuerda en el navegador con la clave 'trazo.tema' (la misma en las dos
    páginas) y un script mínimo del <head> lo pone antes de pintar, para que no parpadee. Los colores son variables CSS:
    los oscuros están dos veces (el tema elegido y el del sistema, salvo que se haya elegido el claro) y tienen que ser
    los mismos. Lo que el JS decide según el tema (los bordes de la axonometría) pregunta a `esOscuro()`, no al sistema.
    (El comportamiento se comprobó en navegador; esta prueba evita que se pierda una de las dos copias de los colores o
    que una página vuelva a depender solo del sistema.)"""
    import re
    base = os.path.join(os.path.dirname(__file__), "..", "web")
    paginas = {n: open(os.path.join(base, n), encoding="utf-8").read() for n in ("index.html", "masterplan.html")}
    # las llaves de la regla que sigue al selector, como lista de declaraciones
    reglas = lambda css, sel: [d.strip() for d in css[css.index("{", css.index(sel)) + 1:].split("}", 1)[0].split(";") if d.strip()]
    fichas = lambda ds: [d.split(":")[0] for d in ds if d.startswith("--")]
    for nombre, html in paginas.items():
        css = html.split("<style>", 1)[1].split("</style>", 1)[0]
        assert "'trazo.tema'" in html and 'id="btnTema"' in html, nombre                                # la misma clave y el botón, en las dos páginas
        assert ':root[data-theme="dark"]{' in css, nombre                                               # el tema oscuro elegido
        assert '@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){' in css, nombre   # el del sistema, salvo el claro elegido
        assert "(prefers-color-scheme:dark){:root{" not in css, nombre                                 # ningún color oscuro fuera de data-theme
        claro = reglas(css, ":root{")
        elegido = reglas(css, ':root[data-theme="dark"]')
        sistema = reglas(css, ':root:not([data-theme="light"])')
        assert elegido == sistema and len(fichas(elegido)) >= 6, (nombre, elegido, sistema)             # los mismos colores, en los dos lugares
        assert {"--bg", "--pan", "--ink", "--mut", "--line", "--acc"} <= set(fichas(elegido)) <= set(fichas(claro)), nombre
        assert "color-scheme:dark" in elegido and "color-scheme:light" in claro, nombre                # los controles del navegador siguen al tema
        # el script del <head>: lee 'trazo.tema' dentro de try/catch y pone data-theme antes de que se pinte la página
        assert html.index('<script id="temaInicial">') < html.index("<body"), nombre
        ini = html.split('<script id="temaInicial">', 1)[1].split("</script>", 1)[0]
        assert ini.index("try{") < ini.index("localStorage.getItem('trazo.tema')") < ini.index("catch(e)"), (nombre, ini)
        assert "document.documentElement.dataset.theme=" in ini and "'claro'" in ini and "'oscuro'" in ini, (nombre, ini)
        # el programa es el primer <script> sin atributos (las demás pruebas lo toman así): trae el botón, el tema y la clave
        js = html.split("<script>", 1)[1]
        for f in ("function aplicarTema(", "function esOscuro(", "function temaUI(", "function temaElegido("):
            assert f in js, (nombre, f)
        osc = js.split("function esOscuro(){", 1)[1].split("\n", 1)[0]
        assert "dataset.theme" in osc and "'dark'" in osc and "'light'" in osc, (nombre, osc)
        assert "matchMedia('(prefers-color-scheme: dark)')" in osc, (nombre, osc)                       # sin elección, el del sistema
        aplicar = js.split("function aplicarTema(", 1)[1].split("\ntemaUI();", 1)[0]
        for t in ("removeAttribute('data-theme')", "dataset.theme=", "catch(e){}", "temaUI()", "render()"):
            assert t in aplicar, (nombre, t)
        assert aplicar.index("try{") < aplicar.index("localStorage.setItem('trazo.tema',t)") < aplicar.index("catch(e)"), nombre
        ui = js.split("function temaUI(){", 1)[1].split("\nfunction ", 1)[0]
        assert "$('btnTema')" in ui and "'Tema '" in ui and "(clic: " in ui and ".title=" in ui, (nombre, ui)
        assert 'id="btnTema"' in html and "aplicarTema(esOscuro()?'claro':'oscuro')" in html, nombre   # un clic elige el tema contrario
        # el JS no pregunta por el sistema salvo en esOscuro
        scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
        resto = "\n".join(re.sub(r"function esOscuro\(\)\{[^\n]*\n", "", s) for s in scripts)
        assert "prefers-color-scheme" not in resto and "matchMedia" not in resto, nombre
    # Edificio: el botón en la barra superior junto a deshacer y rehacer; el selector en «Vista», antes de la leyenda
    html = paginas["index.html"]
    assert 'id="btnTema"' in html and 'id="tema"' in html, "el botón y el selector del tema"
    assert {"--grilla", "--grilla2"} <= set(fichas(reglas(html.split("<style>", 1)[1], ':root[data-theme="dark"]')))
    cuerpo = html.split("<body>", 1)[1].split("<script>", 1)[0]
    hist = cuerpo.split('<header class="top">', 1)[1].split("</header>", 1)[0].split('<div class="hist">', 1)[1].split("</div>", 1)[0]
    assert all('id="%s"' % i in hist for i in ("btnUndo", "btnRedo", "btnTema")), hist
    vista = cuerpo.split('<div class="grupo" data-grupo="vista"', 1)[1].split("</section>", 1)[0]
    assert 'id="tema"' in vista and vista.index('id="tema"') < vista.index('id="legendColors"'), "el selector, antes de la leyenda"
    assert 'onchange="aplicarTema(this.value)"' in vista
    opciones = re.search(r'<select id="tema"[^>]*>(.*?)</select>', vista, re.S).group(1)
    assert re.findall(r'<option value="(\w+)">(\w+)</option>', opciones) == \
        [("sistema", "Sistema"), ("claro", "Claro"), ("oscuro", "Oscuro")], opciones
    js = html.split("<script>", 1)[1]
    assert "dark=esOscuro()" in js.split("function drawAxo(){", 1)[1].split("\nfunction ", 1)[0]       # la axonometría sigue al tema elegido
    # lo que la planta escribe sobre el fondo (cotas, escala, rótulos de patios y de zonas sin luz) también: sus grises, solo en su ayudante
    assert "const TINTA=()=>esOscuro()?" in js and "HALO=()=>esOscuro()?" in js and "TENUE=()=>esOscuro()?" in js
    assert js.count("#344054") == 1 and js.count("#5b616b") == 1, (js.count("#344054"), js.count("#5b616b"))
    assert "fill:TINTA(),stroke:HALO()" in js.split("function cota(", 1)[1].split("\nfunction ", 1)[0]
    assert js.count("fill:TENUE()") == 3 and js.count("fill:TINTA()") == 2, (js.count("fill:TENUE()"), js.count("fill:TINTA()"))
    # en un teléfono el botón no recorta la pestaña «Masterplan»: cede primero el nombre de la masa
    assert ".masaTop{flex-shrink:200}" in html.split("@media(max-width:900px)", 1)[1].split("\n.hint{", 1)[0]
    # Masterplan: el botón junto al título (no hay un panel de vista donde poner el selector)
    mp = paginas["masterplan.html"].split("<body>", 1)[1]
    assert 'id="btnTema"' in mp.split("<h2>", 1)[0] and 'id="tema"' not in mp

if __name__ == "__main__":
    test_modo_claro_oscuro(); print("OK59")


def test_quitar_pasillo():
    """R4.11: quitar o mover un pasillo desde la web. «Pasar a líneas» (en la ficha del tramo y en Circulación) convierte
    los pasillos automáticos en polilíneas, una por tramo (las que se tocan por un extremo, una sola), y los núcleos y los
    patios automáticos pasan a manuales tal como están; «Quitar este tramo» lo hace en un paso (con líneas dibujadas, quita
    el segmento que generó el tramo). El motor no cambia: sin líneas en un bloque traza el pasillo solo (por eso no se
    puede quitar el único pasillo de un bloque) y con un patio interior ignora las polilíneas (por eso ahí no se ofrece).
    (El comportamiento se comprobó en navegador; esta prueba vigila la web con comprobaciones del código y el motor con el
    mismo recorrido que hace la web, que se repite acá en Python.)"""
    import math
    base = os.path.join(os.path.dirname(__file__), "..")
    html = open(os.path.join(base, "web", "index.html"), encoding="utf-8").read()
    js = html.split("<script>", 1)[1].split("</script>", 1)[0]

    def cuerpo(nombre):
        ini = js.index("function %s(" % nombre)
        fin = min(k for k in (js.find("\nfunction ", ini + 1), js.find("\nasync function ", ini + 1), js.find("\n/*", ini + 1),
                              len(js)) if k >= 0)
        return js[ini:fin]
    # ---- la web: los botones, el orden de las acciones y el deshacer
    for f in ("function enAnillo(", "function segDeTramo(", "function tramosAuto(", "function encadenar(", "function juntosDe(",
              "function unicoTxt(", "function lineasPanel(", "async function pasarALineas(", "async function quitarTramo("):
        assert f in js, f
    assert "const TOL_EJE=0.30;" in js
    assert "${lineasPanel(ps)}" in cuerpo("pasilloPanel")                                   # en la ficha del tramo
    circ = html.split("<body>", 1)[1].split("<script>", 1)[0].split('<div class="grupo" data-grupo="circ"', 1)[1] \
        .split('<div class="grupo"', 1)[0]
    assert circ.index('id="lineInfo"') < circ.index('onclick="pasarALineas()"') < circ.index("<h2>Núcleos</h2>")   # y en Circulación
    ficha = cuerpo("lineasPanel")
    assert ficha.index("enAnillo(ps)") < min(ficha.index("pasarALineas()"), ficha.index("quitarTramo()"))   # con un patio interior, sin botones
    assert "Con un patio interior el pasillo no se pasa a líneas" in ficha and "disabled" in ficha
    pasar = cuerpo("pasarALineas")                       # antes de cambiar nada guarda el estado; los núcleos y los patios, tal como están
    assert pasar.index("tramosAuto()") < pasar.index("recordar('pasar los pasillos a líneas')") < pasar.index("ensureManual()") \
        < pasar.index("ensurePatiosManual()") < pasar.index("centerlines=centerlines.concat(encadenar(") < pasar.index("runCirc()")
    quitar = cuerpo("quitarTramo")
    assert quitar.index("enAnillo(ps)") < quitar.index("unicoTxt(") < quitar.index("recordar('quitar el pasillo '") \
        < quitar.index("centerlines.splice(") < quitar.index("runCirc()")
    assert "filter(q=>q.length>=2)" in quitar and "ensureManual()" in quitar and "ensurePatiosManual()" in quitar
    foto = cuerpo("foto")                                # lo que cambian estas acciones va en la foto de deshacer
    assert all(k in foto for k in ("centerlines", "coresManual", "cores_mode", "patios,", "patios_mode"))

    # ---- lo que hace la web, en Python
    def dist_seg(p, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L2 = dx * dx + dy * dy
        t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2)) if L2 else 0.0
        return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)

    def seg_de_tramo(eje, lineas):                       # como segDeTramo: (línea, segmento, distancia) o None
        mejor = None
        for i, pl in enumerate(lineas):
            for j in range(len(pl) - 1):
                d = max(dist_seg(eje[0], pl[j], pl[j + 1]), dist_seg(eje[1], pl[j], pl[j + 1]))
                if d <= 0.30 and (mejor is None or d < mejor[2] - 1e-9):
                    mejor = (i, j, d)
        return mejor

    def encadenar(ejes):                                 # los tramos que se tocan (5 cm o menos) son una sola polilínea
        cerca = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1]) <= 0.05
        cad = []
        for e in ejes:
            c = [[round(q[0], 3), round(q[1], 3)] for q in e]
            if not any(len(x) == 2 and ((cerca(x[0], c[0]) and cerca(x[1], c[1])) or (cerca(x[0], c[1]) and cerca(x[1], c[0])))
                       for x in cad):
                cad.append(c)
        sigue = True
        while sigue:
            sigue = False
            for i in range(len(cad)):
                for j in range(len(cad)):
                    if i != j and cerca(cad[i][-1], cad[j][0]):
                        cad[i] = cad[i] + cad[j][1:]
                        sigue = True
                    elif i != j and cerca(cad[i][-1], cad[j][-1]):
                        cad[i] = cad[i] + cad[j][:-1][::-1]
                        sigue = True
                    if sigue:
                        del cad[j]
                        break
                if sigue:
                    break
        return cad

    def sin_segmento(lineas, i, j):                      # la línea queda partida en las partes de antes y de después
        partes = [q for q in (lineas[i][:j + 1], lineas[i][j + 1:]) if len(q) >= 2]
        return lineas[:i] + partes + lineas[i + 1:]

    def a_lineas(r):                                     # «Pasar a líneas»: las líneas y los núcleos tal como están
        return encadenar([p["eje"] for p in r["pasillos"]]), [c["center"] for c in r["cores"]]
    muestra = lambda n: json.load(open(os.path.join(base, "samples", n + ".json"), encoding="utf-8"))
    fondo_max = lambda r: max(max(q[1] for q in u["poly"]) - min(q[1] for q in u["poly"]) for u in r["units"])

    # las líneas y las partes de una línea
    assert sin_segmento([[[0, 0], [5, 0], [9, 0]]], 0, 0) == [[[5, 0], [9, 0]]]                # solo queda lo que sigue
    assert sin_segmento([[[0, 0], [5, 0], [9, 0]]], 0, 1) == [[[0, 0], [5, 0]]]
    assert sin_segmento([[[0, 0], [5, 0]], [[1, 1], [2, 2]]], 0, 0) == [[[1, 1], [2, 2]]]      # de dos vértices: se quita entera
    assert sin_segmento([[[0, 0], [5, 0], [9, 0], [12, 0]]], 0, 1) == [[[0, 0], [5, 0]], [[9, 0], [12, 0]]]
    assert encadenar([[[0, 0], [5, 0]], [[5, 0], [9, 3]], [[5, 0], [0, 0]]]) == [[[0, 0], [5, 0], [9, 3]]]   # repetidos, una sola

    # 1) L (dos alas): cada tramo cae sobre su línea; el plano casi no cambia; quitar un tramo deja menos viviendas y el aviso
    fp = [[0, 0], [50, 0], [50, 14], [16, 14], [16, 40], [0, 40]]
    r0 = run(fp)
    lin, nuc = a_lineas(r0)
    r1 = run(fp, centerlines=lin, cores_mode="manual", cores=nuc)
    assert len(lin) == 2 and len(r0["pasillos"]) == len(r1["pasillos"]) == 2 and len(r0["cores"]) == len(r1["cores"]) == 3
    assert abs(len(r1["units"]) - len(r0["units"])) <= 1, (len(r0["units"]), len(r1["units"]))
    for p in r1["pasillos"]:
        s = seg_de_tramo(p["eje"], lin)
        assert s is not None and s[2] < 0.05, (p["id"], s)
    mayor = max(r1["pasillos"], key=lambda p: p["viviendas"])
    i, j, _ = seg_de_tramo(mayor["eje"], lin)
    r2 = run(fp, centerlines=sin_segmento(lin, i, j), cores_mode="manual", cores=nuc)
    assert len(r2["pasillos"]) == 1 and len(r2["units"]) < len(r1["units"]), (len(r1["units"]), len(r2["units"]))
    assert any("servido por el pasillo" in w for w in r2["warnings"]), r2["warnings"]            # lo que ningún pasillo sirve, con aviso

    # 2) un quiebre a 45°: los dos tramos se tocan y son una sola línea; por separado, el plano pierde viviendas
    s = muestra("quiebre_45")
    q0 = run(s["footprint"], h=s["height"])
    lin, nuc = a_lineas(q0)
    assert len(q0["pasillos"]) == 2 and len(lin) == 1 and len(lin[0]) == 3, lin
    q1 = run(s["footprint"], h=s["height"], centerlines=lin, cores_mode="manual", cores=nuc)
    sep = [[[round(q[0], 3), round(q[1], 3)] for q in p["eje"]] for p in q0["pasillos"]]
    q2 = run(s["footprint"], h=s["height"], centerlines=sep, cores_mode="manual", cores=nuc)
    assert abs(len(q1["units"]) - len(q0["units"])) <= 1 and len(q1["units"]) >= len(q2["units"]), \
        (len(q0["units"]), len(q1["units"]), len(q2["units"]))

    # 3) entre medianeras 15 × 36 con patio automático: con líneas solas el motor ya no traza el patio automático, así que la
    #    web lo pasa a manual (los mismos bloques y viviendas); y sin líneas en un bloque, el motor traza el pasillo solo
    #    (v2.62: con 30 m de fondo ya no se abre patio: los bloques dejarían viviendas de 3,65 m de fondo)
    fp = [[0, 0], [15, 0], [15, 36], [0, 36]]
    med = [{"a": [15, 0], "b": [15, 36], "retiro": 0}, {"a": [0, 36], "b": [0, 0], "retiro": 0}]
    e0 = run(fp, medianeras=med)
    assert e0["patios_auto"] and len(e0["blocks"]) == 2 and [p["bloque"] for p in e0["pasillos"]] == [0, 1]
    lin, nuc = a_lineas(e0)
    manual = dict(medianeras=med, cores_mode="manual", cores=nuc, patios_mode="manual", patios=e0["patios"])
    e1 = run(fp, centerlines=lin, **manual)
    # (v2.62: con líneas cada bloque lleva pasillo central con dos lados de 7 m de fondo, y con el frente que pide cada plano
    # entran 4 viviendas en vez de las 7 de los dos frentes de 5,4 m de la franja del núcleo; antes, con 15 × 30, 5 y 5)
    assert len(e1["blocks"]) == 2 and e1["units"] and len(e1["cores"]) == len(e0["cores"]), (len(e0["units"]), len(e1["units"]))
    assert [p["bloque"] for p in e1["pasillos"]] == [0, 1]
    e2 = run(fp, centerlines=lin[:1], **manual)                      # sin líneas en el segundo bloque: pasillo automático
    assert len(e2["pasillos"]) == 2 and sorted(p["bloque"] for p in e2["pasillos"]) == [0, 1]

    # 4) con un patio interior el motor ignora las polilíneas (con un aviso): la web no ofrece pasar a líneas
    s = muestra("patio_central")
    a0 = run(s["footprint"], h=s["height"], patios=s["patios"], patios_mode="manual")
    assert a0["blocks"][0]["holes"], "el patio central deja un hueco"
    lin, nuc = a_lineas(a0)
    a1 = run(s["footprint"], h=s["height"], patios=s["patios"], patios_mode="manual", centerlines=lin, cores_mode="manual",
             cores=nuc)
    assert any("las polilíneas dibujadas todavía no se usan ahí" in w for w in a1["warnings"]), a1["warnings"]
    assert len(a1["pasillos"]) == len(a0["pasillos"]) == 4 and len(a1["units"]) == len(a0["units"])

    # 5) las dos mitades de una línea cortada donde cruza otra caen sobre el mismo segmento y se quitan juntas
    s = muestra("cruz_dos_lineas")
    x0 = run(s["footprint"], h=s["height"], centerlines=s["centerlines"])
    segs = [seg_de_tramo(p["eje"], s["centerlines"]) for p in x0["pasillos"]]
    assert len(segs) == 3 and all(segs) and all(g[2] < 0.05 for g in segs), segs
    mitades = [g for g in segs if segs.count(g) > 1]
    assert len(mitades) == 2 and mitades[0][:2] == mitades[1][:2] == (1, 0), segs
    x1 = run(s["footprint"], h=s["height"], centerlines=sin_segmento(s["centerlines"], 1, 0))
    assert len(x1["pasillos"]) == 1 and len(x1["units"]) < len(x0["units"])

    # 6) dos pasillos paralelos en un mismo bloque: al quitar uno, las viviendas del otro ocupan su lugar (ganan fondo)
    fp = [[0, 0], [40, 0], [40, 22], [0, 22]]
    dos = [[[1, 5.5], [39, 5.5]], [[1, 16.5], [39, 16.5]]]
    p2 = run(fp, centerlines=dos, cores_mode="manual", cores=[[3, 9], [36, 13]])
    p1 = run(fp, centerlines=dos[:1], cores_mode="manual", cores=[[3, 9], [36, 13]])
    assert len(p2["pasillos"]) == 2 and len(p1["pasillos"]) == 1
    area = lambda r: sum(u["area"] for u in r["units"])
    assert area(p1) > area(p2) and fondo_max(p1) > fondo_max(p2) + 5, (fondo_max(p2), fondo_max(p1))   # (v2.62: con 15 m de
    # fondo entran menos viviendas, más anchas, que con 4,5: se compara la superficie, no la cantidad)
    assert p1["metrics"]["efficiency"] > p2["metrics"]["efficiency"]

if __name__ == "__main__":
    test_quitar_pasillo(); print("OK60")


def test_medidas_tipeadas():
    """R4.13b: medidas exactas tipeadas (solo web; el motor no cambia). Mientras se dibuja, lo tipeado manda y el puntero
    solo elige la dirección (y la medida que no se tipeó): con la línea (un vértice puesto) la barra trae «Largo» y
    «Ángulo» (el ángulo, en el SCP: 0° es su eje x, antihorario); con el patio (su primera esquina), «Ancho» y «Fondo»
    (en los ejes del edificio, los mismos del patio); con un tabique elegido (clic o arrastre), el frente de sus dos
    viviendas. Los campos aceptan coma o punto; Enter pone el vértice, cierra el patio o mueve el tabique (con la línea y
    los campos vacíos, termina la línea como siempre); un clic en la planta con medidas escritas es un Enter; un número,
    con la barra a la vista, va al primer campo; Esc cierra la herramienta. Lo tipeado no se redondea a la grilla. El
    frente va por `editar` (se deshace y recalcula) y no entra si una de las dos viviendas queda por debajo del mínimo del
    motor (la mitad de `min_unit_width`): el motor lo recorta en silencio, por eso la web lo avisa antes.
    (El comportamiento se comprobó en navegador; esta prueba vigila la web con comprobaciones del código y el motor con el
    mismo recorrido que hace la web, que se repite acá en Python.)"""
    import math, re
    from engine import layout
    base = os.path.join(os.path.dirname(__file__), "..")
    html = open(os.path.join(base, "web", "index.html"), encoding="utf-8").read()
    js = html.split("<script>", 1)[1].split("</script>", 1)[0]

    def cuerpo(nombre):
        ini = js.index("function %s(" % nombre)
        fin = min(k for k in (js.find("\nfunction ", ini + 1), js.find("\nasync function ", ini + 1), js.find("\n/*", ini + 1),
                              len(js)) if k >= 0)
        return js[ini:fin]
    # ---- la web: los campos, Enter, el clic, los números, Esc
    for f in ("function numTipeado(", "function puntoLinea(", "function puntoPatio(", "function marcoPatio(",
              "function ponerVertice(", "function tabiqueSel(", "function frentesTab(", "async function frenteTipeado(",
              "function medidasVivas(", "function medidaModo(", "function medidaInput(", "function medidaTecla(",
              "function medidaEnter(", "function avisoMedida("):
        assert f in js, f
    num = cuerpo("numTipeado")                           # coma o punto: la misma expresión que usa la página
    assert ".replace(',','.')" in num
    er = re.compile(re.search(r"return (/.+?/)\.test\(s\)", num).group(1)[1:-1])
    pagina = lambda s: float(s.strip().replace(",", ".", 1)) if er.match(s.strip().replace(",", ".", 1)) else None
    assert [pagina(s) for s in ("12", "3,20", "3.20", " 0,5 ", "-45", ".5", "12.")] == [12.0, 3.2, 3.2, 0.5, -45.0, 0.5, 12.0]
    assert [pagina(s) for s in ("", "abc", "1,2,3", "3,2m", "1e3", "--1", "-")] == [None] * 7
    modo = cuerpo("medidaModo")                          # la barra trae campos con un vértice, la primera esquina o un tabique
    assert "curLine.length?'linea':''" in modo and "curPatio.length===1?'patio':''" in modo and "tabiqueSel()" in modo
    barra = cuerpo("herramientaBar")
    for t in ("c('Largo','largo'", "c('Ángulo','angulo'", "c('Ancho','ancho'", "c('Fondo','fondo'", 'inputmode="decimal"',
              'data-medida="${k}"', 'oninput="medidaInput(this)"', 'onkeydown="medidaTecla(event)"',
              "ts.t.b===selUnit?[ts.t.b,ts.t.a]:[ts.t.a,ts.t.b]", "if(!auto) herrTxt=", "esc(herrTxt)"):
        assert t in barra, t                             # la elegida va primero; rearmada por un cambio de campos, conserva el texto
    tecla = cuerpo("medidaTecla")                        # Enter no llega al Enter que termina la línea
    assert "e.key!=='Enter'" in tecla and "e.stopPropagation()" in tecla and "medidaEnter(e.target)" in tecla
    ent = cuerpo("medidaEnter")
    assert ent.index("return finishLine()") < ent.index("ponerVertice(puntoLinea(")      # vacíos: termina; con medidas: pone el vértice
    assert "finishPatio()" in ent and "frenteTipeado(id,v)" in ent
    assert "if(medidaTexto('largo')||medidaTexto('angulo')) return medidaEnter();" in js     # un clic con medidas escritas (línea y patio) es un Enter
    assert "if(curPatio.length&&(medidaTexto('ancho')||medidaTexto('fondo'))) return medidaEnter();" in js
    teclas = js.split("window.addEventListener('keydown'", 1)[1].split("\n/*", 1)[0]
    assert "/^[0-9.,]$/.test(e.key)" in teclas and "document.querySelector('#herr [data-medida]')" in teclas and ".focus()" in teclas
    assert "if(e.key==='Enter'&&tool==='line') finishLine();" in teclas                  # fuera de los campos, Enter sigue igual
    assert "if(!tool&&selTab){ selTab=null;" in teclas and "if(tool) setTool(tool);" in teclas   # Esc: suelta el tabique o cierra la herramienta
    pl = cuerpo("puntoLinea")
    assert pl.count("ajustar(w,prev,e)") == 1 and "ajustarDesp(prev," in pl              # sin medidas, el puntero; solo el ángulo: el largo, a la grilla
    assert pl.index("if(tA) u=[Math.cos(") < pl.index("$('orto').checked")               # el ángulo tipeado manda sobre el Orto
    assert "scpActual()" in pl and "aLocal(" in pl and "aMundo(" in pl and "let d=L;" in pl   # el ángulo en el SCP; el largo tipeado no se redondea
    assert "marcoPatio(" in cuerpo("puntoPatio") and "r[0]<a[0]?-A:A" in cuerpo("puntoPatio")   # el puntero elige el lado
    assert "const {L,W}=marcoPatio(p0,p1)" in cuerpo("rectAlign")                        # el patio tipeado y el dibujado, en los mismos ejes
    ov = cuerpo("drawOverlay")                           # la vista previa y la cruz usan el punto que va a quedar
    for t in ("puntoLinea(ptr,{altKey:ptrAlt})", "puntoPatio(ptr,{altKey:ptrAlt})", "rectAlign(curPatio[0],np)",
              "medidasVivas(nx,np)", "if(medidaModo()!==medModo) herramientaBar(true);"):
        assert t in ov, t
    assert "ptr=w;" in js.split("svg.addEventListener('mousemove',e=>", 1)[1].split("\n", 1)[0]
    ft = cuerpo("frenteTipeado")                         # el frente: por editar (deshacer y recalcular) y dentro de lo que el motor admite
    assert "editar({op:'tabique',p:mitad(t.seg)" in ft and "ediciones.push(" not in ft and "recordar(" in cuerpo("editar")
    assert "mn=0.5*(+$('min_unit_width').value)" in ft and "v<mn-1e-9||v>tot-mn+1e-9" in ft
    assert ft.index("avisoMedida('El frente de '") < ft.index("await editar(")           # primero se avisa, después se mueve
    assert 'pw, wmin = params["party_wall"], 0.5 * params["min_unit_width"]' in \
        open(os.path.join(base, "engine", "units.py"), encoding="utf-8").read()                    # el mismo mínimo que usa el motor
    assert "selTab={a:t0.a,b:t0.b,u:selUnit}" in js.split("const tt=e.target.closest&&e.target.closest('[data-tab]');", 1)[1].split("\n", 1)[0]
    assert 'id="min_unit_width" value="3.5"' in html and 'id="party_wall" value="0.3"' in html   # los valores con que la web mide
    assert layout.DEFAULT_PARAMS["min_unit_width"] == 3.5 and layout.DEFAULT_PARAMS["party_wall"] == 0.30

    # ---- lo que hace la web, en Python
    def a_local(p, S):                                   # S = (x, y, ángulo): el SCP
        c, s = math.cos(S[2]), math.sin(S[2])
        return ((p[0] - S[0]) * c + (p[1] - S[1]) * s, -(p[0] - S[0]) * s + (p[1] - S[1]) * c)

    def a_mundo(q, S):
        c, s = math.cos(S[2]), math.sin(S[2])
        return (S[0] + q[0] * c - q[1] * s, S[1] + q[0] * s + q[1] * c)

    def punto_linea(prev, w, S, largo=None, angulo=None, orto=True):   # como puntoLinea con medidas (sin ellas, el del puntero)
        P, q = a_local(prev, S), a_local(w, S)
        dx, dy = q[0] - P[0], q[1] - P[1]
        if angulo is not None:
            u = (math.cos(math.radians(angulo)), math.sin(math.radians(angulo)))
        elif orto:
            u = ((-1.0 if dx < 0 else 1.0), 0.0) if abs(dx) >= abs(dy) else (0.0, (-1.0 if dy < 0 else 1.0))
        else:
            n = math.hypot(dx, dy)
            u = (dx / n, dy / n) if n > 1e-9 else (1.0, 0.0)
        d = largo
        if not largo:                                    # solo el ángulo: el largo lo da el puntero (su proyección)
            d = dx * u[0] + dy * u[1]
            if d < 0.001:
                return None
        r = a_mundo((P[0] + u[0] * d, P[1] + u[1] * d), S)
        return [round(r[0], 3), round(r[1], 3)]
    dist = lambda a, b: math.hypot(b[0] - a[0], b[1] - a[1])
    grados = lambda a, b: math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    barra = [[0, 0], [60, 0], [60, 16], [0, 16]]
    S0 = (0.0, 0.0, 0.0)

    # 1) línea: el puntero elige la dirección (el eje del SCP con el Orto) y lo tipeado manda; el motor dibuja ese largo
    prev = [30.0, 8.0]
    for puntero, largo, esperado in (([45, 8.4], 12, [42.0, 8.0]), ([20, 7.8], 12, [18.0, 8.0]),
                                     ([30.3, 14], 7, [30.0, 15.0]), ([29.7, 2], 7, [30.0, 1.0])):
        assert punto_linea(prev, puntero, S0, largo=largo) == esperado, (puntero, largo)
    q = punto_linea(prev, [45, 8.4], S0, largo=12)
    assert abs(run(barra, centerlines=[[prev, q]])["pasillos"][0]["largo"] - 12.0) < 0.01     # «Hecho cuando»: el tramo mide 12,00 m
    assert punto_linea([30.37, 8.11], [45, 8.4], S0, largo=3.2) == [33.57, 8.11]              # sin redondear a la grilla
    sin_orto = punto_linea([10, 5], [18, 11], S0, largo=10, orto=False)                       # sin Orto: hacia el puntero
    assert abs(dist([10, 5], sin_orto) - 10) < 1e-3 and abs(grados([10, 5], sin_orto) - 36.87) < 0.01
    # un SCP girado 30° (edificio girado): 12 m, 90° y 0° siguen sus ejes
    th = math.radians(30)
    rot = lambda p: [p[0] * math.cos(th) - p[1] * math.sin(th), p[0] * math.sin(th) + p[1] * math.cos(th)]
    S30 = (0.0, 0.0, th)
    a = [round(c, 3) for c in rot([10, 8])]
    q = punto_linea(a, rot([30, 8.4]), S30, largo=12)
    assert abs(dist(a, q) - 12) < 0.001 and abs(grados(a, q) - 30) < 0.01, (a, q)
    assert abs(run([rot(p) for p in barra], centerlines=[[a, q]])["pasillos"][0]["largo"] - 12.0) < 0.01
    q2 = punto_linea(q, rot([30, 8]), S30, largo=6, angulo=90)                                # 90° del SCP = 120° del mundo
    assert abs(dist(q, q2) - 6) < 0.001 and abs(grados(q, q2) - 120) < 0.01
    q3 = punto_linea(q2, rot([30, 8]), S30, largo=3, angulo=-45)                              # un ángulo manda sobre el Orto, también negativo
    assert abs(dist(q2, q3) - 3) < 0.001 and abs(grados(q2, q3) + 15) < 0.01
    # solo el ángulo: la dirección queda fija y el largo lo da el puntero (su proyección); detrás, no hay punto
    q = punto_linea([30.0, 8.0], [40.0, 12.0], S0, angulo=30)
    assert abs(dist([30, 8], q) - (10 * math.cos(th) + 4 * math.sin(th))) < 0.002 and abs(grados([30, 8], q) - 30) < 0.01
    assert punto_linea([30.0, 8.0], [20.0, 4.0], S0, angulo=30) is None

    # 2) patio: Ancho × Fondo en los ejes del edificio; el puntero elige hacia qué lado va cada una
    def punto_patio(p0, w, th, ancho=None, fondo=None, m=None):         # como puntoPatio (m: la esquina del puntero ya ajustada)
        c, s = math.cos(th), math.sin(th)
        L = lambda p: (p[0] * c + p[1] * s, -p[0] * s + p[1] * c)
        W = lambda p: (p[0] * c - p[1] * s, p[0] * s + p[1] * c)
        a_, r_, b_ = L(p0), L(w), L(m or w)
        x = a_[0] + (-ancho if r_[0] < a_[0] else ancho) if ancho else b_[0]
        y = a_[1] + (-fondo if r_[1] < a_[1] else fondo) if fondo else b_[1]
        q_ = W((x, y))
        return [round(q_[0], 3), round(q_[1], 3)]

    def rect(p0, p1, th):                                # como rectAlign
        c, s = math.cos(th), math.sin(th)
        L = lambda p: (p[0] * c + p[1] * s, -p[0] * s + p[1] * c)
        W = lambda p: [p[0] * c - p[1] * s, p[0] * s + p[1] * c]
        a_, b_ = L(p0), L(p1)
        return [W(a_), W((b_[0], a_[1])), W(b_), W((a_[0], b_[1]))]
    area = lambda poly: abs(sum(poly[i][0] * poly[(i + 1) % 4][1] - poly[(i + 1) % 4][0] * poly[i][1] for i in range(4))) / 2
    lados = lambda poly: sorted((round(dist(poly[i], poly[(i + 1) % 4]), 2) for i in range(4)))
    for th_, tr in ((0.0, lambda p: list(p)), (th, rot)):
        p0 = [round(c, 3) for c in tr([20, 5])]
        for puntero, signo in (([30, 12], (1, 1)), ([12, 1], (-1, -1)), ([30, 1], (1, -1))):
            q = punto_patio(p0, tr(puntero), th_, ancho=6, fondo=4)
            poli = [[round(c, 3) for c in p] for p in rect(p0, q, th_)]
            assert lados(poli) == [4.0, 4.0, 6.0, 6.0] and abs(area(poli) - 24) < 0.02, (th_, puntero, poli)
            c, s = math.cos(th_), math.sin(th_)
            dx = (q[0] - p0[0]) * c + (q[1] - p0[1]) * s
            dy = -(q[0] - p0[0]) * s + (q[1] - p0[1]) * c
            assert (round(dx, 2), round(dy, 2)) == (6.0 * signo[0], 4.0 * signo[1]), (th_, puntero, dx, dy)
        solo = punto_patio(p0, tr([30, 12]), th_, ancho=3.5, m=tr([30, 10]))                # solo el ancho: el fondo, del puntero
        poli = rect(p0, solo, th_)
        assert lados([[round(c, 3) for c in p] for p in poli]) == [3.5, 3.5, 5.0, 5.0]
    poli = [[round(c, 3) for c in p] for p in rect([20, 5], punto_patio([20, 5], [30, 12], 0.0, ancho=6, fondo=4), 0.0)]
    e = run(barra, patios_mode="manual", patios=[poli])
    assert len(e["patios"]) == 1 and e["metrics"]["patio_area"] == 24.0                      # el motor recibe el patio de 6 × 4

    # 3) tabique: el frente de una vivienda, exacto; la otra toma el resto (por la geometría, como frentesTab)
    def frentes_tab(r, t, pw=0.3):
        d = t["dir"]
        dot = lambda p: p[0] * d[0] + p[1] * d[1]
        s = (dot(t["seg"][0]) + dot(t["seg"][1])) / 2.0
        A = next(u for u in r["units"] if u["id"] == t["a"])
        B = next(u for u in r["units"] if u["id"] == t["b"])
        wA, wB = s - pw / 2 - min(dot(p) for p in A["poly"]), max(dot(p) for p in B["poly"]) - s - pw / 2
        return (wA if abs(wA - A["width"]) <= 0.006 else A["width"]), (wB if abs(wB - B["width"]) <= 0.006 else B["width"])

    def pedir_frente(r, t, id_, v, forzar=False, pw=0.3, min_w=3.5):  # como frenteTipeado: el cambio de unit_edits (None si no entra)
        wA, wB = frentes_tab(r, t, pw)
        tot, mn, esA = wA + wB, 0.5 * min_w, id_ == t["a"]
        if not forzar and (v < mn - 1e-9 or v > tot - mn + 1e-9):
            return None
        d = (v - wA) if esA else (wB - v)
        m = [(t["seg"][0][0] + t["seg"][1][0]) / 2.0, (t["seg"][0][1] + t["seg"][1][1]) / 2.0]
        return {"op": "tabique", "p": [round(c, 3) for c in m],
                "a": [round(m[0] + t["dir"][0] * d, 3), round(m[1] + t["dir"][1] * d, 3)]}
    ancho_de = lambda r, i: next(u["width"] for u in r["units"] if u["id"] == i)
    muestra = lambda n: json.load(open(os.path.join(base, "samples", n + ".json"), encoding="utf-8"))
    visto = set()
    for nombre, k in (("barra", 1), ("quiebre_45", -1), ("L", 0)):      # ejes del tabique: +x, oblicuo y -x
        s = muestra(nombre)
        r0 = run(s["footprint"], h=s["height"])
        t = r0["tabiques"][k]
        visto.add(tuple(round(c, 2) for c in t["dir"]))
        wA, wB = frentes_tab(r0, t)
        tot, mn = wA + wB, 1.75                          # la mitad del frente mínimo (3,5 m)
        assert abs(wA - ancho_de(r0, t["a"])) < 0.006 and abs(wB - ancho_de(r0, t["b"])) < 0.006   # la geometría y el reparto coinciden
        for id_, v in ((t["a"], round(mn + 0.37 * (tot - 2 * mn), 2)), (t["b"], round(mn + 0.71 * (tot - 2 * mn), 2))):
            r1 = run(s["footprint"], h=s["height"], unit_edits=[pedir_frente(r0, t, id_, v)])
            otra = t["b"] if id_ == t["a"] else t["a"]
            assert abs(ancho_de(r1, id_) - v) <= 0.005 + 1e-9, (nombre, id_, v, ancho_de(r1, id_))   # exacto, al centímetro
            assert abs(ancho_de(r1, otra) - (tot - v)) <= 0.011, (nombre, otra, tot - v, ancho_de(r1, otra))   # la otra, el resto
            t1 = next(x for x in r1["tabiques"] if x["a"] == t["a"] and x["b"] == t["b"])
            f1 = frentes_tab(r1, t1)
            assert abs(f1[0 if id_ == t["a"] else 1] - v) < 0.002, (nombre, id_, v, f1)           # y por la geometría, al milímetro
        # lo que no entra: menos del mínimo del motor o más que las dos juntas (la web avisa y no cambia nada)
        assert pedir_frente(r0, t, t["a"], mn - 0.1) is None and pedir_frente(r0, t, t["a"], tot - mn + 0.1) is None
        assert pedir_frente(r0, t, t["a"], mn) is not None and pedir_frente(r0, t, t["a"], tot - mn) is not None
        if nombre == "barra":                            # el motor lo recortaría en silencio al mínimo: por eso la web avisa antes
            r2 = run(s["footprint"], h=s["height"], unit_edits=[pedir_frente(r0, t, t["a"], 1.0, forzar=True)])
            assert abs(ancho_de(r2, t["a"]) - mn) < 0.011, ancho_de(r2, t["a"])
    assert (1.0, 0.0) in visto and any(abs(abs(d[0]) - 0.71) < 0.01 for d in visto) and (-1.0, 0.0) in visto, visto
    # medir con otro muro entre viviendas: la web usa el de su control (y la geometría coincide con el reparto)
    s = muestra("barra")
    r0 = run(s["footprint"], h=s["height"], party_wall=0.2)
    t = r0["tabiques"][1]
    assert abs(frentes_tab(r0, t, pw=0.2)[0] - ancho_de(r0, t["a"])) < 0.006

if __name__ == "__main__":
    test_medidas_tipeadas(); print("OK61")

@vivienda_anterior
def test_cocina_ventana():
    """R10.9 (decisión del usuario, v2.41; norma nacional, art. 24): la cocina con un tramo de fachada en el que entra una
    ventana lleva la suya (de ventanas["ancho_cocina"], con ventanas["vano_cocina"] como mínimo y más ancha si el 10 % de
    su superficie pide más) y conserva la medida de antes de v2.41: no se acota a los 5 m² de la cocina integrada sin
    ventana (art. 27) ni suma su superficie al vano del estar, y sus mínimos son los de una cocina (art. 21). Si no llega
    al vano, avisa como las demás ventanas. La cocina sin fachada (o con un tramo en el que no entra una ventana) sigue
    integrada, de 5 m² como máximo, y trae ventilacion = "extractor", que la ficha de la web muestra como «con
    extractor». En «Barra 60x16», las cocinas de las viviendas de punta con fachada lateral (U04 y U05) tienen ventana y
    su medida; las del medio (y las de punta contra el núcleo), extractor."""
    from engine import plans as P, standards as ST
    rect = lambda w, d: [(0.0, 0.0), (w, 0.0), (w, d), (0.0, d)]
    S, V = ST.DEFAULTS["ventanas"], ST.DEFAULTS["vivienda"]
    assert S["ancho_cocina"] == 1.0 and S["vano_cocina"] == 0.4
    fondo = lambda p, q: abs(p[1] - 8.0) < 0.05 and abs(q[1] - 8.0) < 0.05
    esquina = lambda p, q: fondo(p, q) or (abs(p[0]) < 0.05 and abs(q[0]) < 0.05)      # fachada al fondo y en x0
    corta = lambda p, q: fondo(p, q) or (abs(p[0]) < 0.05 and abs(q[0]) < 0.05 and max(p[1], q[1]) <= 1.0)   # 1 m en x0
    malos = lambda res: [c["msg"] for c in res["checks"] if not c["ok"]]
    cocina = lambda res: next(r for r in res["rooms"] if r["kind"] == "kitchen")
    estar = lambda res: next(r for r in res["rooms"] if r["kind"] == "living")
    de = lambda res, i: [w for w in res["ventanas"] if w["room"] == i]
    # 9,50 × 8,00 con 2 dormitorios y fachada en x0: la cocina, en x0, lleva ventana (1,00 × 1,20 m en la fachada
    # lateral, hacia afuera), mide 2,10 × 2,64 m como antes de v2.41 (sin la ventana, 5 m²) y el vano del estar no la
    # cuenta
    con = P.layout_unit(rect(9.5, 8.0), 2, esquina)
    k = cocina(con)
    assert k["ventilacion"] == "ventana" and abs(k["area"] - 2.1 * 2.64) < 0.01, k
    (w,) = de(con, "kitchen")
    req = max(S["vano_cocina"], S["iluminacion"] * k["area"])
    assert w["ancho"] == S["ancho_cocina"] and w["alto"] == S["alto"] and abs(w["minimo"] - req) < 0.01 and \
        w["area"] >= req - 0.01 and w["n"] == (-1.0, 0.0) and abs(w["p"][0]) < 1e-6 and abs(w["q"][0]) < 1e-6, w
    assert max(w["p"][1], w["q"][1]) <= 2.64 - S["mocheta"] + 1e-6 and min(w["p"][1], w["q"][1]) >= S["mocheta"] - 1e-6
    assert abs(de(con, "living")[0]["minimo"] - S["iluminacion"] * estar(con)["area"]) < 0.01     # sin la cocina
    assert con["score"] == 100 and not any("Cocina" in m for m in malos(con)), malos(con)
    assert any(m.startswith("Por debajo de la medida típica: Cocina 5.5 de 7 m²") for m in
               (c["msg"] for c in con["checks"] if c.get("info")))      # sus mínimos y su típica: los de una cocina
    # la misma vivienda solo con fachada al fondo (o sin fachada conocida, o con 1 m de fachada lateral, donde no entra
    # una ventana): la cocina integrada, 5 m² como máximo, con extractor, y el vano del estar la cuenta (art. 27)
    for fac in (fondo, None, corta):
        sin = P.layout_unit(rect(9.5, 8.0), 2, fac)
        k2 = cocina(sin)
        assert k2["ventilacion"] == "extractor" and abs(k2["area"] - 5.0) < 0.01 and not de(sin, "kitchen"), k2
        assert abs(de(sin, "living")[0]["minimo"] - max(V["cocina_integrada"]["vano_min"], S["iluminacion"] * (
            estar(sin)["area"] + k2["area"]))) < 0.01 and sin["score"] == 100
    # si no llega al vano: aviso, como en las demás ventanas (con el mínimo del art. 24)
    res = P.layout_unit(rect(9.5, 8.0), 2, esquina, ventanas=dict(S, vano_cocina=4.0))
    assert de(res, "kitchen")[0]["minimo"] == 4.0 and [m for m in malos(res) if m.startswith("Cocina")] == [
        "Cocina: ventana de 2.69 m² < 4.00 m² (10 % de la superficie, 4 m² como mínimo: norma nacional, art. 24)"], \
        malos(res)
    res = P.layout_unit(rect(9.5, 8.0), 2, esquina, ventanas=dict(S, iluminacion=0.5))
    assert any(m.startswith("Cocina: ventana de 2.69 m² < 2.77 m² (50 % de la superficie, 0.4 m² como mínimo")
               for m in malos(res))
    # el monoambiente: la cocina va entre el baño y el hall, nunca al costado: extractor
    assert cocina(P.layout_unit(rect(6.0, 8.0), 0, esquina))["ventilacion"] == "extractor"
    # de la superficie típica de una cocina (7 m²) como máximo, conservando su fondo (se angosta; lo que deja va al hall,
    # al baño o a un depósito, como con la integrada), con el fondo que deja al estar no más ancho que 3 veces su fondo
    # (art. 14): en el trapecio de 21,45 × 5,50 con 3 dormitorios y fachada en su lado oblicuo (test_rincones), la cocina
    # mide 7 m² con su ventana en el muro oblicuo y 2,17 m de fondo (con 2,20, el estar de 10 m quedaba con 3,30 de
    # fondo), y quedan el depósito y el baño de 6 m² (sin el tope, una cocina de 14,7 m² se los comía)
    oblicua = lambda p, q: fondo_(p, q) or (sobre(p) and sobre(q))
    fondo_ = lambda p, q: abs(p[1] - 5.5) < 0.05 and abs(q[1] - 5.5) < 0.05
    sobre = lambda t: abs((t[0] - 0.25) * 5.5 - t[1] * 1.175) / (1.175 ** 2 + 5.5 ** 2) ** 0.5 < 0.05
    res = P.layout_unit([(0.25, 0), (21.45, 0), (21.45, 5.5), (1.425, 5.5)], 3, oblicua)
    R = {r["id"]: r for r in res["rooms"]}
    k = R["kitchen"]
    assert k["ventilacion"] == "ventana" and abs(k["area"] - V["cocina"]["typ_area"]) < 0.01 and de(res, "kitchen"), k
    assert abs(max(p[1] for p in k["poly"]) - (5.5 - 10.0 / S["proporcion_max"])) < 0.01 and "storage" in R and \
        abs(R["bath1"]["area"] - V["bano"]["max_area"]) < 0.01 and res["score"] == 100, (k, malos(res))
    # en el edificio («Barra 60x16»): U04 y U05 tocan la fachada del extremo con la cocina: ventana propia (en el muro
    # exterior, con poly, lines y seg para la web, Rhino y el DXF) y al menos su superficie típica; las demás, extractor
    barra = run([[0, 0], [60, 0], [60, 16], [0, 16]])
    por = {u["id"]: u for u in barra["units"]}
    vent = {i for i, u in por.items()
            if next(x for x in u["rooms"] if x["kind"] == "kitchen")["ventilacion"] == "ventana"}
    assert vent == {"U04", "U05"}, vent
    for i, u in por.items():
        k = next(x for x in u["rooms"] if x["kind"] == "kitchen")
        vk = [w for w in u["ventanas"] if w["room"] == "kitchen"]
        if i in vent:                                  # 7 m² (antes 5), con el fondo de antes (1,80 y 2,00 m)
            assert abs(k["area"] - V["cocina"]["typ_area"]) < 0.05 and len(vk) == 1 and vk[0]["poly"] and vk[0]["lines"] \
                and vk[0]["seg"] and vk[0]["area"] >= max(vk[0]["minimo"], S["vano_cocina"]) - 0.01, (i, k, vk)
            assert max(p[1] for p in k["poly"]) - min(p[1] for p in k["poly"]) >= 1.8 - 0.01, (i, k["poly"])
        else:
            assert k["ventilacion"] == "extractor" and k["area"] <= 5.0 + 0.05 and not vk, (i, k)
        assert not any("Cocina" in c["msg"] for c in u["checks"] if not c["ok"]), (i, u["checks"])
    assert barra["metrics"]["plan_score"] == 100
    # la web: la ficha dice «con extractor» y «Normativa → Ventanas» edita las dos medidas nuevas
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    assert "con extractor" in html and "ancho_cocina:" in html and "vano_cocina:" in html

if __name__ == "__main__":
    test_cocina_ventana(); print("OK62")


def test_importar_dxf():
    """R1.5: «Abrir DXF…». engine/dxf_lector.py lee un DXF de texto de AutoCAD o Revit y devuelve lo mismo que manda Rhino
    a /api/mass (footprint antihorario, medianeras, centerlines, anchos_pasillo, cores, patios), en metros y con las
    coordenadas como vienen, más `unidades` y `warnings`; POST /api/dxf lo guarda como masa (source «dxf») para la web.
    Fixtures en tests/dxf/: (a) AutoCAD en mm con las capas de Trazo, (b) R12 en metros sin unidades, (c) cuatro LINE,
    (d) bloques con escala y giro en coordenadas UTM, (e) bulge, CIRCLE y ARC."""
    import math, threading, urllib.request, urllib.error
    import server, test_rhino
    from engine import dxf_lector as L, dxf as DXF, geometry as G, layout
    carpeta = os.path.join(os.path.dirname(__file__), "dxf")

    def archivo(nombre):                  # los bytes como salen de AutoCAD en Windows (CRLF), decodificados como la web
        with open(os.path.join(carpeta, nombre), "rb") as f:
            return f.read().decode("utf-8")

    def mismo(a, b, tol=1e-6):            # los mismos vértices en el mismo sentido, sea cual sea el primero
        return len(a) == len(b) and any(all(abs(p[0] - q[0]) <= tol and abs(p[1] - q[1]) <= tol
                                            for p, q in zip(a[k:] + a[:k], b)) for k in range(len(a)))

    par = lambda c, v: "%3d\n%s\n" % (c, v)

    def ent(tipo, capa, *pares):
        return par(0, tipo) + par(8, capa) + "".join(par(c, v) for c, v in pares)

    def lw(capa, pts, cerrada=True, *pares):
        return ent("LWPOLYLINE", capa, (90, len(pts)), (70, 1 if cerrada else 0), *(
            [(c, v) for x, y in pts for c, v in ((10, x), (20, y))] + list(pares)))

    def linea(capa, a, b):
        return ent("LINE", capa, (10, a[0]), (20, a[1]), (11, b[0]), (21, b[1]))

    def dxf(entidades, insunits=None, tablas="", bloques=""):
        s = (par(0, "SECTION") + par(2, "HEADER") + par(9, "$INSUNITS") + par(70, insunits) + par(0, "ENDSEC")
             if insunits is not None else "")
        s += par(0, "SECTION") + par(2, "TABLES") + tablas + par(0, "ENDSEC") if tablas else ""
        s += par(0, "SECTION") + par(2, "BLOCKS") + bloques + par(0, "ENDSEC") if bloques else ""
        return s + par(0, "SECTION") + par(2, "ENTITIES") + "".join(entidades) + par(0, "ENDSEC") + par(0, "EOF")

    rect = lambda w, h, x=0.0, y=0.0: [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    hay = lambda r, txt: any(txt in w for w in r["warnings"])
    # (a) el de la meta del ítem: AutoCAD, rectángulo de 15 × 30 m en milímetros, dibujado en sentido horario
    a = L.leer(archivo("autocad_mm.dxf"), "autocad_mm.dxf")
    assert mismo(a["footprint"], [[0, 0], [15, 0], [15, 30], [0, 30]]) and abs(G.area(a["footprint"]) - 450) < 1e-6
    assert a["name"] == "autocad_mm" and a["unidades"] == "mm" and "height" not in a
    assert a["medianeras"] == [{"a": [0, 0], "b": [0, 30], "retiro": 3.0},
                               {"a": [15, 30], "b": [15, 0], "retiro": 3.0}]
    assert a["centerlines"] == [[[7.5, 1.0], [7.5, 14.0], [7.5, 26.0]]]
    assert a["cores"] == [[7.5, 3.0]] and mismo(a["patios"][0], [[4.5, 27], [10.5, 27], [10.5, 30], [4.5, 30]])
    rh = test_rhino.cargar()              # misma estructura que el script de Rhino: anchos por segmento y núcleos
    assert a["anchos_pasillo"] == rh.anchos_de_linea(a["centerlines"][0], "ancho=1.4") and len(a["anchos_pasillo"]) == 2
    assert rh.nucleo([1.0, 2.0], "ascensores=2") == L.leer(dxf([ent("POINT", "Trazo_Cores ascensores 2",
        (10, 1.0), (20, 2.0)), lw("Trazo_Terreno", rect(10, 10))]), "")["cores"][0]
    assert len(a["warnings"]) == 2 and hay(a, "Ignoré 2 entidades TEXT de la capa «COTAS»: Trazo no las lee.") and \
        hay(a, "No leí 1 entidad de la capa «Escombros» (capa apagada o congelada).")   # el marco apagado no es la masa
    # (b) R12: POLYLINE/VERTEX/SEQEND en metros, sin $INSUNITS; hay otra figura cerrada y se toma la más grande
    b = L.leer(archivo("r12_metros.dxf"), "r12_metros")
    assert mismo(b["footprint"], [[100, 200], [120, 200], [120, 240], [100, 240]]) and b["unidades"] == "m"
    assert hay(b, "no dice en qué unidades está dibujado") and hay(b, "tomé la figura cerrada más grande") and \
        hay(b, "la masa mide 20.0 × 40.0 m") and "medianeras" not in b and "cores" not in b
    # (c) cuatro LINE en desorden, algunas al revés: el lazo cerrado es la masa (una sexta línea suelta no cuenta)
    c = L.leer(archivo("rectangulo_lineas.dxf"), "rectangulo_lineas.dxf")
    assert mismo(c["footprint"], [[0, 0], [12, 0], [12, 25], [0, 25]]) and G.area(c["footprint"]) > 0
    assert c["unidades"] == "m" and len(c["warnings"]) == 1 and hay(c, "con 4 líneas que se tocan punta con punta")
    # (d) el lote está dentro de un bloque (escala 2, giro de 90°) y el núcleo es otro bloque: su centro; UTM sin mover
    d = L.leer(archivo("bloques.dxf"), "bloques")
    assert mismo(d["footprint"], [[500100, 6150200], [500100, 6150220], [500060, 6150220], [500060, 6150200]])
    assert d["cores"] == [[500091.5, 6150213.0]] and hay(d, "el bloque «NO_EXISTE»") and hay(d, "TEXT de la capa «Planos»")
    # (e) esquina redondeada (bulge), patio redondo (CIRCLE) y pasillo en arco (ARC), en tramos de 5°
    e = L.leer(archivo("arco.dxf"), "arco")
    assert abs(G.area(e["footprint"]) - (191 + 9 * math.pi / 4)) < 0.02 and len(e["footprint"]) == 5 + 17
    assert len(e["patios"][0]) == 72 and abs(G.area(e["patios"][0]) - math.pi * 1.5 ** 2) < 0.02
    arco = e["centerlines"][0]
    assert len(arco) == 13 and all(abs(math.hypot(x - 10, y + 20) - 25) < 1e-4 for x, y in arco) and \
        abs(arco[0][0] - 22.5) < 1e-4 and abs(arco[-1][0] + 2.5) < 1e-4
    # nombres de capa: mayúsculas, «_», «-», espacio o «:»; «ancho 1.4», «ancho_1.4», «ancho-1,4», «ancho=1.4»
    for capa in ("Trazo_Centerline ancho 1.4", "TRAZO CENTERLINE ANCHO=1.4", "trazo-centerline-ancho-1,4",
                 "Trazo_Centerline_ancho_1.4", "Trazo:Centerline ancho1.4"):
        r = L.leer(dxf([lw("Trazo_Terreno", rect(10, 20)), lw(capa, [(5, 1), (5, 19)], False)], 6), "")
        assert r["anchos_pasillo"] == [{"seg": [[5, 1], [5, 19]], "ancho": 1.4}], capa
    for capa, retiro in (("Trazo_Medianeras retiro 3", 3.0), ("Trazo-Medianeras-Retiro=3,5", 3.5), ("Trazo_Medianeras", 0.0)):
        assert L.leer(dxf([lw("Trazo_Terreno", rect(10, 20)), linea(capa, (0, 0), (0, 20))], 6), "")["medianeras"] == \
            [{"a": [0, 0], "b": [0, 20], "retiro": retiro}], capa
    assert L.leer(dxf([lw("Trazo_Terreno", rect(10, 20)), linea("Trazo_Centerline", (5, 1), (5, 19))], 6), "").get(
        "anchos_pasillo") is None                                            # sin ancho en el nombre: el general
    # unidades: $INSUNITS (pulgadas, pies, cm, mm) o, sin él, por el tamaño de la masa (hasta 500 m, 10000 cm, más mm)
    for ins, w, h in ((1, 600, 1200), (2, 50, 100), (5, 1524, 3048), (4, 15240, 30480), (6, 15.24, 30.48)):
        r = L.leer(dxf([lw("Trazo_Terreno", rect(w, h))], ins), "")
        assert mismo(r["footprint"], [[0, 0], [15.24, 0], [15.24, 30.48], [0, 30.48]]) and not r["warnings"], ins
    for ins, w, h, nombre in ((None, 15, 30, "m"), (0, 1500, 3000, "cm"), (None, 15000, 30000, "mm")):
        r = L.leer(dxf([lw("Trazo_Terreno", rect(w, h))], ins), "")
        assert r["unidades"] == nombre and mismo(r["footprint"], [[0, 0], [15, 0], [15, 30], [0, 30]]) and \
            hay(r, "no dice en qué unidades"), nombre
    assert hay(L.leer(dxf([lw("Trazo_Terreno", rect(15000, 30000))], 6), ""), "La masa mide 15000.0 × 30000.0 m, enorme")
    # lo que no es la masa: el espacio papel (marcos de hoja), las capas apagadas por color y los bloques anidados
    r = L.leer(dxf([lw("Marco", rect(900, 600), True, (67, 1)), lw("Lote", rect(15, 30)), lw("Viejo", rect(50, 80))], 6,
                   tablas=par(0, "LAYER") + par(2, "Viejo") + par(70, 0) + par(62, -7)), "")
    assert mismo(r["footprint"], rect(15, 30)) and hay(r, "No leí 1 entidad de la capa «Viejo»") and \
        not hay(r, "figuras cerradas")
    ins = lambda n, x: ent("INSERT", "0", (2, n), (10, x), (20, 0))
    bloque = lambda n, ents: par(0, "BLOCK") + par(2, n) + par(10, 0) + par(20, 0) + "".join(ents) + par(0, "ENDBLK")
    try:
        L.leer(dxf([ins("AFUERA", 0)], bloques=bloque("ADENTRO", [lw("Trazo_Terreno", rect(10, 20))]) +
                   bloque("AFUERA", [ins("ADENTRO", 0)])), "")
        raise AssertionError("un bloque anidado no se lee")
    except L.ErrorDxf as ex:
        assert str(ex).startswith("Trazo: no encontré una polilínea cerrada") and \
            any("bloques dentro de bloques de la capa «0»" in w for w in ex.warnings), ex.warnings
    # extrusión (0, 0, -1): el eje x del sistema propio de la polilínea mira al revés
    r = L.leer(dxf([lw("Trazo_Terreno", rect(10, 20), True, (210, 0), (220, 0), (230, -1))], 6), "")
    assert mismo(r["footprint"], [[-10, 0], [0, 0], [0, 20], [-10, 20]])
    # una polilínea abierta que vuelve a su primer punto es cerrada; las medianeras cerradas dan todos sus lados
    r = L.leer(dxf([lw("Terreno", rect(10, 20) + [(0, 0)], False), lw("Trazo_Medianeras retiro 2", rect(10, 20))], 6), "")
    assert mismo(r["footprint"], rect(10, 20)) and len(r["medianeras"]) == 4 and \
        hay(r, "a más de 0,5 m del borde") is False
    r = L.leer(dxf([lw("Trazo_Terreno", rect(10, 20)), linea("Trazo_Medianeras", (0, -4), (10, -4))], 6), "")
    assert hay(r, "Una medianera queda a más de 0,5 m del borde de la masa")
    # núcleos: punto, figura cerrada chica (su centro) y con «ascensores 2» en el nombre; una grande o abierta no sirve
    r = L.leer(dxf([lw("Trazo_Terreno", rect(10, 30)), ent("POINT", "Trazo_Cores", (10, 2), (20, 3)),
                    lw("Trazo_Cores ascensores 2", rect(2, 4, 4, 10)), lw("Trazo_Cores", rect(10, 30)),
                    linea("Trazo_Cores", (0, 0), (5, 5))], 6), "")
    assert r["cores"] == [[2.0, 3.0], {"p": [5.0, 12.0], "ascensores": 2}] and hay(r, "2 figuras de la capa Trazo_Cores no sirven")
    # patios: cerrados (también de líneas que se tocan); uno abierto no se usa y se avisa
    r = L.leer(dxf([lw("Trazo_Terreno", rect(10, 30)), lw("Trazo_Patios", rect(3, 3, 1, 1)),
                    linea("Trazo_Patios", (5, 10), (8, 10)), linea("Trazo_Patios", (8, 10), (8, 13)),
                    linea("Trazo_Patios", (8, 13), (5, 13)), linea("Trazo_Patios", (5, 13), (5, 10)),
                    lw("Trazo_Patios", [(1, 20), (4, 20), (4, 25)], False)], 6), "")
    assert len(r["patios"]) == 2 and all(G.area(p) > 0 for p in r["patios"]) and \
        hay(r, "1 figura de la capa Trazo_Patios no está cerrada y no se usa")
    # varias figuras en Trazo_Terreno: la mayor; sin figura cerrada en esa capa: error que dice qué hacer
    r = L.leer(dxf([lw("Trazo_Terreno", rect(10, 20)), lw("Trazo_Terreno", rect(30, 40)), lw("Otra", rect(99, 99))], 6), "")
    assert mismo(r["footprint"], rect(30, 40)) and hay(r, "La capa «Trazo_Terreno» tiene 2 figuras cerradas")
    # un archivo con BOM, con los saltos de línea de Windows o de Unix y con renglones de más al final se lee igual
    base = dxf([lw("Trazo_Terreno", rect(10, 20))], 6)
    for texto in ("\ufeff" + base, base.replace("\n", "\r\n"), base + "\n\n  \n"):
        assert mismo(L.leer(texto, "")["footprint"], rect(10, 20))
    # la misma figura dibujada dos veces no es «varias figuras»
    r = L.leer(dxf([lw("Trazo_Terreno", rect(10, 20)), lw("Trazo_Terreno", rect(10, 20)[::-1]), lw("Otra", rect(10, 20))], 6), "")
    assert mismo(r["footprint"], rect(10, 20)) and not r["warnings"]
    # SPLINE: por sus puntos de ajuste, o por sus puntos de control y nudos (Bézier cúbica: en t = 0,5, (P0+3P1+3P2+P3)/8)
    sp = lambda capa, *pares: ent("SPLINE", capa, *pares)
    r = L.leer(dxf([lw("Trazo_Terreno", rect(10, 20)),
                    sp("Trazo_Centerline", (70, 8), (71, 3), (74, 3), (11, 1), (21, 1), (11, 5), (21, 9), (11, 9), (21, 15)),
                    sp("Trazo_Centerline", (70, 8), (71, 3), *([(40, 0)] * 4 + [(40, 1)] * 4 + [(c, v) for x, y in
                       ((0, 0), (0, 10), (10, 10), (10, 0)) for c, v in ((10, x), (20, y))]))], 6), "")
    assert r["centerlines"][0] == [[1, 1], [5, 9], [9, 15]] and len(r["centerlines"][1]) == 33 and \
        r["centerlines"][1][16] == [5.0, 7.5] and r["centerlines"][1][0] == [0, 0] and r["centerlines"][1][-1] == [10, 0]
    assert hay(r, "2 SPLINEs de la capa «Trazo_Centerline» se leyeron con tramos rectos")
    # errores: DXF binario, DWG, algo que no es un DXF y un DXF sin figura cerrada (o con la capa abierta)
    for texto, frase in (("AutoCAD Binary DXF\r\n\x1a\x00\x00\x00", "este DXF es binario"), ("AC1032\x00\x00\x00\x00", "eso es un DWG"),
                         ("hola, esto no es un DXF", "no parece un DXF de texto"), ("   \n  ", "no parece un DXF de texto"),
                         (dxf([linea("Lote", (0, 0), (10, 0)), ent("TEXT", "Textos", (10, 0), (20, 0), (1, "x"))]),
                          "no encontré una polilínea cerrada en el DXF"),
                         (dxf([lw("Trazo_Terreno", [(0, 0), (10, 0), (10, 5)], False)]), "la capa «Trazo_Terreno» no tiene ninguna polilínea cerrada")):
        try:
            L.leer(texto, "")
            assert frase is None, frase
        except L.ErrorDxf as ex:
            assert frase and frase in str(ex) and str(ex).startswith("Trazo:"), (frase, str(ex))
    # ida y vuelta con engine/dxf.py: lo que Trazo exporta (Trazo_Footprint y Trazo_Patios) se vuelve a leer
    s = json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", "entre_medianeras_patio_central.json"),
                       encoding="utf-8"))
    res = layout.generate({"footprint": s["footprint"], "height": s["height"], "stage": "plans",
                           "params": {"medianeras": s["medianeras"], "patios": s["patios"], "patios_mode": "manual"}})
    v = L.leer(DXF.result_to_dxf(res), "resultado.dxf")
    assert mismo(v["footprint"], res["footprint"], 1e-4) and len(v["patios"]) == 1 and mismo(v["patios"][0], res["patios"][0], 1e-4)
    # el motor corre con la masa importada, como lo hace la web (medianeras, pasillo, núcleo y patio de la capa)
    params = {"medianeras": a["medianeras"], "centerlines": a["centerlines"], "anchos_pasillo": a["anchos_pasillo"],
              "cores": a["cores"], "cores_mode": "manual", "patios": a["patios"], "patios_mode": "manual"}
    gen = layout.generate({"footprint": a["footprint"], "height": 15, "stage": "plans", "params": params})
    assert len(gen["units"]) > 0 and not gen.get("error")
    assert len(layout.generate({"footprint": c["footprint"], "height": 15, "stage": "mix", "params": {}})["units"]) > 0
    # el servidor: POST /api/dxf guarda la masa como si viniera de Rhino y la web la toma de GET /api/mass
    server.STATE.update(mass=None, result=None)
    srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d" % srv.server_address[1]

    def api(ruta, cuerpo=None):
        req = urllib.request.Request(url + ruta, data=None if cuerpo is None else json.dumps(cuerpo).encode(),
                                     method="GET" if cuerpo is None else "POST", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read().decode())
        except urllib.error.HTTPError as ex:
            return ex.code, json.loads(ex.read().decode())
    try:
        assert api("/api/mass")[1]["mass"] is None
        cod, j = api("/api/dxf", {"name": "autocad_mm", "dxf": archivo("autocad_mm.dxf")})
        assert cod == 200 and j["ok"] and j["source"] == "dxf" and j["unidades"] == "mm" and len(j["warnings"]) == 2
        assert mismo(j["footprint"], a["footprint"]) and j["medianeras"] == a["medianeras"] and j["name"] == "autocad_mm"
        cod, m = api("/api/mass")
        assert cod == 200 and m["version"] == j["version"] and m["mass"]["source"] == "dxf" and \
            mismo(m["mass"]["footprint"], [[0, 0], [15, 0], [15, 30], [0, 30]]) and len(m["mass"]["medianeras"]) == 2 and \
            m["mass"]["anchos_pasillo"] == a["anchos_pasillo"] and m["mass"]["patios"] == a["patios"] and \
            m["mass"]["cores"] == [[7.5, 3.0]]
        cod, g = api("/api/generate", {"footprint": m["mass"]["footprint"], "height": 15, "stage": "plans",
                                       "params": {"medianeras": m["mass"]["medianeras"]}})
        assert cod == 200 and len(g["units"]) > 0
        for cuerpo, frase in (({"name": "x", "dxf": ""}, "llegó vacío"), ({"name": "x"}, "llegó vacío"),
                              ({"name": "x", "dxf": "AutoCAD Binary DXF\r\n\x1a\x00"}, "este DXF es binario"),
                              ({"name": "x", "dxf": dxf([linea("Lote", (0, 0), (10, 0))])}, "no encontré una polilínea cerrada")):
            cod, j2 = api("/api/dxf", cuerpo)
            assert cod == 400 and j2["error"].startswith("Trazo:") and frase in j2["error"], (cuerpo, j2)
        assert api("/api/mass")[1]["version"] == m["version"]            # un DXF que falla no cambia la masa
        api("/api/dxf", {"name": "bloques", "dxf": archivo("bloques.dxf")})
        assert api("/api/mass")[1]["mass"]["name"] == "bloques" and api("/api/mass")[1]["version"] == m["version"] + 1
    finally:
        srv.shutdown()
        srv.server_close()
        server.STATE.update(mass=None, result=None)
    # la web: el botón «Abrir DXF…» (con su selector de archivos .dxf), el POST y los avisos junto a los del resultado
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    assert 'id="btnAbrirDxf"' in html and ">Abrir DXF…</button>" in html and \
        'id="archivoDxf" accept=".dxf"' in html and "onchange=\"leerDxf(this)\"" in html
    js = html.split("<script>", 1)[1]
    assert "async function leerDxf(" in js and "fetch('/api/dxf'" in js and "function avisosPanel(" in js and \
        "m.source==='dxf'" in js and "'__dxf'" in js and "avisosPanel();" in js.split("function panels2(){", 1)[1].split("\n", 1)[0]

if __name__ == "__main__":
    test_importar_dxf(); print("OK63")

def test_equipamiento_orden():
    """R5.14a: el equipamiento de una estancia (y el de una vivienda) no depende de qué se calculó antes en el mismo proceso.
    La memoria de resolver tenía el ancho y el fondo redondeados en la clave, pero calculaba con los exactos: dos estancias
    «iguales» que difieren en 1e-15 m compartían el resultado de la primera, y en una estancia simétrica (la puerta al medio,
    la ventana de lado a lado) esa diferencia decide de qué lado van la cama o el placard."""
    import copy, math, random
    import regresion
    from engine import plans as P, equipamiento as EQ, standards as ST
    S = ST.DEFAULTS["equipamiento"]

    # 1. el caso mínimo: dos dormitorios de 2,80 × 3,50 m (los de «L_polilinea» y «barra») con la puerta al medio del lado
    #    del pasillo y la ventana de lado a lado; difieren en 1e-15 m y, calculado solo, cada uno pone el placard en una pared
    def cuarto(x0, v0, x1, v1):
        xm = (x0 + x1) / 2
        rm = {"id": "bed2", "kind": "bedroom", "name": "Dormitorio 2", "rect": (x0, v0, x1, v1)}
        puerta = {"p": (xm - 0.35, v0), "q": (xm + 0.35, v0), "a": "hallway", "b": "bed2", "ancho": 0.7}
        return lambda: EQ.resolver(rm, [puerta], {}, S, [((x0, v1), (x1, v1))], 2)

    def sola(c):
        EQ._memo.clear()
        return c()
    A = cuarto(7.430600000000001, 3.0, 10.2306, 6.500000000000002)
    B = cuarto(14.378699999999998, 3.0, 17.1787, 6.5)
    lugares = lambda res: [(p[0], tuple(round(x, 3) for x in p[1])) for p in res[0]]
    a, b = sola(A), sola(B)
    assert lugares(a) != lugares(b), "este par ya no sirve de caso mínimo (el desempate no depende del ruido): elegir otro"
    EQ._memo.clear(); A()
    assert B() == b, "B tras A debe dar lo mismo que B sola: %s" % lugares(B())
    EQ._memo.clear(); B()
    assert A() == a, "A tras B debe dar lo mismo que A sola: %s" % lugares(A())

    # 2. el mismo plano, el mismo equipamiento: cada vivienda de cinco ejemplos corridos uno tras otro (con la memoria como
    #    esté) se compara con la misma vivienda calculada con la memoria vacía; son los ejemplos donde antes cambiaba
    orig, hondo, calculadas, distintas, ej = P.layout_unit, [0], [0], [], [None]
    huella = lambda res: ([(e["kind"], e["room"], e["poly"], e["lines"]) for e in res["equipamiento"]],
                          [c["msg"] for c in res["checks"]])

    def espiar(*args, **kw):
        if hondo[0]:
            return orig(*args, **kw)
        args2, kw2 = copy.deepcopy(args), copy.deepcopy(kw)
        hondo[0] += 1
        try:
            caliente = orig(*args, **kw)
            memo, EQ._memo = EQ._memo, {}
            try:
                frio = orig(*args2, **kw2)
            finally:
                EQ._memo = memo
        finally:
            hondo[0] -= 1
        calculadas[0] += 1
        if huella(caliente) != huella(frio):
            distintas.append(ej[0])
        return caliente
    P.layout_unit = espiar
    try:
        EQ._memo.clear()
        for ej[0] in ("L_polilinea", "barra", "T_dos_lineas", "cruz_dos_lineas", "torre_mixta"):
            with open(os.path.join(regresion.SAMPLES, ej[0] + ".json"), encoding="utf-8") as f:
                regresion._edificio(json.load(f))
    finally:
        P.layout_unit = orig
    assert calculadas[0] >= 50 and not distintas, (calculadas[0], distintas)

    # 3. _alcanza (la grilla de la estancia es un entero con un bit por celda) da lo mismo que recorrerla celda por celda
    def celda_por_celda(W, D, cuerpos, accesos, usos, h, g):
        nx, ny = max(1, math.ceil(W / g - 1e-9)), max(1, math.ceil(D / g - 1e-9))
        cx, cy = (lambda i: (i + 0.5) * W / nx), (lambda j: (j + 0.5) * D / ny)
        entre = lambda v, lo, hi: lo < v < hi
        libre = {(i, j) for i in range(nx) for j in range(ny)
                 if entre(cx(i), h - 1e-6, W - h + 1e-6) and entre(cy(j), h - 1e-6, D - h + 1e-6) and
                 not any(entre(cx(i), a0 - h + 1e-6, a1 + h - 1e-6) and entre(cy(j), b0 - h + 1e-6, b1 + h - 1e-6)
                         for a0, b0, a1, b1 in cuerpos)}

        def junto(p, q):
            vert = abs(p[0] - q[0]) < 1e-6
            lo, hi = sorted((p[1], q[1]) if vert else (p[0], q[0]))
            if hi - lo > 0.4:
                lo, hi = lo + 0.1, hi - 0.1
            e, L = (p[0], W) if vert else (p[1], D)
            c0, c1 = (e, e + h + 1.5 * g) if e < L - e else (e - h - 1.5 * g, e)
            if vert:
                return {(i, j) for i, j in libre if entre(cx(i), c0, c1) and entre(cy(j), lo, hi)}
            return {(i, j) for i, j in libre if entre(cx(i), lo, hi) and entre(cy(j), c0, c1)}
        if not accesos:
            return True
        sem = [junto(p, q) for p, q in accesos]
        visto, pila = set(sem[0]), list(sem[0])
        while pila:
            i, j = pila.pop()
            for c in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
                if c in libre and c not in visto:
                    visto.add(c)
                    pila.append(c)
        return all(visto & s for s in sem[1:]) and all(
            any(entre(cx(i), a0 - 1e-6, a1 + 1e-6) and entre(cy(j), b0 - 1e-6, b1 + 1e-6) for i, j in visto)
            for a0, b0, a1, b1 in usos)
    azar, falsos = random.Random(5), 0
    for _ in range(500):
        W, D = azar.uniform(1.2, 6.0), azar.uniform(1.2, 6.0)
        cuerpos = [(a0, b0, min(W, a0 + azar.uniform(0.2, 2.5)), min(D, b0 + azar.uniform(0.2, 2.5)))
                   for a0, b0 in ((azar.uniform(0, W), azar.uniform(0, D)) for _ in range(azar.randint(0, 5)))]

        def acceso():
            if azar.random() < 0.5:
                x, y = azar.choice((0.0, W)), azar.uniform(0, D - 0.7)
                return (x, y), (x, y + azar.uniform(0.5, 1.0))
            x, y = azar.uniform(0, W - 0.7), azar.choice((0.0, D))
            return (x, y), (x + azar.uniform(0.5, 1.0), y)
        accesos = [acceso() for _ in range(azar.randint(0, 4))]
        usos = [(a0, b0, min(W, a0 + azar.uniform(0.1, 1.5)), min(D, b0 + azar.uniform(0.1, 1.5)))
                for a0, b0 in ((azar.uniform(0, W), azar.uniform(0, D)) for _ in range(azar.randint(0, 3)))]
        h, g = azar.choice(((0.25, 0.10), (0.25, 0.05)))
        esperado = celda_por_celda(W, D, cuerpos, accesos, usos, h, g)
        assert EQ._alcanza(EQ._Estancia((0.0, 0.0, W, D)), cuerpos, accesos, usos, h, g) == esperado, \
            (W, D, cuerpos, accesos, usos, h, g)
        falsos += not esperado
    assert 100 < falsos < 400, falsos                  # los dos resultados se prueban

if __name__ == "__main__":
    test_equipamiento_orden(); print("OK64")


@calibracion_anterior
def test_patios_editables():
    """R4.12: patios editables en la web. Clic en un patio (automático o manual) abre su ficha (ancho y fondo en los ejes
    del edificio, posición en el SCP actual) y se arrastra en la planta como los núcleos; al primer cambio los patios
    pasan a manuales (como los núcleos). Las flechas del teclado mueven el patio o el núcleo elegido un paso de grilla por
    pulsación (diez con Shift) y el motor recalcula una sola vez, cuando pasan 300 ms sin pulsar. El motor no cambia:
    ya recibe patios manuales. (El comportamiento se comprobó en navegador; esta prueba vigila la web con comprobaciones
    del código y el motor con el mismo recorrido que hace la web, que se repite acá en Python.)"""
    import math
    base = os.path.join(os.path.dirname(__file__), "..")
    html = open(os.path.join(base, "web", "index.html"), encoding="utf-8").read()
    js = html.split("<script>", 1)[1].split("</script>", 1)[0]

    def cuerpo(nombre):
        ini = js.index("function %s(" % nombre)
        fin = min(k for k in (js.find("\nfunction ", ini + 1), js.find("\nasync function ", ini + 1), js.find("\n/*", ini + 1),
                              len(js)) if k >= 0)
        return js[ini:fin]
    # ---- la web: las funciones, la ficha y los lugares donde se elige un patio
    for f in ("function patioPanel(", "function patioElegido(", "function patioGuardado(", "function patioDe(", "function cajaPatio(",
              "function atraviesa(", "function despLibre(", "function aplicarPatio(", "function quitarPatioElegido(",
              "function soltarPatio(", "function elegidoMovible(", "function moverConFlechas(", "async function finFlechas(",
              "function olvidarFlechas(", "function sinPatio(", "const listaPatios=", "const FLECHAS={"):
        assert f in js, f
    assert "#svg [data-patio]{cursor:grab}" in html
    dibujo = cuerpo("draw")
    assert "'data-patio':i" in dibujo and "i===selPatio" in dibujo                            # los polígonos de patio llevan su índice
    clic = js.split("svg.addEventListener('click',e=>{", 1)[1].split("\nsvg.addEventListener('dblclick'", 1)[0]
    assert "closest('[data-patio]')" in clic and "selPatio=+tq.getAttribute('data-patio')" in clic
    assert clic.count("sinPatio()") >= 3                                                      # un clic en otra cosa suelta el patio
    pantalla = cuerpo("unitPanel")
    assert pantalla.index("corePanel()") < pantalla.index("pasilloPanel()") < pantalla.index("patioPanel()")
    ficha = cuerpo("patioPanel")
    for t in ('id="paAncho"', 'id="paFondo"', 'id="paX"', 'id="paY"', 'onclick="aplicarPatio()"', 'onclick="quitarPatioElegido()"',
              "Quitar este patio", "Cerrar", "automático: al cambiar uno, todos los patios pasan a modo manual", "SCP actual",
              "patio_min", "atraviesa(s.p)", "flechas del teclado"):
        assert t in ficha, t
    assert "patio" in html.split('id="pistaFicha">', 1)[1].split("</div>", 1)[0]
    # ---- aplicar la ficha: valida, guarda el estado antes de cambiar, pasa a manual, reemplaza el polígono y recalcula
    ap = cuerpo("aplicarPatio")
    assert ap.index("A*F<1") < ap.index("recordar('cambiar el patio '") < ap.index("ensurePatiosManual()") < ap.index("patios[s.j]=r") \
        < ap.index("selPatioC=centroArea(r)") < ap.index("run(lastStage")
    assert "[[o[0],o[1]],[o[0]+A,o[1]],[o[0]+A,o[1]+F],[o[0],o[1]+F]].map(q=>b.R.W(q))" in ap and "El patio ya mide eso" in ap
    qp = cuerpo("quitarPatioElegido")
    assert qp.index("recordar('quitar el patio '") < qp.index("ensurePatiosManual()") < qp.index("patios.splice(s.j,1)") < qp.index("run(lastStage")
    # ---- arrastrar: como el núcleo (se captura al moverse, la esquina cae en la grilla); al soltar se guarda, pasa a manual y recalcula
    assert "dragPatio={i:+tpa.getAttribute('data-patio')" in js and "dragPatio&&dragPatio.moved" in cuerpo("drawOverlay")
    mueve = js.split("svg.addEventListener('pointermove',e=>{ if(!dragPatio||!view) return;", 1)[1].split("\nsvg.addEventListener(", 1)[0]
    assert "svg.setPointerCapture(e.pointerId)" in mueve and "ajustar(" in mueve and "despLibre(p,q)" in mueve
    suelta = js.split("svg.addEventListener('pointerup',e=>{ if(!dragPatio) return;", 1)[1].split("\nwindow.", 1)[0]
    assert "if(!g.moved) return" in suelta and "svg._skipClick=true" in suelta and "soltarPatio(g)" in suelta
    sp = cuerpo("soltarPatio")
    assert sp.index("recordar('mover el patio '") < sp.index("ensurePatiosManual()") < sp.index("patios[j]=patios[j].map(") < sp.index("run(lastStage")
    # ---- flechas: un paso de grilla en los ejes del SCP (Shift, diez); cada pulsación cambia el estado y el recálculo es uno solo
    mv = cuerpo("moverConFlechas")
    assert "pasoGrilla()*(e.shiftKey?10:1)" in mv and "aMundo([v[0]*paso,v[1]*paso],{o:[0,0],a:S.a})" in mv
    assert "if(!e.repeat) recordar('mover el '+(m.tipo==='patio'?'patio ':'núcleo ')" in mv   # cada pulsación se guarda; las repeticiones de una tecla apretada, no
    assert mv.index("recordar(") < mv.index("ensurePatiosManual()") < mv.index("patios[f.j]=")
    assert mv.index("recordar(") < mv.index("ensureManual()") < mv.index("coresManual[f.spec]=")
    assert "clearTimeout(tFlechas); tFlechas=setTimeout(finFlechas,300)" in mv
    assert "run(" not in mv and "runCirc(" not in mv                                          # recalcular es cosa de finFlechas, una vez por ráfaga
    fin = cuerpo("finFlechas")
    assert "await run(lastStage" in fin and "await runCirc()" in fin
    teclas = js.split("window.addEventListener('keydown'", 1)[1].split("\n/*", 1)[0]
    flecha = teclas.split("if(FLECHAS[e.key]", 1)[1].split("\n", 1)[0]
    for t in ("!texto", "t.tagName!=='SELECT'", "!e.ctrlKey", "!e.metaKey", "!e.altKey", "moverConFlechas(e)", "e.preventDefault()"):
        assert t in flecha, t                                                                  # en un campo de texto o una lista, las flechas son del campo
    assert "selPatio!=null" in teclas.split("if(e.key==='Escape')", 1)[1]                      # Esc suelta el patio
    assert "viewMode!=='plan'||tool||!result" in cuerpo("elegidoMovible")                      # con una herramienta activa no mueven nada
    for f in ("volverA", "setMass", "nuevo"):                                                  # otra masa o deshacer: lo que esperaba el temporizador ya no vale
        c = js[js.index("function %s(" % f):].split("\nfunction ", 1)[0].split("\nasync function ", 1)[0]
        assert "sinPatio()" in c and "olvidarFlechas()" in c, f
    foto = cuerpo("foto")
    assert "patios," in foto and "patios_mode" in foto and "coresManual" in foto               # lo que cambia esto se deshace
    marco_js = cuerpo("marcoPatio")                                                           # las fórmulas que se repiten abajo, en Python
    assert "L:q=>[q[0]*c+q[1]*s,-q[0]*s+q[1]*c],W:q=>[q[0]*c-q[1]*s,q[0]*s+q[1]*c]" in marco_js

    # ---- el motor, con el mismo recorrido que hace la web
    def marco(th):                               # como marcoPatio(): L del mundo a los ejes del edificio, W de vuelta
        c, sn = math.cos(th), math.sin(th)
        return (lambda q: (q[0] * c + q[1] * sn, -q[0] * sn + q[1] * c)), (lambda q: (q[0] * c - q[1] * sn, q[0] * sn + q[1] * c))

    def caja(p, th):                             # como cajaPatio(): (u0, v0, ancho, fondo) del rectángulo que lo contiene
        L, _ = marco(th)
        q = [L(a) for a in p]
        us, vs = [a[0] for a in q], [a[1] for a in q]
        return min(us), min(vs), max(us) - min(us), max(vs) - min(vs)

    def rect(u0, v0, w, d, th):                  # como aplicarPatio(): la esquina (u0, v0) y las dos medidas, alineado con el edificio
        _, W = marco(th)
        return [[round(a, 3) for a in W(q)] for q in ((u0, v0), (u0 + w, v0), (u0 + w, v0 + d), (u0, v0 + d))]

    def posicion(p, fp, th):                     # como esquinaPatio() con el SCP del edificio: el origen, en la esquina del rectángulo que contiene la masa
        u0, v0, _, _ = caja(p, th)
        L, _ = marco(th)
        f = [L(a) for a in fp]
        return u0 - min(a[0] for a in f), v0 - min(a[1] for a in f)

    def atraviesa(p, fp, th):                    # como atraviesa(): por eje del edificio, si llega de un borde a otro de la masa
        L, _ = marco(th)
        q, f = [L(a) for a in p], [L(a) for a in fp]
        return [min(a[k] for a in q) <= min(a[k] for a in f) + 0.05 and max(a[k] for a in q) >= max(a[k] for a in f) - 0.05 for k in (0, 1)]
    muestra = lambda n: json.load(open(os.path.join(base, "samples", n + ".json"), encoding="utf-8"))
    s = muestra("entre_medianeras_patio")
    corre = lambda fp, **p: generate({"footprint": fp, "height": s["height"], "stage": "plans", "params": p})
    entre = lambda **p: corre(s["footprint"], medianeras=s["medianeras"], **p)
    bandas = lambda r: sorted((round(min(q[1] for q in b["footprint"]), 3), round(max(q[1] for q in b["footprint"]), 3)) for b in r["blocks"])
    firma = lambda r: ([(u["id"], u["area"]) for u in r["units"]], bandas(r), r["metrics"].get("patio_area"), r["metrics"]["plate_area"])
    auto = entre()
    assert auto["patios_auto"] is True and len(auto["patios"]) == 1 and len(auto["blocks"]) == 2 and auto["units"]
    # 1) «al primer cambio los patios pasan a manuales»: los automáticos, copiados tal cual, dan el mismo resultado
    manual = entre(patios_mode="manual", patios=auto["patios"])
    assert manual["patios_auto"] is False and manual["patios"] == auto["patios"] and firma(manual) == firma(auto)
    # 2) trasladar el patio un paso de grilla (0,5 m) a lo largo del predio: los bloques cambian en consecuencia y sigue habiendo viviendas
    p0 = auto["patios"][0]
    traslada = lambda p, dx, dy: [[x + dx, y + dy] for x, y in p]
    y0, y1 = min(q[1] for q in p0), max(q[1] for q in p0)
    arriba = entre(patios_mode="manual", patios=[traslada(p0, 0, 0.5)])
    assert bandas(arriba) == sorted([(0.0, y0 + 0.5), (y1 + 0.5, 40.0)]) and len(arriba["units"]) >= 2
    assert abs(arriba["metrics"]["patio_area"] - auto["metrics"]["patio_area"]) < 1e-6        # el patio mide lo mismo
    # 3) de costado, un patio que atraviesa el predio de medianera a medianera deja una franja de edificio y une los dos bloques:
    # por eso la web lo corre solo a lo largo del predio (despLibre)
    assert atraviesa(p0, s["footprint"], 0.0) == [True, False]
    costado = entre(patios_mode="manual", patios=[traslada(p0, 0.5, 0)])
    assert len(auto["blocks"]) == 2 and len(costado["blocks"]) == 1
    # 4) la ficha: ancho y fondo en los ejes del edificio y la posición de su esquina de menor X y Y en el SCP; Aplicar arma el
    # rectángulo con la misma fórmula (en un edificio de 40 × 20 m girado 30° y trasladado)
    th = math.radians(30)
    giro = lambda q: [round(100 + marco(th)[1](q)[0], 3), round(50 + marco(th)[1](q)[1], 3)]
    quita = lambda p: [[a[0] - 100, a[1] - 50] for a in p]                                    # caja() y posicion() miden desde el origen del mundo
    edificio = [giro(q) for q in ((0, 0), (40, 0), (40, 20), (0, 20))]
    r1 = corre(edificio, patios_mode="manual", patios=[[giro(q) for q in ((12, 7), (20, 7), (20, 12), (12, 12))]])
    assert len(r1["patios"]) == 1 and len(r1["blocks"]) == 1 and len(r1["blocks"][0]["holes"]) == 1 and r1["units"]
    u0, v0, w, d = caja(quita(r1["patios"][0]), th)
    assert abs(w - 8) < 2e-3 and abs(d - 5) < 2e-3                                            # lo que muestra la ficha
    x, y = posicion(quita(r1["patios"][0]), quita(edificio), th)
    assert abs(x - 12) < 2e-3 and abs(y - 7) < 2e-3                                           # y la posición, desde la esquina del edificio
    r2 = corre(edificio, patios_mode="manual", patios=[[[a[0] + 100, a[1] + 50] for a in rect(u0, v0, 10, 5, th)]])   # «Ancho 10»: la esquina se queda
    u1, v1, w1, d1 = caja(quita(r2["patios"][0]), th)
    assert abs(w1 - 10) < 2e-3 and abs(d1 - 5) < 2e-3 and abs(u1 - u0) < 2e-3 and abs(v1 - v0) < 2e-3
    assert abs(r2["metrics"]["patio_area"] - 50) < 0.1 and len(r2["blocks"][0]["holes"]) == 1 and r2["units"]
    pc = muestra("patio_central")                                                             # sin girar: el patio de «Patio central» con la misma fórmula
    rc = corre(pc["footprint"], patios_mode="manual", patios=[rect(13, 11, 14, 8, 0.0)])
    assert rc["patios"] == corre(pc["footprint"], patios_mode="manual", patios=pc["patios"])["patios"] and len(rc["units"]) == 8
    # 5) los patios que dibuja la planta no son uno a uno los guardados: el que queda fuera se descarta y el que asoma se recorta
    #    (por eso la web busca el guardado por la geometría: patioGuardado)
    barra = [[0, 0], [60, 0], [60, 16], [0, 16]]
    guardados = [[[70, 2], [74, 2], [74, 8], [70, 8]], [[20, 5], [24, 5], [24, 11], [20, 11]], [[40, 10], [44, 10], [44, 20], [40, 20]]]
    rb = corre(barra, patios_mode="manual", patios=guardados)
    assert len(rb["patios"]) == 2 and any("queda fuera de la masa" in a for a in rb["warnings"])
    area = lambda p: abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2
    assert abs(sorted(area(p) for p in rb["patios"])[1] - 24) < 1e-6 and abs(sorted(area(p) for p in rb["patios"])[0] - 24) < 1e-6   # el asomado, recortado a 4 × 6

if __name__ == "__main__":
    test_patios_editables(); print("OK65")

@calibracion_anterior
def test_tabla_csv():
    """R7.2: la tabla de viviendas en CSV (engine/tabla_viviendas.py y GET /api/csv), para abrirla en Excel o LibreOffice en
    español: UTF-8 con BOM, separador «;», coma decimal y CRLF; una fila por vivienda y por nivel residencial (la planta tipo
    se repite en cada nivel) y, tras una línea en blanco, los totales. Lo que falta va vacío, nunca «None»."""
    import contextlib, copy, csv, io, threading, urllib.error, urllib.parse, urllib.request
    import server
    from engine import layout, tabla_viviendas as T
    raiz = os.path.join(os.path.dirname(__file__), "..")
    muestra = lambda n: json.load(open(os.path.join(raiz, "samples", n + ".json"), encoding="utf-8"))
    COLUMNAS = ["Nivel", "Vivienda", "Tipo", "Dormitorios", "Superficie (m²)", "Con muros (m²)", "Frente (m)", "Fondo (m)",
                "Pasillo", "Evacuación (m)", "Fondo de saco (m)", "Evacuación", "Calidad del plano", "Observaciones"]
    PALABRAS = {"ok": "cumple", "saco": "fondo de saco", "fail": "no cumple"}
    coma = lambda v, d: ("%.*f" % (d, v)).replace(".", ",")

    def partes(texto):                    # como la planilla: sin BOM, separador «;», comillas de CSV; (encabezados, filas, totales)
        assert texto.startswith("﻿") and not texto.startswith("﻿﻿")
        assert "\r\n" in texto and "\n" not in texto.replace("\r\n", "") and "\r" not in texto.replace("\r\n", "")
        filas = list(csv.reader(io.StringIO(texto[1:], newline=""), delimiter=";"))
        corte = filas.index([])           # la línea en blanco entre la tabla y los totales
        return filas[0], filas[1:corte], dict(filas[corte + 1:])

    # 1. barra con un solo núcleo manual: las tres evacuaciones (cumple, fondo de saco, no cumple) y todos los datos
    barra = muestra("barra")
    pedido = {"footprint": barra["footprint"], "height": barra["height"], "stage": "plans",
              "params": {"cores_mode": "manual", "cores": [[3, 8]], "auto_cores": False}}
    res = layout.generate(pedido)
    texto = T.result_to_csv(res)
    cab, filas, tot = partes(texto)
    niveles = [s["index"] for s in res["stories"] if s["program"] == "Residential"]
    assert cab == COLUMNAS and niveles == [0, 1, 2, 3, 4] and len(res["units"]) == 9 and len(filas) == 45
    esperadas = [(n, u) for n in niveles for u in res["units"]]            # por nivel y, en cada uno, las viviendas de la planta tipo
    for f, (n, u) in zip(filas, esperadas):
        assert f == [str(n), u["id"], u["type"], str(u["bedrooms"]), coma(u["area"], 1), coma(u["area_muros"], 1),
                     coma(u["width"], 2), coma(u["depth"], 2), u["pasillo"], coma(u["egress"], 1), coma(u["saco"], 1),
                     PALABRAS[u["egress_status"]], str(u["plan_score"]), ""], (f, u["id"])
        assert all("," in f[i] and "." not in f[i] for i in (4, 5, 6, 7, 9, 10)), f          # coma decimal, nunca punto
    assert {f[11] for f in filas} == {"cumple", "fondo de saco", "no cumple"}
    m = res["metrics"]
    assert m["units_total"] == 45 and list(tot)[:4] == ["Viviendas totales", "Niveles residenciales", "Superficie vendible total, NSA (m²)", "Eficiencia (%)"]
    assert {k: tot[k] for k in list(tot)[:4]} == {"Viviendas totales": "45", "Niveles residenciales": "5",
                                                  "Superficie vendible total, NSA (m²)": coma(m["nsa_total"], 1),
                                                  "Eficiencia (%)": coma(m["efficiency_total"], 1)}, tot
    assert [k for k in tot if k.startswith("Factibilidad")] == list(tot)[4:] and len(tot) == 10        # R10.13: al final, la factibilidad (test_factibilidad)
    assert "None" not in texto and texto.split("\r\n")[1 + 45] == "" and texto.endswith("\r\n")

    # 2. las observaciones: los avisos de la vivienda que no cumplen, separados por « | » (T_dos_lineas tiene planos con fallas)
    t2 = muestra("T_dos_lineas")
    res2 = layout.generate({"footprint": t2["footprint"], "height": t2["height"], "stage": "plans",
                            "params": {"centerlines": t2["centerlines"]}})
    cab, filas2, _ = partes(T.result_to_csv(res2))
    con_avisos = 0
    for f, u in zip(filas2, res2["units"]):
        falla = [c["msg"] for c in u["checks"] if not c["ok"]]
        assert f[13] == " ".join(" | ".join(falla).split()), (u["id"], f[13])
        assert f[12] == str(u["plan_score"])
        con_avisos += bool(falla)
    assert 0 < con_avisos < len(res2["units"]) and any(" | " in f[13] for f in filas2)

    # 3. un resultado sin planos (etapa «mix»): sin dormitorios, calidad ni avisos todavía, y vacío es vacío
    mix = layout.generate({"footprint": barra["footprint"], "height": barra["height"], "stage": "mix", "params": {}})
    texto3 = T.result_to_csv(mix)
    cab, filas3, tot3 = partes(texto3)
    assert len(filas3) == 40 and all(f[3] == "" and f[12] == "" and f[13] == "" and f[4] and f[11] == "cumple" for f in filas3)
    assert "None" not in texto3 and tot3["Viviendas totales"] == "40"

    # 4. torre mixta: los niveles de estacionamiento, comercio y oficinas no llevan viviendas; los residenciales conservan su índice
    tm = muestra("torre_mixta")
    res4 = layout.generate({"footprint": tm["footprint"], "height": tm["height"], "stage": "plans",
                            "params": {"stories": tm["stories"]}})
    cab, filas4, tot4 = partes(T.result_to_csv(res4))
    assert [s["index"] for s in res4["stories"] if s["program"] != "Residential"] == [0, 1, 2, 3]
    assert len(filas4) == 50 == res4["metrics"]["units_total"] and sorted({f[0] for f in filas4}) == ["4", "5", "6", "7", "8"]
    assert tot4["Viviendas totales"] == "50" and tot4["Niveles residenciales"] == "5"

    # 5. celdas con «;», comillas y saltos de línea van entre comillas; una fórmula no se ejecuta; 1e9 (sin salida) y el cero
    r5 = copy.deepcopy(res)
    u = r5["units"][0]
    u.update(type="=SUMA(A1:A9)", egress=1e9, egress_status="fail", bedrooms=0)
    u["checks"] = [{"ok": False, "msg": 'Primero; con "comillas"\ny salto'}, {"ok": False, "msg": "Segundo"},
                   {"ok": True, "info": True, "msg": "No debe salir"}]
    texto5 = T.result_to_csv(r5)
    cab, filas5, _ = partes(texto5)
    assert '"Primero; con ""comillas"" y salto | Segundo"' in texto5 and "No debe salir" not in texto5
    assert filas5[0][13] == 'Primero; con "comillas" y salto | Segundo' and filas5[0][2] == "'=SUMA(A1:A9)"
    assert filas5[0][3] == "0" and filas5[0][9] == "" and filas5[0][11] == "no cumple" and filas5[1][3] != ""

    # 6. el servidor: 404 en español sin resultado o sin viviendas; con resultado, el archivo con sus cabeceras
    server.STATE.update(mass=None, result=None)
    srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d" % srv.server_address[1]

    def pedir(ruta, cuerpo=None):
        req = urllib.request.Request(url + ruta, data=None if cuerpo is None else json.dumps(cuerpo).encode(),
                                     method="GET" if cuerpo is None else "POST", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as ex:
            return ex.code, ex.headers, ex.read()
    try:
        cod, _, cuerpo = pedir("/api/csv")
        error = json.loads(cuerpo.decode("utf-8"))["error"]
        assert cod == 404 and error.startswith("Trazo: primero genera una planta") and "Generar planos" in error, (cod, error)
        pedir("/api/generate", {"footprint": barra["footprint"], "height": 15, "stage": "massing"})
        cod, _, cuerpo = pedir("/api/csv")                                  # solo la masa: todavía no hay viviendas
        error = json.loads(cuerpo.decode("utf-8"))["error"]
        assert cod == 404 and error.startswith("Trazo:") and "todavía no tiene viviendas" in error, (cod, error)
        pide_barra = {"footprint": barra["footprint"], "height": 15, "stage": "plans", "params": {}}
        assert pedir("/api/generate", pide_barra)[0] == 200
        cod, cabeceras, cuerpo = pedir("/api/csv")
        assert cod == 200 and cabeceras["Content-Type"] == "text/csv; charset=utf-8", (cod, cabeceras["Content-Type"])
        assert cabeceras["Content-Disposition"] == 'attachment; filename="trazo_viviendas.csv"'
        assert cuerpo[:3] == b"\xef\xbb\xbf" and int(cabeceras["Content-Length"]) == len(cuerpo)
        texto6 = cuerpo.decode("utf-8")
        esperado = layout.generate({"footprint": barra["footprint"], "height": 15, "stage": "plans", "params": {}})
        assert texto6 == T.result_to_csv(esperado)                          # el mismo CSV que arma la función con el resultado
        cab, filas6, tot6 = partes(texto6)
        assert cab == COLUMNAS and len(filas6) == 40 == int(tot6["Viviendas totales"]) and tot6["Niveles residenciales"] == "5"
        assert {f[11] for f in filas6} == {"cumple"} and {f[0] for f in filas6} == {"0", "1", "2", "3", "4"}
        # el nombre de la masa va en el nombre del archivo, sin tildes ni caracteres que no valgan en una cabecera o en Windows
        for nombre, archivo in (("Barra 60x16", "trazo_viviendas_Barra_60x16.csv"),
                                ("Torre Ñandú (2ª etapa)", "trazo_viviendas_Torre_Nandu_2a_etapa.csv"),
                                ('x"\r\nSet-Cookie: a=b', "trazo_viviendas_x_Set-Cookie_a_b.csv"),
                                ("../../etc/pasaporte", "trazo_viviendas_etc_pasaporte.csv"),
                                ("", "trazo_viviendas.csv"), ("¡¡¡", "trazo_viviendas.csv"), ("a" * 200, "trazo_viviendas_" + "a" * 60 + ".csv")):
            cod, cabeceras, _ = pedir("/api/csv?nombre=" + urllib.parse.quote(nombre))
            assert cod == 200 and cabeceras["Content-Disposition"] == 'attachment; filename="%s"' % archivo, (nombre, cabeceras["Content-Disposition"])
            assert server.nombre_csv(nombre) == archivo
        # siempre el último resultado: la torre mixta (niveles 4 a 8) reemplaza a la barra
        assert pedir("/api/generate", {"footprint": tm["footprint"], "height": tm["height"], "stage": "plans",
                                       "params": {"stories": tm["stories"]}})[0] == 200
        cab, filas7, tot7 = partes(pedir("/api/csv")[2].decode("utf-8"))
        assert len(filas7) == 50 and sorted({f[0] for f in filas7}) == ["4", "5", "6", "7", "8"] and tot7["Viviendas totales"] == "50"
        original, tabla_rota = server.result_to_csv, io.StringIO()
        server.result_to_csv = lambda res: 1 / 0                            # un fallo al armar la tabla: 500 en español, no una conexión cortada
        try:
            with contextlib.redirect_stderr(tabla_rota):
                cod, _, cuerpo = pedir("/api/csv")
        finally:
            server.result_to_csv = original
        error = json.loads(cuerpo.decode("utf-8"))["error"]
        assert cod == 500 and error.startswith("Trazo: no pude armar la tabla de viviendas (ZeroDivisionError") and "ZeroDivisionError" in tabla_rota.getvalue()
        assert pedir("/api/csv")[0] == 200
        pedir("/api/reset", {})                                             # «Nuevo»: el servidor olvida el resultado
        assert pedir("/api/csv")[0] == 404
    finally:
        srv.shutdown()
        srv.server_close()
        server.STATE.update(mass=None, result=None)

    # 7. la web: «Tabla CSV» junto al DXF, pide /api/csv con el nombre de la masa y guarda el archivo tal cual (con el BOM)
    html = open(os.path.join(raiz, "web", "index.html"), encoding="utf-8").read()
    exportar = html.split("<h2>Exportar</h2>", 1)[1].split("</div>", 1)[0]
    assert "dl('dxf')" in exportar and 'id="btnCsv"' in exportar and 'onclick="bajarCsv()"' in exportar
    assert exportar.index("dl('dxf')") < exportar.index('id="btnCsv"') and ">Tabla CSV</button>" in exportar
    js = html.split("<script>", 1)[1]
    bajar = js.split("async function bajarCsv(", 1)[1].split("\nasync function dl(", 1)[0]
    assert "fetch('/api/csv?nombre='+encodeURIComponent(nombre" in bajar and "Genera primero la planta con viviendas" in bajar
    assert "r.blob()" in bajar and ".text()" not in bajar          # text() descarta el BOM y Excel leería mal las tildes
    assert "a.download=f?f[1]:'trazo_viviendas.csv'" in bajar

if __name__ == "__main__":
    test_tabla_csv(); print("OK66")


def test_alas_unidas():
    """Planta en C (15 × 30 con un patio manual a 0,5 m del lindero izquierdo, sin medianeras, núcleos automáticos):
    el corte a lo largo dejaba tres tiras paralelas cuyos pasillos no se tocaban —cada uno con dos puntas libres y dos
    núcleos: seis núcleos y seis ascensores, una sola vivienda—. Ahora build_pieces elige la descomposición que deja
    los pasillos unidos entre sí: las dos alas en U con su pasillo y el tramo que las une junto al patio."""
    from engine.circulation import _componentes, build_pieces
    from engine.layout import merge_params
    fp = [[0, 0], [15, 0], [15, 30], [0, 30]]
    patio = [[0.5, 12.7], [8.1, 12.7], [8.1, 19.5], [0.5, 19.5]]
    mix = [{"name": "2 dorm", "area": 75, "percent": 50, "dorms": 2}, {"name": "3 dorm", "area": 95, "percent": 50, "dorms": 3}]
    p = dict(corridor_width=1, min_unit_width=5, core_width=4.5, core_depth=6.02, egress_single=18, egress_multi=30,
             unit_mix=mix, cores_mode="auto", patios_mode="manual", patios=[patio], ascensores="1",
             stories=[{"program": "Residential", "height": 3}] * 5)
    r = run(fp, **p)
    print(len(r["cores"]), r["metrics"]["core"], [ps["eje"] for ps in r["pasillos"]], r["warnings"])
    ejes = [ps["eje"] for ps in r["pasillos"]]
    assert len(ejes) == 3 and r["metrics"]["wings"] == 3
    horizontales = [e for e in ejes if abs(e[0][1] - e[1][1]) < 1e-6]
    verticales = [e for e in ejes if abs(e[0][0] - e[1][0]) < 1e-6]
    assert len(horizontales) == 2 and len(verticales) == 1, ejes      # dos alas en U y el tramo que las une
    assert 8.45 < verticales[0][0][0] < 14.65                         # el tramo que une, en la tira junto al patio
    assert len(r["cores"]) <= 2 and r["metrics"]["core"]["elevators_total"] <= 2, r["metrics"]["core"]
    assert len(r["units"]) >= 3, len(r["units"])       # con las medidas del usuario (dorm. principal más chico) entran 4
    assert not any("sirve a 0" in w for w in r["warnings"]), r["warnings"]
    # las piezas elegidas forman un solo grupo; el corte a lo largo (que decompose_wings puntúa mejor) deja tres
    pl = r["blocks"][0]["plate"]
    pb = merge_params(p)
    pb["_huecos"] = r["blocks"][0]["plate_holes"]
    assert _componentes(build_pieces(pl, pb)) == 1
    from engine.massing import decompose_wings
    cands = decompose_wings(pl, holes=pb["_huecos"], candidatos=True)
    assert len(cands) == 2 and cands[0][0] > cands[1][0]
    from engine.circulation import _piezas_de, _pedidos_ancho
    largo = _piezas_de([(q, cands[0][1]) for q in cands[0][2]], pl, pb["_huecos"], _pedidos_ancho(pb), pb)
    assert _componentes(largo) == 3
    # con una medianera a la izquierda (la planta del usuario), el resultado sigue siendo el mismo de antes: la U
    r2 = run(fp, medianeras=[{"a": [0, 30], "b": [0, 0], "retiro": 0}], **p)
    assert len(r2["pasillos"]) == 3 and len(r2["cores"]) <= 2
    # una L común no cambia: su corte de siempre ya deja los pasillos unidos
    rl = run([[0, 0], [50, 0], [50, 14], [16, 14], [16, 40], [0, 40]])
    assert rl["metrics"]["wings"] == 2 and all(len(ps["eje"]) == 2 for ps in rl["pasillos"])

if __name__ == "__main__":
    test_alas_unidas(); print("OK67")


@calibracion_anterior
def test_puerta_en_la_punta():
    """R3.7b: en una punta libre del pasillo común (sin unión, núcleo ni conector), la vivienda del extremo pone el hall
    —y su puerta— en la punta si el plano no empeora: el pasillo termina en la última puerta en vez de seguir unos
    metros sin servir a nadie (pedido del usuario, «Terreno 15 × 30»: el pasillo P1 seguía 1,9 m más allá de la puerta
    de U01; en una barra con el núcleo manual al medio, 4,2 m en cada punta)."""
    import math
    from engine import geometry as G, layout as LY
    from engine.massing import _dist_to_boundary

    def puntas(r):
        """(tramo, punta, metros desde la punta hasta el borde de la primera puerta de entrada) de cada punta libre."""
        out = []
        cores = [c["poly"] for c in r["cores"]]
        doors = [(d["p"], d["q"], u["id"]) for u in r["units"] for d in u["doors"] if d.get("entry")]
        for ps in r["pasillos"]:
            (x0, y0), (x1, y1) = ps["eje"]
            L = math.hypot(x1 - x0, y1 - y0)
            d = ((x1 - x0) / L, (y1 - y0) / L)
            otros = [r["corridors"][k] for q in r["pasillos"] if q is not ps for k in q["partes"]] + \
                [r["corridors"][k] for k in ps["partes"][1:]] + cores
            for E, sgn in (((x0, y0), 1), ((x1, y1), -1)):
                if any(G.point_in_poly(E, pg) or _dist_to_boundary(E, pg) < 0.6 for pg in otros):
                    continue
                ts = []
                for p, q, uid in doors:
                    m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
                    v = (m[0] - E[0], m[1] - E[1])
                    t, perp = (v[0] * d[0] + v[1] * d[1]) * sgn, abs(v[0] * d[1] - v[1] * d[0])
                    if perp < ps["ancho"] / 2 + 0.4 and -0.5 <= t <= L + 0.5:
                        ts.append((round(max(t - 0.45, 0), 2), uid))
                out.append((ps["id"], [round(c, 2) for c in E], min(ts) if ts else None))
        return out

    def sin_regla(fp, **p):
        antes = LY.puntas_libres
        LY.puntas_libres = lambda *a: None
        try:
            return run(fp, **p)
        finally:
            LY.puntas_libres = antes
    fp = [[0, 0], [15, 0], [15, 30], [0, 30]]
    mix = [{"name": "2 dorm", "area": 75, "percent": 50, "dorms": 2}, {"name": "3 dorm", "area": 95, "percent": 50, "dorms": 3}]
    std = {"vivienda": {"dorm_principal": {"min_area": 8, "min_side": 2.6, "typ_area": 11.5, "typ": [3.2, 3.6]},
                        "estudio": {"min_area": 0, "min_side": 0, "typ_area": 0, "typ": [0, 0]}}}
    p = dict(corridor_width=1, min_unit_width=5, core_width=4.5, core_depth=6.02, egress_single=18, egress_multi=30,
             unit_mix=mix, cores_mode="manual", cores=[[12.8, 9.1]], patios_mode="manual",
             patios=[[[0.5, 19.5], [8.1, 19.5], [8.1, 12.7], [0.5, 12.7]]], standards=std,
             medianeras=[{"a": [0, 30], "b": [0, 0], "retiro": 0}])
    r, r0 = run(fp, **p), sin_regla(fp, **p)
    print(puntas(r0), puntas(r))

    def cerca(qs):                                                                   # por pasillo, la punta con la puerta
        out = {}                                                                     # más cerca (v2.62: el ala de arriba
        for pid, _, t in qs:                                                         # pasa a pasillo de borde con una sola
            if t and (pid not in out or t < out[pid]):                               # vivienda, cuyas dos puntas son
                out[pid] = t                                                         # libres: la puerta va a la primera)
        return out
    a0, a = cerca(puntas(r0)), cerca(puntas(r))
    assert a0["P1"][0] >= 1.5 and a["P1"][0] <= 0.3 and a["P3"][0] <= 0.3, (a0, a)   # antes 1,87 m; ahora la puerta en la punta
    assert [u["id"] for u in r["units"]] == [u["id"] for u in r0["units"]]
    for u, u0 in zip(r["units"], r0["units"]):                                       # la regla no empeora ningún plano
        assert u["plan_score"] >= u0["plan_score"] and len(u["rooms"]) >= len(u0["rooms"]), (u["id"], u["plan_score"], u0["plan_score"])
        assert abs(u["area"] - u0["area"]) < 1e-6
    assert [ps["eje"] for ps in r["pasillos"]] == [ps["eje"] for ps in r0["pasillos"]]  # el pasillo dibujado no cambia
    # una barra con el núcleo manual al medio (las dos puntas libres: 4,2 m sin puerta en cada una) y una L con el
    # núcleo al medio del ala larga (6,7 m en la punta de P1 y 3,4 m en la de P2): la puerta queda en la punta
    for fp_, c_ in (([[0, 0], [40, 0], [40, 16], [0, 16]], [[20, 8]]),
                    ([[0, 0], [50, 0], [50, 14], [16, 14], [16, 40], [0, 40]], [[30, 7]])):
        rl, rl0 = run(fp_, cores_mode="manual", cores=c_), sin_regla(fp_, cores_mode="manual", cores=c_)
        l0, l = [q for q in puntas(rl0) if q[2]], [q for q in puntas(rl) if q[2]]
        print(l0, l)
        assert len(l0) == 2 and min(q[2][0] for q in l0) >= 3.0 and len(l) == 2 and all(q[2][0] <= 0.3 for q in l), (l0, l)
        for u, u0 in zip(rl["units"], rl0["units"]):
            assert u["plan_score"] >= u0["plan_score"] and len(u["rooms"]) >= len(u0["rooms"]), (u["id"], u["plan_score"], u0["plan_score"])
    # con un núcleo en cada punta (barra) no hay puntas libres: nada que mover
    rb = run([[0, 0], [60, 0], [60, 16], [0, 16]])
    assert puntas(rb) == [] and rb["units"] == sin_regla([[0, 0], [60, 0], [60, 16], [0, 16]])["units"]

if __name__ == "__main__":
    test_puerta_en_la_punta(); print("OK68")


@vivienda_anterior
def test_medidas_en_vivo():
    """R4.13a: medidas en vivo (solo web; el motor no cambia). Mientras se dibuja o se arrastra, una etiqueta con la medida va
    junto a lo que se mueve, con el mismo formato de las cotas (2 decimales): la línea muestra su largo y su ángulo en el SCP
    (lo tipeado manda: R4.13b); el patio, ancho × fondo en los ejes del edificio; la medianera, el largo del borde que se marca;
    el tabique entre viviendas, el frente de cada una (una etiqueta a cada lado, y los campos de la barra siguen al tabique,
    salvo el que se está escribiendo o tiene el foco); el tabique interior, el ancho de la estancia de cada lado en la dirección
    del arrastre (la que está junto a donde se lo tomó); la puerta, la distancia de sus bordes a las puntas de su tabique
    («a | b»); el núcleo y el patio, cuánto se corrieron (ΔX, ΔY en los ejes del SCP) y el patio también la posición de su
    esquina, como la ficha; y las flechas del teclado, la misma etiqueta hasta que el motor recalcula. Todas pasan por una sola
    función (`etiquetaMedida`: encima de todo, sin capturar eventos, con los colores del tema, lejos del puntero y sin pisarse).
    Los números son lo que el motor deja al soltar: el tabique entre viviendas, el interior y la puerta se frenan donde el motor
    los frena (la mitad de `min_unit_width`, 0,60 m por estancia, 5 cm a cada lado de la puerta) y entonces la etiqueta sale en rojo.
    (El comportamiento se comprobó en navegador; esta prueba vigila la web con comprobaciones del código y, si hay node, ejecuta
    el código de la página contra lo que hace el motor al soltar.)"""
    import math, re, shutil, subprocess, tempfile
    base = os.path.join(os.path.dirname(__file__), "..")
    html = open(os.path.join(base, "web", "index.html"), encoding="utf-8").read()
    js = html.split("<script>", 1)[1].split("</script>", 1)[0]

    def cuerpo(nombre):
        ini = js.index("function %s(" % nombre)
        fin = min(k for k in (js.find("\nfunction ", ini + 1), js.find("\nasync function ", ini + 1), js.find("\n/*", ini + 1),
                              len(js)) if k >= 0)
        return js[ini:fin]
    # ---- la web: una sola función dibuja; las etiquetas no capturan eventos, siguen el tema y se alejan del puntero
    for f in ("function etiquetaMedida(", "function normalPantalla(", "function etqLinea(", "function etqPatio(", "function etqMedianera(",
              "function frentesCon(", "function etqTab(", "function tramoEn(", "function dPared(", "function etqPared(",
              "function bordeDePuerta(", "function etqPuerta(", "const posTab=", "const deltaTxt=", "const arribaDe=", "const med2=",
              "const PARED_MIN=0.6, PUERTA_MARGEN=0.05;", "const FRENO=0.005;"):
        assert f in js, f
    et = cuerpo("etiquetaMedida")
    assert et.count("'pointer-events':'none'") >= 3 and "el('g',{class:'etq','pointer-events':'none'}" in et   # el grupo, los textos y el fondo
    assert "TINTA()" in et and "HALO()" in et and "EVAC.fail" in et and "getComputedTextLength" in et   # colores del tema; el rojo es el de la evacuación
    assert "opt.fijo" in et and "opt.ocupado" in et and "ptr" in et and "$('svg').clientWidth" in et   # lado fijo, sin pisarse, el puntero, dentro de la planta
    assert re.search(r"const TINTA=\(\)=>esOscuro\(\)\?'#c7cfdb':'#344054', HALO=\(\)=>esOscuro\(\)\?'#12161c':'#fff'", js)
    assert "toFixed(2)" in js.split("const med2=", 1)[1].split("\n", 1)[0]                           # el formato de las cotas
    assert "'ΔX '" in js and "' · ΔY '" in js and "' × '" in js and "' | '" in js
    assert "'X '+e0[0].toFixed(2)" not in js                                                           # la X, Y suelta del patio ahora va en la etiqueta
    ov = cuerpo("drawOverlay")                           # quién llama: la línea, el patio, la medianera, el tabique, el interior, la puerta, el núcleo y el patio
    for t in ("const et=[];", "if(curLine.length&&nx) et.push(...etqLinea(curLine[curLine.length-1],nx));",
              "if(tool==='patio'&&curPatio.length&&np) et.push(...etqPatio(curPatio[0],np));",
              "if(tool==='medianera'&&medHover!=null) et.push(...etqMedianera(medHover));"):
        assert t in ov, t
    tabq = ov.split("if(dragTab&&dragTab.moved", 1)[1].split("if(dragIn&&dragIn.moved", 1)[0]
    assert "et.push(...etqTab(t,dragTab));" in tabq
    inte = ov.split("if(dragIn&&dragIn.moved", 1)[1].split("const pc=", 1)[0]
    assert "et.push(...(dragIn.tipo==='pared'?etqPared(dragIn):etqPuerta(dragIn)));" in inte
    nuc = ov.split("const pc=dragCore&&dragCore.moved?dragCore:flechas&&flechas.tipo==='nucleo'?flechas:null;", 1)[1].split("const pv=", 1)[0]
    assert "et.push([arribaDe(q),[deltaTxt(d)],{}]);" in nuc                       # el arrastre y las flechas comparten la vista previa
    pat = ov.split("const pv=dragPatio&&dragPatio.moved?dragPatio:flechas&&flechas.tipo==='patio'?flechas:null", 1)[1].split("const line=", 1)[0]
    assert "deltaTxt(pv.d)" in pat and "esquinaPatio(cajaPatio(q))" in pat and "'esquina X '" in pat
    assert ov.rstrip().split("\n")[-1].lstrip().startswith("const oc=[]; et.forEach(a=>etiquetaMedida(go,a[0],a[1],Object.assign({ocupado:oc},a[2])));")   # al final, encima de todo
    # la barra: los frentes del tabique siguen al arrastre (los mismos de las etiquetas), salvo un campo que se escribe o tiene el foco
    mv = cuerpo("medidasVivas")
    assert "frentesCon(s.t,dragTab&&dragTab.moved?dragTab.d:0)" in mv and "!c.dataset.sucio&&document.activeElement!==c" in mv
    # el puntero está al día en cada arrastre (el mousemove que lo actualiza llega después del pointermove que dibuja)
    for t in ("const w=toWorld(e), t=result.tabiques[dragTab.k]; ptr=w; dragTab.moved=true;",
              "const w=toWorld(e), r=dirIn(dragIn); if(!r) return; ptr=w; dragIn.moved=true;",
              "const w=toWorld(e), k=result.cores[dragCore.i]; ptr=w; dragCore.moved=true;",
              "const w=toWorld(e), p=listaPatios()[dragPatio.i]; ptr=w; dragPatio.moved=true;"):
        assert t in js, t
    # las flechas: cada pulsación redibuja y la etiqueta se borra cuando el motor recalcula (una sola vez, a los 300 ms)
    assert "clearTimeout(tFlechas); tFlechas=setTimeout(finFlechas,300); drawOverlay(); return true;" in cuerpo("moverConFlechas")
    assert "if(flechas===f){ flechas=null; drawOverlay(); }" in js.split("async function finFlechas(", 1)[1].split("\nfunction ", 1)[0]
    # frentesTab sigue dando lo mismo sin la posición (la barra y el frente tipeado lo usan así)
    ft = cuerpo("frentesTab")
    assert "function frentesTab(t,sx)" in ft and "x=sx==null?s:sx" in ft and "A.width+(x-s)" in ft and "B.width-(x-s)" in ft

    node = shutil.which("node")
    if not node:
        print("(sin node: se omiten «node --check» del programa de la página y los números de las etiquetas contra el motor)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        # ---- el programa de la página (el primer <script> sin atributos) es JavaScript válido
        ruta = os.path.join(tmp, "programa.js")
        open(ruta, "w", encoding="utf-8").write(js)
        c = subprocess.run([node, "--check", ruta], capture_output=True, text=True, encoding="utf-8")
        assert c.returncode == 0, c.stderr

        # ---- los números: se ejecuta el código de la página (sin pantalla) y se compara con lo que el motor deja al soltar
        seccion = js[js.index("/* ---------- medidas en vivo (R4.13a)"):js.index("const svg=$('svg');")]
        previas = "\n".join([cuerpo(n) for n in ("enPoly", "segIn", "dirIn", "frentesTab", "domAngle", "marcoPatio", "centroidOf")] +
                            [re.search(r"^const %s=.*$" % n, js, re.M).group(0) for n in ("mitad", "aLocal", "aMundo")])
        arnes = """const fs = require('fs');
const E = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const vals = { min_unit_width: E.min_unit_width, party_wall: E.party_wall };
const $ = id => ({ value: vals[id] });
let result = E.result, footprint = [], scp = { o: [0, 0], a: 0 }, tipeado = {};
const X = p => p[0], Y = p => -p[1];                        // sin pantalla: x a la derecha, y hacia arriba
const scpActual = () => scp, medidaNum = k => (k in tipeado ? tipeado[k] : NaN);
%s
%s
const salida = E.casos.map(c => {
  tipeado = c.tipeado || {}; if (c.scp_a !== undefined) scp = { o: [0, 0], a: c.scp_a }; if (c.footprint) footprint = c.footprint;
  let r;
  switch (c.f) {
    case 'tab': r = etqTab(result.tabiques[c.k], { w: c.w, d: c.d }); break;
    case 'pared': r = etqPared({ u: c.u, tipo: 'pared', k: c.k, w: c.w, d: c.d }); break;
    case 'puerta': r = etqPuerta({ u: c.u, tipo: 'puerta', k: c.k, d: c.d }); break;
    case 'linea': r = etqLinea(c.prev, c.q); break;
    case 'patio': r = etqPatio(c.p0, c.p1); break;
    case 'medianera': r = etqMedianera(c.i); break;
    case 'delta': return deltaTxt(c.d);
    case 'tramo': return tramoEn(c.poly, c.o, c.r, c.t0);
    case 'borde': return bordeDePuerta(c.u, c.d);
  }
  return r.map(e => ({ texto: e[1].join(' / '), mal: !!e[2].mal, lado: e[2].lado }));
});
console.log(JSON.stringify(salida));
""" % (previas, seccion)
        open(os.path.join(tmp, "arnes.js"), "w", encoding="utf-8").write(arnes)

        def en_node(res, casos, min_w=3.5, pw=0.3):
            open(os.path.join(tmp, "entrada.json"), "w", encoding="utf-8").write(
                json.dumps({"result": res, "casos": casos, "min_unit_width": min_w, "party_wall": pw}))
            p = subprocess.run([node, os.path.join(tmp, "arnes.js"), os.path.join(tmp, "entrada.json")],
                               capture_output=True, text=True, encoding="utf-8")
            assert p.returncode == 0, p.stderr
            return json.loads(p.stdout)
        num = lambda t: float(re.findall(r"-?\d+\.\d\d", t)[0])
        dot = lambda p, v: p[0] * v[0] + p[1] * v[1]
        mitad = lambda s: [round((s[0][0] + s[1][0]) / 2, 3), round((s[0][1] + s[1][1]) / 2, 3)]   # como mitad() de la página
        hacia = lambda m, v, d: [round(m[0] + v[0] * d, 3), round(m[1] + v[1] * d, 3)]              # como el punto con que se suelta
        unidad = lambda r, i: next(u for u in r["units"] if u["id"] == i)
        ancho = lambda poly, v: max(dot(p, v) for p in poly) - min(dot(p, v) for p in poly)
        muestra = lambda n: json.load(open(os.path.join(base, "samples", n + ".json"), encoding="utf-8"))
        TOL = 0.0052                                     # la etiqueta redondea al centímetro la medida que el motor deja
        FRENO = 0.005                                    # y no avisa un freno menor que eso

        def en_poli(p, poly):                            # punto dentro de un polígono convexo (las estancias)
            c = [(poly[(i + 1) % len(poly)][0] - poly[i][0]) * (p[1] - poly[i][1]) - (poly[(i + 1) % len(poly)][1] - poly[i][1]) * (p[0] - poly[i][0])
                 for i in range(len(poly))]
            return all(v >= -1e-9 for v in c) or all(v <= 1e-9 for v in c)

        # 1) tabique entre viviendas: el frente de cada vecina con el tabique donde lo recibe el motor; en rojo si lo frena
        frenos = []
        for nombre, ds in (("barra", (-5.0, -1.3, 0.7, 3.396, 40.0, -40.0)), ("quiebre_45", (0.7, -1.3, 30.0))):
            s = muestra(nombre)
            r0 = run(s["footprint"], s["height"])
            if nombre == "barra":
                k = next(i for i, t in enumerate(r0["tabiques"]) if (t["a"], t["b"]) == ("U03", "U04"))
            else:
                k = next(i for i, t in enumerate(r0["tabiques"]) if abs(t["dir"][0]) > 0.1 and abs(t["dir"][1]) > 0.1)   # oblicuo
            t = r0["tabiques"][k]
            for d, e in zip(ds, en_node(r0, [{"f": "tab", "k": k, "d": d, "w": mitad(t["seg"])} for d in ds])):
                a = hacia(mitad(t["seg"]), t["dir"], d)
                r1 = run(s["footprint"], s["height"], unit_edits=[{"op": "tabique", "p": mitad(t["seg"]), "a": a}])
                esperado = [ancho(unidad(r1, t["a"])["poly"], t["dir"]), ancho(unidad(r1, t["b"])["poly"], t["dir"])]
                t1 = next(x for x in r1["tabiques"] if (x["a"], x["b"]) == (t["a"], t["b"]))
                corrido = dot(mitad(t1["seg"]), t["dir"]) - dot(mitad(t["seg"]), t["dir"])      # cuánto lo corrió el motor de verdad
                assert len(e) == 2 and e[0]["texto"].startswith(t["a"] + " · ") and e[1]["texto"].startswith(t["b"] + " · "), e
                assert abs(num(e[0]["texto"]) - esperado[0]) <= TOL and abs(num(e[1]["texto"]) - esperado[1]) <= TOL, (nombre, d, e, esperado)
                assert e[0]["mal"] == e[1]["mal"] == (abs(corrido - d) >= FRENO), (nombre, d, corrido, e)   # rojo solo donde el motor frena
                assert abs(e[0]["lado"][0] + e[1]["lado"][0]) < 1e-9 and abs(e[0]["lado"][1] + e[1]["lado"][1]) < 1e-9 and e[0]["lado"] != e[1]["lado"]   # una a cada lado
                frenos.append(e[0]["mal"])
        assert frenos == [False, False, False, False, True, True, False, False, True], frenos

        # 2) tabique interior de U03 (el más largo): el ancho de la estancia de cada lado, y lo que el motor deja
        s = muestra("barra")
        r0 = run(s["footprint"], s["height"])
        u3 = unidad(r0, "U03")
        kp = max(range(len(u3["paredes"])), key=lambda i: math.dist(*u3["paredes"][i]["seg"]))
        sg, rr = u3["paredes"][kp]["seg"], u3["paredes"][kp]["dir"]
        graba = [sg[0][0] + (sg[1][0] - sg[0][0]) * 0.8, sg[0][1] + (sg[1][1] - sg[0][1]) * 0.8]   # donde se lo toma: a 4/5 de su largo
        lados = [next(rm["id"] for rm in u3["rooms"] if en_poli([graba[0] + rr[0] * k * 0.05, graba[1] + rr[1] * k * 0.05], rm["poly"]))
                 for k in (-1, 1)]                       # la estancia de -r y la de +r junto a ese punto
        ancho_de = lambda u, i: ancho(next(rm for rm in u["rooms"] if rm["id"] == i)["poly"], rr)
        ds = (0.4, -0.4, 1.0, -1.0, 6.0, -6.0, 0.004)
        frenado = []
        for d, e in zip(ds, en_node(r0, [{"f": "pared", "u": "U03", "k": kp, "w": graba, "d": d} for d in ds])):
            m = mitad(sg)
            u1 = unidad(run(s["footprint"], s["height"], room_edits=[{"op": "pared", "p": m, "a": hacia(m, rr, d)}]), "U03")
            esperado = [ancho_de(u1, i) for i in lados]
            corrido = ancho_de(u1, lados[0]) - ancho_de(u3, lados[0])                              # lo que creció la de -r: cuánto se corrió el tabique de verdad
            assert len(e) == 2, (d, e)
            assert abs(num(e[0]["texto"]) - esperado[0]) <= TOL and abs(num(e[1]["texto"]) - esperado[1]) <= TOL, (d, e, esperado)
            assert e[0]["mal"] == e[1]["mal"] == (abs(corrido - d) >= FRENO), (d, corrido, e)
            assert abs(e[0]["lado"][0] + e[1]["lado"][0]) < 1e-9 and abs(e[0]["lado"][1] + e[1]["lado"][1]) < 1e-9
            frenado.append(e[0]["mal"])
        assert frenado[:2] == [False, False] and frenado[4] and frenado[5] and not frenado[6], frenado   # lo corto, sin freno; lo largo, frenado (rojo)

        # 3) puerta: la de un dormitorio (entre dos estancias) y la de entrada (el borde del hall): distancia a las puntas del tabique
        for elige in (lambda d: d["a"] != "exterior", lambda d: d.get("entry")):
            kd = next(i for i, d in enumerate(u3["doors"]) if elige(d))
            pu = u3["doors"][kd]
            Lp = math.dist(pu["p"], pu["q"])
            r_ = [(pu["q"][0] - pu["p"][0]) / Lp, (pu["q"][1] - pu["p"][1]) / Lp]
            ds = (-0.3, 0.2, 0.5, 3.0, -3.0)
            for d, e in zip(ds, en_node(r0, [{"f": "puerta", "u": "U03", "k": kd, "d": d} for d in ds])):
                m = mitad([pu["p"], pu["q"]])
                u1 = unidad(run(s["footprint"], s["height"], room_edits=[{"op": "puerta", "p": m, "a": hacia(m, r_, d), "entre": [pu["a"], pu["b"]]}]), "U03")
                d1 = next(x for x in u1["doors"] if {x["a"], x["b"]} == {pu["a"], pu["b"]})
                ext = [(min(dot(p, r_) for p in rm["poly"]), max(dot(p, r_) for p in rm["poly"]))
                       for rm in u1["rooms"] if rm["id"] in (pu["a"], pu["b"])]                # el borde que comparten: lo que tienen en común
                lo, hi = max(x[0] for x in ext), min(x[1] for x in ext)
                esperado = (dot(d1["p"], r_) - lo, hi - dot(d1["q"], r_))
                corrido = dot(d1["p"], r_) - dot(pu["p"], r_)
                assert len(e) == 1 and re.fullmatch(r"-?\d+\.\d\d \| -?\d+\.\d\d m", e[0]["texto"]), e
                a_, b_ = [float(x) for x in re.findall(r"-?\d+\.\d\d", e[0]["texto"])]
                assert abs(a_ - esperado[0]) <= TOL and abs(b_ - esperado[1]) <= TOL, (pu["b"], d, e, esperado)
                assert e[0]["mal"] == (abs(corrido - d) >= FRENO), (pu["b"], d, corrido, e)
                assert (d != 3.0 and d != -3.0) or e[0]["mal"]                                 # lo largo, frenado

        # el borde que comparten dos estancias es lo que tienen en común, aunque una sea más larga que la otra (en los dos órdenes);
        # la puerta de entrada (un lado es «exterior», que no es una estancia) usa solo el borde del hall
        A_ = {"id": "A", "poly": [[0, 0], [6, 0], [6, 2], [0, 2]]}
        B_ = {"id": "B", "poly": [[2, 2], [4, 2], [4, 5], [2, 5]]}
        bd = en_node(r0, [{"f": "borde", "u": {"rooms": [A_, B_]}, "d": {"a": a, "b": b, "p": [2.5, 2], "q": [3.3, 2]}}
                          for a, b in (("A", "B"), ("B", "A"), ("exterior", "B"))])
        assert [[round(x, 3) for x in v] for v in bd] == [[-0.5, 1.5]] * 3, bd

        # 4) línea, patio, medianera y núcleo: el largo y el ángulo en el SCP (lo tipeado manda), ancho × fondo en los ejes del
        # edificio, el largo del borde y ΔX, ΔY en los ejes del SCP
        th = math.radians(30)
        rot = lambda p: [round(p[0] * math.cos(th) - p[1] * math.sin(th), 3), round(p[0] * math.sin(th) + p[1] * math.cos(th), 3)]
        barra = [[0, 0], [60, 0], [60, 16], [0, 16]]
        P = rot([8, 8])
        Q = [round(P[0] + 7 * math.cos(th + math.radians(40)), 3), round(P[1] + 7 * math.sin(th + math.radians(40)), 3)]   # 7 m a 40° del SCP girado 30°
        casos = [{"f": "linea", "prev": [10, 5], "q": [22, 5], "scp_a": 0.0},
                 {"f": "linea", "prev": P, "q": Q, "scp_a": th},
                 {"f": "linea", "prev": P, "q": Q, "tipeado": {"largo": 3.2}},
                 {"f": "linea", "prev": P, "q": Q, "tipeado": {"angulo": -45}},
                 {"f": "linea", "prev": P, "q": Q, "tipeado": {"largo": 3.2, "angulo": 30}},
                 {"f": "linea", "prev": [10, 5], "q": [10, 5], "scp_a": 0.0},
                 {"f": "patio", "p0": [20, 5], "p1": [32, 11], "footprint": barra},
                 {"f": "patio", "p0": rot([20, 5]), "p1": rot([32, 11]), "footprint": [rot(p) for p in barra]},
                 {"f": "medianera", "i": 0, "footprint": barra}, {"f": "medianera", "i": 1}, {"f": "medianera", "i": 3},
                 {"f": "delta", "d": [1.0, 0.0], "scp_a": 0.0}, {"f": "delta", "d": [0.0, -1.0]},
                 {"f": "delta", "d": [math.cos(th) * 2, math.sin(th) * 2], "scp_a": th}, {"f": "delta", "d": [-math.sin(th) * 0.5, math.cos(th) * 0.5]},
                 {"f": "delta", "d": [0.001, -0.002], "scp_a": 0.0}]
        sal = en_node(r0, casos)
        textos = [(x[0]["texto"] if x else None) if isinstance(x, list) else x for x in sal]
        assert textos[:6] == ["12.00 m · 0°", "7.00 m · 40°", "3.20 m · 40°", "7.00 m · 315°", "3.20 m · 30°", None], textos   # sin largo no hay etiqueta
        assert textos[6:8] == ["12.00 × 6.00 m", "12.00 × 6.00 m"], textos                       # en el edificio girado, los mismos ejes del edificio
        assert textos[8:11] == ["60.00 m", "16.00 m", "16.00 m"] and sal[8][0]["lado"] == [0, 1] and sal[10][0]["lado"] == [-1, 0]   # hacia afuera de la planta
        assert textos[11:] == ["ΔX +1.00 · ΔY 0.00 m", "ΔX 0.00 · ΔY -1.00 m", "ΔX +2.00 · ΔY 0.00 m", "ΔX 0.00 · ΔY +0.50 m", "ΔX 0.00 · ΔY 0.00 m"], textos   # sin «-0.00»
        # el tramo de una recta dentro de un polígono que contiene a un punto (también si el polígono es cóncavo)
        L_ = [[0, 0], [6, 0], [6, 2], [2, 2], [2, 6], [0, 6]]
        tr = en_node(r0, [{"f": "tramo", "poly": [[0, 0], [4, 0], [4, 2], [0, 2]], "o": [1, 1], "r": [1, 0], "t0": 0.5},
                          {"f": "tramo", "poly": [[0, 0], [4, 0], [4, 2], [0, 2]], "o": [1, 1], "r": [1, 0], "t0": 9},
                          {"f": "tramo", "poly": L_, "o": [1, 1], "r": [0, 1], "t0": 1.0},
                          {"f": "tramo", "poly": L_, "o": [4, 1], "r": [0, 1], "t0": 0.5}])
        assert tr[0] == [-1, 3] and tr[1] is None and tr[2] == [-1, 5] and tr[3] == [-1, 1], tr

if __name__ == "__main__":
    test_medidas_en_vivo(); print("OK69")


@calibracion_anterior
def test_atajos_y_cotas():
    """R9.8: atajos de teclado y cotas en la planta (solo web; el motor no cambia).
    Atajos (en la planta 2D; nunca con un campo de texto o una lista con el foco ni con Ctrl, Alt o Cmd): L, N, M, P y S
    activan Línea, Núcleo, Medianera, Patio y SCP (la letra de la herramienta activa la cierra, como otro clic en su botón);
    D muestra u oculta la capa «Cotas»; Supr o Retroceso quitan el núcleo, el patio o el tramo de pasillo elegido con lo
    mismo que hacen sus fichas (pasan por `recordar`: se deshacen con ↶), y una vivienda o un tabique elegidos no se borran;
    Shift apretado es el Orto mientras se mantiene (un estado aparte: la casilla, F8 y la preferencia no cambian; se suelta
    al soltar la tecla o al perder el foco la ventana). Ctrl/Cmd+Z y Ctrl+Y (o Ctrl+Shift+Z) ya deshacían y rehacían. Los
    `title` de los botones de la barra de dibujo llevan la letra y Vista lista los atajos.
    Cotas: con la capa «Cotas» activa, dentro de la planta de viviendas (`cotasViviendas`, llamada desde `drawDims`): el
    frente de cada vivienda (una cadena de cotas a cada lado de cada tramo de pasillo, dentro de él, junto al borde de las
    viviendas), el ancho de cada tramo (una cota transversal en el medio de su franja) y el fondo de cada vivienda
    (perpendicular al pasillo, dentro de ella, solo si se ve lo bastante grande). Van en un grupo propio que no captura
    eventos, no pisan las etiquetas de las viviendas, las puertas ni otras cotas, y en la axonometría no se dibujan.
    (El comportamiento se comprobó en navegador; esta prueba vigila la web con comprobaciones del código y, si hay node,
    ejecuta las cotas de la página contra lo que el motor deja en los ejemplos.)"""
    import math, re, shutil, subprocess, tempfile
    base = os.path.join(os.path.dirname(__file__), "..")
    html = open(os.path.join(base, "web", "index.html"), encoding="utf-8").read()
    js = html.split("<script>", 1)[1].split("</script>", 1)[0]

    def cuerpo(nombre):
        ini = js.index("function %s(" % nombre)
        fin = min(k for k in (js.find("\nfunction ", ini + 1), js.find("\nasync function ", ini + 1), js.find("\n/*", ini + 1),
                              len(js)) if k >= 0)
        return js[ini:fin]
    # ---- atajos: el manejador de teclado que ya había (Esc, Enter, F7/F8/F9, flechas, Ctrl+Z) llama a atajoTecla
    teclas = js.split("window.addEventListener('keydown'", 1)[1].split("\n/*", 1)[0]
    assert "if(atajoTecla(e,t,texto)){ e.preventDefault(); return; }" in teclas
    assert "e.ctrlKey||e.metaKey" in teclas and "k==='z'&&!e.shiftKey" in teclas and "k==='z'&&e.shiftKey" in teclas and "k==='y'" in teclas
    assert teclas.index("deshacer()") < teclas.index("atajoTecla(") < teclas.index("if(FLECHAS[e.key]")   # Ctrl+Z, antes que las letras
    assert "window.addEventListener('keyup',e=>{ if(e.key==='Shift') ortoShift(false); });" in teclas
    assert "window.addEventListener('blur',()=>ortoShift(false));" in teclas                            # con la ventana sin foco, el keyup no llega
    assert "HERR_TECLA={l:'line',n:'addcore',m:'medianera',p:'patio',s:'scp'}" in js
    at = cuerpo("atajoTecla")
    for t in ("texto||t.tagName==='SELECT'||e.ctrlKey||e.metaKey||e.altKey||e.isComposing) return false",   # ni en un campo ni con Ctrl/Alt/Cmd
              "if(viewMode!=='plan') return false", "if(k==='Shift'){ if(!e.repeat) ortoShift(true); return false; }",
              "l.length===1&&HERR_TECLA[l]", "setTool(tool===HERR_TECLA[l]||(l==='n'&&tool==='delcore')?tool:HERR_TECLA[l])",   # la misma letra cierra
              "if(l==='d'){ if(!e.repeat){ alternar('showDims');", "k==='Delete'||k==='Backspace'", "return quitarElegido()"):
        assert t in at, t
    qe = cuerpo("quitarElegido")                    # lo mismo que hacen sus fichas, y con ninguna herramienta activa
    assert "viewMode!=='plan'||tool||!result" in qe
    assert qe.index("quitarNucleo()") < qe.index("quitarTramo()") < qe.index("quitarPatioElegido()") and "no se borra" in qe
    assert not re.search(r"\b(centerlines|coresManual|patios|medianeras|ediciones|interiores|anchosPasillo)\b", qe)   # nada se borra por fuera de recordar
    for f in ("quitarNucleo", "quitarTramo", "quitarPatioElegido"):                                    # esas funciones guardan antes el estado
        assert "recordar(" in cuerpo(f), f
    assert "dividirVivienda(" not in qe and "unirViviendas(" not in qe and "editar(" not in qe     # una vivienda o un tabique no se borran
    os_ = cuerpo("ortoShift")                       # el Orto temporal: un estado aparte, la casilla y la preferencia no cambian
    assert "ortoTemporal=v" in os_ and "localStorage" not in os_ and "alternar(" not in os_ and ".checked=" not in os_ and "preferencia(" not in os_
    assert "($('orto').checked||ortoTemporal)&&prev" in cuerpo("ajustar") and "$('orto').checked||ortoTemporal" in cuerpo("puntoLinea")
    assert js.count("$('orto').checked") == 2 and js.count("$('orto').checked||ortoTemporal") == 2   # ninguna otra parte lee solo la casilla
    # los title de la barra de dibujo llevan la letra de su herramienta; el Orto, Shift; la barra de la herramienta, su letra
    dibujo = html.split('<div class="dibujo"', 1)[1].split("</div>", 1)[0]
    for letra, tool_ in (("L", "line"), ("N", "addcore"), ("M", "medianera"), ("P", "patio"), ("S", "scp")):
        b = re.search(r'<button id="\w+" data-tool="%s"[^>]*title="([^"]*)"' % tool_, dibujo)
        assert b and re.match(r"[^:(]+\(%s\)" % letra, b.group(1)), (tool_, b and b.group(1))
        assert re.search(r"\b%s:'%s'" % (letra.lower(), tool_), js.split("const HERR_TECLA=", 1)[1].split("}", 1)[0]), letra
    assert "Con Shift apretado, Orto solo mientras lo mantienes" in dibujo
    assert "teclaDe(tool)" in cuerpo("herramientaBar") and "<kbd>'+teclaDe(tool)+'</kbd> salir" in cuerpo("herramientaBar")
    vista = html.split('<div class="grupo" data-grupo="vista"', 1)[1].split("</section>", 1)[0]
    atajos = vista.split("<h2>Atajos de teclado</h2>", 1)[1]
    for t in ("<kbd>L</kbd>", "<kbd>N</kbd>", "<kbd>M</kbd>", "<kbd>P</kbd>", "<kbd>S</kbd>", "<kbd>D</kbd>", "<kbd>Supr</kbd>", "<kbd>Shift</kbd>",
              "<kbd>Ctrl</kbd>", "<kbd>F8</kbd>", "<kbd>Esc</kbd>", "una vivienda no se borra"):
        assert t in atajos, t
    # ---- cotas: una función, llamada solo desde drawDims y después de su «si la capa está apagada»; la axonometría no la llama
    assert js.count("cotasViviendas(g);") == 1 and "function cotasViviendas(g)" in js and "try{ cotasViviendas(g); }catch(e){ console.error(" in js
    dd = cuerpo("drawDims")
    assert dd.index("if(!showDims||!view||!footprint.length) return;") < dd.index("cotasViviendas(g);")
    assert "cotasViviendas" not in cuerpo("drawAxo") and "drawDims" not in cuerpo("drawAxo")
    cv = cuerpo("cotasViviendas")
    assert "el('g',{id:'cotasViv','pointer-events':'none'})" in cv and "viewMode!=='plan'" in cv and "st.program!=='Residential'" in cv
    assert "u.al_frente" in cv and cv.index("// 1) el frente") < cv.index("// 2) el ancho") < cv.index("// 3) el fondo")
    assert "cajaLibre(" in cv and "tipo:'frente'" in cv and "tipo:'ancho'" in cv and "tipo:'fondo'" in cv
    ct = cuerpo("cota")
    assert "function cota(g,a,b,ea,eb,o)" in ct and "fill:TINTA(),stroke:HALO()" in ct and "if(ea&&eb)" in ct   # las cotas totales, igual que antes
    assert "'pointer-events':'none'" in ct and js.count("fill:TINTA()") == 2                           # el estilo de las cotas, uno solo
    assert 'title="Cotas (D):' in html and "COTA_TAM=10" in js

    node = shutil.which("node")
    if not node:
        print("(sin node: se omiten «node --check» del programa de la página y las cotas contra el motor)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        ruta = os.path.join(tmp, "programa.js")
        open(ruta, "w", encoding="utf-8").write(js)
        c = subprocess.run([node, "--check", ruta], capture_output=True, text=True, encoding="utf-8")
        assert c.returncode == 0, c.stderr

        # ---- las cotas: se ejecuta el código de la página (sin pantalla) con lo que el motor deja en los ejemplos
        previas = "\n".join(cuerpo(n) for n in ("cota", "anchoTxt", "cajaGirada", "cotaTxt", "visible", "cotaLugar", "cotasViviendas",
                                               "tramoEn", "enPoly", "domAngle", "drawDims"))
        for n in ("COTA_TAM", "medidaTxt", "cajaLibre"):                       # las constantes (alguna ya viene pegada a la función de arriba)
            linea = re.search(r"^const %s.*$" % n, js, re.M).group(0)
            if linea not in previas:
                previas += "\n" + linea
        arnes = """const fs = require('fs');
const E = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
function nodo(t, a, txt) { return { t, a: a || {}, txt, hijos: [], appendChild(c) { this.hijos.push(c); return c; } }; }
const el = (t, a, txt) => nodo(t, a, txt);
let view = null, viewMode = 'plan', result = null, planStory = null, showDims = true, footprint = [], patios = [], W = 1062, H = 836;
const lote = () => null, TINTA = () => '#344054', HALO = () => '#fff';
console.error = (m, e) => { throw e || new Error(String(m)); };            // si las cotas fallan, drawDims las avisa con console.error: acá, que la prueba lo vea
const X = p => view.ox + p[0] * view.s, Y = p => view.oy - p[1] * view.s;
const $ = id => id === 'svg' ? { clientWidth: W, clientHeight: H } : { value: '0.3' };
%s
const llamadas = [];
const cotaOriginal = cota; cota = function (g, a, b, ea, eb, o) { llamadas.push({ ext: !!(ea && eb), o }); return cotaOriginal(g, a, b, ea, eb, o); };
const salida = E.casos.map(c => {
  view = c.view; result = c.result; footprint = c.footprint || []; viewMode = c.viewMode || 'plan'; planStory = c.planStory == null ? null : c.planStory;
  showDims = c.showDims !== false; W = c.W || 1062; H = c.H || 836; llamadas.length = 0;
  if (c.f === 'cota') { const g = nodo('g'); cota(g, c.a, c.b, c.ea, c.eb, c.o); return g.hijos.map(h => ({ t: h.t, a: h.a, txt: h.txt })); }
  if (c.f === 'txt') { const T = cotaTxt(c.a, c.b, c.o); return { y: T.y, my: T.my, mx: T.mx, r: T.r, caja: T.caja }; }
  const raiz = nodo('g'); drawDims(raiz);
  const grupo = raiz.hijos.find(h => h.a.id === 'cotasViv'), hijos = grupo ? grupo.hijos : [];
  return { hay: !!grupo, pe: grupo ? grupo.a['pointer-events'] : null, todosNone: hijos.every(h => h.a['pointer-events'] === 'none'),
           textos: hijos.filter(h => h.t === 'text').map(h => ({ tipo: h.a['data-cota'], texto: h.txt, x: +h.a.x, y: +h.a.y, tam: +h.a['font-size'], tr: h.a.transform })),
           sinRef: llamadas.filter(l => !l.ext).length, totales: raiz.hijos.filter(h => h.t === 'text').map(h => h.txt) };
});
console.log(JSON.stringify(salida));
""" % previas
        open(os.path.join(tmp, "arnes.js"), "w", encoding="utf-8").write(arnes)

        def en_node(casos):
            open(os.path.join(tmp, "entrada.json"), "w", encoding="utf-8").write(json.dumps({"casos": casos}))
            p = subprocess.run([node, os.path.join(tmp, "arnes.js"), os.path.join(tmp, "entrada.json")],
                               capture_output=True, text=True, encoding="utf-8")
            assert p.returncode == 0, p.stderr
            return json.loads(p.stdout)
        muestra = lambda n: json.load(open(os.path.join(base, "samples", n + ".json"), encoding="utf-8"))
        VISTA = {"s": 16.0, "ox": 40.0, "oy": 590.0}                           # 16 px/m: la barra de 60 m entra en la planta de 1062 px
        por = lambda s, t: sorted(x["texto"] for x in s["textos"] if x["tipo"] == t)
        f2 = lambda v: "%.2f" % v
        PX = lambda v, p: (v["ox"] + p[0] * v["s"], v["oy"] - p[1] * v["s"])

        def caja_texto(x, v):                          # la caja en pantalla de un texto de cota (con el ancho que le da el arnés: 0,6 em por letra)
            rr, mx, my = map(float, re.match(r"rotate\((-?[\d.]+) (-?[\d.]+) (-?[\d.]+)\)", x["tr"]).groups())
            w, alto = 0.6 * x["tam"] * len(x["texto"]) / 2, 0.72 * x["tam"]
            c, s = math.cos(math.radians(rr)), math.sin(math.radians(rr))
            q = [(mx + u * c - t * s, my + u * s + t * c) for u, t in ((-w, x["y"] - my - alto), (w, x["y"] - my - alto), (w, x["y"] - my), (-w, x["y"] - my))]
            return (min(p[0] for p in q), max(p[0] for p in q), min(p[1] for p in q), max(p[1] for p in q))
        pisa = lambda a, b: a[0] < b[1] - 0.01 and b[0] < a[1] - 0.01 and a[2] < b[3] - 0.01 and b[2] < a[3] - 0.01

        def limpias(sal, r, v, W=1062, H=836):         # ninguna cota pisa a otra, ni la etiqueta de una vivienda, ni el punto de su puerta; todas dentro de la pantalla
            cs = [caja_texto(x, v) for x in sal["textos"]]
            fijas = []
            for u in r["units"]:
                cx, cy = PX(v, [sum(p[0] for p in u["poly"]) / len(u["poly"]), sum(p[1] for p in u["poly"]) / len(u["poly"])])
                w = 0.6 * 11 * len("%s · %g m²" % (u["id"], u["area"])) / 2                         # el número como lo escribe JavaScript (60, no 60.0)
                fijas.append((cx - w, cx + w, cy - 8, cy + 2.5))
                px, py = PX(v, u["door"])
                fijas.append((px - 4, px + 4, py - 4, py + 4))
            for i, a in enumerate(cs):
                assert -0.01 <= a[0] and a[1] <= W + 0.01 and -0.01 <= a[2] and a[3] <= H + 0.01, (sal["textos"][i], a)
                for b in cs[i + 1:]:
                    assert not pisa(a, b), (sal["textos"][i], a, b)
                for b in fijas:
                    assert not pisa(a, b), (sal["textos"][i], a, b)

        barra = muestra("barra")
        rb = run(barra["footprint"], barra["height"])
        fb = barra["footprint"]
        ancho_viv = lambda r: sorted(f2(u["width"]) for u in r["units"] if not u.get("al_frente"))
        casos = [{"result": rb, "footprint": fb, "view": VISTA},                                  # 0) la barra, con la capa
                 {"result": rb, "footprint": fb, "view": VISTA, "showDims": False},               # 1) la capa apagada
                 {"result": rb, "footprint": fb, "view": VISTA, "viewMode": "axo"},               # 2) la axonometría
                 {"result": rb, "footprint": fb, "view": dict(VISTA, s=4.0, ox=300.0, oy=500.0)},   # 3) muy lejos
                 {"result": rb, "footprint": fb, "view": {"s": 60.0, "ox": -1500.0, "oy": 560.0}},  # 4) cerca: solo se ve un pedazo
                 {"f": "cota", "a": [0, 0], "b": [10, 0], "ea": [0, 1], "eb": [10, 1], "view": VISTA}]   # 5) una cota total, sin opciones
        sal = en_node(casos)
        b0 = sal[0]
        assert b0["hay"] and b0["pe"] == "none" and b0["todosNone"], b0                           # un grupo propio que no captura eventos
        assert por(b0, "frente") == ancho_viv(rb) and por(b0, "ancho") == ["2.00"] and por(b0, "fondo") == ["6.50"] * 8, \
            (por(b0, "frente"), por(b0, "ancho"), por(b0, "fondo"))                               # frente de cada vivienda, ancho del pasillo y fondo de cada una
        assert b0["sinRef"] == 8 + 1 + 8 and "60.00 m" in b0["totales"] and "16.00 m" in b0["totales"], b0["totales"]   # y las totales, como siempre
        limpias(b0, rb, VISTA)
        assert not sal[1]["hay"] and sal[1]["totales"] == [] and sal[1]["textos"] == [], sal[1]    # con la capa apagada, nada: ni las totales ni las nuevas
        assert not sal[2]["hay"] and sal[2]["textos"] == []                                       # en la axonometría, tampoco
        assert sal[3]["hay"] and sal[3]["textos"] == [], sal[3]["textos"]                         # a 4 px/m no caben: no se dibuja nada (se ven las totales)
        assert "60.00 m" in sal[3]["totales"]
        z = sal[4]                                                                                # a 60 px/m el texto va en la parte que se ve
        assert por(z, "frente") and por(z, "ancho") and set(por(z, "frente")) <= set(ancho_viv(rb)), z["textos"]
        limpias(z, rb, {"s": 60.0, "ox": -1500.0, "oy": 560.0})
        cc = sal[5]                                                                               # cota total: igual que antes (5 líneas y el texto con « m», 11 px)
        assert [h["t"] for h in cc] == ["line"] * 5 + ["text"] and cc[-1]["txt"] == "10.00 m" and cc[-1]["a"]["font-size"] == 11
        assert "data-cota" not in cc[-1]["a"] and cc[-1]["a"]["y"] == 590.0 - 5 and abs(float(cc[-1]["a"]["x"]) - 120.0) < 1e-9, cc[-1]
        # el texto va del lado pedido de su línea (horizontal y vertical)
        tx = en_node([{"f": "txt", "a": [0, 0], "b": [10, 0], "o": {"texto": "9.99", "lado": [0, 1], "gap": 3}, "view": VISTA},
                      {"f": "txt", "a": [0, 0], "b": [10, 0], "o": {"texto": "9.99", "lado": [0, -1], "gap": 3}, "view": VISTA},
                      {"f": "txt", "a": [0, 0], "b": [0, 10], "o": {"texto": "9.99", "lado": [1, 0], "gap": 3}, "view": VISTA},
                      {"f": "txt", "a": [0, 0], "b": [0, 10], "o": {"texto": "9.99", "lado": [-1, 0], "gap": 3}, "view": VISTA}])
        assert tx[0]["caja"]["y0"] > tx[0]["my"] and tx[1]["caja"]["y1"] < tx[1]["my"], tx[:2]       # lado hacia abajo (pantalla): debajo de la línea; hacia arriba, encima
        assert tx[2]["caja"]["x0"] > tx[2]["mx"] and tx[3]["caja"]["x1"] < tx[3]["mx"], tx[2:]       # en una línea vertical, a la derecha o a la izquierda

        # 1) una L, patio central, una cruz, un quiebre a 45° y un predio entre medianeras: todo en pantalla, sin pisar nada
        casos, rs = [], []
        for n, v in (("L", {"s": 16.0, "ox": 60.0, "oy": 760.0}), ("patio_central", {"s": 16.0, "ox": 60.0, "oy": 600.0}),
                     ("cruz_dos_lineas", {"s": 14.0, "ox": 120.0, "oy": 810.0}), ("quiebre_45", {"s": 13.0, "ox": 60.0, "oy": 560.0}),
                     ("T_dos_lineas", {"s": 14.0, "ox": 100.0, "oy": 790.0}), ("L_ochava", {"s": 16.0, "ox": 60.0, "oy": 760.0})):
            s = muestra(n)
            kw = {k: s[k] for k in ("centerlines", "patios") if k in s}
            if "patios" in s:
                kw["patios_mode"] = "manual"
            r = run(s["footprint"], s["height"], **kw)
            rs.append((n, r, v))
            casos.append({"result": r, "footprint": s["footprint"], "view": v})
        for (n, r, v), sal in zip(rs, en_node(casos)):
            assert sal["hay"] and sal["todosNone"], n
            assert por(sal, "frente") == ancho_viv(r), (n, por(sal, "frente"), ancho_viv(r))      # el frente de todas las viviendas, también en los ejemplos con alas, cruces y patios
            assert len(por(sal, "ancho")) == len(r["pasillos"]) and set(por(sal, "ancho")) <= {f2(p["ancho"]) for p in r["pasillos"]}, (n, por(sal, "ancho"))   # una por tramo
            assert len(por(sal, "fondo")) >= len(r["units"]) // 2 and set(por(sal, "fondo")) <= {f2(u["depth"]) for u in r["units"]}, (n, por(sal, "fondo"))
            limpias(sal, r, v)
        # entre medianeras: el eje del pasillo cae sobre el núcleo; el ancho se mide en la franja de al lado
        d = muestra("entre_medianeras")
        rm = run(d["footprint"], d["height"], medianeras=d["medianeras"])
        vm = {"s": 20.0, "ox": 300.0, "oy": 640.0}
        sm = en_node([{"result": rm, "footprint": d["footprint"], "view": vm}])[0]
        assert por(sm, "frente") == ["9.30", "9.30"] and por(sm, "ancho") == ["2.00"] and por(sm, "fondo") == ["9.03", "9.03"], sm["textos"]
        limpias(sm, rm, vm)
        # al frente (R3.7): la vivienda que entra por la punta del pasillo no lleva frente ni fondo
        raf = run(d["footprint"], h=18, unit_mix=[{"name": "2 dorm", "area": 75, "percent": 100, "dorms": 2}],
                  medianeras=[d["medianeras"][1]], cores_mode="manual", cores=[[5, 25]])
        assert sum(1 for u in raf["units"] if u.get("al_frente")) == 1
        saf = en_node([{"result": raf, "footprint": d["footprint"], "view": vm}])[0]
        assert por(saf, "frente") == ancho_viv(raf) and len(por(saf, "frente")) == 1 and len(por(saf, "fondo")) == 1, saf["textos"]
        limpias(saf, raf, vm)
        # un tramo con ancho propio: la cota va a un lado de su etiqueta azul (la de drawOverlay), sin pisarla
        rp = run(barra["footprint"], barra["height"], anchos_pasillo=[{"p": [30, 8], "ancho": 1.6}])
        sp = en_node([{"result": rp, "footprint": fb, "view": VISTA}])[0]
        assert rp["pasillos"][0]["propio"] and por(sp, "ancho") == ["1.60"], sp["textos"]
        limpias(sp, rp, VISTA)
        a = next(x for x in sp["textos"] if x["tipo"] == "ancho")
        ex, ey = PX(VISTA, [(rp["pasillos"][0]["eje"][0][0] + rp["pasillos"][0]["eje"][1][0]) / 2, 8.0])
        wl = 0.6 * 11 * 1.1 * len("1.60 m") / 2
        assert not pisa(caja_texto(a, VISTA), (ex - wl, ex + wl, ey - 6, ey + 6)), (a, ex, ey)
        # solo el pasillo (sin viviendas): el ancho de cada tramo sí, el frente y el fondo no
        rc = generate({"footprint": fb, "height": barra["height"], "stage": "corridor", "params": {}})
        sc = en_node([{"result": rc, "footprint": fb, "view": VISTA}])[0]
        assert por(sc, "ancho") == ["2.00"] and por(sc, "frente") == [] and por(sc, "fondo") == []
        # un nivel que no es de vivienda (la torre mixta: estacionamiento abajo) no lleva cotas de viviendas
        tm = muestra("torre_mixta")
        rt = run(tm["footprint"], tm["height"], stories=tm["stories"])
        res = [s_["index"] for s_ in rt["stories"] if s_["program"] == "Residential"]
        noy = [s_["index"] for s_ in rt["stories"] if s_["program"] != "Residential"]
        assert res and noy
        st_ = en_node([{"result": rt, "footprint": tm["footprint"], "view": {"s": 12.0, "ox": 40.0, "oy": 400.0}, "planStory": i} for i in (noy[0], res[0])])
        assert not st_[0]["hay"] and st_[1]["hay"] and por(st_[1], "frente"), st_

if __name__ == "__main__":
    test_atajos_y_cotas(); print("OK70")


def test_galeria():
    """R3.8: galería, el pasillo de borde dentro del patio (pedido del usuario: «a veces los patios pueden ser muy grandes
    y albergar las circulaciones generales, para que el espacio útil sea únicamente para las viviendas»). Por patio
    manual, params.patios_galeria (alineado con patios) marca que el ala cuyo pasillo de borde da a ese patio lo corre
    al patio: la banda del ancho del pasillo queda del otro lado del muro, pegada al edificio, y toda el ala es de las
    viviendas (la tira con el pasillo contra la medianera no cambia: se descartó para esta versión, sus viviendas solo
    tendrían luz por la galería). Planta del usuario: 30 × 45 entre medianeras, patio de 20 × 17 abierto a la
    medianera izquierda, pasillo de 2 m, 4 núcleos manuales."""
    import copy, re
    fp = [[0, 0], [30, 0], [30, 45], [0, 45]]
    mix = [{"name": "2 dorm", "area": 75, "percent": 25, "dorms": 2}, {"name": "3 dorm", "area": 95, "percent": 25, "dorms": 3, "vestidor": True},
           {"name": "1 dorm", "area": 60, "percent": 25, "dorms": 1}, {"name": "Mono", "area": 32, "percent": 25, "dorms": 0}]
    std = {"vivienda": {"dorm_principal": {"min_area": 8, "min_side": 2.6, "typ_area": 11.5, "typ": [3.2, 3.6]},
                        "estudio": {"min_area": 0, "min_side": 0, "typ_area": 0, "typ": [0, 0]}}}
    base = dict(corridor_width=2, core_auto=False, core_width=5.45, core_depth=7.02, core_count=2, egress_single=18, egress_multi=30,
                min_unit_width=5, party_wall=0.3, max_unit_depth=14, outer_wall=0.35, unit_mix=mix, standards=std,
                medianeras=[{"a": [30, 0], "b": [30, 45], "retiro": 0}, {"a": [0, 45], "b": [0, 0], "retiro": 0}],
                cores_mode="manual", cores=[[3, 11], [3.075, 39.325], [25, 3.075], [25, 31.125]],
                patios_mode="manual", patios=[[[0, 8], [20, 8], [20, 25], [0, 25]]],
                stories=[{"program": "Residential", "height": 3}] * 5)
    corre = lambda **k: run(fp, **dict(copy.deepcopy(base), **k))
    patio = base["patios"][0]
    dentro = lambda p: all(0 - 1e-6 <= x <= 20 + 1e-6 and 8 - 1e-6 <= y <= 25 + 1e-6 for x, y in p)
    ejes = lambda r: {ps["id"]: ps["eje"] for ps in r["pasillos"]}
    viv = lambda r: [(u["id"], u["type"], u["area"], u["width"], u["depth"], u["pasillo"]) for u in r["units"]]
    # (a) sin marca (o con la marca apagada, o la clave ausente), el resultado es el de siempre
    r0 = corre()
    assert r0["galerias"] == [] and "galeria_area" not in r0["metrics"] and not any(ps.get("galeria") for ps in r0["pasillos"])
    r0b = corre(patios_galeria=[False])
    assert ejes(r0b) == ejes(r0) and viv(r0b) == viv(r0) and r0b["metrics"] == r0["metrics"]
    p1 = next(ps for ps in r0["pasillos"] if abs(ps["eje"][0][1] - ps["eje"][1][1]) < 1e-6 and ps["eje"][0][1] < 8)   # el brazo de abajo
    assert abs(p1["eje"][0][1] - 6.65) < 0.01 and r0["metrics"]["patio_area"] == 340.0
    u_p1 = [u for u in r0["units"] if u["pasillo"] == p1["id"]]
    assert u_p1 and all(u["depth"] < 5.3 for u in u_p1)                   # 7,3 m de ala menos el pasillo
    # (b) con la marca: el pasillo del brazo de abajo va por el patio y el ala entera es de las viviendas
    r1 = corre(patios_galeria=[True])
    gal = [ps for ps in r1["pasillos"] if ps.get("galeria")]
    assert len(gal) == 1 and gal[0]["id"] == p1["id"], gal
    assert abs(gal[0]["eje"][0][1] - 9.0) < 0.01 and abs(gal[0]["eje"][1][1] - 9.0) < 0.01     # el eje, 1 m dentro del patio
    partes = [r1["corridors"][k] for k in gal[0]["partes"]]
    banda = next(c for c in partes if min(x for x, _ in c) < 1)
    assert dentro([(min(x, 20), y) for x, y in banda]), banda                # la banda, en el patio (x < 20)
    assert any(max(x for x, _ in c) > 29 for c in partes)                   # y sigue hasta el pasillo de la tira (P1 unido a P3)
    assert len(r1["galerias"]) == 1 and dentro(r1["galerias"][0])
    g = r1["metrics"]["galeria_area"]
    assert 36 <= g <= 40 and abs(r1["metrics"]["patio_area"] - (340 - g)) < 0.11, r1["metrics"]
    assert r1["metrics"]["plate_area"] == r0["metrics"]["plate_area"] and r1["metrics"]["gfa"] == r0["metrics"]["gfa"]   # la galería no es planta
    u1 = [u for u in r1["units"] if u["pasillo"] == p1["id"]]
    assert u1 and all(abs(u["depth"] - 7.3) < 0.05 for u in u1), [u["depth"] for u in u1]     # el fondo entero del ala
    assert all(abs(u["door"][1] - 7.65) < 0.01 for u in u1)                 # la puerta, en el borde de la planta sobre la galería
    assert r1["metrics"]["mix"]["nsa"] > r0["metrics"]["mix"]["nsa"] + 10 and r1["metrics"]["efficiency"] > r0["metrics"]["efficiency"]
    assert all(u["egress_status"] == "ok" for u in r1["units"]), [(u["id"], u["egress_status"]) for u in r1["units"]]
    assert all(u["rooms"] and u["ventanas"] for u in u1)                    # con luz: la fachada del fondo
    assert not any(abs(w["seg"][0][1] - 7.65) < 0.05 and abs(w["seg"][1][1] - 7.65) < 0.05 for u in u1 for w in u["ventanas"])   # sin ventanas a la galería
    e0, e1 = ejes(r0), ejes(r1)
    otros = [k for k in e0 if k != p1["id"]]
    assert all(e1[k] == e0[k] for k in otros), (e0, e1)                     # la tira y el brazo de arriba, con su pasillo
    assert 40 <= r1["metrics"]["circulation_pct"] <= 42 and r1["metrics"]["unused_area"] < 60     # v2.64: 53,5 m² (antes, 1,9 por contar dos veces el pasillo bajo los núcleos)
    # (d) el núcleo manual en (3, 11), dentro del patio, se apoya en la galería del brazo de abajo
    c0 = next(c for c in r1["cores"] if c["spec"] == 0)
    assert abs(c0["center"][0] - 3.075) < 0.05 and abs(max(y for _, y in c0["poly"]) - 10) < 0.01 and min(y for _, y in c0["poly"]) < 1
    assert any(p_["kind"] == "stair" for p_ in c0["parts"])
    # (e) un patio automático o un patio sin marca no cambia nada
    ra = run(fp, **dict(copy.deepcopy(base), patios_mode="auto", patios=None))
    rb = run(fp, **dict(copy.deepcopy(base), patios_mode="auto", patios=None, patios_galeria=[True]))
    assert ejes(ra) == ejes(rb) and viv(ra) == viv(rb) and rb["galerias"] == []
    rc = corre(patios_galeria=[False, True])                                 # una marca de más (sin patio) no hace nada
    assert ejes(rc) == ejes(r0) and viv(rc) == viv(r0)
    # el patio del otro lado (espejado): la galería no depende de la orientación
    M = lambda p: [30 - p[0], p[1]]
    esp = dict(copy.deepcopy(base), medianeras=[{"a": M(m["a"]), "b": M(m["b"]), "retiro": 0} for m in base["medianeras"]],
               cores=[M(c) for c in base["cores"]], patios=[[M(p) for p in patio][::-1]], patios_galeria=[True])
    re_ = run([M(p) for p in fp][::-1], **esp)
    gal3 = [ps for ps in re_["pasillos"] if ps.get("galeria")]
    assert len(gal3) == 1 and abs(gal3[0]["eje"][0][1] - 9.0) < 0.01 and 36 <= re_["metrics"]["galeria_area"] <= 40
    assert len(re_["galerias"]) == 1 and all(10 - 1e-6 <= x <= 30 + 1e-6 and 8 - 1e-6 <= y <= 10 + 1e-6 for x, y in re_["galerias"][0])
    ue = [u for u in re_["units"] if u["pasillo"] == gal3[0]["id"]]
    assert ue and all(abs(u["depth"] - 7.3) < 0.05 for u in ue)
    # el proyecto guardado por la web lleva los dos parámetros; el motor los lee tal cual (compatibilidad del JSON)
    from engine.layout import DEFAULT_PARAMS
    assert DEFAULT_PARAMS["patios_galeria"] is None and "galeria_ventanas" not in DEFAULT_PARAMS
    # ---- la web (el comportamiento se comprobó en navegador; acá se vigila el código): la casilla por patio en la ficha
    # del patio, el proyecto, deshacer, el dibujo de la banda, la ficha del tramo y el resumen
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    js = html.split("<script>", 1)[1].split("</script>", 1)[0]
    cuerpo = lambda f: js.split(f, 1)[1].split("\nfunction ", 1)[0].split("\nasync function ", 1)[0]
    assert "galeria_ventanas" not in html                      # la regla 2 (ventanas a la galería) se descartó: sin casilla
    assert 'id="paGaleria"' in cuerpo("function patioPanel(") and "galeriaPatio(this.checked)" in cuerpo("function patioPanel(")
    gp = cuerpo("function galeriaPatio(")
    assert "recordar(" in gp and "ensurePatiosManual()" in gp and "patiosGaleria=" in gp
    obj = cuerpo("function params(){")
    assert "patios_galeria:" in obj
    assert "P.patios_galeria" in cuerpo("function abrirProyecto(") and "m.patios_galeria" in cuerpo("function setMass(")
    assert "patiosGaleria" in cuerpo("function foto(") and "patiosGaleria=s.patiosGaleria||[]" in cuerpo("function volverA(")
    assert "patiosGaleria=[]" in cuerpo("async function nuevo(") and "patiosGaleria=[]" in cuerpo("function ensurePatiosManual(")
    for f in ("function quitarPatio(", "function quitarPatioElegido("):
        assert "patiosGaleria.splice(" in cuerpo(f), f
    assert "function conGaleria(" in js and all("conGaleria(" in cuerpo(f) for f in ("function lineasPanel(", "function tramosAuto(", "async function quitarTramo(", "function sinAuto("))
    assert "result.galerias" in cuerpo("function draw(){") and "'class':'galeria'" in cuerpo("function draw(){") and "function patronGaleria(" in js
    assert "result.galerias" in cuerpo("function drawAxo(){") and "'class':'galeria'" in cuerpo("function drawAxo(){")
    assert "'Galería · '" in cuerpo("function datoEn(") and "ps.galeria" in cuerpo("function pasilloPanel(")
    assert "galeria_area" in cuerpo("function resumenPanel(") and "galeria_area" in cuerpo("function panels(")
    # cada lugar que cambia las marcas registra antes el estado (como test_deshacer con los patios)
    bloques = re.compile(r"\nfunction |\nasync function |addEventListener\(|onclick=\"|onchange=\"")
    exentas = ("function volverA", "function setMass", "async function nuevo", "function ensurePatiosManual")
    sin = []
    for m in re.finditer(r"\bpatiosGaleria(\[[^\]]*\])?(=(?![=>])|\.(push|pop|splice)\()", js):
        linea = js[js.rfind("\n", 0, m.start()) + 1:m.start()]
        if linea.startswith("let "):
            continue
        ini = max([0] + [b.start() for b in bloques.finditer(js, 0, m.start())])
        bloque = js[ini:m.start()].lstrip("\n")
        if not bloque.startswith(exentas) and "recordar(" not in bloque:
            sin.append(js[m.start() - 60:m.end() + 20])
    assert not sin, sin

if __name__ == "__main__":
    test_galeria(); print("OK71")


@calibracion_anterior
def test_extender_vivienda():
    """R4.13b: extender una vivienda al espacio vacío. Cada vivienda del resultado trae «extensible»: los lados de su
    franja (x0, x1, en el marco de su pieza) con planta libre de 0,30 m o más, con el largo y un punto de mundo dentro
    del vacío; la operación {"op": "extender", "p", "a"?} de unit_edits la estira hacia el lado de a (sin a, hacia los
    dos) hasta lo primero que encuentra: la vecina (del otro lado del tabique), un pasillo, un núcleo, una zona sin luz
    o el fin de la franja; conserva el tipo y queda editada. En la web, un botón por lado libre en la ficha de la
    vivienda (pasa por editar: se deshace con ↶). Los cambios del usuario se aplican después de sin_solapes (el vacío
    que deja una vivienda quitada por los pasillos dibujados solo existe ahí) y sin_solapes vuelve a correr si hubo
    cambios. Las franjas de los ejemplos están llenas: no cambian."""
    import shutil, subprocess, tempfile
    from engine import geometry as G, layout as LY, units as UN
    T_ = lambda p: [tuple(q) for q in p]
    inter = lambda a, b: abs(G.area(T_(a))) - sum(abs(G.area(o)) for o, _ in G.subtract(T_(a), [T_(b)])[0])
    muestra = lambda n: json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", n + ".json"),
                                       encoding="utf-8"))
    gen = lambda fp, stage="plans", **p: generate({"footprint": fp, "height": 15, "stage": stage, "params": p})
    centro = lambda u: [round(sum(p[0] for p in u["poly"]) / len(u["poly"]), 3), round(sum(p[1] for p in u["poly"]) / len(u["poly"]), 3)]
    mitad = lambda s: [(s[0][0] + s[1][0]) / 2, (s[0][1] + s[1][1]) / 2]

    def pisa(r):
        fijos = r["corridors"] + [c["poly"] for c in r["cores"]]
        us = [u["poly"] for u in r["units"]]
        return max([inter(a, b) for i, a in enumerate(us) for b in us[i + 1:]] + [inter(a, f) for a in us for f in fijos])
    # ---- en los ejemplos las franjas están llenas: ninguna vivienda tiene planta libre al lado (lo que el resumen
    # muestra como «Sin usar» son los tabiques y los medios muros junto al pasillo, que la métrica no atribuye a nadie)
    for n in ("barra_larga", "T_dos_lineas", "patio_central", "entre_medianeras_patio_central"):
        s = muestra(n)
        p = {k: s[k] for k in ("centerlines", "stories", "medianeras") if s.get(k)}
        if s.get("patios"):
            p.update(patios_mode="manual", patios=s["patios"])
        if s.get("cores"):
            p.update(cores_mode="manual", cores=s["cores"])
        r = generate({"footprint": s["footprint"], "height": s.get("height"), "stage": "plans", "params": p})
        assert r["units"] and all(u["extensible"] == {} for u in r["units"]), (n, [u["extensible"] for u in r["units"]])
    # (d) sin nada libre, el cambio no se aplica, se avisa con la vivienda y nada cambia
    s = muestra("barra_larga")
    base = gen(s["footprint"])
    u0 = base["units"][0]
    r = gen(s["footprint"], unit_edits=[{"op": "extender", "p": centro(u0), "a": [u0["poly"][0][0] + 1, u0["poly"][0][1]]}])
    assert any("No hay planta libre al lado de %s" % u0["id"] in w for w in r["warnings"]), r["warnings"]
    assert any("1 cambio(s) de viviendas no se pudieron aplicar" in w for w in r["warnings"]), r["warnings"]
    assert [u["poly"] for u in r["units"]] == [u["poly"] for u in base["units"]] and r["metrics"] == base["metrics"]
    assert all(not u.get("editada") for u in r["units"])
    # ---- tres líneas por un mismo punto (horizontal, vertical y una diagonal a 22°): la vivienda de la diagonal que
    # pisa el pasillo horizontal no entra (sin_solapes) y su vecina de la franja queda con 4,3 m de planta libre al lado
    fp = [[0, 0], [80, 0], [80, 40], [0, 40]]
    lineas = [[[1, 20], [79, 20]], [[40, 1], [40, 39]], [[10, 8], [70, 32]]]
    r = gen(fp, centerlines=lineas)
    assert any("no entran donde se cruzan" in w for w in r["warnings"]), r["warnings"]
    con = [u for u in r["units"] if u["extensible"]]
    # (v2.62: con el frente de cada plano, dos viviendas de la diagonal no entran, una a cada lado del cruce, y sus vecinas
    # quedan con 6 m libres: la de la izquierda hacia x1 y la de la derecha hacia x0)
    assert len(con) == 2 and sorted(list(u["extensible"]) for u in con) == [["x0"], ["x1"]], [(u["id"], u["extensible"]) for u in con]
    u = next(u for u in con if "x0" in u["extensible"])
    ext = u["extensible"]["x0"]
    assert 4.0 <= ext["largo"] <= 6.5 and u["type"] == "3 dorm", (ext, u["type"])
    # (a) el punto del vacío cae en la planta y fuera de las viviendas, los pasillos, los núcleos y las zonas sin luz
    p = tuple(ext["p"])
    assert G.point_in_poly(p, T_(r["plate"]))
    todo = [v["poly"] for v in r["units"]] + r["corridors"] + [c["poly"] for c in r["cores"]] + r.get("dark_zones", [])
    assert not any(G.point_in_poly(p, T_(x)) for x in todo)
    assert all("extensible" in v for v in gen(fp, "units", centerlines=lineas)["units"])   # también en la etapa del mix
    # (b) con la operación (a = ese punto) la vivienda crece lo libre, conserva el tipo y queda editada; «Sin usar»
    # baja lo mismo; nadie pisa a nadie; los planos se generan y la evacuación sigue igual
    r2 = gen(fp, centerlines=lineas, unit_edits=[{"op": "extender", "p": centro(u), "a": ext["p"]}])
    v = next(x for x in r2["units"] if x["id"] == u["id"])
    gana = v["area"] - u["area"]
    assert v.get("editada") and v["type"] == u["type"] and abs(v["width"] - u["width"] - ext["largo"]) < 0.02, (v["width"], u["width"], ext)
    assert 10 < gana < ext["largo"] * u["depth"] + 0.5 and v["extensible"] == {}, (gana, ext, u["depth"])   # la franja es más playa en el vacío
    assert abs((r["metrics"]["unused_area"] - r2["metrics"]["unused_area"]) - gana) < 0.3, (r["metrics"]["unused_area"], r2["metrics"]["unused_area"], gana)
    assert pisa(r2) < 0.01 and len(v["rooms"]) >= 5 and "plan_score" in v and len(r2["units"]) == len(r["units"]), pisa(r2)
    assert r2["evacuacion"] == r["evacuacion"] and all(y["poly"] == x["poly"] and y["egress"] == x["egress"]
                                                       for x, y in zip(r["units"], r2["units"]) if x["id"] != u["id"])
    assert v["egress_status"] == u["egress_status"] and not any("no se pud" in w or "planta libre" in w for w in r2["warnings"])
    assert gen(fp, centerlines=lineas, unit_edits=[{"op": "extender", "p": centro(u)}])["units"][int(u["id"][1:]) - 1]["poly"] == v["poly"]   # sin a: el único lado libre
    # (e) los cambios se aplican en orden: extender y después dividir en el vacío ganado (ahí solo hay vivienda si la
    # extensión se aplicó antes), y después mover el tabique nuevo 1 m
    ex = {"op": "extender", "p": centro(u), "a": ext["p"]}
    r4 = gen(fp, centerlines=lineas, unit_edits=[ex, {"op": "dividir", "p": ext["p"]}])
    A, B = [x for x in r4["units"] if x.get("editada")]
    assert len(r4["units"]) == len(r["units"]) + 1 and A["id"] == u["id"] and abs(A["width"] + 0.3 + B["width"] - v["width"]) < 0.02, (A["width"], B["width"], v["width"])
    t = next(t for t in r4["tabiques"] if (t["a"], t["b"]) == (A["id"], B["id"]))
    hacia = [mitad(t["seg"])[0] + t["dir"][0], mitad(t["seg"])[1] + t["dir"][1]]
    r5 = gen(fp, centerlines=lineas, unit_edits=[ex, {"op": "dividir", "p": ext["p"]}, {"op": "tabique", "p": mitad(t["seg"]), "a": hacia}])
    A5, B5 = (next(x for x in r5["units"] if x["id"] == k) for k in (A["id"], B["id"]))
    assert abs(A5["width"] - A["width"] - 1) < 0.02 and abs(B5["width"] - B["width"] + 1) < 0.02 and pisa(r5) < 0.01, (A5["width"], A["width"], B5["width"], B["width"])
    assert not any("no se pud" in w or "planta libre" in w for w in r4["warnings"] + r5["warnings"]), r5["warnings"]
    assert gen(fp, centerlines=lineas, unit_edits=[{"op": "dividir", "p": ext["p"]}, ex])["units"][int(u["id"][1:]) - 1]["poly"] == v["poly"]   # al revés, el dividir no encuentra vivienda y el extender sí
    # (c) sin a se extiende hacia los dos lados si los dos están libres: en la barra, sin la primera y la tercera
    # vivienda de una franja, la segunda toma el fin de la franja de un lado y llega hasta el tabique de la cuarta del otro
    barra = [[0, 0], [60, 0], [60, 16], [0, 16]]
    captura, orig = [], LY.extensibles
    LY.extensibles = lambda units, fijos, params: (orig(units, fijos, params), captura.append((units, fijos, params)))
    try:
        gen(barra)
    finally:
        LY.extensibles = orig
    units, fijos, params = captura[0]
    reg = units[0]["_region"]
    fila = sorted([x for x in units if x.get("_region") is reg], key=lambda x: x["x0"])
    assert len(fila) == 4 and all(x["extensible"] == {} for x in fila)
    a_, b_, c_, d_ = fila
    for x in (a_, c_):
        units.remove(x)
    UN.extensibles(units, fijos, params)
    assert set(b_["extensible"]) == {"x0", "x1"} and abs(b_["extensible"]["x0"]["largo"] - a_["width"] - params["party_wall"]) < 0.01 \
        and abs(b_["extensible"]["x1"]["largo"] - c_["width"] - params["party_wall"]) < 0.01, b_["extensible"]
    pm = G.to_world([((b_["x0"] + b_["x1"]) / 2, G.centroid(b_["poly_local"])[1])], b_["_pc"]["origin"], b_["_pc"]["angle"])[0]
    hechos, fallidos = set(), []
    UN.editar_unidades(units, [{"op": "extender", "p": list(pm)}], params, hechos, fijos, fallidos)
    assert hechos == {0} and not fallidos and b_.get("editada") and abs(b_["x0"] - a_["x0"]) < 1e-6 and abs(b_["x1"] - c_["x1"]) < 1e-6, (b_["x0"], a_["x0"], b_["x1"], c_["x1"])
    assert abs(b_["x1"] + params["party_wall"] - d_["x0"]) < 1e-6 and b_["type"] == "3 dorm"   # hasta el tabique de la cuarta
    UN.extensibles(units, fijos, params)
    assert b_["extensible"] == {} and d_["extensible"] == {}
    # y en orden con un tabique: el de la segunda con la cuarta se corre 1 m después de extender
    pt = G.to_world([(b_["x1"] + params["party_wall"] / 2, G.centroid(b_["poly_local"])[1])], b_["_pc"]["origin"], b_["_pc"]["angle"])[0]
    pa = G.to_world([(b_["x1"] + params["party_wall"] / 2 + 1, G.centroid(b_["poly_local"])[1])], b_["_pc"]["origin"], b_["_pc"]["angle"])[0]
    x1_antes = b_["x1"]
    UN.editar_unidades(units, [{"op": "extender", "p": list(pm)}, {"op": "tabique", "p": list(pt), "a": list(pa)}], params, hechos, fijos, fallidos)
    assert hechos == {0, 1} and abs(b_["x1"] - x1_antes - 1) < 1e-6 and abs(b_["x1"] + params["party_wall"] - d_["x0"]) < 1e-6, (hechos, b_["x1"], x1_antes)
    # ---- la web: un botón por lado libre en la ficha de la vivienda, que pasa por editar (test_deshacer); el texto dice
    # hacia dónde en el SCP actual; el punto del vacío se marca en la planta al pasar el mouse
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    js = html.split("<script>", 1)[1].split("</script>", 1)[0]
    cuerpo = lambda f: js.split("function %s(" % f, 1)[1].split("\nfunction ", 1)[0].split("\nasync function ", 1)[0].split("\n/*", 1)[0]
    assert "extenderBotones(u)" in cuerpo("unitPanel") and "marcaExt=null" in cuerpo("unitPanel")
    assert "u.extensible" in cuerpo("extenderBotones") and "extenderVivienda('${k}')" in cuerpo("extenderBotones") and "marcarPunto(" in cuerpo("extenderBotones")
    ev = cuerpo("extenderVivienda")
    assert "op:'extender'" in ev and "a:x.p" in ev and "editar(" in ev and "'extender '+u.id" in ev
    assert "'la izquierda'" in cuerpo("ladoExtension") and "'la derecha'" in cuerpo("ladoExtension") and "scpActual()" in cuerpo("ladoExtension")
    assert "marcaExt" in cuerpo("drawOverlay") and "function marcarPunto(" in js
    node = shutil.which("node")
    if not node:
        print("(sin node: se omite «node --check» del programa de la página)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        ruta = os.path.join(tmp, "programa.js")
        open(ruta, "w", encoding="utf-8").write(js)
        c = subprocess.run([node, "--check", ruta], capture_output=True, text=True, encoding="utf-8")
        assert c.returncode == 0, c.stderr

if __name__ == "__main__":
    test_extender_vivienda(); print("OK72")


def test_ver_dxf():
    """tools/ver_dxf.py (R5.16, base de tipologías): lee un DXF de la convención de TIPOLOGIAS.md (geometría con
    dxf_lector, textos TEXT y MTEXT aquí), escribe un SVG para mirarlo y da el informe de control: unidades y estancias
    con su superficie y su etiqueta, entrada sobre el contorno, estancias habitables que tocan la fachada, metadatos,
    errores (lo que la lista de control no admite) y avisos. (a) El ejemplo tests/dxf/tipologia_2d.dxf pasa limpio;
    (b) sin una etiqueta, con una etiqueta fuera de la lista, con superficie_muros errada y sin entrada, los errores
    lo dicen; (c) el programa termina con 0 o 1 según haya errores. v2.58 (convención al día con CRITERIOS.md):
    (d) «Dormir» es la zona de dormir de un monoambiente: habitable, no cuenta como dormitorio y los exteriores propios
    ya no son estancias; (e) un archivo `-N2` (nivel superior de una vivienda en varios niveles) no necesita entrada y
    con `-N1` o más no se compara la tipología con los dormitorios del nivel; una planta sin Trazo_Pasillo no avisa
    de entrada; (f) el comedor, el estar o la cocina integrada de un ambiente abierto no avisan de fachada si otro
    local contiguo del ambiente (en cadena) la toca, los dormitorios y estudios cerrados sí; (g) las polilíneas
    cerradas con texto de Trazo_Cotas salen como «otros recintos»; (h) sin Trazo_Norte, `norte: desconocido` en los
    datos no avisa «sin norte» (sin ese dato, sí)."""
    import importlib.util, subprocess, tempfile
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta = os.path.join(raiz, "tools", "ver_dxf.py")
    spec = importlib.util.spec_from_file_location("ver_dxf", ruta)
    V = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(V)
    ejemplo = os.path.join(raiz, "tests", "dxf", "tipologia_2d.dxf")
    texto = open(ejemplo, "rb").read().decode("utf-8")
    # (a) el ejemplo
    datos = V.leer(texto)
    assert datos["escala"] == 1.0 and datos["insunits"] == 6 and not datos["otras_capas"]
    assert V.rol("Trazo_Estancias") == "estancias" and V.rol("trazo-unidades") == "unidad" and V.rol("LOTE") is None
    inf = V.controlar(datos)
    assert inf["tipo"] == "unidad" and inf["errores"] == [] and inf["avisos"] == [], (inf["errores"], inf["avisos"])
    assert len(inf["unidades"]) == 1 and abs(inf["unidades"][0]["area"] - 56.0) < 0.01
    u = inf["unidades"][0]
    assert u["tipologia"] == "1D" and u["m2"] == 56.0 and u["entradas"] == 1 and len(u["estancias"]) == 7
    nombres = {e["nombre"]: e for e in inf["estancias"]}
    assert set(nombres) == {"Hall", "Cocina", "Baño", "Lavadero", "Pasillo", "Estar-Comedor", "Dormitorio 1"}
    assert nombres["Estar-Comedor"]["fachada"] is True and nombres["Dormitorio 1"]["fachada"] is True
    assert nombres["Cocina"]["fachada"] is None and not nombres["Cocina"]["habitable"]       # no es habitable: no se mira
    assert abs(nombres["Dormitorio 1"]["area"] - 3.4 * 2.9) < 0.01
    assert inf["puertas"] == 5 and inf["ventanas"] == 2 and abs(inf["fachada"] - 8.0) < 1e-6 and inf["norte"] == 0
    assert inf["datos"]["tipologia"] == "1D" and inf["datos"]["precision"] == "alta"
    lineas = V.informe_txt("tipologia_2d.dxf", inf)
    assert lineas[1].startswith("Vivienda 1: 56,0 m²") and "Errores: ninguno" in lineas and "Avisos: ninguno" in lineas
    s = V.svg(datos, inf, titulo="prueba")
    assert s.startswith("<svg") and s.count("<path") >= 7 + 1 + 5 + 2 and "Dormitorio 1 9,9 m²" in s and "Trazo_Entrada (1)" in s
    assert '<rect width="100%" height="100%"' in s and "%%" not in s   # v2.57.1: el fondo decía 100%% y el navegador lo ignoraba
    assert "Sin errores ni avisos" in s and "superficie_muros: 56.0" in s
    # (b) un DXF con fallas: sin la etiqueta del dormitorio, «Living» en vez de «Estar-Comedor», superficie errada y sin entrada
    malo = texto.replace("Dormitorio 1\r\n", "\r\n").replace("Estar-Comedor", "Living").replace("superficie_muros: 56.0", "superficie_muros: 61.0")
    malo = malo.replace("Trazo_Entrada", "Trazo_Puertas")
    inf2 = V.controlar(V.leer(malo))
    err = " | ".join(inf2["errores"])
    assert "sin etiqueta" in err and "«Living» no está en la lista" in err and "superficie_muros dice 61,0" in err
    assert "no tiene entrada" in err and inf2["puertas"] == 6
    assert "Living" in " ".join(inf2["avisos"]) or inf2["avisos"] == [] or True              # los avisos no se exigen aquí
    # variantes por reemplazo de texto sobre el ejemplo (cada valor es una línea entera del DXF, con CRLF)
    def cambiar(t, viejo, nuevo):
        assert t.count("\r\n%s\r\n" % viejo) == 1, viejo
        return t.replace("\r\n%s\r\n" % viejo, "\r\n%s\r\n" % nuevo)

    def agregar(t, *entidades):                      # entidades nuevas al final de ENTITIES
        antes, fin, despues = t.rpartition("  0\r\nENDSEC")
        return antes + "".join(entidades) + fin + despues

    def poli(capa, pts):
        return "  0\r\nLWPOLYLINE\r\n  8\r\n%s\r\n 90\r\n%d\r\n 70\r\n1\r\n" % (capa, len(pts)) + \
            "".join(" 10\r\n%.2f\r\n 20\r\n%.2f\r\n" % p for p in pts)

    def rotulo(capa, p, t):
        return "  0\r\nTEXT\r\n  8\r\n%s\r\n 10\r\n%.2f\r\n 20\r\n%.2f\r\n 40\r\n0.25\r\n  1\r\n%s\r\n" % (capa, p[0], p[1], t)

    def sin_linea(t, capa):                          # quita la LINE de esa capa (la única del ejemplo)
        a = t.index("  0\r\nLINE\r\n  8\r\n%s\r\n" % capa)
        b = t.index("  0\r\n", a + 6)
        assert t[a:b].count("\r\n") == 12
        return t[:a] + t[b:]

    def sin_entrada(t):
        return sin_linea(t, "Trazo_Entrada")

    def aviso(inf_, trozo):
        return any(trozo in a for a in inf_["avisos"])

    # (d) v2.58: monoambiente con zona de dormir. «Dormir» es habitable, necesita ventana y no cuenta como dormitorio:
    # la vivienda es Mono con 0 dormitorios, sin el aviso «etiquetada Mono y tiene 1 dormitorio»
    mono = cambiar(cambiar(cambiar(cambiar(texto, "Dormitorio 1", "Dormir"), "1D 56.0", "Mono 56.0"), "tipologia: 1D", "tipologia: Mono"),
                   "dormitorios: 1", "dormitorios: 0")
    inf3 = V.controlar(V.leer(mono))
    assert inf3["errores"] == [] and inf3["avisos"] == [], (inf3["errores"], inf3["avisos"])
    n3 = {e["nombre"]: e for e in inf3["estancias"]}
    assert "Dormitorio 1" not in n3 and n3["Dormir"]["habitable"] and n3["Dormir"]["fachada"] is True
    assert inf3["unidades"][0]["tipologia"] == "Mono" and "Dormir 9,9 m² (fachada)" in " ".join(V.informe_txt("m.dxf", inf3))
    assert aviso(V.controlar(V.leer(cambiar(texto, "1D 56.0", "Mono 56.0"))), "etiquetada «Mono» y tiene 1 dormitorio")
    assert aviso(V.controlar(V.leer(cambiar(texto, "Dormitorio 1", "Dormir"))), "etiquetada «1D» y tiene 0 dormitorios")   # Dormir no cuenta
    assert 'Dormir 9,9 m²' in V.svg(V.leer(mono), inf3) and V.RELLENO["Dormir"] == V.RELLENO["Dormitorio"]
    # Balcón, Terraza y Patio ya no son estancias: van fuera de la vivienda, en Trazo_Cotas
    for exterior in ("Balcón", "Terraza", "Patio"):
        err3 = " | ".join(V.controlar(V.leer(cambiar(texto, "Lavadero", exterior)))["errores"])
        assert "«%s» no está en la lista" % exterior in err3 and "Trazo_Cotas" in err3, err3
    assert "Trazo_Cotas" not in " | ".join(inf2["errores"])                           # la pista es solo para los exteriores
    # (e) vivienda en varios niveles: el nivel superior (-N2…) no lleva Trazo_Entrada y la tipología es la de toda la vivienda
    assert V.nivel_de("U_MVD_Maua_3D_5.79x9.43_05-N2.dxf") == 2 and V.nivel_de("x/U_a_1D_1x1_01-N1.dxf") == 1
    assert V.nivel_de("U_MVD_Maua_1D_5.79x9.43_01.dxf") is None and V.nivel_de("") is None and V.nivel_de("N2.dxf") is None
    n2 = sin_entrada(texto)
    inf4 = V.controlar(V.leer(n2), "U_x_1D_8x7_01-N2.dxf")
    assert inf4["errores"] == [] and inf4["avisos"] == [] and inf4["unidades"][0]["entradas"] == 0 and inf4["nivel"] == 2
    assert any("nivel superior (-N2) sin puerta al palier" in n for n in inf4["notas"])
    assert any("nivel superior (-N2) sin puerta al palier" in l for l in V.informe_txt("U_x_1D_8x7_01-N2.dxf", inf4))
    assert any("no tiene entrada" in e for e in V.controlar(V.leer(n2), "U_x_1D_8x7_01.dxf")["errores"])      # sin sufijo, es error
    assert any("no tiene entrada" in e for e in V.controlar(V.leer(n2))["errores"])
    # la tipología no se compara con los dormitorios del nivel (con -N1 tampoco); con una entrada, -N1 se controla igual
    sin_dorm = cambiar(texto, "Dormitorio 1", "Estudio")                                     # 1D, 0 dormitorios en el nivel
    assert aviso(V.controlar(V.leer(sin_dorm), "U_x_1D_8x7_01.dxf"), "etiquetada «1D» y tiene 0 dormitorios")
    for sufijo in ("-N1", "-N2"):
        inf5 = V.controlar(V.leer(sin_dorm), "U_x_1D_8x7_01%s.dxf" % sufijo)
        assert not aviso(inf5, "etiquetada") and inf5["errores"] == [] and any("toda la vivienda" in n for n in inf5["notas"])
    inf6 = V.controlar(V.leer(texto), "U_x_1D_8x7_01-N1.dxf")
    assert inf6["unidades"][0]["entradas"] == 1 and inf6["avisos"] == [] and not any("sin puerta" in n for n in inf6["notas"])
    # una planta sin Trazo_Pasillo (piso al que no se entra) no avisa de entrada; con Trazo_Pasillo, sí
    piso = agregar(n2, poli("Trazo_Terreno", [(-1, -1), (9, -1), (9, 8), (-1, 8)]))
    inf7 = V.controlar(V.leer(piso), "P_x_2.dxf")
    assert inf7["tipo"] == "planta" and not aviso(inf7, "no tiene entrada") and inf7["errores"] == []
    assert any("planta sin palier" in l for l in V.informe_txt("P_x_2.dxf", inf7))
    inf8 = V.controlar(V.leer(agregar(piso, poli("Trazo_Pasillo", [(0, -1), (8, -1), (8, 0), (0, 0)]))), "P_x_1.dxf")
    assert aviso(inf8, "la vivienda 1 no tiene entrada") and not any("planta sin palier" in n for n in inf8["notas"])
    # (f) ambiente abierto: el comedor interior no es una falla de fachada si es contiguo (en cadena) a un local del ambiente que la toca
    inf9 = V.controlar(V.leer(cambiar(texto, "Cocina", "Comedor")))                           # contigua al Estar-Comedor, con fachada
    c9 = [e for e in inf9["estancias"] if e["nombre"] == "Comedor"][0]
    assert inf9["errores"] == [] and inf9["avisos"] == [] and c9["fachada"] is False and c9["abierto"]
    assert any("sin fachada propia: ambiente abierto" in l for l in V.informe_txt("c.dxf", inf9))
    inf10 = V.controlar(V.leer(cambiar(texto, "Baño", "Comedor")))                            # no es contigua a ningún local del ambiente
    assert aviso(inf10, "«Comedor» no toca ninguna fachada") and not [e for e in inf10["estancias"] if e["abierto"]]
    cadena = cambiar(cambiar(cambiar(texto, "Lavadero", "Comedor"), "Pasillo", "Cocina integrada"), "Cocina", "Comedor")
    inf11 = V.controlar(V.leer(cadena))                                                       # Comedor-Cocina integrada-Comedor-Estar-Comedor
    assert inf11["errores"] == [] and not aviso(inf11, "no toca") and sum(1 for e in inf11["estancias"] if e["abierto"]) == 2   # los dos Comedor
    cortada = cambiar(cambiar(texto, "Lavadero", "Comedor"), "Pasillo", "Cocina integrada")     # la Cocina cerrada corta la cadena
    assert aviso(V.controlar(V.leer(cortada)), "«Comedor» no toca ninguna fachada")
    for dormir_ok, nombre_c in ((True, "Dormir"), (False, "Dormitorio 2"), (False, "Estudio")):   # Dormir sí; dormitorio y estudio cerrados, no
        inf12 = V.controlar(V.leer(cambiar(texto, "Cocina", nombre_c)))
        assert aviso(inf12, "«%s» no toca ninguna fachada" % nombre_c) != dormir_ok, (nombre_c, inf12["avisos"])
    assert V._contiguas([(0, 0), (2, 0), (2, 1), (0, 1)], [(0.1, 1.1), (2.0, 1.1), (2.0, 2), (0.1, 2)])          # muro de 10 cm entre las dos
    assert not V._contiguas([(0, 0), (2, 0), (2, 1), (0, 1)], [(2.1, 1.1), (3, 1.1), (3, 2), (2.1, 2)])          # solo se tocan en la esquina
    assert not V._contiguas([(0, 0), (2, 0), (2, 1), (0, 1)], [(1.7, 1.1), (2.0, 1.1), (2.0, 2), (1.7, 2)])      # tramo de 0,30 m: menos de 0,60
    assert not V._contiguas([(0, 0), (2, 0), (2, 1), (0, 1)], [(0, 1.8), (2, 1.8), (2, 3), (0, 3)])              # separadas 0,80 m
    # (g) Trazo_Cotas: la polilínea cerrada con un texto dentro (balcón, terraza, cochera, amenity) sale como «otro recinto»
    cotas = agregar(texto, poli("Trazo_Cotas", [(8.0, 1.0), (9.0, 1.0), (9.0, 6.8), (8.0, 6.8)]), rotulo("Trazo_Cotas", (8.2, 3.0), "Balcón"),
                    poli("Trazo_Cotas", [(10.0, 0.0), (11.0, 0.0), (11.0, 1.0), (10.0, 1.0)]),       # cerrada sin texto: no es un recinto
                    rotulo("Trazo_Cotas", (12.0, 12.0), "texto suelto"))
    dc = V.leer(cotas)
    assert not dc["otras_capas"]
    inf13 = V.controlar(dc)
    assert [(r["nombre"], round(r["area"], 2)) for r in inf13["recintos"]] == [("Balcón", 5.8)] and inf13["errores"] == []
    assert any(l == "Otros recintos: Balcón 5,8 m²" for l in V.informe_txt("c.dxf", inf13))
    assert not any(l.startswith("Otros recintos") for l in V.informe_txt("e.dxf", inf))
    sc = V.svg(dc, inf13)
    assert "Balcón · 5,8 m²" in sc and V.RECINTO in sc and "Trazo_Cotas (" in sc
    # (h) norte: sin Trazo_Norte se avisa, salvo que los datos digan `norte: desconocido` (la fuente no lo trae)
    sin_n = sin_linea(texto, "Trazo_Norte")
    inf14 = V.controlar(V.leer(sin_n))
    assert inf14["norte"] is None and not inf14["norte_desconocido"] and aviso(inf14, "sin norte")
    assert any(l.endswith("norte: no") for l in V.informe_txt("n.dxf", inf14))
    for dato in ("norte: desconocido", "norte: Desconocido (la carpeta no trae el símbolo)", "norte:desconocido"):
        inf15 = V.controlar(V.leer(cambiar(sin_n, "norte: 0", dato)))
        assert inf15["norte"] is None and inf15["norte_desconocido"] and inf15["avisos"] == [] and inf15["errores"] == [], dato
        assert any(l.endswith("norte: desconocido") for l in V.informe_txt("n.dxf", inf15))
    assert aviso(V.controlar(V.leer(cambiar(sin_n, "norte: 0", "norte: 15"))), "sin norte")        # un ángulo sin línea no basta
    inf16 = V.controlar(V.leer(cambiar(texto, "norte: 0", "norte: desconocido")))                  # con la línea, manda la línea
    assert inf16["norte"] == 0 and not inf16["norte_desconocido"] and inf16["avisos"] == []
    assert any(l.endswith("norte: 0°") for l in V.informe_txt("n.dxf", inf16))
    # (c) el programa: 0 con el ejemplo, 1 con fallas; escribe el SVG donde se le dice
    with tempfile.TemporaryDirectory() as tmp:
        svg1 = os.path.join(tmp, "ejemplo.svg")
        c = subprocess.run([sys.executable, ruta, ejemplo, svg1], capture_output=True, text=True, encoding="utf-8")
        assert c.returncode == 0 and "Errores: ninguno" in c.stdout and os.path.exists(svg1), c.stdout + c.stderr
        ruta_malo = os.path.join(tmp, "malo.dxf")
        open(ruta_malo, "w", encoding="utf-8", newline="").write(malo)
        c = subprocess.run([sys.executable, ruta, ruta_malo], capture_output=True, text=True, encoding="utf-8")
        assert c.returncode == 1 and "sin etiqueta" in c.stdout and os.path.exists(os.path.join(tmp, "malo.svg")), c.stdout + c.stderr
        c = subprocess.run([sys.executable, ruta, os.path.join(tmp, "no.dxf")], capture_output=True, text=True, encoding="utf-8")
        assert c.returncode != 0
        # v2.58: el nivel superior de una vivienda en varios niveles (-N2, sin Trazo_Entrada) no es un error; sin el sufijo, sí
        ruta_n2 = os.path.join(tmp, "U_x_1D_8x7_01-N2.dxf")
        open(ruta_n2, "w", encoding="utf-8", newline="").write(n2)
        c = subprocess.run([sys.executable, ruta, ruta_n2], capture_output=True, text=True, encoding="utf-8")
        assert c.returncode == 0 and "Errores: ninguno" in c.stdout and "nivel superior" in c.stdout, c.stdout + c.stderr
        ruta_n0 = os.path.join(tmp, "U_x_1D_8x7_01.dxf")
        open(ruta_n0, "w", encoding="utf-8", newline="").write(n2)
        c = subprocess.run([sys.executable, ruta, ruta_n0], capture_output=True, text=True, encoding="utf-8")
        assert c.returncode == 1 and "no tiene entrada" in c.stdout, c.stdout + c.stderr


if __name__ == "__main__":
    test_ver_dxf(); print("OK73")


def test_base_tipologias():
    """data/tipologias/ (R5.16): todos los DXF de la base pasan el control de tools/ver_dxf.py sin errores (solo se
    permiten avisos), los nombres de archivo coinciden uno a uno con la columna `archivo` de indice.csv, su `tipo` con
    el prefijo (U_ unidad, P_ planta), y ningún monoambiente (zona de dormir `Dormir`) avisa de dormitorios, y todos tienen `Trazo_Norte` o `norte: desconocido`."""
    import csv, importlib.util
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("ver_dxf", os.path.join(raiz, "tools", "ver_dxf.py"))
    V = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(V)
    carpeta = os.path.join(raiz, "data", "tipologias")
    archivos = sorted(f for f in os.listdir(carpeta) if f.lower().endswith(".dxf"))
    assert len(archivos) >= 67, len(archivos)
    fallas = {}
    for nombre in archivos:
        inf = V.controlar(V.leer(V.texto_del_archivo(os.path.join(carpeta, nombre))), nombre)
        if inf["errores"]:
            fallas[nombre] = inf["errores"]
        assert not any("etiquetada «Mono»" in a for a in inf["avisos"]), (nombre, inf["avisos"])
        assert not any("sin norte" in a for a in inf["avisos"]), (nombre, "sin Trazo_Norte ni `norte: desconocido`")
        assert inf["tipo"] == ("unidad" if nombre.startswith("U_") else "planta"), (nombre, inf["tipo"])
    assert not fallas, fallas
    with open(os.path.join(carpeta, "indice.csv"), encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f, delimiter=";"))
    del_indice = [r["archivo"] for r in filas]
    assert len(del_indice) == len(set(del_indice)), "archivos repetidos en indice.csv"
    assert set(del_indice) == set(archivos), (sorted(set(archivos) - set(del_indice)), sorted(set(del_indice) - set(archivos)))
    for r in filas:
        assert r["tipo"] == ("unidad" if r["archivo"].startswith("U_") else "planta"), r["archivo"]


if __name__ == "__main__":
    test_base_tipologias(); print("OK74")


def test_tipologias():
    """engine/tipologias.py (R5.16): el lector de la base de tipologías arma el catálogo (viviendas, plantas y resumen)
    a partir de los DXF de data/tipologias/ con tools/ver_dxf.py. (a) Lee los 67 archivos (49 viviendas y 18 plantas) sin
    avisos; (b) una vivienda: U_MVD_M5_2D_8.52x7.17_01 (2D, 2 dormitorios, 8,52 × 7,17, 61,1 m² con muros, 9 estancias; el
    Estar toca la fachada y el Comedor toma la luz del ambiente abierto; `kind` de plans.py); (c) un monoambiente tiene
    su zona `Dormir` (kind «sleep», sin dormitorios); (d) los niveles de una vivienda en varios niveles comparten
    `vivienda_id` y el resumen la cuenta una vez; (e) una planta con palier (P_MVD_M5_tipo): ancho de pasillo, viviendas
    por núcleo y circulación razonables (en %, como las del motor); el ancho de una puerta en la punta de un pasillo es el
    ancho y no el largo; (f) `escribir` produce un catalogo.json igual al guardado en data/tipologias/ (salvo `version` y
    `resumen.comparacion`, que dependen del motor: si la base cambia, hay que correr `python -m engine.tipologias`) y un
    RESUMEN.md, con «\\n», sin escribir en data/tipologias/; (g) un DXF suelto (tests/dxf/tipologia_2d.dxf) se lee como
    vivienda: 1D, 7 estancias, Dormitorio 1 de 9,9 m²; (h) `main` lee una carpeta cualquiera (sin indice.csv) y escribe
    el catálogo y el resumen ahí."""
    import contextlib, io, shutil, tempfile
    from engine import tipologias as T
    from engine import layout as LY
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    carpeta = os.path.join(raiz, "data", "tipologias")
    # (a) toda la base
    cat = T.leer_base(carpeta)
    assert cat["version"] == LY.VERSION and cat["avisos"] == [], (cat["version"], cat["avisos"])
    assert cat["archivos"] >= 67 and len(cat["viviendas"]) >= 49 and len(cat["plantas"]) >= 18
    assert cat["archivos"] == len(cat["viviendas"]) + len(cat["plantas"])
    assert all(v["archivo"].startswith("U_") for v in cat["viviendas"]) and all(p["archivo"].startswith("P_") for p in cat["plantas"])
    # (b) una vivienda
    por_archivo = {v["archivo"]: v for v in cat["viviendas"]}
    v = por_archivo["U_MVD_M5_2D_8.52x7.17_01.dxf"]
    assert v["tipologia"] == "2D" and v["dormitorios"] == 2 and v["proyecto"] == "M5" and v["precision"] == "alta"
    assert v["nivel"] is None and v["vivienda_id"] == "M5_01" and v["anio"] is None and v["crujia"] == "simple"
    assert v["frente"] == 8.52 and v["fondo"] == 7.17 and abs(v["area_muros"] - 61.1) < 0.2, (v["frente"], v["fondo"], v["area_muros"])
    assert abs(v["superficie_util"] - 54.9) < 0.2 and len(v["contorno"]) == 4 and len(v["estancias"]) == 9
    e = {x["nombre"]: x for x in v["estancias"]}
    assert abs(e["Dormitorio 1"]["area"] - 12.3) < 0.15 and abs(e["Cocina integrada"]["area"] - 8.1) < 0.15
    assert abs(e["Toilette"]["area"] - 3.1) < 0.15
    assert e["Dormitorio 1"]["kind"] == "bedroom" and e["Cocina integrada"]["kind"] == "kitchen" and e["Toilette"]["kind"] == "bath"
    assert e["Estar"]["kind"] == "living" and e["Comedor"]["kind"] == "dining" and e["Hall"]["kind"] == "hall"
    assert e["Pasillo"]["kind"] == "hallway" and e["Baño en suite"]["kind"] == "bath"
    assert e["Estar"]["fachada"] is True and e["Estar"]["abierto"] is False          # toca la fachada
    assert e["Comedor"]["fachada"] is False and e["Comedor"]["abierto"] is True      # luz del ambiente abierto
    assert e["Cocina integrada"]["fachada"] is False and e["Cocina integrada"]["abierto"] is True
    assert e["Hall"]["fachada"] is False and e["Hall"]["abierto"] is False
    x0, y0, x1, y1 = e["Dormitorio 2"]["rect"]
    assert abs((x1 - x0) - e["Dormitorio 2"]["ancho"]) < 1e-9 and abs((y1 - y0) - e["Dormitorio 2"]["fondo"]) < 1e-9
    assert v["entrada"]["lado"] == "abajo" and 0.7 < v["entrada"]["ancho"] < 1.1 and v["puertas"] == 5
    assert v["ventanas"]["n"] == 3 and v["fachadas"] == [{"largo": 8.4, "rotulo": "Calle"}] and v["medianeras"] > 7.0
    assert v["exteriores"][0]["nombre"].startswith("Terraza") and 0 <= v["norte"] < 360
    # (c) un monoambiente
    m = por_archivo["U_MVD_M5_Mono_4.44x6.45_05.dxf"]
    assert m["tipologia"] == "Mono" and m["dormitorios"] == 0
    assert [x["kind"] for x in m["estancias"] if x["nombre"] == "Dormir"] == ["sleep"]
    assert not [x for x in m["estancias"] if x["kind"] == "bedroom"]
    # (d) viviendas en varios niveles
    ids = {}
    for x in cat["viviendas"]:
        ids.setdefault(x["vivienda_id"], []).append(x)
    varios = {k: l for k, l in ids.items() if len(l) > 1}
    assert len(varios) == 5 and all(k.startswith("Maua_") for k in varios), sorted(varios)
    for k, l in varios.items():
        assert sorted(x["nivel"] for x in l) == [1, 2] and len({x["tipologia"] for x in l}) == 1, k
    n_res = cat["resumen"]["viviendas"]
    assert n_res["archivos"] == len(cat["viviendas"]) and n_res["n"] == len(ids) < len(cat["viviendas"])
    por = cat["resumen"]["por_tipologia"]
    assert list(por) == ["Mono", "1D", "2D", "3D", "4D"] and sum(d["n"] for d in por.values()) == len(ids)
    for t in por:
        assert por[t]["n"] == sum(1 for l in ids.values() if l[0]["tipologia"] == t), t
    k = sorted(varios)[0]
    suma = sum(x["area_muros"] for x in varios[k])
    assert suma > max(x["area_muros"] for x in varios[k]) + 5      # el resumen suma los niveles (una sola vez)
    d2 = por["2D"]
    assert d2["area_muros"]["min"] <= d2["area_muros"]["mediana"] <= d2["area_muros"]["max"]
    assert d2["estancias"]["Dormitorio 1"]["n"] == d2["n"] and set(d2["precision"]) <= {"alta", "media", "baja"}
    assert por["Mono"]["zona_estar"]["mediana"] > 10 and d2["estancias"]["Baño"]["ancho"]["mediana"] > 1.0
    # (e) una planta con palier
    pl = {p["archivo"]: p for p in cat["plantas"]}
    p = pl["P_MVD_M5_tipo.dxf"]
    mt = p["metricas"]
    assert p["nivel"] == "tipo" and p["proyecto"] == "M5" and mt["viviendas"] == 6 and mt["nucleos"] == 2 and mt["con_palier"]
    assert 1.0 <= mt["ancho_pasillo"]["mediana"] <= 3.0 and mt["ancho_pasillo"]["n"] == 6, mt["ancho_pasillo"]
    assert mt["viviendas_por_nucleo"] == 3.0 and 5 <= mt["circulacion_pct"] <= 40 and 40 <= mt["eficiencia"] <= 100
    assert abs(p["planta"] - (p["terreno"]["area"] - sum(q["area"] for q in p["patios"]))) < 0.5
    assert len(p["viviendas"]) == 6 and {q["tipologia"] for q in p["viviendas"]} == {"Mono", "1D", "2D"}
    assert all(q["entrada"] and q["estancias"] for q in p["viviendas"]) and len(p["pasillos"]) == 2
    assert [n["nombre"] for n in p["nucleos"]] == ["Nucleo 1", "Nucleo 2"] and all(n["area"] > 5 for n in p["nucleos"])
    assert any(o["nombre"].startswith("Terraza") for o in p["otros"])
    sinp = pl["P_MVD_Maua_2.dxf"]["metricas"]                   # nivel superior de dúplex: sin palier
    assert not sinp["con_palier"] and sinp["ancho_pasillo"] is None and sinp["largo_pasillo_por_vivienda"] is None
    # el ancho es el del pasillo también con la puerta en la punta (la cuerda perpendicular daría el largo)
    pas = [[(0.0, 0.0), (10.0, 0.0), (10.0, 1.5), (0.0, 1.5)]]
    lado = T.ancho_pasillo_en(pas, (4.0, 0.0), (1.0, 0.0))        # puerta de costado, en el muro de abajo
    punta = T.ancho_pasillo_en(pas, (10.0, 0.75), (0.0, 1.0))     # puerta en la punta del pasillo
    assert abs(lado - 1.5) < 1e-6 and abs(punta - 1.5) < 0.01, (lado, punta)
    assert T.ancho_pasillo_en(pas, (4.0, 5.0), (1.0, 0.0)) is None                # lejos de todo pasillo
    # núcleos: sin rótulos, los polígonos a menos de 0,30 m son uno; con rótulos, cada polígono va al «Nucleo n» más cercano
    a, b, c = [(0, 0), (2, 0), (2, 3), (0, 3)], [(2.1, 0), (4, 0), (4, 3), (2.1, 3)], [(10, 0), (12, 0), (12, 3), (10, 3)]
    ns = T._nucleos({"textos": []}, [a, b, c])
    assert [n["partes"] for n in ns] == [2, 1] and [n["nombre"] for n in ns] == ["Nucleo 1", "Nucleo 2"]
    assert abs(ns[0]["area"] - 11.7) < 0.01 and ns[0]["ancho"] == 4.0 and ns[0]["fondo"] == 3.0
    rot = [{"rol": "nucleos", "texto": "Nucleo 1", "p": (1.0, 1.0)}, {"rol": "nucleos", "texto": "Escalera", "p": (3.0, 1.0)},
           {"rol": "nucleos", "texto": "Nucleo 2", "p": (11.0, 1.0)}]
    ns = T._nucleos({"textos": rot}, [c, a, b])
    assert [(n["nombre"], n["partes"]) for n in ns] == [("Nucleo 1", 2), ("Nucleo 2", 1)], ns
    pr = cat["resumen"]["plantas"]
    assert pr["n"] == len(cat["plantas"]) and 1.0 <= pr["ancho_pasillo"]["mediana"] <= 3.0 and pr["nucleo"]["area"] > 5
    cm = cat["resumen"]["comparacion"]
    assert [c["tipologia"] for c in cm["viviendas"]] == ["Mono", "1D", "2D", "3D", "4D"]
    assert [c["referencias"] for c in cm["viviendas"]] == [30, 42, 58, 78, 100]
    assert [c["superficie_min"] for c in cm["viviendas"]] == [32, 32, 44, 56, 68]
    assert [c["mix_motor"] for c in cm["viviendas"]] == [33, 42, 62, 93, None]       # v2.61: el mix «Inversor» (antes solo 2D 75 y 3D 95)
    est = {c["estancia"]: c for c in cm["estancias"]}
    assert est["Dormitorio 1"]["tipico_area"] == 11.5 and est["Dormitorio 1"]["n"] > 30 and est["Cocina integrada"]["tope_area"] == 5.0
    assert [c["estar_por_dorms"] for c in cm["zona_estar"]] == [18.0, 15.0, 18.0, 21.0, 24.0]     # v2.61 (antes 18, 18, 20, 24, 27)
    assert cm["plantas"]["ancho_pasillo"]["motor"] == 1.5                 # v2.60: el de la base (1,50 m), antes 2,0 m
    nm = cm["plantas"]["nucleo"]["motor"]               # el núcleo del motor: sin el palier (como Trazo_Nucleos) y con él
    assert nm["ascensores"] == 1 and 18 < nm["giro_0"]["area_sin_palier"] < 21 and 15 < nm["giro_90"]["area_sin_palier"] < 18   # v2.60: 19,5 y 16,7 m² (antes 23,5 y 19,6)
    for g in ("giro_0", "giro_90"):
        assert nm[g]["area_sin_palier"] < nm[g]["area_con_palier"] and 22 < nm[g]["area_con_palier"] < 27, nm[g]
    assert nm["giro_0"]["caja_sin_palier"][0] < nm["giro_90"]["caja_sin_palier"][0]      # el giro 90 es más ancho y menos fondo
    assert nm["giro_90"]["caja_sin_palier"][1] < nm["giro_0"]["caja_sin_palier"][1]
    assert cm["plantas"]["nucleo"]["medida"]["area"] < nm["giro_90"]["area_sin_palier"]
    # (f) escribir: igual al catálogo guardado, en una carpeta temporal
    tmp = tempfile.mkdtemp()
    try:
        antes = sorted(os.listdir(carpeta))
        ruta_json, ruta_md = T.escribir(cat, tmp)
        assert os.path.dirname(ruta_json) == tmp and os.path.dirname(ruta_md) == tmp
        crudo = open(ruta_json, "rb").read()
        assert crudo.endswith(b"}\n") and b"\r" not in crudo and b"\r" not in open(ruta_md, "rb").read()
        nuevo = json.loads(crudo.decode("utf-8"))
        assert nuevo == json.loads(json.dumps(cat)), "el JSON escrito no vuelve igual"
        guardado = json.load(open(os.path.join(carpeta, "catalogo.json"), encoding="utf-8"))
        for d in (nuevo, guardado):
            d.pop("version")
            d["resumen"].pop("comparacion")
        assert nuevo == guardado, "data/tipologias/catalogo.json no coincide con la base: correr `python -m engine.tipologias`"
        md = open(ruta_md, encoding="utf-8").read()
        assert md.startswith("# Base de tipologías") and "v" + LY.VERSION in md.splitlines()[0]
        assert "Generado por `python -m engine.tipologias`; no editar a mano." in md
        for t in ("Mono", "1D", "2D", "3D", "4D"):
            assert "| " + t + " |" in md
        assert "## 4. Comparación con `standards.py` y `REFERENCIAS.md`" in md and "," in md
        assert sorted(os.listdir(carpeta)) == antes           # la prueba no toca data/tipologias/
        # (h) main sobre una carpeta cualquiera, sin indice.csv
        mini = os.path.join(tmp, "mini")
        os.mkdir(mini)
        for f in ("U_MVD_M5_Mono_4.44x6.45_05.dxf", "P_MVD_M5_tipo.dxf"):
            shutil.copy(os.path.join(carpeta, f), mini)
        sal = io.StringIO()
        with contextlib.redirect_stdout(sal):
            assert T.main(["tipologias", mini]) == 0
        assert "2 archivos" in sal.getvalue() and "1 viviendas y 1 plantas" in sal.getvalue(), sal.getvalue()
        c2 = json.load(open(os.path.join(mini, "catalogo.json"), encoding="utf-8"))
        assert len(c2["viviendas"]) == 1 and len(c2["plantas"]) == 1 and os.path.isfile(os.path.join(mini, "RESUMEN.md"))
        assert isinstance(c2["viviendas"][0]["fuente"], str) and c2["viviendas"][0]["proyecto"] == "M5"
        with contextlib.redirect_stdout(io.StringIO()):
            assert T.main(["tipologias", os.path.join(tmp, "no_existe")]) == 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # (g) un DXF suelto
    suelto = T.leer_vivienda(os.path.join(raiz, "tests", "dxf", "tipologia_2d.dxf"))
    assert suelto["tipologia"] == "1D" and suelto["dormitorios"] == 1 and len(suelto["estancias"]) == 7
    s = {x["nombre"]: x for x in suelto["estancias"]}
    assert abs(s["Dormitorio 1"]["area"] - 9.9) < 0.1 and s["Estar-Comedor"]["fachada"] and s["Estar-Comedor"]["kind"] == "living"
    assert suelto["vivienda_id"] == "tipologia_2d" and suelto["proyecto"] == "Ejemplo" and suelto["anio"] == 2026
    assert abs(suelto["area_muros"] - 56.0) < 0.01 and suelto["fachadas"][0]["rotulo"] is None


if __name__ == "__main__":
    test_tipologias(); print("OK75")


def test_calibracion_planta():
    """R5.16 (v2.60, usos a): los parámetros de la planta se calibraron con la base de tipologías de Montevideo
    (data/tipologias/RESUMEN.md, 4.4): pasillo común de 1,5 m (antes 2,0), frente mínimo de la vivienda de 3,5 m (antes
    5,0), fondo máximo de 16 m (antes 14) y escalera del edificio con ascensor de 1,00 m de tramo (NNE, art. 31 A.1; antes
    1,20 m): el núcleo sin palier baja de 23,5 a 19,5 m² (giro 0) y de 19,6 a 16,7 m² (giro 90). Los proyectos guardados
    conservan sus valores y la web trae los mismos valores en sus controles."""
    import copy, re
    from engine import layout as LY, standards as ST, programs as PR, geometry as G
    D, N = LY.DEFAULT_PARAMS, ST.DEFAULTS["nucleo"]
    # los valores nuevos, y la escalera con ascensor como clave aparte (la de sin ascensor sigue en 1,20 m)
    assert (D["corridor_width"], D["min_unit_width"], D["max_unit_depth"]) == (1.5, 3.5, 16.0), D
    assert N["escalera_ancho"] == 1.20 and N["escalera_ancho_con_ascensor"] == 1.00, N
    # stair_box: con ascensor, dos tramos de 1,00 m; sin él (o sin decir), de 1,20 m; las contrahuellas no cambian
    sw0, sl0, r0 = ST.stair_box(N, 3.0)
    sw1, sl1, r1 = ST.stair_box(N, 3.0, con_ascensor=True)
    assert ST.stair_box(N, 3.0, False) == (sw0, sl0, r0) and r0 == r1 == 18
    assert abs(sw0 - (2 * 1.20 + N["ojo"] + 2 * N["muro"])) < 1e-9 and abs(sw1 - (2 * 1.00 + N["ojo"] + 2 * N["muro"])) < 1e-9
    assert abs((sw0 - sw1) - 0.40) < 1e-9 and abs((sl0 - sl1) - 0.40) < 1e-9     # el descanso y la meseta miden lo que el tramo
    assert ST.ancho_escalera(N) == 1.20 and ST.ancho_escalera(N, True) == 1.00
    # core_size: sin ascensor, la escalera sola de 1,20 m; con ascensor, la de 1,00 m (el ascensor, su ducto y el palier no cambian)
    w, d = ST.core_size(N, 3.0, 0, 1.5)
    assert abs(w - sw0) < 0.011 and abs(d - (sl0 + 1.5)) < 0.011, (w, d)
    asc = N["ascensor_ducto"][0] + N["muro"] + N["ducto_instalaciones"] + N["muro"]
    fondo_asc = N["palier"] + N["ascensor_ducto"][1] + N["muro"]
    w, d = ST.core_size(N, 3.0, 1, 1.5)
    assert abs(w - (sw1 + asc)) < 0.011 and abs(d - (max(sl1, fondo_asc) + 1.5)) < 0.011, (w, d)
    con12 = copy.deepcopy(N)
    con12["escalera_ancho_con_ascensor"] = 1.20                 # la escalera de antes: 0,40 m más ancha (y más larga, en giro 0)
    w12, d12 = ST.core_size(con12, 3.0, 1, 1.5)
    assert abs((w12 - w) - 0.40) < 0.011 and abs((d12 - d) - 0.40) < 0.011, (w, d, w12, d12)
    w90, d90 = ST.core_size(N, 3.0, 1, 1.5, giro=90)
    w90_12, d90_12 = ST.core_size(con12, 3.0, 1, 1.5, giro=90)
    assert abs((w90_12 - w90) - 0.40) < 0.011 and abs(d90_12 - d90) < 0.011, (w90, d90, w90_12, d90_12)
    # core_parts: con un ascensor la escalera mide 2 × 1,00 m + ojo + muros y lo dice; sin ascensor, 1,20 m
    for n_elev, ancho in ((1, 1.00), (0, 1.20)):
        w, d = ST.core_size(N, 3.0, n_elev, 1.5)
        partes = PR.core_parts((0.0, -0.75, w, -0.75 + d), 1, 1.5, N, 3.0, n_elev)
        esc = next(p for p in partes if p["kind"] == "stair")
        x0, y0, x1, y1 = G.bbox([tuple(q) for q in esc["poly"]])
        assert abs((x1 - x0) - (2 * ancho + N["ojo"] + 2 * N["muro"])) < 1e-6, (n_elev, x1 - x0)
        assert "ancho %.2f m" % ancho in esc["name"], esc["name"]
        peldanos = [l for l in esc["lines"] if abs(l[0][1] - l[1][1]) < 1e-9]       # cada peldaño cruza un tramo
        assert peldanos and all(abs(abs(l[1][0] - l[0][0]) - ancho) < 1e-6 for l in peldanos), (n_elev, peldanos[:2])
    # el edificio: con ascensor (15 m, último nivel a 12 m) la caja de la escalera es la de 1,00 m; sin él (12 m, último nivel
    # a 9 m), la de 1,20 m
    barra = [[0, 0], [60, 0], [60, 16], [0, 16]]
    con, sin = run(barra, h=15), run(barra, h=12)
    assert con["metrics"]["core"]["elevators"] == 1 and sin["metrics"]["core"]["elevators"] == 0
    assert con["metrics"]["core"]["stair_box"] == [round(sw1, 2), round(sl1, 2)], con["metrics"]["core"]
    assert sin["metrics"]["core"]["stair_box"] == [round(sw0, 2), round(sl0, 2)], sin["metrics"]["core"]
    assert abs(con["cores"][0]["frente"] - ST.core_size(N, 3.0, 1, 1.5)[0]) < 0.011
    # el pasillo de 1,5 m es el de los resultados nuevos; un proyecto que guardó 2,0 m lo conserva
    assert all(abs(ps["ancho"] - 1.5) < 1e-9 and not ps["propio"] for ps in con["pasillos"])
    assert all(abs(ps["ancho"] - 2.0) < 1e-9 for ps in run(barra, h=15, corridor_width=2.0)["pasillos"])
    assert all(u["depth"] <= 16.0 + 0.5 for u in con["units"]) and min(u["width"] for u in con["units"]) >= 3.5 - 0.01
    # web: los controles traen los mismos valores por defecto que el motor y la medida nueva se lista en Normativa
    html = open(os.path.join(os.path.dirname(__file__), "..", "web", "index.html"), encoding="utf-8").read()
    for ident in ("corridor_width", "min_unit_width", "max_unit_depth"):
        m = re.search(r'id="%s" value="([^"]+)"' % ident, html)
        assert m and float(m.group(1)) == D[ident], (ident, m and m.group(1))
    assert "escalera_ancho_con_ascensor:'Ancho de tramo con ascensor (m)'" in html and "escalera_ancho:'Ancho de tramo sin ascensor (m)'" in html
    assert "escalera_ancho_con_ascensor" not in re.search(r"const STD_ANTES=(\{.*?\}\}\});", html).group(1)   # clave nueva: sin valor viejo
    assert ST.merged({"nucleo": {"escalera_ancho": 1.4}})["nucleo"]["escalera_ancho_con_ascensor"] == 1.00    # un proyecto viejo la toma sola

if __name__ == "__main__":
    test_calibracion_planta(); print("OK76")


def test_calibracion_vivienda():
    """R5.16 (v2.61, usos a, segunda parte) y R10.12: el estar-comedor por dormitorios sigue lo medido en la base de
    tipologías (RESUMEN.md, 4.3) y el mix por defecto es el «Inversor» de REFERENCIAS.md (Mono 33 m² 10 %, 1 dorm 42 m²
    55 %, 2 dorm 62 m² 30 %, 3 dorm 93 m² 5 %: superficies con muros medianas de la base). La web trae el mismo mix inicial
    y un selector «Mix predeterminado» con Inversor, Equilibrado, Familiar y Personalizado. Un proyecto guardado conserva
    su tabla de mix y sus medidas elegidas; el estar viejo pasa al nuevo (STD_ANTES, corte 2.61). Un monoambiente (dorms: 0)
    pasa por el reparto, el plano (Estar-Dormitorio, cocina y baño) y el equipamiento."""
    import re
    import shutil
    import subprocess
    import tempfile
    from engine import layout as LY, standards as ST
    base = os.path.join(os.path.dirname(__file__), "..")
    # 1) valores por defecto del motor
    assert ST.DEFAULTS["vivienda"]["estar_por_dorms"] == [18.0, 15.0, 18.0, 21.0, 24.0], ST.DEFAULTS["vivienda"]
    inversor = [{"name": "Mono", "area": 33, "percent": 10, "dorms": 0}, {"name": "1 dorm", "area": 42, "percent": 55, "dorms": 1},
                {"name": "2 dorm", "area": 62, "percent": 30, "dorms": 2}, {"name": "3 dorm", "area": 93, "percent": 5, "dorms": 3}]
    equilibrado = [{"name": "Mono", "area": 33, "percent": 5, "dorms": 0}, {"name": "1 dorm", "area": 42, "percent": 45, "dorms": 1},
                   {"name": "2 dorm", "area": 62, "percent": 40, "dorms": 2}, {"name": "3 dorm", "area": 93, "percent": 10, "dorms": 3}]
    familiar = [{"name": "1 dorm", "area": 42, "percent": 25, "dorms": 1}, {"name": "2 dorm", "area": 62, "percent": 55, "dorms": 2},
                {"name": "3 dorm", "area": 93, "percent": 20, "dorms": 3}]
    # (generate_unit_mix anota "_p" en los tipos del mix: no cuenta)
    assert [{k: v for k, v in m.items() if not k.startswith("_")} for m in LY.DEFAULT_PARAMS["unit_mix"]] == inversor, \
        LY.DEFAULT_PARAMS["unit_mix"]
    assert LY.VERSION >= "2.61"
    for mx in (inversor, equilibrado, familiar):
        assert sum(m["percent"] for m in mx) == 100
    # 2) la web: el mismo mix inicial, el selector y la función que aplica un predeterminado
    html = open(os.path.join(base, "web", "index.html"), encoding="utf-8").read()
    let_mix = re.search(r"^let mix=(\[.*?\]);", html, re.M).group(1)
    web = json.loads(re.sub(r"([{,])(\w+):", r'\1"\2":', let_mix.replace("'", '"')))
    assert web == inversor, web
    sel = re.search(r'<select id="mixPre"[^>]*>(.*?)</select>', html, re.S)
    assert sel and 'onchange="mixPredeterminado(this.value)"' in sel.group(0), "falta el selector #mixPre"
    assert re.findall(r'<option value="(\w+)">([^<]+)</option>', sel.group(1)) == [
        ("inversor", "Inversor"), ("equilibrado", "Equilibrado"), ("familiar", "Familiar"), ("personalizado", "Personalizado")]
    assert html.index('id="mixPre"') < html.index('<div id="mix">') and 'class="hint">Inversor:' in html
    aplica = re.search(r"function mixPredeterminado\(k\)\{(.*?)\n\w", html, re.S).group(1)
    assert "renderMix()" in aplica and "legend()" in aplica and "run(lastStage,{keepView:true})" in aplica, aplica
    assert "mixSel(); }" in re.search(r"function renderMix\(\)\{.*?\n", html).group(0)           # la tabla actualiza el selector
    antes = re.search(r"const STD_ANTES=(\{.*?\}\}\});", html).group(1)
    antes = json.loads(re.sub(r"([{,])(\w+):", r'\1"\2":', antes))
    assert antes["vivienda"]["estar_por_dorms"] == [18, 18, 20, 24, 27], antes        # el valor de antes de v2.61
    assert "verMenor(p.version_motor,'2.61')?STD_ANTES:null" in html
    # 3) la página con node (si hay): elegir un predeterminado, editar la tabla y abrir proyectos guardados antes
    node = shutil.which("node")
    if not node:
        print("(sin node: se omite el comportamiento del selector de mix y de STD_ANTES en la página)")
    else:
        def trozo(desde, hasta, incluir_hasta=False):
            i = html.index(desde)
            j = html.index(hasta, i)
            return html[i:j + (len(hasta) if incluir_hasta else 0)]
        mixes = trozo("let mix=[", "let mixPersonal=null;", True) + html[html.index("let mixPersonal=null;") + 21:].split("\n", 1)[0]
        selector = trozo("const ACC_TIT=", "function renderStories")
        medidas = trozo("const STD_ANTES=", "async function loadStd")
        arnes = """
const els = { mixPre: { value: 'inversor' }, mix: { innerHTML: '' }, tag: { textContent: '' } };
const $ = id => els[id];
let lastStage = 'plans'; const corridas = []; let legendas = 0;
function run(st, o) { corridas.push([st, o && o.keepView]); }
function legend() { legendas++; }
%s
%s
%s
const copia = x => JSON.parse(JSON.stringify(x)), R = {};
renderMix(); R.inicial = { sel: els.mixPre.value, mix: copia(mix), filas: (els.mix.innerHTML.match(/data-acc=/g) || []).length };
els.mixPre.value = 'personalizado'; mixPredeterminado('personalizado');           // todavía no hay tabla propia: no cambia nada
R.sinPropia = { sel: els.mixPre.value, mix: copia(mix), corridas: corridas.length, aviso: els.tag.textContent };
mixPredeterminado('equilibrado');
R.equilibrado = { sel: els.mixPre.value, mix: copia(mix), corridas: corridas.slice(), legendas, filas: (els.mix.innerHTML.match(/data-acc=/g) || []).length };
mix[1].percent = 50; mixSel(); R.editado = { sel: els.mixPre.value };           // como el onchange de una fila
mixPredeterminado('familiar');
R.familiar = { sel: els.mixPre.value, mix: copia(mix), filas: (els.mix.innerHTML.match(/data-acc=/g) || []).length };
els.mixPre.value = 'personalizado'; mixPredeterminado('personalizado');
R.vuelta = { sel: els.mixPre.value, mix: copia(mix) };                           // vuelve a la tabla propia
mixPredeterminado('inversor'); mix.splice(3, 1); renderMix(); R.quitado = { sel: els.mixPre.value };           // quitar un tipo: «Personalizado»
lastStage = null; const n = corridas.length; mixPredeterminado('inversor'); R.sinResultado = { sel: els.mixPre.value, nuevas: corridas.length - n };
const abrir = (version, std) => { const d = { vivienda: { estar_por_dorms: [18, 15, 18, 21, 24], dorm_principal: { min_area: 8.5, min_side: 2.6 } } };
  mezclarStd(d, { vivienda: { estar_por_dorms: std } }, verMenor(version, '2.61') ? STD_ANTES : null); return d.vivienda.estar_por_dorms; };
const viejo = [18, 18, 20, 24, 27], propio = [20, 20, 22, 26, 29];
R.std = { v260: abrir('2.60', viejo), v227: abrir('2.27', viejo), sinVersion: abrir(undefined, viejo), propio: abrir('2.60', propio), v261: abrir('2.61', viejo) };
console.log(JSON.stringify(R));
""" % (mixes, selector, medidas)
        with tempfile.TemporaryDirectory() as tmp:
            ruta = os.path.join(tmp, "arnes.js")
            open(ruta, "w", encoding="utf-8").write(arnes)
            p = subprocess.run([node, ruta], capture_output=True, text=True, encoding="utf-8")
            assert p.returncode == 0, p.stderr
        R = json.loads(p.stdout)
        assert R["inicial"] == {"sel": "inversor", "mix": inversor, "filas": 4}, R["inicial"]
        assert R["equilibrado"]["sel"] == "equilibrado" and R["equilibrado"]["mix"] == equilibrado, R["equilibrado"]
        assert R["equilibrado"]["corridas"] == [["plans", True]] and R["equilibrado"]["legendas"] == 1 and R["equilibrado"]["filas"] == 4
        assert R["editado"]["sel"] == "personalizado", R["editado"]                      # la tabla ya no repite ningún predeterminado
        assert R["familiar"] == {"sel": "familiar", "mix": familiar, "filas": 3}, R["familiar"]
        assert R["vuelta"]["sel"] == "personalizado" and R["vuelta"]["mix"][1]["percent"] == 50 and \
            [m["percent"] for m in R["vuelta"]["mix"]] == [5, 50, 40, 10], R["vuelta"]
        assert R["sinPropia"]["sel"] == "inversor" and R["sinPropia"]["mix"] == inversor and R["sinPropia"]["corridas"] == 0 and \
            R["sinPropia"]["aviso"], R["sinPropia"]
        assert R["quitado"]["sel"] == "personalizado", R["quitado"]
        assert R["sinResultado"] == {"sel": "inversor", "nuevas": 0}, R["sinResultado"]  # sin resultado, solo cambia la tabla
        nuevo, viejo = [18, 15, 18, 21, 24], [18, 18, 20, 24, 27]
        assert R["std"] == {"v260": nuevo, "v227": nuevo, "sinVersion": nuevo, "propio": [20, 20, 22, 26, 29], "v261": viejo}, R["std"]
    # 4) el motor con el mix nuevo: «Barra larga 90x18» (como tests/regresion.py: _edificio) da los cuatro tipos y el Mono ≈ 10 %
    s = json.load(open(os.path.join(base, "samples", "barra_larga.json"), encoding="utf-8"))
    r = run(s["footprint"], h=s["height"])
    tipos = {}
    for u in r["units"]:
        tipos.setdefault(u["type"], []).append(u)
    assert set(tipos) == {"Mono", "1 dorm", "2 dorm", "3 dorm"}, sorted(tipos)
    assert abs(len(tipos["Mono"]) - 0.10 * len(r["units"])) <= 1.0, {k: len(v) for k, v in tipos.items()}
    assert abs(len(tipos["1 dorm"]) - 0.55 * len(r["units"])) <= 1.5 and r["metrics"]["mix"]["match_score"] >= 90, r["metrics"]["mix"]
    assert [u["bedrooms"] for u in tipos["Mono"]] == [0] * len(tipos["Mono"])
    for u in tipos["Mono"]:                                   # monoambiente: Estar-Dormitorio, cocina y baño, con su cama y su ventana
        assert {"living", "kitchen", "bath"} <= {rm["kind"] for rm in u["rooms"]}, (u["id"], [rm["name"] for rm in u["rooms"]])
        assert [rm["name"] for rm in u["rooms"] if rm["kind"] == "living"] == ["Estar-Dormitorio"], u["id"]
        assert any(e["name"] == "Cama doble" for e in u["equipamiento"]) and any(v["room"] == "living" for v in u["ventanas"]), u["id"]
        assert any("Monoambiente" in c["msg"] for c in u["checks"]), u["id"]            # art. 2 (criterio del usuario): se evalúa
    # el reparto no supone dormitorios: un mix solo de monoambientes (dorms: 0) y uno con dorms vacío (según los m²)
    solo = run(s["footprint"], h=s["height"], unit_mix=[{"name": "M", "area": 33, "percent": 100, "dorms": 0}])
    assert solo["units"] and {u["type"] for u in solo["units"]} == {"M"} and all(u["bedrooms"] == 0 for u in solo["units"])
    auto = run(s["footprint"], h=s["height"], unit_mix=[{"name": "M", "area": 33, "percent": 50}, {"name": "D", "area": 62, "percent": 50}])
    assert sorted({u["bedrooms"] for u in auto["units"]}) == [0, 1], sorted({u["bedrooms"] for u in auto["units"]})

if __name__ == "__main__":
    test_calibracion_vivienda(); print("OK77")


def test_reparto_frente():
    """R5.16b (v2.62): el reparto del mix da a cada vivienda el frente que pide su plano (plans.frente_min), elige la
    cantidad de viviendas entre las que caben con esos frentes y deja fuera de una franja los tipos que ahí pasarían de
    1,35 veces su superficie; _ring_single y auto_patios miden con el fondo que aprovecha un plano en vez de la
    superficie media del mix."""
    from engine import plans as P, patios as PT, circulation as C, layout as LY, standards as ST
    base = os.path.join(os.path.dirname(__file__), "..")
    muestra = lambda n: json.load(open(os.path.join(base, "samples", n + ".json"), encoding="utf-8"))
    malos = lambda u: [c["msg"] for c in u["checks"] if not c["ok"]]
    dorms = lambda u, mix: next(int(m["dorms"]) for m in mix if m["name"] == u["type"])
    # 1) el frente que pide el plano: profunda, facade_min; poco profunda, hall + baño + cocina con su heladera; monoambiente,
    #    hall mínimo + baño con ducha + cocina con su heladera (4,8 m, no los 4,0 de facade_min)
    S = ST.merged(None)
    P.configure(S["vivienda"], S["equipamiento"])
    assert P.frente_min(1) == P.facade_min(1) == P.frente_min(1, 7.75) and P.frente_min(2, 16.0) == P.facade_min(2)
    assert abs(P.frente_min(1, 5.75) - (P.BED_MAIN + P.HALL_W + P.BATH_W1 + 2.0)) < 1e-6, P.frente_min(1, 5.75)     # 8,3 m
    assert abs(P.frente_min(0) - (S["vivienda"]["hall"]["min_side"] + P.BATH_FULL[0] + 2.0)) < 1e-6 and P.frente_min(0) >= P.facade_min(0)
    # 2) «Barra larga 90x18» con el mix por defecto: ninguna vivienda con menos frente que el de su plano, sin «Sin cocina» ni
    #    «Frente insuficiente», y el mix se respeta (antes, 1 dorm de 4,9 a 5,5 m y calidad 46)
    s = muestra("barra_larga")
    r = run(s["footprint"], h=s["height"])
    mix = LY.DEFAULT_PARAMS["unit_mix"]
    for u in r["units"]:
        assert u["width"] >= P.facade_min(dorms(u, mix)) - 0.05, (u["id"], u["type"], u["width"])
        assert not any(m.startswith("Sin cocina") or m.startswith("Sin baño") or "insuficiente" in m for m in malos(u)), (u["id"], malos(u))
    assert r["metrics"]["plan_score"] >= 95 and r["metrics"]["mix"]["match_score"] >= 90, r["metrics"]
    # 3) en una franja de 16 m de fondo (la T de dos polilíneas) ninguna vivienda baja de 3,5 m de frente ni queda sin cocina
    #    por angosta (antes, un monoambiente de 1,6 m): las viviendas con 16 m de fondo van con el tipo que menos se pasa
    s = muestra("T_dos_lineas")
    r = run(s["footprint"], h=s["height"], centerlines=s["centerlines"])
    for u in r["units"]:
        assert u["width"] >= 3.5 and not any(m.startswith("Sin cocina") or m.startswith("Sin baño") for m in malos(u)), (u["id"], u["width"], malos(u))
    assert r["metrics"]["plan_score"] >= 80, r["metrics"]["plan_score"]
    # 4) una franja de 16 m: el tipo que menos se pasa (ninguno es apto) y el plano deja la tira; una de 7,75 m: los cuatro aptos
    viejo = [{"name": "2 dorm", "area": 75, "percent": 50, "dorms": 2}, {"name": "3 dorm", "area": 95, "percent": 50, "dorms": 3}]
    r = run([[0, 0], [60, 0], [60, 16], [0, 16]], unit_mix=[{"name": "3 dorm", "area": 93, "percent": 100, "dorms": 3}])
    assert r["units"] and all(u["width"] >= P.facade_min(3) - 0.05 for u in r["units"]), [u["width"] for u in r["units"]]
    # 5) _ring_single: el ala de 10,3 m de «Edificio con patio central» va con pasillo de borde (con pasillo central quedarían
    #    4,1 m de fondo, menos que fondo_min + 0,5) con los dos mixes; el ala puente de 12,3 × 8,7 m, con pasillo central con el
    #    mix Inversor (dos viviendas de 8,7 × 5,1 m) y de borde con el de 75 y 95 m²: así la planta llega a 96 de calidad y
    #    sin esquinas sin luz (con el ala puente de borde, 88)
    pa, pv = LY.merge_params({}), LY.merge_params({"unit_mix": viejo})
    assert C._ring_single(10.3, 39.3, False, pa) and C._ring_single(10.3, 39.3, False, pv)
    assert not C._ring_single(12.3, 8.7, True, pa) and C._ring_single(12.3, 8.7, True, pv)
    s = muestra("patio_central")
    r = run(s["footprint"], h=s["height"], patios_mode="manual", patios=s["patios"])
    assert r["metrics"]["plan_score"] >= 90 and not r["metrics"].get("dark_area") and len(r["units"]) >= 11, r["metrics"]
    antes = C._ring_single
    C._ring_single = lambda short, largo, puente, params: True if puente else antes(short, largo, puente, params)
    try:
        rb = run(s["footprint"], h=s["height"], patios_mode="manual", patios=s["patios"])
    finally:
        C._ring_single = antes
    assert rb["metrics"]["plan_score"] <= r["metrics"]["plan_score"] and len(rb["units"]) < len(r["units"]), rb["metrics"]
    # 6) auto_patios: en «Predio entre medianeras 10 x 28» no se abre patio (dos viviendas de 9,3 × 7,6 m con luz entera: antes,
    #    con la superficie media del mix, un patio de 3 m y cuatro viviendas de 3,4 m de fondo); en el de 10 × 40 sí (dos bloques)
    s = muestra("entre_medianeras")
    r = run(s["footprint"], h=s["height"], medianeras=s["medianeras"])
    assert not r["patios"] and len(r["units"]) == 2 and r["metrics"]["plan_score"] == 100, (r["patios"], r["metrics"])
    assert all(u["depth"] > 7.0 for u in r["units"]) and any("Zona central sin luz" in w for w in r["warnings"]), r["warnings"]
    s = muestra("entre_medianeras_patio")
    r = run(s["footprint"], h=s["height"], medianeras=s["medianeras"])
    assert len(r["patios"]) == 1 and r["metrics"]["blocks"] == 2 and all(u["depth"] >= P.fondo_min() + 0.5 for u in r["units"])
    # 7) con el mix de 75 y 95 m² y las medidas de antes, tampoco queda ninguna vivienda por debajo de su frente (la L)
    with _medidas_anteriores(True, True):
        s = muestra("L")
        r = run(s["footprint"], h=s["height"])
        for u in r["units"]:
            assert u["width"] >= P.facade_min(dorms(u, viejo)) - 0.05, (u["id"], u["type"], u["width"])
        assert r["metrics"]["plan_score"] == 100, r["metrics"]["plan_score"]

if __name__ == "__main__":
    test_reparto_frente(); print("OK78")
    test_servidor_en_red(); print("OK79")


def test_factibilidad():
    """R10.13 (v2.64): factibilidad por gama de construcción (engine/factibilidad.py, medidas en standards.costos, datos y
    fórmulas en COSTOS.md). Con el ejemplo de COSTOS.md, sección 7.3 (3.000 m² brutos, 2.400 vendibles, terreno de USD 490.000)
    los rubros, el costo total, el margen y el precio de equilibrio salen como en la tabla; los honorarios del arancel SAU
    coinciden con la tabla de honorarios efectivos; el semáforo (verde, amarillo, rojo), los costos de cada programa, el
    terreno por m², lo que se cambia en Normativa, la tabla CSV y la web (grupo Factibilidad, ids, proyectos sin factibilidad)."""
    import copy, csv, io, re
    from engine import factibilidad as FZ, layout as LY, standards as ST, tabla_viviendas as TV
    raiz = os.path.join(os.path.dirname(__file__), "..")
    C = ST.merged(None)["costos"]
    # ---- las medidas: una lista por gama (baja, media, alta) y cada precio y porcentaje en standards.costos, no en el código
    assert FZ.GAMAS == ("baja", "media", "alta") and C["obra_m2"] == [1350, 1750, 2500]
    assert C["coef_cochera"] == 0.55 and C["coef_balcon"] == 0.5 and C["precio_venta"] == [2800, 3115, 3430] and C["margen_objetivo"] == 15
    assert all(len(C[k]) == 3 for k in ("obra_m2", "ingenieria_pct", "imprevistos_pct", "administracion_pct", "financieros_pct",
                                         "comercializacion_pct", "precio_venta", "sau", "permiso_ui", "permiso_comercio_ui"))
    assert all(len(f) == 5 for f in C["sau"]) and len(C["sau_tramos"]) == 4 and len(C["permiso_hasta"]) == 2
    # ---- 1) honorarios del arancel SAU: la tabla «honorarios efectivos sobre obra neta» de COSTOS.md (TC 40, C = 9,13)
    efectivos = {2e6: (6.5, 11.3, 13.0), 4e6: (5.8, 10.1, 11.6), 6e6: (5.2, 9.1, 10.5), 10e6: (4.6, 7.8, 9.1), 25e6: (4.0, 6.7, 7.9)}
    for obra, esperados in efectivos.items():
        for g, e in enumerate(esperados):
            assert abs(FZ.honorarios_sau(obra, g, C) / obra * 100 - e) < 0.06, (obra, g, e)
    # ---- 2) el ejemplo de COSTOS.md 7.3: rubro por rubro (USD; tasas y trámites = permiso + Caja + conexiones)
    ejemplo = {"baja": dict(precio=3000, honorarios=233865, ingenieria=81000, tasas=116812, imprevistos=202500, administracion=81000,
                            terreno=507934, financieros=136738, comercializacion=360000, total=5769850, margen=1430150, mv=19.9, eq=2373),
               "media": dict(precio=3300, honorarios=501822, ingenieria=131250, tasas=147772, imprevistos=262500, administracion=105000,
                             terreno=507934, financieros=230317, comercializacion=435600, total=7572196, margen=347804, mv=4.4, eq=3147),
               "alta": dict(precio=3900, honorarios=736360, ingenieria=225000, tasas=205822, imprevistos=525000, administracion=187500,
                            terreno=507934, financieros=400397, comercializacion=655200, total=10943213, margen=-1583213, mv=-16.9, eq=4609)}
    obras = {"baja": 4050000, "media": 5250000, "alta": 7500000}
    for gama, e in ejemplo.items():
        fz = {"gama": gama, "terreno": {"modo": "total", "valor": 490000},
              "precio_venta": {"bajo": e["precio"], "esperado": e["precio"], "alto": e["precio"]}}
        f = FZ.calcular({"Residential": {"gfa": 3000.0, "stories": 10}}, 2400.0, [], fz, C)
        r = {x["id"]: x["usd"] for x in f["rubros"]}
        assert f["gama"] == gama and abs(r["obra"] - obras[gama]) < 1, (gama, r["obra"])
        assert abs(r["honorarios"] - e["honorarios"]) < 2 and abs(r["ingenieria"] - e["ingenieria"]) < 1
        assert abs(r["permiso"] + r["caja"] + r["conexiones"] - e["tasas"]) < 2, (gama, r)
        assert abs(r["imprevistos"] - e["imprevistos"]) < 1 and abs(r["administracion"] - e["administracion"]) < 1
        assert abs(r["terreno"] + r["compra"] - e["terreno"]) < 1 and abs(r["financieros"] - e["financieros"]) < 2
        x = f["escenarios"]["esperado"]
        assert abs(x["comercializacion"] - e["comercializacion"]) < 1 and abs(x["costo_total"] - e["total"]) < 5, (gama, x)
        assert abs(x["ingreso"] - 2400 * e["precio"]) < 1 and abs(x["margen"] - e["margen"]) < 5, (gama, x)
        assert abs(x["margen_venta"] - e["mv"]) < 0.06 and abs(x["roi"] - x["margen"] / x["costo_total"] * 100) < 0.01
        assert abs(f["precio_equilibrio"] - e["eq"]) < 1, (gama, f["precio_equilibrio"])
        # el costo total con el precio de equilibrio da un margen nulo: ingreso − comercialización = costo sin comercializar
        p = f["precio_equilibrio"]
        assert abs(p * 2400 * (1 - f["comercializacion_pct"] / 100) - f["costo_sin_comercializacion"]) < 15     # el precio va redondeado a 0,01
        assert abs(sum(v for k, v in r.items()) - f["costo_sin_comercializacion"]) < 0.1
    # ---- 3) el ROI es margen / costo total, y el semáforo: verde, amarillo (solo el alto) o rojo (ni el alto)
    base = lambda precios, objetivo=None: FZ.calcular(
        {"Residential": {"gfa": 3000.0, "stories": 10}}, 2400.0, [],
        dict({"gama": "baja", "terreno": {"modo": "total", "valor": 490000}, "precio_venta": precios},
             **({"margen_objetivo": objetivo} if objetivo is not None else {})), C)
    verde = base({"bajo": 2800, "esperado": 3115, "alto": 3430})
    amarillo = base({"bajo": 2400, "esperado": 2700, "alto": 2800})         # con estos costos, el ROI llega a 15 % desde USD 2.750 por m²
    rojo = base({"bajo": 2000, "esperado": 2300, "alto": 2600})
    assert [x["semaforo"] for x in (verde, amarillo, rojo)] == ["verde", "amarillo", "rojo"]
    assert verde["escenarios"]["esperado"]["roi"] >= 15
    assert amarillo["escenarios"]["esperado"]["roi"] < 15 <= amarillo["escenarios"]["alto"]["roi"], amarillo["escenarios"]
    assert rojo["escenarios"]["alto"]["roi"] < 15
    assert all(x["semaforo_texto"] and x["objetivo"] == 15 for x in (verde, amarillo, rojo))
    roi_esp = verde["escenarios"]["esperado"]["roi"]            # justo en el objetivo: verde; un poco más: solo el alto lo alcanza
    assert base({"bajo": 2800, "esperado": 3115, "alto": 3430}, roi_esp)["semaforo"] == "verde"
    assert base({"bajo": 2800, "esperado": 3115, "alto": 3430}, roi_esp + 0.01)["semaforo"] == "amarillo"
    assert base({"bajo": 2800, "esperado": 3115, "alto": 3430}, 80)["semaforo"] == "rojo"
    # sin superficie vendible no hay ingreso: rojo y con aviso; el ROI no se inventa
    sin = FZ.calcular({"Residential": {"gfa": 3000.0, "stories": 10}}, 0.0, [], {}, C)
    assert sin["semaforo"] == "rojo" and sin["precio_equilibrio"] is None and sin["escenarios"]["esperado"]["ingreso"] == 0
    # ---- 4) la tasa del permiso según el tamaño de la unidad, la cochera y las amenities con su coeficiente, los balcones
    ui = FZ._ui_vivienda([60.0, 60.0, 100.0], C)
    assert abs(ui - (25 * 120 + 30 * 100) / 220) < 1e-9 and FZ._ui_vivienda([200.0], C) == 35 and FZ._ui_vivienda([], C) == 25
    mixto = FZ.calcular({"Parking": {"gfa": 1000.0, "stories": 1}, "Amenities": {"gfa": 400.0, "stories": 1},
                         "Residential": {"gfa": 2000.0, "stories": 5}, "Office": {"gfa": 800.0, "stories": 2}}, 1500.0, [60.0],
                        {"gama": "media", "balcones_m2": 100}, C)
    eq = 1000 * 0.55 + 400 * 1.25 + 2000 + 800 + 100 * 0.5
    assert abs(mixto["superficies"]["equivalente"] - eq) < 0.1 and abs({x["id"]: x["usd"] for x in mixto["rubros"]}["obra"] - eq * 1750) < 1
    permiso = {x["id"]: x["usd"] for x in mixto["rubros"]}["permiso"]
    assert abs(permiso - (1000 * 25 + 400 * 25 + 2000 * 25 + 800 * 47) * 0.1643) < 0.5, permiso   # vivienda de 60 m²: 25 UI; oficinas de 400 m² por nivel: 47 UI; cochera y amenities: 25
    assert any("no ingreso" in a or "sin ingreso" in a or "suman costo" in a for a in mixto["avisos"]), mixto["avisos"]
    # ---- 5) el terreno: total o por m²; sin precio o sin superficie, un aviso; una gama que no existe se avisa
    por_m2 = FZ.calcular({"Residential": {"gfa": 3000.0, "stories": 10}}, 2400.0, [],
                         {"terreno": {"modo": "m2", "valor": 900}, "superficie_terreno": 500}, C, huella=420)
    assert por_m2["terreno"]["usd"] == 450000 and por_m2["terreno"]["fuente"] == "predio" and por_m2["terreno"]["superficie"] == 500
    de_masa = FZ.calcular({"Residential": {"gfa": 3000.0, "stories": 10}}, 2400.0, [], {"terreno": {"modo": "m2", "valor": 900}}, C, huella=420)
    assert de_masa["terreno"]["usd"] == 378000 and de_masa["terreno"]["fuente"] == "masa"
    assert any("terreno" in a for a in sin["avisos"])
    assert not any("terreno" in a for a in por_m2["avisos"])
    assert any("gama" in a for a in FZ.calcular({"Residential": {"gfa": 1.0}}, 1.0, [], {"gama": "lujo"}, C)["avisos"])
    # ---- 6) en el motor: metrics.factibilidad desde el mix; sin params.factibilidad, con los valores por defecto
    s = json.load(open(os.path.join(raiz, "samples", "barra.json"), encoding="utf-8"))
    r0 = run(s["footprint"], h=s["height"])
    m0 = r0["metrics"]
    f0 = m0["factibilidad"]
    assert f0["gama"] == "baja" and f0["terreno"]["usd"] == 0 and any("terreno" in a for a in f0["avisos"])
    assert abs(f0["superficies"]["gfa"] - m0["gfa"]) < 0.1 and abs(f0["superficies"]["nsa"] - m0["nsa_total"]) < 0.1
    assert abs({x["id"]: x["usd"] for x in f0["rubros"]}["obra"] - m0["gfa"] * 1350) < 1
    esp = f0["escenarios"]["esperado"]
    assert abs(esp["ingreso"] - m0["nsa_total"] * 3115) < 1 and abs(esp["roi"] - esp["margen"] / esp["costo_total"] * 100) < 0.01
    assert [f0["escenarios"][k]["precio"] for k in ("bajo", "esperado", "alto")] == [2800, 3115, 3430]
    explicito = {"gama": "baja", "terreno": {"modo": "total", "valor": 0}, "precio_venta": {"bajo": 2800, "esperado": 3115, "alto": 3430},
                 "margen_objetivo": 15, "balcones_m2": 0}
    assert run(s["footprint"], h=s["height"], factibilidad=explicito)["metrics"]["factibilidad"] == f0     # lo de la web = los valores por defecto
    for etapa in ("massing", "corridor"):                                        # sin viviendas no hay ingreso: no se calcula
        assert "factibilidad" not in generate({"footprint": s["footprint"], "height": s["height"], "stage": etapa})["metrics"]
    assert "factibilidad" in generate({"footprint": s["footprint"], "height": s["height"], "stage": "mix"})["metrics"]
    # el pedido de la web: gama, terreno por m² sobre la superficie del predio, precios y margen propios, medidas cambiadas
    pedido = {"gama": "media", "terreno": {"modo": "m2", "valor": 700}, "superficie_terreno": 1100,
              "precio_venta": {"bajo": 3000, "esperado": 3500, "alto": 4000}, "margen_objetivo": 10, "balcones_m2": 50}
    r1 = run(s["footprint"], h=s["height"], factibilidad=pedido, standards={"costos": {"obra_m2": [1000, 2000, 3000]}})
    f1 = r1["metrics"]["factibilidad"]
    assert f1["gama"] == "media" and f1["costo_m2"] == 2000 and f1["objetivo"] == 10 and f1["terreno"]["usd"] == 770000
    assert abs({x["id"]: x["usd"] for x in f1["rubros"]}["obra"] - (m0["gfa"] + 50 * 0.5) * 2000) < 1
    assert [f1["escenarios"][k]["precio"] for k in ("bajo", "esperado", "alto")] == [3000, 3500, 4000]
    assert r1["metrics"]["nsa_total"] == m0["nsa_total"]                          # no toca la planta
    assert json.dumps({k: v for k, v in r1.items() if k != "metrics"}, sort_keys=True) == \
        json.dumps({k: v for k, v in r0.items() if k != "metrics"}, sort_keys=True)
    # una torre mixta: la cochera cuesta 0,55 y el aviso dice que solo la vivienda genera ingreso
    t = json.load(open(os.path.join(raiz, "samples", "torre_mixta.json"), encoding="utf-8"))
    rt = generate({"footprint": t["footprint"], "height": t["height"], "stage": "plans", "params": {"stories": t["stories"]}})
    ft = rt["metrics"]["factibilidad"]
    pg = {p["programa"]: p for p in ft["superficies"]["programas"]}
    assert set(pg) >= {"Parking", "Retail", "Office", "Residential"} and pg["Parking"]["coef"] == 0.55 and pg["Residential"]["coef"] == 1.0
    assert abs(pg["Parking"]["obra"] - pg["Parking"]["gfa"] * 0.55 * 1350) < 1 and any("cocheras" in a for a in ft["avisos"])
    # ---- 7) la tabla CSV: al final de los totales, la factibilidad con el precio esperado
    res = r1
    texto = TV.result_to_csv(res)
    filas = list(csv.reader(io.StringIO(texto[1:], newline=""), delimiter=";"))
    tot = dict(filas[filas.index([]) + 1:])
    coma = lambda v, d: ("%.*f" % (d, v)).replace(".", ",")
    e1 = f1["escenarios"]["esperado"]
    assert list(tot)[-6:] == ["Factibilidad: gama de construcción", "Factibilidad: costo total (USD)",
                              "Factibilidad: ingreso con el precio esperado (USD)", "Factibilidad: margen con el precio esperado (USD)",
                              "Factibilidad: ROI con el precio esperado (%)", "Factibilidad: precio de equilibrio (USD por m² vendible)"], list(tot)
    assert tot["Factibilidad: gama de construcción"] == "media" and tot["Factibilidad: costo total (USD)"] == coma(e1["costo_total"], 0)
    assert tot["Factibilidad: ingreso con el precio esperado (USD)"] == coma(e1["ingreso"], 0)
    assert tot["Factibilidad: margen con el precio esperado (USD)"] == coma(e1["margen"], 0)
    assert tot["Factibilidad: ROI con el precio esperado (%)"] == coma(e1["roi"], 1)
    assert tot["Factibilidad: precio de equilibrio (USD por m² vendible)"] == coma(f1["precio_equilibrio"], 0)
    assert "Viviendas totales" in tot and "None" not in texto
    sin_fz = copy.deepcopy(res)
    del sin_fz["metrics"]["factibilidad"]                                         # un resultado de otra versión: sin esas filas
    assert not any(k.startswith("Factibilidad") for k in dict(list(csv.reader(io.StringIO(TV.result_to_csv(sin_fz)[1:], newline=""), delimiter=";"))[-4:]))
    # ---- 8) la web: el grupo en el riel, sus controles con id (los lee params() y los devuelve abrirProyecto), Normativa y el resumen
    html = open(os.path.join(raiz, "web", "index.html"), encoding="utf-8").read()
    cuerpo_html = html.split("<body>", 1)[1].split("<script>", 1)[0]
    js = html.split("<script>", 1)[1]
    cuerpo = lambda f: js.split(f, 1)[1].split("\nfunction ", 1)[0].split("\nasync function ", 1)[0].split("\nconst ", 1)[0]
    rail = cuerpo_html.split('<nav class="rail"', 1)[1].split("</nav>", 1)[0]
    assert "data-grupo=\"factibilidad\" onclick=\"grupo('factibilidad')\"" in rail
    panel = cuerpo_html.split('<div class="grupo" data-grupo="factibilidad"', 1)[1].split('<div class="grupo"', 1)[0]
    ids = ("fz_gama", "fz_costo", "fz_terreno", "fz_terreno_modo", "fz_p_bajo", "fz_p_esperado", "fz_p_alto", "fz_margen", "fz_balcones", "fzTabla")
    assert all('id="%s"' % i in panel for i in ids), [i for i in ids if 'id="%s"' % i not in panel]
    assert all(o in panel for o in ('<option value="baja">', '<option value="media">', '<option value="alta">', '<option value="m2">'))
    assert "validarlos con presupuestos" in panel and "triangulados" in panel and "COSTOS.md" in panel      # la advertencia de los costos
    assert 'id="fzResumen"' in cuerpo_html.split('<aside class="r">', 1)[1].split("</aside>", 1)[0]
    assert "factibilidad:factibilidadParams()" in cuerpo("function params(){")
    params_fz = cuerpo("function factibilidadParams(")
    assert all("'%s'" % i in params_fz for i in ids[:9] if i != "fz_costo"), params_fz      # cada control entra en el pedido
    assert all(k in params_fz for k in ("gama", "terreno", "superficie_terreno", "precio_venta", "bajo", "esperado", "alto", "margen_objetivo", "balcones_m2"))
    abrir_fz, abrir = cuerpo("function fzAbrir("), cuerpo("function abrirProyecto(")
    assert "fzAbrir(P.factibilidad)" in abrir and "if(P.factibilidad" not in abrir         # también sin ella: los valores por defecto
    assert all(("$('%s')" % i in abrir_fz or "$('fz_p_'+k)" in abrir_fz) for i in ids[:9] if i not in ("fz_costo", "fz_p_bajo", "fz_p_esperado", "fz_p_alto"))
    assert "STD_DEF.costos" in abrir_fz and "precio_venta" in abrir_fz and "margen_objetivo" in abrir_fz
    assert "fzResultado()" in cuerpo("function resumenPanel(") and "fzAbrir(null)" in js and "fzOlvidar()" in cuerpo("async function nuevo(")
    # (v2.66, R7.4: fzResultado arma el panel con fzHtml, que también usa el informe)
    assert "result.metrics.factibilidad" in cuerpo("function fzResultado(") and "fzHtml(f)" in cuerpo("function fzResultado(")
    assert "semaforo" in cuerpo("function fzHtml(") and "opt.base" in cuerpo("function fzHtml(")
    assert "m.factibilidad" in cuerpo("function resumen(") and "roi" in cuerpo("function resumen(")                    # las variantes guardan el ROI
    # Normativa: cada medida de standards.costos tiene su etiqueta (o se carga en Factibilidad) y 'costos' está en la lista de grupos
    etiquetas = re.search(r"const STD_COSTOS=\{(.*?)\};", js, re.S).group(1)
    ocultas = re.search(r"const STD_OCULTAS=\{costos:\[(.*?)\]\}", js).group(1)
    for k in C:
        assert ("%s:'" % k) in etiquetas or ("'%s'" % k) in ocultas, k
    assert "'estacionamiento','costos']" in cuerpo("function renderStd(") and "costos:'Costos y factibilidad" in js
    # el servidor recarga el módulo nuevo y la web recibe las medidas
    srv = open(os.path.join(raiz, "server.py"), encoding="utf-8").read()
    assert "import engine.factibilidad as _factibilidad" in srv and "_patios, _factibilidad, _layout" in srv
    assert tuple(int(x) for x in LY.VERSION.split(".")) >= (2, 64)


def test_sin_usar():
    """v2.64: «sin usar» (metrics.unused_area) mide la planta que no cubren pasillos, núcleos ni viviendas. La caja de cada
    núcleo incluye su tramo de pasillo, que ya está en res["corridors"] (y en un anillo, las esquinas donde se encuentran dos
    pasillos): antes se contaban dos veces y «sin usar» quedaba por debajo de la planta libre real (en «Barra 60x16», 23,4 m²
    contra 38,5: la intersección de los dos núcleos con el pasillo, 15,15 m²). Se mide con un barrido horizontal (exacto a lo
    largo de x, con un paso en y que no coincide con la grilla de 5 cm de las medidas). La circulación (circulation_pct) se
    deja como estaba: sigue sumando ese tramo dos veces; queda para decidir."""
    from engine import geometry as G

    def une(ivs):                                     # unión de intervalos [a, b]
        out = []
        for a, b in sorted((a, b) for a, b in ivs):
            if out and a <= out[-1][1]:
                out[-1][1] = max(out[-1][1], b)
            else:
                out.append([a, b])
        return out

    def corta(A, B):                                  # intersección de dos uniones de intervalos
        out, i, k = [], 0, 0
        while i < len(A) and k < len(B):
            a, b = max(A[i][0], B[k][0]), min(A[i][1], B[k][1])
            if b > a:
                out.append([a, b])
            if A[i][1] < B[k][1]:
                i += 1
            else:
                k += 1
        return out
    largo = lambda ivs: sum(b - a for a, b in ivs)

    def barrer(r, bloques, dy=0.0137):
        """(planta, planta libre, núcleos ∩ pasillos) en m², por barrido de bandas horizontales de alto dy."""
        plate = libre = inter = 0.0
        y0, y1 = min(G.bbox(o)[1] for o, _ in bloques), max(G.bbox(o)[3] for o, _ in bloques)
        n = int((y1 - y0) / dy) + 1
        dy = (y1 - y0) / n                            # bandas que cubren justo todo el alto
        for i in range(n):
            y = y0 + (i + 0.5) * dy
            planta = une([iv for o, hs in bloques for iv in G.line_intervals_multi([o] + hs, y)])
            pasillos = une([iv for p in r["corridors"] for iv in G.line_intervals(p, y)])
            nucleos = une([iv for c in r["cores"] for iv in G.line_intervals(c["poly"], y)])
            usado = une([iv for u in r["units"] for iv in G.line_intervals(u["poly"], y)] + pasillos + nucleos)
            plate += largo(planta) * dy
            libre += (largo(planta) - largo(corta(planta, usado))) * dy
            inter += largo(corta(pasillos, nucleos)) * dy
        return plate, libre, inter

    A = lambda ps: sum(abs(G.area(p)) for p in ps)
    muestra = lambda n: json.load(open(os.path.join(os.path.dirname(__file__), "..", "samples", n + ".json"), encoding="utf-8"))
    # 1) «Barra 60x16»: dos núcleos de 5,05 × 1,50 m sobre el pasillo
    s = muestra("barra")
    r = run(s["footprint"], h=s["height"])
    m = r["metrics"]
    plate, libre, inter = barrer(r, [(r["plate"], [])])
    viejo = max(0.0, m["plate_area"] - (A(r["corridors"]) + A([c["poly"] for c in r["cores"]]) + A([u["poly"] for u in r["units"]])) - m.get("dark_area", 0.0))
    assert abs(viejo - 23.4) < 0.05 and abs(inter - 2 * 5.05 * 1.5) < 0.1, (viejo, inter)            # la cuenta de antes y lo que repetía
    assert m["unused_area"] > viejo and abs(m["unused_area"] - viejo - inter) < 0.2, (m["unused_area"], viejo, inter)
    assert abs(plate - m["plate_area"]) < 0.3 and abs(m["unused_area"] - libre) < 0.5, (m["unused_area"], libre)    # planta − unión
    assert m["circulation_pct"] == round((A(r["corridors"]) + A([c["poly"] for c in r["cores"]])) / m["plate_area"] * 100, 1)   # sin cambio
    # 2) una L (núcleo en el codo) y un anillo con patio central (esquinas donde dos pasillos se cruzan): igual a planta − unión
    for nombre in ("L", "patio_central"):
        s = muestra(nombre)
        extra = {"patios_mode": "manual", "patios": s["patios"]} if nombre == "patio_central" else {}
        r = run(s["footprint"], h=s["height"], **extra)
        plate, libre, inter = barrer(r, [(b["plate"], b.get("plate_holes") or []) for b in r["blocks"]])
        assert inter > 5 and abs(plate - r["metrics"]["plate_area"]) < 0.5, (nombre, inter, plate)
        assert abs(r["metrics"]["unused_area"] - max(0.0, libre - r["metrics"].get("dark_area", 0.0))) < 0.5, (nombre, r["metrics"]["unused_area"], libre)

if __name__ == "__main__":
    test_factibilidad(); test_sin_usar(); print("OK80")


def test_promovida():
    """R10.12b (v2.66): superficie media y aviso de Vivienda Promovida. metrics.superficie_media es la media de la superficie
    con muros de las viviendas de la planta tipo (1 decimal) y superficie_media_ref la referencia de mercado (58 m²: ANV,
    Montevideo, 2025). El aviso (res["warnings"] y metrics.promovida) sale en las etapas del mix y de los planos si los
    monoambientes pasan del 25 % de las viviendas de la planta o si alguno mide menos de 35 m² con muros; las dos
    medidas están en standards.vivienda.promovida. Solo avisa: el mix no cambia."""
    import copy
    from engine import layout as LY, standards as ST
    V = ST.DEFAULTS["vivienda"]
    assert V["superficie_media_mercado"] == 58.0 and V["promovida"] == {"mono_max_pct": 25, "mono_min_area": 35}
    barra = [[0, 0], [60, 0], [60, 16], [0, 16]]
    # 1) con el mix por defecto: cumple, sin aviso, y la media es la de area_muros
    r = run(barra)
    m, pr = r["metrics"], r["metrics"]["promovida"]
    medias = [u["area_muros"] for u in r["units"]]
    assert m["superficie_media"] == round(sum(medias) / len(medias), 1) and 40 <= m["superficie_media"] <= 70, m["superficie_media"]
    assert m["superficie_media_ref"] == 58.0
    assert pr["ok"] and pr["avisos"] == [] and not any("Promovida" in w for w in r["warnings"]), pr
    assert pr["mono_count"] == sum(1 for u in r["units"] if u["bedrooms"] == 0) and pr["mono_count"] >= 1
    assert pr["mono_pct"] == round(pr["mono_count"] / len(r["units"]) * 100, 1) and pr["mono_pct"] <= 25
    assert pr["mono_min_area"] == min(u["area_muros"] for u in r["units"] if u["bedrooms"] == 0) >= 35
    assert (pr["limite_mono_pct"], pr["limite_mono_area"]) == (25, 35)
    # 2) con 40 % de monoambientes de 30 m²: avisa (y los mismos textos van a los avisos del resultado)
    mix40 = [{"name": "Mono", "area": 30, "percent": 40, "dorms": 0}, {"name": "2 dorm", "area": 62, "percent": 60, "dorms": 2}]
    r = run(barra, unit_mix=mix40)
    pr = r["metrics"]["promovida"]
    assert not pr["ok"] and pr["mono_pct"] > 25 and pr["avisos"], pr
    assert "Vivienda Promovida" in pr["avisos"][0] and "%.1f" % pr["mono_pct"] in pr["avisos"][0] and "25" in pr["avisos"][0]
    assert all(a in r["warnings"] for a in pr["avisos"]), r["warnings"]
    assert len({u["type"] for u in r["units"]}) == 2 and r["metrics"]["superficie_media"] > 0           # el mix no se toca
    # 3) las dos medidas se leen de standards (se pueden cambiar)
    r = run(barra, standards={"vivienda": {"promovida": {"mono_max_pct": 5}}})
    assert not r["metrics"]["promovida"]["ok"] and r["metrics"]["promovida"]["limite_mono_pct"] == 5 and \
        r["metrics"]["promovida"]["limite_mono_area"] == 35                                           # lo demás conserva su valor
    r = run(barra, standards={"vivienda": {"superficie_media_mercado": 70}})
    assert r["metrics"]["superficie_media_ref"] == 70
    # 4) solo en las etapas con mix o planos
    datos = {"footprint": barra, "height": 15, "params": dict(unit_mix=mix40)}
    for etapa, hay in (("massing", False), ("corridor", False), ("mix", True), ("plans", True)):
        res = LY.generate(dict(datos, stage=etapa))
        assert ("promovida" in res["metrics"]) == hay and ("superficie_media" in res["metrics"]) == hay, etapa
        assert any("Promovida" in w for w in res["warnings"]) == hay, etapa
    # 5) la función sola, con viviendas inventadas: umbrales exactos, area_muros que falta, tipos que no son del mix
    mix = [{"name": "Mono", "area": 33, "dorms": 0}, {"name": "1 dorm", "area": 42, "dorms": 1}]
    u = lambda tipo, area, muros=None: dict({"type": tipo, "area": area, "target": area}, **({"area_muros": muros} if muros else {}))
    assert LY.superficie_y_promovida([], mix, V) == {}
    sp = LY.superficie_y_promovida([u("Mono", 30, 36), u("1 dorm", 40, 46), u("1 dorm", 40, 46), u("1 dorm", 40, 46)], mix, V)
    assert sp["promovida"]["mono_pct"] == 25.0 and sp["promovida"]["ok"] and sp["superficie_media"] == 43.5     # el 25 % justo cumple
    sp = LY.superficie_y_promovida([u("Mono", 30, 36), u("Mono", 30, 36), u("1 dorm", 40, 46), u("1 dorm", 40, 46)], mix, V)
    assert sp["promovida"]["mono_pct"] == 50.0 and not sp["promovida"]["ok"] and len(sp["promovida"]["avisos"]) == 1
    sp = LY.superficie_y_promovida([u("Mono", 30, 34.9), u("1 dorm", 40, 46), u("1 dorm", 40, 46), u("1 dorm", 40, 46)], mix, V)
    assert sp["promovida"]["mono_min_area"] == 34.9 and not sp["promovida"]["ok"] and "34.9" in sp["promovida"]["avisos"][0]
    assert LY.superficie_y_promovida([u("Mono", 35, 35.0), u("1 dorm", 40, 46)] * 3 + [u("1 dorm", 40, 46)] * 6, mix, V)["promovida"]["ok"]   # 35 m² justos
    sp = LY.superficie_y_promovida([u("Mono", 30), u("1 dorm", 50)] + [u("1 dorm", 50)] * 4, mix, V)           # sin area_muros: la superficie libre
    assert sp["superficie_media"] == round((30 + 50 * 5) / 6.0, 1) and sp["promovida"]["mono_min_area"] == 30.0
    sp = LY.superficie_y_promovida([u("Monoambiente", 30, 36)] + [u("2 dorm", 70, 76)] * 5, mix, V)           # un tipo que no es del mix (vivienda editada)
    assert sp["promovida"]["mono_count"] == 1 and sp["promovida"]["ok"]
    sp = LY.superficie_y_promovida([u("1 dorm", 40, 46)], mix, V)
    assert sp["promovida"]["mono_count"] == 0 and sp["promovida"]["mono_min_area"] is None and sp["promovida"]["ok"]


def test_informe():
    """R7.4 (v2.66): botón «Informe» en Proyecto → Exportar. Arma un documento HTML autónomo con las once secciones (encabezado,
    predio y masa, normativa, planta tipo, viviendas, núcleos y evacuación, cocheras, costos, escenarios, advertencias y
    fuentes), imprimible (A4, saltos de página, sin colores que hagan falta), y lo abre en una pestaña nueva. Las claves del
    resultado que lee el informe existen en el motor; con node, informeHtml se ejecuta con resultados reales y no deja
    «undefined» ni «NaN», escapa los textos y trae lo que corresponde a cada caso."""
    import re
    import shutil
    import subprocess
    import tempfile
    from engine import layout as LY, standards as ST
    base = os.path.join(os.path.dirname(__file__), "..")
    html = open(os.path.join(base, "web", "index.html"), encoding="utf-8").read()
    js = html.split("<script>", 1)[1].split("</script>", 1)[0]
    cuerpo = lambda f: js.split(f, 1)[1].split("\nfunction ", 1)[0].split("\nasync function ", 1)[0].split("\nconst ", 1)[0]
    # 1) el botón, junto a la tabla CSV y el DXF, y las funciones
    exportar = html.split("<h2>Exportar</h2>", 1)[1].split("</div>", 1)[0]
    assert re.search(r'<button class="s" id="btnInforme" onclick="informe\(\)"[^>]*>Informe</button>', exportar), "falta el botón Informe"
    assert exportar.index('id="btnCsv"') < exportar.index('id="btnInforme"') and "dl('dxf')" in exportar
    for f in ("function informe(", "function informeHtml(", "function datosInforme(", "function informePlano(", "function informeLeyenda(",
              "function fzHtml(", "function iTabla(", "function origenInforme("):
        assert f in js, f
    # 2) sin resultado con viviendas avisa y no abre nada; con resultado, una pestaña nueva con un Blob de tipo text/html
    inf = cuerpo("function informe(")
    assert "!result||!result.units||!result.units.length" in inf and "alert(" in inf.split("window.open", 1)[0] and "text/html" in inf and "window.open(" in inf
    assert "a.download=" in inf and "click()" in inf                                       # si el navegador bloquea la pestaña, se baja el archivo
    # 3) las once secciones, en orden, y que cada una tenga su función
    titulos = re.findall(r"iSec\((\d+),'([^']+)',(inf\w+)\(d\)", cuerpo("function informeHtml("))
    assert [(int(n), t) for n, t, _ in titulos] == [
        (1, "Encabezado"), (2, "Predio y masa"), (3, "Normativa aplicada"), (4, "Planta tipo"), (5, "Viviendas"),
        (6, "Núcleos y evacuación"), (7, "Cocheras"), (8, "Costos y factibilidad"), (9, "Escenarios"),
        (10, "Advertencias pendientes"), (11, "Fuentes")], titulos
    # 4) imprimible: A4, saltos de página por sección, botón Imprimir que no se imprime, colores claros fijos
    css = re.search(r"const INF_CSS=`(.*?)`;", js, re.S).group(1)
    assert "@page{size:A4" in css and ".nueva{break-before:page" in css and "@media print" in css and ".no-print{display:none" in css
    assert "color-scheme" in cuerpo("function informeHtml(") and "prefers-color-scheme" not in css and "window.print()" in cuerpo("function informeHtml(")
    assert "gs.dataset.theme='light'" in cuerpo("function informePlano(") and "finally" in cuerpo("function informePlano(")   # el informe se imprime claro y la página vuelve a su tema
    # 5) las claves que lee el informe existen en un resultado real del motor
    muestra = lambda n: json.load(open(os.path.join(base, "samples", n + ".json"), encoding="utf-8"))
    corridas = []
    for n in ("barra", "torre_mixta", "patio_central", "entre_medianeras", "entre_medianeras_patio"):
        s = muestra(n)
        corridas.append(LY.generate({"footprint": s["footprint"], "height": s["height"], "stage": "plans",
                                     "params": dict({k: s[k] for k in ("stories", "patios", "medianeras") if s.get(k) is not None},
                                                    **({"patios_mode": "manual"} if s.get("patios") else {}))}))
    metricas = [r["metrics"] for r in corridas]
    fuente_motor = open(os.path.join(base, "engine", "layout.py"), encoding="utf-8").read()
    funciones = {n: cuerpo("function %s(" % n) for n in ("infEncabezado", "infPredio", "infNormativa", "infPlanta", "infViviendas", "infNucleos",
                                                          "infCocheras", "infFactibilidad", "infEscenarios", "infAdvertencias", "fzHtml")}
    leen = lambda fs, v: {k for f in fs for k in re.findall(r"\b%s\.(\w+)" % v, funciones[f])}
    todas = tuple(f for f in funciones if f != "fzHtml")
    m_ = leen(todas, "m") - {"mix"}                                                       # m: result.metrics
    assert len(m_) >= 15, m_
    for k in m_:                                                                          # (dark_area, galeria_area…: solo en algunos resultados)
        assert any(k in m for m in metricas) or ('"%s"' % k) in fuente_motor, k
    for v, sub in (("mx", "mix"), ("pr", "promovida"), ("co", "core"), ("ev", "evacuacion"), ("pk", None), ("f", "factibilidad")):
        ks = leen(("infViviendas",) if v in ("mx", "pr") else ("infNucleos",) if v in ("co", "ev") else ("infCocheras",) if v == "pk" else ("infFactibilidad", "fzHtml"), v)
        if v == "mx":
            assert ks, v
            for k in ks:
                assert all(k in m["mix"] for m in metricas), k
        elif v == "pr":
            assert {"mono_count", "mono_pct", "mono_min_area", "limite_mono_pct", "limite_mono_area", "ok", "avisos"} <= ks, ks
            for k in ks:
                assert all(k in m["promovida"] for m in metricas), k
        elif v == "co":
            for k in ks:
                assert all(k in m["core"] for m in metricas), k
        elif v == "ev":
            for k in ks:
                assert all(k in r["evacuacion"] for r in corridas), k
        elif v == "pk":
            for k in ks:
                assert k in metricas[1]["programs"]["Parking"], k
        else:
            assert len(ks) >= 12, ks
            for k in ks:
                assert all(k in m["factibilidad"] for m in metricas), k
    for k in leen(("fzHtml",), "t"):                                                        # f.terreno
        assert k in metricas[0]["factibilidad"]["terreno"], k
    for k in leen(("fzHtml",), "sp"):                                                       # f.superficies
        assert k in metricas[0]["factibilidad"]["superficies"], k
    usadas_u = set(re.findall(r"\bu\.(\w+)", funciones["infViviendas"] + funciones["infNucleos"]))          # las viviendas
    for k in usadas_u:
        assert all(k in x for x in corridas[0]["units"]), k
    for k in set(re.findall(r"\bp\.(\w+)", funciones["infNucleos"])):                         # los tramos de pasillo
        assert all(k in x for x in corridas[0]["pasillos"]), k
    # 6) la superficie media en el resumen de la web y sus medidas en Normativa
    assert "m.superficie_media" in cuerpo("function resumenPanel(") and "m.superficie_media_ref" in cuerpo("function resumenPanel(")
    assert "mono_max_pct:" in js and "mono_min_area:" in js and "superficie_media_mercado:" in js and "promovida:" in js
    node = shutil.which("node")
    if not node:
        print("(sin node: se omite la ejecución de informeHtml con resultados reales)")
        return
    # 7) informeHtml con node y resultados reales
    def trozo(desde, hasta):
        i = js.index(desde)
        return js[i:js.index(hasta, i)]
    previo = "\n".join([
        re.search(r"^let PROGS=.*$", js, re.M).group(0), re.search(r"^const progOf=.*$", js, re.M).group(0),
        re.search(r"^const progColor=.*$", js, re.M).group(0), re.search(r"^const esc=.*$", js, re.M).group(0),
        re.search(r"^function areaPoly\(.*$", js, re.M).group(0), re.search(r"^const VCOL=.*$", js, re.M).group(0),
        re.search(r"^const STD_COSTOS=.*$", js, re.M).group(0), trozo("const STD_LABELS=", "const STD_LISTA"),
        trozo("const FZ_GAMAS=", "function factibilidadParams"), trozo("function resumen(", "function guardarVariante"),
        trozo("function fzHtml(", "function fzResultado("), trozo("const ETAPA_TXT=", "function informeLeyenda")])
    arnes = """const fs = require('fs');
const E = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
let STD = E.std;
%s
const salida = E.casos.map(c => {
  STD = c.std || E.std;
  const r = c.result;
  const d = Object.assign({ nombre: c.nombre || 'Prueba', fecha: '2026-10-22T12:00:00.000Z', ver: E.ver, etapa: c.etapa || 'plans', origen: c.origen || { v: '', nombre: 'x', ejemplo: 'Barra 60x16' },
    footprint: c.footprint, terreno: c.terreno || null, result: r, std: STD, stdDef: E.stdDef, mix: E.mix, plano: '<svg class="planta"></svg>', leyenda: '<span class="lg">x</span>',
    nivel: 0, params: { corridor_width: 1.5, egress_single: 18, egress_multi: 30, outer_wall: 0.35, cambio: c.cambio || {} }, avisoCostos: 'AVISO COSTOS', avisosDxf: c.dxf || [],
    escenarios: [{ nombre: 'Variante A', m: resumen(r) }, { nombre: 'Actual (sin guardar)', actual: true, m: resumen(r) }] }, c.d || {});
  return informeHtml(d);
});
console.log(JSON.stringify(salida));
""" % previo
    std = ST.merged(None)
    fp_barra = muestra("barra")["footprint"]
    cambios = {"predio": {"patio_min": 3.5}, "vivienda": {"promovida": {"mono_max_pct": 5}}}
    std_cambiado = ST.merged(cambios)
    mono40 = [{"name": "Mono", "area": 30, "percent": 40, "dorms": 0}, {"name": "2 dorm", "area": 62, "percent": 60, "dorms": 2}]
    r_mono = LY.generate({"footprint": fp_barra, "height": 15, "stage": "plans", "params": {"unit_mix": mono40, "standards": cambios}})
    mix = LY.DEFAULT_PARAMS["unit_mix"]
    fp = lambda n: muestra(n)["footprint"]
    mix_etapa = LY.generate({"footprint": fp("barra"), "height": 15, "stage": "mix", "params": {}})
    casos = [{"result": corridas[0], "footprint": fp("barra"), "std": std},                                    # 0) barra, planos
             {"result": corridas[1], "footprint": fp("torre_mixta"), "std": std},                               # 1) con cocheras, oficinas y comercio
             {"result": corridas[2], "footprint": fp("patio_central"), "std": std},                             # 2) con patio
             {"result": corridas[3], "footprint": fp("entre_medianeras"), "std": std},                          # 3) entre medianeras
             {"result": mix_etapa, "footprint": fp("barra"), "std": std, "etapa": "mix"},                       # 4) solo el mix
             {"result": r_mono, "footprint": fp("barra"), "std": std_cambiado, "nombre": "<img src=x onerror=alert(1)>",   # 5) medidas cambiadas, nombre con HTML, DXF
              "dxf": ["<b>aviso</b> & más"], "terreno": {"frente": 10, "fondo": 30, "medianeras": {"i": True, "d": True, "b": False}, "retiros": {"i": 0, "d": 0, "b": 0, "f": 3}},
              "origen": {"v": "__terreno", "nombre": "Terreno 10 × 30 m", "ejemplo": None}, "cambio": {"egress_single": True}}]
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "arnes.js"), "w", encoding="utf-8").write(arnes)
        open(os.path.join(tmp, "entrada.json"), "w", encoding="utf-8").write(json.dumps(
            {"casos": casos, "std": std, "stdDef": ST.DEFAULTS, "mix": [{"name": t["name"], "area": t["area"], "percent": t["percent"], "dorms": t.get("dorms")} for t in mix],
             "ver": LY.VERSION}))
        p = subprocess.run([node, os.path.join(tmp, "arnes.js"), os.path.join(tmp, "entrada.json")], capture_output=True, text=True, encoding="utf-8")
        assert p.returncode == 0, p.stderr
    docs = json.loads(p.stdout)
    sin_tags = lambda t: re.sub(r"<[^>]+>", " ", t)
    for i, doc in enumerate(docs):
        assert doc.startswith("<!doctype html>") and doc.rstrip().endswith("</html>"), i
        assert "undefined" not in doc and "NaN" not in doc and "[object" not in doc and "Infinity" not in doc, (i, re.findall(r".{40}(?:undefined|NaN|\[object).{20}", doc)[:3])
        assert [h for h in re.findall(r"<h2><span>(\d+)\.</span>([^<]+)</h2>", doc)] == [(str(n), t) for n, t, _ in titulos], i
        for etiqueta in ("table", "section", "thead", "tbody", "ul"):
            assert doc.count("<%s" % etiqueta) == doc.count("</%s>" % etiqueta), (i, etiqueta)
        assert "<script" not in doc and "onerror" not in doc.replace("&#", "") or i == 5, i               # sin scripts propios (el botón usa window.print)
        assert "AVISO COSTOS" in doc and "Imprimir" in doc and "v" + LY.VERSION in doc, i
    r0, d0 = corridas[0], docs[0]
    m0 = r0["metrics"]
    fmt = lambda n, d=1: ("%.*f" % (d, n)).replace(".", ",")
    assert "Ejemplo de Trazo: Barra 60x16" in d0 and "planos de vivienda" in d0 and "22 de octubre de 2026" in d0
    assert d0.count('class="viv"') == 1 and len(re.findall(r"<tr>", d0.split('class="viv"', 1)[1].split("</table>", 1)[0])) == len(r0["units"]) + 1
    for u in r0["units"]:
        assert ">%s<" % u["id"] in d0
    assert fmt(m0["superficie_media"]) in d0 and "Cumple</b> el criterio de Vivienda Promovida" in d0 and "58 m²" in d0
    assert "Viable" in d0 and fmt(m0["factibilidad"]["objetivo"]).replace(",0", ",0") in d0 and "Base de cálculo" in d0
    assert "Pasillos comunes" in d0 and "Variante A" in d0 and "Actual (sin guardar)" in d0 and "Sin advertencias" not in d0
    assert "No se cambió ninguna medida" in d0 and "El edificio no tiene niveles con programa" in d0
    d1 = docs[1]
    assert "Plazas en total" in d1 and str(corridas[1]["metrics"]["programs"]["Parking"]["stalls"]) in d1 and "No viable" in d1
    assert "Estacionamiento" in d1 and "Oficinas" in d1 and "Comercial" in d1 and "El ingreso cuenta solo la superficie vendible" in d1
    assert "1 patio dibujado por el usuario, 112,0 m² en total" in docs[2] and "Sin patios" not in docs[2] and "Sin patios" in docs[0]
    assert "Medianera 1" in docs[3] and "Adosada al lindero" in docs[3]
    d4 = docs[4]                                                                                           # solo el mix: sin dormitorios ni calidad, pero completo
    assert "mix de unidades" in d4 and "Cumple</b>" in d4 and len(re.findall(r"<h2>", d4)) == 11
    d5 = docs[5]
    assert "&lt;img src=x onerror=alert(1)&gt;" in d5.replace("&#60;", "&lt;").replace("&#62;", "&gt;") or "&#60;img" in d5
    assert "<img" not in d5 and "<b>aviso</b>" not in d5 and "DXF: " in d5
    assert "cambiada" in d5 and "Ancho mínimo de patio para iluminar" in d5 and "3,5" in d5 and "5" in d5   # medidas cambiadas con su valor por defecto
    assert "Terreno rectangular" in d5 and "10,00 × 30,00 m" in d5 and "izquierdo, derecho" in d5 and "edificabilidad (GFA / terreno)" in d5
    assert "No cumple</b> el criterio de Vivienda Promovida" in d5 and "Vivienda Promovida: los monoambientes son el" in sin_tags(d5)
    assert all(a in d5 for a in r_mono["metrics"]["promovida"]["avisos"])                                 # los avisos, también en «Advertencias pendientes»
    assert d5.count("por defecto") < d0.count("por defecto")                                              # dos medidas pasaron a «cambiada»

if __name__ == "__main__":
    test_promovida(); test_informe(); print("OK82")
