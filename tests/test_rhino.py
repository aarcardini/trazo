"""Pruebas del puente de Rhino sin Rhino (ROADMAP R1.1).

El script rhino/trazo_rhino.py se carga con Rhino, rhinoscriptsyntax, scriptcontext y System simulados
(unittest.mock) y habla con el servidor de Trazo de verdad (server.py en un puerto libre). Cubren los mensajes
de conexión, objetos no válidos, control de medidas, origen del resultado, el diagnóstico, el menú y Recibir sin
duplicar (R1.4: qué capas se reemplazan, qué se borra y qué se pregunta).
La geometría de Rhino (base del sólido, dibujo de capas) solo se puede probar en Rhino: ver los pasos del PR.

    python tests/test_rhino.py     (también corre dentro de tests/test_engine.py)
"""
import importlib.util
import io
import os
import socket
import sys
import threading
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

sys.dont_write_bytecode = True   # sin __pycache__: tras revertir un cambio, nunca se prueba bytecode viejo
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import server  # noqa: E402
from engine import layout  # noqa: E402

FALSOS = ("Rhino", "rhinoscriptsyntax", "scriptcontext", "System", "System.Drawing",
          "System.Collections", "System.Collections.Generic")


def cargar():
    """El script de Rhino con módulos de Rhino simulados: Rhino 8.12, archivo en milímetros, sin capas de Trazo."""
    with mock.patch.dict(sys.modules, {n: mock.MagicMock(name=n) for n in FALSOS}):
        spec = importlib.util.spec_from_file_location("trazo_rhino", os.path.join(RAIZ, "rhino", "trazo_rhino.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    m.Rhino.RhinoApp.Version = "8.12.24282.7001"
    m.Rhino.RhinoMath.UnitScale.return_value = 0.001
    m.sc.doc.ModelUnitSystem = "Millimeters"
    m.sc.doc.ModelAbsoluteTolerance = 0.001
    m.rs.IsLayer.return_value = False
    return m


def salida(fn, *a, **k):
    """Lo que fn escribe en la consola de Rhino."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*a, **k)
    return buf.getvalue()


class Servidor:
    """server.py de verdad, en un puerto libre y en otro hilo. Devuelve su dirección."""

    def __enter__(self):
        server.STATE.update(mass=None, result=None)
        self.srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        return "http://127.0.0.1:%d" % self.srv.server_address[1]

    def __exit__(self, *exc):
        self.srv.shutdown()
        self.srv.server_close()


def sin_servidor():
    """Una dirección donde no escucha nadie."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return "http://127.0.0.1:%d" % port


def test_servidor_apagado():
    """Servidor apagado: mensaje con el comando para arrancarlo; Enviar ni siquiera pide la masa."""
    m = cargar()
    m.SERVER = sin_servidor()
    try:
        m.http("GET", "/api/version", timeout=10)
        raise AssertionError("debía fallar sin servidor")
    except m.TrazoError as e:
        txt = str(e)
    assert "No hay conexión con Trazo" in txt and "server.py" in txt, txt
    m.rs.GetString.return_value = "Enviar"
    out = salida(m.main)
    assert "No hay conexión con Trazo" in out and "Traceback" not in out, out
    assert not m.rs.GetObject.called
    m.rs.GetString.return_value = "Diagnostico"
    out = salida(m.main)
    assert "Rhino 8.12" in out and "milímetros (1 unidad = 0.001 m)" in out and "No hay conexión" in out, out
    assert "falta arrancar el servidor" in out, out


def test_con_servidor():
    """Servidor encendido: diagnóstico completo, error del motor con su detalle y Recibir sin resultado."""
    m = cargar()
    with Servidor() as url:
        m.SERVER = url
        assert m.http("GET", "/api/version")["version"] == layout.VERSION
        out = salida(m.diagnostico)
        assert "Servidor: Trazo v%s conectado" % layout.VERSION in out, out
        assert "Masa en el servidor: ninguna" in out and "Resultado en el servidor: ninguno" in out, out
        assert "Capa Trazo::Centerline: no existe" in out and "Capa Trazo::Patios: no existe" in out and "todo listo" in out, out
        assert "Resultado dibujado en este archivo: ninguno" in out, out
        m.http("POST", "/api/mass", {"name": "Barra de prueba", "footprint": [[0, 0], [60, 0], [60, 16], [0, 16]]})
        assert "«Barra de prueba»" in salida(m.diagnostico)
        with redirect_stderr(io.StringIO()):                 # el servidor imprime el error en su ventana
            try:
                m.http("POST", "/api/generate", {})
                raise AssertionError("debía fallar: falta la huella")
            except m.TrazoError as e:
                assert "error (500" in str(e) and "footprint" in str(e), str(e)
        try:
            m.http("GET", "/api/no-existe")
            raise AssertionError("debía fallar: ruta inexistente")
        except m.TrazoError as e:
            assert "404" in str(e), str(e)
        m.rs.GetString.return_value = "Recibir"
        out = salida(m.main)
        assert "Todavía no hay un resultado" in out and "Traceback" not in out, out


def test_objeto_no_valido():
    """Si se elige algo que no es un sólido, dice qué es y cómo convertirlo."""
    m = cargar()
    assert "una curva" in m.objeto_no_valido(4) and "_ExtrudeCrv" in m.objeto_no_valido(4)
    assert "una malla" in m.objeto_no_valido(32) and "_MeshToNURB" in m.objeto_no_valido(32)
    assert "un bloque" in m.objeto_no_valido(4096) and "SubD" in m.objeto_no_valido(262144)
    with Servidor() as url:
        m.SERVER = url
        m.rs.GetString.return_value = "Enviar"
        m.rs.GetObject.return_value = "id-de-la-curva"
        m.rs.ObjectType.return_value = 4
        out = salida(m.main)
    assert "Seleccionaste una curva" in out and "Traceback" not in out, out


def test_medidas():
    """Medidas que no parecen de un edificio: avisa y sugiere revisar las unidades."""
    m = cargar()
    assert m.revisar_medidas(60, 16, 15, "metros") == []
    chica = m.revisar_medidas(0.06, 0.016, 0.015, "milímetros")
    assert "muy pequeña" in chica[0] and "milímetros" in chica[1] and "_Units" in chica[1], chica
    assert "enorme" in m.revisar_medidas(60000, 16000, 15000, "metros")[0]
    assert m._area([[0, 0], [60, 0], [60, 16], [0, 16]]) == 960


def test_nucleo_con_ascensores():
    """R10.7: un punto de Trazo::Cores llamado «ascensores=2» fija los ascensores de ese núcleo; sin nombre (o con uno
    que no es una cantidad) va solo el punto, como antes."""
    m = cargar()
    assert m.nucleo([1.0, 2.0], "ascensores=2") == {"p": [1.0, 2.0], "ascensores": 2}
    assert m.nucleo([1.0, 2.0], "Ascensores = 3") == {"p": [1.0, 2.0], "ascensores": 3}
    assert m.nucleo([1.0, 2.0], None) == [1.0, 2.0] and m.nucleo([1.0, 2.0], "ascensores=dos") == [1.0, 2.0]


def test_ancho_de_linea():
    """R10.8: una polilínea de Trazo::Centerline llamada «ancho=1.4» pide ese ancho para cada uno de sus tramos."""
    m = cargar()
    pts = [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0]]
    assert m.anchos_de_linea(pts, "ancho=1.4") == [{"seg": [[0.0, 0.0], [10.0, 0.0]], "ancho": 1.4},
                                                   {"seg": [[10.0, 0.0], [10.0, 8.0]], "ancho": 1.4}]
    assert m.anchos_de_linea(pts, "Ancho = 1,6")[0]["ancho"] == 1.6
    assert m.anchos_de_linea(pts, None) == [] and m.anchos_de_linea(pts, "ancho=uno") == [] and \
        m.anchos_de_linea(pts, "ancho=0") == []
    # un tramo de 5 cm o menos (una esquina resuelta en dos vértices) no se manda: el motor une esos vértices
    assert [a["seg"] for a in m.anchos_de_linea([[0.0, 0.0], [10.0, 0.0], [10.03, 0.0], [10.03, 8.0]], "ancho=1.4")] == \
        [[[0.0, 0.0], [10.0, 0.0]], [[10.03, 0.0], [10.03, 8.0]]]


def test_curva_a_puntos():
    """El contorno pasa a polilínea con las dos formas en que el Python de Rhino devuelve TryGetPolyline."""
    m = cargar()

    class Punto:
        def __init__(self, x, y):
            self.X, self.Y = x, y

        def DistanceTo(self, o):
            return ((self.X - o.X) ** 2 + (self.Y - o.Y) ** 2) ** 0.5

    class Polilinea(list):
        Count = property(len)

    cuadrado = Polilinea([Punto(0, 0), Punto(10, 0), Punto(10, 10), Punto(0, 10), Punto(0, 0)])
    curva = mock.MagicMock()
    curva.TryGetPolyline.return_value = (True, cuadrado)
    assert len(m.curve_to_points(curva, 0.001)) == 4            # sin repetir el vértice de cierre
    curva.TryGetPolyline.side_effect = TypeError("falta el parámetro de salida")
    curva.ToPolyline.return_value.ToPolyline.return_value = cuadrado
    assert len(m.curve_to_points(curva, 0.001)) == 4


def test_origen_resultado():
    """Avisa si lo que se recibe no corresponde a la masa enviada desde Rhino."""
    m = cargar()
    res = {"footprint": [[0.35, 0.35], [59.65, 0.35], [59.65, 15.65], [0.35, 15.65]]}
    assert "no viene de una masa de Rhino" in m.origen_resultado(res, {})
    assert m.origen_resultado(res, {"footprint": [[0, 0], [60, 0], [60, 16], [0, 16]]}) is None
    otra = {"name": "Torre", "footprint": [[100, 100], [130, 100], [130, 130], [100, 130]]}
    assert "no coincide" in m.origen_resultado(res, otra) and "«Torre»" in m.origen_resultado(res, otra)


def test_error_inesperado():
    """Un error no previsto se muestra con un mensaje en español y el detalle para copiar."""
    m = cargar()
    m.rs.GetString.return_value = "Diagnostico"
    m.diagnostico = lambda: 1 / 0
    out = salida(m.main)
    assert "error inesperado" in out and "ZeroDivisionError" in out, out
    m.rs.GetString.return_value = "Imprimir"
    assert "no conozco la opción «Imprimir»" in salida(m.main)


# ------------------------------------------------------------------ Recibir sin duplicar (R1.4)
class Capa:
    """Capa de Rhino simulada."""

    def __init__(self, indice, ruta):
        self.Index, self.FullPath, self.IsDeleted = indice, ruta, False


class Capas(list):
    """Tabla de capas simulada: se recorre como una lista y anota las capas borradas, en orden."""

    def __init__(self, capas):
        super().__init__(capas)
        self.borradas = []

    def Delete(self, indice, silencioso):
        self.borradas.append(indice)
        for c in self:
            c.IsDeleted = c.IsDeleted or c.Index == indice
        return True


class Objeto:
    """Objeto de Rhino simulado, en la capa de ese índice."""

    def __init__(self, capa):
        self.Attributes = mock.Mock(LayerIndex=capa)
        self.Id = "objeto-en-capa-%d" % capa


def capas_de_prueba():
    """Un resultado anterior de dos niveles, las capas de entrada de Trazo y una capa del usuario."""
    return Capas([Capa(1, "Trazo::Footprint"), Capa(2, "Trazo::L00"), Capa(3, "Trazo::L00::Units"),
                  Capa(4, "Trazo::L01"), Capa(5, "Trazo::L01::Units"), Capa(6, "Trazo::L01::Rooms"),
                  Capa(7, "Trazo::L01::Rooms::bath"), Capa(8, "Trazo::Patios"), Capa(9, "Trazo::Cores"),
                  Capa(10, "Terreno")])


class Documento:
    """Archivo de Rhino simulado con estado: las capas y los objetos se crean, se mueven y se borran de verdad."""

    def __init__(self, m):
        self.capas, self.objetos = Capas([Capa(0, "Predeterminada")]), []
        m.sc.doc.Layers = self.capas
        m.sc.doc.Objects.GetObjectList.side_effect = lambda ajustes: list(self.objetos)
        m.sc.doc.Objects.Delete.side_effect = lambda o, *a: self.objetos.remove(o) is None
        m.sc.doc.Objects.AddPolyline.side_effect = m.sc.doc.Objects.AddLine.side_effect = lambda *a: self.nuevo(0)
        m.rs.IsLayer.side_effect = lambda ruta: any(c.FullPath == ruta and not c.IsDeleted for c in self.capas)
        m.rs.AddLayer.side_effect = self.capa
        m.rs.ObjectLayer.side_effect = lambda o, ruta: setattr(o.Attributes, "LayerIndex", self.capa(ruta))

    def capa(self, ruta, color=None):
        """Índice de la capa; la crea con sus capas madre si no existe (como rs.AddLayer)."""
        partes = ruta.split("::")
        for i in range(1, len(partes) + 1):
            r = "::".join(partes[:i])
            if not any(c.FullPath == r and not c.IsDeleted for c in self.capas):
                self.capas.append(Capa(len(self.capas), r))
        return next(c.Index for c in self.capas if c.FullPath == ruta and not c.IsDeleted)

    def nuevo(self, capa):
        self.objetos.append(Objeto(capa))
        return self.objetos[-1]

    def en(self, prefijo):
        """Cuántos objetos hay en las capas que empiezan por ese prefijo."""
        rutas = {c.Index: c.FullPath for c in self.capas}
        return sum(1 for o in self.objetos if rutas[o.Attributes.LayerIndex].startswith(prefijo))

    def existe(self, ruta):
        return any(c.FullPath == ruta and not c.IsDeleted for c in self.capas)


LOTE = [[0, 0], [10, 0], [10, 40], [0, 40]]


def resultado_de_prueba(alto=3):
    """En el servidor, una masa de Rhino y su resultado: lote 10 × 40 entre medianeras (un nivel cada 3 m), con patio."""
    meds = [{"a": [10, 0], "b": [10, 40], "retiro": 0}, {"a": [0, 40], "b": [0, 0], "retiro": 0}]
    res = layout.generate({"footprint": LOTE, "height": alto, "stage": "plans", "params": {"medianeras": meds}})
    assert res["patios"] and len(res["stories"]) == alto // 3
    server.STATE.update(mass={"name": "Lote", "footprint": LOTE, "height": alto, "origin_z": 0.0}, result=res)


def test_capas_resultado():
    """Solo Trazo::Footprint y los niveles Trazo::Lnn son resultado; las capas de entrada no se tocan nunca."""
    m = cargar()
    for ruta in ("Trazo::Footprint", "Trazo::L00", "Trazo::L12::Rooms::bath"):
        assert m.es_capa_resultado(ruta), ruta
    for ruta in ("Trazo", "Trazo::Patios", "Trazo::Cores", "Trazo::Centerline", "Trazo::Medianeras", "Trazo::Lote",
                 "Trazo::L", "Otra::L00", "", None):
        assert not m.es_capa_resultado(ruta), ruta

    def borrar_sin_variante(*a):          # un Rhino sin Delete(objeto, silencioso, ignorar modos)
        if len(a) == 3:
            raise TypeError("No method matches given arguments")
        return True
    m.sc.doc.Objects.Delete.side_effect = borrar_sin_variante
    assert m.borrar([Objeto(1), Objeto(3)]) == []                 # los borró los dos con la otra variante


def test_recibir_primera_vez():
    """Sin resultado anterior no pregunta nada; los patios se dibujan en el nivel, no en la capa Trazo::Patios. El
    equipamiento y los muebles (F5) van en su capa de nivel, con su contorno cerrado y su dibujo abierto; las ventanas
    (R5.5), en Trazo::L00::Ventanas, con su medida en el nombre."""
    m = cargar()
    with Servidor() as url:
        m.SERVER = url
        resultado_de_prueba()
        out = salida(m.receive_result)
    assert not m.rs.GetString.called and not m.sc.doc.Objects.Delete.called
    capas = {c.args[1] for c in m.rs.ObjectLayer.call_args_list}
    assert "Trazo::L00::Patios" in capas and "Trazo::Patios" not in capas, capas
    assert "Trazo::L00::Equipamiento" in capas, capas
    nombres = {c.args[1] for c in m.rs.ObjectName.call_args_list}
    assert {"Inodoro", "Ducha", "Heladera", "Lavarropas"} <= nombres, nombres
    assert {"Cama doble", "Cama individual", "Mesa de luz", "Placard", "Sofá", "Rack de TV", "Mesa", "Silla"} <= nombres, nombres
    assert "Trazo::L00::Ventanas" in capas and "Ventana 1.50 x 1.20" in nombres, nombres
    assert "Trazo: recibido" in out and "(niveles L00)" in out and "Traceback" not in out, out


def test_recibir_reemplaza():
    """Reemplazar borra el resultado anterior (también lo oculto o bloqueado) y las capas de nivel que sobran."""
    m = cargar()
    m.sc.doc.Layers = capas_de_prueba()
    viejos = [Objeto(1), Objeto(3), Objeto(5), Objeto(7)]
    ajenos = [Objeto(8), Objeto(10)]                     # un patio para enviar y un objeto del usuario
    m.sc.doc.Objects.GetObjectList.side_effect = [viejos + ajenos, [Objeto(1), Objeto(3)] + ajenos]
    m.sc.doc.Objects.Delete.return_value = True
    m.rs.GetString.return_value = "Reemplazar"
    with Servidor() as url:
        m.SERVER = url
        resultado_de_prueba()
        out = salida(m.receive_result)
    assert m.rs.GetString.call_args[0][2] == ["Reemplazar", "Agregar", "Cancelar"]
    busqueda = m.sc.doc.Objects.GetObjectList.call_args[0][0]     # también ocultos y bloqueados; no los vinculados
    assert busqueda.HiddenObjects is True and busqueda.LockedObjects is True and busqueda.ReferenceObjects is False
    assert [c.args for c in m.sc.doc.Objects.Delete.call_args_list] == [(o, True, True) for o in viejos]
    llamadas = [c[0] for c in m.sc.doc.Objects.mock_calls]
    assert llamadas.index("Delete") > llamadas.index("AddPolyline")    # primero dibuja: si algo falla, no se pierde
    assert "4 objeto(s) en Trazo::Footprint y Trazo::L00…L01" in out, out
    assert "reemplacé el resultado anterior (4 objeto(s) borrados)" in out and "Traceback" not in out, out
    # el resultado nuevo tiene un solo nivel: las capas de L01 se borran de las subcapas hacia arriba
    assert m.sc.doc.Layers.borradas == [7, 5, 6, 4], m.sc.doc.Layers.borradas


def test_recibir_cancelar_o_agregar():
    """Cancelar (o Esc) no cambia nada; Agregar dibuja el nuevo y deja el anterior. El diagnóstico lo cuenta."""
    with Servidor() as url:
        resultado_de_prueba()
        for respuesta in ("Cancelar", None, "Agregar"):
            m = cargar()
            m.SERVER = url
            m.sc.doc.Layers = capas_de_prueba()
            m.sc.doc.Objects.GetObjectList.return_value = [Objeto(1), Objeto(3), Objeto(8)]
            m.rs.GetString.return_value = respuesta
            out = salida(m.receive_result)
            assert not m.sc.doc.Objects.Delete.called and not m.sc.doc.Layers.borradas, respuesta
            if respuesta == "Agregar":
                assert m.sc.doc.Objects.AddPolyline.called and "sigue en sus capas" in out, out
            else:
                assert not m.sc.doc.Objects.AddPolyline.called and "no recibí nada" in out, out
        out = salida(m.diagnostico)
    assert "Resultado dibujado en este archivo: 2 objeto(s) en Trazo::Footprint y Trazo::L00 (Recibir pregunta" in out, out


def test_recibir_dos_veces():
    """El caso de todos los días: recibir 3 pisos, cambiar la masa a 1 piso y recibir con Reemplazar.
    Queda un solo resultado, sin copias; las capas de los pisos que ya no existen se quitan; lo demás no se toca."""
    m = cargar()
    doc = Documento(m)
    doc.nuevo(doc.capa("Trazo::Patios"))             # un patio dibujado para enviar
    doc.nuevo(doc.capa("Terreno"))                   # algo del usuario
    with Servidor() as url:
        m.SERVER = url
        resultado_de_prueba(9)
        salida(m.receive_result)
        assert not m.rs.GetString.called
        por_piso = doc.en("Trazo::L00")
        assert por_piso > 10 and doc.en("Trazo::L01") == doc.en("Trazo::L02") == por_piso, por_piso
        resultado_de_prueba(3)
        m.rs.GetString.return_value = "Reemplazar"
        out = salida(m.receive_result)
    assert doc.en("Trazo::L00") == por_piso and doc.en("Trazo::Footprint") == 1, out
    assert not doc.existe("Trazo::L01") and not doc.existe("Trazo::L02::Units") and doc.existe("Trazo::L00::Patios")
    assert doc.en("Trazo::Patios") == 1 and doc.en("Terreno") == 1
    assert "reemplacé el resultado anterior (%d objeto(s) borrados)" % (3 * por_piso + 1) in out, out


def test_recibir_no_pudo_borrar():
    """Si un objeto del resultado anterior no se puede borrar, lo avisa y no quita la capa de su piso."""
    m = cargar()
    doc = Documento(m)
    with Servidor() as url:
        m.SERVER = url
        resultado_de_prueba(6)
        salida(m.receive_result)
        rutas = {c.Index: c.FullPath for c in doc.capas}
        rebelde = next(o for o in doc.objetos if rutas[o.Attributes.LayerIndex].startswith("Trazo::L01::"))
        borrar = m.sc.doc.Objects.Delete.side_effect
        m.sc.doc.Objects.Delete.side_effect = lambda o, *a: o is not rebelde and borrar(o, *a)
        resultado_de_prueba(3)
        m.rs.GetString.return_value = "Reemplazar"
        out = salida(m.receive_result)
    assert "no pude borrar 1 objeto(s) del resultado anterior: bórralos a mano en Trazo::L01" in out, out
    assert doc.existe(rutas[rebelde.Attributes.LayerIndex]) and doc.existe("Trazo::L01"), out


def todas():
    for t in (test_servidor_apagado, test_con_servidor, test_objeto_no_valido, test_medidas,
              test_curva_a_puntos, test_origen_resultado, test_error_inesperado,
              test_capas_resultado, test_recibir_primera_vez, test_recibir_reemplaza, test_recibir_cancelar_o_agregar,
              test_recibir_dos_veces, test_recibir_no_pudo_borrar, test_nucleo_con_ascensores, test_ancho_de_linea):
        t()


if __name__ == "__main__":
    todas()
    print("OK rhino")
