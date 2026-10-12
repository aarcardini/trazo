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
   - Para fijar los núcleos, coloca puntos en la capa `Trazo::Cores`; se usan en modo manual (nombre `ascensores=2` para fijar los ascensores de ese núcleo).
   - Para marcar medianeras, dibuja líneas en la capa `Trazo::Medianeras` (nombre `retiro=3` si el edificio se retira).
   - Para abrir patios, dibuja curvas cerradas en la capa `Trazo::Patios`; llegan a la web en modo manual.
3. En la web: Calcular masa → Generar pasillo y núcleos → Generar mix → Generar planos. Cada botón está al pie de su grupo, en el riel de la izquierda: **Masa** (Calcular masa), **Circulación** (Generar pasillo y núcleos) y **Viviendas** (Generar mix y Generar planos). Un clic en el grupo abre su panel y otro lo cierra (o Esc).
   - **La interfaz (v2.37):**
     - **Arriba:** el nombre de lo que está abierto, su etapa, deshacer y rehacer, y el botón del sol o la luna que cambia entre el tema claro y el oscuro (v2.43).
     - **Riel de la izquierda:** Proyecto (nuevo, abrir, guardar, ejemplos, variantes, exportar), Masa, Circulación, Viviendas, Normativa (medidas) y Vista (tema, colores y leyenda).
     - **Sobre la planta:** la vista 2D o 3D, el nivel y el menú **Capas** (conexiones, equipamiento, cotas, evacuación y datos al pasar el mouse).
     - **Abajo, la barra de dibujo:** **Línea**, **Núcleo**, **Medianera** y **Patio**, más **SCP**, **Grilla** (F7), **Orto** (F8) y **Snap** (F9; con Alt, el punto queda libre). Mientras una herramienta está activa, arriba de la barra aparecen qué hacer y sus botones (Terminar, Borrar última, Quitar núcleo…); con un vértice de la línea o la primera esquina de un patio puestos, también campos para **escribir las medidas** (largo y ángulo; ancho y fondo).
     - **A la derecha:** el resumen (unidades, NSA, eficiencia, calidad de planos, núcleos, ascensores), los avisos y la ficha de la vivienda o del núcleo que elijas. **Ver todo** suma los programas, todas las métricas y la tabla de unidades.
   - **Patios** (Masa → Patios): en modo automático, Trazo abre patios donde un predio entre medianeras es demasiado profundo para tener luz; cada bloque lleva su núcleo. Con **Patio**, en la barra de dibujo, haces clic en dos esquinas opuestas, o en una y escribes el ancho y el fondo (el patio se alinea con el edificio y se recorta a la masa); la × de la lista lo quita. Dibujar o quitar un patio pasa a modo manual. Las estancias que dan a un patio de al menos 3 m (editable en «Normativa → Predio») tienen luz.
   - Un patio **dentro** de la masa (sin tocar el borde) la convierte en un anillo: alas alrededor del patio y un pasillo que da la vuelta (U cerrada o claustro). Ejemplos: «Edificio con patio central 40 × 30» y «Entre medianeras 30 × 45 con patio central (U cerrada)».
   - **Guardar y abrir proyectos:** **Guardar proyecto** crea un archivo `nombre.trazo.json` con todo lo que define la planta: masa, programa por planta, medianeras, patios, polilíneas, núcleos (con sus medidas), mix, parámetros, las medidas de normativa que cambiaste y la etapa a la que llegaste. En Chrome y Edge eliges la carpeta (por ejemplo, junto al archivo de Rhino); en Safari y Firefox va a Descargas. **Abrir proyecto…** lo vuelve a cargar y genera hasta la misma etapa; las medidas, el mix y los parámetros pasan a ser los del proyecto. También abre una masa suelta (por ejemplo, un archivo de `samples/`). El resultado no se guarda: se recalcula al abrir. El botón **Resultado (JSON)** de «Exportar» es otra cosa: el resultado calculado, para leerlo con otros programas.
   - **Equipamiento y muebles:** con «Generar planos», los baños llevan ducha, inodoro, lavatorio y bidé (si entra), la cocina una mesada de 0,60 m con heladera, bacha y cocina, y el lavadero lavarropas y pileta, cada uno con su paso libre. El dormitorio principal lleva cama doble con mesas de luz y placard; los demás, dos camas individuales (o una, si no entran dos) con mesa de luz y placard; el estar, un sofá frente al rack de TV y butacas si entran; la mesa del comedor tiene 4 asientos y 2 más por cada dormitorio después del primero (un monoambiente: cama doble y mesa para 2). Las puertas interiores miden 0,70 m y la de entrada 0,90 m. Si algo no entra, la ficha de la vivienda lo dice (por ejemplo «Cocina: no entra la heladera» o «Estar-Comedor: no entra la mesa para 6 (entra una para 4)»); en una estancia que ya no llega a su medida mínima no se repite el aviso. Un segundo baño donde no entra la ducha queda como toilette. **Vivienda accesible:** marca la casilla **Acc.** de un tipo en el mix y sus viviendas llevan puertas de 0,82 m en dormitorios y baño, y un baño más ancho (2,20 m) que abre hacia afuera, con ducha a nivel, inodoro con 0,80 m de transferencia al costado, lavatorio y un círculo de giro de 1,50 m (punteado en la planta); la ficha dice «♿ accesible» y avisa si el baño no llega. **Vestidor:** marca la casilla **Vest.** de un tipo y el dormitorio principal de sus viviendas lleva un vestidor con estantes en lugar del placard (con la suite, entre el dormitorio y su baño); si no entra, la ficha dice por qué. Las medidas se cambian en «Normativa → Equipamiento y muebles», y la capa **Equipamiento** (menú «Capas», sobre la planta) lo muestra u oculta. En Rhino va a la capa `Trazo::L00::Equipamiento` (y en el DXF a `Trazo_L00_Equipamiento`).
   - **Editar viviendas:** haz clic en una vivienda (después de «Generar mix» o «Generar planos»). Sus tabiques con las vecinas se ven en azul: **arrástralos** para mover el límite (cada vivienda conserva al menos la mitad del ancho mínimo). En su ficha, **Dividir en dos** la parte por la mitad (después puedes mover el tabique nuevo) y **Unir con U0X** la junta con la vecina. Una vivienda unida o dividida toma el tipo del mix si su superficie se parece; si no, se nombra por sus dormitorios (por ejemplo «Monoambiente»). Las editadas llevan ✎; los planos, la evacuación y las métricas se recalculan. Todo se deshace con Ctrl+Z, se guarda con el proyecto y con las variantes, y **Descartar cambios** (Viviendas → Viviendas editadas) vuelve al mix automático. Si cambias la planta y un cambio ya no entra, Trazo avisa.
   - **Ventanas:** con «Generar planos», cada dormitorio, estar y estudio con fachada lleva su ventana, centrada en su pared de fachada (primero la del fondo) y a 0,20 m de las esquinas: de 1,50 m en los dormitorios y 2,00 m en el estar, o más ancha si el vano mínimo lo pide (10 % de la superficie del local, con ventanas de 1,20 m de alto). Si un comedor no tiene fachada, la ventana del estar ilumina los dos. Si no alcanza, se agrega otra en la fachada lateral, y una estancia de esquina lleva además una ventana típica en la otra fachada; si aun así no llega, o si no entra ninguna, la ficha lo avisa. Las ventanas se dibujan en el muro exterior y la ficha lista su ancho. En Rhino van a la capa `Trazo::L00::Ventanas` (con su medida en el nombre) y en el DXF a `Trazo_L00_Ventanas`. Las medidas se cambian en «Normativa → Ventanas».
   - **Segunda fachada:** una vivienda de esquina o de extremo (con fachada al fondo y en un costado) la usa. Si el frente alcanza, el **estar va a la esquina**, con ventana en las dos fachadas (el plano se dibuja al revés si hace falta). Si el frente no alcanza para todos los dormitorios al fondo y hay fondo suficiente, el **último dormitorio va al costado**, entre el pasillo común y el pasillo interno, con su ventana a esa fachada; Trazo lo hace solo si el plano mejora y no pierde estancias (puede quedar un solo baño). La ficha lo dice en «Comprobaciones» («Fachada lateral: …»). Si el fondo no es todo fachada, o si la vivienda da a las dos puntas, el plano queda como antes.
   - **Editar la vivienda por dentro:** con una vivienda elegida (después de «Generar planos»), sus tabiques interiores se ven en verde y sus puertas en naranja. **Arrastra un tabique** para agrandar una estancia y achicar la vecina: las estancias que se apoyan en ese tabique se mueven juntas y cada una conserva al menos 0,60 m. **Arrastra una puerta** para correrla a lo largo de su pared. En la ficha, la lista **Puertas** cambia el ancho de cada una y con **⇄** la hace abrir hacia el otro lado (la de entrada solo se corre o cambia de ancho). Los artefactos, los muebles y las comprobaciones se recalculan: si una estancia queda por debajo de su medida mínima o algo deja de entrar, la ficha lo dice. Todo se deshace con Ctrl+Z, se guarda con el proyecto y las variantes, y **Descartar los cambios por dentro** (en la ficha) vuelve a la distribución automática de esa vivienda. Si cambias la planta o el mix y un cambio ya no entra, Trazo avisa.
   - **Variantes:** con **Guardar como variante** (Proyecto → Variantes) guardas la solución actual; **Comparar** muestra una tabla con cada variante y la solución actual: unidades por planta y totales, NSA, eficiencia, match, circulación, superficie sin usar, núcleos, viviendas que no cumplen la evacuación y calidad de planos, con lo mejor de cada columna en verde. **Abrir** vuelve a esa variante (masa, líneas, núcleos, mix y parámetros); un clic en el nombre lo cambia; **×** la borra; **Copiar tabla** la copia para pegarla en una planilla. Las variantes se guardan con el proyecto («Guardar proyecto») y «Nuevo» las borra.
   - **Mover o quitar un pasillo (v2.44):** clic en un tramo de pasillo de la planta; en su ficha, «Mover o quitar» ofrece **Pasar a líneas** (el pasillo automático pasa a líneas que mueves arrastrando sus vértices) y **Quitar este tramo**. El mismo «Pasar a líneas» está en Circulación, junto a «Auto». Los detalles, en «Novedades v2.44».
   - **Mover un núcleo:** arrástralo en la planta 2D. Mientras lo arrastras se ve punteado dónde va a quedar; al soltarlo, Trazo lo ajusta al pasillo más cercano, del lado donde lo dejaste (si cruzas el pasillo, cambia de lado), y recalcula. Si los núcleos eran automáticos, pasan a manual (los demás quedan donde estaban). Conserva sus medidas propias y su giro. Un clic sin mover abre su ficha, como antes.
   - **Deshacer y rehacer:** botones **↶** y **↷** de la barra superior, o **Ctrl+Z** (Cmd+Z en Mac) y **Ctrl+Shift+Z** (o Ctrl+Y). Deshacen lo que dibujas o cambias en la planta: polilíneas y sus vértices, núcleos (añadir, quitar, cambiar en su ficha, modo), medianeras y patios. Al pasar el ratón sobre ↶ dice qué se va a deshacer. Mientras dibujas una polilínea, Ctrl+Z borra el último vértice. Al cambiar de masa o abrir un proyecto la historia empieza de nuevo.
   - Para empezar de cero: botón **Nuevo (en blanco)**, en Proyecto. Borra la masa, las polilíneas, los núcleos, las medianeras, las variantes y el resultado, también los guardados en el servidor; conserva las medidas, el mix y los colores. Después envía una masa desde Rhino o elige un ejemplo.
   - En la planta 2D se ven las **cotas totales** de la huella (por fuera, alineadas con el edificio) y una **escala gráfica** abajo a la derecha; se ocultan con la capa «Cotas» (menú «Capas»).
   - El selector «Ejemplo» (Proyecto → Masa abierta) y la barra superior muestran siempre qué está cargado: un ejemplo, «Masa de Rhino: …» o «— En blanco —». Si miras un ejemplo, puedes volver a tu masa de Rhino eligiéndola en el selector.
