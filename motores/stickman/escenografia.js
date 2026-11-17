// Escenografía material en tres planos: arquitectura, suelo/utilería y primer término.
import { E, alpha, shade, mix, linGrad, glow, rng, poly, seg, rr } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';
import * as FX from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/fx2d.js';
import { semillaLugar } from './decorados.js';
import { fondoCalle, sueloCalle } from './calle.js';
import { fondoCine, sueloCine, frenteCine } from './cine.js';
import { fondoResidencial, sueloResidencial } from './calle_residencial.js';

const TIPOS=new Set(['teatro','cine','fiesta','salon','oficina','laboratorio','cocina','aula','barrio','calle_comercial','calle_residencial','parque','interior','ciudad','naturaleza']);
export const tipoEscenografia=escena=>escena.realizacion?.escenario?.tipo||escena.decorado;
export function usaEscenografia(escena){
  return Boolean(escena.realizacion?.escenografia_detallada&&!escena.realizacion.comparacion&&
    escena.realizacion.encuadre!=='dividido'&&!escena.espacio3d&&TIPOS.has(tipoEscenografia(escena)));
}
export function luzEscenografia(escena){
  const tipo=tipoEscenografia(escena);
  return escena.realizacion.escenario?.luz||(tipo==='calle_comercial'?'#ffc16b':tipo==='teatro'?'#ffe1ad':
    ['laboratorio','oficina'].includes(tipo)||(['barrio','parque','ciudad','naturaleza'].includes(tipo)&&
      ['night','storm'].includes(escena.ambiente))?'#c6e6f4':'#ffe4bd');
}
function datos(escena){
  const tipo=tipoEscenografia(escena),lugar=escena.realizacion.escenario||{};
  return {tipo,lugar,seed:semillaLugar(lugar),dia:['day','golden'].includes(escena.ambiente),W:E.W,H:E.H};
}
function caja(g,x,y,w,h,color,radio=6){
  rr(g,x,y,w,h,radio);g.fillStyle=linGrad(g,x,y,x+w,y+h,[shade(color,.12),color,shade(color,-.24)]);g.fill();
  g.strokeStyle=alpha('#fff5e0',.12);g.lineWidth=1.5;g.stroke();
}
function suelo(g,escena){
  const {tipo,W,H,dia,seed}=datos(escena),y=H*.83;
  const baldosa=['laboratorio','cocina'].includes(tipo),base=baldosa?'#718183':tipo==='oficina'?'#454b50':'#825331';
  const material=dia?base:shade(base,-.34);
  g.fillStyle=linGrad(g,0,y,0,H*1.3,[shade(material,-.45),material,shade(material,-.30)]);
  g.fillRect(-W,y,W*3,H*1.5);
  const random=rng(seed+37),filas=baldosa?5:7;
  for(let i=0;i<=filas;i++){
    const z=i/filas,yy=y+H*.48*z*z;
    seg(g,[[-W,yy],[W*2,yy]],1.5,alpha('#100c0b',.4));
    if(i<filas){
      const siguiente=y+H*.48*((i+1)/filas)**2;
      for(let j=-2;j<14;j++){
        const x=(j+(i%2)*.5)*W/10;
        seg(g,[[W/2+(x-W/2)*(.8+z*.2),yy],[W/2+(x-W/2)*(.8+(i+1)/filas*.2),siguiente]],1.3,alpha('#120d0b',.32));
        if(!baldosa){
          const gy=yy+(siguiente-yy)*(.2+random()*.6);
          seg(g,[[x+8,gy],[x+W*(.025+random()*.05),gy+1]],.8,alpha('#e9ba7a',.12));
        }
      }
    }
  }
  seg(g,[[-W,y],[W*2,y]],4,alpha('#110c0b',.7));
}
function ventana(g,x,y,w,h,dia,seed,interior=false){
  caja(g,x-9,y-9,w+18,h+18,'#342d28',5);
  g.fillStyle=linGrad(g,x,y,x,y+h,interior?['#756246','#c0a477']:dia?['#739db7','#c5d9dc']:['#0c1526','#283a50']);g.fillRect(x,y,w,h);
  if(!dia&&!interior){
    g.save();g.beginPath();g.rect(x,y,w,h);g.clip();
    FX.skyline(g,{seed,x,y:y+h,w,minH:h*.12,maxH:h*.7,color:'#101923',windowColor:'#e8bb72'});g.restore();
  }
  for(const xx of [x+w/3,x+w*2/3])seg(g,[[xx,y],[xx,y+h]],6,'#282b2b');
  seg(g,[[x,y+h*.5],[x+w,y+h*.5]],5,'#282b2b');
  poly(g,[[x+w*.04,y],[x+w*.25,y],[x+w*.7,y+h],[x+w*.54,y+h]],'#d9efff10');
  caja(g,x-18,y+h,w+36,10,'#706256',3);
}
function telon(g,W,H,seed,color='#652622'){
  const random=rng(seed),paso=W/30;
  g.fillStyle=shade(color,-.8);g.fillRect(-W,-H,W*3,H*2.4);
  for(let i=-1;i<32;i++){
    const x=i*paso,w=paso*(.92+random()*.16),brillo=.03+random()*.08;
    g.fillStyle=linGrad(g,x,0,x+w,0,[[0,shade(color,-.75)],[.18,shade(color,-.46)],[.43,shade(color,brillo)],
      [.63,shade(color,-.28)],[.88,shade(color,-.65)],[1,shade(color,-.82)]]);
    g.beginPath();g.moveTo(x,-H*.2);g.bezierCurveTo(x+w*.08,H*.26,x-w*.10,H*.70,x+w*.03,H*1.15);
    g.lineTo(x+w,H*1.15);g.bezierCurveTo(x+w*.85,H*.75,x+w*1.08,H*.22,x+w,-H*.2);g.closePath();g.fill();
  }
  g.fillStyle=linGrad(g,0,0,0,H,[alpha('#000000',.30),alpha('#000000',0),alpha('#000000',.28)]);
  g.fillRect(-W,-H*.1,W*3,H*1.3);
}

