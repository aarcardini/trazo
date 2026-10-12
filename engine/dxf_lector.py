"""Lector DXF (R1.5): el terreno de AutoCAD o Revit como masa de Trazo. Solo biblioteca estándar.

`leer(texto, nombre)` recibe un DXF de texto (pares código/valor) y devuelve lo mismo que manda el script de Rhino a
`/api/mass` (footprint, medianeras, centerlines, anchos_pasillo, cores, patios) más `unidades` y `warnings`. Todo sale en
metros y sin mover las coordenadas (pueden ser UTM). Sin masa, o con un DXF binario o un DWG, levanta `ErrorDxf` y su
mensaje dice qué hacer.

Capas (sin distinguir mayúsculas; «_», «-», «:» o espacio valen igual): `Trazo_Terreno` es la masa; `Trazo_Centerline`
lleva el ancho de pasillo en el nombre («ancho 1.4»); `Trazo_Cores`, los núcleos («ascensores 2» fija sus ascensores);
`Trazo_Medianeras`, el retiro («retiro 3»); `Trazo_Patios`, los patios. AutoCAD no admite «=» en el nombre de una capa:
«ancho 1.4», «ancho_1.4», «ancho-1.4» y «ancho=1.4» (también con coma) dicen lo mismo. Sin `Trazo_Terreno`, la masa es
la figura cerrada más grande del dibujo.

Se leen LINE, LWPOLYLINE, POLYLINE/VERTEX/SEQEND, ARC, CIRCLE (arcos y círculos, en tramos rectos de 5°), POINT, SPLINE
(aproximada) e INSERT (un nivel de bloques). Lo demás se ignora con un aviso que dice la entidad y la capa."""
import io
import math
import re

from . import geometry as G
from .massing import _dist_to_boundary

# $INSUNITS -> (nombre, metros por unidad)
UNIDADES = {1: ("pulgadas", 0.0254), 2: ("pies", 0.3048), 4: ("mm", 0.001), 5: ("cm", 0.01), 6: ("m", 1.0),
            10: ("yardas", 0.9144), 14: ("dm", 0.1)}
ROLES = ("terreno", "centerline", "cores", "medianeras", "patios")
_CAPA = re.compile(r"^trazo[ _:-]+(terreno|footprint|centerline|cores|medianeras|patios)(?![a-z0-9])(.*)$")
PASO_ARCO = math.radians(5.0)      # arcos y círculos: tramos rectos de 5° como máximo
NUCLEO_MAX = 120.0                 # m²: una figura cerrada de Trazo_Cores más grande que esto no es un núcleo
SECCIONES = ("HEADER", "TABLES", "BLOCKS", "ENTITIES")
MSG_NO_DXF = ("Trazo: el archivo no parece un DXF de texto. Elige un archivo .dxf guardado desde AutoCAD o Revit "
              "(un DWG no se puede leer: guárdalo antes como DXF).")
AYUDA_UNIDADES = ("fija las unidades de inserción del dibujo (la variable INSUNITS, que también está en el cuadro del "
                  "comando UNITS de AutoCAD) y guarda el DXF de nuevo.")
MSG_SIN_MASA = ("Trazo: no encontré una polilínea cerrada en el DXF. Dibuja el terreno como una polilínea cerrada "
                "(en AutoCAD: PEDIT y la opción Cerrar) en la capa «Trazo_Terreno» y vuelve a guardar el DXF.")


class ErrorDxf(ValueError):
    """Un DXF que no se puede usar. El mensaje dice qué hacer; `warnings`, lo que se alcanzó a avisar."""

    def __init__(self, mensaje, warnings=None):
        ValueError.__init__(self, mensaje)
        self.warnings = list(warnings or [])


class Forma(object):
    """Una figura del dibujo, en unidades del dibujo. tipo: «curva» (línea, polilínea, arco…) o «punto»."""
    __slots__ = ("tipo", "capa", "pts", "cerrada")

    def __init__(self, tipo, capa, pts, cerrada=False):
        self.tipo, self.capa, self.pts, self.cerrada = tipo, capa, pts, cerrada


