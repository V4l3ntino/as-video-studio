// Contorno de contraste común a textos nativos y a todas las familias del kit.
// Se conserva el color solicitado: el respaldo es claro para tinta oscura y viceversa.
import { rgb } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';

export function protegerTexto(g, activo, grosor=.12) {
  const original = g.fillText;
  g.fillText = function(str, x, y, ...args) {
    if (activo() && typeof this.fillStyle === 'string') {
      const canales = rgb(this.fillStyle).slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
      const luminancia = .2126*canales[0] + .7152*canales[1] + .0722*canales[2];
      const size = Number(this.font.match(/([\d.]+)px/)?.[1] || 32);
      this.save();
      this.shadowBlur = 0; this.lineJoin = 'round';
      this.lineWidth = Math.max(2, size*(typeof grosor==='function'?grosor():grosor));
      this.strokeStyle = luminancia < .179 ? '#ffffff' : '#000000';
      this.strokeText(str, x, y, ...args);
      // El resplandor de la tinta no debe tapar el contorno de contraste.
      const resultado = original.call(this, str, x, y, ...args);
      this.restore();
      return resultado;
    }
    return original.call(this, str, x, y, ...args);
  };
}
