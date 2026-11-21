"""Reproducción real de las secuencias locales en Edge, sin proveedores.

No certifica actuación ni equivalencia artística: registra decodificación completa,
metadatos y errores. Las hojas temporales y la revisión visual son independientes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--renders',type=Path,required=True);p.add_argument('--salida',type=Path,required=True)
    a=p.parse_args();a.salida.mkdir(parents=True,exist_ok=False)
    for clave in ('ESTUDIO_SECRETOS','ESTUDIO_ESTADISTICAS','ESTUDIO_AJUSTES'):
        os.environ[clave]=str(a.salida/clave)
    renders=json.loads(a.renders.read_text(encoding='utf8'))
    from pasos import medios
    from playwright.sync_api import sync_playwright
    resultados=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=medios.edge())
        page=browser.new_page(viewport=dict(width=360,height=680));errores=[]
        page.on('pageerror',lambda error:errores.append(str(error)))
        page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(('file:','data:','about:')) else route.abort())
        # Página local, no contenido servido por el proxy ni frontend del Estudio.
        pagina=a.salida/'reproductor.html'
        pagina.write_text('<!doctype html><meta charset="utf-8"><style>video{width:360px;height:640px}</style><video muted controls></video>',encoding='utf8')
        page.goto(pagina.resolve().as_uri())
        for render in renders:
            path=Path(render['clip']).resolve()
            page.evaluate('(url)=>{const v=document.querySelector("video");v.src=url;v.load()}',path.as_uri())
            page.wait_for_function('document.querySelector("video").readyState>=2')
            dato=page.evaluate('''()=>new Promise((resolve,reject)=>{
                const v=document.querySelector('video');let callbacks=0,ultimo=0;
                const cuadro=(now,meta)=>{callbacks++;ultimo=meta.mediaTime;if(!v.ended)v.requestVideoFrameCallback(cuadro)};
                v.requestVideoFrameCallback(cuadro);
                v.onerror=()=>reject(new Error('video local no decodificable'));
                v.onended=()=>{const q=v.getVideoPlaybackQuality();resolve({fin:true,ancho:v.videoWidth,alto:v.videoHeight,
                    duracion:v.duration,tiempo:v.currentTime,callbacks,ultimo,total:q.totalVideoFrames,descartados:q.droppedVideoFrames})};
                v.play().catch(reject);
            })''')
            assert dato['fin'] and (dato['ancho'],dato['alto'])==(1080,1920),dato
            assert abs(dato['duracion']-render['duracion'])<.05 and dato['total']>=55,dato
            page.locator('video').screenshot(path=str(a.salida/(render['plano']+'.png')))
            with path.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
            resultados.append(dict(plano=render['plano'],clip=str(path),sha256_clip=sha,**dato))
        assert not errores,errores
        browser.close()
    (a.salida/'reproduccion.json').write_text(json.dumps(dict(secuencias=resultados,errores=errores,
        limite='Reproducción real; no verificación semántica automática ni calidad equivalente.'),indent=2),encoding='utf8')
    print('Reproducidas hasta el final:',len(resultados))


if __name__=='__main__':main()