4. En Rhino: ejecuta de nuevo el script y elige **Recibir** (capas `Trazo::L00::Units`, `Rooms`, etc.).
   - Si ya habías recibido un resultado, pregunta qué hacer: **Reemplazar** (borra el anterior, también lo que esté oculto o bloqueado, y dibuja el nuevo), **Agregar** (deja los dos) o **Cancelar**. No dibujes a mano en las capas `Trazo::Footprint` ni `Trazo::L00…`: Reemplazar las vacía.
   - Los patios recibidos se dibujan en cada nivel (`Trazo::L00::Patios`…); la capa `Trazo::Patios` es solo para enviar.
   - Alternativa sin script: botón **DXF (Rhino)** y luego `Import`.

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
| Rhino: después de **Recibir** aparece todo repetido | Hasta la v2.4, cada Recibir dibujaba encima del anterior. Ahora pregunta: elige **Reemplazar** y borra también las copias viejas. |
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

## Novedades v2.48
- **Equipamiento independiente del orden (R5.14a, corrección):** el equipamiento de una vivienda (camas, placard, sofá, artefactos) **ya no depende de qué otras viviendas se calcularon antes**. Antes, Trazo guardaba el equipamiento de cada estancia para reusarlo en las de la misma medida, pero «la misma medida» se comparaba al décimo de milímetro y el cálculo usaba la medida exacta: dos dormitorios de 2,80 × 3,50 m, con la puerta al medio y la ventana de lado a lado, pueden diferir en una billonésima de milímetro (según dónde cae la vivienda a lo largo del pasillo) y, en una estancia simétrica, esa diferencia decide si el placard o la cama van contra la pared de la izquierda o la de la derecha. La segunda estancia recibía lo que había decidido la primera: el mismo plano salía con los muebles de un lado o del otro según las viviendas (o los ejemplos) que se hubieran generado antes, al volver a generar, al abrir un proyecto o al comparar dos versiones de Trazo.
  - **Qué cambia en la planta:** nada en la distribución, solo el lado de algunos muebles en estancias simétricas; cada vivienda sale como saldría calculada sola. En los 13 ejemplos, corridos en el orden de `tests/regresion.py`, 6 de las 124 viviendas cambian de lado un mueble (el placard del Dormitorio 2 de U01 y U05 en `barra`, el del principal de U06 en `barra_larga`, el estar de U09 en `cruz_dos_lineas`, las camas de U09 y U10 en `torre_mixta`) y otras 6 se corren una décima de milímetro; en las demás todo sigue igual. Las métricas de los ejemplos (unidades, eficiencia, sin usar, núcleos, avisos) son las mismas. Rhino y la web: sin cambios.
  - **Cómo probarlo:** `python tests/test_engine.py` (`test_equipamiento_orden`): el caso mínimo —dos dormitorios de 2,80 × 3,50 m calculados en uno y otro orden— y cada vivienda de cinco ejemplos corridos uno tras otro, comparada con la misma vivienda calculada con la memoria vacía, dan lo mismo.
  - **Velocidad:** la memoria ahora distingue más estancias (se calculan más), así que la comprobación de que se llega a todos los muebles recorre la grilla por bits, con el mismo resultado y unas cuatro veces más rápido: `python tests/regresion.py` tarda prácticamente lo mismo que antes.

## Novedades v2.46
- **Cocina con ventana propia (R10.9):** la cocina que toca una fachada (en las viviendas de punta o de esquina, donde su costado da al exterior) lleva ahora **su propia ventana**, de 1,00 × 1,20 m (0,40 m² como mínimo, norma nacional, art. 24; más ancha si el 10 % de su superficie pide más), y **conserva su medida típica**: es una cocina según el art. 21 (mínimo 4 m² y lado 1,60 m), se dibuja con su superficie típica (7 m², «Normativa → Vivienda → Cocina») como máximo en vez de los 5 m² de la cocina integrada sin ventana, conserva su fondo (se angosta, y lo que deja va al hall, al baño o a un depósito, como antes) y no cuenta en el vano del estar. En «Barra 60x16», las dos viviendas de punta que tocan la fachada del extremo (U04 y U05) pasan de 5 a 7 m² de cocina, con su ventana en el muro del extremo.
  - **Las demás, con extractor:** la cocina sin fachada sigue integrada al estar con 5 m² como máximo (art. 27) y se ventila con extractor eléctrico (decisión del usuario): en la ficha de la vivienda, junto a «Cocina», dice **(con extractor)**. Un «Hall / Cocina» con fachada también lleva su ventana.
  - **Dónde verlo:** en Viviendas → «Generar planos», clic en una vivienda de punta: la ventana de la cocina se dibuja en la planta y la ficha la lista en «Ventanas» (si no llega a su vano mínimo, avisa como las demás). En «Normativa → Ventanas» se editan el ancho típico de la ventana de la cocina y su vano mínimo. En Rhino, la ventana sale con las demás en `Trazo::Lnn::Ventanas` (y en el DXF), sin cambios en el script.
  - Los planos de las viviendas sin cocina con fachada no cambian; las métricas de los ejemplos son las mismas.

