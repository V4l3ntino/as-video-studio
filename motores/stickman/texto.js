// Contorno de contraste común a textos nativos y a todas las familias del kit.
// Se conserva el color solicitado: el respaldo es claro para tinta oscura y viceversa.
import { rgb } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';

// Se pinta DESPUÉS de la tinta, en sus mismas coordenadas y con la fuente ajustada.
export function pintarTachado(g, texto, size, tachado, t) {
  if (!tachado || t <= tachado.inicio) return;
  const progreso = Math.min(1,(t-tachado.inicio)/(tachado.fin-tachado.inicio));
  const m = g.measureText(texto);
  const ancho = m.width + size*.1;
  const y = ((m.actualBoundingBoxDescent||0)-(m.actualBoundingBoxAscent||size*.6))/2;
  g.save();
  g.shadowBlur=0;g.strokeStyle='#ef3434';g.lineWidth=Math.max(4,size*.075);g.lineCap='round';
  g.beginPath();g.moveTo(-ancho/2,y);g.lineTo(-ancho/2+ancho*progreso,y);g.stroke();
  g.restore();
}

// Tinta con relieve suave: el degradado queda dentro del glifo, nunca borroso.
export function rotuloRedondeado(g, texto, size, color) {
  const [r,v,b] = rgb(color);
  const mezclar = (destino, cantidad) => `rgb(${[r,v,b].map(c=>Math.round(c+(destino-c)*cantidad)).join(',')})`;
  const tinta = g.createLinearGradient(0,-size*.5,0,size*.5);
  tinta.addColorStop(0,mezclar(255,.52));
  tinta.addColorStop(.48,color);
  tinta.addColorStop(1,mezclar(0,.12));
  g.save();
  g.lineJoin='round';g.lineWidth=Math.max(1,size*.018);
  g.strokeStyle=mezclar(0,.55);g.strokeText(texto,0,0);
  // fillStyle degradado evita el contorno grueso del texto auxiliar.
  g.fillStyle=tinta;g.fillText(texto,0,0);
  g.restore();
}

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
