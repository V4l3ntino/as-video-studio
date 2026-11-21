"""Evidencia local reproducible: referencia recortada, renders y conservación SHA.

Nunca consulta proveedores. --inicio crea una carpeta nueva; --render usa fuentes
de trabajo con las dependencias YA instaladas de v3, sin escribir en ese paquete.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pasos import medios


def inventario(estilo):
    paths = []
    for name in ('referencias', 'constructor_respuestas', 'analisis_visual', 'transcripcion'):
        paths += [p for p in (estilo/name).rglob('*') if p.is_file() and not any(
            s in p.parts for s in ('dependencias', 'whisper', 'pyscenedetect', '__pycache__'))]
    for version in (estilo/'versiones').glob('v*'):
        paths += [p for p in version.rglob('*') if p.is_file() and not any(
            s in p.parts for s in ('dependencias', 'cache', 'trabajo', '__pycache__'))]
    paths += [estilo/'referencia.mp4']
    # Estados, manifiestos y fuentes de proyectos existentes (solo lectura).
    from pasos import presets_canal
    paths += [Path(presets_canal.ruta())] if hasattr(presets_canal, 'ruta') else []
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--estilo', required=True, type=Path)
    p.add_argument('--salida', required=True, type=Path)
    p.add_argument('--inicio', action='store_true')
    p.add_argument('--render', action='store_true')
    p.add_argument('--conservar', action='store_true')
    a = p.parse_args()
    if a.inicio:
        a.salida.mkdir(parents=True, exist_ok=False)
        (a.salida/'conservacion_antes.json').write_text(json.dumps(inventario(a.estilo), indent=2), encoding='utf8')
        times = [0.8, 5, 9, 18, 33, 42, 57, 64, 77, 99.64, 104, 108, 117.5, 123, 148, 163, 177.4, 185,169.04]
        for i, t in enumerate(times):
            subprocess.run([medios.ffmpeg(), '-v', 'error', '-ss', str(t), '-i', str(a.estilo/'referencia.mp4'),
                '-frames:v', '1', '-vf', 'crop=608:1080:656:0', str(a.salida/f'ref_{i:02}_{t}.png')], check=True)
        # Secuencias temporales sin cambiar análisis ni caché previos.
        for start in (32, 56, 98, 115, 175, 182):
            subprocess.run([medios.ffmpeg(), '-v', 'error', '-ss', str(start), '-i', str(a.estilo/'referencia.mp4'),
                '-t', '3', '-vf', 'crop=608:1080:656:0,fps=4,scale=180:320,tile=6x2', '-frames:v', '1',
                str(a.salida/f'temporal_ref_{start}.png')], check=True)
        sys.path.insert(0, str(a.estilo/'versiones/v3/dependencias'))
        from PIL import Image, ImageDraw
        for group in range(3):
            sheet=Image.new('RGB',(360*6,660),'#20202C')
            for i,t in enumerate(times[group*6:group*6+6]):
                file=list(a.salida.glob(f'ref_{group*6+i:02}_*.png'))[0]
                im=Image.open(file);im.thumbnail((360,640));sheet.paste(im,(i*360,20))
                ImageDraw.Draw(sheet).text((i*360+10,2),f'{t}s',fill='white')
            sheet.save(a.salida/f'referencia_{group}.jpg')
    if a.render:
        a.salida.mkdir(parents=True,exist_ok=False)
        sys.path[:0]=[str(a.estilo/'versiones/v3/dependencias'),str(Path(__file__).resolve().parents[1]/'motores/ricksclips'),
            str(a.estilo/'versiones/v3/herramientas')]
        import types
        from herramientas.preparar_ricksclips import compilar_rig
        rig=types.ModuleType('personaje_base')
        exec(compilar_rig((a.estilo/'versiones/v1/herramientas/personaje_base.py').read_text(encoding='utf8')),rig.__dict__)
        sys.modules['personaje_base']=rig
        import escena
        from PIL import Image
        pedido=dict(ancho=540,alto=960,fps=25,duracion=3,parametros={})
        escena.preparar(pedido)
        sheet=Image.new('RGB',(540*6,960))
        for i,name in enumerate(('oeste','taberna','cocina','mar','canon','puente')):
            pedido['parametros']=dict(escenario=name,demostracion=False)
            im=escena.pintar(pedido,1.5);im.save(a.salida/(name+'.png'));sheet.paste(im,(i*540,0))
        sheet.save(a.salida/'escenarios.jpg')
        from planos_revision import plano
        names=('general','medio','rostro','movil','cocina','cuenco','tormenta','calma','canon','torcida','puente','explosion')
        for row in range(3):
            sheet=Image.new('RGB',(540*4,960))
            for col,name in enumerate(names[row*4:row*4+4]):
                pedido['parametros']=plano(name)
                im=escena.pintar(pedido,1.3);im.save(a.salida/(name+'_plano.png'));sheet.paste(im,(col*540,0))
            sheet.save(a.salida/f'planos_{row}.jpg')
    if a.conservar:
        before=json.loads((a.salida/'conservacion_antes.json').read_text(encoding='utf8'))
        changed=[p for p,h in before.items() if not Path(p).is_file() or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
        result=dict(archivos=len(before),alterados=changed)
        (a.salida/'conservacion_despues.json').write_text(json.dumps(result,indent=2),encoding='utf8')
        print(result)
        assert not changed


if __name__=='__main__':
    main()
