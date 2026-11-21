"""Muestra del SVG real de p7 con marcas sintéticas de prueba, SIN locución.
No lee ni modifica proyectos. Fondo: un render local del motor, no la referencia.
"""
import argparse
import base64
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pasos import p7_callouts,medios


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fondo',required=True,type=Path);p.add_argument('--salida',required=True,type=Path)
    p.add_argument('--ancho',type=int,default=360);p.add_argument('--alto',type=int,default=640)
    p.add_argument('--fps',type=int,default=12)
    a=p.parse_args()
    if a.salida.exists():raise ValueError('elige una salida nueva')
    a.salida.mkdir(parents=True)
    from playwright.sync_api import sync_playwright
    escena=dict(id='prueba',narracion='The rail bends. ¿Por qué?',t_in=0,t_out=2,
        marcas=[[0,.3],[.3,.6],[.6,1],[1,1.4],[1.4,2]])
    svg,fichas=p7_callouts.capa_fija_de(escena,dict(subtitulo_perfil='ricksclips_v1'),salida=(a.ancho,a.alto))
    (a.salida/'subtitulos.svg').write_text(svg,encoding='utf-8')
    (a.salida/'marcas_de_prueba.json').write_text(json.dumps(dict(escena=escena,fichas=fichas,voz_generada=False)),encoding='utf-8')
    video=a.fondo.suffix.lower() in ('.mp4','.mov','.mkv','.webm')
    if video:
        fondos=a.salida/'fondos';fondos.mkdir()
        subprocess.run([medios.ffmpeg(),'-v','error','-i',str(a.fondo),'-t','2',
            '-vf',f'fps={a.fps},scale={a.ancho}:{a.alto}','-start_number','0',str(fondos/'%03d.png')],check=True)
        if len(list(fondos.glob('*.png')))!=a.fps*2:raise ValueError('el fondo no cubre dos segundos')
        bg=base64.b64encode((fondos/'000.png').read_bytes()).decode()
    else:bg=base64.b64encode(a.fondo.read_bytes()).decode()
    # Documento de prueba aislado, no HTML servido por el proxy del Estudio.
    html=f'<html><body style="margin:0;background:#17121f"><img style="position:absolute;width:{a.ancho}px;height:{a.alto}px" src="data:image/png;base64,{bg}"><div style="position:absolute">{svg}</div></body></html>'
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,executable_path=medios.edge())
        page=browser.new_page(viewport=dict(width=a.ancho,height=a.alto));page.set_content(html)
        page.wait_for_function('document.images[0].complete')
        page.evaluate('document.querySelector("svg").pauseAnimations()')
        for i in range(a.fps*2):
            if video:
                frame=base64.b64encode((fondos/f'{i:03d}.png').read_bytes()).decode()
                page.evaluate('(src)=>{document.images[0].src=src}', 'data:image/png;base64,'+frame)
                page.wait_for_function('document.images[0].complete')
                page.evaluate('document.images[0].decode()')
            page.evaluate('(t)=>document.querySelector("svg").setCurrentTime(t)',i/a.fps)
            page.screenshot(path=str(a.salida/f'{i:03d}.png'))
        browser.close()
    subprocess.run([medios.ffmpeg(),'-v','error','-y','-framerate',str(a.fps),'-i',str(a.salida/'%03d.png'),
        '-an','-c:v','libx264','-pix_fmt','yuv420p',str(a.salida/'clip.mp4')],check=True)
    from PIL import Image
    strip=Image.new('RGB',(a.ancho*5,a.alto))
    for i,t in enumerate((.08,.42,.75,1.17,1.67)):
        strip.paste(Image.open(a.salida/f'{round(t*a.fps):03d}.png'),(i*a.ancho,0))
    strip.save(a.salida/'subtitulos.png')
    print('Subtítulos reales de p7 renderizados; marcas de prueba, sin voz ni proveedores.')


if __name__=='__main__':main()