## Novedades v2.45
- **Medidas exactas tipeadas (R4.13b):** mientras dibujas, **lo que escribes manda y el puntero solo elige la dirección** (y la medida que no escribiste), como la entrada directa de distancia de AutoCAD. Solo cambia la web: el motor es el mismo.
  - **Línea:** con el primer vértice puesto, la barra de dibujo suma **Largo (m)** y **Ángulo (°)**. Mueve el puntero hacia donde va el tramo (con **Orto**, hacia el eje del SCP más cercano), escribe el largo —`12`, `3,20` o `3.20`— y pulsa **Enter**: el vértice queda a 12,00 m del anterior, en la dirección del puntero. Si escribes también el ángulo, la dirección es esa: se mide en el SCP (0° es su eje x, y crece en sentido antihorario) y manda sobre el Orto; si escribes solo el ángulo, la dirección queda fija y el largo lo da el puntero (hasta donde lo proyecta sobre esa dirección, al paso de la grilla). Un clic en la planta con algo escrito también pone el vértice con esa medida, y al ponerlo los campos se vacían. Lo escrito no se redondea a la grilla (el snap y el Orto son del puntero). En gris, dentro de cada campo, ves lo que da el puntero. **Enter con los campos vacíos termina la línea**, como siempre.
  - **Patio:** con la primera esquina puesta, la barra trae **Ancho (m)** y **Fondo (m)**, en los ejes del edificio (los mismos con que se dibuja el patio). Escribe una o las dos y pulsa **Enter**: el patio se cierra con esas medidas; el puntero elige hacia qué lado va cada una y da la que no escribiste. Un patio de menos de 1 m² no se crea y Trazo lo dice.
  - **Tabique entre viviendas:** con una vivienda elegida, un clic en uno de sus tabiques azules —o empezar a arrastrarlo— muestra en la barra el **frente de las dos viviendas vecinas** (su medida a lo largo del pasillo; el tabique elegido se dibuja más grueso). Escribe el frente de una —la elegida va primera— y pulsa **Enter**: el tabique se mueve hasta que esa vivienda quede con ese frente exacto y la otra toma el resto («U03 mide ahora 13.25 m de frente»). **↶** lo deshace. Si no entra —menos de la mitad del ancho mínimo de vivienda (2,50 m con el valor de 5 m) o más de lo que suman las dos menos esa mitad— Trazo lo avisa y no cambia nada. Mientras arrastras, los dos frentes de la barra siguen al tabique. **Esc** suelta el tabique, y un clic en otra cosa también.
  - **Teclado:** con la barra a la vista, un número que escribes va directo al primer campo (no hace falta hacer clic en él); **Tab** pasa al campo siguiente; **Esc** cierra la herramienta, como hoy.
  - **Exactitud:** el tramo de línea de 12 m mide 12,00 m (el motor lo dibuja con `largo` 12,0, también con un SCP girado) y el frente tipeado de un tabique queda exacto al centímetro: en 42 tabiques de los ejemplos (11 de los 13 tienen tabiques; sus ejes van en x, en −x, en y y oblicuos a 45°) y, medido con la geometría, al milímetro.
  - **Pendiente:** lo mismo para el tabique interior de una vivienda (R5.7) y para el desplazamiento de un núcleo; el patio sigue alineado con el edificio, no con un SCP girado a mano (R4.7). El terreno rectangular ya se escribía (Masa → Terreno rectangular).

## Novedades v2.44
- **Quitar o mover un pasillo (R4.11):** si el pasillo automático deja un tramo que no sirve a nadie y planta vacía donde entrarían viviendas, ahora lo quitas o lo mueves. Haz clic en el tramo de la planta: en su ficha, bajo **«Mover o quitar»**, están **Pasar a líneas** y **Quitar este tramo**. En Circulación, junto a «Auto», hay otro **Pasar a líneas**.
  - **Pasar a líneas:** los pasillos automáticos pasan a líneas centrales, una por tramo (los tramos que se tocan por un extremo, como en un quiebre a 45°, forman una sola línea). Desde ahí cada tramo se mueve arrastrando sus vértices o se quita, como cualquier línea dibujada; «Auto» devuelve el pasillo automático (los núcleos y los patios siguen manuales: para volver a todo como estaba, **↶**). Los **núcleos quedan donde están** (pasan a modo manual) y, si el predio tenía patios automáticos, también **los patios** (pasan a manuales: con líneas dibujadas Trazo ya no traza solos los patios entre medianeras). Los anchos propios de un tramo se conservan. **↶** deshace todo junto: líneas, núcleos y patios.
  - **El plano casi no cambia:** donde dos alas se encuentran en un codo (por ejemplo una L), el reparto de las viviendas del codo puede cambiar y Trazo avisa «no entran donde se cruzan los pasillos dibujados»: en «Forma en L» queda una vivienda menos; revisa el codo. Entre medianeras, la franja del núcleo se reparte distinto como línea (puede dar más o menos viviendas): la ficha lo dice.
  - **Quitar este tramo:** lo hace en un paso. Con el pasillo automático, pasa los pasillos a líneas sin ese tramo; con líneas ya dibujadas, quita el segmento de la línea que lo genera (si la línea tenía más vértices, queda partida en la parte de antes y la de después; si cruzaba otra y quedó cortada en dos tramos, la ficha lo dice y se quitan juntos). Trazo reparte las viviendas con los pasillos que quedan: donde un pasillo cercano alcanza, sus viviendas ocupan el lugar (con dos pasillos paralelos a 11 m en un edificio de 40 × 22 m, al quitar uno las viviendas del otro pasan de 4 m a 14 m de fondo, de 6 a 8 viviendas, y la eficiencia de 64 % a 75 %). Lo que ningún pasillo sirve queda sin usar, y si la planta servida baja de 55 % aparece el aviso «Solo el X % de la planta está servido por el pasillo…».
  - **Núcleos sueltos:** los núcleos quedan donde estaban: si el tramo quitado tenía un núcleo en su punta, el motor lo pasa al pasillo más cercano, donde puede quedar sobre otro núcleo («El núcleo N se superpone con otro»); quítalo con **Núcleo** en la barra de dibujo.
  - **Lo que no se puede:** el único pasillo de un bloque no se quita, porque un bloque sin líneas vuelve a trazar su pasillo solo: el botón queda apagado y la ficha lo explica (en «Entre medianeras 15 × 30 con patio» cada bloque trae un solo pasillo: se puede pasar a líneas y moverlo, no quitarlo; dibuja antes otro pasillo en ese bloque). Con un **patio interior** (U cerrada, claustro) el pasillo da la vuelta al patio y Trazo no usa las líneas: ahí no se ofrece y la ficha dice por qué.
  - **En Rhino:** la web no cambia tu archivo. Si el pasillo viene de Rhino, para quitar o mover un tramo allá, borra o mueve la polilínea de la capa `Trazo::Centerline` y vuelve a **Enviar**.

## Novedades v2.43
- **Modo claro y oscuro con un botón (R4.10):** en la barra superior, junto a ↶ y ↷, el botón del sol o la luna cambia entre el tema claro y el oscuro; el mismo botón está junto al título del Masterplan. Cambia todo: paneles, grilla, planta y axonometría. Sobre el fondo oscuro, las cotas, la escala y los rótulos de patios y zonas sin luz de la planta (antes grises fijos: la escala y los rótulos casi no se leían) y las aristas de la axonometría pasan a claros; con el tema claro la planta no cambia. Al pasar el mouse por el botón dice el tema de ahora y qué hace el clic.
  - **Se recuerda:** Trazo guarda tu elección en el navegador y la usa en el modo Edificio y en el Masterplan, sin parpadeo al abrir la página.
  - **«Sistema»:** en «Vista → Apariencia → Tema» eliges «Sistema» (sigue el tema del equipo, como hasta ahora), «Claro» u «Oscuro»; el selector y el botón van juntos. En el Masterplan está solo el botón: para volver a «Sistema», usa el selector del modo Edificio.

## Novedades v2.42
- **La tira sin luz de las viviendas muy profundas, para servicios (R5.11):** en una vivienda de más de 9,30 m de fondo, entre la franja de baños y el pasillo común quedaba una tira oscura sin uso (en «Edificio con patio central», 6,6 m² en las U04 y U05). Ahora esa tira es una banda de servicios:
  - **Cocina y lavadero en la tira:** el hall va al extremo del estar, con la entrada, y la cocina corre de él hacia la tira, integrada al estar como hasta ahora (5 m² como máximo, art. 27), con su mesada en línea o en L. Sigue el lavadero, con puerta desde la cocina. El estar (o el comedor, si ya lo había) baja hasta la banda y gana el fondo que tenía la cocina; la banda no parte el estar en un comedor aparte.
  - **El depósito vuelve a la franja,** con puerta desde el pasillo interno, y la franja ya no lleva el lavadero: ese largo deja lugar a la suite o a baños más grandes. Si así queda menos sin uso, el depósito va a la banda, después del lavadero y con puerta desde él.
  - **Lo que sobra** agranda el lavadero hasta 4 m². Si después queda poco (menos de 0,90 m de largo o de 1 m²), que no da para otra estancia, también va al lavadero, aunque pase de 4 m² (hasta unos 6,6 m²): es la misma regla de la franja desde v2.33. Lo demás queda sin uso, con el aviso del fondo. La banda no pasa de 2,90 m (el fondo típico de una cocina, en «Normativa → Vivienda → Cocina»): en una vivienda de 17 m de fondo, lo que queda sobre ella sigue sin uso.
  - **Tira de 1,00 a 1,60 m:** no entra la mesada; la cocina sigue en la zona de día y la tira lleva el lavadero, con puerta desde el hall (o desde la cocina, si el hall está en el extremo porque el pasillo común solo llega ahí, R3.7). Con menos de 1,20 m (el lavarropas y su paso), solo si igual entran el lavarropas y la pileta, con su paso (el lavarropas, contra una pared del costado); si no, el lavadero sigue en la franja, como antes.
  - **La cocina no va a la tira** si el estar quedaría más de 3 veces más profundo que ancho (art. 14) o si su ventana dejaría de alcanzar para él y la cocina (art. 27): entonces se queda en la zona de día, como antes, y la tira lleva el lavadero.
  - **Con un muro oblicuo o un entrante** (un costado inclinado, una esquina cortada junto al pasillo común), la banda se mide con el contorno real: el hall conserva su borde sobre el pasillo común para la puerta de entrada, la cocina sus 3 m² y su mesada, el lavadero sus 1,5 m² y sus artefactos, y el depósito su superficie mínima; si no, la tira queda como antes. Y la banda va solo si el plano no empeora: si sin ella tiene más calidad o más estancias, queda el plano de antes. En una vivienda con tira, la suite va solo si el muro no se come el dormitorio principal ni su baño (antes, el baño en suite podía quedar sin acceso), y la que permite la banda, con el baño completo (no un toilette).
  - **En los ejemplos:** en «Edificio con patio central» la U05 queda sin sin uso y pasa de 50 a 100 de calidad (cocina de 5,0 m², lavadero de 4,5 m² y depósito de 4,0 m² en la banda; suite), y la U04 baja de 6,6 a 3,6 m² sin uso; la calidad de planos del ejemplo sube de 83 a 90. En la T y en la cruz el sin uso baja (cruz: de 75,7 a 61,8 m²). En una barra de 60 × 22 la calidad de planos sube de 37 a 63; en una de 60 × 24 el sin uso baja de 72 a 28 m². Las viviendas sin tira (hasta 9,30 m de fondo) no cambian, tampoco con un muro oblicuo.
  - Funciona con el plano al revés, el hall en el extremo (R3.7), el dormitorio al costado (R5.3), la vivienda accesible, el vestidor (R5.10) y los cambios a mano (R5.7).
