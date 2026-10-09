"""Pruebas de regresión (ROADMAP R0.3): métricas de referencia de cada ejemplo de samples/.

Cada ejemplo tiene en tests/golden/ un JSON con sus métricas (unidades, eficiencia, sin usar, núcleos...).
La prueba avisa si el motor las cambia más que el margen de cada métrica. Corre dentro de tests/test_engine.py.

    python tests/regresion.py               compara con las referencias y muestra la tabla de cada ejemplo
    python tests/regresion.py --actualizar  vuelve a guardar las referencias (solo si el cambio es intencional)
"""
import json
import math
import os
import sys

sys.dont_write_bytecode = True   # sin __pycache__: tras revertir un cambio, nunca se mide bytecode viejo
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)
from engine import layout, masterplan, standards as ST  # noqa: E402

SAMPLES = os.path.join(RAIZ, "samples")
GOLDEN = os.path.join(AQUI, "golden")

# métrica: (etiqueta, margen absoluto, margen relativo). Margen 0 = debe coincidir exactamente.
METRICAS = {
    "edificio": {
        "unidades": ("unidades por planta", 0, 0),
        "unidades_totales": ("unidades totales", 0, 0),
        "por_tipo": ("unidades por tipo", 0, 0),
        "nucleos": ("núcleos", 0, 0),
        "ascensores": ("ascensores por núcleo", 0, 0),
        "tramos": ("tramos de pasillo", 0, 0),
        "area_planta": ("área por planta (m²)", 0.5, 0),
        "eficiencia_planta": ("eficiencia de planta (%)", 0.5, 0),
        "eficiencia_total": ("eficiencia total (%)", 0.5, 0),
        "sin_usar": ("sin usar (m²)", 1.0, 0.02),
        "circulacion": ("circulación (%)", 0.5, 0),
        "match_score": ("match score", 1.0, 0),
        "fit_m2": ("fit medio (m²)", 0.5, 0),
        "calidad_planos": ("calidad de planos", 1.0, 0),
        "evacuacion_max": ("máx. distancia a núcleo (m)", 0.5, 0),
        "nsa_total": ("NSA total (m²)", 1.0, 0.01),
        "sin_luz": ("zona sin luz (m²)", 1.0, 0.02),
        "plazas": ("plazas de estacionamiento", 0, 0),
        "planta_libre": ("planta libre oficinas/comercio (m²)", 1.0, 0.01),
    },
    "masterplan": {
        "manzanas": ("manzanas", 0, 0),
        "lotes": ("lotes", 0, 0),
        "lotes_obs": ("lotes con observaciones", 0, 0),
        "lote_medio": ("lote medio (m²)", 1.0, 0.01),
        "calles_pct": ("calles (%)", 0.5, 0),
        "reserva_pct": ("reserva verde + equipamiento (%)", 0.5, 0),
        "cesiones_pct": ("cesiones (%)", 0.5, 0),
        "ocupacion": ("ocupación (m²)", 1.0, 0.01),
        "construible": ("área construible (m²)", 1.0, 0.01),
        "viviendas_est": ("viviendas estimadas", 1, 0.01),
    },
}


