// Ambiente ligero detrás del contenido, activado explícitamente en planes nuevos.
import { E, S, alpha } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';
import { dust } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/fx2d.js';
import { semillaLugar } from './decorados.js';
import { paletaEditorial } from './estilo.js';

export function ambienteVisual(g,escena,t){
  const r=escena.realizacion||{},p=paletaEditorial(r.paleta),W=E.W,H=E.H;
  const activo=item=>t>=item.inicio&&t<item.fin;
  g.save();
  // Sin relleno opaco: respeta el fondo elegido y nunca tapa los gráficos previos.
  if(r.malla&&!(escena.graficos||[]).some(i=>i.tipo==='blueprint'&&activo(i))){
    const paso=80,color=p?.acento||S().ui.blueprint;
    for(let mayor=0;mayor<2;mayor++){
      g.strokeStyle=alpha(color,mayor?.075:.035);g.lineWidth=1;
      const salto=paso*(mayor?5:1);g.beginPath();
      for(let x=0;x<=W;x+=salto){g.moveTo(x,0);g.lineTo(x,H);}
      for(let y=0;y<=H;y+=salto){g.moveTo(0,y);g.lineTo(W,y);}
      g.stroke();
    }
  }
  const polvo=escena.atmosfera==='polvo'||(escena.efectos_visuales||[]).some(i=>i.tipo==='dust'&&activo(i));
  if(r.particulas&&!polvo){
    dust(g,t+(r.desfase_ambiente||0),{seed:semillaLugar(r.escenario||{}),count:32,
      color:p?.texto||S().ui.cream,size:2.3,speed:9,a:.16});
  }
  g.restore();
}