- **Corrección:** un rincón sin uso podía dibujarse sin su aviso en la ficha (cuando el trozo que llevaba el aviso quedaba vacío) y no bajaba la calidad del plano. Ahora cada rincón sin uso lleva su aviso, con la superficie que queda dentro de la vivienda (con un muro oblicuo, antes decía la del rectángulo).
- **Sin puerta de entrada:** si un muro oblicuo deja la vivienda sin hall, y con él sin puerta de entrada, la ficha lo avisa y baja la calidad del plano (antes, el recorrido arrancaba en otra estancia y decía que se llegaba a todas).
- **Mesada de la cocina con la puerta del lavadero:** si esa puerta queda junto a una punta de la pared de la mesada, la mesada entra en el resto de esa pared (antes, «no entra la mesada»), sin que la heladera encierre la puerta: desde las puertas y aberturas de la cocina se llega a la heladera y a la mesada. Las demás cocinas no cambian.
- **Pendiente (R5.11):** los rincones sin luz en un codo o detrás de un núcleo (tipo 2) y un toilette en lo que sobra de la franja (tipo 3).

## Novedades v2.41
- **Más artículos de la norma nacional de higiene de la vivienda (R10.8):** la ficha de cada vivienda los comprueba y, si no se cumplen, baja la calidad del plano.
  - **Superficie con muros (art. 3):** junto a la superficie libre, cada vivienda muestra la superficie con muros: hasta la cara exterior del muro de fachada y de la medianera, y hasta el eje de los muros con la vecina, el pasillo común y el núcleo. Por ejemplo, la U01 de la barra tiene 76,2 m² libres y 82,8 m² con muros. Se ve en la ficha, en la tabla de viviendas y al pasar el mouse. Se compara con el mínimo de la norma: 32 m² con un dormitorio, 44 con dos, 56 con tres y 68 con cuatro (12 m² más por cada dormitorio siguiente). El estudio cuenta como dormitorio (art. 6). En el rincón de una L o de un patio, el cuadrado de muro de la esquina se reparte entre las dos viviendas. La superficie libre, la NSA y la eficiencia no cambian.
  - **Monoambiente (art. 2):** su dormitorio y su baño no son locales independientes. Se acepta desde 32 m² con muros (criterio del usuario); con menos, la ficha lo avisa. El hall llega a 1,20 m solo si la cocina conserva su heladera (o si el baño, que conserva la ducha, le deja el ancho). Si el muro del extremo es oblicuo, el baño o el hall de ese lado se ensancha y la puerta de entrada queda siempre dentro de la vivienda.
  - **Cocina integrada al estar sin ventana (art. 27):** Trazo la dibuja con 5 m² como máximo. Primero pierde fondo, que gana el estar: 1,60 m con la mesada en línea, 2,00 o 2,20 m en L y 2,70 m si es muy angosta (la mesada contra la pared del costado). Si aun así pasa de 5 m², se angosta y el hall se agranda. En un monoambiente y en una vivienda poco profunda, donde el baño tiene el mismo fondo que la cocina, primero se angosta: el baño no se achica. Lo que deja la cocina va al baño, hasta 6 m², y después a un depósito que se abre al estar. En la vivienda poco profunda el hall, abierto al estar, queda de 1,40 m para no quitarle la pared del sofá y del rack: si tiene mucho más frente del que su tipo necesita, lo que sobra queda sin uso, con aviso. Si un muro oblicuo corta la cocina, la mesada se prueba en su pared recta. El estar no queda más de 3 veces más profundo que ancho por el fondo que gana. Sus mínimos son 3 m² y 1,40 m de lado. La ventana del estar ilumina también la cocina: el 10 % de los dos locales, con 2 m² como mínimo. Si la agrandas a mano a más de 5 m², la ficha lo avisa.
  - **Profundidad de los locales (art. 14):** se avisa un dormitorio, estar, comedor o estudio más de 3 veces más profundo que su lado menor. También el estar con el comedor interior, medido desde la ventana: en la cruz, la U02 tiene 11,25 m de fondo con 3,00 m de ancho.
  - **Retiro de la divisoria (art. 53 e):** una medianera con un retiro de más de 0 y menos de 1 m se avisa: «pon 0 (adosado) o 1 m o más».
  - **Valores editables** en «Normativa»: «Vivienda → Cocina integrada al estar sin ventana» y «Superficie mínima con muros», «Ventanas → Profundidad máx. / lado menor» y «Predio → Retiro mínimo si se separa de la divisoria».
  - **En los ejemplos** la calidad de planos no cambia. Las cocinas bajan a 5 m² (antes la mitad tenía más de 7 m²) y los estares ganan ese fondo. La «3 dorm» U14 de la cruz (48,3 m² con muros) no llega a los 56 m².
  - **Pendiente:** la ventana en el lado menor o en el primer tercio del mayor (art. 14) y las cocinas con ventana propia, que pueden ser más grandes (art. 24): queda a decisión del usuario.

## Novedades v2.40
- **Grilla y snap (R4.7):** la planta tiene una grilla que se adapta al zoom: la más fina de 10 m, 5 m, 1 m, 0,50 m, 0,10 m y 0,05 m cuyas líneas quedan separadas al menos 12 píxeles. Las líneas marcadas quedan siempre cada 50 m, 5 m o 0,50 m. La barra de dibujo dice qué paso se ve («GRILLA 1 m»), y el zoom llega hasta que 0,05 m se ven bien.
  - **Snap:** todo lo que dibujas o arrastras se pega al paso que se ve: los vértices de las líneas de pasillo, las esquinas de los patios, los núcleos (su centro), los tabiques entre viviendas, los tabiques interiores y las puertas. A menos de 10 píxeles de un vértice de la masa, el punto va al vértice.
  - **SCP:** la grilla y el Orto siguen al edificio, alineados con su fachada principal y con el origen en la esquina del rectángulo que contiene la masa (en una masa con ochava, ese punto queda fuera de ella). Con el botón **SCP**, un clic en un borde de la masa los alinea con ese borde (el extremo más cercano al clic es el origen, como «SCP objeto» de AutoCAD); en la barra que aparece, «Edificio» vuelve al de la masa y «Mundo» a los ejes x, y del plano. El SCP se guarda en el proyecto.
  - **Teclas:** F7 grilla, F8 Orto y F9 snap, como en AutoCAD (en Mac, fn+F7…); con **Alt** apretada, el punto queda libre (sin grilla ni vértices). Trazo recuerda en el navegador si las dejaste prendidas o apagadas.
  - Las medianeras se siguen marcando por borde entero: el snap les llega con su edición en la web (resto de R11.6). Los patios se siguen alineando con la fachada principal de la masa: un patio rodeado de edificio y girado respecto de ella el motor no lo usa.

## Novedades v2.39
- **Ancho del pasillo común tramo por tramo (R10.8):** el ancho general sigue en Circulación → «Ancho pasillo» (2,00 m). Ahora, además, cada tramo puede tener el suyo:
  - **En la web:** haz clic en un tramo de pasillo de la planta. Su ficha muestra el largo del tramo recto, cuántas viviendas sirve por planta y el mínimo de la norma. Escribe el ancho y pulsa «Aplicar»; «Como los demás» lo devuelve al general. Los tramos con ancho propio muestran su medida en la planta, y Circulación dice cuántos hay, con «Quitar». Se guarda en el proyecto y se deshace con Ctrl+Z.
  - **Desde Rhino:** nombra «ancho=1.4» una polilínea de la capa `Trazo::Centerline` y todos sus tramos van con ese ancho.
  - Las viviendas de ese tramo ganan o pierden el fondo que cambia el pasillo; las de los demás tramos no cambian.
- **Art. 35 de la norma nacional:** cada tramo se compara con lo que pide la norma: 1,20 m hasta 3 viviendas, 1,40 de 4 a 10, 1,60 con 11 o más, y 2,00 m si el tramo recto pasa de 15 m. Si no llega, el tramo se dibuja con borde rojo punteado y un aviso lo dice, por ejemplo «Pasillo P2 de 1.40 m: el art. 35 de la norma nacional pide 2.00 m en un tramo recto de más de 15 m (este mide 32.6 m)…». Los valores se cambian en «Normativa → Núcleo». Con 2,00 m, ningún ejemplo tiene avisos.
- **Corrección:** entre medianeras con núcleos manuales, los pasillos que llegan a las viviendas medían siempre 2,00 m aunque cambiaras el ancho general.
- **Si cambias la planta o las líneas** y un ancho se queda sin tramo, el aviso lo dice y Circulación ofrece «Quitar los que no tienen tramo», que borra solo esos.
- Para la norma, un tramo recto es el pasillo que sigue derecho aunque esté dibujado en partes: con un vértice intermedio (aunque esté corrido unos centímetros), una línea cortada en un cruce o una T dibujada como una L más el brazo que falta. En edificios sin viviendas (oficinas, comercio, cocheras) el art. 35 no se aplica. En la etapa «Pasillo y núcleos» el mínimo es 1,20 m «por ahora»: se precisa al repartir las viviendas.
- **Corrección:** en plantas en L, U o Z de alas angostas (o con el pasillo más ancho), el núcleo de una punta podía quedar con la escalera o el ducto encima del pasillo del ala que llega; ahora va al otro lado del pasillo. Ningún ejemplo cambia.
- **Correcciones de la web:** con una vivienda elegida, «Generar pasillo y núcleos» dejaba la planta sin dibujar; el clic derecho sobre un vértice de una línea de pasillo no lo borraba; una variante o un proyecto guardados cambiaban si después se editaban los anchos o las líneas.
- Sin anchos propios, los ejemplos dan exactamente la misma planta que antes.