export function fondoEscenografia(g,escena,t){
  const {tipo,W,H,dia,seed}=datos(escena),r=escena.realizacion;
  if(tipo==='cine'){fondoCine(g,escena,t,seed);return;}
  if(tipo==='calle_comercial'){fondoCalle(g,escena,seed);return;}
  if(tipo==='calle_residencial'){fondoResidencial(g,escena,seed);return;}
  if(tipo==='teatro'){
    telon(g,W,H,seed,r.fondo);
    return;
  }
  const exterior=['barrio','parque','ciudad','naturaleza'].includes(tipo);
  if(exterior){
    g.fillStyle=linGrad(g,0,0,0,H,dia?['#587a96','#a6c3ce','#e4d6b8']:['#07101d','#162b42','#405169']);
    g.fillRect(-W,-H,W*3,H*2.5);
    if(!dia){FX.stars(g,t,{seed,count:45});FX.moon(g,W*.76,H*.17,30,'#e5edf6');}
    else{FX.sun(g,W*.74,H*.18,46,'#fff0cf','#ffe0a0',4);FX.clouds(g,{seed,y:H*.25,h:H*.25,color:'#f0ede2',a:.25});}
    FX.hills(g,{seed,y:H*.72,amp:H*.12,color:dia?'#536d61':'#1b3035'});
    return;
  }
  const bases={laboratorio:'#bbcbd0',oficina:'#b3b6b2',cocina:'#c7bcab',aula:'#c6b48e',fiesta:'#73534a'};
  const material=bases[tipo]||'#aa9b88',pared=r.fondo||(dia?material:mix(material,'#101521',.73));
  g.fillStyle=linGrad(g,0,0,W,H,[shade(pared,-.25),pared,shade(pared,-.25)]);g.fillRect(-W,-H,W*3,H*2);
  for(let x=0;x<W;x+=W/12)seg(g,[[x,0],[x,H]],1,alpha('#fff0d7',.035));
  seg(g,[[0,H*.815],[W,H*.815]],8,shade(material,-.65));
  if(['fiesta','salon','interior','oficina','aula'].includes(tipo)){
    ventana(g,W*.045,H*.14,W*(tipo==='oficina'?.52:.25),H*.40,dia,seed);
    glow(g,W*.17,H*.48,W*.35,dia?'#c9eaff':'#edc486',.09);
  }
  if(tipo==='fiesta'){
    for(let i=0;i<3;i++){
      const x=W*(.41+i*.20),y=H*(.13+(i%2)*.02),w=W*.13,h=H*.17;
      caja(g,x-7,y-7,w+14,h+14,'#281d18',2);
      g.fillStyle=['#845142','#3d7075','#8d7136'][i];g.fillRect(x,y,w,h);
      glow(g,x+w*.62,y+h*.4,Math.min(w,h)*.28,['#d29b75','#73aab0','#dab66a'][i],.35);
    }
  }else if(tipo==='laboratorio'||tipo==='cocina'){
    const y0=H*.27,y1=H*.78;
    for(let x=0;x<W;x+=W/12)seg(g,[[x,y0],[x,y1]],2,alpha('#1b333d',.16));
    for(let y=y0;y<y1;y+=H*.09)seg(g,[[0,y],[W,y]],2,alpha('#1b333d',.16));
    if(tipo==='laboratorio'){
      for(let i=0;i<3;i++)caja(g,W*(.07+i*.13),H*.24,W*.115,H*.24,dia?'#bac5c6':'#405154');
      for(const x of [.22,.72]){
        caja(g,W*(x-.10),H*.07,W*.20,H*.018,'#c6d5d5',3);
        glow(g,W*x,H*.10,W*.26,'#d0edf0',.09);
      }
    }else{
      for(let i=0;i<4;i++){
        const x=W*(.34+i*.115);caja(g,x,H*.16,W*.105,H*.26,dia?'#ad9778':'#615343');
        seg(g,[[x+W*.08,H*.25],[x+W*.08,H*.31]],3,'#c9c5b8');
        g.fillStyle='#e9d2a2';g.fillRect(x+5,H*.422,W*.095,3);
        glow(g,x+W*.05,H*.445,W*.09,'#ffdfa5',.11);
      }
      ventana(g,W*.045,H*.18,W*.24,H*.31,dia,seed);
    }
  }else if(tipo==='aula'){
    caja(g,W*.36,H*.16,W*.57,H*.43,'#795538',7);
    g.fillStyle=linGrad(g,W*.37,H*.18,W*.92,H*.57,['#294d40','#152e2a']);g.fillRect(W*.37,H*.18,W*.55,H*.39);
    for(let i=0;i<9;i++)seg(g,[[W*(.4+i*.055),H*(.27+(i%3)*.09)],
      [W*(.45+i*.055),H*(.275+(i%3)*.09)]],5,'#dce4c509');
    caja(g,W*.35,H*.59,W*.60,12,'#a38157',2);
    caja(g,W*.78,H*.575,W*.04,10,'#c4ac83',2);
    caja(g,W*.50,H*.10,W*.26,H*.016,'#cbbd98',3);glow(g,W*.63,H*.12,W*.28,'#f4dda9',.09);
  }
}

