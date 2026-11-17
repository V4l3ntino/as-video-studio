// Arquitectura residencial en perspectiva: capas locales, sin imágenes externas.
import { E, linGrad, glow, poly, seg, shade, rng } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';

const p=(g,pts,c)=>poly(g,pts.map(([x,y])=>[x*E.W,y*E.H]),c);
const l=(g,pts,c,w=3)=>seg(g,pts.map(([x,y])=>[x*E.W,y*E.H]),w,c);
function disco(g,x,y,r,c){g.fillStyle=c;g.beginPath();g.arc(x*E.W,y*E.H,r*E.H,0,Math.PI*2);g.fill();}
const nocturno=e=>['night','storm'].includes(e.ambiente);

export function fondoResidencial(g,e,seed){
  const W=E.W,H=E.H,noche=nocturno(e),random=rng(seed+211);
  g.fillStyle=linGrad(g,0,0,0,H,noche?['#071a38','#103767','#466789']:['#789fbb','#c4d9dd','#f0d8b5']);
  g.fillRect(-W,-H,W*3,H*3);
  if(noche){
    for(let i=0;i<90;i++)disco(g,random(),random()*.52,.0007+random()*.001,'#d8eaff');
    glow(g,W*.29,H*.16,H*.18,'#b8ddff',.18);disco(g,.29,.16,.06,'#dcefff');
    disco(g,.282,.14,.012,'#b7d9ef');disco(g,.31,.18,.009,'#b7d9ef');
  }
  // Horizontes superpuestos y silueta de ciudad lejana.
  p(g,[[0,.64],[.15,.47],[.28,.60],[.43,.46],[.57,.58],[.72,.43],[1,.62],[1,.78],[0,.78]],noche?'#17385f':'#91a5aa');
  p(g,[[0,.72],[.2,.59],[.34,.68],[.50,.53],[.67,.67],[.83,.55],[1,.68],[1,.8],[0,.8]],noche?'#102b50':'#738e92');
  for(let i=0;i<27;i++){
    const x=.28+i*.017,h=.025+random()*.09,w=.009+random()*.012;
    p(g,[[x,.65],[x,.65-h],[x+w,.65-h],[x+w,.65]],noche?'#0c203b':'#657d88');
    if(noche && i%2===0)p(g,[[x+.003,.64-h*.45],[x+.006,.64-h*.45],[x+.006,.647-h*.45],[x+.003,.647-h*.45]],'#f6cd80');
  }
}

function casa(g,e,a,b,indice,laboratorio){
  const lugar=e.realizacion.escenario,noche=nocturno(e),ink='#101827';
  // Cada fachada y sus detalles comparten la misma proyección trapezoidal.
  const punto=(u,v)=>[a.x+(b.x-a.x)*u,(a.top+(b.top-a.top)*u)*(1-v)+(a.base+(b.base-a.base)*u)*v];
  const caja=(u,v,w,h,c)=>p(g,[punto(u,v),punto(u+w,v),punto(u+w,v+h),punto(u,v+h)],c);
  const trazo=(u,v,x,y,c=ink,w=4)=>l(g,[punto(u,v),punto(x,y)],c,w);
  const pared=lugar.fachada||['#d6c4b4','#b9b3ba','#e1c8b0','#c6bdb8'][indice%4];
  const techo=lugar.tejado||'#34455e';
  p(g,[punto(0,0),punto(1,0),punto(1,1),punto(0,1)],ink);
  caja(.015,.015,.97,.97,shade(pared,(noche?-.22:0)+(indice%3-1)*.045));
  // Cubierta inclinada y líneas de pizarra convergentes.
  const cumA=[a.x-.015,a.top-.10*(a.base-a.top)],cumB=[b.x-.004,b.top-.10*(b.base-b.top)];
  p(g,[punto(0,0),cumA,cumB,punto(1,0)],ink);
  p(g,[punto(.02,-.012),[cumA[0]+.006,cumA[1]+.009],[cumB[0],cumB[1]+.009],punto(.98,-.012)],techo);
  for(let j=1;j<4;j++){
    const f=j/4;l(g,[[cumA[0]*(1-f)+a.x*f,cumA[1]*(1-f)+a.top*f],
      [cumB[0]*(1-f)+b.x*f,cumB[1]*(1-f)+b.top*f]],'#8b9ab350',2);
  }
  // Frontón y chimenea interrumpen la silueta continua de las cubiertas.
  const medio=(a.x+b.x)/2, cima=Math.min(a.top,b.top)-(a.base-a.top)*.12;
  p(g,[[a.x,a.top],[medio,cima],[b.x,b.top]],ink);
  p(g,[[a.x+.008,a.top-.003],[medio,cima+.012],[b.x-.008,b.top-.003]],techo);
  l(g,[[a.x,a.top],[medio,cima],[b.x,b.top]],ink,5);
  const ancho=(b.x-a.x)*.10, cx=medio-ancho/2,cy=cima+.01;
  p(g,[[cx,cy],[cx,cy-.035],[cx+ancho,cy-.035],[cx+ancho,cy+.015]],ink);
  p(g,[[cx+.003,cy-.005],[cx+.003,cy-.030],[cx+ancho-.003,cy-.030],[cx+ancho-.003,cy+.005]],'#647082');
  caja(0,.83,1,.15,noche?'#51576a':'#8d8587');trazo(0,.83,1,.83,ink,4);
  if(laboratorio){
    caja(.06,.12,.86,.18,ink);caja(.08,.14,.82,.14,'#16547c');
    caja(.06,.37,.63,.43,ink);caja(.085,.40,.58,.37,'#087fa6');
    caja(.095,.42,.56,.03,'#9af3ff');caja(.11,.70,.52,.04,'#b9e7ec');
    // Matraces y tubo, en el plano de la fachada.
    for(const u of [.23,.46]){
      trazo(u,.53,u,.60,'#b3f8ff',3);trazo(u,.60,u-.045,.68,'#b3f8ff',3);
      trazo(u-.045,.68,u+.045,.68,'#b3f8ff',3);trazo(u+.045,.68,u,.60,'#b3f8ff',3);
    }
    caja(.73,.38,.19,.60,ink);caja(.76,.41,.13,.55,'#294b61');
    const [x,y]=punto(.38,.48);glow(g,x*E.W,y*E.H,E.H*.20,'#20cfff',.21);
  }else{
    for(const u of [.12,.57]){
      caja(u,.22,.29,.29,ink);
      const iluminada=(indice+(u>.3?1:0))%3===0;
      caja(u+.025,.24,.24,.25,iluminada?(lugar.luz_ventanas||'#ffce7e'):(noche?'#263b55':'#8fb5c3'));
      trazo(u+.145,.24,u+.145,.49,ink,3);trazo(u+.025,.365,u+.265,.365,ink,3);
      caja(u-.01,.51,.31,.025,'#2b3140');
    }
    caja(.39,.59,.23,.40,ink);caja(.42,.61,.17,.37,noche?'#3c4554':'#665955');
    caja(.44,.65,.13,.10,noche?'#e1b875':'#a9c3c8');
  }
  trazo(0,0,1,0,ink,6);trazo(0,0,0,1,ink,5);
}

