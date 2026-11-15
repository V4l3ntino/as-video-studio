// Portadas numeradas dentro del reloj de la escena, con fondo y tipografía propios.
import { E, text, alpha, glow, rng, ease, prog, FONTS } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';
import { dust } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/fx2d.js';
import { rotulo } from './kit.js';
import { conNeon } from './neon.js';

const COLORES={arctic:'#76ccff',ember:'#ff8d38',mixto:'#ffcf70',sakura:'#ff78b9',retro:'#e9b938'};

export function pintarCapitulo(g,item,t,r){
  const o=item.opciones,W=E.W,H=E.H,estilo=o.estilo||'mixto',color=o.color||COLORES[estilo];
  const local=t-item.inicio+(item.desfase||0),reloj=t+(r.desfase_ambiente||0);
  const dur=item.fin-item.inicio,p=ease.out(prog(local,0,Math.min(.45,dur*.18)));
  g.save();g.fillStyle='#06080e';g.fillRect(0,0,W,H);
  const frio=estilo==='arctic'||estilo==='mixto',calido=estilo==='ember'||estilo==='mixto';
  if(frio)glow(g,W*.05,H*.42,W*.72,'#69c6ff',.18);
  if(calido)glow(g,W*.98,H*.42,W*.65,'#f58639',.17);
  if(!frio&&!calido)glow(g,W*.18,H*.42,W*.7,estilo==='sakura'?'#a54588':'#5b8c83',.20);
  if(o.particulas??r.particulas??true){
    const seed=o.numero*137+24;
    if(frio){
      const random=rng(seed),ancho=estilo==='mixto'?W*.51:W;
      for(let i=0;i<30;i++){
        const s=.6+random(),fase=random()*Math.PI*2;
        const x=random()*ancho+Math.sin(reloj*.15+fase)*12,y=(random()*H+reloj*6*s)%H,rad=2+s*2.3;
        g.strokeStyle=alpha('#bee7ff',.17+random()*.17);g.lineWidth=1.2;
        g.beginPath();g.moveTo(x-rad,y);g.lineTo(x+rad,y);g.moveTo(x,y-rad);g.lineTo(x,y+rad);g.stroke();
      }
    }
    if(calido||!frio)dust(g,reloj,{seed,count:34,color:estilo==='sakura'?'#ffd3e9':'#ffd6a0',
      area:estilo==='mixto'?[W*.5,0,W*.5,H]:[0,0,W,H],size:3.1,speed:8,a:.4});
  }
  g.globalAlpha=p;g.translate(0,(1-p)*18);
  conNeon(g,.42,color,ctx=>text(ctx,String(o.numero).padStart(2,'0'),W/2,H*.28,
    {font:FONTS.title,weight:700,size:Math.min(220,H*.28),color}));
  g.strokeStyle=alpha(color,.8);g.lineWidth=2;g.beginPath();
  const ancho=W*.45*p;g.moveTo(W/2-ancho/2,H*.46);g.lineTo(W/2+ancho/2,H*.46);g.stroke();
  conNeon(g,.12,'#fff1dc',ctx=>rotulo(ctx,o.titulo.toLocaleUpperCase(),W/2,H*.64,W*.82,
    Math.min(92,H*.13),'#fff1dc'));
  g.restore();
}
