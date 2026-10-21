"""Patios y bloques: patios automáticos entre medianeras, la huella menos los patios (bloques, también anillos
alrededor de un patio interior) y la luz de los patios angostos. Parte del motor (ver engine/layout.py)."""
import math
from . import geometry as G
from .massing import _dist_to_boundary, _dominant_angle, _is_rectilinear, decompose_wings
from . import plans as P
from .circulation import is_between


# ---------------------------------------------------------------- patios y bloques
def auto_patios(fp, plate, params, ancho):
    """Patios automáticos: un predio entre medianeras demasiado profundo para que llegue la luz a todo se divide en
    bloques iguales separados por patios de `ancho` m (cada bloque con su núcleo y una vivienda hacia cada lado).
    R5.16b (v2.62): «demasiado profundo» lo mide el plano, no el mix: con una vivienda hacia cada frente del fondo que
    el plano aprovecha entero (plans.fondo_sin_tira, hasta max_unit_depth) y la franja del núcleo en el medio, queda
    más de 1 m sin luz (antes, con el fondo que daba la superficie media del mix, y el mix Inversor abría un patio en
    un predio de 10 × 28 m y dejaba cuatro viviendas de 3,4 m de fondo). Y solo si los bloques que quedan dan a sus
    viviendas el fondo de un plano (fondo_min + 0,5); si no, mejor sin patio, con la zona central sin luz avisada."""
    if not is_between(plate, params):
        return []
    th, (poly,) = decompose_wings(plate)
    x0, y0, x1, y1 = G.bbox([G.rotate(p, -th) for p in poly])
    ang = th if (x1 - x0) >= (y1 - y0) else th + math.pi / 2       # a lo largo de las medianeras
    u0, v0, u1, v1 = G.bbox(G.to_local(fp, (0.0, 0.0), ang))
    cw, muro = params["corridor_width"], params["outer_wall"]
    D = min(params["max_unit_depth"], P.fondo_sin_tira())         # el fondo que una vivienda aprovecha entero
    franja = max(cw, params["core_depth"] - cw)              # núcleo + hall en el medio de cada bloque
    lleno = 2 * (D + 1.5) + franja + 2 * muro                # fondo que se ilumina entero desde sus dos frentes
    L = u1 - u0
    if L <= 2 * (D + cw + 1.0) + franja + 2 * muro:          # sin patio quedaría a lo sumo 1 m sin luz
        return []
    n = max(2, int(math.ceil((L + ancho) / (lleno + ancho))))
    B = (L - (n - 1) * ancho) / n
    if (B - franja - 2 * muro) / 2.0 < P.fondo_min() + 0.5:      # viviendas sin fondo para un plano: sin patio
        return []
    out = []
    for k in range(1, n):
        a = u0 + k * B + (k - 1) * ancho
        out.append(G.to_world([(a, v0 - 1), (a + ancho, v0 - 1), (a + ancho, v1 + 1), (a, v1 + 1)], (0.0, 0.0), ang))
    return out


def _anillo(b, hs, muro):
    """Planta de un bloque (huella b con patios interiores hs): el muro exterior hacia afuera y hacia cada patio."""
    pl = G.inset(b, muro) if muro > 0 else b
    ph = [G.ensure_ccw(G.clean(G.inset(G.ensure_ccw(h), -muro) if muro > 0 else G.ensure_ccw(h))) for h in hs]
    return G.ensure_ccw(G.clean(pl)), ph


def split_blocks(fp, patios, params, warnings):
    """Huella menos patios -> (bloques, plantas, patios dentro de la huella). Cada bloque y cada planta es
    (exterior, [huecos]): un patio rodeado de edificio deja un hueco y el bloque es un anillo alrededor del patio."""
    muro = params["outer_wall"]
    usar = list(range(len(patios)))
    while True:
        partes, dentro = G.subtract(fp, [patios[i] for i in usar])
        fuera = [k for k, d in zip(usar, dentro) if not d]
        for k in fuera:
            warnings.append("Patio %d: queda fuera de la masa y no se usa" % (k + 1))
        malos = []
        for b, hs in partes:                 # un anillo tiene que poder dividirse en alas ortogonales
            if hs:
                pl, ph = _anillo(G.ensure_ccw(G.clean(b)), hs, muro)
                if decompose_wings(pl, holes=ph) is None:
                    th = _dominant_angle(pl)
                    orto = all(_is_rectilinear([G.rotate(p, -th) for p in l]) for l in [pl] + ph)
                    for k, d in zip(usar, dentro):       # los patios de este anillo: sus vértices están en un hueco
                        if d and any(_dist_to_boundary(q, h) < 1e-3 for pp in d for q in pp for h in hs):
                            malos.append(k)
                            warnings.append(("Patio %d: deja alas de menos de 5 m a su alrededor; no se usa" if orto else
                                             "Patio %d: está rodeado de edificio en una masa que no es ortogonal (o el "
                                             "patio está girado respecto de la masa); todavía no se puede usar") % (k + 1))
        if not fuera and not malos:
            break
        usar = [k for k in usar if k not in fuera and k not in malos]
    bloques, plantas = [], []
    for b, hs in partes:
        b = G.ensure_ccw(G.clean(b))
        pl, ph = _anillo(b, hs, muro)
        if len(pl) < 3 or G.area(pl) - sum(abs(G.area(h)) for h in ph) < 10.0:
            warnings.append("Un bloque de %.0f m² queda demasiado chico o angosto entre patios: no se usa" % abs(G.area(b)))
            continue
        bloques.append((b, [G.ensure_ccw(G.clean(h)) for h in hs]))
        plantas.append((pl, ph))
    return bloques, plantas, [pp for d in dentro for pp in d]


def make_patio_dark(partes, ancho_min, muro, warnings):
    """Función que dice si un punto de la planta da a un patio más angosto que ancho_min (sus caras no iluminan)."""
    angostos = []
    for p in partes:
        a = G.min_area_rect_angle(p)
        x0, y0, x1, y1 = G.bbox([G.rotate(q, -a) for q in p])
        w = min(x1 - x0, y1 - y0)
        if w + 1e-6 < ancho_min:
            angostos.append(p)
            warnings.append("Patio de %.1f m de ancho: menos de %.1f m, no ilumina (sus caras cuentan como medianera)"
                            % (w, ancho_min))
    if not angostos:
        return None
    return lambda pt: any(G.point_in_poly(pt, p) or _dist_to_boundary(pt, p) <= muro + 0.5 for p in angostos)


def _block_of(pt, bloques):
    for i, b in enumerate(bloques):
        if G.point_in_poly(pt, b):
            return i
    return min(range(len(bloques)), key=lambda i: _dist_to_boundary(pt, bloques[i]))


def _block_of_line(line, bloques):
    """Bloque donde está la mayor parte de una polilínea (por sus vértices y puntos medios)."""
    pts = list(line) + [((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0) for a, b in zip(line, line[1:])]
    votos = [_block_of(p, bloques) for p in pts]
    return max(set(votos), key=votos.count)
