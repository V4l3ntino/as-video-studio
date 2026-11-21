"""Comprueba y, con --aplicar, guarda una corrección local del gato pagado.

No prepara el reparto ni escenas, no publica el estilo, no consulta proveedores.
La entrega y las tres dependencias originales permanecen intactas.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nucleo.proyecto import Proyecto, leer_json, escribir_json
from pasos import recursos_animacion as recursos, espacio_estilo, animacion_nativa

CLAVE='917e3de2a4a65098358d8b7bfa7c14bbbb2ff1e512b2c5edbbc5037c09ca2e54'
BASE='a4ac027f63320b692d16a617420b7a7010ce9f13243f443a35d4e53c352246d7'


def entrega(original):
    return dict(formato='geometria/1',nombre=original['nombre'],concepto=original['concepto'],
        codigo_extra=recursos.BASE.with_name('geometria_felina.py').read_text(encoding='utf-8'),
        interfaz='''Gato cuadrúpedo plano; dibujar(lienzo,estado,contexto), pose(estado,contexto=None).
estado_base(): x=320,y=290 píxeles (suelo bajo centro), esc=1 px/unidad, dir=+1/-1.
Ángulos en grados: torso inclina columna; rotacion gira TODO el gato sobre x,y;
cabeza_inc inclina cabeza; cola=-145+valor orienta cola, cola_curva=25 la curva.
cadera_dy=0 unidades: baja el cuerpo. hombro_i/d y codo_i/d articulan patas
DELANTERAS (0 cuelga, positivo hacia delante). muslo_i/d y rodilla_i/d articulan
TRASERAS. Cada pata tiene FK de dos huesos e IK por objetivo en px: ik={mano_i,
mano_d,pie_i,pie_d:(x,y[,peso])}; peso 0..1. Mano significa zarpa delantera.
mirada=[x,y] -1..1; expresion={ojos:0..1,abierta:0..1}; pelaje,rayas,hocico,iris
son #RRGGBB independientes por estado. Sin ropa ni anatomía humana subyacente.
Devuelve anclas px cabeza,ojo_i/d,radio_cabeza,hombro_i/d,codo_i/d,mano_i/d,
cadera_i/d,rodilla_i/d,pie_i/d,pelvis,hombro,pecho,suelo,cola_base,cola_punta,
cola_puntos,caja. caminar(t,vel=1,amp=1), sentarse(u), saludar(t,freq=2.5) son
ajustes ADITIVOS; combinar e interpolar heredados de la base. Las escenas pueden
programar nuevas actuaciones, caída/rotación, extensión, flexión y aseo usando
estos controles libres; no son poses cerradas. No hay cuerpo/cola 3D.''',
        muestra=[dict(x=340,y=295,esc=1,hombro_d=0,codo_d=8,muslo_i=-12,
            rodilla_i=26,cabeza_inc=0,cola=0),
            dict(x=340,y=295,esc=1,hombro_d=95,codo_d=55,muslo_i=-35,
                rodilla_i=70,cabeza_inc=-18,cola=40)])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('proyecto',type=Path);p.add_argument('--salida',type=Path,required=True)
    p.add_argument('--aplicar',action='store_true');a=p.parse_args()
    proyecto=Proyecto(str(a.proyecto.resolve()))
    ruta=recursos.raiz(proyecto)/'personajes'/CLAVE
    original=leer_json(str(ruta.with_suffix('.entrega.json')),estricto=True)
    config=leer_json(str(ruta.with_suffix('.apariencia.json')),estricto=True)
    refs=leer_json(str(ruta.with_suffix('.base.json')),estricto=True)
    if refs[config['base']]['huella']!=BASE:
        raise ValueError('esta corrección solo está comprobada con la base plana fijada')
    vigilados=[ruta.with_suffix('.entrega.json'),ruta.with_suffix('.apariencia.json'),ruta.with_suffix('.base.json')]
    vigilados += list((ruta.parent/(CLAVE+'.consulta')).rglob('salida.json'))
    vigilados += [Path(proyecto.raiz)/r['ruta'] for r in refs.values()]
    vigilados += [Path(proyecto.raiz)/'estado.json']
    vigilados += list((Path(proyecto.raiz)/'pasos'/'guion').rglob('guion.json'))
    def hashes():return {str(r):hashlib.sha256(r.read_bytes()).hexdigest() for r in vigilados}
    antes=hashes();nuevo=entrega(original)
    base=recursos.cargar(proyecto,refs[config['base']])
    asset=recursos.compilar_apariencia(nuevo,base,config,refs)
    # Solo crea un asset por SHA, nunca publica un puntero de personaje sin pasar
    # el flujo normal. La corrección basta para que ese flujo reutilice la entrega.
    ref=recursos.guardar(proyecto,base['estilo'],asset)
    espacio=Path(proyecto.raiz)/'estilo_ia'/'paquetes'/base['estilo']
    def prohibido(*args,**kwargs):raise AssertionError('Proveedor vetado en recuperación local')
    with patch.object(animacion_nativa,'consultar',side_effect=prohibido),patch.object(espacio_estilo,'dirigir',side_effect=prohibido):
        recursos.comprobar_personaje(proyecto,espacio,ref,a.salida,lambda *args:None)
        codigo='''from PIL import Image
import gato,otro
def pintar(pedido,t):
    im=Image.new('RGB',(960,540),'#263447')
    e=gato.estado_base();e.update(x=300,y=400,esc=1.3)
    gato.dibujar(im,gato.combinar(e,gato.caminar(t)),dict(t=t))
    f=otro.estado_base();f.update(x=720,y=400,esc=1.1,dir=-1,rotacion=35*t,
        pelaje='#B8BEC7',rayas='#505765',iris='#83BADD')
    f=otro.combinar(f,otro.saludar(t));otro.dibujar(im,f,dict(t=t))
    assert gato.rig is not otro.rig
    assert gato.rig.COLORES is not otro.rig.COLORES
    assert e['pelaje']=='#EE9748'
    for direccion in (-1,1):
        estado=dict(e,dir=direccion,rotacion=65)
        p=gato.pose(estado)
        for punta in ('mano_i','mano_d','pie_i','pie_d'):
            target=(p[punta][0]+2,p[punta][1]-3)
            q=gato.pose(dict(estado,ik={punta:target}))
            assert sum((q[punta][i]-target[i])**2 for i in (0,1))<.01, punta
    p=gato.pose(e)
    for control,punto in (('hombro_i','mano_i'),('hombro_d','mano_d'),
        ('muslo_i','pie_i'),('muslo_d','pie_d'),('codo_i','mano_i'),
        ('codo_d','mano_d'),('rodilla_i','pie_i'),('rodilla_d','pie_d'),
        ('cabeza_inc','ojo_i'),('cola','cola_punta')):
        assert gato.pose(dict(e,**{control:45}))[punto]!=p[punto],control
    assert gato.rig.originales['dibujar'] is not gato.rig.dibujar
    return im
'''
        archivos=espacio_estilo.renderizar(espacio,dict(ancho=960,alto=540,fps=12,duracion=2,
            escena={},parametros={}),a.salida/'pareja',lambda *args:None,codigo_escena=codigo,
            herramientas_escena=recursos.fuentes(proyecto,{'gato':ref,'otro':ref}))
        animacion_nativa.comprobar_movimiento(archivos['clip'],a.salida/'pareja',12)
    # Recuperación del cierre portable sin catálogo global ni paquete modificado.
    portable=Proyecto.crear(str(a.salida/'portable'),'Dependencias del gato')
    def copiar(r):
        dato=recursos.cargar(proyecto,r)
        for dep in (dato['asset'].get('dependencias') or {}).values():copiar(dep)
        assert recursos.guardar(portable,dato['estilo'],dato['asset'])==r
    copiar(ref)
    assert recursos.fuentes(portable,{'gato':ref})==recursos.fuentes(proyecto,{'gato':ref})
    if hashes()!=antes:raise AssertionError('Se modificó una entrega o dependencia original')
    correccion=dict(huella_original=espacio_estilo.huella(original),entrega=nuevo,
        motivo='Recuperación local explícita: gato cuadrúpedo atigrado, sin apariencia humana; FK/IK originales reutilizados. Sin proveedores ni cambios en guion/voz/tiempos.')
    destino=ruta.with_suffix('.correccion.json')
    if a.aplicar:
        if destino.exists() and leer_json(str(destino),estricto=True)!=correccion:
            raise ValueError('Ya existe otra corrección: no se sobrescribe')
        escribir_json(str(destino),correccion)
    informe=dict(asset=ref,originales_intactos=antes,correccion_guardada=a.aplicar,
        correccion=str(destino),muestra=archivos,calidad_artistica_verificada=False)
    escribir_json(str(a.salida/'recuperacion.json'),informe)
    print(json.dumps(informe,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
