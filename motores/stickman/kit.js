// Adaptación por lista blanca de TODO ui2d/fx2d. Nunca evalúa datos como código.
import { E, S, text, ease, prog, alpha, glow, ring, circle, seg, rr, linGrad, clamp, FONTS } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';
import * as UI from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/ui2d.js';
import * as FX from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/fx2d.js';

export function efecto(g, tipo, o, t) {
  const {x=E.W/2, y=E.H*.8, w=400, h=300, r=70, s=1, color=S().ui.gold} = o;
  switch (tipo) {
    case 'rain': case 'drops': case 'dust': case 'snow': case 'stars': case 'speedLines': case 'crowd': return FX[tipo](g, t, o);
    case 'godRays': return FX.godRays(g, x, y, {...o, t});
    case 'fog': return FX.fog(g, y, h, color, o.a);
    case 'sun': return FX.sun(g, x, y, r, color, o.glowColor, o.glowR);
    case 'moon': return FX.moon(g, x, y, r, color);
    case 'lightCone': return FX.lightCone(g, x, y, o);
    case 'pool': return FX.pool(g, x, y, o.rx ?? 300, o.ry ?? 50, color, o.a);
    case 'lensStreak': return FX.lensStreak(g, x, y, w, color, o.a, o.h);
    case 'sparkle': return FX.sparkle(g, x, y, o.s ?? 20, color, o.a);
    case 'rings': return FX.rings(g, x, y, t, o);
    case 'tree': case 'pine': case 'chair': case 'stool': return FX[tipo](g, x, y, s, color);
    case 'lampPost': return FX.lampPost(g, x, y, h, o);
    case 'clock': return FX.clock(g, x, y, r, t, o);
    case 'floorLines': return FX.floorLines(g, o.y0 ?? E.H*.79, o.y1 ?? E.H, color, o.spacing);
    case 'windowFrame': return FX.windowFrame(g, {x, y, w, h, ...o}, (ctx, xx, yy, ww, hh) => {
      ctx.fillStyle = linGrad(ctx, 0, yy, 0, yy+hh, ['#101a38', '#3e3b65']); ctx.fillRect(xx,yy,ww,hh);
      FX.skyline(ctx, {x:xx,y:yy+hh,w:ww,minH:hh*.15,maxH:hh*.65});
    });
    case 'lightning': case 'skyline': case 'hills': case 'clouds': case 'facade': case 'door':
    case 'counter': case 'screen': case 'bed': return FX[tipo](g, o);
    default: throw new Error(`Efecto del kit desconocido: ${tipo}`);
  }
}

// Ajuste multilínea común; evita que títulos y etiquetas salgan de su caja.
export function rotulo(g, str, x, y, w, size=42, color=S().ui.cream, extra={}) {
  const words = String(str || '').split(/\s+/), lines=[];
  g.save(); g.font = `700 ${size}px "${extra.font || FONTS.title}"`;
  let line='';
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (line && g.measureText(next).width > w) { lines.push(line); line=word; } else line=next;
  }
  if (line) lines.push(line);
  const scale = Math.min(1, 3 / Math.max(1, lines.length));
  lines.forEach((ln,i) => {
    const width = g.measureText(ln).width;
    text(g, ln, x, y+(i-(lines.length-1)/2)*size*1.18*scale,
      {size:size*scale*Math.min(1,w/Math.max(1,width)),color,...extra});
  });
  g.restore();
}

