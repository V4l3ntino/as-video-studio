// Escenario de contraste: luz fría/cálida, profundidad, partículas y una unión luminosa.
import { E, alpha, linGrad, glow, rng } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';
import { dust, pool } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/fx2d.js';
import { semillaLugar } from './decorados.js';

export function bordeComparacion(o={}){
  const W=E.W,H=E.H;
  if(o.corte==='vertical')return [[W/2,0],[W/2,H]];
  if(o.corte==='diagonal')return [[W*.53,0],[W*.47,H]];
  return [[W*.53,0],[W*.495,H*.28],[W*.52,H*.62],[W*.50,H]];
}

export function recortarComparacion(g,lado,o={}){
  const puntos=bordeComparacion(o),W=E.W,H=E.H;
  g.beginPath();
  if(lado==='izquierda'){
    g.moveTo(0,0);for(const [x,y] of puntos)g.lineTo(x,y);g.lineTo(0,H);
  }else{
    g.moveTo(W,0);g.lineTo(W,H);for(const [x,y] of [...puntos].reverse())g.lineTo(x,y);
  }
  g.closePath();g.clip();
}

function oscuro(color,factor){
  const rgb=color.slice(1).match(/../g).map(c=>Math.round(parseInt(c,16)*factor));
  return `rgb(${rgb.join(',')})`;
}

export function fondoComparacion(g,escena,t){
  const r=escena.realizacion,o=r.comparacion,W=E.W,H=E.H;
  const colores=[o.color_izquierdo||'#83d9f7',o.color_derecho||'#ff8d38'];
  const reloj=t+(r.desfase_ambiente||0),seed=semillaLugar(r.escenario||{});
  for(let i=0;i<2;i++){
    const color=colores[i],x=W*(i?.77:.23);
    g.save();recortarComparacion(g,i?'derecha':'izquierda',o);
    g.fillStyle=linGrad(g,0,0,0,H,[oscuro(color,.07),oscuro(color,.20),oscuro(color,.09)]);
    g.fillRect(0,0,W,H);
    glow(g,x,H*.48,Math.max(W*.43,H*.68),color,.22);
    // Piso oscuro con reflejo de luz, no una franja gris opaca.
    const suelo=H*.88;
    g.fillStyle=linGrad(g,0,suelo,0,H,[oscuro(color,.035),'#010309']);g.fillRect(0,suelo,W,H-suelo);
    pool(g,x,H*.915,W*.20,H*.032,color,.28);
    if(r.malla&&!i){
      g.strokeStyle=alpha(color,.025);g.lineWidth=1;g.beginPath();
      for(let xx=0;xx<W;xx+=80){g.moveTo(xx,0);g.lineTo(xx,H);}
      for(let yy=0;yy<H;yy+=80){g.moveTo(0,yy);g.lineTo(W,yy);}
      g.stroke();
    }
    if(r.particulas!==false){
      if(i)dust(g,reloj,{seed:seed+11,count:30,area:[W*.5,0,W*.5,H],color:'#ffc982',size:3.3,speed:12,a:.48});
      else{
        const random=rng(seed+5);
        for(let n=0;n<32;n++){
          const s=.5+random(),fase=random()*Math.PI*2;
          const xx=random()*W*.54+Math.sin(reloj*.18+fase)*12;
          const yy=((random()*H+reloj*7*s)%H+H)%H;
          const rad=2+s*2;
          g.strokeStyle=alpha('#d0efff',.18+s*.09);g.lineWidth=1;
          g.beginPath();g.moveTo(xx-rad,yy);g.lineTo(xx+rad,yy);
          g.moveTo(xx,yy-rad);g.lineTo(xx,yy+rad);g.stroke();
          if(n%4===0)glow(g,xx,yy,rad*3,color,.14);
        }
      }
    }
    g.restore();
  }
}

export function separadorComparacion(g,o={}){
  const color=o.color_separador||'#ffdb83';
  g.save();g.lineJoin='round';g.lineCap='round';
  g.beginPath();bordeComparacion(o).forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));
  g.strokeStyle=alpha(color,.45);g.lineWidth=9;g.shadowColor=color;g.shadowBlur=22*E.PX;g.stroke();
  g.shadowBlur=8*E.PX;g.strokeStyle=color;g.lineWidth=3;g.stroke();g.restore();
}
