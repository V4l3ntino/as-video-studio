// Calle comercial: edificios laterales en perspectiva, escaparates y acera común.
import { E, linGrad, glow, poly, seg, shade, alpha, rng } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';

const noche=e=>['night','storm'].includes(e.ambiente);
const atardecer=e=>e.ambiente==='golden';
function pol(g,p,color){poly(g,p.map(([x,y])=>[x*E.W,y*E.H]),color);}
function linea(g,p,color,w=2){seg(g,p.map(([x,y])=>[x*E.W,y*E.H]),w,color);}
function circulo(g,x,y,r,color){g.fillStyle=color;g.beginPath();g.arc(x*E.W,y*E.H,r*E.H,0,Math.PI*2);g.fill();}

export function fondoCalle(g,escena,seed){
  const W=E.W,H=E.H,oscuro=noche(escena),dorado=atardecer(escena),random=rng(seed);
  const cielo=oscuro?['#101a36','#283556','#62516c']:dorado?
    ['#303d76','#68557f','#c9758b','#ff9a6a','#ffb866']:['#527da2','#9bbccd','#e8d4b2'];
  g.fillStyle=linGrad(g,0,-H*.1,0,H*.72,cielo);g.fillRect(-W,-H,W*3,H*3);
  if(oscuro){
    for(let i=0;i<65;i++)circulo(g,.18+random()*.65,random()*.5,.0006+random()*.0007,'#dce5f3');
    glow(g,W*.59,H*.28,H*.1,'#cddcf5',.13);circulo(g,.59,.28,.027,'#dce5ef');
  }else{
    const y=dorado?.39:.25,color=dorado?'#ffd080':'#fff1cd';
    glow(g,W*.53,H*y,H*(dorado?.32:.24),dorado?'#ff9d54':'#ffe9b6',dorado?.42:.24);
    circulo(g,.53,y,dorado?.055:.035,color);
  }
  for(let i=0;i<7;i++){
    const x=.18+random()*.5,y=.08+random()*.31,w=.08+random()*.16;
    pol(g,[[x,y],[x+w*.5,y+.008],[x+w,y+.022],[x+w*.4,y+.025]],
      oscuro?'#68718b30':dorado?'#ec9c9b55':'#e7e8db55');
  }
  // Tres escalas de edificios lejanos, sin tejados de vivienda unifamiliar.
  for(let plano=0;plano<3;plano++){
    const base=.65+plano*.018;
    for(let i=0;i<15;i++){
      const x=.27+i*.034,w=.025+random()*.018,h=.06+random()*(.18-plano*.04);
      const c=['#6a657f','#4d536e','#363f59'][plano];
      pol(g,[[x,base],[x,base-h],[x+w,base-h],[x+w,base]],c);
      for(let fila=0;fila<4;fila++)for(let col=0;col<2;col++)if(random()>.5){
        const xx=x+.006+col*.011,yy=base-h+.013+fila*.027;
        if(yy<base-.012)pol(g,[[xx,yy],[xx+.003,yy],[xx+.003,yy+.008],[xx,yy+.008]],'#e4b472');
      }
    }
  }
}

function fachada(g,escena,x0,x1,t0,t1,b0,b1,color,indice){
  // Proyección de cada detalle sobre el mismo cuadrilátero de fachada.
  const punto=(u,v)=>{const top=t0+(t1-t0)*u,bot=b0+(b1-b0)*u;
    return [x0+(x1-x0)*u,top+(bot-top)*v];};
  const caja=(u,v,w,h,c)=>pol(g,[punto(u,v),punto(u+w,v),punto(u+w,v+h),punto(u,v+h)],c);
  const trazo=(u,v,uu,vv,c,w=2)=>linea(g,[punto(u,v),punto(uu,vv)],c,w);
  const oscuro=noche(escena),dorado=atardecer(escena),lugar=escena.realizacion.escenario;
  const material=lugar.fachada||color;
  caja(0,0,1,1,linGrad(g,x0*E.W,0,x1*E.W,E.H,[shade(material,oscuro?-.52:-.2),shade(material,oscuro?-.30:.08)]));
  // Ladrillo y cornisas: textura subordinada a los escaparates.
  for(let fila=1;fila<27;fila++){
    const v=fila/27;trazo(0,v,1,v,alpha('#e8c4aa',.10),1);
    for(let col=0;col<7;col++){
      const u=(col+(fila%2)*.5)/7;
      if(u<1)trazo(u,v,u,v+1/27,alpha('#241e2d',.13),1);
    }
  }
  caja(0,.01,1,.025,'#35303d');caja(0,.045,1,.025,shade(material,.25));
  for(const u of [.12,.57])for(const v of [.13,.34]){
    caja(u-.018,v-.012,.30,.175,'#403844');
    caja(u,v,.265,.15,linGrad(g,0,E.H*.2,0,E.H*.6,['#e5a76e','#ffe0a1']));
    trazo(u+.13,v,u+.13,v+.15,'#4b3b3c',5);trazo(u,v+.075,u+.265,v+.075,'#4b3b3c',4);
    caja(u-.025,v+.15,.315,.016,'#564652');
  }
  // Vitrina continua con luz interior, estantes y objetos a escala del edificio.
  caja(.065,.59,.87,.35,'#282633');
  caja(.085,.61,.83,.30,linGrad(g,0,E.H*.5,0,E.H*.9,oscuro?['#ad784d','#614534']:['#d89c65','#825a42']));
  for(const v of [.70,.80]){
    caja(.13,v,.72,.008,'#654937');
    for(let k=0;k<7;k++)caja(.14+k*.095,v-.035-(k%3)*.008,.045,.035+(k%3)*.008,['#a58055','#bc9469','#785947'][k%3]);
  }
  // Lámparas del local y reflejos diagonales recortados dentro de los cristales.
  for(const u of [.27,.71]){
    trazo(u,.61,u,.65,'#554039',2);
    const [x,y]=punto(u,.655);circulo(g,x,y,.006/(indice+1),'#ffdf9e');
    glow(g,x*E.W,y*E.H,E.H*.04/(indice+1),'#ffc979',.12);
  }
  pol(g,[punto(.11,.62),punto(.22,.62),punto(.50,.90),punto(.39,.90)],'#fff0d315');
  for(const u of [.36,.64])trazo(u,.61,u,.91,'#49383a',5);
  caja(.055,.91,.90,.075,'#4d3d42');
  const toldo=indice%2?'#855448':'#27394f';
  caja(.03,.555,.94,.055,toldo);
  pol(g,[punto(.03,.555),punto(.97,.555),punto(1.04,.61),punto(-.04,.61)],shade(toldo,.12));
  trazo(-.04,.61,1.04,.61,dorado?'#eab268':'#ac8c69',3);
  for(let k=0;k<9;k++)caja(-.04+k*.12,.61,.12,.017,shade(toldo,k%2?-.15:-.05));
}

