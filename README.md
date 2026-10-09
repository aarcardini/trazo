# Trazo

**Trazo** (antes «Finch Local») es una herramienta local de estudio de planta tipo, inspirada en el flujo público de herramientas como Finch3D (masa → planta → pasillo y núcleos → mix de unidades → planos de unidad). Es una implementación propia: no contiene código, datos ni marcas de terceros.

## Requisitos
- Python 3.9 o superior (sin librerías externas).
- Rhino 8 en Mac o Windows (para el puente). La web funciona sola, sin Rhino, con los ejemplos.
- Para desarrollar con Claude Code: ver `CLAUDE.md` y `ROADMAP.md`.

## Uso
1. En una terminal: `python server.py` y abre http://127.0.0.1:8765
2. En Rhino 8: comando `RunPythonScript` y elige `rhino/trazo_rhino.py`.
   - **Enviar**: selecciona tu masa (sólido cerrado). Aparece sola en la web.
   - Para controlar el pasillo, dibuja polilíneas en la capa `Trazo::Centerline` antes de enviar (cada vértice es un giro del pasillo).
   - Para fijar los núcleos, coloca puntos en la capa `Trazo::Cores`; se usan en modo manual.
   - Para marcar medianeras, dibuja líneas en la capa `Trazo::Medianeras` (nombre `retiro=3` si el edificio se retira).
3. En la web: Calcular masa → Generar pasillo y núcleos → Generar mix → Generar planos.
4. En Rhino: ejecuta de nuevo el script y elige **Recibir** (capas `Trazo::L00::Units`, `Rooms`, etc.).
   Alternativa sin script: botón **DXF (Rhino)** y luego `Import`.

## Qué hace cada etapa
- **Masa**: huella, altura, nº de plantas, programa y altura por planta, espesor de muro exterior, GFA.
- **Pasillo y núcleos**: eje (automático o dibujado), ancho de pasillo, núcleos (ancho, fondo incluyendo pasillo, cantidad), distancias de evacuación (salida única / múltiple) y núcleos extra automáticos.
- **Mix**: tipos con m² objetivo y %, ancho mínimo, muro medianero; métricas Match Score, Fit y Unidades únicas.
- **Planos**: distribución día/noche con pasillo interno, puertas y grafo de conexiones verificado.

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
`python tests/test_engine.py`
