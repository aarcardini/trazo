"""Estándares dimensionales (mínimos normativos y medidas típicas). Editables desde la web.

Fuentes principales (ver STANDARDS.md):
- Ordenanzas de higiene de la vivienda (modelo departamental uruguayo; San José Res. 1244/1977, Río Negro Dec. 92/1979):
  habitación principal 10 m² / lado 2,50; otras 6,5 m² / 2,00; cocina 4 m² / 1,60; baño 2,40 m² / 1,20;
  baño auxiliar 1,50 m² / 0,80; pasillos 0,90; pasaje de entrada 1,20; escaleras colectivas 1,00-1,20; 2a+b=0,64.
- Ley 13.728 art. 18 y ANV (áreas vigentes según dormitorios).
- Bomberos IT 19 (salidas de emergencia): ancho mínimo 1,20; contrahuella 16-18 cm; tipos de escalera por altura.
- Intendencia de Montevideo: ductos y cabinas de ascensor (accesible: ducto 1,75 x 1,95; cabina 1,10 x 1,40).
- Decreto 406/988 art. 78: inodoros por trabajadores (1 cada 15 hasta 100).
- Estacionamiento: plaza 2,50 x 5,00 y calle de 6,00 (práctica habitual en Uruguay, indicado por el usuario).
Las medidas "típicas" son criterios de proyecto (no normativos) y pueden ajustarse.
"""
import copy
import math

DEFAULTS = {
    "vivienda": {
        # estancia: área mínima (m²), lado mínimo (m), área típica (m²), medidas típicas [frente, fondo]
        "dorm_principal": {"min_area": 10.0, "min_side": 2.50, "typ_area": 11.5, "typ": [3.20, 3.60]},
        "dorm_secundario": {"min_area": 6.5, "min_side": 2.00, "typ_area": 9.0, "typ": [2.80, 3.20]},
        "estar_comedor": {"min_area": 10.0, "min_side": 2.50, "typ_area": 20.0, "typ": [3.60, 5.50]},
        "cocina": {"min_area": 4.0, "min_side": 1.60, "typ_area": 7.0, "typ": [2.40, 2.90]},
        "bano": {"min_area": 2.4, "min_side": 1.20, "typ_area": 4.0, "typ": [1.70, 2.40]},
        "bano_aux": {"min_area": 1.5, "min_side": 0.80, "typ_area": 2.6, "typ": [1.20, 2.20]},
        "lavadero": {"min_area": 1.5, "min_side": 0.90, "typ_area": 2.5, "typ": [1.20, 2.10]},
        "pasillo": {"min_side": 0.90, "typ_side": 1.00},
        "hall": {"min_side": 1.20, "typ": [1.40, 1.80]},
        "estudio": {"min_area": 6.5, "min_side": 2.00, "typ_area": 8.0, "typ": [2.60, 3.10]},
        # estar-comedor típico según dormitorios (m²)
        "estar_por_dorms": [18.0, 18.0, 20.0, 24.0, 27.0],
        # rangos de superficie de la vivienda según dormitorios (ANV): [mín, máx]
        "rango_vivienda": [[25, 40], [35, 50], [50, 75], [65, 100], [80, 125]],
    },
    "nucleo": {
        "escalera_ancho": 1.20,          # ancho de cada tramo (IT 19)
        "contrahuella": 0.175,           # 16-18 cm
        "huella": 0.29,                  # 2a + b = 0,64
        "ojo": 0.10,                     # separación entre tramos
        "muro": 0.15,                    # muros de la caja
        "ascensor_ducto": [1.75, 1.95],  # accesible: ancho x fondo
        "ascensor_cabina": [1.10, 1.40],
        "palier": 1.50,                  # fondo libre frente a ascensores (giro 1,50)
        "ducto_instalaciones": 0.60,     # ancho del ducto de instalaciones
        "unidades_por_ascensor": 60,     # criterio de proyecto
        "altura_sin_ascensor": 9.0,      # acceso a más de 9 m requiere ascensor (MVOT)
        "pisos_dos_ascensores": 10,      # a partir de este nº de niveles, mínimo 2 ascensores
    },
    "oficinas": {
        "m2_por_persona": 10.0,          # puestos de trabajo (IT 19 usa 7 m²/persona para evacuación)
        "trabajadores_por_inodoro": 15,  # Dec. 406/988 art. 78 (hasta 100 trabajadores)
        "cubiculo": [0.95, 1.50],        # inodoro: ancho x fondo
        "zona_lavabos": 1.30,            # fondo de la zona de lavabos y paso
        "bano_accesible": [1.80, 2.00],
        "hall_extra": 1.50,              # largo del hall de acceso más allá de núcleo y baños
    },
    "comercial": {
        "m2_por_persona": 20.0,          # personal + uso de baños (criterio de proyecto)
        "trabajadores_por_inodoro": 15,
        "cubiculo": [0.95, 1.50],
        "zona_lavabos": 1.30,
        "bano_accesible": [1.80, 2.00],
        "hall_extra": 1.50,
    },
    "predio": {
        "retiro_ventanas": 3.0,          # retiro desde la medianera para poder abrir ventanas
        "patio_min": 3.0,                # ancho mínimo de un patio para que las estancias que dan a él tengan luz
    },
    "masterplan": {
        "calzada": 9.0,                  # ancho de calzada de calle local (criterio de proyecto)
        "vereda": 4.0,                   # ancho de cada vereda (calle de 17 m entre líneas de propiedad)
        "ochava": 3.0,                   # corte de esquina de manzana, medido sobre cada lado
        "manzana": [80.0, 120.0],        # damero: ancho x largo de manzana
        "lote_area_min": 300.0,          # Ley 10.723 art. 16 (texto Ley 19.044): mínimo 300 m² urbano/suburbano
        "lote_frente_min": 12.0,         # Ley 10.723 art. 16 original: 12 m de ancho medio (hoy, instrumentos departamentales)
        "fondo_min": 25.0,               # fondo mínimo para partir la manzana en dos filas de lotes
        "fondo_max": 50.0,               # fondo a partir del cual se sugiere una calle intermedia
        "reserva_min_pct": 10.0,         # Ley 18.308 art. 38: espacios libres + equipamiento >= 10 % (sin contar calles)
        "retiro_frontal": 4.0,
        "retiro_lateral": 0.0,           # 0 = construcción entre medianeras
        "retiro_fondo_pct": 20.0,        # % del fondo del lote
        "fos": 60.0,                     # factor de ocupación del suelo (%)
        "pisos": 3,
        "altura_piso": 3.0,
        "m2_por_vivienda": 75.0,         # para estimar viviendas a partir del área construida
    },
    "estacionamiento": {
        "plaza": [2.50, 5.00],           # ancho x largo
        "calle": 6.00,                   # calle de circulación
    },
}


