// Fuentes del kit congeladas en el bundle: sin red ni rutas externas al exportar.
import fredoka from './node_modules/@fontsource/fredoka/files/fredoka-latin-700-normal.woff2';
import nunito from './node_modules/@fontsource/nunito/files/nunito-latin-900-normal.woff2';
import playfair from './node_modules/@fontsource/playfair-display/files/playfair-display-latin-900-italic.woff2';

export async function cargarFuentes() {
  for (const [nombre, url, peso, estilo] of [
    ['Fredoka', fredoka, '700', 'normal'], ['Nunito', nunito, '900', 'normal'],
    ['Playfair Display', playfair, '900', 'italic'],
  ]) {
    const fuente = new FontFace(nombre, `url(${url})`, {weight: peso, style: estilo});
    document.fonts.add(await fuente.load());
  }
}
