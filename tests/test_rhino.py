"""Pruebas del puente de Rhino sin Rhino (ROADMAP R1.1).

El script rhino/trazo_rhino.py se carga con Rhino, rhinoscriptsyntax, scriptcontext y System simulados
(unittest.mock) y habla con el servidor de Trazo de verdad (server.py en un puerto libre). Cubren los mensajes
de conexión, objetos no válidos, control de medidas, origen del resultado, el diagnóstico y el menú.
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


def todas():
    for t in (test_servidor_apagado, test_con_servidor, test_objeto_no_valido, test_medidas,
              test_curva_a_puntos, test_origen_resultado, test_error_inesperado):
        t()


if __name__ == "__main__":
    todas()
    print("OK rhino")
