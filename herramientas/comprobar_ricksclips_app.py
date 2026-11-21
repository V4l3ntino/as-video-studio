"""Inspección de la tarjeta real en navegador, solo lectura y sin proveedores.
Playwright debe instalarse en un entorno de herramientas, no en el servicio.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pasos import medios


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--servicio',default='http://127.0.0.1:8020')
    parser.add_argument('--salida',required=True,type=Path)
    parser.add_argument('--ancho',type=int,default=720)
    parser.add_argument('--alto',type=int,default=1280)
    parser.add_argument('--version',type=int,default=4)
    parser.add_argument('--duracion',type=float,default=18)
    parser.add_argument('--experimental',action='store_true')
    parser.add_argument('--clip-esperado',type=Path,help='comprueba bytes del vídeo servido contra la muestra publicada')
    args=parser.parse_args();args.salida.mkdir(parents=True,exist_ok=True)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=medios.edge())
        page=browser.new_page(viewport=dict(width=1180,height=920));errors=[];blocked=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        def route(r):
            u=urlsplit(r.request.url)
            if u.netloc!=urlsplit(args.servicio).netloc:
                blocked.append(u.path);r.abort();return
            if r.request.method not in ('GET','HEAD') and u.path!='/api/estimacion':
                blocked.append(r.request.method+' '+u.path);r.abort();return
            # Ni siquiera consultar catálogos de voces o salud/login de CLI.
            if any(x in u.path for x in ('/api/voces','/api/claude','/api/codex','/api/asistente','/api/claves')):
                blocked.append(u.path)
                if '/api/voces' in u.path:r.fulfill(json={'voces':[]})
                else:r.fulfill(json={})
                return
            r.continue_()
        page.route('**/*',route)
        page.goto(args.servicio)
        page.wait_for_function('APP.light.datos && !APP.light.cargando')
        page.evaluate("document.querySelector('#inicio')?.remove()")
        page.locator('#btn-estilos-ia').click()
        card=page.locator('.ficha-estilo').filter(has=page.get_by_text('RicksClips',exact=True))
        assert card.count()==1,'RicksClips debe tener una sola tarjeta'
        card.get_by_role('button',name='Ver análisis y recursos').click()
        detail=page.locator('.estilo-ia-detalle')
        video=detail.get_by_label('Muestra animada del motor del estilo')
        video.scroll_into_view_if_needed()
        page.wait_for_function("document.querySelector('.estilo-ia-muestra video')?.readyState >= 2")
        metadata=video.evaluate('(v)=>({src:v.currentSrc,w:v.videoWidth,h:v.videoHeight,duracion:v.duration})')
        assert metadata['w']==args.ancho and metadata['h']==args.alto and abs(metadata['duracion']-args.duracion)<.15,metadata
        if args.experimental:
            assert 'Vista previa experimental' in detail.locator('.estilo-ia-muestra').inner_text()
            assert 'Crear vídeo sigue usando el motor v5' in detail.locator('.estilo-ia-muestra').inner_text()
        else:
            texto=detail.locator('.estilo-ia-muestra').inner_text()
            assert 'Vista previa experimental' not in texto and 'Crear vídeo sigue usando el motor v5' not in texto,texto
        if args.clip_esperado:
            assert urlsplit(metadata['src']).netloc==urlsplit(args.servicio).netloc
            with urllib.request.urlopen(metadata['src'],timeout=60) as response:
                servido=hashlib.sha256(response.read()).hexdigest()
            with args.clip_esperado.open('rb') as f:esperado=hashlib.file_digest(f,'sha256').hexdigest()
            assert servido==esperado,'la tarjeta no sirve la muestra del motor publicado'
            metadata['sha256']=servido
        video.evaluate('(v)=>{v.currentTime=10;return v.play()}')
        page.wait_for_function("document.querySelector('.estilo-ia-muestra video').currentTime > 10.3")
        video.evaluate('(v)=>v.pause()')
        detail.locator('.estilo-ia-muestra').screenshot(path=str(args.salida/'tarjeta_muestra.png'))
        button=detail.get_by_role('button',name='Crear vídeo con este estilo',exact=True)
        assert button.is_enabled()
        button.click()
        page.wait_for_function("APP.light.video.vista === 'encargo'")
        selected=page.evaluate('estiloElegido().datos.estilo.espacio_ia')
        assert selected['version']==args.version,selected
        assert page.evaluate('encargoVideoLight().formato')=='vertical','el encargo nuevo debe partir de 9:16'
        page.screenshot(path=str(args.salida/'formulario.png'),full_page=True)
        assert not errors,errors
        resultado=dict(tarjeta_unica=True,muestra=metadata,crear_video_habilitado=True,
            formulario_espacio=selected,errores_js=errors,peticiones_proveedor_bloqueadas=blocked)
        (args.salida/'navegador.json').write_text(json.dumps(resultado,indent=2),encoding='utf-8')
        print(json.dumps(resultado,ensure_ascii=False));browser.close()


if __name__=='__main__':main()
