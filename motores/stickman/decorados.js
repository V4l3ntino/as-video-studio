// Localizaciones estables, compuestas con el mobiliario y las luces originales.
import { E, mood, alpha, shade, rr, seg, poly, linGrad, rng } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';
import * as FX from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/fx2d.js';
import { blueprint } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/ui2d.js';

export function semillaLugar(lugar) {
  let seed=lugar.semilla??7;
  for(const c of lugar.id||lugar.tipo||'')seed=(Math.imul(seed,31)+c.charCodeAt(0))>>>0;
  return seed;
}

export function decorado(g, escena, t) {
  const R=escena.realizacion||{},lugar=R.escenario||{tipo:escena.decorado},tipo=lugar.tipo;
  const W=E.W,H=E.H,M=mood(escena.ambiente),floor=H*.84,seed=semillaLugar(lugar),random=rng(seed);
  if(R.fondo){g.fillStyle=R.fondo;g.fillRect(-W,-H,W*3,H*3);}
  else if(['grafico','cierre'].includes(R.encuadre)&&tipo==='vacio')blueprint(g,{a:.035});
  else {g.fillStyle=linGrad(g,0,0,0,H,[shade(M.wall,-.3),M.wall,M.floor]);g.fillRect(-W,-H,W*3,H*3);}
  if(tipo==='vacio')return;
  const exterior=['barrio','parque','ciudad','naturaleza'].includes(tipo);
  if(exterior){
    g.fillStyle=linGrad(g,0,0,0,floor,M.sky);g.fillRect(-W,-H,W*3,H+floor);
    if(['night','storm'].includes(escena.ambiente)){
      FX.stars(g,t,{seed,count:75});FX.moon(g,W*.76,H*.16,34);
    }else {FX.sun(g,W*.64,H*.32,50,M.key,M.practical,5);FX.clouds(g,{seed,color:M.key,a:.12});}
    FX.hills(g,{seed,y:floor-H*.05,amp:H*.12,color:shade(M.dark,.08)});
  }else{
    for(let x=0;x<W;x+=W/12){g.strokeStyle=alpha(M.dark,.22);g.lineWidth=2;g.beginPath();g.moveTo(x,0);g.lineTo(x,floor);g.stroke();}
  }
  g.fillStyle=exterior?(tipo==='parque'?M.grass:M.road):M.floor;g.fillRect(-W,floor,W*3,H);
  FX.floorLines(g,floor,H,alpha(M.dark,.25));
  function ventana(x,y,w,h,arch=false){
    FX.windowFrame(g,{x,y,w,h,cols:3,rows:1,frame:M.dark,bar:9,arch},(ctx,xx,yy,ww,hh)=>{
      ctx.fillStyle=linGrad(ctx,0,yy,0,yy+hh,M.sky);ctx.fillRect(xx,yy,ww,hh);
      FX.skyline(ctx,{seed,x:xx,y:yy+hh,w:ww,minH:hh*.1,maxH:hh*.7,color:M.dark,windowColor:M.practical});
    });
  }
  function foco(x,y,len=H*.8,a=.12){FX.lightCone(g,x,y,{len,spread:.55,color:M.key,a});FX.pool(g,x,floor,W*.18,H*.025,M.key,a);}
  function mesa(x,y,w){FX.counter(g,{x,y,w,h:H*.12,color:M.dark,top:shade(M.wall,.15),doors:3});}
  switch(tipo){
    case 'fiesta':
      ventana(W*.02,H*.16,W*.25,H*.4);
      for(let i=0;i<3;i++){
        const x=W*(.4+i*.22),y=H*(.12+random()*.05),w=W*.13,h=H*.16;
        g.fillStyle=M.dark;g.fillRect(x-7,y-7,w+14,h+14);g.fillStyle=['#725044','#315b63','#796431'][i];g.fillRect(x,y,w,h);
        g.fillStyle=alpha(M.key,.18);g.beginPath();g.arc(x+w*.6,y+h*.4,Math.min(w,h)*.2,0,Math.PI*2);g.fill();
      }
      mesa(W*.82,floor,W*.18);foco(W*.38,H*.04);foco(W*.7,H*.04);
      break;
    case 'salon':
      ventana(W*.04,H*.14,W*.29,H*.44);
      rr(g,W*.36,H*.64,W*.39,H*.18,30);g.fillStyle=shade(M.dark,.1);g.fill();
      rr(g,W*.33,H*.72,W*.45,H*.1,20);g.fillStyle=M.dark;g.fill();
      FX.screen(g,{x:W*.72,y:H*.22,w:W*.23,h:H*.25,a:.04});
      FX.pool(g,W*.52,floor,W*.32,H*.04,M.practical,.12);break;
    case 'oficina':
      ventana(W*.04,H*.08,W*.58,H*.6);mesa(W*.68,floor,W*.3);
      FX.chair(g,W*.82,floor,1.5,M.dark);FX.screen(g,{x:W*.74,y:H*.53,w:W*.1,h:H*.12,a:.08});
      FX.lightCone(g,W*.85,H*.1,{len:H*.85,spread:.55,color:M.key,a:.11});break;
    case 'laboratorio':
      FX.screen(g,{x:W*.63,y:H*.2,w:W*.31,h:H*.3,bg:'#10232c',glowC:M.practical,a:.08});
      FX.chair(g,W*.32,floor,2.4,M.dark);
      for(let i=0;i<3;i++){g.fillStyle=shade(M.dark,.05*i);g.fillRect(W*.03,H*(.32+i*.13),W*.09,H*.11);}
      foco(W*.32,H*.06,H*.85,.13);break;
    case 'barrio':
      for(const [x,w,h] of [[W*.03,W*.32,H*.48],[W*.64,W*.32,H*.53]]){
        FX.facade(g,{x,y:floor,w,h,color:M.wall,win:M.practical,dark:M.dark,cols:2,rows:2,lit:.25,seed,door:true});
        poly(g,[[x-w*.05,floor-h],[x+w*.5,floor-h-H*.14],[x+w*1.05,floor-h]],M.dark);
      }
      FX.lampPost(g,W*.5,floor,H*.58,{color:M.dark,light:M.practical,a:.18});break;
    case 'parque':
      for(let i=0;i<9;i++)FX.tree(g,W*(i/8),floor-H*.05,.8+random()*.6,shade(M.dark,.04));
      seg(g,[[W*.66,floor],[W*.69,H*.3],[W*.92,H*.3],[W*.95,floor]],9,M.dark);
      for(const x of [.75,.85]){seg(g,[[W*x,H*.3],[W*(x-.02),H*.7]],3,M.dark);g.fillStyle=M.dark;g.fillRect(W*(x-.04),H*.7,W*.05,10);}
      break;
    case 'cocina':
      ventana(W*.05,H*.19,W*.28,H*.35);mesa(0,floor,W*.72);
      g.fillStyle=shade(M.wall,.15);g.fillRect(W*.82,H*.26,W*.16,H*.58);
      seg(g,[[W*.82,H*.48],[W*.98,H*.48]],4,M.dark);
      FX.lightCone(g,W*.5,H*.05,{len:H*.85,color:M.key,spread:.7,a:.15});break;
    case 'teatro':
      g.fillStyle='#261523';g.fillRect(0,0,W,floor);
      for(let x=0;x<W;x+=W/36){g.fillStyle=x%(W/18)<W/36?'#58232c':'#311623';g.fillRect(x,0,W/72,floor);}
      foco(W*.5,H*.02,H,.2);FX.crowd(g,t,{seed,y:H*.96,rows:2,w:W,color:M.dark,size:1.5,flags:0});break;
    case 'aula':
      rr(g,W*.3,H*.16,W*.61,H*.45,12);g.fillStyle='#79533b';g.fill();
      rr(g,W*.31,H*.18,W*.59,H*.41,5);g.fillStyle='#24473d';g.fill();
      g.fillStyle='#9f7950';g.fillRect(W*.29,H*.6,W*.63,14);foco(W*.6,H*.04,H,.07);break;
    case 'ciudad':FX.skyline(g,{seed,y:floor,w:W,maxH:H*.6,color:M.dark});break;
    case 'naturaleza':for(let i=0;i<8;i++)FX.pine(g,W*i/7,floor,1+random(),M.dark);break;
    default:ventana(W*.65,H*.18,W*.22,H*.4);break;
  }
}