function mesa(g,x,sueloY,w,h,color='#5e4534'){
  caja(g,x-w*.44,sueloY-h,w*.88,h*.85,color,5);
  for(let i=1;i<3;i++)seg(g,[[x-w*.44+w*.88*i/3,sueloY-h],[x-w*.44+w*.88*i/3,sueloY-h*.15]],2,shade(color,-.4));
  caja(g,x-w/2,sueloY-h-12,w,18,shade(color,.30),3);
  for(const dx of [-.36,.36])caja(g,x+w*dx,sueloY-h*.17,w*.025,h*.17,'#29272a',2);
}
function atril(g,x,y,W,H){
  const w=W*.095,h=H*.235;
  poly(g,[[x-w*.43,y-h],[x+w*.43,y-h],[x+w*.36,y],[x-w*.36,y]],'#302018');
  g.fillStyle=linGrad(g,x-w*.4,y-h,x+w*.4,y,['#493024','#241712','#38231a']);g.fillRect(x-w*.36,y-h,w*.72,h);
  caja(g,x-w/2,y-h-10,w,12,'#cca358',2);
  seg(g,[[x-w*.28,y-h*.85],[x-w*.28,y-h*.05]],1,'#b5895326');
}
function lamparaMesa(g,x,y,W,H){
  seg(g,[[x,y],[x,y-H*.12]],5,'#716455');
  caja(g,x-W*.024,y-5,W*.048,8,'#72665a',4);
  poly(g,[[x-W*.027,y-H*.17],[x+W*.027,y-H*.17],[x+W*.048,y-H*.105],[x-W*.048,y-H*.105]],'#b99c6d');
  glow(g,x,y-H*.11,W*.17,'#ffd79c',.16);
  FX.pool(g,x,y+H*.17,W*.15,H*.025,'#ffdcaa',.12);
}
function haz(g,x,y,color,W){
  g.save();g.globalCompositeOperation='screen';
  for(const [ancho,a] of [[.18,.025],[.15,.035],[.11,.04],[.065,.03]]){
    g.fillStyle=linGrad(g,0,0,0,y,[alpha(color,0),alpha(color,a*.75),alpha(color,a)]);
    poly(g,[[x+W*.03-8,0],[x+W*.03+8,0],[x+W*ancho,y],[x-W*ancho,y]],g.fillStyle);
  }
  g.restore();FX.pool(g,x,y,W*.17,E.H*.027,color,.32);
}

