// Escenas de establecimiento y recorridos del kit Three.js; datos declarativos.
import * as T from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/three-kit.js';
import { mood } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';

let actual, stage, canvas, figuras=[];
export function pintar3D(g, escena, t, duracion, estadoActor) {
  const d=escena.espacio3d;
  if(actual!==d){
    stage?.dispose();actual=d;figuras=[];
    if(!canvas){canvas=document.createElement('canvas');T.getRenderer(canvas);}
    stage=T.stage({mood:escena.ambiente,bloom:d.bloom,fog:d.niebla?[18,70]:false,keyPos:[-6,10,8]});
    // El kit coloca la luz principal detrás de los personajes por defecto.
    // Una luz de relleno neutra mantiene ropa y caras legibles en el Estudio.
    stage.add(new T.THREE.HemisphereLight('#f4ecdf','#424d63',1.1));
    for(const item of d.objetos){
      const o=item.opciones||{},c=item.color||mood(escena.ambiente).wall,p=item.posicion||[0,0,0];
      let obj;
      switch(item.tipo){
        case 'box':obj=T.box(o.w??2,o.h??2,o.d??2,c);break;
        case 'cyl':obj=T.cyl(o.rt??1,o.rb??1,o.h??2,c);break;
        case 'cone':obj=T.cone(o.r??1,o.h??2,c);break;
        case 'sphere':obj=T.sphere(o.r??1,c);break;
        case 'plane':obj=T.plane(o.w??4,o.h??3,c);break;
        case 'ground':obj=T.ground(o.w??40,o.d??40,c,o.textura==='planks'?T.planks(c):o.textura==='tiles'?T.tiles(c):null);break;
        case 'building':obj=T.building(o.w??5,o.h??10,o.d??4,{color:c,lit:o.lit,seed:o.seed});break;
        case 'tree3D':case 'pine3D':obj=T[item.tipo](0,0,o.s??1,c);break;
        case 'crowd3D':obj=T.crowd3D(o);break;
        case 'windowPane':obj=T.windowPane(o.w??4,o.h??3,{...o,glowColor:c});break;
        case 'shaft':obj=T.shaft(o.w??3,o.len??10,c,o.opacity??.08);break;
        case 'figure3D':{
          const actor=escena.personajes.find(a=>a.id===o.personaje),v=actor?.diseno;
          if(!v)throw new Error('figure3D necesita actor presente');
          obj=T.figure3D({top:v.ropa,color:v.color,color2:v.secundario,head:v.accesorio,headColor:v.secundario},{rim:v.contorno});
          figuras.push({obj,actor});break;
        }
        default:throw new Error(`Objeto 3D desconocido: ${item.tipo}`);
      }
      // building/tree/crowd sitúan su geometría sobre el suelo dentro del constructor.
      obj.position.add(new T.THREE.Vector3(...p));
      if(item.rotacion)obj.rotation.set(...item.rotacion);
      stage.add(obj);
    }
  }
  for(const {obj,actor} of figuras)obj.setPose(estadoActor(actor,t).pose);
  const cam=d.camara;
  if(cam.modo==='dolly'){
    T.dolly(stage.camera,t,[[0,{pos:cam.posicion||[0,3,8],look:cam.target||[0,1,0]}],
      [duracion,{pos:cam.destino||[2,3,6],look:cam.target||[0,1,0]}]]);
  }else T.orbit(stage.camera,t,{target:cam.target||[0,1,0],radius:cam.radius??8,height:cam.height??3,
    from:cam.desde??-.3,to:cam.hasta??.3,dur:duracion});
  stage.render();
  g.save();g.setTransform(1,0,0,1,0,0);g.drawImage(canvas,0,0,g.canvas.width,g.canvas.height);g.restore();
}
