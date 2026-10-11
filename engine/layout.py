"""Motor de generación: masa -> planta -> pasillo/núcleos -> mix de unidades -> planos de unidad.

Inspirado en el flujo público de Finch 101 (Massing Studio, Generate Corridors and Core,
Generate Unit Mix around Corridor, Unit Plans). Es una implementación propia y simplificada.
"""
import math

from . import geometry as G
from . import standards as ST
from . import programs as PR
from . import evacuacion as EV
from . import plans as P
# el motor está repartido en módulos; layout reexporta sus funciones (las usan las pruebas y el servidor)
from .massing import (_inward, apply_setbacks, make_blind, build_massing, _dominant_angle, _is_rectilinear, _slabs,
                      decompose_wings, _lado_ciego, _dist_point_segment, _dist_to_boundary)  # noqa: F401
from .circulation import (pick_frame, core_positions, side_for, _frame_for_poly, _make_piece, _avg_unit_area,
                          _choose_single, _ring_single, _single_frame, _bridge_axis, build_pieces, _link, _connect,
                          _franjas_sin_luz, _clip_sr, build_user_pieces, _stem_vs_trunk, _split_parallel, egress_at,
                          _add_core, _propagate_core_blocks, generate_circulation, is_between, _between_depth,
                          _generate_circulation, nucleo_punto, medidas_nucleo)  # noqa: F401
from .units import (_bisect_x, _chain_union, _is_rect, _segments, generate_unit_mix, metrics_mix, bedrooms_for,
                    unit_rooms, sin_solapes, editar_unidades, vecinas, formar_frentes, entradas)  # noqa: F401
from .patios import (auto_patios, _anillo, split_blocks, make_patio_dark, _block_of, _block_of_line)  # noqa: F401

VERSION = "2.35"

DEFAULT_PARAMS = {
    # Masa
    "floor_height": 3.0,
    "outer_wall": 0.35,
    "stories": None,            # lista opcional [{program, height}]
    # Pasillo / núcleos
    "centerline": None,         # (compatibilidad) [[x,y],[x,y]]
    "centerlines": None,        # lista de polilíneas [[[x,y],...],...] en coordenadas de mundo; None = automático
    "cores_mode": "auto",       # auto | manual
    "cores": None,              # núcleos manuales: [x, y] o {"p": [x, y], "frente", "fondo", "giro": 0|90} (mundo; se ajustan al pasillo)
    "corridor_width": 2.0,
    "core_width": 5.0,
    "core_depth": 7.0,          # incluye el pasillo (como en Finch)
    "core_count": 2,
    "auto_cores": True,
    "core_side": "alternate",   # alternate | left | right
    "egress_single": 18.0,      # fondo de saco máximo: con una sola dirección de salida (R3.6)
    "egress_multi": 30.0,       # recorrido máximo desde la puerta hasta el núcleo más cercano
    # Mix
    "unit_mix": [{"name": "2 dorm", "area": 75, "percent": 50, "dorms": 2},
                 {"name": "3 dorm", "area": 95, "percent": 50, "dorms": 3}],
    "min_unit_width": 5.0,
    "party_wall": 0.30,
    "max_unit_depth": 14.0,
    "unit_width_target_min": 4.0,
    "loading": "auto",          # auto | double | single (pasillo central o pasillo de borde)
    "core_auto": True,          # núcleo dimensionado a partir de escalera + ascensores (standards)
    "ascensores": "auto",       # R10.7: ascensores de cada núcleo: auto (según las viviendas que sirve) o una cantidad
    "standards": None,          # valores que sobrescriben engine/standards.py
    "medianeras": None,         # [{"a":[x,y],"b":[x,y],"retiro":m}] bordes del predio contra linderos
    "patios_mode": "auto",      # auto (patios en predios entre medianeras demasiado profundos) | manual
    "patios": None,             # patios manuales: [[[x,y],...],...] en coordenadas de mundo
    "unit_edits": None,         # R4.4: [{"op": "tabique"|"fusionar"|"dividir", "p": [x,y], "a": [x,y]}] en orden (units.editar_unidades)
    "room_edits": None,         # R5.7: [{"op": "pared", "p", "a"} | {"op": "puerta", "p", "entre"?, "a"?, "ancho"?, "abre"?}] en orden (plans)
}