export function grafico(g, item, t, reparto, contraste=null) {
  const o = item.opciones, local = t-item.inicio+(item.desfase||0),
    dur = item.duracion_total??(item.fin-item.inicio+(item.desfase||0)), ui=S().ui;
  const p = ease.out(prog(local, 0, Math.min(1.1,dur*.35))), color=o.color || ui.gold;
  const W=E.W, H=E.H;
  if (['titleCard','bigLine','callout','dimension','dataCard','compareBars','meter'].includes(item.tipo)) {
    const ajustadas = {...o, dur, total:dur, start:0};
    if (item.tipo === 'dataCard') ajustadas.dur = Math.max(.1, Math.min(2,dur*.55));
    if (item.tipo === 'dimension') Object.assign(ajustadas,{x1:o.x1??W*.2,y1:o.y1??H*.5,x2:o.x2??W*.8,y2:o.y2??H*.5});
    return UI[item.tipo](g, local, ajustadas);
  }
  switch(item.tipo) {
    case 'badge': case 'readout': case 'blueprint': return UI[item.tipo](g,o);
    case 'lineFigure':return UI.lineFigure(g,{x:W/2,y:H*.8,s:2,...o});
    case 'bubble': return UI.bubble(g,o.x??W/2,o.y??H/2,o);
    case 'captions': return UI.captions(g,t,o);
    case 'endScreen': {
      const cast=(o.personajes||[]).map(id=>{
        const v=reparto[id]; return {top:v.ropa,color:v.color,color2:v.secundario,head:v.accesorio,headColor:v.secundario};
      });
      UI.endScreen(g,local,{question:o.question,cast});
      // El kit usa Subscribe; el adaptador localiza el rótulo con el idioma del guion.
      if (o.suscribir) {
        const x=W/2+60,y=E.vertical?560:300;
        g.fillStyle='#e0302a';g.fillRect(x-65,y-25,195,50);
        rotulo(g,o.suscribir,x+30,y+2,170,30,'#ffffff',{font:FONTS.ui});
      }
      return;
    }
    case 'lista': {
      const x=o.x??W*.16,y=o.y??H*.3,w=Math.min(o.w??W*.68,W*.86);
      if(o.titulo) rotulo(g,o.titulo,x+w/2,y-H*.13,w,48);
      const filas=o.filas, gap=Math.min(110,H*.58/filas.length), step=o.intervalo??Math.min(1,dur/(filas.length+1));
      filas.forEach((fila,i)=>{
        const a=ease.out(prog(local,i*step,i*step+.35));
        g.save();g.globalAlpha*=a;rr(g,x+(1-a)*30,y+i*gap,w,gap*.82,12);
        g.fillStyle=alpha(color,.08);g.fill();g.strokeStyle=alpha(color,.6);g.lineWidth=2;g.stroke();
        rotulo(g,fila,x+w*.49,y+i*gap+gap*.4,w*.82,34);
        text(g,'✓',x+w*.94,y+i*gap+gap*.4,{size:34,color:ui.good,font:FONTS.ui});g.restore();
      }); return;
    }
    case 'barras': {
      const filas=o.filas, base=H*.76, altura=H*.43,gap=W*.66/filas.length;
      rotulo(g,o.titulo,W/2,H*.16,W*.85,50);
      filas.forEach((fila,i)=>{
        const x=W*.17+gap*(i+.5),w=Math.min(170,gap*.48),c=fila.color||color;
        rr(g,x-w/2,base-altura,w,altura,12);g.fillStyle=alpha(c,.08);g.fill();g.strokeStyle=alpha(c,.45);g.lineWidth=2;g.stroke();
        const val=altura*fila.v*p;
        if(val>.1){rr(g,x-w/2,base-val,w,val,Math.min(8,val/2));g.fillStyle=linGrad(g,0,base-val,0,base,[c,alpha(c,.65)]);g.fill();}
        rotulo(g,fila.label,x,base+H*.07,gap*.85,30,ui.cream,{font:FONTS.ui});
      });return;
    }
    case 'poblacion': {
      const total=o.total??100,
        cols=o.columnas??(o.filas?Math.ceil(total/o.filas):Math.ceil(Math.sqrt(total*1.9))),
        rows=o.filas??Math.ceil(total/cols);
      const dx=W*.78/cols,dy=H*.58/rows,rad=Math.min(dx*.17,dy*.15,14),active=Math.round((o.destacados??0)*p);
      const indices=o.indices_destacados??Array.from({length:o.destacados??0},(_,i)=>i);
      const seleccion=new Set(indices);
      const explicita=['color_base','indices_destacados','atenuacion','inicio_destacado','duracion_destacado'].some(k=>k in o);
      const avance=ease.out(prog(local,o.inicio_destacado??0,(o.inicio_destacado??0)+(o.duracion_destacado??Math.min(1.1,dur*.35))));
      rotulo(g,o.titulo,W/2,H*.16,W*.85,48);
      for(let i=0;i<total;i++){
        const x=W*.11+dx*(i%cols+.5),y=H*.3+dy*(Math.floor(i/cols)+.2);
        const figura=c=>{circle(g,x,y,rad,c);rr(g,x-rad,y+rad*1.4,rad*2,rad*2.8,rad*.8);g.fillStyle=c;g.fill();};
        if(!explicita){
          if(i<active&&o.neon_destacados)glow(g,x,y+rad*1.8,rad*5,color,o.neon_destacados*.45);
          figura(i<active?color:alpha(ui.blueprint,.32));continue;
        }
        g.save();
        if(!seleccion.has(i)&&seleccion.size)g.globalAlpha*=1-(1-(o.atenuacion??1))*avance;
        if(seleccion.has(i)&&o.neon_destacados)glow(g,x,y+rad*1.8,rad*5,color,o.neon_destacados*.45*avance);
        figura(o.color_base??'#888888');
        if(seleccion.has(i)){g.globalAlpha*=avance;figura(color);}
        g.restore();
      }return;
    }
    case 'cronologia': {
      rotulo(g,o.titulo,W/2,H*.22,W*.85,48);
      const y=H*.56,x0=W*.12,x1=W*.88;
      seg(g,[[x0,y],[x0+(x1-x0)*p,y]],3,color);
      (o.etiquetas||[]).forEach((label,i,all)=>{
        const u=i/(all.length-1),x=x0+(x1-x0)*u;
        if(p+.01<u)return;
        seg(g,[[x,y-12],[x,y+12]],3,color);rotulo(g,label,x,y+H*.09,W*.7/all.length,28,ui.cream);
        glow(g,x,y,22,color,.45);
      });return;
    }
    case 'documento': {
      const x=W*.2,y=H*.12,w=W*.6,h=H*.76,filas=o.filas;
      rr(g,x+12,y+14,w,h,10);g.fillStyle='#0005';g.fill();
      rr(g,x,y,w,h,10);g.fillStyle='#f0e9db';g.fill();
      rotulo(g,o.titulo,W/2,y+h*.12,w*.86,46,'#241e29');
      const step=h*.65/filas.length;
      filas.forEach((fila,i)=>{
        const yy=y+h*.27+i*step;
        if(i===o.destacar){g.fillStyle=alpha('#f4bf52',.65*p);g.fillRect(x+w*.05,yy-step*.38,w*.9,step*.76);}
        rotulo(g,fila,W/2,yy,w*.86,Math.min(34,step*.4),'#342e36',{font:FONTS.ui});
      });
      if(o.sello&&p>.8){g.save();g.translate(W*.63,H*.75);g.rotate(-.1);g.strokeStyle='#d95245';g.lineWidth=5;g.strokeRect(-200,-36,400,72);rotulo(g,o.sello,0,0,375,36,'#d95245');g.restore();}return;
    }
    case 'comparacion': {
      if(contraste){
        const actores=Object.keys(reparto).length>0;
        if(o.titulo)rotulo(g,o.titulo,W/2,H*.09,W*.88,80,'#ffdb83');
        rotulo(g,o.izquierda,W*.25,H*.23,W*.40,78,contraste.color_izquierdo||'#a5e6ff');
        rotulo(g,o.derecha,W*.75,H*.23,W*.40,78,contraste.color_derecho||'#ffc487');
        for(const [lado,xx] of [['izquierdos',actores?.36:.25],['derechos',actores?.64:.75]]){
          const filas=o[`rasgos_${lado}`]||[];
          filas.forEach((fila,i)=>rotulo(g,fila,W*xx,H*(.43+i*.13),W*(actores?.235:.39),62,'#fff1dc'));
        }
        if(o.detalle_izquierdo)rotulo(g,o.detalle_izquierdo,W*.25,H*.93,W*.4,40,'#e5f4fc');
        if(o.detalle_derecho)rotulo(g,o.detalle_derecho,W*.75,H*.93,W*.4,40,'#ffdfbc');
        return;
      }
      rotulo(g,o.izquierda,W*.25,H*.18,W*.4,48,ui.blueprint);
      rotulo(g,o.derecha,W*.75,H*.18,W*.4,48,'#ff9b50');
      if(o.detalle_izquierdo)rotulo(g,o.detalle_izquierdo,W*.25,H*.95,W*.39,34);
      if(o.detalle_derecho)rotulo(g,o.detalle_derecho,W*.75,H*.95,W*.39,34);
      return;
    }
    case 'interruptor': {
      let on=o.activo??true;if(o.cambio!==undefined&&local>=o.cambio)on=!on;
      const x=W/2,y=H*.49,w=170,h=260;
      rr(g,x-w/2,y-h/2,w,h,18);g.fillStyle='#eee7d6';g.fill();
      rr(g,x-37,y-75,74,150,10);g.fillStyle='#b4ae9f';g.fill();
      rr(g,x-30,y+(on?-68:8),60,60,8);g.fillStyle=on?'#ffffd7':'#76766e';g.fill();
      if(on)glow(g,x,y-35,130,'#fff0a0',.3);
      rotulo(g,o.titulo,x,H*.77,W*.8,50);text(g,on?'ON':'OFF',x,y-h*.38,{size:26,color:on?'#2f795a':'#9c4038',font:FONTS.ui});return;
    }
    case 'dial': {
      const x=W/2,y=H*.55,r=Math.min(W*.2,H*.28),max=o.maximo??100,val=o.valor??0;
      g.beginPath();g.arc(x,y,r,Math.PI*.8,Math.PI*2.2);g.strokeStyle=alpha(color,.3);g.lineWidth=20;g.stroke();
      for(let i=0;i<=8;i++){
        const a=Math.PI*.8+i/8*Math.PI*1.4;
        seg(g,[[x+Math.cos(a)*r*.83,y+Math.sin(a)*r*.83],[x+Math.cos(a)*r*.94,y+Math.sin(a)*r*.94]],3,color);
      }
      const a=Math.PI*.8+clamp(val/max)*p*Math.PI*1.4;
      seg(g,[[x,y],[x+Math.cos(a)*r*.78,y+Math.sin(a)*r*.78]],8,color);circle(g,x,y,14,color);
      rotulo(g,o.titulo,x,H*.17,W*.85,48);text(g,`${Math.round(val*p*10)/10}${o.unidad||''}`,x,y+r*.66,{size:64,color});return;
    }
    default: throw new Error(`Gráfico del kit desconocido: ${item.tipo}`);
  }
}