# ---------------------------------------------------------------- métricas de cada ejemplo
def _edificio(s):
    """Lo mismo que la web al elegir el ejemplo y pulsar «Generar planos» con los valores por defecto."""
    p = {}
    lines = s.get("centerlines") or ([s["centerline"]] if s.get("centerline") else None)
    if lines:
        p["centerlines"] = lines
    if s.get("cores"):
        p["cores_mode"], p["cores"] = "manual", s["cores"]
    for k in ("stories", "medianeras"):
        if s.get(k):
            p[k] = s[k]
    m = layout.generate({"footprint": s["footprint"], "height": s.get("height"), "stage": "plans", "params": p})["metrics"]
    progs = m.get("programs", {})
    libre = sum(v.get("free_area", 0) for v in progs.values())
    out = {"unidades": m["mix"]["count"], "unidades_totales": m["units_total"],
           "por_tipo": {k: v["count"] for k, v in sorted(m["mix"]["by_type"].items())},
           "nucleos": m["core_count"], "ascensores": m["core"]["elevators"], "tramos": m["wings"],
           "area_planta": m["plate_area"], "eficiencia_planta": m["efficiency"],
           "eficiencia_total": m["efficiency_total"], "sin_usar": m["unused_area"],
           "circulacion": m["circulation_pct"], "match_score": m["mix"]["match_score"], "fit_m2": m["mix"]["fit_m2"],
           "calidad_planos": m.get("plan_score"), "evacuacion_max": m["egress_max"], "nsa_total": m["nsa_total"],
           "sin_luz": m.get("dark_area"), "plazas": progs.get("Parking", {}).get("stalls"),
           "planta_libre": round(libre, 1) if libre else None}
    return {k: v for k, v in out.items() if v is not None}


def _media(pl):
    return sum(p[0] for p in pl) / len(pl), sum(p[1] for p in pl) / len(pl)


def _masterplan(s):
    """Lo mismo que la web al elegir el ejemplo: damero según la manzana del ejemplo y manzana verde central."""
    over = s.get("masterplan") or {}
    S = ST.merged(None)["masterplan"]
    S.update({k: v for k, v in over.items() if v is not None})
    data = {"predio": s["predio"], "frontage": s.get("frontage"), "params": {"masterplan": over},
            "streets": masterplan.damero(s["predio"], S) if s.get("damero") else s.get("streets") or []}
    r = masterplan.generate(data)
    if s.get("verde_centro") and r["blocks"]:
        c = _media(s["predio"])
        b = min(r["blocks"], key=lambda b: math.hypot(_media(b["poly"])[0] - c[0], _media(b["poly"])[1] - c[1]))
        data["block_uses"] = {b["key"]: "verde"}
        r = masterplan.generate(data)
    return {k: r["metrics"][k] for k in METRICAS["masterplan"]}


def ejemplos():
    """[(modo, nombre, ruta)] de los ejemplos de samples/ (modo Edificio) y samples/masterplan/."""
    out = []
    for modo, d in (("edificio", SAMPLES), ("masterplan", os.path.join(SAMPLES, "masterplan"))):
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                out.append((modo, fn[:-5], os.path.join(d, fn)))
    return out


def medir(modo, ruta):
    with open(ruta, encoding="utf-8") as f:
        s = json.load(f)
    return s.get("name", ""), (_masterplan(s) if modo == "masterplan" else _edificio(s))


def _ruta_ref(modo, nombre):
    return os.path.join(GOLDEN, "masterplan", nombre + ".json") if modo == "masterplan" \
        else os.path.join(GOLDEN, nombre + ".json")


def _rel(p):
    return os.path.relpath(p, RAIZ).replace(os.sep, "/")


# ---------------------------------------------------------------- comparación
def _margen(ref, a, r):
    return max(a, r * abs(ref)) if isinstance(ref, (int, float)) else 0


def _igual(ref, act, a, r):
    if isinstance(ref, (int, float)) and isinstance(act, (int, float)):
        return abs(act - ref) <= _margen(ref, a, r) + 1e-9
    return ref == act


def _fmt(v):
    if v is None:
        return "—"
    if isinstance(v, dict):
        return ", ".join("%s: %s" % kv for kv in v.items()) or "—"
    if isinstance(v, float):
        return str(round(v, 2))
    return str(v)


def filas(modo, ref, act):
    """[(etiqueta, referencia, ahora, margen, dentro_del_margen)] de un ejemplo."""
    out = []
    for k, (etq, a, r) in METRICAS[modo].items():
        if k in ref or k in act:
            vr, va = ref.get(k), act.get(k)
            out.append((etq, vr, va, _margen(vr, a, r), _igual(vr, va, a, r)))
    return out


