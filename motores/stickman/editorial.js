import { E, S, mood, layer, blurLayer, linGrad, alpha, clamp } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';
import * as FX from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/fx2d.js';
import { decorado } from './decorados.js';
import { efecto, grafico } from './kit.js';
import { acabado } from './acabado.js';
import { pintar3D } from './espacio3d.js';
import { encuadrar } from './encuadre.js';
import { conNeon } from './neon.js';
import { paletaEditorial } from './estilo.js';

export function pintarEditorial(g,t,D,draw) {
  const S0=D.escena,R=S0.realizacion||{},W=E.W,H=E.H;
  const cam={z:draw.valor(S0.camara,t,'escala',1),x:draw.valor(S0.camara,t,'x',0)*W,
    y:draw.valor(S0.camara,t,'y',0)*H,r:draw.valor(S0.camara,t,'rot',0)};
  if(['medio','primer_plano'].includes(R.encuadre)){
    const actor=S0.personajes.find(c=>c.id===R.sujeto),head=draw.cabeza(actor,t);
    const close=R.encuadre==='primer_plano';
    cam.z=clamp((close?H*.23:H*.13)/head.r,1.1,5)*cam.z;
    cam.x+=head.x-W/2;cam.y+=head.y+(close?H*.035:H*.14)-H/2;
  }else if(R.encuadre==='detalle'&&R.foco){
    cam.z*=2.6;cam.x+=R.foco[0]*W-W/2;cam.y+=R.foco[1]*H-H/2;
  }
  if(!S0.espacio3d&&!['medio','primer_plano','dividido'].includes(R.encuadre)){
    const zona={arriba:H*(.04+(R.bandas||0)),abajo:H*(.96-(R.bandas||0))};
    // Los títulos de pantalla no siguen a la cámara: reservarles su franja evita
    // que un gráfico completo encajado termine debajo de su propio encabezado.
    for(const item of S0.graficos||[]){
      if(item.capa!=='pantalla'||!['badge','readout','bigLine'].includes(item.tipo))continue;
      const o=item.opciones,y=o.y??(item.tipo==='badge'?110:item.tipo==='readout'?200:H/2),size=o.size??(item.tipo==='bigLine'?84:46);
      if(y<H*.25)zona.arriba=Math.max(zona.arriba,y+size*1.2);
      else if(y>H*.75)zona.abajo=Math.min(zona.abajo,y-size*1.2);
    }
    if(zona.abajo>zona.arriba)encuadrar(cam,draw.limites(),W,H,zona);
  }
  g.setTransform(E.PX,0,0,E.PX,0,0);g.globalAlpha=1;g.globalCompositeOperation='source-over';
  g.clearRect(0,0,W,H);
  // blurLayer atenúa el alpha en los bordes: mantener un respaldo opaco.
  g.fillStyle=R.fondo||paletaEditorial(R.paleta)?.fondo||mood(S0.ambiente).wall;g.fillRect(0,0,W,H);
  const activo=item=>t>=item.inicio&&t<item.fin;
  function efectos(ctx,capa){
    for(const item of S0.efectos_visuales||[])if(item.capa===capa&&activo(item)){
      ctx.save();efecto(ctx,item.tipo,item.opciones,t-item.inicio+(item.desfase||0));ctx.restore();
    }
  }
  const blur=R.desenfoque??(['medio','primer_plano','detalle'].includes(R.encuadre)?5:0);
  function graficos(capa){
    for(const item of S0.graficos||[])if(item.capa===capa&&activo(item)){
      g.save();
      const pintar=()=>conNeon(g,item.neon,item.opciones.color||S().ui.gold,
        ctx=>grafico(ctx,item,t,draw.reparto));
      if(capa==='pantalla')pintar();
      else layer(g,cam,capa==='fondo'?(R.profundidad??.65):1,pintar);
      g.restore();
    }
  }
  if(S0.espacio3d)pintar3D(g,S0,t,D.duracion,draw.estado);
  else if(R.encuadre==='dividido'){
    for(const [i,colors] of [[0,['#061421','#184466']],[1,['#211008','#693414']]]){
      g.save();g.beginPath();g.rect(W*i/2,0,W/2,H);g.clip();
      g.fillStyle=linGrad(g,0,0,0,H,colors);g.fillRect(W*i/2,0,W/2,H);
      FX.pool(g,W*(i?.75:.25),H*.87,W*.25,H*.04,i?'#ff9b50':'#8acbff',.2);g.restore();
    }
  }else{
    blurLayer(g,blur,ctx=>{decorado(ctx,S0,t);efectos(ctx,'fondo');},cam,R.profundidad??.65);
  }
  if(R.encuadre==='dividido')layer(g,cam,1,()=>efectos(g,'fondo'));
  graficos('fondo');
  if(!S0.espacio3d){
    layer(g,cam,1,()=>{
      const panel=(p,fn)=>{
        g.save();
        if(R.encuadre==='dividido'&&p){g.beginPath();g.rect(p==='izquierda'?0:W/2,0,W/2,H);g.clip();}
        fn();g.restore();
      };
      S0.objetos.filter(o=>o.tipo!=='texto'&&o.capa==='fondo'&&t>=o.inicio&&t<o.fin).forEach(o=>draw.objeto(g,o,t));
      S0.personajes.forEach(c=>panel(c.panel,()=>{
        g.save();if(c.rol==='figurante')g.globalAlpha*=.42;
        if(R.encuadre==='primer_plano'&&c.id===R.sujeto&&c.diseno.familia==='classic')draw.rostro(g,c,t);
        else draw.figura(g,c,t);g.restore();
      }));
      S0.objetos.filter(o=>o.tipo!=='texto'&&o.capa!=='fondo'&&t>=o.inicio&&t<o.fin).forEach(o=>{
        const p=o.ancla&&S0.personajes.find(c=>c.id===o.ancla.personaje)?.panel;
        panel(p,()=>draw.objeto(g,o,t));
      });
      efectos(g,'frente');
    });
  }
  graficos('frente');
  if(S0.atmosfera==='lluvia')FX.rain(g,t,{count:120,a:.2});
  else if(S0.atmosfera==='polvo')FX.dust(g,t,{count:25,a:.2});
  else if(S0.atmosfera==='nieve')FX.snow(g,t,{count:80});
  // Primero gradación de la imagen; texto y gráficos conservan contraste y color.
  acabado(g,t,R);
  g.setTransform(E.PX,0,0,E.PX,0,0);
  // Rótulos fuera de la gradación, conservando cámara, posición y ancla del mundo.
  layer(g,cam,1,()=>{
    S0.objetos.filter(o=>o.tipo==='texto'&&activo(o)).forEach(o=>{
      const panel=o.ancla&&S0.personajes.find(c=>c.id===o.ancla.personaje)?.panel;
      g.save();
      if(R.encuadre==='dividido'&&panel){g.beginPath();g.rect(panel==='izquierda'?0:W/2,0,W/2,H);g.clip();}
      draw.objeto(g,o,t);g.restore();
    });
  });
  graficos('pantalla');
  efectos(g,'pantalla');
  if(R.encuadre==='dividido'){g.strokeStyle=alpha(S().ui.gold,.5);g.lineWidth=2;g.beginPath();g.moveTo(W/2,H*.12);g.lineTo(W/2,H*.9);g.stroke();}
  const bars=(R.bandas||0)*H;
  if(bars){g.fillStyle='#000';g.fillRect(0,0,W,bars);g.fillRect(0,H-bars,W,bars);}
  return 1;
}
