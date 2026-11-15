// Halo local de una silueta alfa. El dibujo original se compone nítido al final.
import { E } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';
import { protegerTexto } from './texto.js';

let dibujo, mascara;
function lienzo(actual,w,h){
  if(!actual)actual=document.createElement('canvas');
  if(actual.width!==w||actual.height!==h){actual.width=w;actual.height=h;}
  return actual;
}

export function conNeon(g,intensidad,color,pintar){
  if(!intensidad){pintar(g);return;}
  const {width:w,height:h}=g.canvas;
  dibujo=lienzo(dibujo,w,h);mascara=lienzo(mascara,w,h);
  const ctx=dibujo.getContext('2d'),mask=mascara.getContext('2d');
  // El neón mantiene una línea de contraste fina; un borde grueso parecería pegatina.
  if(!ctx.neonTexto){protegerTexto(ctx,()=>true,.04);ctx.neonTexto=true;}
  ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,w,h);
  ctx.save();ctx.setTransform(g.getTransform());pintar(ctx);ctx.restore();
  mask.clearRect(0,0,w,h);mask.globalCompositeOperation='source-over';
  mask.drawImage(dibujo,0,0);mask.globalCompositeOperation='source-in';
  mask.fillStyle=color;mask.fillRect(0,0,w,h);mask.globalCompositeOperation='source-over';
  g.save();g.setTransform(1,0,0,1,0,0);
  const alpha=g.globalAlpha;
  g.globalAlpha=alpha*intensidad*.65;
  g.filter=`blur(${(8+intensidad*12)*E.PX}px)`;
  g.drawImage(mascara,0,0);
  g.filter='none';g.globalAlpha=alpha;g.drawImage(dibujo,0,0);
  g.restore();
}