def merge_params(p):
    out = dict(DEFAULT_PARAMS)
    out.update({k: v for k, v in (p or {}).items() if v is not None or k in ("stories", "centerline", "centerlines", "cores", "medianeras", "patios")})
    return out


# ---------------------------------------------------------------- ascensores por núcleo (R10.7)
def _nucleo_de(red, pieces, i, x):
    """Índice en res["cores"] del núcleo más cercano por el pasillo desde x en la pieza i (None si no se llega)."""
    n = EV.nucleo(red, i, x)
    if n is None:
        return None
    return next((c.get("_res") for c in pieces[n[0]]["cores"] if abs(c["x"] - n[1]) < 1e-6), None)


def _ascensores_pedidos(cores, S, n_niveles, sube, units=None, n_res=1, por_nucleo=None):
    """Ascensores que lleva cada núcleo automático, iguales en todos: los que pide el más cargado, 1 cada
    S["unidades_por_ascensor"] viviendas de las que sirve (las que tienen en él su recorrido más corto, por los niveles
    residenciales) y al menos 1. Desde S["pisos_dos_ascensores"] niveles, el edificio lleva al menos 2 en total
    (criterio del usuario: el mínimo es por edificio). Sin viviendas todavía, con por_nucleo = viviendas estimadas del
    edificio, repartidas entre los núcleos. None si no hay núcleos automáticos."""
    auto = [k for k, c in enumerate(cores) if not c.get("ascensores_propios")]
    if not auto:
        return None
    if not sube:
        return 0
    if units is not None:
        por = {}
        for u in units:
            if u.get("_nucleo") is not None:
                por[u["_nucleo"]] = por.get(u["_nucleo"], 0) + 1
        servidas = [por.get(k, 0) * n_res for k in auto]
    else:
        servidas = [por_nucleo / float(len(cores))] * len(auto)
    n = max(max(1, int(math.ceil(s / float(S["unidades_por_ascensor"]) - 1e-9))) for s in servidas)
    propios = sum(c["ascensores"] for c in cores if c.get("ascensores_propios"))
    if n_niveles >= S["pisos_dos_ascensores"] and n * len(auto) + propios < 2:
        n = 2 - propios if len(auto) == 1 else n
    return n