function arbol(g,x,y,s){
  // Copa agrupada y tronco ramificado, sin tapar las trayectorias centrales.
  const H=E.H;
  for(const [dx,dy,r] of [[-.023,-.19,.052],[.022,-.19,.057],[0,-.24,.06]]){
    circulo(g,x+dx*s,y+dy*s,r*s,'#dca75c');
    circulo(g,x+(dx-.003)*s,y+(dy+.003)*s,r*s,'#344b42');
  }
  linea(g,[[x,y],[x,y-.22*s]],'#554237',H*.009*s);
  linea(g,[[x,y-.14*s],[x-.025*s,y-.20*s]],'#554237',H*.004*s);
  linea(g,[[x,y-.17*s],[x+.022*s,y-.235*s]],'#554237',H*.004*s);
}

function farola(g,x,y,s,encendida){
  const H=E.H,color='#282936',luz='#ffd494';
  linea(g,[[x,y],[x,y-.48*s],[x-.009*s,y-.49*s],[x-.039*s,y-.49*s]],color,H*.009*s);
  pol(g,[[x-.012*s,y],[x+.012*s,y],[x+.012*s,y-.04*s],[x-.012*s,y-.04*s]],'#242734');
  if(encendida){
    glow(g,(x-.04*s)*E.W,(y-.48*s)*H,H*.095*s,luz,.40);
    const grad=g.createRadialGradient(x*E.W,y*H,0,x*E.W,y*H,H*.16*s);
    grad.addColorStop(0,'#ffc87c40');grad.addColorStop(1,'#ffc87c00');g.fillStyle=grad;
    g.beginPath();g.ellipse(x*E.W,y*H,H*.16*s,H*.025*s,0,0,Math.PI*2);g.fill();
  }
  circulo(g,x-.04*s,y-.48*s,.016*s,encendida?'#fff2bb':'#a7a49a');
  pol(g,[[x-.064*s,y-.484*s],[x-.057*s,y-.50*s],[x-.027*s,y-.50*s],[x-.017*s,y-.484*s]],'#59453a');
}

export function sueloCalle(g,escena){
  const W=E.W,H=E.H,lugar=escena.realizacion.escenario,oscuro=noche(escena),dorado=atardecer(escena);
  g.fillStyle=linGrad(g,0,H*.65,0,H,oscuro?['#4b4854','#252c3e']:['#a08d8b','#55576c']);g.fillRect(-W,H*.65,W*3,H);
  // Juntas convergentes y separación de las aceras laterales.
  for(const x of [-.6,-.15,.18,.40,.65,.9,1.3,1.8])linea(g,[[.53,.64],[x,1.25]],'#34334488',2);
  for(const y of [.68,.71,.76,.83,.94,1.10])linea(g,[[-.2,y],[1.2,y]],'#3b384b80',2);
  for(const lado of [0,1]){
    g.save();if(lado){g.translate(W,0);g.scale(-1,1);}
    if(lugar.edificios!==false){
      fachada(g,escena,.35,.43,.29,.40,.69,.66,'#75636e',2);
      fachada(g,escena,.21,.35,.10,.29,.78,.69,'#8e6b70',1);
      fachada(g,escena,-.025,.21,-.18,.10,.94,.78,'#9c7473',0);
    }
    arbol(g,.31,.72,1.15);arbol(g,.40,.67,.36);
    farola(g,.275,.86,1.4,dorado||oscuro);farola(g,.405,.70,.46,dorado||oscuro);
    // Jardineras bajas, fuera del paso de los personajes.
    for(const [x,y,s] of [[.035,.98,1],[.35,.72,.40]]){
      for(let k=0;k<5;k++)circulo(g,x+(k-2)*.013*s,y-.055*s-(k%2)*.01*s,.027*s,'#3c5344');
      pol(g,[[x-.055*s,y-.055*s],[x+.055*s,y-.055*s],[x+.055*s,y],[x-.055*s,y]],'#33394a');
      linea(g,[[x-.055*s,y-.055*s],[x+.055*s,y-.055*s]],'#a58c79',3);
    }
    g.restore();
  }
}
