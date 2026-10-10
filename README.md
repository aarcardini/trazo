# Trazo

**Trazo** (antes «Finch Local») es una herramienta local de estudio de planta tipo, inspirada en el flujo público de herramientas como Finch3D (masa → planta → pasillo y núcleos → mix de unidades → planos de unidad). Es una implementación propia: no contiene código, datos ni marcas de terceros.

## Requisitos
- Python 3.9 o superior (sin librerías externas). Se instala una sola vez: ver «Instalación».
- Rhino 8 en Mac o Windows (para el puente). La web funciona sola, sin Rhino, con los ejemplos.
- Para desarrollar con Claude Code: ver `CLAUDE.md` y `ROADMAP.md`.

## Instalación

### 1. Instalar Python (una sola vez)

**Windows**
1. Entra en https://www.python.org/downloads/ y descarga Python para Windows (botón amarillo «Download Python…»).
2. Abre el archivo descargado:
   - Si es el instalador clásico (`python-3.x.x-amd64.exe`): en la primera pantalla marca **«Add python.exe to PATH»** y pulsa **Install Now**.
   - Si es el **Python install manager**: instálalo; la primera vez que escribas `py` puede preguntarte si quieres instalar Python: responde que sí (`Y`).
3. Comprueba la instalación: abre el menú Inicio, escribe `cmd` y abre **Símbolo del sistema**. Escribe `py --version` y pulsa Enter. Debe responder `Python 3.` y la versión (3.9 o más).
   - Si `py` no funciona pero `python --version` sí, usa `python` donde esta guía dice `py`.

**Mac**
1. Entra en https://www.python.org/downloads/ y descarga Python para macOS (botón amarillo «Download Python…»).
2. Abre el archivo `.pkg` y sigue los pasos (Continuar → Aceptar → Instalar).
3. Comprueba la instalación: abre **Terminal** (Cmd+Espacio, escribe «Terminal» y pulsa Enter), escribe `python3 --version` y pulsa Enter. Debe responder `Python 3.` y la versión.
   - En Mac el comando es `python3` (no `python`).

### 2. Descargar Trazo
El código está en GitHub: https://github.com/aarcardini/trazo (repositorio privado: entra con tu cuenta).

**Opción A — GitHub Desktop (recomendada: actualizar es un clic).** Igual en Mac y Windows.
1. Descarga GitHub Desktop de https://desktop.github.com, instálalo y entra con tu cuenta de GitHub.
2. Menú **File → Clone repository…**, pestaña **GitHub.com**, elige `aarcardini/trazo` y pulsa **Clone**. Por defecto queda en `Documentos/GitHub/trazo`.
3. Para abrir la carpeta: **Repository → Show in Explorer** (Windows) o **Repository → Show in Finder** (Mac).

**Opción B — ZIP.** En la página del repositorio: botón verde **Code → Download ZIP** y descomprímelo donde quieras (la carpeta se llama `trazo-main`).

### 3. Arrancar Trazo
Trazo es un pequeño servidor que corre en tu computadora; se usa desde el navegador.

**Windows**
1. Abre la carpeta de Trazo en el Explorador de archivos (la que contiene `server.py`).
2. Haz clic en la barra de dirección (arriba), escribe `cmd` y pulsa Enter: se abre una ventana negra ya situada en esa carpeta.
3. Escribe `py server.py` y pulsa Enter. Debe aparecer un mensaje como `Trazo v2.0 en http://127.0.0.1:8765  (Ctrl+C para salir)`.
4. Abre http://127.0.0.1:8765 en el navegador (Chrome, Edge o Firefox).

**Mac**
1. Abre **Terminal**.
2. Escribe `cd ` (con un espacio al final), arrastra la carpeta de Trazo desde el Finder a la ventana de Terminal y pulsa Enter.
3. Escribe `python3 server.py` y pulsa Enter. Debe aparecer un mensaje como `Trazo v2.0 en http://127.0.0.1:8765  (Ctrl+C para salir)`.
4. Abre http://127.0.0.1:8765 en el navegador (Safari, Chrome o Firefox).

