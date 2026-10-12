"""Tabla de viviendas en CSV (ROADMAP R7.2), para abrirla en Excel o LibreOffice en español.

Una fila por vivienda y por nivel residencial (la planta tipo se repite en cada nivel) y, después de una línea en blanco,
los totales del edificio. Formato pensado para la planilla de Uruguay: UTF-8 con BOM (así Excel respeta las tildes),
separador «;», coma decimal y fines de línea CRLF. Solo biblioteca estándar.
"""
import csv
import io
import math

COLUMNAS = ("Nivel", "Vivienda", "Tipo", "Dormitorios", "Superficie (m²)", "Con muros (m²)", "Frente (m)", "Fondo (m)",
            "Pasillo", "Evacuación (m)", "Fondo de saco (m)", "Evacuación", "Calidad del plano", "Observaciones")
EVACUACION = {"ok": "cumple", "saco": "fondo de saco", "fail": "no cumple"}   # egress_status de cada vivienda
SIN_SALIDA = 1e8     # el motor da 1e9 m cuando el recorrido no llega a ningún núcleo: en la planilla, celda vacía


def _num(v, decimales):
    """Número con coma decimal (la planilla lo lee como número); vacío si falta o no es un valor real."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) >= SIN_SALIDA:
        return ""
    return ("%.*f" % (decimales, round(v, decimales) + 0.0)).replace(".", ",")


def _entero(v):
    return str(int(v)) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) else ""


def _texto(v):
    """Texto de una celda: en una sola línea y sin que la planilla lo tome por una fórmula (si empieza con = + - @ se
    le antepone un apóstrofo, como recomienda OWASP para los CSV: el tipo de unidad sale del mix, que puede venir de un
    proyecto ajeno)."""
    s = " ".join(str(v).split()) if v is not None else ""
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s


def niveles(res):
    """Índices de los niveles residenciales del resultado (los demás programas no llevan viviendas)."""
    stories = res.get("stories")
    if not stories:
        return [0]
    return [s.get("index", i) for i, s in enumerate(stories) if s.get("program") == "Residential"]


def fila(nivel, u):
    """La fila de una vivienda en un nivel, en el orden de COLUMNAS."""
    avisos = [str(c.get("msg") or "") for c in u.get("checks") or [] if not c.get("ok")]
    return [_entero(nivel), _texto(u.get("id")), _texto(u.get("type")), _entero(u.get("bedrooms")),
            _num(u.get("area"), 1), _num(u.get("area_muros"), 1), _num(u.get("width"), 2), _num(u.get("depth"), 2),
            _texto(u.get("pasillo")), _num(u.get("egress"), 1), _num(u.get("saco"), 1),
            EVACUACION.get(u.get("egress_status"), ""), _entero(u.get("plan_score")),
            _texto(" | ".join(a for a in avisos if a.strip()))]


def filas(res):
    """Todas las filas de la tabla: por nivel residencial, las viviendas de la planta tipo."""
    return [fila(n, u) for n in niveles(res) for u in res.get("units") or []]


def totales(res, cantidad):
    """Bloque de totales: pares (clave, valor). Las viviendas se cuentan de la tabla; la superficie vendible y la
    eficiencia son las del resumen de la web (metrics.nsa_total y metrics.efficiency_total)."""
    m = res.get("metrics") or {}
    return [("Viviendas totales", str(cantidad)),
            ("Niveles residenciales", str(len(niveles(res)))),
            ("Superficie vendible total, NSA (m²)", _num(m.get("nsa_total"), 1)),
            ("Eficiencia (%)", _num(m.get("efficiency_total"), 1))]


def result_to_csv(res):
    """El CSV de un resultado del motor, como texto que empieza con el BOM (codificarlo en UTF-8 tal cual)."""
    tabla = filas(res)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow(COLUMNAS)
    w.writerows(tabla)
    w.writerow([])
    w.writerows(totales(res, len(tabla)))
    return "﻿" + buf.getvalue()
