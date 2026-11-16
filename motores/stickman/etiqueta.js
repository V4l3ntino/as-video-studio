import { FONTS } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';
import { rotuloRedondeado } from './texto.js';

// Marco y letras comparten transformación, halo y trayectoria. Hasta tres líneas.
export function pintarEtiqueta(g, o) {
  const {w,h}=o, lineas=o.texto.split('\n').slice(0,3);
  g.save();
  g.fillStyle='#160d08';g.strokeStyle=o.color;g.lineWidth=o.grosor;
  g.beginPath();g.roundRect(-w/2,-h/2,w,h,Math.min(h/2,56));g.fill();g.stroke();
  let size=Math.min(o.fuente,(h-24)/(lineas.length*1.15));
  g.font=`700 ${size}px "${FONTS.title}"`;
  size*=Math.min(1,(w-40)/Math.max(1,...lineas.map(s=>g.measureText(s).width)));
  g.font=`700 ${size}px "${FONTS.title}"`;g.textAlign='center';g.textBaseline='middle';
  lineas.forEach((s,i)=>{
    g.save();g.translate(0,(i-(lineas.length-1)/2)*size*1.15);
    rotuloRedondeado(g,s,size,o.color);g.restore();
  });
  g.restore();
}