Deja esa ventana abierta mientras trabajas: si la cierras, Trazo se detiene. Para salir, pulsa **Ctrl+C** en esa ventana (también en Mac).
El modo Masterplan está en http://127.0.0.1:8765/masterplan.

### 4. Conectar con Rhino 8 (Mac y Windows)
El puente es el archivo `rhino/trazo_rhino.py`. Funciona con **Rhino 8** (usa Python 3; no funciona en Rhino 7).
1. Arranca Trazo (paso 3) **antes** de usar el puente.
2. En Rhino 8 escribe el comando `_RunPythonScript` y elige el archivo `rhino/trazo_rhino.py` dentro de la carpeta de Trazo. Con el guion bajo delante, el comando funciona aunque Rhino esté en español.
   - La primera vez, Rhino prepara Python 3 y puede tardar un poco.
   - En Mac, si el sistema pregunta si Rhino puede acceder a la carpeta Documentos, elige **Permitir**.
   - Alternativa: comando `_ScriptEditor`, abre el archivo y pulsa ▶ (Run).
3. En la línea de comandos elige **Enviar** (manda la masa seleccionada a la web), **Recibir** (dibuja en Rhino lo generado en la web) o **Diagnostico**.
   - **Diagnostico** comprueba que todo esté listo: muestra la versión de Rhino y de Python, las unidades del archivo, las capas de Trazo y si el servidor responde. Úsalo primero si algo no funciona.
   - Al enviar, la consola muestra la huella (m²), las medidas y la altura **en metros**: así ves enseguida si las unidades del archivo están bien.

Las unidades del archivo de Rhino (mm, cm o m) se convierten solas: Trazo trabaja en metros.

**Atajo (opcional):** crea un alias para no buscar el archivo cada vez. En Windows: **Herramientas → Opciones → Alias** (Tools → Options → Aliases); en Mac: **Rhino 8 → Ajustes → Aliases** (Settings). Añade el alias `trazo` con esta macro, cambiando la ruta por la de tu carpeta:
- Windows: `_-RunPythonScript "C:\Users\TU_USUARIO\Documents\GitHub\trazo\rhino\trazo_rhino.py"`
- Mac: `_-RunPythonScript "/Users/TU_USUARIO/Documents/GitHub/trazo/rhino/trazo_rhino.py"`

Desde entonces basta con escribir `trazo` en Rhino.

## Uso
1. Arranca Trazo (ver «Instalación», paso 3) y abre http://127.0.0.1:8765
2. En Rhino 8: comando `_RunPythonScript` y elige `rhino/trazo_rhino.py` (o el alias `trazo`).
   - **Enviar**: selecciona tu masa (sólido cerrado). Aparece sola en la web.
   - Para controlar el pasillo, dibuja polilíneas en la capa `Trazo::Centerline` antes de enviar (cada vértice es un giro del pasillo).
   - Para fijar los núcleos, coloca puntos en la capa `Trazo::Cores`; se usan en modo manual.
   - Para marcar medianeras, dibuja líneas en la capa `Trazo::Medianeras` (nombre `retiro=3` si el edificio se retira).
3. En la web: Calcular masa → Generar pasillo y núcleos → Generar mix → Generar planos.
   - Para empezar de cero: botón **Nuevo (en blanco)**, junto a «Ejemplo». Borra la masa, las polilíneas, los núcleos, las medianeras y el resultado, también los guardados en el servidor; conserva las medidas, el mix y los colores. Después envía una masa desde Rhino o elige un ejemplo.
   - En la planta 2D se ven las **cotas totales** de la huella (por fuera, alineadas con el edificio) y una **escala gráfica** abajo a la derecha; se ocultan con la casilla «Cotas».
   - El selector «Ejemplo» muestra siempre qué está cargado: un ejemplo, «Masa de Rhino: …» o «— En blanco —». Si miras un ejemplo, puedes volver a tu masa de Rhino eligiéndola en el selector.
