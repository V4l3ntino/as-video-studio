import { E, setStyle } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';
import PALETAS from './paletas.json';

// Perfil neutro para vídeos nuevos: no tiñe todas las identidades de verde/rojo.
// Los cinco acabados originales siguen pasando por setStyle sin alteraciones.
const EDITORIAL = {
  name:'Editorial Cinema',ink:'#090d16',inkFar:'#22283a',feature:'#fff5e6',rimWidth:3.2,
  ui:{card:'rgba(18,28,48,.94)',cardLine:'rgba(150,180,230,.25)',text:'#b9cce6',sub:'#8599b7',
    accent:'#ff9360',gold:'#ffd080',cream:'#fff1dc',blueprint:'#91cfff',bpBg:'#091424',good:'#73d6ad'},
  grade:{contrast:1.03,sat:.96,lift:[0,0,0],gamma:[1,1,1],gain:[1.02,1,1],vignette:.32,grain:.018,bloom:.4},
  moods:{},
};

export function aplicarEstilo(id){
  if(id==='editorial'){E.styleId=id;E.style=EDITORIAL;}
  else setStyle(id);
}

export function paletaEditorial(id){return PALETAS[id];}

export function aplicarPaleta(id){
  const p=paletaEditorial(id);
  if(!p)return;
  // Solo grafismo: ni el vestuario ni los materiales de utilería se recolorean.
  E.style={...E.style,ui:{...E.style.ui,accent:p.detalle||p.acento,gold:p.acento,cream:p.texto,
    text:p.texto,sub:p.secundario,blueprint:p.secundario,bpBg:p.fondo}};
}