# ------------------------------------------------------------------ lectura de pares y valores
def _num(v, defecto=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return defecto


def _v(pares, codigo, defecto=None):
    for c, v in pares:
        if c == codigo:
            return v
    return defecto


def _f(pares, codigo, defecto=0.0):
    return _num(_v(pares, codigo), defecto)


def _pares(texto):
    """Pares (código, valor) de un DXF de texto: en una línea el código y en la siguiente su valor."""
    lineas = iter(texto.split("\n"))
    for c, v in zip(lineas, lineas):
        c = c.strip()
        if c:
            try:
                yield int(c), v.strip()
            except ValueError:
                raise ErrorDxf(MSG_NO_DXF)


def _contar(cuentas, clave, tipo, capa):
    k = (clave, tipo, capa)
    cuentas[k] = cuentas.get(k, 0) + 1


# ------------------------------------------------------------------ curvas
def _arco_bulge(p, q, bulge):
    """Puntos intermedios del arco de p a q con ese bulge (tangente de un cuarto del ángulo; positivo = antihorario)."""
    cuerda = math.hypot(q[0] - p[0], q[1] - p[1])
    if cuerda < 1e-12:
        return []
    ang = 4.0 * math.atan(bulge)
    d = (cuerda / 2.0) / math.tan(ang / 2.0)                 # del medio de la cuerda al centro, hacia la izquierda
    ux, uy = (q[0] - p[0]) / cuerda, (q[1] - p[1]) / cuerda
    cx, cy = (p[0] + q[0]) / 2.0 - uy * d, (p[1] + q[1]) / 2.0 + ux * d
    r = math.hypot(p[0] - cx, p[1] - cy)
    a0 = math.atan2(p[1] - cy, p[0] - cx)
    n = max(1, int(math.ceil(abs(ang) / PASO_ARCO - 1e-9)))
    return [(cx + r * math.cos(a0 + ang * i / n), cy + r * math.sin(a0 + ang * i / n)) for i in range(1, n)]


def _con_arcos(verts, cerrada):
    """Vértices [x, y, bulge] -> puntos; el bulge de un vértice curva el tramo que sale de él."""
    n, out = len(verts), []
    for i, (x, y, b) in enumerate(verts):
        out.append((x, y))
        if b and (i < n - 1 or cerrada):
            out.extend(_arco_bulge((x, y), tuple(verts[(i + 1) % n][:2]), b))
    return out


def _de_boor(t, c, p, x):
    """Punto de la B-spline de grado p, con nudos t y puntos de control c, en el parámetro x."""
    n, k = len(c), p
    while k < n - 1 and x >= t[k + 1]:
        k += 1
    d = [list(c[j + k - p]) for j in range(p + 1)]
    for r in range(1, p + 1):
        for j in range(p, r - 1, -1):
            den = t[j + 1 + k - r] - t[j + k - p]
            a = (x - t[j + k - p]) / den if den else 0.0
            d[j] = [(1.0 - a) * d[j - 1][i] + a * d[j][i] for i in (0, 1)]
    return tuple(d[p])


def _spline(pares):
    """Puntos de una SPLINE: los de ajuste si los trae; si no, la curva de sus puntos de control (nudos y grado)."""
    ajuste, ctrl, nudos, grado = [], [], [], int(_f(pares, 71, 3))
    for c, v in pares:
        if c == 11:
            ajuste.append([_num(v), 0.0])
        elif c == 21 and ajuste:
            ajuste[-1][1] = _num(v)
        elif c == 10:
            ctrl.append([_num(v), 0.0])
        elif c == 20 and ctrl:
            ctrl[-1][1] = _num(v)
        elif c == 40:
            nudos.append(_num(v))
    if len(ajuste) >= 2:
        return [tuple(p) for p in ajuste]
    if len(ctrl) >= 2 and grado >= 1 and len(nudos) == len(ctrl) + grado + 1 and nudos[-1] > nudos[0]:
        m = max(16, min(400, 8 * len(ctrl)))
        t0, t1 = nudos[grado], nudos[len(ctrl)]
        return [_de_boor(nudos, ctrl, grado, t0 + (t1 - t0) * i / m) for i in range(m + 1)]
    return [tuple(p) for p in ctrl]


def _normalizar(pts, cerrada, tol):
    """Sin puntos repetidos; un contorno que vuelve a su primer punto es cerrado."""
    out = []
    for p in pts:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol * 0.01:
            out.append(p)
    if len(out) > 3 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= tol:
        out.pop()
        cerrada = True
    return out, cerrada


# ------------------------------------------------------------------ el dibujo
class _Dibujo(object):
    """Lo que el DXF dibuja: las figuras del espacio modelo (en unidades del dibujo) y lo que no se pudo leer."""

    def __init__(self):
        self.insunits = None
        self.tol = 0.01               # unidades del dibujo: dos puntas a menos que esto se tocan
        self.apagadas = set()         # capas apagadas o congeladas
        self.bloques = {}             # NOMBRE -> {nombre, base, formas, cuentas, saltar}
        self.modelo = []
        self.cuentas = {}             # (clave, tipo, capa) -> cantidad: lo que se avisa al final
        self.seccion = None
        self.secciones = 0
        self.bloque = None
        self._poli = None             # (cabecera, destino, vértices, cuentas) de la POLYLINE que se está leyendo

    def leer(self, texto):
        rec = None
        for c, v in _pares(texto):
            if c == 0:
                if rec is not None:
                    self._registro(rec)
                rec = [v, []]
                if v == "ENDSEC":
                    self._cerrar_poli()
                    self.seccion, self.bloque = None, None
            elif rec is not None:
                if rec[0] == "SECTION":                   # el encabezado trae todas sus variables en este registro
                    if c == 2 and not rec[1]:
                        self.seccion = v
                        self.secciones += 1
                    rec[1].append((c, v))
                elif self.seccion in SECCIONES:
                    rec[1].append((c, v))
        if rec is not None:
            self._registro(rec)
        self._cerrar_poli()
        if not self.secciones:
            raise ErrorDxf(MSG_NO_DXF)

    def _registro(self, rec):
        tipo, pares = rec
        if tipo == "SECTION":
            if _v(pares, 2) == "HEADER":
                for i, (c, v) in enumerate(pares):
                    if c == 9 and v == "$INSUNITS" and i + 1 < len(pares):
                        self.insunits = int(_num(pares[i + 1][1], 0))
                        if self.insunits in UNIDADES:
                            self.tol = 0.01 / UNIDADES[self.insunits][1]
        elif self.seccion == "TABLES":
            if tipo == "LAYER" and _v(pares, 2) is not None and (int(_f(pares, 70)) & 1 or _f(pares, 62, 7) < 0):
                self.apagadas.add(_v(pares, 2).lower())
        elif self.seccion == "BLOCKS":
            if tipo == "BLOCK":
                nombre = _v(pares, 2, "")
                self.bloque = {"nombre": nombre, "base": (_f(pares, 10), _f(pares, 20)), "formas": [], "cuentas": {},
                               "saltar": nombre.lower().startswith(("*model_space", "*paper_space"))}
            elif tipo == "ENDBLK":
                self._cerrar_poli()
                if self.bloque is not None:
                    self.bloques[self.bloque["nombre"].upper()] = self.bloque
                self.bloque = None
            elif self.bloque is not None and not self.bloque["saltar"]:
                self._entidad(tipo, pares, self.bloque["formas"], self.bloque["cuentas"])
        elif self.seccion == "ENTITIES":
            self._entidad(tipo, pares, self.modelo, self.cuentas)

    def _entidad(self, tipo, pares, destino, cuentas):
        if tipo == "VERTEX":
            if self._poli is not None:
                self._poli[2].append(pares)
            return
        self._cerrar_poli()                      # cualquier otra entidad termina la POLYLINE abierta, falte o no su SEQEND
        if tipo in ("SEQEND", "ATTRIB"):
            return
        if tipo == "POLYLINE":
            self._poli = (pares, destino, [], cuentas)
            return
        capa = _v(pares, 8, "0")
        if (self.seccion == "ENTITIES" and _v(pares, 67) == "1") or _v(pares, 60) == "1":
            return                               # espacio papel (hojas, marcos, ventanas) o entidad invisible
        if capa.lower() in self.apagadas:
            _contar(cuentas, "oculta", tipo, capa)
        elif tipo == "INSERT":
            self._insert(pares, capa, destino, cuentas)
        else:
            hechas = self._formas(tipo, pares, capa, cuentas)
            if hechas is None:
                _contar(cuentas, "ignorada", tipo, capa)
            else:
                destino.extend(hechas)

    def _formas(self, tipo, pares, capa, cuentas):
        """Las figuras de una entidad, o None si Trazo no la lee."""
        if tipo == "POINT":
            return [Forma("punto", capa, [(_f(pares, 10), _f(pares, 20))])]
        cerrada, ocs = False, True               # ocs: coordenadas del sistema propio de la entidad (extrusión)
        if tipo == "LINE":
            pts, ocs = [(_f(pares, 10), _f(pares, 20)), (_f(pares, 11), _f(pares, 21))], False
        elif tipo == "LWPOLYLINE":
            verts = []
            for c, v in pares:
                if c == 10:
                    verts.append([_num(v), 0.0, 0.0])
                elif verts and c == 20:
                    verts[-1][1] = _num(v)
                elif verts and c == 42:
                    verts[-1][2] = _num(v)
            cerrada = bool(int(_f(pares, 70)) & 1)
            pts = _con_arcos(verts, cerrada)
        elif tipo in ("CIRCLE", "ARC"):
            cx, cy, r = _f(pares, 10), _f(pares, 20), _f(pares, 40)
            if r <= 0:
                return []
            a0 = math.radians(_f(pares, 50)) if tipo == "ARC" else 0.0
            barrido = ((math.radians(_f(pares, 51)) - a0) % (2 * math.pi) or 2 * math.pi) if tipo == "ARC" else 2 * math.pi
            n = max(1, int(math.ceil(barrido / PASO_ARCO - 1e-9)))
            pts = [(cx + r * math.cos(a0 + barrido * i / n), cy + r * math.sin(a0 + barrido * i / n))
                   for i in range(n + (1 if tipo == "ARC" else 0))]
            cerrada = tipo == "CIRCLE"
        elif tipo == "SPLINE":
            pts, ocs, cerrada = _spline(pares), False, bool(int(_f(pares, 70)) & 1)
            _contar(cuentas, "aprox", tipo, capa)
        else:
            return None
        if ocs and _f(pares, 230, 1.0) < 0:      # extrusión (0, 0, -1): el eje x del sistema propio mira al revés
            pts = [(-x, y) for x, y in pts]
        pts, cerrada = _normalizar(pts, cerrada, self.tol)
        return [Forma("curva", capa, pts, cerrada)] if len(pts) >= (3 if cerrada else 2) else []

    def _cerrar_poli(self):
        if self._poli is None:
            return
        cab, destino, vertices, cuentas = self._poli
        self._poli = None
        capa = _v(cab, 8, "0")
        if (self.seccion == "ENTITIES" and _v(cab, 67) == "1") or _v(cab, 60) == "1":
            return
        if capa.lower() in self.apagadas:
            _contar(cuentas, "oculta", "POLYLINE", capa)
            return
        flags = int(_f(cab, 70))
        if flags & (16 | 64):                    # malla 3D o malla de caras: no es un contorno
            _contar(cuentas, "ignorada", "POLYLINE (malla)", capa)
            return
        verts = [[_f(p, 10), _f(p, 20), _f(p, 42)] for p in vertices if not int(_f(p, 70)) & 16]
        pts = _con_arcos(verts, bool(flags & 1))
        if not flags & 8 and _f(cab, 230, 1.0) < 0:
            pts = [(-x, y) for x, y in pts]
        pts, cerrada = _normalizar(pts, bool(flags & 1), self.tol)
        if len(pts) >= (3 if cerrada else 2):
            destino.append(Forma("curva", capa, pts, cerrada))

    def _insert(self, pares, capa, destino, cuentas):
        """Un bloque en el dibujo: sus figuras con el punto de inserción, la escala y el giro (un solo nivel)."""
        nombre = _v(pares, 2, "")
        if self.seccion == "BLOCKS":
            _contar(cuentas, "anidado", "INSERT", capa)
            return
        bl = self.bloques.get(nombre.upper())
        if bl is None:
            _contar(cuentas, "vacio", nombre, "")
            return
        for (clave, tipo, c), n in bl["cuentas"].items():     # lo que el bloque no pudo leer se avisa cuando se usa
            cuentas.setdefault((clave, tipo, capa if c == "0" else c), n)
        if not bl["formas"]:
            if not bl["cuentas"]:
                _contar(cuentas, "vacio", nombre, "")
            return
        if int(_f(pares, 70, 1)) > 1 or int(_f(pares, 71, 1)) > 1:
            _contar(cuentas, "minsert", "INSERT", capa)
        sx, sy, giro = _f(pares, 41, 1.0), _f(pares, 42, 1.0), math.radians(_f(pares, 50))
        ix, iy, (bx, by) = _f(pares, 10), _f(pares, 20), bl["base"]
        co, si, espejo = math.cos(giro), math.sin(giro), _f(pares, 230, 1.0) < 0

        def mover(p):
            u, w = sx * (p[0] - bx), sy * (p[1] - by)
            x, y = ix + u * co - w * si, iy + u * si + w * co
            return (-x if espejo else x, y)
        hijos = [Forma(f.tipo, capa if f.capa == "0" else f.capa, [mover(p) for p in f.pts], f.cerrada)
                 for f in bl["formas"]]
        if _rol(capa)[0] == "cores":             # un núcleo: el centro del bloque (o su punto de inserción)
            pts = [p for f in hijos for p in f.pts]
            c = (((min(p[0] for p in pts) + max(p[0] for p in pts)) / 2.0,
                  (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2.0) if pts else mover((bx, by)))
            destino.append(Forma("punto", capa, [c]))
        else:
            destino.extend(hijos)


# ------------------------------------------------------------------ capas y contornos
def _rol(capa):
    """(rol, resto del nombre) de una capa de Trazo, o (None, "")."""
    m = _CAPA.match(capa.strip().lower())
    if not m:
        return None, ""
    return ("terreno" if m.group(1) == "footprint" else m.group(1)), m.group(2)


def _numero(resto, clave):
    """El número que sigue a «clave» en el nombre de la capa («ancho 1.4», «ancho_1,4», «ancho=1.4»), o None."""
    m = re.search(clave + r"[ _=:-]*(\d+(?:[.,]\d+)?)", resto)
    return float(m.group(1).replace(",", ".")) if m else None


def _lazos(abiertas, tol):
    """Contornos cerrados que forman las figuras abiertas al tocarse punta con punta (sin ramas ni puntas sueltas):
    [(puntos, cantidad de figuras, capa)]."""
    celdas = {}
    clave = lambda p: (int(math.floor(p[0] / tol)), int(math.floor(p[1] / tol)))
    punta = lambda i, fin: abiertas[i].pts[0 if fin == 0 else -1]
    for i in range(len(abiertas)):
        for fin in (0, 1):
            celdas.setdefault(clave(punta(i, fin)), []).append((i, fin))

    def cerca(i, fin):
        p = punta(i, fin)
        cx, cy = clave(p)
        return [(j, fj) for dx in (-1, 0, 1) for dy in (-1, 0, 1) for j, fj in celdas.get((cx + dx, cy + dy), ())
                if (j, fj) != (i, fin) and math.hypot(punta(j, fj)[0] - p[0], punta(j, fj)[1] - p[1]) <= tol]
    usadas, lazos = set(), []
    for i0 in range(len(abiertas)):
        if i0 in usadas:
            continue
        cadena, vistos, (i, fin), ok = [(i0, 0)], {i0}, (i0, 1), False
        while True:
            vec = cerca(i, fin)
            if len(vec) != 1:
                break
            j, fj = vec[0]
            if j in vistos:
                ok = (j, fj) == (i0, 0)
                break
            vistos.add(j)
            cadena.append((j, fj))
            i, fin = j, 1 - fj
        usadas |= vistos
        if ok and len(cadena) >= 2:
            pts = []
            for j, fj in cadena:
                p = abiertas[j].pts if fj == 0 else abiertas[j].pts[::-1]
                pts.extend(p if not pts else p[1:])
            lazos.append((pts[:-1] if math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) <= tol else pts,
                          len(cadena), abiertas[i0].capa))
    return lazos


def _contornos(formas, tol, siempre=True):
    """Contornos cerrados de unas figuras: las cerradas y los lazos de las abiertas (con siempre=False, solo si
    ninguna está cerrada: en un dibujo grande no se buscan lazos de más). Sin repetir los idénticos (la misma polilínea
    dibujada dos veces). [(puntos, figuras, capa)]"""
    out = [(f.pts, 1, f.capa) for f in formas if f.cerrada and len(f.pts) >= 3 and abs(G.area(f.pts)) > 1e-12]
    if siempre or not out:
        out += [l for l in _lazos([f for f in formas if not f.cerrada and f.tipo == "curva"], tol)
                if len(l[0]) >= 3 and abs(G.area(l[0])) > 1e-12]
    vistos, distintos = set(), []
    for c in out:
        clave = (round(abs(G.area(c[0])), 4),) + tuple(round(v, 4) for v in G.bbox(c[0]))
        if clave not in vistos:
            vistos.add(clave)
            distintos.append(c)
    return distintos


def _plural(n, uno, varios):
    return "%d %s" % (n, uno if n == 1 else varios)


def _capas_txt(capas):
    nom = ["«%s»" % c for c in capas[:3]]
    txt = ", ".join(nom[:-1]) + " y " + nom[-1] if len(nom) > 1 else nom[0]
    return txt + (" y %d más" % (len(capas) - 3) if len(capas) > 3 else "")


def _avisos_cuentas(cuentas):
    """Los avisos de lo que no se leyó o se leyó aproximado: uno por tipo de entidad, con sus capas."""
    por, vacios = {}, set()
    for (clave, tipo, capa), n in cuentas.items():
        if clave == "vacio":
            vacios.add(tipo)
        else:
            d = por.setdefault((clave, tipo if clave in ("ignorada", "aprox") else ""), {})
            d[capa] = d.get(capa, 0) + n
    out = []
    for (clave, tipo), capas in sorted(por.items(), key=lambda kv: (kv[0][0] != "ignorada", -sum(kv[1].values()))):
        n, nombres = sum(capas.values()), sorted(capas, key=lambda c: -capas[c])
        de = ("de la capa %s" if len(nombres) == 1 else "de las capas %s") % _capas_txt(nombres)
        if clave == "ignorada":
            out.append("Ignoré %s %s %s: Trazo no %s lee." % (_plural(n, "entidad", "entidades"), tipo, de,
                                                              "la" if n == 1 else "las"))
        elif clave == "aprox":
            out.append(("%s %s se leyó con tramos rectos (curva aproximada)." if n == 1 else
                        "%s %s se leyeron con tramos rectos (curvas aproximadas).") % (_plural(n, "SPLINE", "SPLINEs"), de))
        elif clave == "oculta":
            out.append("No leí %s %s (%s)." % (_plural(n, "entidad", "entidades"), de,
                                              "capa apagada o congelada" if len(nombres) == 1 else
                                              "capas apagadas o congeladas"))
        elif clave == "anidado":
            out.append("Hay bloques dentro de bloques %s y no los leí. Si el terreno está en uno, explota los bloques "
                       "(EXPLODE) y guarda el DXF de nuevo." % de)
        elif clave == "minsert":
            out.append("Un arreglo de bloques (MINSERT) %s se leyó como una sola copia." % de)
    if vacios:
        out.append("Sin figuras que leer en %s (¿referencia externa, XREF?). Si el terreno está ahí, enlázalo o "
                   "explótalo y guarda el DXF de nuevo." %
                   (("el bloque %s" if len(vacios) == 1 else "los bloques %s") % _capas_txt(sorted(vacios))))
    return out


# ------------------------------------------------------------------ la masa y las capas de Trazo
def _formato(texto):
    """Rechaza lo que no es un DXF de texto, diciendo qué hacer."""
    if not isinstance(texto, str):
        raise ErrorDxf(MSG_NO_DXF)
    cabeza = texto[:64].lstrip("\ufeff \t\r\n")
    if cabeza.startswith("AutoCAD Binary DXF"):
        raise ErrorDxf("Trazo: este DXF es binario y Trazo lee solo DXF de texto (ASCII). En AutoCAD, guárdalo con "
                       "«Guardar como» → «DXF de AutoCAD» y, en Herramientas → Opciones → Opciones DXF, elige el formato "
                       "ASCII; el DXF que exporta Revit ya es de texto.")
    if re.match(r"AC10\d\d", cabeza):
        raise ErrorDxf("Trazo: eso es un DWG, el formato binario de AutoCAD, y Trazo no lo lee. Guarda una copia como DXF "
                       "(«Guardar como» → «DXF de AutoCAD») o exporta el DXF desde Revit.")


def leer(texto, nombre=""):
    """Un DXF de texto -> lo que manda Rhino a /api/mass (sin altura) más `unidades` y `warnings`; todo en metros.
    Levanta ErrorDxf si no es un DXF de texto o no tiene una figura cerrada para la masa."""
    _formato(texto)
    d = _Dibujo()
    d.leer(texto.lstrip("\ufeff"))
    por_rol, libres = dict((r, []) for r in ROLES), []
    for f in d.modelo:
        rol, resto = _rol(f.capa)
        if rol:
            por_rol[rol].append((f, resto))
        else:
            libres.append(f)
    del_dibujo = _avisos_cuentas(d.cuentas)
    # --- la masa: la capa Trazo_Terreno; si no hay, la figura cerrada más grande del dibujo (o un lazo de líneas)
    terreno = [f for f, _ in por_rol["terreno"]]
    candidatas = _contornos(terreno if terreno else libres, d.tol, siempre=bool(terreno))
    if not candidatas:
        raise ErrorDxf(("Trazo: la capa «%s» no tiene ninguna polilínea cerrada. Ciérrala (en AutoCAD: PEDIT y la opción "
                        "Cerrar) y guarda el DXF de nuevo." % terreno[0].capa) if terreno else MSG_SIN_MASA, del_dibujo)
    pts, n_figuras, capa_masa = max(candidatas, key=lambda c: abs(G.area(c[0])))
    # --- unidades: $INSUNITS, o por el tamaño de la masa (hasta 500: m; hasta 10000: cm; más: mm)
    avisos = []
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    grande = max(max(xs) - min(xs), max(ys) - min(ys))
    if d.insunits in UNIDADES:
        unidad, k = UNIDADES[d.insunits]
    else:
        unidad, k = ("m", 1.0) if grande <= 500 else ("cm", 0.01) if grande <= 10000 else ("mm", 0.001)
    cv = lambda p: [round(p[0] * k, 6) + 0.0, round(p[1] * k, 6) + 0.0]
    footprint = [cv(p) for p in G.ensure_ccw(pts)]
    largo, ancho = (max(xs) - min(xs)) * k, (max(ys) - min(ys)) * k
    medidas = "%.1f × %.1f m" % (largo, ancho)
    if d.insunits not in UNIDADES:
        avisos.append("El DXF no dice en qué unidades está dibujado (o no las reconozco): por el tamaño del dibujo lo "
                      "tomé como %s (la masa mide %s). Si no es así, %s" %
                      ({"m": "metros", "cm": "centímetros", "mm": "milímetros"}[unidad], medidas, AYUDA_UNIDADES))
    if terreno:
        if len(candidatas) > 1:
            avisos.append("La capa «%s» tiene %d figuras cerradas: tomé la más grande (%s)." %
                          (capa_masa, len(candidatas), medidas))
    elif len(candidatas) > 1:
        avisos.append("No hay una capa Trazo_Terreno: tomé la figura cerrada más grande del dibujo (%s, capa «%s»; había "
                      "%d). Para elegir otra, ponla en la capa Trazo_Terreno." % (medidas, capa_masa, len(candidatas)))
    if n_figuras > 1:
        avisos.append("Armé el contorno de la masa (%s, capa «%s») con %d líneas que se tocan punta con punta." %
                      (medidas, capa_masa, n_figuras))
    if max(largo, ancho) < 3 or max(largo, ancho) > 1000:
        avisos.append("La masa mide %s, %s para un edificio. El DXF está en %s: si dibujaste pensando en otra unidad, %s" %
                      (medidas, "muy pequeña" if max(largo, ancho) < 3 else "enorme", unidad, AYUDA_UNIDADES))
    res = {"name": re.sub(r"\.dxf$", "", (nombre or "").strip(), flags=re.I) or "Terreno del DXF", "footprint": footprint}
    # --- pasillos: polilíneas de Trazo_Centerline, con el ancho en el nombre de la capa
    lineas, anchos = [], []
    for f, resto in por_rol["centerline"]:
        if f.tipo != "curva":
            continue
        q = [cv(p) for p in f.pts] + ([cv(f.pts[0])] if f.cerrada else [])
        lineas.append(q)
        a = _numero(resto, "ancho")
        if a:
            anchos += [{"seg": [list(p), list(r)], "ancho": a} for p, r in zip(q, q[1:])
                       if math.hypot(r[0] - p[0], r[1] - p[1]) > 0.05]
    # --- medianeras: cada tramo de las líneas de Trazo_Medianeras, con el retiro en el nombre de la capa
    meds = []
    for f, resto in por_rol["medianeras"]:
        if f.tipo == "curva":
            q = [cv(p) for p in f.pts]
            meds += [{"a": a, "b": b, "retiro": _numero(resto, "retiro") or 0.0}
                     for a, b in zip(q, q[1:] + (q[:1] if f.cerrada else [])) if a != b]
    lejos = sum(1 for m in meds
                if _dist_to_boundary(((m["a"][0] + m["b"][0]) / 2.0, (m["a"][1] + m["b"][1]) / 2.0), footprint) > 0.5)
    if lejos:
        avisos.append("%s a más de 0,5 m del borde de la masa: dibuja las medianeras sobre el borde (Trazo las usa igual)." %
                      ("Una medianera queda" if lejos == 1 else "%d medianeras quedan" % lejos))
    # --- núcleos: puntos, bloques o figuras cerradas chicas de Trazo_Cores
    cores, malos = [], 0
    for f, resto in por_rol["cores"]:
        if f.tipo == "punto":
            c = f.pts[0]
        elif f.cerrada and abs(G.area(f.pts)) * k * k <= NUCLEO_MAX:
            c = G.centroid(f.pts)
        else:
            malos += 1
            continue
        asc, p = _numero(resto, "ascensores"), cv(c)
        cores.append({"p": p, "ascensores": int(asc)} if asc is not None else p)
    if malos:
        avisos.append("%s de la capa Trazo_Cores no sirve%s como núcleo (una línea abierta o una figura cerrada de más de "
                      "%d m²): marca cada núcleo con un punto, un bloque o una figura cerrada chica." %
                      (_plural(malos, "figura", "figuras"), "" if malos == 1 else "n", NUCLEO_MAX))
    # --- patios: figuras cerradas de Trazo_Patios
    formas_p = [f for f, _ in por_rol["patios"]]
    contornos = _contornos(formas_p, d.tol)
    patios = [[cv(p) for p in G.ensure_ccw(c[0])] for c in contornos]
    sueltas = sum(1 for f in formas_p if not f.cerrada and f.tipo == "curva") - sum(c[1] for c in contornos if c[1] > 1)
    if sueltas > 0:
        avisos.append("%s de la capa Trazo_Patios no está%s cerrada%s y no se usa%s: ciérra%s (en AutoCAD: PEDIT y la "
                      "opción Cerrar)." % (_plural(sueltas, "figura", "figuras"), "" if sueltas == 1 else "n",
                                           "" if sueltas == 1 else "s", "" if sueltas == 1 else "n",
                                           "la" if sueltas == 1 else "las"))
    for clave, valor in (("centerlines", lineas), ("anchos_pasillo", anchos), ("medianeras", meds), ("patios", patios),
                         ("cores", cores)):
        if valor:
            res[clave] = valor
    res["unidades"] = unidad
    res["warnings"] = avisos + del_dibujo
    return res
