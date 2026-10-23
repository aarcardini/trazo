# HANDOFF.md — estado entre sesiones

Dice dónde estamos ahora. Cómo es el código está en `CLAUDE.md`; qué falta en general, en `ROADMAP.md`: no repetir ni uno ni otro.
- Se lee al inicio de cada sesión, después de `CLAUDE.md`.
- Se actualiza en el mismo commit que cierra cada tarea o abre cada PR, nunca después.
- Al integrar un PR, si el handoff que trae ya no describe el estado real (por ejemplo, otro PR apilado sigue abierto), corregirlo en un commit chico directo a main antes de seguir.
- Cada entrada lleva fecha. Lo cerrado se borra, no se tacha: el historial está en git.
- Máximo unas 80 líneas; si crece, está repitiendo a `CLAUDE.md` o al `ROADMAP.md`.

## 1. Estado del repositorio (23/10/2026)
- `main` = v2.70 (06ba592): #87 (`PADRON.md`, la investigación de R1.6) y #88 (R5.12 estancias editables, v2.70) integrados el 23/10, después de #86.
- Sin PRs abiertos. Las pruebas terminan en OK86.

## 2. Trabajo en curso (23/10/2026)
- **R1.6 Abrir padrón de Montevideo, programar** — rama `padron-montevideo` (worktree `scratchpad/padron/repo`, parte de 5f60329, hoy dentro de `main`), v2.71 / OK87; un agente Sonnet programa el diseño de `PADRON.md` §8 con dos supuestos (las tres preguntas de la sección 4 siguen sin respuesta; si la respuesta difiere, se ajusta en la misma rama): se muestran altura, FOS y uso preferente como orientativos, y las medianeras deducidas van como propuesta editable. Respuestas reales del WFS (23/10) guardadas en `tests/padron/` (421264, 432478, 1531, 32512, 65411, 9108 y 99999999: parcela, cat_suelo, puertas y vecinas). Al cerrar: PR con base `main`.
- **R11.4 Entre medianeras con más de dos viviendas por piso** — en diseño por el orquestador (estudia las plantas entre medianeras de la base: Isla de Flores y M5, «barras entradas por el costado desde un palier corto»); cuando arranque, rama `entre-medianeras-lateral`, v2.72 / OK88, agente Fable.
- **Base de tipologías:** el usuario busca más planos. Cuando mande un `.zip`: descomprimir en una carpeta nueva del scratchpad, pasar cada DXF por `python tools/ver_dxf.py`, organizar en `data/tipologias/` (DXF, nota por proyecto, filas en `indice.csv`; sin SVG ni PNG), regenerar con `python -m engine.tipologias` y `python tools/comparar_tipologias.py`, y abrir un PR como el #73.
- Decisiones de R5.13 que no se vuelven a discutir: primera etapa = la entrada en una de las tres posiciones que el plano ya arma (punta x0, junto a la zona de noche, punta x1 al revés); la posición cualquiera es la segunda etapa y queda en el ROADMAP.

## 3. Cola de tareas (23/10/2026), en el orden acordado (R1.6 y R11.4 ya están en curso, arriba); la rama siguiente toma v2.73 y OK89
1. **R5.8 Muros y tabiques con espesor** (L): tabiques interiores con espesor en los planos; antes de R7.1. Empezar por (a), que sola es M.
2. **Reparto del mix con el frente de la segunda fachada** (`units.generate_unit_mix`; quedó fuera de v2.67): solo vale cuando se prioricen crujías simples y predios entre medianeras con franjas profundas.

