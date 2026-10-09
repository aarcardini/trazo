#!/usr/bin/env python3
"""Servidor local: sirve la interfaz web y la API. Sin dependencias externas.

    python server.py            ->  http://127.0.0.1:8765
"""
import json, os, sys, time, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import importlib
import engine.layout as _layout
import engine.geometry as _geometry
import engine.plans as _plans
import engine.standards as _standards
import engine.programs as _programs
import engine.masterplan as _masterplan
import engine.dxf as _dxf


def _stamp():
    d = os.path.join(ROOT, "engine")
    return max(os.path.getmtime(os.path.join(d, f)) for f in os.listdir(d) if f.endswith(".py"))


_loaded = [_stamp()]


def engine():
    """Recarga el motor si cambió algún archivo (así no hace falta reiniciar tras actualizar)."""
    st = _stamp()
    if st != _loaded[0]:
        importlib.reload(_geometry)
        importlib.reload(_standards)
        importlib.reload(_plans)
        importlib.reload(_programs)
        importlib.reload(_masterplan)
        importlib.reload(_layout)
        importlib.reload(_dxf)
        _loaded[0] = st
    return _layout, _dxf


def generate(data):
    return engine()[0].generate(data)


def result_to_dxf(res):
    return engine()[1].result_to_dxf(res)

STATE = {"mass": None, "mass_version": 0, "result": None, "result_version": 0}
LOCK = threading.Lock()
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        if not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text") or ctype == "application/json" else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        p = self.path.split("?")[0]
        if p in ("/masterplan", "/masterplan.html"):
            with open(os.path.join(ROOT, "web", "masterplan.html"), "rb") as f:
                return self._send(200, f.read(), "text/html")
        if p == "/api/mp_samples":
            d = os.path.join(ROOT, "samples", "masterplan")
            out = {}
            for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                if fn.endswith(".json"):
                    with open(os.path.join(d, fn), encoding="utf-8") as f:
                        out[fn[:-5]] = json.load(f)
            return self._send(200, out)
        if p in ("/", "/index.html"):
            with open(os.path.join(ROOT, "web", "index.html"), "rb") as f:
                return self._send(200, f.read(), "text/html")
        if p == "/api/standards":
            return self._send(200, engine()[0].ST.DEFAULTS)
        if p == "/api/version":
            return self._send(200, {"version": engine()[0].VERSION})
        if p == "/api/mass":
            with LOCK:
                return self._send(200, {"version": STATE["mass_version"], "mass": STATE["mass"]})
        if p == "/api/result":
            with LOCK:
                return self._send(200, {"version": STATE["result_version"], "result": STATE["result"]})
        if p == "/api/dxf":
            with LOCK:
                if not STATE["result"]:
                    return self._send(404, {"error": "sin resultado"})
                return self._send(200, result_to_dxf(STATE["result"]).encode(), "text/plain")
        if p == "/api/samples":
            d = os.path.join(ROOT, "samples")
            out = {}
            for fn in sorted(os.listdir(d)):
                if fn.endswith(".json"):
                    with open(os.path.join(d, fn), encoding="utf-8") as f:
                        out[fn[:-5]] = json.load(f)
            return self._send(200, out)
        self._send(404, {"error": "no encontrado"})

    def do_POST(self):
        p = self.path.split("?")[0]
        try:
            body = self._body()
        except Exception as e:
            return self._send(400, {"error": str(e)})
        if p == "/api/mass":      # Rhino -> servidor
            with LOCK:
                STATE["mass"] = body
                STATE["mass_version"] += 1
            return self._send(200, {"ok": True, "version": STATE["mass_version"]})
        if p == "/api/masterplan":
            engine()
            try:
                return self._send(200, _masterplan.generate(body))
            except Exception as e:
                import traceback
                traceback.print_exc()
                return self._send(500, {"error": "%s: %s" % (type(e).__name__, e)})
        if p == "/api/damero":
            engine()
            S = _standards.merged(body.get("standards"))["masterplan"]
            for k, v in (body.get("masterplan") or {}).items():
                if v is not None:
                    S[k] = v
            return self._send(200, {"streets": _masterplan.damero(body["predio"], S, body.get("angle"))})
        if p == "/api/generate":  # UI -> motor
            try:
                res = generate(body)
            except Exception as e:
                import traceback
                traceback.print_exc()
                return self._send(500, {"error": "%s: %s" % (type(e).__name__, e)})
            with LOCK:
                STATE["result"] = res
                STATE["result_version"] += 1
                with open(os.path.join(DATA, "last_result.json"), "w", encoding="utf-8") as f:
                    json.dump(res, f)
            return self._send(200, res)
        self._send(404, {"error": "no encontrado"})


if __name__ == "__main__":
    port = int(os.environ.get("TRAZO_PORT", "8765"))
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    print("Trazo v%s en http://127.0.0.1:%d  (Ctrl+C para salir)" % (_layout.VERSION, port))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
