// La locomoción sigue los tramos de desplazamiento, no la duración del plano.
export function movimientoEn(c,t) {
  const modo=c.claves.filter(k=>k.t<=t&&k.movimiento!==undefined).at(-1)?.movimiento??c.movimiento;
  if(!['caminar','correr'].includes(modo))return 'gesto';
  for(const campo of ['x','y']){
    let anterior={t:0,v:c[campo]};
    for(const k of c.claves){
      if(k[campo]===undefined)continue;
      if(t>=anterior.t&&t<k.t&&k[campo]!==anterior.v)return modo;
      anterior={t:k.t,v:k[campo]};
    }
  }
  return 'gesto';
}
