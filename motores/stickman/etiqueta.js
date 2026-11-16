import { FONTS } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';
import { rotuloRedondeado } from './texto.js';

// Marco y letras comparten transformación, halo y trayectoria. Hasta tres líneas.
export function pintarEtiqueta(g, o) {
  const {w,h}=o, lineas=o.texto.split('\n').slice(0,3);
  const fondo=o.fondo||'#160d08';
  const luminancia=c=>{
    const v=c.match(/[a-f\d]{2}/gi).map(h=>parseInt(h,16)/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4);
    return v[0]*.2126+v[1]*.7152+v[2]*.0722;
  };
  const contraste=c=>(Math.max(luminancia(c),luminancia(fondo))+.05)/(Math.min(luminancia(c),luminancia(fondo))+.05);
  const tinta=o.tinta||(contraste(o.color)>=4.5?o.color:contraste('#fff1dc')>=4.5?'#fff1dc':'#12263f');
  g.save();
  g.fillStyle=fondo;g.strokeStyle=o.color;g.lineWidth=o.grosor;
  g.beginPath();g.roundRect(-w/2,-h/2,w,h,Math.min(h/2,56));g.fill();g.stroke();
  let size=Math.min(o.fuente,(h-24)/(lineas.length*1.15));
  g.font=`700 ${size}px "${FONTS.title}"`;
  size*=Math.min(1,(w-40)/Math.max(1,...lineas.map(s=>g.measureText(s).width)));
  g.font=`700 ${size}px "${FONTS.title}"`;g.textAlign='center';g.textBaseline='middle';
  lineas.forEach((s,i)=>{
    g.save();g.translate(0,(i-(lineas.length-1)/2)*size*1.15);
    rotuloRedondeado(g,s,size,tinta);g.restore();
  });
  g.restore();
}
