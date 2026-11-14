// El motor Node es independiente del frontend. Reutiliza esbuild de Remotion.
import { build } from '../remotion/node_modules/esbuild/lib/main.js';
import { fileURLToPath } from 'node:url';
await build({ entryPoints: [fileURLToPath(new URL('./escena.js', import.meta.url))],
  outfile: process.argv[2], bundle: true, format: 'iife', platform: 'browser', target: 'chrome110' });