4. En Rhino: ejecuta de nuevo el script y elige **Recibir** (capas `Trazo::L00::Units`, `Rooms`, etc.).
   Alternativa sin script: botón **DXF (Rhino)** y luego `Import`.

## Actualizar Trazo
Cuando haya cambios nuevos en GitHub (por ejemplo, después de aceptar un PR):
- **GitHub Desktop:** pulsa **Fetch origin** y luego **Pull origin**.
- **ZIP:** descarga de nuevo el ZIP y reemplaza la carpeta.

Después cierra Trazo (Ctrl+C), vuelve a arrancarlo y recarga la página en el navegador. Los colores y las medidas que guardaste en la web se conservan: están guardados en el navegador.

## Problemas frecuentes
| Mensaje o síntoma | Qué hacer |
|---|---|
| Windows: `"py" no se reconoce como un comando interno o externo` | Prueba `python --version`. Si tampoco funciona, Python no está instalado o no está en el PATH: reinstálalo marcando «Add python.exe to PATH». |
| Windows: al escribir `python` se abre la Microsoft Store | Python no está instalado: instálalo desde python.org (paso 1). |
| Mac: `command not found: python` | En Mac el comando es `python3`. |
| Mac: aparece una ventana para instalar las «herramientas de línea de comandos para desarrolladores» | Python no está instalado: cancela e instálalo desde python.org (paso 1). |
| `can't open file ... server.py` | La terminal no está en la carpeta de Trazo. Repite el paso 3 desde la carpeta que contiene `server.py`. |
| `Solo se permite un uso de cada dirección de socket` (Windows) o `Address already in use` (Mac) | Trazo ya está abierto en otra ventana: usa esa o ciérrala antes de arrancarlo de nuevo. |
| El navegador no abre la página («No se puede acceder a este sitio», «rechazó la conexión») | Trazo no está corriendo: arráncalo (paso 3) y recarga la página. |
| Rhino: `No hay conexión con Trazo` | Arranca Trazo antes de ejecutar el script: el mensaje dice el comando para tu sistema. |
| Rhino: `Seleccionaste una curva` (o una malla, un bloque, un SubD…) | La masa tiene que ser un sólido cerrado (polisuperficie o extrusión): el mensaje dice cómo convertirlo. |
| Rhino: `No encontré una cara inferior plana y horizontal` | La masa necesita una base plana y horizontal (por ejemplo, una extrusión cerrada). Si está abierta abajo, `_Cap`. |
| Rhino: `La masa es muy pequeña` o `La masa es enorme` | Casi siempre son las unidades del archivo: revísalas con `_Units` (Trazo trabaja en metros). Pregunta antes de enviar. |
| Rhino: `Todavía no hay un resultado` | Genera primero en la web y después elige **Recibir**. |
| Rhino: `El resultado no viene de una masa de Rhino` o `no coincide con la última masa` | En la web elegiste un ejemplo u otra masa: vuelve a **Enviar** tu masa, genera y recibe de nuevo. |
| Rhino: `error inesperado` | Copia el mensaje completo y pégalo en la sesión de Claude Code. |
| Rhino: `No module named request` o errores de sintaxis | El script se ejecutó con el Python 2 de Rhino 7. Usa Rhino 8: la primera línea del archivo (`#! python 3`) le indica que use Python 3. |

Si algo falla en Rhino, ejecuta el script y elige **Diagnostico**. Si no se resuelve, copia el mensaje completo de la terminal o de la línea de comandos de Rhino y pégalo en la sesión de Claude Code.

## Desarrollo con Claude Code (en la nube)
1. Entra en https://claude.ai/code y elige el repositorio `aarcardini/trazo`.
2. Pide una tarea del `ROADMAP.md`, por ejemplo: «implementa R1.1 del ROADMAP». Una tarea por sesión.
3. Claude trabaja en una rama nueva, ejecuta las pruebas y abre un **pull request** (PR) explicando qué cambia y cómo probarlo.
4. Revisa el PR en GitHub y prueba los cambios (en Rhino si hace falta). Si está bien, pulsa **Merge pull request** → **Confirm merge**.
5. Actualiza tu copia local (ver «Actualizar Trazo»). Cada PR marca su tarea con `[x]` en el `ROADMAP.md`, así que queda marcada al aceptarlo.

