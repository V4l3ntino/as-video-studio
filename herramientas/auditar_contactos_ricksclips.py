"""Inspección reproducible del móvil con tres apariencias, sin proveedores.

Lee un paquete instalado. Mide el contacto en el plano del actor, NO contacto
3D ni fidelidad de actuación. Conserva láminas, medidas y SHA de las fuentes.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--espacio',required=True,type=Path)
    parser.add_argument('--salida',required=True,type=Path)
    args=parser.parse_args()
    args.salida.mkdir(parents=True,exist_ok=False)
    sys.path[:0]=[str(args.espacio/'dependencias'),str(args.espacio/'herramientas'),str(args.espacio/'motores')]
    import escena
    import personaje_base
    import movil
    from contactos import transformar
    from PIL import Image,ImageDraw
    original_rig=personaje_base.dibujar
    original_movil=movil.dibujar
    seen={}

    def dibujar_rig(*a,**kw):
        anchors=original_rig(*a,**kw)
        seen['mano']=anchors['mano_d']
        return anchors

    def dibujar_movil(im,state,*a,**kw):
        seen['movil']=dict(state)
        return original_movil(im,state,*a,**kw)

    apariencias=({},dict(altura=1.12,cuerpo=1.2,cabeza=.9,pelo='largo',ropa='vestido',gafas=True),
        dict(pelo='trenzas',ropa='camisa',colores={'piel':'#A86F4E','ropa':'#7457A0'}))
    records=[]
    personaje_base.dibujar=dibujar_rig
    movil.dibujar=dibujar_movil
    try:
        for variant,appearance in enumerate(apariencias):
            sheet=Image.new('RGB',(400*8,580),'#D1C9BC')
            draw=ImageDraw.Draw(sheet)
            for col,t in enumerate((.3,.6,.88,.94,.96,1.2,1.6,2.1)):
                im=escena.sprite(t,dict(accion='atrapar',apariencia=appearance,sombrero='oeste'))
                sheet.paste(im,(col*400,20),im)
                draw.text((col*400+10,2),str(t)+' s',fill='black')
                if t>=.95:
                    p=seen['movil']
                    grip=transformar((-14,8),(p['x'],p['y']),p['ang'])
                    error=math.dist(grip,seen['mano'])
                    assert error<1e-8,'el objeto se separa de la mano resuelta'
                    records.append(dict(variante=variant,t=t,error_px=error,piel=personaje_base.COLORES['piel']))
            sheet.save(args.salida/f'variante_{variant}.jpg')
        fuentes={p.relative_to(args.espacio).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path(escena.__file__),Path(personaje_base.__file__),Path(movil.__file__),args.espacio/'herramientas/contactos.py')}
        result=dict(medidas=records,fuentes=fuentes,apariencias=apariencias,
            alcance='Contacto sostenido en plano articulado; no constraint 3D ni certificación artística')
        (args.salida/'contactos.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        print('Contactos sostenidos comprobados:',len(records))
    finally:
        personaje_base.dibujar=original_rig
        movil.dibujar=original_movil


if __name__=='__main__':main()