function farola(g,x,y,s,encendida){
  const ink='#101827';
  l(g,[[x,y],[x,y-.34*s],[x-.008*s,y-.39*s],[x-.035*s,y-.40*s],[x-.065*s,y-.38*s]],ink,12*s);
  p(g,[[x-.022*s,y],[x+.022*s,y],[x+.016*s,y-.05*s],[x-.016*s,y-.05*s]],ink);
  if(encendida)glow(g,(x-.065*s)*E.W,(y-.36*s)*E.H,E.H*.13*s,'#ffc36b',.42);
  disco(g,x-.065*s,y-.36*s,.023*s,encendida?'#ffe09b':'#a7b7b9');
  p(g,[[x-.095*s,y-.38*s],[x-.085*s,y-.40*s],[x-.045*s,y-.40*s],[x-.034*s,y-.38*s]],ink);
}

export function sueloResidencial(g,e){
  const W=E.W,H=E.H,noche=nocturno(e),lugar=e.realizacion.escenario;
  g.fillStyle=linGrad(g,0,H*.64,0,H,noche?['#294566','#111d37']:['#9ba7ac','#606c7f']);g.fillRect(-W,H*.63,W*3,H);
  // Calzada, bordillos y aceras comparten un punto de fuga.
  p(g,[[.48,.64],[.53,.64],[1.25,1.18],[-.25,1.18]],noche?'#172943':'#6c7883');
  for(const lado of [0,1]){
    g.save();if(lado){g.translate(W,0);g.scale(-1,1);}
    p(g,[[0,.70],[.47,.64],[.08,1.12],[0,1.12]],noche?'#59677c':'#b5afa5');
    l(g,[[.47,.64],[.08,1.12]],'#121d2d',8);l(g,[[.46,.65],[.07,1.13]],'#af9c89',3);
    for(const x of [-.2,-.05,.12,.25,.35,.42])l(g,[[.47,.64],[x,1.10]],'#28354a',3);
    if(lugar.edificios!==false){
      const edificios=[{x:.42,top:.52,base:.67},{x:.35,top:.43,base:.70},
        {x:.24,top:.30,base:.76},{x:.08,top:.12,base:.85},{x:-.13,top:-.09,base:.99}];
      for(let i=0;i<edificios.length-1;i++)casa(g,e,edificios[i+1],edificios[i],i+(lado?1:0),!lado&&i===2&&lugar.laboratorio);
    }
    for(const [x,y,s] of [[.40,.70,.33],[.32,.77,.62],[.17,.91,1.15]])farola(g,x,y,s,noche);
    g.restore();
  }
  // Línea central discontinua y reflejos discretos, sin alterar la narración.
  for(const [y,w,h] of [[.68,.004,.015],[.72,.006,.024],[.78,.009,.035],[.87,.014,.055]])
    p(g,[[.505-w,y],[.505+w,y],[.505+w*1.3,y+h],[.505-w*1.3,y+h]],noche?'#a3b2c8':'#ede1bd');
}
