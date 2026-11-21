"""Índice de evidencias e integridad tras publicación. No genera ni consulta IA."""
import argparse
import copy
import hashlib
import html
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--estilo',required=True,type=Path)
    p.add_argument('--revision',required=True,type=Path)
    p.add_argument('--renders',default='hd_final',help='carpeta de renders final dentro de revision')
    p.add_argument('--ajustes',default='hd_ajuste_subtitulos',help='carpeta opcional de sustituciones; se omite si no existe')
    p.add_argument('--base-proyectos',default='proyectos_antes.json',help='inventario de proyectos previo dentro de revision')
    p.add_argument('--extra-renders',nargs='*',default=[],help='otras carpetas de secuencias HD que se añaden a la entrega')
    p.add_argument('--comparaciones',default='comparacion_definitiva',help='carpeta de comparaciones dentro de revision')
    a=p.parse_args();out=a.revision/'entrega'
    if out.exists() and any(out.iterdir()):raise ValueError('la entrega ya contiene evidencias; no se sobrescribe')
    out.mkdir(exist_ok=True)
    from pasos import presets_canal,espacio_estilo,medios
    old=json.loads((a.revision/'preset_antes.json').read_text(encoding='utf8'))
    now=presets_canal.leer(old['id']);marca=now['datos']['estilo']['espacio_ia']
    espacio=a.estilo/'versiones'/('v'+str(marca['version']))
    espacio_estilo.verificar(espacio,marca['huella'])
    datos_old=copy.deepcopy(old['datos']);datos_new=copy.deepcopy(now['datos'])
    for d in (datos_old,datos_new):
        d['estilo'].pop('espacio_ia',None)
        # Metadatos de procedencia del NUEVO manifiesto, no ajustes de voz/montaje.
        origen=d.get('origen',{}).get('estilo_ia',{})
        origen.pop('version',None);origen.pop('huella',None)
    conservar={}
    actualizaciones={}
    for file in ('conservacion_antes.json',a.base_proyectos):
        before=json.loads((a.revision/file).read_text(encoding='utf8'))
        changed=[p for p,h in before.items() if not Path(p).is_file() or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
        ficha_path=str(a.estilo/'estilo.json')
        snapshot=a.revision/'estilo_antes.json'
        if file=='conservacion_antes.json' and ficha_path in changed and snapshot.is_file():
            assert hashlib.sha256(snapshot.read_bytes()).hexdigest()==before[ficha_path]
            anterior=json.loads(snapshot.read_text(encoding='utf8'))
            actual=json.loads(Path(ficha_path).read_text(encoding='utf8'))
            claves={k for k in anterior.keys()|actual.keys() if anterior.get(k)!=actual.get(k)}
            assert claves.issubset({'espacio','estado','error','muestra_comprobada','limites'}),claves
            assert actual['espacio']==marca and actual['estado']=='preparado'
            actualizaciones[ficha_path]=dict(campos=sorted(claves),motivo='Publicación real de una nueva versión; instantánea anterior conservada')
            changed.remove(ficha_path)
        conservar[file]=dict(archivos=len(before),alterados=changed)
        assert not changed,changed
    assert datos_old==datos_new,'algún ajuste del preset ajeno a espacio_ia cambió'
    resultado=dict(preset=old['id'],espacio=marca,paquete_sellado_verificado=True,
        ajustes_del_preset_conservados=True,nombre_conservado=old['nombre']==now['nombre'],
        conservacion=conservar,proveedores_usados=0,calidad_equivalente=False)
    resultado['actualizaciones_autorizadas']=actualizaciones
    renders=json.loads((a.revision/a.renders/'renders.json').read_text(encoding='utf8'))
    for folder in a.extra_renders:
        renders.extend(json.loads((a.revision/folder/'renders.json').read_text(encoding='utf8')))
    ajuste_path=a.revision/a.ajustes/'renders.json'
    ajustes=json.loads(ajuste_path.read_text(encoding='utf8')) if ajuste_path.is_file() else []
    requeridos={'general','medio','rostro','movil','cocina','cuenco','tormenta','calma','canon','torcida','puente','explosion','pupila','expresiones'}
    assert requeridos.issubset({r['plano'] for r in renders}),'faltan secuencias HD'
    nuevos={r['plano']:r for r in ajustes}
    finales=[nuevos.get(r['plano'],r) for r in renders]
    probes=[]
    for r in finales:
        raw=subprocess.check_output([medios.ffprobe(),'-v','error','-select_streams','v:0',
            '-show_entries','stream=width,height,avg_frame_rate,nb_frames:format=duration','-of','json',r['clip']])
        probe=json.loads(raw);v=probe['streams'][0]
        assert (v['width'],v['height'],v['avg_frame_rate'],int(v['nb_frames']))==(1080,1920,'25/1',round(r['duracion']*25))
        probes.append(dict(plano=r['plano'],clip=r['clip'],ffprobe=probe))
    resultado['renders_hd']=probes
    (out/'integridad.json').write_text(json.dumps(resultado,indent=2),encoding='utf8')
    concat=out/'secuencias.txt'
    concat.write_text('\n'.join("file '"+Path(r['clip']).as_posix()+"'" for r in finales),encoding='utf8')
    subprocess.run([medios.ffmpeg(),'-v','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',
        str(out/'revision_hd.mp4')],check=True)
    partes=[f'<!doctype html><meta charset="utf-8"><title>RicksClips: evidencias v{marca["version"]}</title>',
        '<h1>RicksClips: revisión local</h1><p>Calidad mejorada, NO equivalente a la referencia.</p>',
        '<p><a href="revision_hd.mp4">Vídeo de revisión HD</a> · <a href="../INFORME_VISUAL.md">Informe visual</a> · <a href="integridad.json">Integridad y FFprobe</a></p>',
        '<p>Los fotogramas originales solo se usaron para estudiar y comparar. No son fondos del motor.</p>',
        '<h2>Comparaciones: referencia / versión anterior / nueva versión</h2>']
    for im in sorted((a.revision/a.comparaciones).glob('*_comparacion.jpg')):
        rel='../'+im.relative_to(a.revision).as_posix()
        partes.append(f'<h3>{html.escape(im.stem)}</h3><a href="{rel}"><img width="810" src="{rel}"></a>')
    partes.append('<h2>Secuencias 1080 × 1920 / 25 fps</h2>')
    for renderdir in (a.renders,a.ajustes,*a.extra_renders):
        if not (a.revision/renderdir/'renders.json').is_file():continue
        records=json.loads((a.revision/renderdir/'renders.json').read_text(encoding='utf8'))
        for r in records:
            clip=Path(r['clip']);rel='../'+clip.relative_to(a.revision).as_posix()
            partes.append(f'<p><a href="{rel}">{html.escape(renderdir+" / "+r["plano"])}</a></p>')
    partes.append('<h2>Subtítulos: fallo detectado y corrección</h2>')
    for folder in ('subtitulos_rostro','subtitulos_rostro_corregido'):
        if not (a.revision/folder/'019.png').is_file():continue
        partes.append(f'<p>{folder}</p><img width="270" src="../{folder}/019.png">')
    partes.append('<p>Marcas de subtítulos sintéticas, sin generar voz.</p>')
    for folder in sorted(a.revision.glob('subtitulos_*')):
        if folder.is_dir() and (folder/'clip.mp4').is_file():
            partes.append(f'<p><a href="../{folder.name}/clip.mp4">{html.escape(folder.name)}: p7 real</a></p><img width="270" src="../{folder.name}/019.png">')
    (out/'indice.html').write_text('\n'.join(partes),encoding='utf8')
    print(json.dumps(resultado,ensure_ascii=False))


if __name__=='__main__':main()
