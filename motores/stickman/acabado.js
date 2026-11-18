// Pipeline del player original, adaptado al reloj local del Estudio.
import { E, S, clamp, rng } from '../../GrowKaz_Stickman/skills/make-2d-video/kit/engine/core.js';

let tablas, estilo, granos;
function preparar() {
  if (estilo === S()) return;
  estilo = S();
  const gr = estilo.grade || {};
  tablas = [0, 1, 2].map(c => {
    const tabla = new Uint8ClampedArray(256);
    for (let i = 0; i < 256; i++) {
      let v = clamp((i / 255 - .5) * (gr.contrast ?? 1) + .5);
      v = clamp((gr.gain?.[c] ?? 1) * (v + (gr.lift?.[c] || 0) * (1 - v)));
      tabla[i] = Math.round(Math.pow(v, 1 / (gr.gamma?.[c] || 1)) * 255);
    }
    return tabla;
  });
  granos = Array.from({length: 4}, (_, n) => {
    const c = document.createElement('canvas'); c.width = c.height = 128;
    const ctx = c.getContext('2d'), img = ctx.createImageData(128, 128), random = rng(1234 + n * 999);
    for (let i = 0; i < img.data.length; i += 4) {
      img.data[i] = img.data[i+1] = img.data[i+2] = Math.floor(random() * 256); img.data[i+3] = 255;
    }
    ctx.putImageData(img, 0, 0); return c;
  });
}

export function acabado(g, t, r) {
  if (r.acabado === false) return;
  preparar();
  const W = g.canvas.width, H = g.canvas.height, gr = S().grade || {}, sat = gr.sat ?? 1;
  g.save(); g.setTransform(1, 0, 0, 1, 0, 0);
  // El acabado cromático del estilo no puede recolorear una instrucción explícita.
  if (!r.color_fiel) {
    const img = g.getImageData(0, 0, W, H), d = img.data;
    for (let i = 0; i < d.length; i += 4) {
      const r0 = tablas[0][d[i]], g0 = tablas[1][d[i+1]], b0 = tablas[2][d[i+2]];
      const l = .2126 * r0 + .7152 * g0 + .0722 * b0;
      d[i] = l + (r0-l)*sat; d[i+1] = l + (g0-l)*sat; d[i+2] = l + (b0-l)*sat;
    }
    g.putImageData(img, 0, 0);
  }
  const vineta = r.vineta ?? Math.min(.45, gr.vignette || .3);
  if (vineta) {
    const grad = g.createRadialGradient(W/2, H*.46, Math.min(W,H)*.3, W/2, H/2, Math.max(W,H)*.65);
    grad.addColorStop(0, '#0000'); grad.addColorStop(1, `rgba(0,0,0,${vineta})`);
    g.fillStyle = grad; g.fillRect(0, 0, W, H);
  }
  const grano = r.grano ?? Math.min(.025, gr.grain || 0);
  if (grano) {
    g.globalAlpha = grano; g.globalCompositeOperation = 'overlay';
    g.drawImage(granos[Math.floor(t*Math.min(E.fps, 30)) % 4], 0, 0, W, H);
  }
  g.restore();
}
