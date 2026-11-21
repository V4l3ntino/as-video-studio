"""Comparación A/B con mismo pedido, cámara, tiempo y resolución; sin proveedores.

La cocina Blender adapta el gesto al constraint de agarre. No se atribuye esa
diferencia de actuación únicamente al renderer ni se afirma pose idéntica.

Lee dos paquetes instalados sin escribir en ellos. Los PNG, parámetros y láminas
van a una carpeta nueva. La referencia se incluye solo en la lámina final.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import shutil

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--anterior',required=True,type=Path);p.add_argument('--nuevo',required=True,type=Path)
    p.add_argument('--referencias',required=True,type=Path);p.add_argument('--salida',required=True,type=Path)
    p.add_argument('--worker',action='store_true')
    a=p.parse_args()
    if a.worker:
        from pasos import espacio_estilo
        params=json.loads((a.salida/'encuadres.json').read_text(encoding='utf8'))
        for name,datos in params.items():
            pedido=dict(ancho=540,alto=960,fps=25,duracion=.04,parametros=datos)
            # También Blender debe pasar por el coordinador, no importarse en un
            # worker sin sesión. No modifica ejecutores ni fuentes históricas.
            codigo='import escena as motor\ndef pintar(p,t):return motor.pintar(p,1.3)\n'
            archivos=espacio_estilo.renderizar(a.nuevo,pedido,a.salida/(a.nuevo.name+'_'+name),
                lambda *a:None,codigo_escena=codigo)
            shutil.copyfile(archivos['poster'],a.salida/(a.nuevo.name+'_'+name+'.png'))
        return
    a.salida.mkdir(parents=True,exist_ok=False)
    sys.path[:0]=[str(a.nuevo/'dependencias'),str(a.nuevo/'herramientas')]
    from planos_revision import plano
    from PIL import Image,ImageDraw
    names=('general','medio','movil','cocina','cuenco','tormenta','calma','canon','torcida','puente','explosion')
    (a.salida/'encuadres.json').write_text(json.dumps({n:plano(n) for n in names},indent=2),encoding='utf8')
    for espacio in (a.anterior,a.nuevo):
        subprocess.run([sys.executable,'-B',__file__,'--worker','--anterior',str(a.anterior),'--nuevo',str(espacio),
            '--referencias',str(a.referencias),'--salida',str(a.salida)],check=True)
    refs=('ref_01_5.png','ref_04_33.png','ref_05_42.png','ref_09_99.64.png','ref_11_108.png','ref_12_117.5.png',
        'ref_12_117.5.png','ref_13_123.png','ref_16_177.4.png','ref_18_169.04.png','ref_17_185.png')
    for name,ref in zip(names,refs):
        sheet=Image.new('RGB',(1080,660),'#20202A');d=ImageDraw.Draw(sheet)
        for i,path in enumerate((a.referencias/ref,a.salida/(a.anterior.name+'_'+name+'.png'),a.salida/(a.nuevo.name+'_'+name+'.png'))):
            im=Image.open(path);im.thumbnail((360,640));sheet.paste(im,(i*360,20))
        for i,label in enumerate(('REFERENCIA',a.anterior.name+' - MISMO ENCUADRE',a.nuevo.name+' - MISMO ENCUADRE')):d.text((i*360+6,2),label,fill='white')
        sheet.save(a.salida/(name+'_comparacion.jpg'))


if __name__=='__main__':main()
