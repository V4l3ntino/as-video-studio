// Acentos puntuales; no se repiten ni se deducen de la emoción persistida.
import { E } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';

export function pulsoEnfasis(t,duracion,fps,brusco=false){
  if(t<=0||t>=duracion)return {alpha:0,escala:1};
  const entrada=Math.min((brusco?2:3)/fps,duracion*.35);
  const salida=Math.min(5/fps,duracion*.5);
  const subir=Math.min(1,t/entrada),bajar=Math.min(1,(duracion-t)/salida);
  return {alpha:subir*bajar,escala:1+.12*Math.sin(Math.PI*t/duracion)};
}

export function pintarEnfasis(g,item,t,ancla,mirar=1){
  const o=item.opciones,modo=o.modo;
  const pulso=pulsoEnfasis(t-item.inicio,item.fin-item.inicio,E.fps,modo==='sobresalto');
  if(!pulso.alpha)return;
  const r=ancla.r*(o.escala??1),impacto=modo==='impacto';
  const lado=ancla.x+r*2>E.W?-1:1;
  let angulos=modo==='descubrimiento'?[-2.7,-2.15,-1.57,-1,-.45]:
    modo==='confusion'?[-.45,.05]:[-1.25,-.95,-.65];
  // En un primer plano sin aire por arriba, usar el lateral libre.
  if(!impacto&&modo!=='enfado'&&modo!=='confusion'&&ancla.y-r*1.9<12){
    angulos=angulos.map((_,i)=>-.55+i*.7/(angulos.length-1));
  }
  if(impacto)angulos=Array.from({length:6},(_,i)=>i*Math.PI/3);
  g.save();g.globalAlpha*=pulso.alpha;g.strokeStyle=o.color||'#ffc052';
  g.lineWidth=Math.max(3,r*(modo==='confusion'?.085:.12));g.lineCap='round';g.lineJoin='round';
  if(modo==='enfado'){
    for(const dy of [-.3,.1,.5]){
      const x=ancla.x+mirar*r*.8,y=ancla.y+r*.35+dy*r;
      const len=r*.55*pulso.escala;
      g.beginPath();g.moveTo(x,y);g.lineTo(x+mirar*len*.5,y-r*.12);
      g.lineTo(x+mirar*len,y);g.stroke();
    }
  }else{
    const radio=impacto?.22:modo==='confusion'?1.4:1.55;
    const longitud=(modo==='confusion'?.24:impacto?.65:.48)*pulso.escala;
    for(const a of angulos){
      const dx=Math.cos(a)*(impacto?1:lado),dy=Math.sin(a);
      g.beginPath();g.moveTo(ancla.x+dx*r*radio,ancla.y+dy*r*radio);
      g.lineTo(ancla.x+dx*r*(radio+longitud),ancla.y+dy*r*(radio+longitud));g.stroke();
    }
  }
  g.restore();
}
