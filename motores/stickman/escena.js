// Adaptador declarativo sobre el rig GrowKaz. No ejecuta código del modelo.
import { E, setStyle, mood, layer, ease, key, glow } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';
import { posesAt, breathe, walkPose, face, drawFigure } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/rig2d.js';
import * as FX from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/fx2d.js';

const D = window.STICKMAN;
const canvas = document.querySelector('canvas'), g = canvas.getContext('2d');
canvas.width = D.ancho; canvas.height = D.alto;
Object.assign(E, { W: 1920, H: 1920 * D.alto / D.ancho, PX: D.ancho / 1920,
  vertical: D.alto > D.ancho, fps: D.fps, cfg: {}, words: [] });
setStyle(D.variante.acabado);
function valor(keys, t, campo, defecto, interpolacion = ease.inOut) {
  const lista = keys.filter(k => k[campo] !== undefined).map(k => [k.t, k[campo]]);
  // Una primera clave tardía es un destino, no el valor desde el primer frame.
  if (lista.length && lista[0][0] > 0) lista.unshift([0, defecto]);
  return lista.length ? key(t, lista, interpolacion) : defecto;
}
function estado(c, t) {
  const v = c.diseno, keys = c.claves;
  const x = valor(keys, t, 'x', c.x) * E.W, y = valor(keys, t, 'y', c.y) * E.H;
  const s = valor(keys, t, 'escala', c.escala) * (D.escena.muestra ? E.H / 1920 : 1), rot = valor(keys, t, 'rot', 0);
  const fase = t * Math.PI * (c.movimiento === 'correr' ? 3.2 : 1.8);
  const pose = ['caminar', 'correr'].includes(c.movimiento) ? walkPose(fase, {run: c.movimiento === 'correr'})
    : breathe(posesAt(t, keys.filter(k => k.pose).map(k => [k.t, k.pose])), t);
  const exp = keys.filter(k => k.t <= t && k.expresion).at(-1)?.expresion || c.expresion;
  const mirar = keys.filter(k => k.t <= t && k.mirar !== undefined).at(-1)?.mirar ?? c.mirar;
  return {x, y, s, rot, pose, exp, mirar};
}
function figura(c, t) {
  const v = c.diseno, {x, y, s, rot, pose, exp, mirar} = estado(c, t);
  const habla = c.habla.some(a => t >= a[0] && t < a[1]) ? .35 + .6 * Math.abs(Math.sin(t * 14)) : 0;
  g.save(); g.translate(x, y); g.rotate(rot); g.scale(s * v.altura * mirar, s * v.altura);
  g.globalAlpha *= valor(c.claves, t, 'opacidad', 1);
  // El Classic conserva ropa, accesorios y utilería del rig original.
  if (v.familia === 'classic' && v.cabeza === 1 && v.cuerpo === 1 && v.ancho === 1 && v.ojos === 'dot' && v.boca === 'smallSmile') {
    drawFigure(g, {x: 0, y: 0, s: 1, facing: 1, pose, expr: exp, talk: habla,
      outfit: {top: v.ropa, color: v.color, color2: v.secundario, head: v.accesorio, headColor: v.secundario},
      rim: {color: v.contorno, dir: [-1, -.5], w: v.trazo}, blink: (t % 3.3) > 3.15});
    g.restore(); return;
  }
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
function vector(o, t) {
  const d = D.escena.utileria[o.recurso];
  const paleta = {principal: D.variante.color, secundario: D.variante.secundario,
    contorno: D.variante.contorno, claro: '#fff8ee', oscuro: '#162532', ...o.paleta};
  const color = c => c?.startsWith('$') ? paleta[c.slice(1)] : c;
  g.save();
  const ajuste = Math.min(o.w / d.ancho, o.h / d.alto);
  g.scale(ajuste, ajuste);
  g.translate(-d.ancho/2, -d.alto/2);
  for (const p of d.partes) {
    const anim = p.animacion;
    const reloj = anim ? Math.max(0, t-o.inicio) % anim.duracion : 0;
    const ks = o.partes?.find(a => a.id === p.id)?.claves || [];
    const v = (campo, defecto) => {
      const base = anim ? valor(anim.claves, reloj, campo, defecto, ease.linear) : defecto;
      if (!ks.some(k => k[campo] !== undefined)) return base;
      const inicial = anim ? valor(anim.claves, 0, campo, defecto, ease.linear) : defecto;
      return valor(ks, t, campo, inicial);
    };
    const [px, py] = p.pivote;
    g.save(); g.translate(px + v('x', 0), py + v('y', 0));
    g.rotate(v('rot', 0)); const s = v('escala', 1); g.scale(s, s); g.translate(-px, -py);
    g.globalAlpha *= v('opacidad', 1);
    for (const f of p.formas) {
      g.beginPath();
      if (f.tipo === 'elipse') g.ellipse(f.x+f.w/2, f.y+f.h/2, f.w/2, f.h/2, 0, 0, Math.PI*2);
      else if (f.tipo === 'rectangulo') g.roundRect(f.x, f.y, f.w, f.h, f.radio);
      else for (const [cmd, ...n] of f.comandos) {
        if (cmd === 'M') g.moveTo(...n);
        else if (cmd === 'L') g.lineTo(...n);
        else if (cmd === 'Q') g.quadraticCurveTo(...n);
        else if (cmd === 'C') g.bezierCurveTo(...n);
        else if (cmd === 'Z') g.closePath();
      }
      if (f.relleno !== null) {g.fillStyle = color(f.relleno); g.fill();}
      if (f.trazo !== null) {g.strokeStyle = color(f.trazo); g.lineWidth = f.grosor; g.stroke();}
    }
    g.restore();
  }
  g.restore();
}
function objeto(o, t) {
  let x = valor(o.claves, t, 'x', o.x) * E.W, y = valor(o.claves, t, 'y', o.y) * E.H;
  if (o.ancla) {
    const c = D.escena.personajes.find(c => c.id === o.ancla.personaje);
    const a = estado(c, t), v = c.diseno;
    const p = o.ancla.punto === 'pecho'
      ? [(a.pose.sh[0]+a.pose.hip[0])/2, (a.pose.sh[1]+a.pose.hip[1])/2]
      : a.pose[{mano: 'hF', cabeza: 'head'}[o.ancla.punto]];
    const custom = !(v.familia === 'classic' && v.cabeza === 1 && v.cuerpo === 1 && v.ancho === 1 && v.ojos === 'dot' && v.boca === 'smallSmile');
    const dx = p[0] * a.s * v.altura * a.mirar * (custom ? v.ancho : 1);
    const dy = p[1] * a.s * v.altura * (custom ? v.cuerpo : 1);
    x += a.x + dx * Math.cos(a.rot) - dy * Math.sin(a.rot);
    y += a.y + dx * Math.sin(a.rot) + dy * Math.cos(a.rot);
  }
  const s = valor(o.claves, t, 'escala', o.escala);
  const progreso = valor(o.claves, t, 'progreso', o.progreso ?? 1);
  const w = o.w, h = o.h;
  g.save(); g.translate(x, y); g.rotate(valor(o.claves, t, 'rot', 0)); g.scale(s, s);
  g.globalAlpha *= valor(o.claves, t, 'opacidad', o.opacidad ?? 1);
  g.fillStyle = o.color; g.strokeStyle = o.color; g.lineWidth = o.grosor ?? 6;
  g.lineJoin = g.lineCap = 'round';
  const caja = (x, y, w, h, r=8) => {g.beginPath(); g.roundRect(x, y, w, h, Math.min(r, w/2, h/2)); g.fill();};
  const trazo = (x, y, xx, yy) => {g.beginPath(); g.moveTo(x, y); g.lineTo(xx, yy); g.stroke();};
  if (o.tipo === 'vector') vector(o, t);
  else if (o.tipo === 'circulo') {g.beginPath(); g.ellipse(0, 0, w/2, h/2, 0, 0, Math.PI * 2); g.fill();}
  else if (o.tipo === 'linea') {trazo(0, 0, w * progreso, h * progreso);}
  else if (o.tipo === 'texto') {
    let size = Math.min(o.fuente ?? 48, h * .8);
    g.font = `800 ${size}px sans-serif`;
    size *= Math.min(1, w / Math.max(1, g.measureText(o.texto).width));
    g.font = `800 ${size}px sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText(o.texto, 0, 0);
  }
  else if (o.tipo === 'pizarra') {
    const marco = Math.min(14, w*.04, h*.07);
    g.fillStyle = '#79533b'; caja(-w/2, -h/2, w, h, 12);
    g.fillStyle = o.color; caja(-w/2+marco, -h/2+marco, w-2*marco, h-2*marco, 3);
    g.strokeStyle = '#ffffff26'; g.lineWidth = 3;
    trazo(-w*.44, -h*.39, -w*.15, -h*.39);
    g.fillStyle = '#ba916b'; caja(-w*.52, h/2-10, w*1.04, 20, 4);
    g.fillStyle = '#fff8ee'; caja(w*.26, h/2-19, Math.min(65,w*.12), 9, 3);
    g.fillStyle = '#263d36'; caja(-w*.3, h/2-29, Math.min(90,w*.16), 19, 4);
  }
  else if (o.tipo === 'tarjeta') {
    g.fillStyle = '#0003'; caja(-w/2+7, -h/2+9, w, h, 10);
    g.fillStyle = o.color; caja(-w/2, -h/2, w, h, 10);
    g.strokeStyle = '#263d36'; g.lineWidth = 3;
    g.stroke();
  }
  else if (o.tipo === 'movil') {
    g.fillStyle = '#162532'; caja(-w/2, -h/2, w, h, w*.15);
    g.fillStyle = o.color; caja(-w*.37, -h*.36, w*.74, h*.68, 3);
    g.strokeStyle = '#ffffff'; g.lineWidth = Math.max(2, w*.04); trazo(-w*.12, h*.4, w*.12, h*.4);
  }
  else if (o.tipo === 'mensaje') {
    caja(-w/2, -h/2, w, h*.8, h*.16);
    g.beginPath(); g.moveTo(-w*.3, h*.2); g.lineTo(-w*.35, h*.5); g.lineTo(-w*.1, h*.2); g.fill();
    g.strokeStyle = '#243746'; g.lineWidth = Math.max(3, h*.05);
    trazo(-w*.32, -h*.18, w*.3, -h*.18); trazo(-w*.32, h*.02, w*.12, h*.02);
  }
  else if (o.tipo === 'calendario') {
    g.fillStyle = '#fffdf5'; caja(-w/2, -h/2, w, h, 12);
    g.fillStyle = o.color; caja(-w/2, -h/2, w, h*.24, 8);
    g.strokeStyle = '#283d4c'; g.lineWidth = 5;
    trazo(-w*.28, -h*.58, -w*.28, -h*.38); trazo(w*.28, -h*.58, w*.28, -h*.38);
    g.strokeStyle = '#b9c4ca'; g.lineWidth = 2;
    for (let i=1; i<7; i++) trazo(-w*.43+i*w*.86/7, -h*.19, -w*.43+i*w*.86/7, h*.42);
    for (let i=0; i<4; i++) trazo(-w*.43, -h*.19+i*h*.61/3, w*.43, -h*.19+i*h*.61/3);
    g.fillStyle = '#364957'; g.font = `${Math.min(w/18,h/12)}px sans-serif`; g.textAlign = 'center'; g.textBaseline = 'middle';
    for (let i=0; i<21; i++) g.fillText(String(i+1), -w*.43+(i%7+.5)*w*.86/7, -h*.19+(Math.floor(i/7)+.5)*h*.61/3);
    g.strokeStyle = '#e16a3d'; g.lineWidth = 5;
    for (let i=0; i<Math.ceil(progreso*3); i++) {
      const cx = -w*.43+([2,10,18][i]%7+.5)*w*.86/7, cy = -h*.19+(i+.5)*h*.61/3;
      g.beginPath(); g.ellipse(cx, cy, w*.055, h*.075, 0, 0, Math.PI*2); g.stroke();
    }
  }
  else if (o.tipo === 'nube') {
    for (const [cx,cy,rx,ry] of [[-.28,.05,.22,.29],[-.08,-.12,.27,.38],[.19,-.04,.28,.32],[.34,.12,.16,.22]]) {
      g.beginPath(); g.ellipse(cx*w,cy*h,rx*w,ry*h,0,0,Math.PI*2); g.fill();
    }
    caja(-w*.32, 0, w*.64, h*.32, h*.12);
  }
  else if (o.tipo === 'corazon') {
    g.beginPath(); g.moveTo(0,h/2); g.bezierCurveTo(-w,-h*.15,-w*.35,-h*.85,0,-h*.2);
    g.bezierCurveTo(w*.35,-h*.85,w,-h*.15,0,h/2); g.fill();
  }
  else {g.beginPath(); g.roundRect(-o.w/2, -o.h/2, o.w, o.h, o.tipo === 'rectangulo' ? 0 : 12); g.fill();}
  g.restore();
}
window.pintar = t => {
  const S = D.escena, M = mood(S.ambiente);
  g.setTransform(E.PX, 0, 0, E.PX, 0, 0);
  const bg = g.createLinearGradient(0, 0, 0, E.H); bg.addColorStop(0, M.sky[0]); bg.addColorStop(1, M.wall);
  g.fillStyle = bg; g.fillRect(0, 0, E.W, E.H);
  const cam = {z: 1, x: valor(S.camara, t, 'x', 0) * E.W,
    y: valor(S.camara, t, 'y', 0) * E.H};
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