## Novedades v2.38
- **Vestidor opcional (R5.10):** cada tipo del mix tiene una casilla **Vest.**, apagada por defecto. Sus viviendas llevan un vestidor de todo el ancho del dormitorio principal, entre el pasillo interno y el dormitorio. El dormitorio sigue con su ventana a la fachada, abierto al vestidor, y ya no lleva placard: el vestidor tiene estantes en sus paredes libres.
  - **Con la suite:** el vestidor queda entre el dormitorio y su baño, en la parte del dormitorio que no tenía luz. Se entra desde el pasillo y desde el vestidor al baño. Si el tipo lo pide, la suite se arma aunque no sobre franja, siempre que los demás dormitorios no pierdan fondo; el depósito puede no entrar, porque el vestidor guarda.
  - **Sin la suite:** el vestidor va a la entrada del dormitorio (pasillo → vestidor → dormitorio).
  - **Medidas:** 1,50 m de fondo, o hasta 1,20 m para que el dormitorio conserve su medida mínima y la cama doble con su paso al pie. Se cambian en «Normativa → Vivienda → Vestidor».
  - **Si no entra o el plano empeora:** no se agrega y la ficha dice por qué, por ejemplo «Vestidor: no entra (el dormitorio principal tiene 3.50 m de fondo y necesita 3.86 m…)». En los ejemplos entra en casi todas las de 3 dormitorios (van en suite); en las de 1 y 2 dormitorios, solo si el dormitorio principal tiene unos 3,90 m de fondo o más.
  - En Rhino va a la capa `Trazo::L00::Rooms::vestidor` y en el DXF a `Trazo_L00_Rooms_vestidor`.

## Novedades v2.37
- **Interfaz por grupos (R4.6, la opción B, «Riel», que elegiste en la maqueta):**
  - **Riel de la izquierda:** Proyecto, Masa, Circulación, Viviendas, Normativa y Vista. Cada uno abre su panel al lado, de a uno, con su botón de generar al pie. La planta usa el resto de la pantalla y Trazo recuerda qué grupo estaba abierto.
  - **Sobre la planta:** 2D o 3D, el nivel y el menú **Capas**.
  - **Abajo, una barra de dibujo como la de AutoCAD:** Línea, Núcleo, Medianera, Patio y **Orto (F8)**. La herramienta activa muestra qué hacer y sus botones (Terminar, Borrar última, Quitar núcleo…), y Esc la cierra.
  - **Arriba:** lo que está abierto, su etapa, y deshacer y rehacer.
  - **A la derecha:** el resumen (unidades, NSA, eficiencia, calidad de planos, núcleos, ascensores), los avisos y la ficha. **Ver todo** suma programas, métricas y unidades.
  - «Muro medianero» pasa a llamarse **«Muro entre viviendas»**, para no confundirlo con las medianeras del predio.
  - Cada control conserva su id: los proyectos y las variantes guardados se abren igual.
  - En el teléfono, el riel va arriba y el resumen debajo de la planta.
  - La grilla y el snap con F7 y F9 llegaron con R4.7 (v2.40).

## Novedades v2.36
- **Datos al pasar el mouse:** sobre la planta aparece, sin hacer clic, un recuadro con el nombre y la superficie de lo que está debajo. Muestra la estancia y su vivienda («Dormitorio principal · 11.2 m²», «U03 · 2 dorm · 84.1 m²»), lo sin uso, cada parte de un núcleo (escalera, ascensor) con sus ascensores, el pasillo común, las zonas sin luz y los patios. En los niveles de oficinas, comercio o estacionamiento muestra sus partes, por ejemplo una plaza. Se apaga con «Datos al pasar», en la barra de la planta, y no aparece mientras se dibuja o se arrastra. El clic sigue abriendo la ficha.

## Novedades v2.35
- **Terreno rectangular sin Rhino:** en «1 · Masa → Terreno rectangular» se cargan el frente y el fondo del terreno, qué linderos son medianeras (izquierdo, derecho, de fondo) y los retiros de cada lado y del frente. «Crear masa del terreno» arma la masa:
  - los linderos sin medianera y el frente se descuentan de la masa;
  - las medianeras van con su retiro: sin retiro son ciegas y con retiro de 3 m o más pasan a ser fachada.

  La planta muestra el contorno del terreno (raya y punto) y las cotas de los retiros. El terreno se guarda en el proyecto y en las variantes, y vuelve a la lista de ejemplos como «Terreno 10 × 30 m».

## Novedades v2.34
- **El pasillo común termina en la última puerta (R3.7):**
  - **Punta de un pasillo de borde sin núcleo** (por ejemplo, un predio con una sola medianera y el núcleo atrás, puesto a mano): la vivienda del extremo toma todo el ancho del frente, entra por la punta del pasillo y las viviendas se reparten parejas. Al frente va el tipo de menos dormitorios del tramo, con un fondo de hasta 9,25 m (el que el plano aprovecha sin dejar una tira sin uso). En el predio de 10 × 28 con 100 % de «2 dorm», el pasillo deja de llegar a la fachada (10 m² menos por planta) y las dos viviendas quedan de 86 y 88 m², con calidad 100. La eficiencia pasa de 60,7 a 68,5 % y el fondo de saco de la última, de 19 a 15 m.
  - **Punta después de un cruce:** en las L, el pasillo del ala larga seguía 6,65 m después del cruce hasta la fachada sin servir a ninguna puerta. Ahora la franja de viviendas del ala vecina cruza ese tramo, y la vivienda del otro lado entra por el pasillo que queda. En la L, 10 viviendas por planta en lugar de 9 (match 94 → 100). En la L con ochava, la calidad de planos pasa de 87 a 95. En las dos, la eficiencia sube 1,1 puntos.
  - **Lo que no cambia:** las puntas con núcleo, el anillo del patio central (del otro lado del pasillo hay otra ala) y los paliers del predio entre dos medianeras siguen como estaban (anotado en el ROADMAP).
  - Una vivienda al frente se marca `al_frente` en el resultado. Se puede editar como las demás: al arrastrar su tabique, el pasillo lo sigue.

## Novedades v2.33
- **Sin placards como habitación:** el placard es el armario de 0,60 m que se dibuja dentro de cada dormitorio. La franja sin luz entre el pasillo interno y el pasillo común lleva los baños (con ducha), el lavadero y un solo depósito de hasta 4 m² (editable en «Medidas y normativa → Vivienda»; 0 = sin depósito), con el fondo justo para que entren: los dormitorios ganan fondo (3,50 a 3,70 m en una vivienda de 6,50 m, antes 3,10). Si sobra franja, el dormitorio principal pasa al final del pasillo, en suite, con su baño; si no se puede, baños y lavadero más grandes; y si aún sobra, queda rayado como «Sin uso», con un aviso en la ficha (también en Rhino, `Trazo::L00::SinUso`, y en el DXF). El pasillo interno termina en la última puerta. Un rincón sin luz de más de 4 m² ya no es un depósito: queda sin uso, con aviso; la ochava, con su fachada oblicua, es un estudio con ventana. En los 13 ejemplos, placards y depósitos ocupaban el 8,4 % de la superficie vendible (846 m² por planta): ahora, depósitos de hasta 4 m² (336 m²) y 98 m² sin uso. La calidad de planos sube en la L (84 → 94), la L con ochava (80 → 87), la L con polilínea (89 → 100), el quiebre a 45° (88 → 95) y la cruz (46 → 50); baja en «Patio central» (90 → 83) por lo que queda sin uso en sus viviendas de 10 m de fondo.

## Novedades v2.32
- **Ascensores por núcleo (R10.7):** cada núcleo lleva los ascensores que piden las viviendas que sirve (1 cada 60), y en automático todos los núcleos son iguales. Antes, la cantidad calculada para todo el edificio se ponía en cada núcleo: la cruz de 70 viviendas y 4 núcleos llevaba 8 ascensores, y ahora lleva 4. Desde 10 niveles el edificio lleva al menos 2 en total (el mínimo es por edificio); si se fijan menos a mano, se avisa. Se fijan en la ficha de cada núcleo (0 = solo escalera), para todos en «Ascensores por núcleo» o desde Rhino (punto llamado `ascensores=2`). En los ejemplos con varios núcleos, los núcleos son 1,90 m más angostos y crece la superficie vendible: «T con 2 polilíneas» +217 m² (2 viviendas más por planta; su calidad de planos baja de 62 a 47 porque el mix arma viviendas de 3 dormitorios de menos frente), «Barra larga 90x18» +299 m² y la cruz +247 m².