## 4. Decisiones pendientes del usuario (23/10/2026)
- R1.6 (el agente ya programa con los supuestos de la sección 2): (a) ¿mostrar altura, FOS y uso preferente aunque sean orientativos (la capa parece heredada y 1 de 7 retiros difiere del CITIM), o solo categoría y retiro frontal? (b) ¿escribir antes a la IM (uit@imm.gub.uy, sig@imm.gub.uy) para confirmar la capa y su vigencia? (c) ¿las medianeras deducidas van como propuesta editable o solo se señalan los lados con vecino?
- ¿La segunda etapa de R5.13 (la entrada en cualquier posición, corriendo la división día / noche) va antes de R5.8? Si sí, entra en la cola; si no, queda en el ROADMAP hasta que la pida.
- Cerradas y anotadas en el ROADMAP (no reabrir): 22/10: costos por gama cerrados; ingreso de oficinas, comercio y cocheras para más adelante; el tope del 25 % de monoambientes queda; sin ventanas hacia galerías ni corredores; GitHub Pages desestimado, se sigue en la red local; los avisos del motor siguen con punto decimal. 23/10: R1.6 se programa aceptando el servicio público de la IM sin garantía, con carga a mano o DXF como respaldo.

## 5. Convenciones de sesión (23/10/2026), las que no están en `CLAUDE.md`
- **Aceptación:** el usuario acepta con «aceptá» / «acepta» / «ya acepté», en general varios PRs juntos; se integran con `merge` (nunca squash ni rebase) en el orden de las versiones, con `expectedHeadSha`. Las ramas remotas ya integradas las borra el usuario en GitHub (desde la sesión da 403).
- **Ramas apiladas:** una tarea por rama y PR; una rama que depende de otra abierta parte de ella y su PR lleva esa rama como base; al integrar la de abajo se retargetea la de arriba a `main` y se integra después. Cada rama toma la versión y el número de prueba (`print("OKnn")`) siguientes **en el orden previsto de integración**; la que se integra después mezcla `main` (o la rama de abajo) y resuelve: `VERSION` la mayor, la cola de pruebas en orden, «Novedades» del README con la más nueva arriba, `CLAUDE.md` y `ROADMAP.md` con las dos partes, `tests/golden/` con `--actualizar` solo si lo único que cambia es `version_motor`.
- **Worktrees:** uno por tarea bajo `/tmp/claude-0/-home-user-trazo/<sesión>/scratchpad/<tarea>/repo` (`git worktree add -b <rama> ... origin/main`); se quitan al integrar. Nada se edita en `/home/user/trazo` fuera de `main`.
- **Commits y PRs:** autor «Alejandro Arcardini <alejandro.arcardini@hotmail.com>»; cada commit termina con `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` y `Claude-Session: https://claude.ai/code/session_01Rnt3KpTTaNS1XwmXUQ7R2p`; cada PR termina con «🤖 Generated with [Claude Code](https://claude.com/claude-code)», una línea en blanco y esa misma URL; un comentario en GitHub termina con `---` y `_Generated by [Claude Code](https://claude.ai/code)_`. Sin identificadores de modelo en commits, PRs ni código. El PR se escribe para un arquitecto: «Qué cambia», «Qué no incluye», «Cómo probarlo» (web y Rhino), «Pruebas» (las tres: `test_engine`, `test_rhino`, `regresion`) y la tabla antes / ahora cuando se mueven métricas.
- **Agentes:** como máximo dos en paralelo, cada uno en su worktree, sin commit (el orquestador revisa, corre las pruebas, comete y abre el PR). Sonnet para lo aislado (web, servidor, herramientas, docs, métricas); Fable para `plans.py`, `units.py`, `equipamiento.py` y todo lo que toque el modelo de piezas. Dos agentes no tocan los mismos archivos; si uno cambia `web/index.html` o `layout.py`, el otro evita esos archivos salvo `VERSION`.
- **Higiene:** servidores de prueba en un puerto libre (`TRAZO_PORT`), matados por PID, nunca `pkill -f`; archivos descargados o adjuntos en una carpeta nueva y vacía, leídos con `python -I`; capturas fuera del repo (`scratchpad/out/`).
- **Costos de uso:** si la cuenta llega al límite mensual, el agente se corta y se retoma con `SendMessage` cuando el límite se reinicia (el trabajo en el worktree queda).
