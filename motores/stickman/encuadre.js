// Límites en el espacio del mundo, antes de la cámara. Nunca recorta ni estira.
export function esquinas(x,y,w,h,rot=0) {
  const c=Math.cos(rot),s=Math.sin(rot);
  return [[-w/2,-h/2],[w/2,-h/2],[w/2,h/2],[-w/2,h/2]]
    .map(([dx,dy])=>[x+dx*c-dy*s,y+dx*s+dy*c]);
}

// El decorado residencial ocupa el lienzo completo: evita que una cámara
// descubra sus bordes. Algunos planes publicados usaron .5 como centro en vez
// de desplazamiento cero; reconoce solo esa pareja inequívoca de coordenadas.
export function encuadrarCalle(cam,claves,W,H) {
  const xs=claves.filter(k=>k.x!==undefined).map(k=>k.x);
  const ys=claves.filter(k=>k.y!==undefined).map(k=>k.y);
  if(xs.length&&ys.length&&xs.every(x=>x>=.35&&x<=.65)&&ys.every(y=>y>=.35&&y<=.65)){
    cam.x-=W*.5;cam.y-=H*.5;
  }
  const c=Math.abs(Math.cos(cam.r||0)),s=Math.abs(Math.sin(cam.r||0));
  const mitadX=(c*W+s*H)/2,mitadY=(s*W+c*H)/2;
  cam.z=Math.max(cam.z,1.16,2*mitadX/W,2*mitadY/H);
  const margenX=Math.max(0,W/2-mitadX/cam.z),margenY=Math.max(0,H/2-mitadY/cam.z);
  cam.x=Math.max(-margenX,Math.min(margenX,cam.x));
  cam.y=Math.max(-margenY,Math.min(margenY,cam.y));
}

export function encuadrar(cam,puntos,W,H,zona) {
  if(!puntos.length)return;
  const c=Math.cos(cam.r||0),s=Math.sin(cam.r||0);
  // layer() rota el mundo, por lo que ajustamos también en esos ejes.
  let x0=Infinity,x1=-Infinity,y0=Infinity,y1=-Infinity;
  for(const [x,y] of puntos){
    const rx=x*c-y*s,ry=x*s+y*c;
    x0=Math.min(x0,rx);x1=Math.max(x1,rx);y0=Math.min(y0,ry);y1=Math.max(y1,ry);
  }
  const ancho=W*.92,alto=zona.abajo-zona.arriba;
  cam.z=Math.min(cam.z,ancho/Math.max(1,x1-x0),alto/Math.max(1,y1-y0));
  const x=W/2+cam.x,y=H/2+cam.y;
  const limitar=(v,min,max)=>Math.max(min,Math.min(max,v));
  const cx=limitar(x*c-y*s,x1-ancho/(2*cam.z),x0+ancho/(2*cam.z));
  const cy=limitar(x*s+y*c,y1-(zona.abajo-H/2)/cam.z,y0-(zona.arriba-H/2)/cam.z);
  cam.x=cx*c+cy*s-W/2;cam.y=-cx*s+cy*c-H/2;
}
