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
  g.save();const alpha=g.globalAlpha;g.setTransform(1,0,0,1,0,0);
  g.globalAlpha=alpha*intensidad*.85;
  g.filter=`blur(${(8+intensidad*12)*E.PX}px)`;
  g.drawImage(mascara,0,0);
  g.globalAlpha=alpha*Math.min(1,intensidad*1.3);
  g.filter=`blur(${(4+intensidad*8)*E.PX}px)`;
  g.drawImage(mascara,0,0);
  g.filter='none';g.globalAlpha=alpha;g.drawImage(dibujo,0,0);
  g.restore();
}

let figuraAura, luzAura;
export function conAura(g,aura,pintar){
  if(!aura||!aura.intensidad){pintar(g);return;}
  const {width:w,height:h}=g.canvas,intensidad=aura.intensidad;
  figuraAura=lienzo(figuraAura,w,h);luzAura=lienzo(luzAura,w,h);
  const ctx=figuraAura.getContext('2d'),mask=luzAura.getContext('2d');
  ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,w,h);
  ctx.save();ctx.setTransform(g.getTransform());pintar(ctx);ctx.restore();
  mask.setTransform(1,0,0,1,0,0);mask.clearRect(0,0,w,h);
  mask.globalCompositeOperation='source-over';mask.drawImage(figuraAura,0,0);
  mask.globalCompositeOperation='source-in';mask.fillStyle=aura.color;mask.fillRect(0,0,w,h);
  mask.globalCompositeOperation='source-over';
  g.save();const alpha=g.globalAlpha;g.setTransform(1,0,0,1,0,0);
  for(const [radio,alfa] of [[95,.9],[55,.95],[22,1],[5,1]]){
    g.globalAlpha=alpha*intensidad*alfa;g.filter=`blur(${radio*E.PX}px)`;g.drawImage(luzAura,0,0);
  }
  g.filter='none';g.globalAlpha=alpha*intensidad;
  for(const [dx,dy] of [[-2,0],[2,0],[0,-2],[0,2]])g.drawImage(luzAura,dx*E.PX,dy*E.PX);
  // Recuperar la figura nítida: el halo nunca sustituye su cara o vestuario.
  g.filter='none';g.globalAlpha=alpha;g.drawImage(figuraAura,0,0);g.restore();
}

export function neonObjeto(o,R){
  if(o.neon!==undefined)return o.neon;
  if(!R?.resplandor)return 0;
  if(['texto','etiqueta'].includes(o.tipo))return .6;
  if(o.capa==='fondo'||!['linea','redondeado','circulo'].includes(o.tipo)||o.w*o.h>E.W*E.H*.12)return 0;
  const c=o.color.match(/[a-f\d]{2}/gi)?.map(v=>parseInt(v,16))||[];
  return Math.max(...c)-Math.min(...c)>65?.55:0;
}
