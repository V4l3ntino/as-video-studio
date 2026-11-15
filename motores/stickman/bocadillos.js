// Bocadillos de pantalla con cola unida al rostro proyectado por la cámara.
import { E, FONTS, clamp } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';

export function proyectarRostro(head,cam){
  const x=(head.x-E.W/2-cam.x)*cam.z,y=(head.y-E.H/2-cam.y)*cam.z;
  const c=Math.cos(cam.r||0),s=Math.sin(cam.r||0);
  return {x:E.W/2+x*c-y*s,y:E.H/2+x*s+y*c,r:head.r*cam.z};
}

function envolver(g,texto,ancho){
  const lineas=[];let linea='';
  for(const palabra of texto.split(/\s+/)){
    if(linea&&g.measureText(`${linea} ${palabra}`).width>ancho){lineas.push(linea);linea='';}
    for(const letra of (linea?' ':'')+palabra){
      if(linea&&g.measureText(linea+letra).width>ancho){lineas.push(linea);linea='';}
      linea+=letra;
    }
  }
  if(linea)lineas.push(linea);
  return lineas;
}

export function bocadillo(g,o,head){
  g.save();
  const W=E.W,H=E.H,margen=W*.04;
  let w=clamp(o.w??W*.32,100,W*.75),h=clamp(o.h??H*.18,70,H*.38);
  let size=o.size??40,lineas=[];
  do{
    g.font=`800 ${size}px "${FONTS.ui}"`;lineas=envolver(g,o.texto,w-44);
    if(lineas.length*size*1.2<=h-28||size<=24)break;
    size-=2;
  }while(size>0);
  // Si se pidió una caja demasiado pequeña, amplíala antes de recortar o volver ilegible el texto.
  while(lineas.length*size*1.2>h-28){
    h=Math.min(H*.38,Math.max(h,lineas.length*size*1.2+28));
    if(lineas.length*size*1.2<=h-28||w>=W*.75)break;
    w=Math.min(W*.75,w+80);lineas=envolver(g,o.texto,w-44);
  }
  const izquierda=head.x>=W/2;
  const x=clamp(o.x??W*(izquierda?.20:.80),margen+w/2,W-margen-w/2);
  const y=clamp(o.y??H*.18,H*.04+h/2,H*.94-h/2);
  const dx=head.x-x,dy=head.y-y,l=Math.hypot(dx,dy)||1,ux=dx/l,uy=dy/l;
  const borde=Math.min(w/2/Math.max(.001,Math.abs(ux)),h/2/Math.max(.001,Math.abs(uy)))*.9;
  const bx=x+ux*borde,by=y+uy*borde;
  const tx=head.x-ux*head.r*.90,ty=head.y-uy*head.r*.90;
  g.fillStyle=o.color||'#fff6e6';g.strokeStyle='#ffffff38';g.lineWidth=2;
  if(o.modo==='pensamiento'){
    for(let i=0;i<3;i++){
      const f=(i+1)/4,r=Math.max(3,h*.075*(1-i*.23));
      g.beginPath();g.arc(bx+(tx-bx)*f,by+(ty-by)*f,r,0,Math.PI*2);g.fill();
    }
  }else{
    const base=Math.min(24,w*.07);
    g.beginPath();g.moveTo(bx-uy*base,by+ux*base);g.lineTo(tx,ty);
    g.lineTo(bx+uy*base,by-ux*base);g.closePath();g.fill();
  }
  g.beginPath();g.roundRect(x-w/2,y-h/2,w,h,Math.min(24,h*.2));g.fill();g.stroke();
  // Tinta oscura, sin halo ni efectos cromáticos sobre el texto del bocadillo.
  g.fillStyle=o.tinta||'#16151a';g.textAlign='center';g.textBaseline='middle';
  for(let i=0;i<lineas.length;i++)g.fillText(lineas[i],x,y+(i-(lineas.length-1)/2)*size*1.2);
  g.restore();
}