export function sueloEscenografia(g,escena,t,luz){
  const {tipo,W,H,dia,seed,lugar}=datos(escena);
  if(tipo==='cine'){sueloCine(g);return;}
  if(tipo==='calle_comercial'){sueloCalle(g,escena);return;}
  if(tipo==='calle_residencial'){sueloResidencial(g,escena);return;}
  const exterior=['barrio','parque','ciudad','naturaleza'].includes(tipo);
  if(!exterior)suelo(g,escena);
  else{
    g.fillStyle=linGrad(g,0,H*.79,0,H,[dia?'#5a7350':'#263a2e',dia?'#344c32':'#17281e']);g.fillRect(-W,H*.79,W*3,H);
    poly(g,[[W*.43,H*.76],[W*.58,H*.76],[W*.8,H*1.2],[W*.14,H*1.2]],dia?'#998978':'#4c4b47');
  }
  if(tipo==='teatro'){
    haz(g,luz.x,luz.y,luzEscenografia(escena),W);
    if(lugar.atril)atril(g,W*(lugar.atril_x??.61),H*.87,W,H);
    for(let i=0;i<13;i++){
      const x=W*(.045+i*.076);glow(g,x,H*.965,18,'#ffdc9c',.28);
      caja(g,x-11,H*.965,22,7,'#c2aa79',2);
    }
    const polvo=escena.atmosfera==='polvo'||(escena.efectos_visuales||[]).some(i=>i.tipo==='dust'&&t>=i.inicio&&t<i.fin);
    if(escena.realizacion.particulas!==false&&!polvo){
      const reloj=t+(escena.realizacion.desfase_ambiente||0),random=rng(seed+41);
      for(let i=0;i<44;i++){
        const fase=random()*6.28,s=.5+random(),x=W*(.05+random()*.9)+Math.sin(reloj*.21+fase)*10;
        const y=((random()*H*.87-reloj*8*s)%(H*.87)+H*.87)%(H*.87),r=1.5+s*1.7;
        const cerca=Math.max(0,1-Math.abs(x-luz.x)/(W*.30));
        glow(g,x,y,r*3,'#ffe6bc',.09+cerca*.16);
        if(i%8===0&&cerca>.35){
          const a=.13+cerca*.25;seg(g,[[x-r*2.7,y],[x+r*2.7,y]],1,alpha('#fff3db',a));
          seg(g,[[x,y-r*2.7],[x,y+r*2.7]],1,alpha('#fff3db',a));
        }
      }
    }
  }else if(['salon','interior'].includes(tipo)){
    const color=dia?'#7c817b':'#3f5354';
    caja(g,W*.39,H*.57,W*.37,H*.22,color,24);
    caja(g,W*.36,H*.68,W*.43,H*.14,shade(color,-.14),20);
    for(let i=0;i<3;i++)caja(g,W*(.4+i*.115),H*.67,W*.105,H*.085,shade(color,.10),9);
    for(const x of [.36,.74])caja(g,W*x,H*.64,W*.05,H*.17,shade(color,.06),12);
    g.fillStyle='#8b715744';g.beginPath();g.ellipse(W*.56,H*.91,W*.28,H*.08,0,0,Math.PI*2);g.fill();
    mesa(g,W*.87,H*.84,W*.15,H*.18);glow(g,W*.88,H*.60,W*.12,'#ffd28e',.13);
    lamparaMesa(g,W*.87,H*.65,W,H);
  }else if(tipo==='fiesta'){
    mesa(g,W*.84,H*.85,W*.24,H*.23);
    for(const x of [.44,.72]){
      glow(g,W*x,H*.12,W*.19,'#f7ce92',.09);
      seg(g,[[W*x,0],[W*x,H*.12]],3,'#25201f');caja(g,W*x-25,H*.12,50,20,'#bd9463',4);
      FX.pool(g,W*x,H*.87,W*.17,H*.025,'#ffdba4',.14);
    }
  }else if(tipo==='oficina'){
    mesa(g,W*.72,H*.85,W*.38,H*.24,'#65513d');
    FX.chair(g,W*.87,H*.85,1.45,'#293239');
    caja(g,W*.63,H*.43,W*.15,H*.17,'#20292f',6);
    g.fillStyle='#2c4b5c';g.fillRect(W*.637,H*.44,W*.136,H*.145);
    caja(g,W*.7,H*.60,10,H*.035,'#92989a',2);caja(g,W*.68,H*.63,W*.06,7,'#92989a',2);
    glow(g,W*.7,H*.51,W*.13,'#91c9e5',.08);
    seg(g,[[W*.82,H*.61],[W*.84,H*.52],[W*.81,H*.47]],5,'#8e999b');
    caja(g,W*.785,H*.465,W*.052,H*.02,'#a4afb1',5);glow(g,W*.81,H*.49,W*.13,'#d0e9f1',.10);
  }else if(tipo==='laboratorio'){
    mesa(g,W*.72,H*.85,W*.42,H*.24,'#607479');
    for(let i=0;i<3;i++){
      const x=W*(.57+i*.08),y=H*.61;
      caja(g,x,y-H*.075,W*.035,H*.075,'#708d924d',4);
      g.fillStyle=['#85a9ac80','#b6b18b70','#789aad70'][i];g.fillRect(x+3,y-H*.034,W*.035-6,H*.03);
      seg(g,[[x,y-H*.075],[x+W*.035,y-H*.075]],2,'#d7e7e5');
    }
    const x=W*.86,y=H*.61;
    seg(g,[[x,y],[x-W*.025,y-H*.015],[x-W*.015,y-H*.10],[x+W*.015,y-H*.14]],12,'#c3ccca');
    caja(g,x-W*.025,y-H*.15,W*.045,H*.028,'#44545d',3);caja(g,x-W*.04,y-5,W*.08,9,'#34414a',3);
  }else if(tipo==='cocina'){
    mesa(g,W*.40,H*.85,W*.70,H*.24,'#79664e');
    g.fillStyle='#a0a8a5';g.beginPath();g.ellipse(W*.33,H*.61,W*.065,H*.016,0,0,Math.PI*2);g.fill();
    g.strokeStyle='#bdc3bc';g.lineWidth=6;g.beginPath();g.moveTo(W*.36,H*.61);g.bezierCurveTo(W*.36,H*.48,W*.30,H*.50,W*.30,H*.55);g.stroke();
    caja(g,W*.83,H*.28,W*.14,H*.56,dia?'#d3d2c9':'#7c817e',9);
    seg(g,[[W*.835,H*.49],[W*.965,H*.49]],3,'#56615f');
    for(const yy of [.42,.56])seg(g,[[W*.85,H*yy],[W*.85,H*(yy+.07)]],4,'#454e4e');
  }else if(tipo==='aula'){
    for(let i=0;i<3;i++){
      const x=W*(.30+i*.27),y=H*.87,w=W*.19;
      FX.chair(g,x+W*.025,y-10,1.05,'#554637');
      for(const dx of [-.38,.38])seg(g,[[x+w*dx,y-H*.14],[x+w*dx,y]],5,'#3a3d3b');
      caja(g,x-w/2,y-H*.15,w,12,'#a48254',3);
      seg(g,[[x-w*.35,y-H*.055],[x+w*.35,y-H*.055]],3,'#49443b');
    }
  }else if(tipo==='barrio'||tipo==='ciudad'){
    for(const [x,w,h,color] of lugar.edificios===false?[]:[[W*.04,W*.29,H*.43,'#bd9f7d'],[W*.68,W*.28,H*.49,'#b8ada0']]){
      const material=lugar.fachada||color,pared=dia?material:shade(material,-.57),base=H*.81;
      const tejado=lugar.tejado?(dia?lugar.tejado:shade(lugar.tejado,-.35)):(dia?'#865044':'#462b2a');
      caja(g,x,base-h,w,h,pared,2);
      poly(g,[[x-w*.055,base-h],[x+w*.5,base-h-H*.13],[x+w*1.055,base-h]],tejado);
      for(let k=1;k<5;k++){
        const yy=base-h-H*.13*(1-k/5),medio=w*.5*k/5;
        seg(g,[[x+w*.5-medio,yy],[x+w*.5+medio,yy]],1,alpha(lugar.tejado||'#dba07b',.13));
      }
      for(const wx of [.16,.63]){
        const vx=x+w*wx,vy=base-h*.72,vw=w*.22,vh=h*.26;
        if(!lugar.luz_ventanas)ventana(g,vx,vy,vw,vh,dia,seed,true);
        else{
          // Una ventana iluminada por casa; las restantes quedan apagadas.
          caja(g,vx-9,vy-9,vw+18,vh+18,'#342d28',5);
          g.fillStyle=wx===.16?shade(lugar.luz_ventanas,-.45):'#182431';g.fillRect(vx,vy,vw,vh);
          if(wx===.16)glow(g,vx+vw/2,vy+vh/2,vw*.85,lugar.luz_ventanas,.12);
          seg(g,[[vx+vw/2,vy],[vx+vw/2,vy+vh]],5,'#282b2b');
          seg(g,[[vx,vy+vh/2],[vx+vw,vy+vh/2]],5,'#282b2b');
        }
      }
      caja(g,x+w*.42,base-h*.36,w*.18,h*.36,'#5a4031',2);
      caja(g,x+w*.74,base-h-H*.08,w*.07,H*.09,lugar.fachada?shade(pared,-.2):(dia?'#9d6b55':'#543d33'),2);
      seg(g,[[x-w*.04,base-h],[x+w*1.04,base-h]],3,lugar.tejado?shade(tejado,-.2):'#79564b');
    }
    FX.lampPost(g,W*.57,H*.83,H*.49,{color:'#252c2c',light:'#ffe0a7',a:dia?.02:.06});
    FX.pool(g,W*.59,H*.86,W*.12,H*.024,'#ffe0a7',dia?.04:.17);
  }else{
    const random=rng(seed+9);
    for(let i=0;i<8;i++){
      const x=W*i/7,base=H*(.77+random()*.035),h=H*(.30+random()*.14),r=W*(.055+random()*.025);
      caja(g,x-8,base-h*.7,16,h*.7,'#4c3829',3);
      g.fillStyle=linGrad(g,x-r,base-h,x+r,base,[dia?'#668457':'#2a4937',dia?'#314d37':'#172f27']);
      for(const [dx,dy,escala] of [[-.35,.08,.75],[.35,.12,.8],[0,-.08,1]]){
        g.beginPath();g.ellipse(x+r*dx,base-h+h*dy,r*escala,h*.34*escala,0,0,Math.PI*2);g.fill();
      }
      seg(g,[[x,base-h*.25],[x,base-h*.84]],5,'#4c3829');
      seg(g,[[x,base-h*.6],[x-r*.4,base-h*.8]],3,'#4c3829');
    }
    const x=W*.77,y=H*.82;
    caja(g,x-W*.09,y-H*.15,W*.18,17,'#785437',3);caja(g,x-W*.09,y-H*.075,W*.18,14,'#785437',3);
    for(const dx of [-.07,.07])seg(g,[[x+W*dx,y-H*.15],[x+W*dx,y]],5,'#303934');
  }
}