def comparar(mostrar=False):
    """Diferencias fuera de margen: [(ejemplo, etiqueta, referencia, ahora, margen)]. Lista vacía = todo bien."""
    difs, vistos = [], set()
    for modo, nombre, ruta in ejemplos():
        rr = _ruta_ref(modo, nombre)
        vistos.add(os.path.normcase(rr))
        nom, act = medir(modo, ruta)
        if not os.path.exists(rr):
            difs.append((nombre, "falta la referencia " + _rel(rr), None, None, None))
            continue
        with open(rr, encoding="utf-8") as f:
            ref = json.load(f)["metricas"]
        fs = filas(modo, ref, act)
        difs += [(nombre, etq, vr, va, mg) for etq, vr, va, mg, ok in fs if not ok]
        if mostrar:
            w = max([12] + [len(_fmt(v)) for f in fs for v in f[1:3]])
            print("\n%s · %s" % (nombre, nom))
            print("  %-36s %*s %*s" % ("métrica", w, "referencia", w, "ahora"))
            for etq, vr, va, mg, ok in fs:
                nota = "" if vr == va else ("  (cambió, dentro del margen)" if ok else "  <-- FUERA DE MARGEN")
                print("  %-36s %*s %*s%s" % (etq, w, _fmt(vr), w, _fmt(va), nota))
    for d in (GOLDEN, os.path.join(GOLDEN, "masterplan")):
        for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            p = os.path.join(d, fn)
            if fn.endswith(".json") and os.path.normcase(p) not in vistos:
                difs.append((fn[:-5], "sobra la referencia %s (su ejemplo ya no existe)" % _rel(p), None, None, None))
    return difs


def mensaje(difs):
    lineas = ["Pruebas de regresión: cambiaron métricas de los ejemplos de samples/ (referencias en tests/golden/)."]
    for ej, etq, vr, va, mg in difs:
        if mg is None:
            lineas.append("  %s: %s" % (ej, etq))
        elif vr is None or va is None:
            lineas.append("  %s · %s: %s" % (ej, etq, "antes no había, ahora %s" % _fmt(va) if vr is None
                                             else "era %s, ahora no hay" % _fmt(vr)))
        else:
            lineas.append("  %s · %s: era %s, ahora %s (%s)" % (ej, etq, _fmt(vr), _fmt(va),
                                                               "margen ±%s" % _fmt(mg) if mg else "debe ser igual"))
    lineas += ["Si el cambio es intencional (una mejora del motor o un ejemplo nuevo), actualiza las referencias con",
               "    python tests/regresion.py --actualizar",
               "y explica en el PR qué métricas cambian y por qué (pega la tabla de «python tests/regresion.py»)."]
    return "\n".join(lineas)


def actualizar():
    """Vuelve a medir todos los ejemplos y reescribe tests/golden/ (borra las referencias sin ejemplo)."""
    os.makedirs(os.path.join(GOLDEN, "masterplan"), exist_ok=True)
    vistos = set()
    for modo, nombre, ruta in ejemplos():
        nom, act = medir(modo, ruta)
        rr = _ruta_ref(modo, nombre)
        vistos.add(os.path.normcase(rr))
        with open(rr, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"ejemplo": _rel(ruta), "nombre": nom, "version_motor": layout.VERSION, "metricas": act},
                      f, ensure_ascii=False, indent=1)
            f.write("\n")
    for d in (GOLDEN, os.path.join(GOLDEN, "masterplan")):
        for fn in sorted(os.listdir(d)):
            p = os.path.join(d, fn)
            if fn.endswith(".json") and os.path.normcase(p) not in vistos:
                os.remove(p)
                print("Borrada %s (su ejemplo ya no existe)" % _rel(p))
    print("Referencias guardadas en %s (%d ejemplos)." % (_rel(GOLDEN), len(vistos)))


if __name__ == "__main__":
    if "--actualizar" in sys.argv[1:]:
        actualizar()
    difs = comparar(mostrar=True)
    print()
    print(mensaje(difs) if difs else "Sin cambios fuera de margen en los %d ejemplos." % len(ejemplos()))
    sys.exit(1 if difs else 0)