## Novedades v2.31
- **Medianeras parciales (R11.6, primera parte):** una medianera que ocupa solo parte de un borde retira la huella solo a lo largo de su tramo, y la huella queda escalonada. Antes, una medianera parcial con retiro retiraba el lado entero: en un predio de 20 × 30 m, una de 10 m con 3 m de retiro dejaba 510 m² en vez de 570. Hoy las medianeras parciales se dibujan en Rhino (capa `Trazo::Medianeras`); marcarlas en la web es la segunda parte de R11.6. Los ejemplos no cambian.

## Novedades v2.30
- **Baño y cocina:** una vivienda sin baño o sin cocina baja su calidad de planos y la ficha lo avisa («Sin cocina: toda vivienda lleva una»). La cocina dentro del hall cuenta. Antes, una vivienda chica sin lugar para la cocina podía sacar 100. En los ejemplos, «Entre medianeras 30 × 45 con patio central» baja de 100 a 94: su vivienda U08, de 3 dormitorios, no tiene cocina.

## Novedades v2.29
- **El dormitorio principal conserva su placard:** al repartir el frente entre los dormitorios, el principal conserva el ancho de su cama doble con el placard de 0,60 m al costado (3,20 m con las medidas por defecto) cuando el fondo no deja ponerlo al pie de la cama, siempre que los demás dormitorios lleguen a su mínimo. Si el frente no alcanza, los demás no bajan de su mínimo y la ficha avisa que el placard no entra. En los ejemplos, «Predio entre medianeras 10 × 40» vuelve de 22 a 30 en calidad de planos: en U01 y U03 el dormitorio principal queda de 3,20 × 3,00 m con su placard y el segundo de 2,57 × 3,00 m (7,7 m²).

## Novedades v2.28
- **Segunda fachada:** con 3 dormitorios o más, el dormitorio al costado ya no deja la vivienda con un solo baño; con hasta 2 dormitorios sigue pudiendo (criterio del usuario). En los ejemplos, «T con 2 polilíneas» baja de 67 a 62 en calidad de planos: su vivienda U06, de 3 dormitorios en 9,10 m de frente, vuelve a tener los dormitorios al fondo, con dos baños. El ROADMAP registra tus decisiones: la norma nacional rige en todos los departamentos (R10.1 y R11.5 hechas), monoambientes desde 32 m², mínimo de 2 ascensores por edificio y, en la esquina, el estar o el dormitorio principal según cómo se conecte por dentro.

## Novedades v2.27
- **Normativa nacional de higiene de la vivienda:** los mínimos de la vivienda siguen la Normativa Nacional de Edificación (Congreso de Intendentes, MVOTMA y SAU, 2016): dormitorio principal de 8,5 m² con lado de 2,60 m, dormitorios adicionales y estudio de 7 m², estar de 10 m² con lado de 2,60 m y baño de 3 m². La misma norma confirma el vano de iluminación de 1/10 del local y el retiro de 3 m para abrir ventanas. Las medidas que cambiaste en la web se conservan; un mínimo que el navegador o un proyecto anterior guardó con su valor viejo pasa al nuevo. En los ejemplos solo cambia la calidad de planos: «Forma en L» 87 → 84, «Predio entre medianeras 10 x 28» 58 → 60, «Predio entre medianeras 10 × 40» 30 → 22 y «Cruz con 2 polilíneas» 44 → 45. Artículos y fuentes en `STANDARDS.md`; lo que la norma pide y Trazo todavía no comprueba, en el ROADMAP (R10.8 y R11.2).

## Novedades v2.26
- **Segunda fachada (R5.3):** las viviendas de esquina o de extremo usan la fachada lateral. Si el frente alcanza, el estar va a la esquina con luz y ventana por dos fachadas; si no alcanza para todos los dormitorios al fondo, el último va al costado con su ventana, solo si el plano mejora y no pierde estancias (puede quedar un solo baño). Toda estancia de esquina lleva ventana en las dos fachadas. En los ejemplos, «T con 2 polilíneas» sube de 61 a 67 en calidad de planos (una vivienda de 3 dormitorios con frente corto ya cumple los mínimos); los demás no cambian.

## Novedades v2.25
- **Ventanas (R5.5):** cada estancia habitable con fachada lleva su ventana en el muro exterior, del ancho típico (1,50 m en dormitorios y 2,00 m en el estar) o del que pida el vano mínimo (10 % de la superficie del local, Digesto de Montevideo); si no alcanza, otra en la fachada lateral, y si no llega, un aviso en la ficha. El comedor sin fachada se ilumina por el estar. Junto a una esquina entrante, la ventana no se mete en el muro de la otra ala. Se dibujan en la web, en Rhino (`Trazo::L00::Ventanas`) y en el DXF; las medidas se cambian en «Medidas y normativa → Ventanas».

## Novedades v2.24
- **Editar la vivienda por dentro (R5.7):** con una vivienda elegida, sus tabiques interiores (en verde) y sus puertas (en naranja) se arrastran en la planta: un tabique agranda una estancia y achica la vecina (cada una conserva al menos 0,60 m) y una puerta se corre a lo largo de su pared. En la ficha, cada puerta tiene su ancho y **⇄** para que abra hacia el otro lado. Los artefactos, los muebles y las comprobaciones se recalculan. Se deshace con Ctrl+Z, se guarda con el proyecto y las variantes, y «Descartar los cambios por dentro» vuelve a la distribución automática. Los cambios que ya no entran se avisan.

## Novedades v2.23
- **Vivienda accesible por tipo del mix (R5.6, tercera parte):** cada tipo del mix tiene una casilla **Acc.** Sus viviendas llevan puertas de 0,82 m en dormitorios y baño; el baño principal es más ancho, abre hacia afuera y lleva ducha a nivel, inodoro con 0,80 m de transferencia al costado, lavatorio y un círculo de giro de 1,50 m libre (puede pisar la ducha, que está a nivel), sin bidé. Si el baño no llega, la ficha lo avisa y queda el baño común. Se guarda con el proyecto; las medidas son editables.

## Novedades v2.22
- **Muebles de dormitorios, estar y comedor (R5.6, segunda parte):** el dormitorio principal lleva cama doble con mesas de luz, 0,60 m libres a los lados y al pie, y placard de 0,60 m de fondo; los demás, dos camas individuales con una mesa de luz entre ellas (o una cama, con aviso). El estar lleva un sofá frente al rack de TV (a 1,50 m o más) y butacas si entran; la mesa del comedor, 4 asientos y 2 más por cada dormitorio después del primero. Nada va delante de las aberturas al hall, al pasillo o a la cocina, el placard y el rack no van contra una ventana, y desde la puerta se llega a todo. La puerta de un dormitorio se corre a una esquina cuando así entran mejor los muebles. Lo que no entra se avisa en la ficha (salvo en estancias que ya no llegan a su medida mínima). Todo es editable y va a Rhino y al DXF.

## Novedades v2.21
- **Equipamiento de baños, cocina y lavadero (R5.6, primera parte):** los planos dibujan inodoro, bidé, lavatorio y ducha; mesada de 0,60 m con heladera, bacha y cocina; lavarropas y pileta. Cada artefacto va contra una pared maciza, con su paso libre y sin pisar el barrido de las puertas. Lo que no entra se avisa en la ficha. Las puertas interiores pasan a 0,70 m (la de entrada, 0,90 m), editables. También va a Rhino y al DXF.
- Los baños y el lavadero toman el ancho que necesita su equipamiento (por ejemplo, el segundo baño pasa de 1,20 a 1,30 m) y la puerta de un baño se ubica junto a la esquina cuando así entran todos los artefactos.

## Novedades v2.20
- **Editar viviendas (R4.4):** con una vivienda elegida, sus tabiques (en azul) se arrastran para mover el límite con la vecina, y su ficha tiene **Dividir en dos** y **Unir con…**. Los planos, la evacuación y las métricas (match, eficiencia) se recalculan; las editadas llevan ✎. Los cambios se deshacen con Ctrl+Z, se guardan con el proyecto y las variantes, y se descartan con «Descartar cambios».

## Novedades v2.19.1
- **Corrección: aviso de ancho mínimo.** Con un decimal, una vivienda de 4,98 m avisaba «Unidad con ancho 5.0 m < mínimo 5.0 m», que parecía un error. Ahora muestra dos decimales («4.98 m < mínimo 5.00 m»), igual que el ancho de las estancias en la ficha de la vivienda.

## Novedades v2.19
- **Variantes (R4.5):** «Guardar como variante» guarda la solución actual y «Comparar» las muestra en una tabla (unidades, NSA, eficiencia, match, circulación, sin usar, núcleos, evacuación y calidad de planos), con lo mejor de cada columna en verde. Desde la tabla se abre, renombra o borra cada variante, y se copia la tabla para una planilla. Las variantes van en el archivo del proyecto.

## Novedades v2.18
- **Arrastrar núcleos (R4.3):** un núcleo se mueve arrastrándolo en la planta. Se ve dónde va a quedar, Trazo lo ajusta al pasillo del lado donde lo sueltas y recalcula. Si eran automáticos pasan a manual, sin mover los demás. Se deshace con Ctrl+Z.

