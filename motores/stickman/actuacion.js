// Poses locales: no mutar el repertorio del kit ni las identidades guardadas.
import { posesAt } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/rig2d.js';

export const POSES_ACTUACION = {
  shout: {head:[18,-205],sh:[12,-170],hip:[0,-98],eF:[48,-166],hF:[82,-169],
    eB:[-20,-163],hB:[-32,-137],kF:[24,-48],fF:[34,0],kB:[-18,-48],fB:[-29,0]},
  recoil: {head:[-20,-183],sh:[-13,-151],hip:[0,-91],eF:[18,-129],hF:[30,-166],
    eB:[4,-126],hB:[16,-158],kF:[25,-47],fF:[27,0],kB:[-8,-46],fB:[-28,0]},
};

export function poseActuada(t, claves, mezcla) {
  return posesAt(t, claves.map(k=>[k.t,POSES_ACTUACION[k.pose]||k.pose]), mezcla);
}
