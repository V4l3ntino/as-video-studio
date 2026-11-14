// Adaptador declarativo sobre el rig GrowKaz. No ejecuta código del modelo.
import { E, setStyle, mood, layer, ease, key, glow } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';
import { POSES, posesAt, breathe, walkPose, face, drawFigure } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/rig2d.js';
import * as FX from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/fx2d.js';

const D = window.STICKMAN;
const canvas = document.querySelector('canvas'), g = canvas.getContext('2d');
canvas.width = D.ancho; canvas.height = D.alto;
Object.assign(E, { W: 1920, H: 1920 * D.alto / D.ancho, PX: D.ancho / 1920,
  vertical: D.alto > D.ancho, fps: D.fps, cfg: {}, words: [] });
setStyle(D.variante.acabado);
const clamp = v => Math.min(1, Math.max(0, v));
function valor(keys, t, campo, defecto) {
  const lista = keys.filter(k => k[campo] !== undefined).map(k => [k.t, k[campo]]);
  return lista.length ? key(t, lista, ease.inOut) : defecto;
}
function figura(c, t) {
  const v = c.diseno, keys = c.claves;
  const x = valor(keys, t, 'x', c.x) * E.W, y = valor(keys, t, 'y', c.y) * E.H;
  const s = valor(keys, t, 'escala', c.escala) * (D.escena.muestra ? E.H / 1920 : 1), rot = valor(keys, t, 'rot', 0);
  const fase = t * Math.PI * (c.movimiento === 'correr' ? 3.2 : 1.8);
  const pose = ['caminar', 'correr'].includes(c.movimiento) ? walkPose(fase, {run: c.movimiento === 'correr'})
    : breathe(posesAt(t, keys.filter(k => k.pose).map(k => [k.t, k.pose])), t);
  const exp = keys.filter(k => k.t <= t && k.expresion).at(-1)?.expresion || c.expresion;
  const habla = c.habla.some(a => t >= a[0] && t < a[1]) ? .35 + .6 * Math.abs(Math.sin(t * 14)) : 0;
  const M = mood(D.escena.ambiente);
  // El Classic conserva ropa, accesorios y utilería del rig original.
  if (v.familia === 'classic' && v.cabeza === 1 && v.cuerpo === 1 && v.ancho === 1 && v.ojos === 'dot' && v.boca === 'smallSmile') {
    drawFigure(g, {x, y, s: s * v.altura, facing: c.mirar, rot, pose, expr: exp, talk: habla,
      outfit: {top: v.ropa, color: v.color, color2: v.secundario, head: v.accesorio, headColor: v.secundario},
      rim: {color: v.contorno, dir: [-1, -.5], w: v.trazo}, blink: (t % 3.3) > 3.15});
    return;
  }
  g.save(); g.translate(x, y); g.rotate(rot); g.scale(s * v.altura * c.mirar, s * v.altura);
  g.fillStyle = '#0008'; g.beginPath(); g.ellipse(0, 3, 52 * v.ancho, 9, 0, 0, Math.PI * 2); g.fill();
  g.scale(v.ancho, v.cuerpo);
  const ink = v.familia === 'bean' ? v.color : '#08110f';
  g.lineJoin = g.lineCap = 'round';
  function linea(points, color, width) {
    g.strokeStyle = color; g.lineWidth = width; g.beginPath();
    points.forEach((p, i) => i ? g.lineTo(...p) : g.moveTo(...p)); g.stroke();
  }
  for (const pts of [[pose.hip, pose.kB, pose.fB], [pose.sh, pose.eB, pose.hB],
    [pose.hip, pose.kF, pose.fF], [pose.sh, pose.eF, pose.hF]]) {
    linea(pts, v.contorno, v.trazo + 13); linea(pts, ink, 13);
  }
  if (v.familia === 'bean') {
    g.fillStyle = v.color; g.beginPath(); g.roundRect(-37, -248, 78, 230, 39); g.fill();
  } else {
    linea([pose.sh, pose.hip], v.contorno, 43);
    linea([pose.sh, pose.hip], v.ropa === 'none' ? ink : v.color, v.familia === 'geometric' ? 49 : 37);
    g.fillStyle = v.color;
    if (v.ropa === 'dress') {
      g.beginPath(); g.moveTo(pose.sh[0] - 15, pose.sh[1]); g.lineTo(pose.hip[0] - 40, pose.hip[1] + 20);
      g.lineTo(pose.hip[0] + 40, pose.hip[1] + 20); g.lineTo(pose.sh[0] + 15, pose.sh[1]); g.fill();
    }
    if (['labcoat', 'trench'].includes(v.ropa)) g.fillRect(pose.hip[0] - 21, pose.hip[1] - 12, 42, 40);
    if (['labcoat', 'suit', 'trench'].includes(v.ropa)) linea([[pose.sh[0], pose.sh[1] + 10], [pose.hip[0], pose.hip[1] + 15]], v.secundario, 4);
  }
  g.save(); g.translate(...pose.head); g.scale(v.cabeza, v.cabeza / v.cuerpo);
  if (v.familia !== 'bean') {
    g.fillStyle = v.familia === 'rubber' ? '#fff8ee' : v.familia === 'geometric' ? v.secundario : '#07110d';
    g.strokeStyle = v.contorno; g.lineWidth = v.trazo;
    g.beginPath(); if (v.familia === 'geometric') g.rect(-28, -28, 56, 56);
    else g.ellipse(0, 0, 29, 29, 0, 0, Math.PI * 2); g.fill(); g.stroke();
  }
  face(g, 0, 0, 26, {expr: exp, talk: habla, front: true,
    override: exp === 'neutral' ? {eyes: v.ojos, mouth: v.boca} : {},
    color: ['rubber', 'bean'].includes(v.familia) ? '#11251c' : '#fff', blink: (t % 3.3) > 3.15});
  g.fillStyle = v.secundario;
  if (['cap', 'capBack', 'beanie', 'fedora', 'hood'].includes(v.accesorio)) {
    g.beginPath(); g.ellipse(0, -18, 32, 24, 0, Math.PI, Math.PI * 2); g.fill();
    g.fillRect(-32, -25, v.accesorio === 'cap' ? 78 : 64, 8);
  } else if (v.accesorio === 'headband' || v.accesorio === 'visor') g.fillRect(-30, -22, 60, 8);
  else if (['ponytail', 'bun', 'curly', 'spiky'].includes(v.accesorio)) {
    g.beginPath(); g.ellipse(-28, -20, 15, v.accesorio === 'ponytail' ? 38 : 15, -.3, 0, Math.PI * 2); g.fill();
  }
  g.restore(); g.restore();
}
function objeto(o, t) {
  const x = valor(o.claves, t, 'x', o.x) * E.W, y = valor(o.claves, t, 'y', o.y) * E.H;
  const s = valor(o.claves, t, 'escala', o.escala);
  g.save(); g.translate(x, y); g.rotate(valor(o.claves, t, 'rot', 0)); g.scale(s, s);
  g.fillStyle = o.color; g.strokeStyle = o.color; g.lineWidth = 6;
  if (o.tipo === 'circulo') {g.beginPath(); g.arc(0, 0, o.w, 0, Math.PI * 2); g.fill();}
  else if (o.tipo === 'linea') {g.beginPath(); g.moveTo(0, 0); g.lineTo(o.w, o.h); g.stroke();}
  else if (o.tipo === 'texto') {g.font = `800 ${o.w}px sans-serif`; g.textAlign = 'center'; g.fillText(o.texto, 0, 0);}
  else {g.beginPath(); g.roundRect(-o.w/2, -o.h/2, o.w, o.h, o.tipo === 'rectangulo' ? 0 : 12); g.fill();}
  g.restore();
}
window.pintar = t => {
  const S = D.escena, M = mood(S.ambiente);
  g.setTransform(E.PX, 0, 0, E.PX, 0, 0);
  const bg = g.createLinearGradient(0, 0, 0, E.H); bg.addColorStop(0, M.sky[0]); bg.addColorStop(1, M.wall);
  g.fillStyle = bg; g.fillRect(0, 0, E.W, E.H);
  const cam = {z: 1 + .04 * clamp(t / D.duracion), x: valor(S.camara, t, 'x', 0),
    y: valor(S.camara, t, 'y', 0)};
  cam.z = valor(S.camara, t, 'escala', cam.z);
  layer(g, cam, 1, () => {
    if (S.decorado !== 'vacio') {
      g.fillStyle = M.floor; g.fillRect(-E.W, E.H * .79, E.W * 3, E.H);
      if (S.decorado === 'interior') {
        g.fillStyle = M.key; g.globalAlpha = .75; g.fillRect(E.W * .65, E.H * .18, E.W * .22, E.H * .40);
        g.globalAlpha = 1; g.fillStyle = M.dark; g.fillRect(E.W * .755, E.H * .18, 12, E.H * .40);
        glow(g, E.W * .75, E.H * .4, 300, M.key, .12);
      } else if (S.decorado === 'ciudad') FX.skyline(g, {y: E.H * .72, color: M.dark});
      else if (S.decorado === 'naturaleza') FX.hills(g, {y: E.H * .7, color: M.dark});
    }
    S.objetos.filter(o => o.capa === 'fondo' && t >= o.inicio && t <= o.fin).forEach(o => objeto(o, t));
    S.personajes.forEach(c => figura(c, t));
    S.objetos.filter(o => o.capa !== 'fondo' && t >= o.inicio && t <= o.fin).forEach(o => objeto(o, t));
  });
  if (S.atmosfera === 'lluvia') FX.rain(g, t);
  else if (S.atmosfera === 'polvo') FX.dust(g, t);
  else if (S.atmosfera === 'nieve') FX.snow(g, t);
  return 1;
};