## Novedades v2.17
- **Deshacer y rehacer (R4.2):** botones ↶ ↷ arriba de la planta y Ctrl+Z / Ctrl+Shift+Z (Cmd en Mac; también Ctrl+Y). Sirven para polilíneas, vértices, núcleos, medianeras y patios, y la planta se recalcula sola.
- **Corrección:** «Quitar núcleo» en modo automático pasaba a modo manual pero no quitaba el núcleo, por más clics que se hicieran. Ahora quita el núcleo tocado.

## Novedades v2.16
- **Guardar y abrir proyectos (R4.1):** botones **Guardar proyecto** y **Abrir proyecto…**, junto a «Nuevo». El archivo (`nombre.trazo.json`) guarda la masa, las polilíneas, los núcleos, las medianeras, los patios, el mix, los parámetros, las medidas que cambiaste y la etapa; al abrirlo, la planta vuelve igual. Si el proyecto se guardó con otra versión de Trazo, avisa que el resultado puede variar.
- «Abrir proyecto…» también abre una masa suelta (como los ejemplos de `samples/`), y avisa con claridad si el archivo es un resultado exportado o no es de Trazo.
- El botón «JSON» de «Exportar» ahora se llama **Resultado (JSON)**, para no confundirlo con el proyecto.

## Novedades v2.15
- **Corrección: núcleos encimados.** En plantas con varias alas (por ejemplo, una T o una L con un patio), dos puntas de pasillo cercanas ponían cada una su núcleo, y quedaban encimados: en formas al azar, hasta 60 m² de núcleo pisado. Ahora el segundo núcleo se corre hasta no pisar al primero o, si no entra, el primero sirve a las dos puntas. La evacuación de las viviendas no empeora en ningún caso.
- Si pones a mano dos núcleos que se pisan, quedan donde los pusiste y se avisa: «El núcleo N se superpone con otro: muévelo o quítalo».

## Novedades v2.14
- **Reglas de evacuación (R3.6):** cada vivienda se revisa con dos reglas, editables en el panel:
  - **Recorrido máximo:** por defecto 30 m desde la puerta hasta el núcleo más cercano, por el pasillo.
  - **Fondo de saco máximo:** por defecto 18 m. Es el tramo desde la puerta en el que solo se puede salir en una dirección, hasta llegar a un núcleo o a un punto desde el que se sale en dos. Un pasillo que da la vuelta a un patio da dos direcciones aunque las dos lleguen al mismo núcleo.
- Antes, entre 18 y 30 m la vivienda quedaba «en duda» (punto gris) sin revisar si tenía dos salidas. Ahora se sabe:
  - en los 259 casos de la comparación, 184 de esas viviendas cumplen (tienen dos direcciones) y 23 no (fondo de saco largo).
- Las que no cumplen se ven en la planta, con la casilla **Evacuación** encendida: la puerta y el contorno de la vivienda en **naranja** (fondo de saco) o **rojo** (recorrido), y los tramos de pasillo que no cumplen resaltados con el mismo color. Además:
  - se avisan una por una, con su distancia (por ejemplo «Fondo de saco: U06 (20 m)… agrega un núcleo o une el pasillo»);
  - en la ficha de la vivienda aparecen el recorrido y el fondo de saco.
- Los ejemplos de `samples/` cumplen y no cambian.

## Novedades v2.13
- **Núcleos con medidas propias y giro (R3.5):** un clic sobre un núcleo en la planta abre su ficha. Ahí cambias su **frente** (a lo largo del pasillo), su **fondo** (desde el pasillo) y su **giro**:
  - **0°:** como siempre, la escalera sube perpendicular al pasillo.
  - **90°:** la escalera sube a lo largo del pasillo. El núcleo queda más ancho y menos profundo (por ejemplo 7,7 × 3,6 m en lugar de 5,5 × 5,0 m), útil en alas de poco fondo.
  - **Medidas por defecto** vuelve a las de la normativa para ese giro; **Quitar** saca el núcleo.
  - Si eliges un fondo propio, el núcleo no se estira hasta la fachada: lo que queda detrás se suma a la vivienda vecina.
  - Al editar un núcleo automático, los núcleos pasan a modo manual, como al añadir o quitar uno.
- Rhino sigue mandando los núcleos como puntos (con las medidas por defecto) y dibuja al recibir los núcleos con su forma y su giro.

## Novedades v2.12
- **Plantas no ortogonales (R3.4):** una masa que no es ortogonal (una barra con un quiebre, un ala girada, el tallo oblicuo de una T, o una L, T o U con ochavas) ya no recibe un solo pasillo recto para toda la planta. Se divide en alas y cada ala tiene su propio pasillo a lo largo, que se encuentra con el de la otra en el quiebre (a inglete) o llega a él como una T. Las ochavas y los lados inclinados cortos solo recortan el ala.
  - En «Barra con quiebre a 45°»: antes 4 viviendas, todas a oscuras, con 18 % de eficiencia («Solo el 18 % de la planta está servido»); ahora 10 viviendas con plano completo y 74,6 %.
  - En «Esquina en L con ochava»: de 4 viviendas y 38 % a 10 viviendas y 72,6 %.
  - En formas al azar con quiebres, T oblicuas, Y y ochavas, la superficie de viviendas con plano completo (calidad 80 o más) pasa de casi nada a unos 560-770 m² por planta, y las viviendas a oscuras, de 2,4-5 a menos de 1 por caso (las que quedan dan a una medianera).
- Las plantas convexas (trapecio, paralelogramo, pentágono) siguen con un solo pasillo, como antes, y las formas ortogonales no cambian.
- En un ala con un extremo inclinado, el núcleo se corre hasta donde entra entero (antes podía quedar recortado por el borde).
- Las cotas de la planta van en la dirección del rectángulo más chico que la contiene: en una forma no ortogonal podían quedar giradas y lejos del dibujo.
- Ejemplos nuevos: «Barra con quiebre a 45° (no ortogonal)» y «Esquina en L con ochava».

## Novedades v2.11
- **Corrección: lavadero «sin acceso».** Un lavadero de 0,90 m de ancho (justo lo que pide su puerta) a veces quedaba «sin acceso desde la entrada», según dónde estuviera la vivienda en la planta: un error de redondeo hacía que midiera 0,8999… m. Esas viviendas tenían puntaje 0 en su plano sin un problema real; en formas al azar, 1 de cada 10. En «T con 2 polilíneas», la calidad de planos pasa de 17 a 61.

## Novedades v2.10
- **Pasillos dibujados que se cruzan (R3.3):** dos polilíneas que se cruzan en X ya no ponen viviendas encimadas (en una planta en cruz, unos 500 m² de viviendas se pisaban entre sí y otros 110 m² con pasillos y núcleos). En cada cruce, la línea más larga sigue de largo y la otra se corta en dos; cada mitad se une a la primera como una T. Si una línea pasa del otro lado menos de 4,5 m (el sobrante típico al dibujar una T), ese resto se quita.
- También sin solapes en pasillos dibujados: el codo de una polilínea cuando la planta se ensancha en la esquina, las ramas de una U muy cercanas, el bolsillo detrás de un núcleo junto a otro pasillo y dos núcleos en la misma punta. Un ramal oblicuo ya no bloquea viviendas de más en el pasillo al que llega. En 350 casos al azar con cruces, T, L y U dibujadas, la superficie encimada pasa de unos 218 000 m² (en 258 casos) a prácticamente cero (menos de 1 m² en total).
- La evacuación pasa por las uniones de pasillos dibujados en los dos sentidos: desde el pasillo principal se puede salir por el núcleo de un ramal (en «T con 2 polilíneas», la distancia máxima a un núcleo baja de 26,3 a 16,0 m). En «L con polilínea», dos viviendas del codo se pisaban 3,6 m²: ya no (la eficiencia pasa de 72,7 % a 72,3 % porque ese tramo contaba dos veces).
- Si algo todavía se pisa (por ejemplo, con tres líneas que se cruzan en un mismo punto), la vivienda se recorta o, si pierde más de la mitad, se quita y se avisa.
- Ejemplo nuevo: «Cruz con 2 polilíneas que se cruzan (X)».

## Novedades v2.9
- **Codos más eficientes (R3.2):** en el codo de una L, una T o una U (y en las esquinas de un patio), las viviendas que daban a otra ala quedaban con dormitorios sin ventana: en formas L, T y U al azar, casi 1 de cada 5. Ahora:
  - donde no llega la luz no se ponen viviendas; si el pasillo tiene una punta corta junto al codo, su núcleo va a esa esquina interior (que no necesita luz) y la esquina exterior, con dos fachadas, queda para las viviendas;
  - la franja de viviendas del ala que llega baja hasta el pasillo de la otra cuando su fondo sigue dando a la fachada;
  - lo que queda sin luz se ve rayado como «Sin luz natural» y se avisa («Esquinas sin luz natural»): no es superficie desperdiciada, es la que no recibe luz (para núcleos, ductos o depósitos);
  - en el plano de cada vivienda, las estancias habitables van bajo la parte del fondo que tiene luz y el resto queda como depósito.
- En el ejemplo «Forma en L»: ninguna vivienda a oscuras (antes 1), 0 m² sin usar, calidad de planos 94 (antes 88) y 17,4 m de evacuación máxima (antes 21,4), con 72,1 % de eficiencia (antes 71,8 %). En formas T y U la eficiencia baja (de 71 a 64 % y de 72 a 67 % en promedio) porque ya no cuenta viviendas inválidas: la superficie de viviendas **con luz** sube un 11 %.