def merged(over):
    """Combina los valores por defecto con los que vengan de la web (diccionarios anidados)."""
    out = copy.deepcopy(DEFAULTS)

    def rec(a, b):
        for k, v in (b or {}).items():
            if isinstance(v, dict) and isinstance(a.get(k), dict):
                rec(a[k], v)
            elif v is not None:
                a[k] = v
    rec(out, over or {})
    return out


def stair_box(S, floor_h):
    """Caja de escalera de dos tramos (ida y vuelta). Devuelve (ancho, largo, nº de contrahuellas)."""
    n = S["escalera_ancho"]
    risers = int(math.ceil(floor_h / S["contrahuella"] - 1e-9))
    per = int(math.ceil(risers / 2.0))
    run = (per - 1) * S["huella"]
    width = 2 * n + S["ojo"] + 2 * S["muro"]
    length = n + run + n + 2 * S["muro"]            # descanso + tramo + meseta de piso
    return width, length, risers


def elevators_needed(S, n_levels, top_access_h, units_served):
    if top_access_h <= S["altura_sin_ascensor"]:
        return 0
    n = max(1, int(math.ceil(units_served / float(S["unidades_por_ascensor"]))))
    if n_levels >= S["pisos_dos_ascensores"]:
        n = max(n, 2)
    return n


def core_size(S, floor_h, n_elev, corridor_w, giro=0):
    """Frente y fondo del núcleo (fondo incluye el pasillo) a partir de escalera y ascensores.
    giro 0: la escalera sube perpendicular al pasillo; giro 90: a lo largo del pasillo (núcleo más ancho y menos
    profundo, para alas de poco fondo)."""
    sw, sl, _ = stair_box(S, floor_h)
    ew, ed = S["ascensor_ducto"]
    asc = n_elev * (ew + S["muro"]) + (S["ducto_instalaciones"] + S["muro"] if n_elev else 0)
    fondo_asc = (S["palier"] + ed + S["muro"]) if n_elev else 0
    if giro == 90:
        width, depth = sl + asc, max(sw, fondo_asc)
    else:
        width, depth = sw + asc, max(sl, fondo_asc)
    return round(width, 2), round(depth + corridor_w, 2)


def wc_count(workers, per=15):
    """Inodoros para un grupo (Dec. 406/988 art. 78): 1/per hasta 100, 1/20 hasta 200, 1/30 después."""
    if workers <= 0:
        return 0
    if workers <= 100:
        return int(math.ceil(workers / float(per)))
    n = int(math.ceil(100 / float(per)))
    rest = workers - 100
    n += int(math.ceil(min(rest, 100) / 20.0))
    if rest > 100:
        n += int(math.ceil((rest - 100) / 30.0))
    return n
