import { E, FONTS, ease, prog } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';
import { conNeon } from './neon.js';
import { rotuloRedondeado } from './texto.js';

// Una sola composición: la hoja y sus términos excluidos no pueden taparse.
export function documentoNeon(g,item,t){
  const {W,H}=E,o=item.opciones,local=t-item.inicio+(item.desfase||0);
  const externos=o.excluidos||[],x=W*(externos.length?.32:.23),w=W*(externos.length?.36:.54),y=H*.12,h=H*.76;
  const tinta='#fff1d0',color=o.color||'#5bd8da',oro='#ffbf19';
  const titulo=o.titulo||'',palabras=titulo.split(/\s+/),mitad=Math.ceil(palabras.length/2);
  const titulos=externos.length&&palabras.length>1?[palabras.slice(0,mitad).join(' '),palabras.slice(mitad).join(' ')]:[titulo];
  function texto(ctx,s,cx,cy,ancho,size,color){
    ctx.save();ctx.translate(cx,cy);ctx.font=`700 ${size}px "${FONTS.title}"`;
    size*=Math.min(1,ancho/Math.max(1,ctx.measureText(s).width));
    ctx.font=`700 ${size}px "${FONTS.title}"`;ctx.textAlign='center';ctx.textBaseline='middle';
    rotuloRedondeado(ctx,s,size,color);ctx.restore();
  }
  function trazo(ctx,puntos,grosor,color){
    ctx.beginPath();ctx.lineWidth=grosor;ctx.strokeStyle=color;ctx.lineJoin=ctx.lineCap='round';
    puntos.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.stroke();
  }
  conNeon(g,item.neon??.55,tinta,ctx=>{
    const doblez=Math.min(w*.12,h*.1);
    ctx.beginPath();ctx.moveTo(x+25,y);ctx.lineTo(x+w-doblez,y);ctx.lineTo(x+w,y+doblez);
    ctx.lineTo(x+w,y+h-25);ctx.quadraticCurveTo(x+w,y+h,x+w-25,y+h);
    ctx.lineTo(x+25,y+h);ctx.quadraticCurveTo(x,y+h,x,y+h-25);
    ctx.lineTo(x,y+25);ctx.quadraticCurveTo(x,y,x+25,y);ctx.strokeStyle=tinta;ctx.lineWidth=8;ctx.stroke();
    trazo(ctx,[[x+w-doblez,y],[x+w-doblez,y+doblez],[x+w,y+doblez]],7,color);
    titulos.forEach((s,i)=>texto(ctx,s,x+w/2,y+h*(.15+i*.10),w*.88,Math.min(86,w*.12),tinta));
  });
  conNeon(g,item.neon??.6,color,ctx=>{
    trazo(ctx,[[x+w*.1,y+h*.31],[x+w*.9,y+h*.31]],15,color);
    const filas=o.filas,step=h*.52/filas.length;
    filas.forEach((s,i)=>{
      const yy=y+h*.41+i*step,revelado=ease.out(prog(local,.15+i*.16,.5+i*.16));
      ctx.save();ctx.globalAlpha*=revelado;
      ctx.beginPath();ctx.arc(x+w*.13,yy,12,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();
      // Los renglones simbólicos son trazos vectoriales, no guiones de una fuente.
      if(/^[\s_—–-]+$/.test(s)){
        trazo(ctx,[[x+w*.21,yy-5],[x+w*.86,yy-5]],15,color);
        trazo(ctx,[[x+w*.21,yy+step*.34],[x+w*(i%2?.68:.77),yy+step*.34]],13,color);
      }else texto(ctx,s,x+w*.55,yy,w*.68,Math.min(40,step*.55),color);
      if(i===o.destacar)trazo(ctx,[[x+w*.2,yy+step*.48],[x+w*.87,yy+step*.48]],5,oro);
      ctx.restore();
    });
  });
  externos.forEach((s,i)=>{
    const cx=W*(i===0?.15:.85),cy=H*.44,aparicion=ease.out(prog(local,.2+i*.45,.6+i*.45));
    g.save();g.globalAlpha*=aparicion;
    conNeon(g,item.neon??.65,oro,ctx=>{
      texto(ctx,s,cx,cy,W*.26,86,tinta);
      const cruz=52,yy=cy+H*.16;
      trazo(ctx,[[cx-cruz,yy-cruz],[cx+cruz,yy+cruz]],25,oro);
      trazo(ctx,[[cx-cruz,yy+cruz],[cx+cruz,yy-cruz]],25,oro);
    });g.restore();
  });
  if(o.sello)texto(g,o.sello,x+w/2,y+h*.94,w*.85,36,oro);
}