## Qué hace cada etapa
- **Masa**: huella, altura, nº de plantas, programa y altura por planta, espesor de muro exterior, GFA.
- **Pasillo y núcleos**: eje (automático o dibujado), ancho de pasillo, núcleos (ancho, fondo incluyendo pasillo, cantidad), distancias de evacuación (salida única / múltiple) y núcleos extra automáticos.
- **Mix**: tipos con m² objetivo y %, ancho mínimo, muro medianero; métricas Match Score, Fit y Unidades únicas.
- **Planos**: distribución día/noche con pasillo interno, puertas y grafo de conexiones verificado.

## Novedades v2.3
- **Cotas y escala gráfica en la planta 2D:** medida total de la huella (largo y fondo, alineadas con el edificio aunque esté girado) por fuera del dibujo, y una escala gráfica que se adapta al zoom (0 – 5 – 10 m, 0 – 10 – 20 m…). Casilla «Cotas» en la barra de la planta para mostrarlas u ocultarlas.

## Novedades v2.2.1
- **Corrección:** con una masa recién recibida (de Rhino o de un ejemplo), cambiar «Núcleos → Modo» a automático, pulsar «Auto» en las polilíneas o editar polilíneas y núcleos volvía a calcular solo la masa y dejaba la axonometría sin pasillo. Ahora calcula el pasillo y los núcleos y muestra la planta.
- Si el motor da un error o el servidor está apagado, el mensaje aparece en «Avisos» (antes solo en la etiqueta de abajo).

## Novedades v2.2
- **Nuevo (en blanco):** botón en el modo Edificio para empezar un proyecto de cero. Deja la planta vacía con el aviso «Envía una masa desde Rhino o elige un ejemplo» y borra también la masa y el resultado guardados en el servidor: al recargar la página no vuelve la masa vieja y «Recibir» en Rhino no trae un resultado anterior.
- El selector «Ejemplo» muestra qué está cargado: al llegar una masa de Rhino dice «Masa de Rhino: nombre» (antes seguía mostrando el ejemplo anterior) y se puede volver a ella después de mirar un ejemplo.

## Novedades v2.1
- **Diagnóstico en Rhino:** el script tiene una tercera opción, **Diagnostico**, que muestra la versión de Rhino y de Python, las unidades del archivo, las capas de Trazo, si el servidor responde y qué masa y resultado tiene.
- **Mensajes claros en Rhino** para cada fallo, siempre con qué hacer: servidor apagado (con el comando para Mac o Windows), objeto que no es un sólido (dice qué seleccionaste y cómo convertirlo), base que no es plana, base en varias partes, resultado que no corresponde a la masa enviada y errores inesperados.
- **Unidades a la vista:** al enviar se muestran la huella, las medidas y la altura en metros. Si parecen un error de unidades (una masa de 6 cm o de 60 km), avisa y pregunta antes de enviar.
- Más robusto: si Recibir falla a mitad, la vista de Rhino ya no queda sin redibujar.

## Novedades v2.0.1
- **Corrección (Masterplan):** al cambiar de ejemplo ya no se arrastra el tamaño de manzana del ejemplo anterior. Cada ejemplo usa su manzana o la estándar (80 × 120): por ejemplo, «Predio rectangular» da siempre 4 manzanas y 64 lotes, aunque antes se haya abierto «Barrio con plaza central» (75 × 95).