## Novedades v2.8
- **Sin restos sueltos en las puntas (R3.1):** cuando el pasillo (por ejemplo, una polilínea dibujada) termina antes de la fachada, el núcleo de esa punta dejaba una franja de 1 a 4 m hasta el borde, demasiado chica para una vivienda, que quedaba sin usar. Ahora el núcleo se apoya contra la fachada y la vivienda del otro lado del núcleo crece en su lugar. Solo si el núcleo ya llega a la fachada (si detrás le queda un bolsillo, franja y bolsillo ya forman una vivienda) y si la evacuación sigue dentro del máximo. En el ejemplo «L con polilínea», la eficiencia pasa de 69,8 % a 72,7 %; en «T con 2 polilíneas», de 69,9 % a 70,7 %.

## Novedades v2.7
- **Corrección de geometría (R2.2):** cuando un corte separaba una figura cóncava en dos (por ejemplo, una masa con una muesca en V, o un predio en C en el Masterplan), las dos partes quedaban unidas por una línea de ancho cero: una vivienda o un pasillo de dos piezas, o una manzana doble. Ahora cada parte sale por separado: el pasillo que cruza una muesca se dibuja en dos tramos y cada manzana y cada lote son una sola figura.
- Por dentro, el motor quedó repartido en módulos (R2.1: `massing.py`, `circulation.py`, `units.py`, `patios.py`), sin cambiar ningún resultado.

## Novedades v2.6
- **Patios rodeados de edificio (U cerrada o claustro):** un patio dibujado dentro de la masa, sin tocar el borde, ya se usa (antes avisaba y lo ignoraba). El edificio queda como un anillo alrededor del patio, dividido en alas, con un **pasillo que da la vuelta al patio**: se puede evacuar hacia los dos lados, así que no hace falta un núcleo en cada esquina (van los de «Cantidad» y los que pida la evacuación; una punta de pasillo de hasta 18 m no necesita núcleo propio).
- Las viviendas que dan al patio tienen luz si mide al menos 3 m. En alas de poco fondo, pasillo de borde (hacia el patio o contra la medianera) para que las viviendas no queden playas. En las esquinas interiores, donde no llega la luz, no se ponen viviendas (quedan «sin usar»; las unidades de esquina llegan con la mejora de codos, R3.2).
- En la planta el patio se ve como un hueco del edificio, con sus cotas; en la axonometría, con sus caras interiores. Ejemplos nuevos: «Edificio con patio central 40 × 30» y «Entre medianeras 30 × 45 con patio central (U cerrada)».
- **Corrección:** con coordenadas grandes (UTM, planos georreferenciados) el centro y el área de los polígonos perdían precisión (hasta 5 m), y un patio interior podía no reconocerse.
- Todavía no: patios interiores en masas que no son ortogonales o patios girados respecto de la masa (avisa y no lo usa), y polilíneas dibujadas en un bloque con patio interior (avisa y traza el pasillo solo).

## Novedades v2.5
- **Recibir sin duplicar (Rhino):** si el archivo ya tiene un resultado de Trazo, Recibir dice cuántos objetos hay y en qué capas, y pregunta: **Reemplazar** (borra el anterior, también lo oculto, bloqueado o en capas apagadas, y dibuja el nuevo), **Agregar** (deja los dos) o **Cancelar** (no cambia nada). Al reemplazar, también quita las capas de los niveles que ya no existen (por ejemplo, al pasar de 10 a 5 pisos). Solo toca las capas de resultado (`Trazo::Footprint` y `Trazo::L00…`), nunca las que usas para enviar.
- Los patios recibidos se dibujan en cada nivel (`Trazo::L00::Patios`…) y no en `Trazo::Patios`: antes, al volver a enviar, se mandaban repetidos y un patio automático pasaba a manual.
- **Diagnostico** muestra si el archivo ya tiene un resultado dibujado.

## Novedades v2.4
- **Patios de aire y luz en el modo Edificio:** la masa menos los patios da uno o más **bloques**, cada uno con su muro exterior, su pasillo, **su propio núcleo** y sus viviendas; el mix se reparte entre todos los bloques.
- **Automáticos:** en un predio entre medianeras demasiado profundo (antes quedaba una «zona central sin luz»), Trazo lo divide en bloques iguales separados por patios del ancho mínimo, con la solución típica en cada bloque: núcleo en el medio y una vivienda hacia cada lado (la calle o el fondo, y el patio). Ejemplo nuevo: «Predio entre medianeras 10 × 40 (patio automático)».
- **Manuales:** **Patio** en la barra de dibujo (dos clics en esquinas opuestas, o un clic y el ancho y el fondo escritos), lista de patios con su medida y botón para quitarlos; desde Rhino, curvas cerradas en la capa `Trazo::Patios`.
- **Luz por el patio:** las estancias que dan a un patio de al menos 3 m (editable) cuentan como iluminadas; si es más angosto, avisa y sus caras se tratan como medianera.
- En la planta, los patios se ven rayados y acotados (cotas parciales de bloques y patios); en la axonometría cada bloque es un volumen; métricas «Bloques» y «Patios (m²)»; el GFA no cuenta los patios.
- Todavía no: patios rodeados de edificio por los cuatro lados (avisa y no se usan) y alturas distintas por bloque.

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
- **Medianeras y retiros:** **Medianera** en la barra de dibujo y clic sobre los bordes de la planta (líneas rojas). Cada medianera tiene un retiro: con 0 m (adosado) no admite ventanas; con un retiro ≥ 3 m (editable en «Normativa → Predio») el edificio se retira y esa cara pasa a ser fachada.
- El motor lo usa: estancias contra medianera no cuentan como iluminadas; con una medianera larga el pasillo se apoya contra ella; en un **predio entre medianeras** (los dos lados largos ciegos) arma la solución típica: franja central con núcleo contra la medianera y hall, y una vivienda hacia cada frente con todo el ancho del predio.
- Desde Rhino: curvas en la capa `Trazo::Medianeras` (nombre del objeto `retiro=3` para indicar retiro).
- Ejemplo nuevo: «Predio entre medianeras 10 × 28».

## Novedades v1.7
- **Medidas reales** (`engine/standards.py`, `STANDARDS.md`): mínimos normativos y medidas típicas por estancia, núcleo, oficinas, comercio y estacionamiento. Editables en la web («Normativa») y guardadas en el navegador.
- **Vivienda:** dormitorios, baños, cocina, lavadero, pasillo y hall se dimensionan con esas medidas; la ficha de la unidad marca lo que no llega al mínimo (⚠), lo que queda bajo el típico (ℹ) y si la superficie sale del rango ANV.
- **Núcleo real:** caja de escalera de ida y vuelta (contrahuellas según altura de piso), ascensores accesibles (ducto 1,75 × 1,95) con palier, ducto de instalaciones; nº de ascensores según altura y unidades; tipo de escalera según altura (común, protegida, presurizada). Se dibuja en planta y en 3D.
- **Oficinas y comercio:** hall de acceso, batería de baños (mujeres, hombres, accesible) según Dec. 406/988 y el resto como planta libre.
- **Estacionamiento:** plazas de 2,50 × 5,00 en peine con calles de 6,00 m y calle transversal; cuenta de plazas.
- Ejemplo nuevo: «Barra mixta» (estacionamiento + comercio + oficinas + vivienda).

## Novedades v1.6
- **Colores por programa, editables:** cada programa tiene su color (clic en el cuadrado de color en «Programas», dentro de «Ver todo», o en «Vista → Colores de todos los programas»). Se guardan en el navegador; «Restaurar colores» vuelve a los de fábrica.
- **Áreas internas en tonos del programa:** dentro de Residencial, cada tipo de estancia (dormitorio, estar, cocina, baño, pasillo…) y cada tipo de unidad usa una gama del mismo color. Pasillos y núcleos usan tonos de Circulación. La leyenda muestra la gama.

## Novedades v1.5
- **Axonometría 3D** (botón «Axonometría 3D»): niveles coloreados por programa, girar arrastrando o con ⟲ ⟳, vista explotada con la planta de cada nivel, aislar selección y modo alambre.
- **Selección de niveles** como en un estudio de masas: clic, Shift (rango), Ctrl/Cmd (sueltos), o por función desde el gráfico de anillo «Programas». Panel para cambiar programa y altura (y crear programas nuevos). Doble clic abre la planta 2D de ese nivel.
- **Conexiones dentro de la vivienda** (`engine/plans.py`): zona de día (hall, cocina, estar-comedor) y zona de noche (pasillo interno, dormitorios a fachada, baños, lavadero), puertas y grafo de conexiones (abierto/puerta). Comprobaciones por unidad: acceso desde la entrada, dormitorios y estar con fachada, anchos mínimos y frente mínimo según nº de dormitorios. Clic en una unidad para ver su ficha; «Calidad de planos» en las métricas.
- Mix con columna «Dorm.» (vacío = según m²). Zoom con la rueda y desplazamiento arrastrando en la planta.
- Puertas exportadas a Rhino y DXF (capa `Doors`).

## Novedades v1.4
- **Polilíneas** como líneas centrales: varias líneas, giros, empalmes en T. Se dibujan en la web (clic por vértice, o el largo y el ángulo escritos; Enter o doble clic para terminar), se editan arrastrando los vértices y se borran con clic derecho.
- **Núcleos manuales**: **Núcleo** en la barra de dibujo (y «Quitar núcleo» en la barra que aparece) en la web; se ajustan al pasillo más cercano. Modo automático o manual.
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
