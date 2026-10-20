# Aruma (GROU / Estudio Harispe): nota de la preparación

## Fuente

- Brochure comercial «Aruma» de GROU Desarrollos (diciembre de 2025), 56 págs. Lo desarrollan y comercializan GROU y
  Grupo Caral, lo construye NOVA Construcciones y la arquitectura es de Estudio Harispe.
- Edificio exento de 5 pisos y 37 apartamentos, frente a la Laguna Grande de los Lagos de Carrasco (Parque Miramar).
  - En las plantas, la calle y el acceso están arriba, hacia el Parque Roosevelt, y la laguna abajo.
  - Los Lagos de Carrasco quedan, hasta donde sé, del lado de Canelones (Ciudad de la Costa). Igual se usó `MVD` en los
    nombres de archivo; en los datos dice «área metropolitana».
- **Las plantas son imágenes**: el PDF solo tiene vectoriales los rellenos de color de cada unidad. No hay escala
  gráfica ni cotas de los locales; las únicas cotas son las medidas de las cocheras.
  - **Escala**: sale de las «áreas propias» de las fichas. La carpeta las define casi igual que la convención: muros
    exteriores enteros y la mitad de los muros entre unidades.
    - Pisos 1 a 4: 25,47 pt por m (unos 1:112 en la página). Las 8 unidades quedan entre −0,5 y +0,4 % de la carpeta.
    - Piso 5: 25,81 pt por m. Esa planta está dibujada un 1,3 % más grande, lo mismo que da la correlación de los
      muros del núcleo entre las dos páginas. Las unidades quedan entre −1,3 y +0,8 %.
  - **Control independiente**: las 63 puertas interiores miden 0,80 m de mediana (entre 0,77 y 0,85), y las camas dan
    1,40-1,60 × 2,00 y 0,90 × 1,90.

**Precisión media**: imagen sin cotas, con la escala deducida de superficies publicadas.

## Qué hay

- **Plantas** (`P_`): pisos 1 a 4 (`tipo`, 8 viviendas, iguales del 1 al 4) y piso 5 (5 viviendas). Cada una tiene su
  `_comparacion.png` con lo dibujado sobre la imagen original:
  - rojo: contornos;
  - naranja: estancias;
  - verde: entradas;
  - azul: ventanas;
  - magenta: puertas;
  - celeste: terrazas;
  - verde claro: patios;
  - gris: palier y núcleo;
  - violeta y marrón: muebles y artefactos.
- **Unidades** (`U_`): las 13 tipologías.

  | Archivo | Unidades | Tipo |
  |---|---|---|
  | `_01` | 105 a 405 | 2D en esquina, al Parque Roosevelt |
  | `_02` | 106 a 406 | 2D al Parque Roosevelt |
  | `_03` | 107 a 407 | 1D al Parque Roosevelt |
  | `_04` | 108 a 408 | 2D en esquina, la 105 en espejo |
  | `_05` | 104 a 404 | 3D en esquina, a la laguna |
  | `_06` | 103 a 403 | 2D a la laguna |
  | `_07` | 102 a 402 | 1D a la laguna |
  | `_08` | 101 a 401 | 3D en esquina, la 104 en espejo |
  | `_09` | 503 | 3D en esquina, al parque |
  | `_10` | 504 | 1D al parque |
  | `_11` | 505 | la 503 en espejo |
  | `_12` | 502 | 4D en esquina, a la laguna |
  | `_13` | 501 | la 502 en espejo |

- **Sin DXF**, porque no tienen viviendas: la PB (hall, cocheras 24 a 40 y laundry) y el subsuelo (cocheras 1 a 23).
- **Índice**: se agregaron 15 filas a `indice.csv`.

## Cómo se midió (imagen sin cotas)

- **Fuente de trabajo**: la página se renderizó a 4 px por pt (1 px = 1 cm). Los muros son el verde oscuro macizo y las
  carpinterías, los trazos largos del mismo verde.
- **Locales**: cada uno es el relleno del espacio libre entre muros, con las puertas cerradas.
  - Los rellenos se cortaron con los límites de zona y se llevaron a polígonos ortogonales.
  - Los rellenos partidos por cierres falsos (pasillos frente a una esquina, nichos) se unieron a mano.
- **Contornos, palier y núcleo**: se trazaron a mano con las medidas de la imagen.
  - Contornos: eje de los muros entre unidades, cara exterior hacia el palier, las fachadas y los patios.
  - El palier y los dos patios de aire y luz se trazaron igual.
- **Control**: un recorrido comprueba que desde la entrada se llega a todos los locales, por puertas o por límites de
  zona.
- **Puertas**: los huecos de muro de 0,5 a 1,3 m entre dos locales de la misma vivienda. Tres puertas de la 502 y una de
  la 501, junto a esquinas, se agregaron a mano.
- **Ventanas**: los tramos de fachada sin muro macizo.
- **Equipamiento**: vectorizado de la imagen, así que los trazos son aproximados.
  - Se quitaron los arcos y las hojas de las puertas.
  - Los muebles principales llevan nombre: `Cama`, `Mesa N`, `Sofa`, `Mesada`.
    - Los nombres salen del tamaño de cada grupo de trazos, así que son medidas nominales.
    - Donde el tamaño no era claro, no se puso nombre.

## Criterios que conviene revisar

- **Planta sin girar**: la calle (Parque Roosevelt) ya queda arriba.
  - El palier rodea el núcleo (escalera y ascensor) y dos patios de aire y luz (`Trazo_Patios`), así que no puede quedar
    horizontal.
  - `Trazo_Terreno` es el contorno de la losa con las terrazas: el edificio es exento y no tiene medianeras.
- **Fachadas**: van rotuladas así:
  - las de arriba, `Calle`;
  - las de la laguna, `Contrafrente`;
  - las de los patios, `Patio`;
  - las laterales, sin rótulo.
- **Orientación de las unidades**: la fachada principal va arriba.
  - Las del parque quedan como en la planta.
  - Las de la laguna (104, 103, 102, 101, 502 y 501) van giradas 180°.
  - Las de esquina tienen la entrada a un costado; cada archivo lo dice.
- **Nicho de la heladera (105 y 108)**: está abierto al hall y a la cocina, y va con el `Hall`.
- **Antebaño de la 104 y la 101**: va dentro del `Baño`.
- **Pasillo de los dormitorios (503, 505, 502 y 501)**: no tiene puerta hacia el hall y va dentro del `Hall`.
- **Comedor sin fachada**: el de la 106, la 103, la 102, la 107 y la 504 da `ver_dxf` el aviso del comedor interior, y
  se acepta.
- **Terrazas y terrazas de servicio**: van en `Trazo_Cotas`.
  - Las medidas son las del dibujo.
  - La carpeta da la superficie total de terrazas de cada unidad, y va en `observaciones`.
- **503**: la carpeta no da su área propia, solo el total (130,21 m²). Su contorno da 93,0 m², como el de la 505 en espejo
  (la carpeta da 94,22 para la 505).
- **Norte**: el símbolo de las plantas apunta 45° a la izquierda de la vertical de la página.
  - En las plantas y en las unidades sin girar, `norte: 45`.
  - En las giradas 180°, `norte: 225`.
- **Formato**: igual que en los casos anteriores. Todos pasan `ver_dxf` sin errores y `ezdxf.recover` sin arreglos. Los
  únicos avisos son los de los comedores interiores.
