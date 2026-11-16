// Hoja rígida girando en profundidad. El marco nunca cambia de escala.
export function estadoPuerta(o,t) {
  const c=o.cierre;
  const p=c?Math.max(0,Math.min(1,(t-c.inicio)/(c.fin-c.inicio))):0;
  const angulo=o.apertura*(1-p*p*p);
  const dt=c?t-c.fin:-1;
  const vibracion=dt>=0&&dt<.55?Math.sin(dt*85)*Math.exp(-dt*9)*(1-dt/.55):0;
  return {angulo, vibracion, impacto:dt>=0&&dt<.16?1-dt/.16:0};
}

export function pintarPuerta(g,o,t) {
  const {angulo,vibracion,impacto}=estadoPuerta(o,t),{w,h}=o;
  const borde=Math.min(w*.055,h*.025),ancho=w-2*borde,alto=h-2*borde;
  const lado=o.bisagra==='derecha'?-1:1;
  const bisagra=-lado*ancho/2;
  // Oscilación de 2.5 píxeles de salida, independientemente del lienzo lógico.
  const px=Math.hypot(g.getTransform().a,g.getTransform().b)||1;
  const sacudida=vibracion*2.5/px;
  g.save();
  g.fillStyle=o.marco;g.fillRect(-w/2,-h/2,w,h);
  g.fillStyle='#10171b';g.fillRect(-ancho/2,-alto/2,ancho,alto);
  const proyectar=(u,v)=>{
    const profundidad=u*Math.sin(angulo),perspectiva=1/(1+profundidad/(ancho*3));
    return [bisagra+lado*u*Math.cos(angulo)*perspectiva+sacudida*u/ancho,v*perspectiva];
  };
  const panel=(x,y,ww,hh,relleno,trazo)=>{
    g.beginPath();
    [[x,y],[x+ww,y],[x+ww,y+hh],[x,y+hh]].forEach(([u,v],i)=>{
      const p=proyectar(u,v);if(i)g.lineTo(...p);else g.moveTo(...p);
    });
    g.closePath();if(relleno){g.fillStyle=relleno;g.fill();}
    if(trazo){g.strokeStyle=trazo;g.stroke();}
  };
  g.lineWidth=Math.max(1,borde*.3);
  panel(0,-alto/2,ancho,alto,o.color,'#342519');
  panel(ancho*.09,-alto*.43,ancho*.82,alto*.38,null,'#473222');
  panel(ancho*.09,alto*.06,ancho*.82,alto*.37,null,'#473222');
  const pomo=proyectar(ancho*.87,alto*.01);
  g.fillStyle='#efbd55';g.beginPath();g.ellipse(...pomo,Math.max(1,borde*.4*Math.cos(angulo)),borde*.4,0,0,Math.PI*2);g.fill();
  // Herrajes fijos: hacen visible el eje de giro incluso con la hoja abierta.
  g.fillStyle='#b29a75';for(const v of [-.32,.32])g.fillRect(bisagra-borde*.18,alto*v,borde*.36,alto*.065);
  if(impacto){
    g.save();g.globalAlpha*=impacto;g.strokeStyle='#ffc052';g.lineWidth=3/px;g.lineCap='round';
    for(const s of [-1,1])for(const v of [-.25,0,.25]){
      g.beginPath();g.moveTo(s*(w/2+8/px),h*v);
      g.lineTo(s*(w/2+23/px),h*v+(v===0?0:Math.sign(v)*9/px));g.stroke();
    }g.restore();
  }
  g.restore();
}
