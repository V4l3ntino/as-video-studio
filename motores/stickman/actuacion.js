// Poses locales: no mutar el repertorio del kit ni las identidades guardadas.
import { posesAt } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/rig2d.js';

export const POSES_ACTUACION = {
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
