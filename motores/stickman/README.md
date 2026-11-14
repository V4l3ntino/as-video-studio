# Motor Stickman 2D

`compilar.mjs` empaqueta `escena.js` con esbuild del motor Remotion. El adaptador
usa `core.js`, `styles.js`, `rig2d.js` y `fx2d.js` del kit original en
`GrowKaz_Stickman/skills/make-2d-video/kit/`. Mantener esa carpeta al distribuir
el programa. No hay build del frontend ni instalación de las dependencias Node
del plugin; el render utiliza el navegador/CDP y el codificador del Estudio.

El contrato de entrada es `window.STICKMAN`:

- `variante`: familia, proporciones, ojos, boca, ropa, accesorios, colores y acabado.
- `escena`: ambiente/decorado, atmósfera, cámara, actores y objetos con claves temporales.
- `duracion`, `ancho`, `alto`, `fps`: salida y reloj del plano.

`window.pintar(t)` dibuja el instante local en Canvas. Poses, respiración,
caminata, expresiones y efectos son deterministas. Claude/Codex producen JSON
validado en `pasos/stickman.py`, nunca programas que se ejecuten desde el modelo.

El paso `assets` conserva por escena:

- `escenas/<id>.animacion.json`: firma del encargo y plan de acción, reutilizable tras un fallo.
- `escenas/<id>_<huella>.mp4`: animación visual inmutable, sin narración ni efectos embebidos.
- `escenas/<id>.png`: póster.
- `escenas/<id>.json`: recibo de publicación, narración, firma y recursos de sonido.
- `sonidos/<id>_<índice>_<huella>.wav`: sonidos sintetizados por `audio/sfx.py` y `audio/dsp.py` originales.

La ficha se publica después del clip y de sus efectos. Las rutas de la ficha y
el manifiesto son relativas a la versión de assets; `aplicar_recursos` las
resuelve para la previa, el editor y el montaje, también en trabajo parcial.
No persistir las rutas absolutas resueltas dentro de `plan.json`.

Los efectos usan bloques `stickman:<índice>` de la pista Sonidos. La mezcla final
y la previsualización consumen los mismos eventos. No muxearlos además en el
clip visual: sonarían dos veces. Narración y diálogos conservan sus pistas.

Las definiciones de personajes se guardan en `guion.params.personajes` y un
recibo junto a su PNG inmutable en `medios_usuario/animaciones/`. Al guardar se
comprueba que la definición pertenece al personaje generado, sin admitir fotos
subidas o POV como sustitución de un rig.

Pruebas: `python pasos/prueba_stickman.py` (contratos y síntesis) o
`python pasos/prueba_stickman.py --real` (Chromium, ffmpeg, estilos, interrupción,
reanudación, montaje audible y traslado del proyecto). No llaman a proveedores.
