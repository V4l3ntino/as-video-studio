// Poses locales: no mutar el repertorio del kit ni las identidades guardadas.
import { posesAt } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/rig2d.js';
import { ease } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';

export const POSES_ACTUACION = {
  palmUp: {head:[5,-208],sh:[1,-174],hip:[0,-100],eF:[30,-146],hF:[66,-157],
    eB:[-8,-137],hB:[-14,-104],kF:[8,-50],fF:[10,0],kB:[-4,-50],fB:[-12,0]},
  scratchHead: {head:[-4,-208],sh:[0,-174],hip:[0,-100],eF:[55,-178],hF:[23,-216],
    eB:[-32,-135],hB:[-13,-110],kF:[8,-50],fF:[11,0],kB:[-6,-50],fB:[-14,0]},
  pushReady: {head:[8,-208],sh:[5,-172],hip:[-5,-98],eF:[34,-151],hF:[58,-165],
    eB:[-23,-140],hB:[-18,-113],kF:[20,-49],fF:[33,0],kB:[-24,-47],fB:[-38,0]},
  push: {head:[23,-204],sh:[19,-169],hip:[0,-98],eF:[62,-165],hF:[103,-162],
    eB:[-15,-145],hB:[-28,-121],kF:[29,-49],fF:[42,0],kB:[-22,-47],fB:[-40,0]},
  shout: {head:[18,-205],sh:[12,-170],hip:[0,-98],eF:[48,-166],hF:[82,-169],
    eB:[-20,-163],hB:[-32,-137],kF:[24,-48],fF:[34,0],kB:[-18,-48],fB:[-29,0]},
  recoil: {head:[-20,-183],sh:[-13,-151],hip:[0,-91],eF:[18,-129],hF:[30,-166],
    eB:[4,-126],hB:[16,-158],kF:[25,-47],fF:[27,0],kB:[-8,-46],fB:[-28,0]},
};

// La mano acompaña la mezcla de poses; no aparece de golpe ni queda al caminar.
export function aperturaPalma(t, claves, mezcla=.35) {
  let apertura=claves[0]?.pose==='palmUp'?1:0;
  for(const k of claves.slice(1)) {
    if(t<k.t)break;
    const u=Math.max(0,Math.min(1,(t-k.t)/mezcla));
    const suave=ease.inOut(u),destino=k.pose==='palmUp'?1:0;
    apertura+=(destino-apertura)*suave;
    if(u<1)break;
  }
  return apertura;
}

export function pintarPalma(g, pose, apertura, color, contorno) {
  if(apertura<=0)return;
  g.save();g.translate(...pose.hF);g.globalAlpha*=apertura;
  g.lineJoin=g.lineCap='round';g.fillStyle=color;g.strokeStyle=contorno;g.lineWidth=1.5;
  // Vista de tres cuartos: palma ancha, cuatro puntas escalonadas y pulgar
  // separado por una escotadura. No es una pinza ni una bandeja rectangular.
  g.beginPath();g.moveTo(-6,4);g.quadraticCurveTo(3,10,11,7);
  g.lineTo(20,3);g.quadraticCurveTo(23,1,21,-1);g.lineTo(13,1);
  g.lineTo(25,-3);g.quadraticCurveTo(28,-5,25,-7);g.lineTo(13,-3);
  g.lineTo(24,-9);g.quadraticCurveTo(26,-12,23,-12);g.lineTo(10,-6);
  g.lineTo(18,-13);g.quadraticCurveTo(19,-16,16,-15);g.lineTo(5,-8);
  g.quadraticCurveTo(1,-7,0,-10);g.lineTo(0,-15);
  g.quadraticCurveTo(-2,-19,-5,-15);g.lineTo(-7,-6);
  g.quadraticCurveTo(-8,-2,-6,4);g.closePath();g.fill();g.stroke();
  g.restore();
}

export function poseActuada(t, claves, mezcla, cabeza=1, cuerpo=1) {
  return posesAt(t, claves.map(k=>{
    if(k.pose!=='scratchHead')return [k.t,POSES_ACTUACION[k.pose]||k.pose];
    // Movimiento tangencial corto sobre la sien: una mano en contacto,
    // sin balancear el otro brazo ni sustituir el gesto por respiración.
    const p=POSES_ACTUACION.scratchHead;
    const a=-.28+.12*Math.sin(Math.max(0,t-k.t)*Math.PI*7);
    return [k.t,{...p,hF:[p.head[0]+28*cabeza*Math.cos(a),p.head[1]+28*cabeza/cuerpo*Math.sin(a)],
      eF:[p.eF[0]+(cabeza-1)*20,p.eF[1]]}];
  }), mezcla);
}
