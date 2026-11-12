// Proceso local opcional. No importa ni ejecuta módulos Python del Estudio.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderFrames, selectComposition} from '@remotion/renderer';
import {build} from 'esbuild';

const raiz = path.dirname(fileURLToPath(import.meta.url));
const dependencias = path.join(raiz, 'node_modules');
const informar = (progreso, mensaje) => console.log(JSON.stringify({progreso, mensaje}));

async function ejecutar() {
  if (process.argv[2] === '--comprobar') { informar(1, 'Remotion disponible'); return; }
  const pedido = JSON.parse(await fs.readFile(process.argv[2], 'utf8'));
  const {accion, carpeta, plantilla} = pedido;
  if (accion === 'compilar') {
    await fs.mkdir(carpeta, {recursive: true});
    const componente = path.join(carpeta, 'Plantilla.tsx');
    await fs.writeFile(componente, plantilla.codigo);
    const entrada = path.join(carpeta, 'entrada.tsx');
    await fs.writeFile(entrada, `import React from 'react';
import {registerRoot, Composition} from 'remotion';
import Plantilla from './Plantilla';
registerRoot(() => <Composition id="plantilla" component={Plantilla} width={${plantilla.ancho}} height={${plantilla.alto}} fps={${plantilla.fps}} durationInFrames={${Math.max(1, Math.round(plantilla.duracion * plantilla.fps))}} />);`);
    informar(.1, 'Compilando composición React');
    await bundle({entryPoint: entrada, outDir: path.join(carpeta, 'render'),
      webpackOverride: config => ({...config, resolve: {...config.resolve,
        modules: [dependencias, ...(config.resolve?.modules || [])]}})});
    const previa = path.join(carpeta, 'previa.tsx');
    await fs.writeFile(previa, `import React, {useRef, useState, useEffect} from 'react';
import {createRoot} from 'react-dom/client';
import {Player} from '@remotion/player';
import Plantilla from './Plantilla';
class Limite extends React.Component { state = {error: ''}; static getDerivedStateFromError(e) {return {error: e.message};} render() {return this.state.error ? <pre style={{color: '#ffb4bf', padding: 20}}>{this.state.error}</pre> : this.props.children;} }
function Previa() {
  const ref = useRef(null), [config, setConfig] = useState(null);
  useEffect(() => {const recibir = e => {
    if (e.source !== parent || e.data?.tipo !== 'asvs-remotion') return;
    if (e.data.config) setConfig(e.data.config);
    if (Number.isFinite(e.data.frame)) ref.current?.seekTo(e.data.frame);
    if (e.data.reproducir === true) ref.current?.play();
    if (e.data.reproducir === false) ref.current?.pause();
  }; addEventListener('message', recibir); parent.postMessage({tipo: 'asvs-remotion-listo'}, '*');
  return () => removeEventListener('message', recibir);}, []);
  return config && <Limite key={JSON.stringify(config)}><Player ref={ref} component={Plantilla} inputProps={config.props} compositionWidth={config.ancho} compositionHeight={config.alto} fps={config.fps} durationInFrames={Math.max(1, Math.round(config.duracion * config.fps))} controls={false} style={{width: '100%', height: '100%'}} /></Limite>;
}
createRoot(document.getElementById('root')).render(<Previa/>);`);
    await build({entryPoints: [previa], bundle: true, outfile: path.join(carpeta, 'preview.js'),
      platform: 'browser', format: 'iife', jsx: 'automatic', nodePaths: [dependencias],
      define: {'process.env.NODE_ENV': '"production"'}});
    await fs.writeFile(path.join(carpeta, 'preview.html'), '<!doctype html><html><head><meta charset="utf-8"><style>html,body,#root{margin:0;width:100%;height:100%;overflow:hidden;background:transparent}*{box-sizing:border-box}</style></head><body><div id="root"></div><script src="preview.js"></script></body></html>');
  } else if (accion === 'render') {
    const serveUrl = path.join(pedido.compilado, 'render');
    const composition = await selectComposition({serveUrl, id: 'plantilla', inputProps: plantilla.props, browserExecutable: pedido.navegador});
    await renderFrames({serveUrl, composition: {...composition, width: plantilla.ancho,
      height: plantilla.alto, fps: plantilla.fps,
      durationInFrames: Math.max(1, Math.round(plantilla.duracion * plantilla.fps))},
      inputProps: plantilla.props, outputDir: carpeta, imageFormat: 'png', scale: pedido.escala || 1,
      browserExecutable: pedido.navegador,
      imageSequencePattern: 'f[frame].[ext]', muted: true, concurrency: 2,
      onFrameUpdate: n => informar(n / Math.max(1, Math.round(plantilla.duracion * plantilla.fps)), 'Renderizando animación Remotion')});
  } else throw new Error('Acción Remotion desconocida');
  informar(1, 'Listo');
}
ejecutar().catch(e => {console.error(e.stack || e.message); process.exitCode = 1;});
