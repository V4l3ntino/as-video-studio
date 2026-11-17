// Sala y proyección separadas: nada de la película puede invadir las butacas.
import { E, linGrad, glow, poly, seg } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';

export const PANTALLA_CINE={x:.18,y:.085,w:.64,h:.54};
function caja(g,x,y,w,h,color,r=0){
  g.fillStyle=color;g.beginPath();g.roundRect(x*E.W,y*E.H,w*E.W,h*E.H,r*E.H);g.fill();
}
function pol(g,p,color){poly(g,p.map(([x,y])=>[x*E.W,y*E.H]),color);}
function linea(g,p,color,w=2){seg(g,p.map(([x,y])=>[x*E.W,y*E.H]),w,color);}
function elipse(g,x,y,rx,ry,color){
  g.fillStyle=color;g.beginPath();g.ellipse(x*E.W,y*E.H,rx*E.H,ry*E.H,0,0,Math.PI*2);g.fill();
}

let texturaBruma,claveBruma;
function bruma(g,t,seed,color){
  const clave=`${seed}:${color}`;
  if(claveBruma!==clave){
    const w=256,h=144,c=document.createElement('canvas');c.width=w;c.height=h;
    const ctx=c.getContext('2d'),imagen=ctx.createImageData(w,h);
    const rgb=color.match(/[a-f\d]{2}/gi).map(n=>parseInt(n,16));
    const hash=(x,y)=>{const n=Math.sin(x*127.1+y*311.7+seed*.01)*43758.5453;return n-Math.floor(n);};
    const ruido=(x,y)=>{
      const ix=Math.floor(x),iy=Math.floor(y),u=x-ix,v=y-iy,a=u*u*(3-2*u),b=v*v*(3-2*v);
      return (hash(ix,iy)*(1-a)+hash(ix+1,iy)*a)*(1-b)+(hash(ix,iy+1)*(1-a)+hash(ix+1,iy+1)*a)*b;
    };
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
      const n=ruido(x/28,y/25)*.52+ruido(x/13,y/12)*.27+ruido(x/6,y/6)*.14+ruido(x/3,y/3)*.07;
      const borde=Math.sin(x/w*Math.PI),altura=.3+.7*y/h,i=(y*w+x)*4;
      imagen.data[i]=rgb[0];imagen.data[i+1]=rgb[1];imagen.data[i+2]=rgb[2];
      imagen.data[i+3]=Math.max(0,n-.30)*210*borde*altura;
    }
    ctx.putImageData(imagen,0,0);texturaBruma=c;claveBruma=clave;
  }
  const p=PANTALLA_CINE;g.save();g.globalCompositeOperation='screen';
  g.globalAlpha*=.9;g.imageSmoothingEnabled=true;
  g.drawImage(texturaBruma,(p.x-.015+Math.sin(t*.17)*.006)*E.W,(p.y-.01)*E.H,(p.w+.03)*E.W,(p.h+.03)*E.H);
  g.restore();
}

function pelicula(g,escena,t,seed){
  const W=E.W,H=E.H,p=PANTALLA_CINE,lugar=escena.realizacion.escenario;
  g.save();g.beginPath();g.rect(p.x*W,p.y*H,p.w*W,p.h*H);g.clip();
  caja(g,p.x,p.y,p.w,p.h,linGrad(g,0,p.y*H,W,(p.y+p.h)*H,['#171c28','#38333a','#292732']));
  if(lugar.proyeccion==='silueta_amenazante'){
    const color=lugar.luz||'#ffb456';
    glow(g,W*.51,H*.32,H*.38,color,.70);
    // Humo volumétrico suave y determinista, confinado al fotograma proyectado.
    bruma(g,t,seed,color);
    const respirar=Math.sin(t*1.2)*.002;
    // Busto de abrigo y cuello alto; los hombros siguen siendo reconocibles.
    const cabeza=()=>elipse(g,.51,.24,.128,.128,'#15151a');
    const cuerpo=()=>{
      pol(g,[[.32,.67],[.345,.445+respirar],[.425,.385],[.59,.385],[.66,.445+respirar],[.705,.67]],'#16151a');
      pol(g,[[.43,.46],[.40,.355],[.46,.31],[.56,.31],[.61,.355],[.58,.46]],'#17151a');
    };
    // Copia luminosa detrás de la silueta: contorno continuo, núcleo oscuro.
    g.save();g.shadowColor=color;g.shadowBlur=H*.055;g.strokeStyle='#ffd695';g.lineWidth=H*.011;
    g.beginPath();g.moveTo(W*.32,H*.67);g.lineTo(W*.345,H*(.445+respirar));g.lineTo(W*.425,H*.385);
    g.lineTo(W*.40,H*.355);g.lineTo(W*.46,H*.31);g.lineTo(W*.56,H*.31);
    g.lineTo(W*.61,H*.355);g.lineTo(W*.59,H*.385);g.lineTo(W*.66,H*(.445+respirar));g.lineTo(W*.705,H*.67);g.stroke();
    g.beginPath();g.ellipse(W*.51,H*.24,H*.128,H*.128,0,0,Math.PI*2);g.stroke();g.restore();
    cuerpo();cabeza();
    linea(g,[[.345,.445+respirar],[.385,.67]],'#95623c',H*.004);
    linea(g,[[.66,.445+respirar],[.625,.67]],'#95623c',H*.004);
    // Ojos entrecerrados, sin boca ni rasgos de un personaje del reparto.
    g.save();g.shadowColor='#ffb66c';g.shadowBlur=H*.014;
    for(const lado of [-1,1]){
      const x=.51+lado*.039;
      pol(g,[[x-lado*.014,.242],[x+lado*.015,.223],[x+lado*.010,.242],[x,.246]],'#fff4df');
    }
    g.restore();
    // Bruma delante del abrigo: no revela un bloque plano ni oculta la cabeza.
    for(let i=0;i<12;i++)glow(g,W*(.30+i*.035),H*(.59+Math.sin(i+t*.3)*.015),H*.10,'#b59885',.065);
  }
  // La proyección tiene vida propia, sin cambiar el tamaño de la sala.
  caja(g,p.x,p.y,p.w,p.h,`rgba(255,224,186,${.008+.006*Math.sin(t*13)})`);
  g.restore();
}

