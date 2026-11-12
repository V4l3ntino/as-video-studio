import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

// Edita este componente o pega otro con «export default».
// Props: título, subtítulo, autor, color y valores numéricos.
export default function Plantilla({titulo = 'La Cordillera', subtitulo = 'Territorio, agua y memoria',
  autor = 'Un documental de AS Video Studio', color = '#c4cfec', valor = 72,
  valores = [25, 40, 58, 75, 96], variante = '__VARIANTE__'}) {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const entrada = spring({frame, fps, config: {damping: 24}});
  const entradaFrames = Math.min(18, durationInFrames / 3);
  const opacidad = interpolate(frame, [0, entradaFrames, durationInFrames - entradaFrames, durationInFrames],
    [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const estilo = {color, opacity: opacidad, fontFamily: 'Arial, sans-serif', padding: '8%'};
  const tituloEstilo = {fontSize: 76, fontWeight: 400, margin: '24px 0', letterSpacing: 18};
  let contenido;
  if (variante === 'circular') contenido = <svg viewBox="0 0 400 400" style={{height: '70%'}}>
    <circle cx="200" cy="200" r="140" fill="none" stroke="#ffffff22" strokeWidth="24"/>
    <circle cx="200" cy="200" r="140" fill="none" stroke={color} strokeWidth="24" strokeDasharray={`${880 * entrada * valor / 100} 880`} transform="rotate(-90 200 200)"/>
    <text x="200" y="218" textAnchor="middle" fill={color} fontSize="60">{Math.round(valor * entrada)} %</text></svg>;
  else if (variante === 'barras') contenido = <div style={{display: 'flex', gap: 30, height: '65%', alignItems: 'flex-end'}}>
    {valores.map((v, i) => <div key={i} style={{width: 80, height: `${v * entrada}%`, background: color}}/>)}</div>;
  else if (variante === 'lower') contenido = <div style={{position: 'absolute', left: '8%', bottom: '15%', borderLeft: `8px solid ${color}`, paddingLeft: 28, transform: `translateX(${(1 - entrada) * -100}px)`}}>
    <h1 style={{fontSize: 62, margin: 0}}>{titulo}</h1><p style={{fontSize: 32}}>{subtitulo}</p></div>;
  else if (variante === 'fechas') contenido = <div style={{width: '90%', borderTop: `4px solid ${color}`, display: 'flex', justifyContent: 'space-between'}}>
    {['1990', '2000', '2010', '2020'].map((a, i) => <div key={a} style={{fontSize: 38, opacity: interpolate(frame, [i * 8, i * 8 + 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}}>●<br/>{a}</div>)}</div>;
  else if (variante === 'mapa') contenido = <svg viewBox="0 0 800 400" style={{width: '85%'}}>
    <path d="M50 80L170 30 250 80 215 150 150 140 100 200 80 130ZM230 210L290 180 330 240 280 365 245 300ZM360 65L440 40 500 90 580 40 740 90 710 170 600 190 540 150 500 240 420 180 390 110ZM430 180L490 210 460 330 400 260ZM650 280L740 270 760 330 680 345Z" fill={color} opacity=".6"/>
    <circle cx="440" cy="100" r={10 + entrada * 10} fill="#819aff"/><path d="M180 100Q300 -10 440 100" stroke={color} strokeWidth="3" fill="none" strokeDasharray={`${500 * entrada} 500`}/></svg>;
  else if (variante === 'galeria') contenido = <div style={{display: 'flex', gap: 20, transform: `scale(${.8 + entrada * .2})`}}>
    {[0, 1, 2].map(i => <div key={i} style={{width: 300, height: 340, background: `linear-gradient(${120 + i * 30}deg, #637789, #192b32)`, border: '8px solid #ddd', transform: `rotate(${(i - 1) * 5}deg)`}}/>)}</div>;
  else contenido = <div style={{textAlign: 'center', transform: `translateY(${(1 - entrada) * 30}px)`}}>
    <div style={{fontSize: 20, letterSpacing: 10, textTransform: 'uppercase'}}>{autor}</div>
    <h1 style={{...tituloEstilo, fontFamily: variante === 'titulo' ? 'Georgia, serif' : 'Arial',
      fontSize: variante === 'titulo' ? 104 : 76, textTransform: variante === 'titulo' ? 'uppercase' : 'none',
      letterSpacing: variante === 'subtitulos' || variante === 'cita' ? 1 : 18}}>{titulo}</h1>
    <div style={{display: 'flex', alignItems: 'center', gap: 30, justifyContent: 'center'}}>
      <div style={{height: 1, width: 140 * entrada, background: color}}/>
      <p style={{fontSize: 24, letterSpacing: 8, textTransform: 'uppercase'}}>{subtitulo}</p>
      <div style={{height: 1, width: 140 * entrada, background: color}}/>
    </div></div>;
  return <AbsoluteFill style={{...estilo, alignItems: 'center', justifyContent: 'center'}}>{contenido}</AbsoluteFill>;
}