# ---------------------------------------------------------------- orquestación
def generate(data):
    params = merge_params(data.get("params"))
    S0 = ST.merged(params.get("standards"))
    params["_blind"] = make_blind(params.get("medianeras"), S0["predio"]["retiro_ventanas"])
    P.configure(S0["vivienda"], S0["equipamiento"])         # medidas de los planos (frentes y fondos de las viviendas)
    stage = data.get("stage", "plans")
    footprint = data["footprint"]
    height = float(data.get("height") or params["floor_height"] * 5)
    fp, plate, stories = build_massing(footprint, height, params)
    res = {"stage": stage, "footprint": G.pol_to_list(fp), "stories": stories, "warnings": []}
    meds = params.get("medianeras") or []
    rmin = S0["predio"]["retiro_ventanas"]
    res["medianeras"] = [{"a": m["a"], "b": m["b"], "retiro": float(m.get("retiro") or 0),
                          "ventanas": float(m.get("retiro") or 0) >= rmin} for m in meds]
    for m in res["medianeras"]:
        if 0 < m["retiro"] < rmin:
            res["warnings"].append("Retiro de %.1f m en medianera: menor a %.1f m, sigue sin admitir ventanas" % (m["retiro"], rmin))
    # ---- núcleo real: escalera + ascensores según altura y unidades servidas
    S = ST.merged(params.get("standards"))
    cw = params["corridor_width"]
    hs = [round(s_["height"], 2) for s_ in stories]
    floor_h = max(set(hs), key=hs.count)                  # altura de piso más frecuente
    for s_ in stories:
        if s_["height"] > floor_h + 0.01:
            res["warnings"].append("Nivel %d (%.2f m) más alto que la planta tipo: su escalera necesita %d contrahuellas" %
                                   (s_["index"], s_["height"], ST.stair_box(ST.merged(params.get("standards"))["nucleo"], s_["height"])[2]))
    top_h = stories[-1]["z"]
    n_res_lv = sum(1 for s_ in stories if s_["program"] == "Residential")
    units_est = abs(G.area(plate)) * 0.72 / max(_avg_unit_area(params), 1.0) * n_res_lv
    sube = top_h > S["nucleo"]["altura_sin_ascensor"]      # acceso a más de 9 m: el edificio necesita ascensor
    fijo = str(params.get("ascensores") or "auto").strip()  # R10.7: «auto» o la misma cantidad en todos los núcleos
    if fijo.isdigit():
        n_elev = int(fijo)
    elif params.get("_ascensores") is not None:            # segunda pasada: los que pide el núcleo más cargado
        n_elev = int(params["_ascensores"])
    else:                                                  # primera pasada: uno por núcleo; después se ajusta a las
        n_elev = 1 if sube else 0                          # viviendas que sirve cada uno (_ascensores_pedidos)
    tam = lambda n, giro=0: ST.core_size(S["nucleo"], floor_h, n, cw, giro=giro)
    params["_tam_nucleo"] = tam                            # un núcleo manual con sus propios ascensores
    if params.get("core_auto", True):
        params["core_width"], params["core_depth"] = tam(n_elev)
    params["_core_90"] = tam(n_elev, 90)                   # núcleo girado (R3.5)
    otra_pasada = lambda n: generate(dict(data, params=dict(data.get("params") or {}, _ascensores=n)))
    sw_, sl_, risers_ = ST.stair_box(S["nucleo"], floor_h)
    stype = ("común" if top_h <= 12 else "protegida (EP)" if top_h <= 30 else "presurizada (PFP)")
    core_m = {"elevators": n_elev, "width": params["core_width"],
              "depth": round(params["core_depth"] - cw, 2), "stair_type": stype,
              "stair_box": [round(sw_, 2), round(sl_, 2)], "risers": risers_,
              "riser_h": round(floor_h / risers_, 3), "top_level": round(top_h, 2)}
    # ---- patios: la huella menos los patios da uno o más bloques, cada uno con su planta, su pasillo y su núcleo
    ancho_patio = S0["predio"]["patio_min"]
    auto = params.get("patios_mode", "auto") != "manual"
    patios = auto_patios(fp, plate, params, ancho_patio) if auto else \
        [p for p in (params.get("patios") or []) if len(p) >= 3]
    if patios:
        bloques, plantas, partes = split_blocks(fp, patios, params, res["warnings"])
        params["_patio_dark"] = make_patio_dark(partes, ancho_patio, params["outer_wall"], res["warnings"])
    else:
        bloques, plantas, partes = [(fp, [])], [(plate, [])], []
    neta = lambda bh: abs(G.area(bh[0])) - sum(abs(G.area(h)) for h in bh[1])     # sin los patios interiores
    gfa_plate = sum(neta(p) for p in plantas)
    fp_area = sum(neta(b) for b in bloques)
    res["plate"] = G.pol_to_list(plantas[0][0] if plantas else plate)
    res["blocks"] = []
    for (b, hb), (p, hp) in zip(bloques, plantas):
        res["blocks"].append({"footprint": G.pol_to_list(b), "plate": G.pol_to_list(p)})
        if hb:                                               # anillo alrededor de patios interiores
            res["blocks"][-1].update(holes=[G.pol_to_list(h) for h in hb], plate_holes=[G.pol_to_list(h) for h in hp])
    huellas = [b for b, _ in bloques]
    res["patios"] = [G.pol_to_list(p) for p in partes]
    res["patios_auto"] = auto
    res["metrics"] = {"plate_area": round(gfa_plate, 1), "gfa": round(fp_area * len(stories), 1), "stories": len(stories)}
    if partes:
        res["metrics"]["blocks"] = len(bloques)
        res["metrics"]["patio_area"] = round(sum(abs(G.area(p)) for p in partes), 1)
    progs = {}
    for st in stories:
        d = progs.setdefault(st["program"], {"stories": 0, "gfa": 0.0, "nia": 0.0, "nsa": 0.0, "levels": []})
        d["stories"] += 1
        d["gfa"] += fp_area
        d["nia"] += gfa_plate
        d["levels"].append(st["index"])
    for d in progs.values():
        d["gfa"], d["nia"] = round(d["gfa"], 1), round(d["nia"], 1)
    res["metrics"]["programs"] = progs
    res["metrics"]["core"] = core_m
    if stage == "massing" or not plantas:
        return res
    W = lambda pc, pl: G.pol_to_list(G.to_world(pl, pc["origin"], pc["angle"]))
    manual = params.get("cores_mode") == "manual"
    res["corridors"], res["cores"], res["dark_zones"] = [], [], []
    bloques_pc = []                                          # por bloque: (piezas, parámetros, planta, núcleos, viviendas)
    emax = area_codos = 0.0
    state, hechos, avisos_u = {}, set(), []                  # mix compartido entre bloques, cambios R4.4 aplicados
    for bi, (pl_b, ph_b) in enumerate(plantas):
        pb = dict(params)
        mapa = None
        if len(plantas) > 1:
            pb["core_count"] = 1                             # cada bloque, al menos un núcleo propio
            if manual:
                mapa = [k for k, c in enumerate(params.get("cores") or []) if _block_of(nucleo_punto(c), huellas) == bi]
                pb["cores"] = [params["cores"][k] for k in mapa]
            if params.get("centerlines"):
                pb["centerlines"] = [l for l in params["centerlines"] if _block_of_line(l, huellas) == bi] or None
        if ph_b:                                             # anillo: alas alrededor del patio y pasillo que da la vuelta
            pb["_huecos"] = ph_b
            if pb.get("centerlines") or pb.get("centerline"):
                res["warnings"].append("Bloque %d: con un patio interior, el pasillo se traza solo alrededor del patio; "
                                       "las polilíneas dibujadas todavía no se usan ahí" % (bi + 1))
                pb["centerlines"] = pb["centerline"] = None
        if is_between(pl_b, pb) and not manual:
            pb["_cw_base"] = pb["corridor_width"]
            pb["corridor_width"] = max(pb["corridor_width"], pb["core_depth"] - pb["corridor_width"])
            res["metrics"]["between"] = True
        cw_b = pb["corridor_width"]
        pieces = generate_circulation(pl_b, pb)
        if "frame" not in res:
            p0 = pieces[0]
            res["frame"] = {"origin": [round(p0["origin"][0], 4), round(p0["origin"][1], 4)],
                            "angle": round(p0["angle"], 6), "xa": p0["xa"], "xb": p0["xb"]}
        cpolys = []
        for pc in pieces:
            for c in pc["cores"]:
                if c["poly_local"]:
                    cen = G.to_world([G.centroid(c["poly_local"])], pc["origin"], pc["angle"])[0]
                    n_c = c["ascensores"] if c.get("ascensores") is not None else n_elev      # R10.7
                    if c.get("between"):
                        parts = PR.core_parts(c["box"], 1, -(c["box"][3] - c["box"][1]), S["nucleo"], floor_h, n_c)
                    else:
                        parts = PR.core_parts(c["box"], c["side"], cw_b, S["nucleo"], floor_h, n_c, c.get("giro", 0))
                    c["_res"] = len(res["cores"])
                    spec = c.get("spec")
                    if mapa is not None and spec is not None:
                        spec = mapa[spec]
                    b_ = c["box"]
                    res["cores"].append({"poly": W(pc, G.largest_part(c["poly_local"])), "x": round(c["x"], 3), "side": c["side"],
                                         "center": [round(cen[0], 3), round(cen[1], 3)], "spec": spec,
                                         "giro": c.get("giro", 0), "frente": round(b_[2] - b_[0], 2),
                                         "ascensores": n_c, "ascensores_propios": c.get("ascensores") is not None,
                                         "fondo": round(b_[3] - b_[1] - cw_b, 2),
                                         "parts": [{"kind": p_["kind"], "name": p_["name"], "poly": W(pc, p_["poly"]),
                                                    "lines": [W(pc, ln) for ln in p_["lines"]]} for p_ in parts]})
                    cpolys.append(res["cores"][-1]["poly"])
                    if c.get("pisa"):
                        res["warnings"].append("El núcleo %d se superpone con otro: muévelo o quítalo (núcleos manuales)" %
                                               len(res["cores"]))
        if len(plantas) > 1 and not cpolys:
            res["warnings"].append("El bloque %d no tiene núcleo: añade uno (en modo manual cada bloque necesita el suyo)" % (bi + 1))
        # viviendas del bloque, antes de dibujar el pasillo: R3.7, el pasillo termina en la última puerta
        del_bloque = []
        for i, pc in enumerate(pieces):
            us, warns = generate_unit_mix(pc, pb, state)
            avisos_u += warns
            for u in us:
                u["_pc"], u["_pb"], u["_plate"], u["_i"] = pc, pb, pl_b, i
            del_bloque += us
        editar_unidades(del_bloque, params.get("unit_edits"), pb, hechos)   # R4.4: tabiques movidos, viviendas unidas o divididas
        del_bloque, warns = sin_solapes(del_bloque, pieces, cpolys, pb)
        avisos_u += warns
        formar_frentes(del_bloque, pieces, pb)           # R3.7: vivienda al frente en la punta de un pasillo de borde
        entradas(del_bloque, pieces, pb)                 # R3.7: entrada por el pasillo que queda tras cortar una punta
        for pc in pieces:
            t = pc.get("tramo")                          # R3.7: solo se corta la punta que ya no hace falta
            pasillo = G.clip_rect(pc["corridor_local"], t[0] if t[0] > pc["xa"] + 1e-6 else None,
                                  t[1] if t[1] < pc["xb"] - 1e-6 else None) if t else pc["corridor_local"]
            for parte in G.split_parts(pasillo):           # un pasillo que cruza una muesca: varias partes
                res["corridors"].append(W(pc, parte))
            for ext in pc["corridor_ext"]:
                res["corridors"].append(G.pol_to_list(ext))
        res["dark_zones"] += [G.pol_to_list(d_) for pc in pieces for d_ in pc.get("dark", [])]
        codos = [G.pol_to_list(d_) for pc in pieces for d_ in pc.get("codos", [])]
        res["dark_zones"] += codos
        if codos:
            res.setdefault("dark_corners", []).extend(codos)  # cuáles de las zonas sin luz son esquinas (codos)
        area_codos += sum(abs(G.area(d_)) for d_ in codos)
        for i, pc in enumerate(pieces):
            a_, b_ = pc.get("tramo") or (pc["xa"], pc["xb"])
            n = max(2, int(b_ - a_))
            for k in range(n + 1):
                emax = max(emax, egress_at(pieces, i, a_ + (b_ - a_) * k / n))
        # evacuación (R3.6): tramos del pasillo con un fondo de saco o un recorrido más largos que lo permitido
        pb["_evac"] = EV.analizar(pieces)
        ev = res.setdefault("evacuacion", {"saco": [], "recorrido": [], "fondo_saco_max": params["egress_single"],
                                           "recorrido_max": params["egress_multi"]})
        ev["saco"] += EV.tramos(pieces, pb["_evac"], params["egress_single"], "saco")
        ev["recorrido"] += EV.tramos(pieces, pb["_evac"], params["egress_multi"], "recorrido")
        pb["_neta"] = neta((pl_b, ph_b))
        bloques_pc.append((pieces, pb, pl_b, cpolys, del_bloque))
    res["metrics"]["wings"] = sum(len(b[0]) for b in bloques_pc)
    if res["dark_zones"]:
        dz_area = sum(abs(G.area(d_)) for d_ in res["dark_zones"])
        if dz_area - area_codos > 1.0:
            res["warnings"].append("Zona central sin luz natural (%.0f m² por planta): entre medianeras solo los frentes "
                                   "iluminan; hacen falta patios de aire y luz" % (dz_area - area_codos))
        if area_codos > 1.0:
            res["warnings"].append("Esquinas sin luz natural (%.0f m² por planta): donde se cruzan dos alas no llega la luz "
                                   "y no se ponen viviendas; quedan para núcleos, ductos o depósitos" % area_codos)
        res["metrics"]["dark_area"] = round(dz_area, 1)
    res["metrics"]["core_count"] = len(res["cores"])
    res["metrics"]["egress_max"] = round(emax, 1)
    if emax > params["egress_multi"]:
        res["warnings"].append("Hay puntos del pasillo a %.1f m de un núcleo (> %.0f m permitidos)" %
                               (emax, params["egress_multi"]))
    # ---- programas no residenciales (misma posición de núcleos en todos los niveles)
    layouts = {}
    for prog in sorted({s_["program"] for s_ in stories}):
        if prog in ("Office", "Retail", "Amenities"):
            P_ = S["oficinas"] if prog == "Office" else S["comercial"]
            acc = None
            for pieces, pb, pl_b, cpolys, _ in bloques_pc:
                fp_ = PR.free_plan(pieces, pb["_neta"], sum(abs(G.area(c)) for c in cpolys), pb["corridor_width"], P_)
                if fp_:
                    if acc is None:
                        acc = {"kind": "free", "workers": 0, "wc": 0, "free_area": 0.0, "bath_area": 0.0,
                               "hall_area": 0.0, "shapes": []}
                    for k in ("workers", "wc", "free_area", "bath_area", "hall_area"):
                        acc[k] += fp_[k]
                    acc["shapes"] += [{"kind": sh["kind"], "name": sh["name"], "poly": W(sh["pc"], sh["poly"])}
                                      for sh in fp_["shapes"]]
            if acc:
                layouts[prog] = acc
                d = res["metrics"]["programs"].get(prog)
                if d:
                    d["free_area"] = round(acc["free_area"] * d["stories"], 1)
                    d["workers"] = acc["workers"] * d["stories"]
        elif prog == "Parking":
            acc = {"kind": "parking", "count": 0, "stalls": [], "aisles": []}
            for pieces, pb, pl_b, cpolys, _ in bloques_pc:
                huecos = pb.get("_huecos") or []
                pk = PR.parking(pl_b, cpolys + huecos, S["estacionamiento"])      # sin plazas en los patios
                acc["count"] += pk["count"]
                acc["stalls"] += [G.pol_to_list(p_) for p_ in pk["stalls"]]
                acc["aisles"] += [G.pol_to_list(o) for p_ in pk["aisles"]
                                  for o, _ in (G.subtract(p_, huecos)[0] if huecos else [(p_, [])])]
            layouts[prog] = acc
            d = res["metrics"]["programs"].get(prog)
            if d:
                d["stalls"] = acc["count"] * d["stories"]
    res["program_layouts"] = layouts
    if stage == "corridor":
        pide = _ascensores_pedidos(res["cores"], S["nucleo"], len(stories), sube, por_nucleo=units_est)
        if pide is not None and pide != n_elev and params.get("_ascensores") is None and not fijo.isdigit():
            return otra_pasada(pide)
        return res
    res["warnings"] += avisos_u
    units = []
    for pieces, pb, pl_b, cpolys, del_bloque in bloques_pc:
        for u in del_bloque:                               # desde la puerta: hasta el núcleo y hasta tener dos salidas
            pc, xd = u["_pc"], u["door_local"][0]
            extra = pc.get("egress_extra", {}).get(u["side"], 0.0)
            u["egress"] = min(1e9, EV.recorrido(pb["_evac"], u["_i"], xd) + extra)
            u["saco"] = min(1e9, EV.saco(pb["_evac"], u["_i"], xd) + extra)
            u["_nucleo"] = _nucleo_de(pb["_evac"], pieces, u["_i"], xd)
        units += del_bloque
    pide = _ascensores_pedidos(res["cores"], S["nucleo"], len(stories), sube, units=units, n_res=n_res_lv)
    if pide is not None and pide != n_elev and params.get("_ascensores") is None and not fijo.isdigit():
        return otra_pasada(pide)              # R10.7: núcleos con los ascensores que piden las viviendas que sirven
    total = sum(c["ascensores"] for c in res["cores"])
    res["metrics"]["core"]["elevators_total"] = total
    if sube and len(stories) >= S["nucleo"]["pisos_dos_ascensores"] and res["cores"] and total < 2:
        res["warnings"].append("Desde %d niveles el edificio lleva al menos 2 ascensores y tiene %d: agrega %s en la "
                               "ficha de un núcleo" % (S["nucleo"]["pisos_dos_ascensores"], total, "uno" if total == 1 else "dos"))
    faltan = len(params.get("unit_edits") or []) - len(hechos)
    if faltan > 0:
        res["warnings"].append("%d cambio(s) de viviendas no se pudieron aplicar: la planta cambió desde que los hiciste. "
                               "Descártalos («Descartar cambios», en el mix) o deshazlos (Ctrl+Z)" % faltan)
    for i, u in enumerate(units):
        u["id"] = "U%02d" % (i + 1)
        if u["target"] and not u.get("editada") and abs(u["area"] - u["target"]) > 0.35 * u["target"]:
            res["warnings"].append("%s mide %.0f m² y el objetivo de «%s» es %.0f m²: la geometría no permite ajustarlo" %
                                   (u["id"], u["area"], u["type"], u["target"]))
    lejos = ["%s (%.0f m)" % (u["id"], u["egress"]) for u in units if u["egress"] > params["egress_multi"]]
    sacos = ["%s (%.0f m)" % (u["id"], u["saco"]) for u in units
             if u["egress"] <= params["egress_multi"] and u["saco"] > params["egress_single"]]
    if lejos:
        res["warnings"].append("Evacuación: %s a más de %.0f m de un núcleo (recorrido máximo): agrega un núcleo o acorta "
                               "el pasillo" % (", ".join(lejos[:10]), params["egress_multi"]))
    if sacos:
        res["warnings"].append("Fondo de saco: %s con una sola salida por más de %.0f m: agrega un núcleo o une el pasillo "
                               "para poder salir en dos direcciones" % (", ".join(sacos[:10]), params["egress_single"]))
    mm = metrics_mix(units, params)
    res["metrics"].update({"mix": mm})
    served = sum(u["area"] for u in units)
    res["metrics"]["efficiency"] = round(served / gfa_plate * 100, 1) if gfa_plate else 0
    res["units"] = []
    interiores = list(enumerate(params.get("room_edits") or []))     # R5.7: cambios dentro de las viviendas
    hechos_dentro = set()
    for u in units:
        pc = u["_pc"]
        eg, sc = u["egress"], u["saco"]
        status = "fail" if eg > params["egress_multi"] else ("saco" if sc > params["egress_single"] else "ok")
        item = {"id": u["id"], "type": u["type"], "area": round(u["area"], 1), "target": u["target"],
                "width": round(u["width"], 2), "depth": round(u["depth"], 2), "egress": round(eg, 1),
                "saco": round(sc, 1), "egress_status": status, "poly": W(pc, u["poly_local"]),
                "door": [round(v, 3) for v in G.to_world([u["door_local"]], pc["origin"], pc["angle"])[0]]}
        if u.get("editada"):
            item["editada"] = True
        if u.get("frente"):
            item["al_frente"] = True                        # R3.7: todo el ancho en la punta del pasillo, que entra por ahí
        if any(m.get("accesible") and m.get("name") == u["type"] for m in params["unit_mix"]):
            item["accesible"] = True                        # tipo del mix marcado «accesible» (F5)
        if stage == "plans":
            pl = unit_rooms(u, u["_pb"], pc, u["_plate"], [(k, e) for k, e in interiores if k not in hechos_dentro])
            hechos_dentro.update(pl["ediciones"])
            Wp = lambda pt, pc=pc: [round(v, 3) for v in G.to_world([pt], pc["origin"], pc["angle"])[0]]
            item["bedrooms"] = pl["bedrooms"]
            item["rooms"] = [{"id": r["id"], "name": r["name"], "kind": r["kind"], "area": round(r["area"], 1),
                              "poly": W(pc, r["poly_local"])} for r in pl["rooms"]]
            item["doors"] = [{"p": Wp(d["p"]), "q": Wp(d["q"]), "entry": bool(d.get("entry")),
                              "a": d["a"], "b": d["b"]} for d in pl["doors"]]
            item["graph"] = {"nodes": [{"id": n["id"], "name": n["name"], "kind": n["kind"], "pos": Wp(n["pos"])}
                                       for n in pl["graph"]["nodes"]], "edges": pl["graph"]["edges"]}
            item["equipamiento"] = [{"kind": q["kind"], "name": q["name"], "room": q["room"], "poly": W(pc, q["poly"]),
                                     "lines": [W(pc, ln) for ln in q["lines"]]} for q in pl["equipamiento"]]
            item["ventanas"] = [{"room": w["room"], "name": "Ventana", "ancho": w["ancho"], "alto": w["alto"],   # R5.5
                                 "area": w["area"], "minimo": w["minimo"], "poly": W(pc, w["poly"]),
                                 "lines": [W(pc, ln) for ln in w["lines"]], "seg": [Wp(a) for a in w["seg"]]}
                                for w in pl["ventanas"]]
            item["checks"] = pl["checks"]
            item["plan_score"] = pl["score"]
            item["sin_uso"] = [{"poly": W(pc, p), "area": round(abs(G.area(p)), 1)} for p in pl["sin_uso"]]   # v2.33
            item["paredes"] = []                            # tabiques interiores (se arrastran en la web, R5.7)
            for a, b in pl["paredes"]:
                a, b = Wp(a), Wp(b)
                L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
                item["paredes"].append({"seg": [a, b], "dir": [round(-(b[1] - a[1]) / L, 6), round((b[0] - a[0]) / L, 6)]})
            if pl["ediciones"]:
                item["editada_dentro"] = True
            item["facade"], item["facade_min"] = pl["facade"], pl["facade_min"]
        res["units"].append(item)
    faltan = len(interiores) - len(hechos_dentro) if stage == "plans" else 0
    if faltan > 0:
        res["warnings"].append("%d cambio(s) dentro de las viviendas no se pudieron aplicar: la planta cambió desde que los "
                               "hiciste. Descártalos (en la ficha de la vivienda) o deshazlos (Ctrl+Z)" % faltan)
    res["tabiques"] = []                                    # tabiques entre vecinas de una franja: se arrastran en la web (R4.4)
    for a, b in vecinas(units, params):
        pc, x = a["_pc"], a["x1"] + params["party_wall"] / 2
        ya, yb = [q[1] for q in a["poly_local"]], [q[1] for q in b["poly_local"]]
        lo, hi = max(min(ya), min(yb)), min(max(ya), max(yb))
        if hi - lo > 0.5:
            o, e = G.to_world([(0.0, 0.0), (1.0, 0.0)], pc["origin"], pc["angle"])
            res["tabiques"].append({"a": a["id"], "b": b["id"], "seg": W(pc, [(x, lo), (x, hi)]),
                                    "dir": [round(e[0] - o[0], 6), round(e[1] - o[1], 6)]})
    if stage == "plans" and res["units"]:
        res["metrics"]["plan_score"] = round(sum(u["plan_score"] for u in res["units"]) / len(res["units"]))
        bad = [u["id"] for u in res["units"] if u["plan_score"] < 100]
        if bad:
            res["warnings"].append("Planos con observaciones en: %s (clic en la unidad para ver el detalle)" % ", ".join(bad[:10]))
    _A = lambda ps: sum(abs(G.area(p)) for p in ps)
    used = _A(res["corridors"]) + _A([c["poly"] for c in res["cores"]]) + _A([u["poly"] for u in res["units"]])
    res["metrics"]["unused_area"] = round(max(0.0, gfa_plate - used - res["metrics"].get("dark_area", 0.0)), 1)
    res["metrics"]["circulation_pct"] = round((_A(res["corridors"]) + _A([c["poly"] for c in res["cores"]])) / gfa_plate * 100, 1) if gfa_plate else 0
    n_res = sum(1 for s_ in stories if s_["program"] == "Residential")
    if "Residential" in res["metrics"]["programs"]:
        res["metrics"]["programs"]["Residential"]["nsa"] = round(mm["nsa"] * n_res, 1)
    res["metrics"]["nsa_total"] = round(mm["nsa"] * n_res, 1)
    res["metrics"]["efficiency_total"] = round(res["metrics"]["nsa_total"] / res["metrics"]["gfa"] * 100, 1) \
        if res["metrics"]["gfa"] else 0
    res["metrics"]["units_total"] = mm["count"] * n_res
    served_ratio = served / gfa_plate if gfa_plate else 0
    if served_ratio < 0.55:
        res["warnings"].append("Solo el %.0f%% de la planta está servido por el pasillo. "
                               "Dibuja una línea central que cubra mejor la planta." % (served_ratio * 100))
    return res