function cortina(g,lado){
  const W=E.W,H=E.H;g.save();if(lado){g.translate(W,0);g.scale(-1,1);}
  g.beginPath();g.moveTo(W*.085,-H*.1);g.lineTo(W*.185,-H*.1);
  g.bezierCurveTo(W*.18,H*.16,W*.145,H*.33,W*.12,H*.45);
  g.quadraticCurveTo(W*.13,H*.55,W*.14,H*.70);g.lineTo(W*.09,H*.72);g.closePath();g.clip();
  for(let i=0;i<14;i++){
    const x=W*(.075+i*.009);
    g.fillStyle=linGrad(g,x,0,x+W*.012,0,['#180409','#6b0717','#a21927','#36050f']);
    g.fillRect(x,-H*.1,W*.013,H*.9);
  }
  linea(g,[[.105,.47],[.145,.45]],'#b35b33',H*.020);
  linea(g,[[.105,.464],[.145,.444]],'#dd9753',H*.003);g.restore();
}

export function fondoCine(g,escena,t,seed){
  const W=E.W,H=E.H;
  g.fillStyle=linGrad(g,0,0,W,0,['#392019','#151217','#100e13','#392019']);g.fillRect(-W,-H,W*3,H*3);
  caja(g,.15,.035,.70,.635,'#090a10');
  caja(g,.168,.072,.664,.565,'#3d2a25');
  pelicula(g,escena,t,seed);
  linea(g,[[.16,.66],[.84,.66]],'#6e4130',H*.004);
  for(const lado of [0,1]){
    g.save();if(lado){g.translate(W,0);g.scale(-1,1);}
    caja(g,.015,0,.075,1,linGrad(g,0,0,W*.1,0,['#291512','#693b28','#321c19']));
    for(let i=0;i<12;i++)caja(g,.02+i*.005,0,.001,1,'#cf87551b');
    glow(g,W*.048,H*.25,H*.18,'#ffb852',.18);
    caja(g,.029,.175,.037,.16,'#1b1514',.004);
    caja(g,.037,.185,.022,.14,linGrad(g,0,H*.18,0,H*.34,['#ffc25d','#fff1ad','#ffba50']),.002);
    linea(g,[[.048,.19],[.048,.32]],'#513321',H*.005);
    g.restore();cortina(g,lado);
  }
}

export function sueloCine(g){
  caja(g,-1,.67,3,1.5,linGrad(g,0,E.H*.67,0,E.H,['#261c20','#0e0d13']));
}

function butaca(g,x,y,w,h){
  caja(g,x-w/2,y,w,h,'#260a15',.035);
  caja(g,x-w/2+.003,y+.008,w-.006,h-.012,linGrad(g,0,y*E.H,0,(y+h)*E.H,['#b60f32','#630a23','#2a0b18']),.03);
  caja(g,x-w/2+.009,y+.020,w-.018,h-.025,linGrad(g,0,y*E.H,0,(y+h)*E.H,['#5a0c22','#290d1a','#180e17']),.025);
}
function espectador(g,x,y,s){
  const H=E.H;
  g.save();g.shadowColor='#ffce8e';g.shadowBlur=H*.006;g.lineWidth=H*.006*s;g.strokeStyle='#ddbb92';
  g.fillStyle='#0c0d13';g.beginPath();g.ellipse(x*E.W,y*H,H*.061*s,H*.070*s,0,0,Math.PI*2);g.fill();g.stroke();
  g.restore();
  pol(g,[[x-.055*s,y+.14*s],[x-.049*s,y+.085*s],[x-.021*s,y+.060*s],
    [x+.021*s,y+.060*s],[x+.049*s,y+.085*s],[x+.055*s,y+.14*s]],'#101017');
}

export function frenteCine(g,escena){
  // Filas escalonadas y cercanas, sin crowd de muñecos ni un panel opaco delante.
  for(let i=0;i<9;i++)butaca(g,.06+i*.11,.78,.105,.15);
  if(escena.realizacion.escenario.publico!==false)
    for(const [x,y,s] of [[.21,.72,.65],[.37,.76,.48],[.58,.73,.72],[.80,.74,.65]])espectador(g,x,y,s);
  for(let i=0;i<7;i++)butaca(g,.02+i*.16,.85,.17,.19);
  if(escena.realizacion.escenario.publico!==false)
    for(const [x,y,s] of [[.045,.71,1.20],[.98,.70,1.25],[.83,.79,.65]])espectador(g,x,y,s);
  for(let i=0;i<5;i++)butaca(g,-.01+i*.255,.94,.27,.23);
}
