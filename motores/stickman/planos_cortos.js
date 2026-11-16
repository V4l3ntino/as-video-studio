import { esquinas } from './encuadre.js';
import { proyectarRostro } from './bocadillos.js';

// Un rótulo explicativo sin ancla no forma parte del decorado que se amplía.
// Su trayectoria sigue en coordenadas normalizadas de pantalla. Los objetos
// sujetos a un actor conservan su transformación de mundo.
export function rotuloDePlanoCorto(o, realizacion) {
  return ['medio','primer_plano'].includes(realizacion.encuadre)
    && ['texto','etiqueta'].includes(o.tipo) && !o.ancla;
}

export function reservarRotulos(cam, escena, head, W, H) {
  const r=proyectarRostro(head,cam), margen=W*.04;
  let izquierda=margen,derecha=W-margen,reserva=false;
  for(const o of escena.objetos){
    if(!rotuloDePlanoCorto(o,escena.realizacion)||o.transito)continue;
    // Reservar la posición de lectura, no perseguir la entrada con la cámara.
    const ultimo=campo=>o.claves.filter(k=>k[campo]!==undefined).at(-1)?.[campo]??o[campo];
    if(ultimo('opacidad')<=.001)continue;
    const x=ultimo('x')*W,y=ultimo('y')*H,s=ultimo('escala');
    const puntos=esquinas(x,y,(o.w+24)*s,(o.h+24)*s,ultimo('rot')||0);
    const xs=puntos.map(p=>p[0]),ys=puntos.map(p=>p[1]);
    if(Math.max(...ys)<r.y-r.r||Math.min(...ys)>r.y+r.r)continue;
    reserva=true;
    if(x<W/2)izquierda=Math.max(izquierda,Math.max(...xs)+margen);
    else derecha=Math.min(derecha,Math.min(...xs)-margen);
  }
  if(!reserva||derecha<=izquierda)return;
  // Si hay poco hueco, reducir solo lo necesario sin encuadrar piernas/pies.
  const radio=Math.min(r.r,(derecha-izquierda)/2);
  if(radio<r.r)cam.z*=radio/r.r;
  const centro=Math.max(izquierda+radio,Math.min(derecha-radio,r.x));
  const dx=centro-proyectarRostro(head,cam).x,c=Math.cos(cam.r||0),s=Math.sin(cam.r||0);
  cam.x-=dx*c/cam.z;cam.y+=dx*s/cam.z;
}
