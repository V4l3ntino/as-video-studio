// El kit original invierte las pendientes de angry/worried. Corrección local,
// sin mutar EXPR ni cambiar el aspecto de los planes históricos sin el campo.
export function rasgosExpresion(expresion, diseno, fieles=false, cejasFieles=false) {
  if(expresion==='neutral')return {eyes:diseno.ojos,mouth:fieles?'smallFlat':diseno.boca,brows:null};
  if(!fieles&&!cejasFieles)return {};
  if(['angry','determined'].includes(expresion))return {brows:'worried'};
  if(['worried','nervous','sad','cry'].includes(expresion))return {brows:'angry'};
  // scared comparte las mismas cejas de preocupación, también con ojos abiertos.
  if(expresion==='scared')return {brows:'angry'};
  return {};
}
