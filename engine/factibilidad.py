"""Factibilidad por gama de construcción (ROADMAP R10.13; datos, fórmulas y fuentes en COSTOS.md y STANDARDS.md).

A partir de lo que el motor ya calcula (superficie bruta de cada programa y superficie vendible) estima el costo de obra
según la gama (baja, media o alta), el resto de los rubros de un desarrollo, el ingreso por venta con tres precios (bajo,
esperado y alto), el margen, el ROI (margen / costo total), el precio de equilibrio y un semáforo contra el margen
objetivo. Todas las medidas salen de `standards.costos` (nada escrito aquí) y son valores de referencia: los costos por
gama están triangulados, no hay una fuente pública de obra por m² de edificios en Uruguay, y hay que validarlos con
presupuestos de constructoras antes de confiar en ellos. Solo biblioteca estándar.
"""
import math

from . import geometry as G

GAMAS = ("baja", "media", "alta")           # el orden de las listas por gama de standards.costos (obra_m2, sau, …)
PRECIOS = ("bajo", "esperado", "alto")      # el orden de standards.costos["precio_venta"]


# ---------------------------------------------------------------- utilidades
def _num(v, defecto):
    """Un número finito del pedido de la web; lo que no lo es (vacío, texto, None) vale `defecto`."""
    if isinstance(v, bool):
        return defecto
    try:
        x = float(v)
    except (TypeError, ValueError):
        return defecto
    return x if math.isfinite(x) else defecto


def _de(lista, g):
    """El valor de la gama g de una lista de standards.costos (la última, si la lista es más corta)."""
    return lista[min(g, len(lista) - 1)]


def _pc(x):
    """Porcentaje para un texto, con coma decimal y al menos un decimal: «2,0 %», «3,66 %»."""
    t = "%.2f" % x
    return (t[:-1] if t.endswith("0") else t).replace(".", ",") + " %"


def gama_de(fz):
    """Índice de la gama de params.factibilidad (baja si falta o no se conoce)."""
    g = str((fz or {}).get("gama") or "").strip().lower()
    return GAMAS.index(g) if g in GAMAS else 0


# ---------------------------------------------------------------- honorarios y permiso
def honorarios_sau(obra, g, C):
    """Honorarios de arquitectura y dirección de obra según el arancel de la SAU (COSTOS.md, 3.2): tramos acumulativos
    sobre el valor de la obra con IVA (`sau_iva`) en millones de pesos de marzo de 1997. Cada tramo (`sau_tramos`) pasa a
    USD con el coeficiente de actualización (`sau_actualizacion`) y el tipo de cambio (`tipo_cambio`), así que se aplica
    directo sobre la obra en USD. `g`: gama (0 baja = categoría A, 1 media = B, 2 alta = C, la fila de `sau`)."""
    base = obra * C["sau_iva"]
    por_millon = C["sau_actualizacion"] * 1e6 / max(C["tipo_cambio"], 1e-9)       # USD de un millón de pesos de 1997
    limites = [t * por_millon for t in C["sau_tramos"]] + [math.inf]
    total, desde = 0.0, 0.0
    for hasta, tasa in zip(limites, _de(C["sau"], g)):
        if base > desde:
            total += (min(base, hasta) - desde) * tasa / 100.0
        desde = hasta
    return total


def _ui_por_m2(tamano, serie, hasta):
    """UI por m² del permiso de construcción según el tamaño (m²) de la unidad: `serie` tiene un valor por tramo y `hasta`
    los límites entre tramos (hasta 70 m², hasta 140 m² y más)."""
    for i, h in enumerate(hasta):
        if tamano <= h:
            return serie[min(i, len(serie) - 1)]
    return serie[min(len(hasta), len(serie) - 1)]


def _ui_vivienda(unidades, C):
    """UI por m² de la vivienda: la de cada unidad según su tamaño, ponderada por su superficie (sin unidades todavía,
    la del primer tramo)."""
    total = sum(unidades)
    if total <= 0:
        return C["permiso_ui"][0]
    return sum(_ui_por_m2(a, C["permiso_ui"], C["permiso_hasta"]) * a for a in unidades) / total


def _coef(programa, C):
    """Coeficiente del costo de obra de un programa: cochera (y subsuelo), amenities y 1 para el resto."""
    return C["coef_cochera"] if programa == "Parking" else C["coef_amenities"] if programa == "Amenities" else 1.0


def _precios(fz, C):
    """Los tres precios de venta (USD por m² vendible): los del pedido y, donde faltan, los de standards.costos."""
    p = fz.get("precio_venta")
    p = p if isinstance(p, dict) else {}
    return [max(0.0, _num(p.get(k), C["precio_venta"][min(i, len(C["precio_venta"]) - 1)])) for i, k in enumerate(PRECIOS)]