export function frenteEscenografia(g,escena){
  const {tipo,W,H,seed,lugar}=datos(escena);
  if(tipo==='cine'){frenteCine(g,escena);return;}
  if(tipo!=='teatro')return;
  for(let lado=0;lado<2;lado++){
    g.save();if(lado){g.translate(W,0);g.scale(-1,1);}
    const w=W*.062;
    const tela=escena.realizacion.fondo||'#6c201d';
    g.fillStyle=linGrad(g,0,0,w,0,[shade(tela,-.67),tela,shade(tela,-.48)]);
    g.beginPath();g.moveTo(-W,-H);g.lineTo(w*1.1,-H);g.lineTo(w,0);
    g.bezierCurveTo(w*.50,H*.30,w*.03,H*.45,w*.40,H*.62);
    g.bezierCurveTo(w*.52,H*.76,w*.86,H*.90,w,H*1.1);g.lineTo(-W,H*1.1);g.closePath();g.fill();g.restore();
  }
  if(lugar.publico!==false){
    const random=rng(seed+88);
    g.fillStyle='#060607';
    for(let i=-1;i<13;i++){
      const x=(i+.4)*W/11,y=H*(1.015+random()*.025),rx=W*(.044+random()*.009),ry=H*(.06+random()*.018);
      g.beginPath();g.ellipse(x,y,rx,ry,0,0,Math.PI*2);g.fill();
    }
    g.fillRect(-W,H*1.01,W*3,H);
  }
}