## Novedades v2.0
- **Modo Masterplan** (`http://127.0.0.1:8765/masterplan`, enlace arriba a la izquierda en ambos modos): predio → calles con perfil (calzada + veredas) → manzanas con ochavas → lotes por frente con mix de tamaños → construcción por lote (retiros, FOS, pisos).
- Calles: «Trazar damero» (según ancho × largo de manzana) o dibujadas a mano; perfil propio por calle. Funcionan cruces y T; los bordes del predio pueden marcarse como calle existente.
- Manzanas: clic para cambiar el uso (Lotes → Espacio verde → Equipamiento). Lotes en una o dos filas según los frentes a calle; los frentes nunca bajan del mínimo del mix y los lotes de borde que no llegan al área mínima se funden con el vecino.
- Métricas: % de calles, reserva para espacios libres y equipamiento (aviso si queda bajo el 10 % de la Ley 18.308, art. 38), cesiones, nº y área media de lotes, ocupación, área construible y viviendas estimadas; donut de usos del suelo; vista axonométrica con las construcciones.
- **Del lote al edificio:** «Abrir en modo Edificio» lleva la huella, la altura y las medianeras del lote al modo Edificio para estudiar la planta tipo.

## Novedades v1.9
- **Nuevo nombre: Trazo.** Capas de Rhino `Trazo::...`, script `rhino/trazo_rhino.py`, capas DXF `Trazo_...`. Los colores y medidas guardados en el navegador se conservan.
- **Corrección del mix:** cuando un tramo no admitía la cantidad de unidades calculada, se generaba una sola unidad enorme (por ejemplo 413 m²). Ahora se usa la cantidad máxima posible y avisa si una unidad se aleja más de 35 % de su m² objetivo.
- **Predios largos entre medianeras:** solo los frentes reciben luz. Las viviendas se ubican en cada frente con el fondo justo para su m² y su frente mínimo, se llega a ellas por un pasillo contra la medianera, y la zona central se marca «sin luz — requiere patio» con su superficie.

## Novedades v1.8
- **Medianeras y retiros:** «Marcar medianeras» y clic sobre los bordes de la planta (líneas rojas). Cada medianera tiene un retiro: con 0 m (adosado) no admite ventanas; con un retiro ≥ 3 m (editable en «Medidas y normativa → Predio») el edificio se retira y esa cara pasa a ser fachada.
- El motor lo usa: estancias contra medianera no cuentan como iluminadas; con una medianera larga el pasillo se apoya contra ella; en un **predio entre medianeras** (los dos lados largos ciegos) arma la solución típica: franja central con núcleo contra la medianera y hall, y una vivienda hacia cada frente con todo el ancho del predio.
- Desde Rhino: curvas en la capa `Trazo::Medianeras` (nombre del objeto `retiro=3` para indicar retiro).
- Ejemplo nuevo: «Predio entre medianeras 10 × 28».

## Novedades v1.7
- **Medidas reales** (`engine/standards.py`, `STANDARDS.md`): mínimos normativos y medidas típicas por estancia, núcleo, oficinas, comercio y estacionamiento. Editables en la web («0 · Medidas y normativa») y guardadas en el navegador.
- **Vivienda:** dormitorios, baños, cocina, lavadero, pasillo y hall se dimensionan con esas medidas; la ficha de la unidad marca lo que no llega al mínimo (⚠), lo que queda bajo el típico (ℹ) y si la superficie sale del rango ANV.
- **Núcleo real:** caja de escalera de ida y vuelta (contrahuellas según altura de piso), ascensores accesibles (ducto 1,75 × 1,95) con palier, ducto de instalaciones; nº de ascensores según altura y unidades; tipo de escalera según altura (común, protegida, presurizada). Se dibuja en planta y en 3D.
- **Oficinas y comercio:** hall de acceso, batería de baños (mujeres, hombres, accesible) según Dec. 406/988 y el resto como planta libre.
- **Estacionamiento:** plazas de 2,50 × 5,00 en peine con calles de 6,00 m y calle transversal; cuenta de plazas.
- Ejemplo nuevo: «Barra mixta» (estacionamiento + comercio + oficinas + vivienda).