# ---------------------------------------------------------------- el cálculo
def calcular(programas, nsa, unidades, fz, C, huella=0.0):
    """La factibilidad de un edificio.
    programas: {programa: {"gfa": m² brutos de todos sus niveles, "stories": niveles}} (metrics.programs).
    nsa: superficie vendible total (m², metrics.nsa_total). unidades: superficie con muros de cada vivienda de la planta tipo
    (para la tasa del permiso según el tamaño). fz: params.factibilidad {gama, terreno {modo: total | m2, valor},
    superficie_terreno, precio_venta {bajo, esperado, alto}, margen_objetivo (%), balcones_m2}. C: standards["costos"].
    huella: superficie de la masa (m²), para el terreno por m² cuando no se conoce la del predio.
    Devuelve el diccionario de metrics.factibilidad (ver más abajo)."""
    fz = fz if isinstance(fz, dict) else {}
    avisos = []
    nombre = str(fz.get("gama") or "").strip().lower()
    if nombre and nombre not in GAMAS:
        avisos.append("La gama «%s» no existe: se calcula con la baja (elige baja, media o alta)." % nombre)
    g = gama_de(fz)
    costo_m2 = _de(C["obra_m2"], g)

    # ---- obra: m² brutos de cada programa por el costo de la gama y el coeficiente de su tipo de superficie
    progs, gfa_total, equivalente, obra = [], 0.0, 0.0, 0.0
    permiso = 0.0                                        # UI del permiso (los balcones no lo pagan)
    sin_ingreso = 0.0
    for prog, d in programas.items():
        gfa = _num(d.get("gfa"), 0.0)
        if gfa <= 0:
            continue
        coef = _coef(prog, C)
        niveles = max(1, int(_num(d.get("stories"), 1)))
        if prog == "Residential":
            ui = _ui_vivienda(unidades, C)
        elif prog in ("Office", "Retail"):               # oficinas y comercio: según el tamaño de la planta de cada nivel
            ui = _ui_por_m2(gfa / niveles, C["permiso_comercio_ui"], C["permiso_hasta"])
        else:
            ui = C["permiso_otros_ui"]
        progs.append({"programa": prog, "niveles": niveles, "gfa": round(gfa, 1), "coef": coef,
                      "obra": round(gfa * coef * costo_m2, 2), "ui_m2": round(ui, 2)})
        gfa_total += gfa
        equivalente += gfa * coef
        obra += gfa * coef * costo_m2
        permiso += gfa * ui * C["ui_usd"]
        if prog != "Residential":
            sin_ingreso += gfa
    balcones = max(0.0, _num(fz.get("balcones_m2"), 0.0))
    if balcones:
        equivalente += balcones * C["coef_balcon"]
        obra += balcones * C["coef_balcon"] * costo_m2

    # ---- los demás rubros (todos sobre la obra, salvo el permiso, el terreno y lo que se calcula sobre él)
    t = fz.get("terreno")
    t = t if isinstance(t, dict) else {"valor": t}
    modo = "m2" if str(t.get("modo") or "").lower() == "m2" else "total"
    valor = max(0.0, _num(t.get("valor"), 0.0))
    sup = max(0.0, _num(fz.get("superficie_terreno"), 0.0))
    fuente = "predio" if sup > 0 else "masa"
    sup = sup or huella
    terreno = valor * sup if modo == "m2" else valor
    if modo == "m2" and sup <= 0:
        avisos.append("No se conoce la superficie del terreno: el precio por m² no se puede multiplicar. Carga el precio "
                      "total o crea la masa con «Terreno rectangular».")
    elif terreno <= 0:
        avisos.append("Falta el precio del terreno: el costo y el margen no lo incluyen. Cárgalo en Factibilidad.")
    compra = terreno * C["compra_terreno_pct"] / 100.0
    pct = lambda clave: _de(C[clave], g)
    rubros = [
        ("obra", "Obra", obra, "%s m² equivalentes a USD %s/m²" % (("%.0f" % equivalente), ("%.0f" % costo_m2))),
        ("honorarios", "Honorarios de arquitectura (SAU)", honorarios_sau(obra, g, C),
         "arancel de la SAU, categoría %s" % "ABC"[min(g, 2)]),
        ("ingenieria", "Ingeniería y estudios", obra * pct("ingenieria_pct") / 100.0, _pc(pct("ingenieria_pct")) + " de la obra"),
        ("permiso", "Permiso de construcción", permiso, "UI por m² del permiso, USD %s por UI" % ("%.4f" % C["ui_usd"]).replace(".", ",")),
        ("caja", "Caja de Profesionales", obra * C["caja_pct"] / 100.0 * C["mano_obra_pct"] / 100.0,
         _pc(C["caja_pct"]) + " de la mano de obra (" + _pc(C["mano_obra_pct"]) + " de la obra)"),
        ("conexiones", "Conexiones, Bomberos y escribanía", obra * C["conexiones_pct"] / 100.0, _pc(C["conexiones_pct"]) + " de la obra"),
        ("imprevistos", "Imprevistos", obra * pct("imprevistos_pct") / 100.0, _pc(pct("imprevistos_pct")) + " de la obra"),
        ("administracion", "Administración del desarrollador", obra * pct("administracion_pct") / 100.0,
         _pc(pct("administracion_pct")) + " de la obra"),
        ("terreno", "Terreno", terreno, "USD por m² × %.0f m²" % sup if modo == "m2" else "precio total"),
        ("compra", "Comisión y gastos de compra del terreno", compra, _pc(C["compra_terreno_pct"]) + " del terreno"),
        ("financieros", "Costos financieros", (obra + terreno + compra) * pct("financieros_pct") / 100.0,
         _pc(pct("financieros_pct")) + " de obra + terreno"),
    ]
    fijo = sum(r[2] for r in rubros)
    com = pct("comercializacion_pct") / 100.0

    # ---- ingreso y margen con cada precio; el ROI es margen / costo total (la comercialización depende del ingreso)
    objetivo = _num(fz.get("margen_objetivo"), C["margen_objetivo"])
    esc = {}
    precios = _precios(fz, C)
    for k, p in zip(PRECIOS, precios):
        ingreso = nsa * p
        comercializacion = ingreso * com
        costo = fijo + comercializacion
        margen = ingreso - costo
        esc[k] = {"precio": round(p, 2), "ingreso": round(ingreso, 2), "comercializacion": round(comercializacion, 2),
                  "costo_total": round(costo, 2), "margen": round(margen, 2),
                  "roi": round(margen / costo * 100.0, 2) if costo > 0 else None,
                  "margen_venta": round(margen / ingreso * 100.0, 2) if ingreso > 0 else None}
    if not precios[0] <= precios[1] <= precios[2]:
        avisos.append("Los precios de venta no van de menor a mayor (bajo, esperado, alto): el semáforo supone que sí.")
    equilibrio = fijo / (nsa * (1.0 - com)) if nsa > 0 and com < 1 else None     # ingreso − comercialización = costo fijo

    # ---- semáforo: verde si el ROI esperado alcanza el objetivo; amarillo si solo lo alcanza el precio alto; rojo si ni ese
    eps = 1e-9
    roi = {k: esc[k]["roi"] for k in PRECIOS}
    alcanza = lambda k: roi[k] is not None and roi[k] + eps >= objetivo
    if nsa <= 0:
        semaforo, texto = "rojo", "Sin superficie vendible no hay ingreso: genera el mix o los planos con viviendas."
        avisos.append(texto)
    elif alcanza("esperado"):
        semaforo, texto = "verde", "Viable: el ROI esperado (%s) alcanza el margen objetivo (%s)." % (_pc(roi["esperado"]), _pc(objetivo))
    elif alcanza("alto"):
        semaforo, texto = "amarillo", "Ajustado: solo el precio alto alcanza el margen objetivo (%s); con el esperado el ROI es %s." % (
            _pc(objetivo), _pc(roi["esperado"]))
    else:
        semaforo, texto = "rojo", "No viable: ni con el precio alto se alcanza el margen objetivo (%s); el ROI con el precio alto es %s." % (
            _pc(objetivo), _pc(roi["alto"] if roi["alto"] is not None else 0.0))
    if sin_ingreso > 0:
        avisos.append("El ingreso cuenta solo la superficie vendible de vivienda: %.0f m² de oficinas, comercio, amenities o "
                      "cocheras suman costo pero no ingreso." % sin_ingreso)
    esperado = esc["esperado"]
    return {
        "gama": GAMAS[g], "costo_m2": costo_m2, "objetivo": objetivo,
        "superficies": {"gfa": round(gfa_total, 1), "equivalente": round(equivalente, 1), "nsa": round(nsa, 1),
                        "balcones": balcones, "programas": progs},
        "terreno": {"modo": modo, "valor": valor, "superficie": round(sup, 1), "fuente": fuente, "usd": round(terreno, 2)},
        "rubros": [{"id": i, "nombre": n, "usd": round(v, 2), "base": b} for i, n, v, b in rubros],
        "costo_sin_comercializacion": round(fijo, 2), "comercializacion_pct": round(com * 100.0, 2),
        "escenarios": esc,
        "precio_equilibrio": round(equilibrio, 2) if equilibrio is not None else None,
        "costo_m2_bruto": round(esperado["costo_total"] / gfa_total, 2) if gfa_total > 0 else None,
        "costo_m2_vendible": round(esperado["costo_total"] / nsa, 2) if nsa > 0 else None,
        "semaforo": semaforo, "semaforo_texto": texto, "avisos": avisos,
    }


def estimar(res, params, S, footprint=None):
    """La factibilidad del resultado `res` del motor (metrics.programs, metrics.nsa_total y las viviendas) con
    params.factibilidad y las medidas S["costos"]; `footprint`: la masa del pedido, para el terreno por m² sin predio."""
    m = res["metrics"]
    unidades = [_num(u.get("area_muros"), 0.0) or _num(u.get("area"), 0.0) for u in res.get("units") or []]
    huella = abs(G.area([tuple(p) for p in footprint])) if footprint and len(footprint) >= 3 else 0.0
    return calcular(m.get("programs") or {}, _num(m.get("nsa_total"), 0.0), unidades, params.get("factibilidad"),
                    S["costos"], huella)