## Novedades v1.6
- **Colores por programa, editables:** cada programa tiene su color (clic en el cuadrado de color en «Programas» o en «Leyenda → Colores de todos los programas»). Se guardan en el navegador; «Restaurar colores» vuelve a los de fábrica.
- **Áreas internas en tonos del programa:** dentro de Residencial, cada tipo de estancia (dormitorio, estar, cocina, baño, pasillo…) y cada tipo de unidad usa una gama del mismo color. Pasillos y núcleos usan tonos de Circulación. La leyenda muestra la gama.

## Novedades v1.5
- **Axonometría 3D** (botón «Axonometría 3D»): niveles coloreados por programa, girar arrastrando o con ⟲ ⟳, vista explotada con la planta de cada nivel, aislar selección y modo alambre.
- **Selección de niveles** como en un estudio de masas: clic, Shift (rango), Ctrl/Cmd (sueltos), o por función desde el gráfico de anillo «Programas». Panel para cambiar programa y altura (y crear programas nuevos). Doble clic abre la planta 2D de ese nivel.
- **Conexiones dentro de la vivienda** (`engine/plans.py`): zona de día (hall, cocina, estar-comedor) y zona de noche (pasillo interno, dormitorios a fachada, baños, lavadero), puertas y grafo de conexiones (abierto/puerta). Comprobaciones por unidad: acceso desde la entrada, dormitorios y estar con fachada, anchos mínimos y frente mínimo según nº de dormitorios. Clic en una unidad para ver su ficha; «Calidad de planos» en las métricas.
- Mix con columna «Dorm.» (vacío = según m²). Zoom con la rueda y desplazamiento arrastrando en la planta.
- Puertas exportadas a Rhino y DXF (capa `Doors`).

## Novedades v1.4
- **Polilíneas** como líneas centrales: varias líneas, giros, empalmes en T. Se dibujan en la web (clic por vértice, Enter o doble clic para terminar), se editan arrastrando los vértices y se borran con clic derecho.
- **Núcleos manuales**: «+ Añadir núcleo» y «Quitar núcleo» en la web; se ajustan al pasillo más cercano. Modo automático o manual.
- Desde Rhino: las curvas de `Trazo::Centerline` y los puntos de `Trazo::Cores` viajan con la masa.

## Novedades v1.3
- Plantas ortogonales (L, U, T…) se dividen en alas, cada una con su pasillo; los pasillos se conectan.
- Pasillo central (doble crujía) o de borde (simple): en modo *auto* elige por ala el que da unidades más proporcionadas.
- Los núcleos absorben o ceden los bolsillos detrás de ellos; la web muestra Circulación y Área sin usar.
- El servidor recarga el motor solo si actualizas los archivos de `engine/`. La versión se ve junto al título en la web.

## Límites conocidos
- En modo automático, formas no ortogonales usan un solo pasillo recto: dibuja una polilínea para controlarlo.
- Si dos líneas se cruzan en X (no en T), las unidades cerca del cruce pueden solaparse.
- Las plantas residenciales repiten la misma planta tipo.
- Los planos de unidad son reglas geométricas (sin optimización ni mobiliario); las unidades en esquina no aprovechan aún su segunda fachada.
- El script de Rhino no se pudo probar en un Rhino real durante el desarrollo; si falla algo, copia el mensaje de la consola de Rhino.

## Pruebas
`python tests/test_engine.py` (en Windows `py tests/test_engine.py`; en Mac `python3 tests/test_engine.py`).

Incluye **pruebas de regresión**: para cada ejemplo de `samples/` hay métricas de referencia en `tests/golden/` (unidades, eficiencia, sin usar, núcleos, lotes…). Si un cambio del motor las mueve más que el margen, la prueba falla y dice qué cambió. `python tests/regresion.py` muestra la tabla completa (referencia y valor actual).

En GitHub las pruebas corren solas en cada PR (GitHub Actions, sin usar Claude): el PR muestra el check **Pruebas** en verde (todo bien) o en rojo (algo se rompió; el detalle está en «Details»).
