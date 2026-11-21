"""Congela la tarjeta real en un proyecto temporal y renderiza código nativo.
Sin analista, constructor, dirección ni proveedores. No usa proyectos existentes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import shutil
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--preset',required=True)
    p.add_argument('--trabajo',type=Path,help='raíz NUEVA y corta para proyectos/copias; evita el límite de rutas DLL en Windows')
    p.add_argument('--salida',required=True,type=Path)
    p.add_argument('--paquete-local',type=Path,help='prepara/publica primero en una copia aislada del estilo y preset')
    p.add_argument('--estilo',type=Path,help='estilo de origen, solo lectura, para --paquete-local')
    p.add_argument('--preparacion-comprobada',type=Path,help='recibo previo de esta preparación aislada; no repite preparar')
    p.add_argument('--ancho',type=int,default=720);p.add_argument('--alto',type=int,default=1280)
    p.add_argument('--fps',type=int,default=25);p.add_argument('--duracion',type=float,default=2)
    a=p.parse_args()
    if a.paquete_local and not a.estilo:p.error('--paquete-local necesita --estilo')
    if a.salida.exists():raise ValueError('la salida debe ser nueva')
    a.salida.mkdir(parents=True)
    trabajo=a.trabajo or a.salida
    if a.trabajo:a.trabajo.mkdir(parents=True,exist_ok=False)
    for clave in ('ESTUDIO_SECRETOS','ESTUDIO_ESTADISTICAS','ESTUDIO_AJUSTES','ESTUDIO_RECURSOS_ANIMACION'):
        os.environ[clave]=str(a.salida/clave)
    from nucleo.proyecto import Proyecto,leer_json,escribir_json
    from pasos import estilos_ia,presets_canal,espacio_estilo,recursos_animacion,animacion_nativa
    preparacion=None
    if a.preparacion_comprobada:
        preparacion=leer_json(str(a.preparacion_comprobada),estricto=True)['preparacion_real']
    if a.paquete_local:
        # Copias de entradas reales, no estados inventados para eludir preparar.
        original=Path(presets_canal.carpeta_de(a.preset))
        banco=trabajo/'banco';shutil.copytree(original,banco/a.preset,
            ignore=shutil.ignore_patterns('dependencias','cache','trabajo','__pycache__'))
        fichero=trabajo/'presets.json';shutil.copyfile(presets_canal.FICHERO,fichero)
        presets_canal.FICHERO=str(fichero);presets_canal.BANCO=str(banco)
        local=trabajo/'estilos'/a.estilo.name;local.mkdir(parents=True)
        os.environ['ESTUDIO_ESTILOS_IA']=str(local.parent)
        shutil.copyfile(a.estilo/'estilo.json',local/'estilo.json')
        shutil.copytree(a.estilo/'referencias',local/'referencias')
        for ruta in ('analisis_visual/informe_actual.json','transcripcion/resultado.json'):
            if (a.estilo/ruta).is_file():
                (local/ruta).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(a.estilo/ruta,local/ruta)
        paquete=espacio_estilo.validar(leer_json(str(a.paquete_local),estricto=True),exigir_biblioteca=True)
        ultimo=['']
        def avance(v,m):
            if m!=ultimo[0]:print(m,flush=True);ultimo[0]=m
        with patch.object(espacio_estilo,'consultar_constructor',side_effect=AssertionError('proveedores prohibidos')):
            preparacion=estilos_ia.preparar(avance,str(local.parent),local.name,presets_canal,
                paquete_local=paquete,muestra_local=dict(ancho=192,alto=320,fps=4,duracion=18))
    ficha=presets_canal.leer(a.preset);cambios=presets_canal.cambios_para(ficha)
    assert cambios['callouts']['subtitulo_perfil']=='ricksclips_v1'
    assert cambios['brief']['formato']=='vertical'
    proyecto=Proyecto.crear(str(trabajo/'proyectos'),'Prueba local RicksClips')
    estilos_ia.congelar(presets_canal,ficha,proyecto)
    marca=ficha['datos']['estilo']['espacio_ia']
    if preparacion is not None:assert preparacion['espacio']==marca,'la preparación no corresponde al preset'
    espacio=Path(proyecto.ruta('estilo_ia','paquetes',marca['huella']))
    espacio_estilo.verificar(espacio,marca['huella'])
    base=leer_json(str(recursos_animacion.raiz(proyecto)/'rig_base.json'),estricto=True)
    herramientas=recursos_animacion.fuentes(proyecto,{'actor_congelado':base})
    codigo='''from PIL import Image
from espacio3d import Renderer
from decorados3d import escena
import actor_congelado as actor
R=None
def preparar(pedido):
    global R
    R=Renderer(pedido['ancho'],pedido['alto'])
    actor.aplicar_apariencia(dict(pelo='trenzas',ropa='camisa',gafas=True,colores={'ropa':'#557CB0'}))
def pintar(pedido,t):
    m,cam,amb=escena('taberna',t)
    cam.update(eye=(.7,2.3,5),target=(0,1.2,0),fov=49)
    im=Image.new('RGBA',(400,560))
    estado=actor.estado_base()
    estado.update(actor.caminar(t));estado.update(x=140+60*t,y=530,esc=1.45,sombra=0)
    actor.dibujar(im,estado,dict(t=t,ancho=400,alto=560,duracion=2))
    return R.render(m,cam,[(im,(0,-2.7*30/560,0),2.7)],amb)
'''
    animacion_nativa.validar_codigo(codigo,['espacio3d','decorados3d',*herramientas])
    pedido=dict(ancho=a.ancho,alto=a.alto,fps=a.fps,duracion=a.duracion,escena={},parametros={})
    files=espacio_estilo.renderizar(espacio,pedido,a.salida/'render_nativo',lambda *args:None,
        codigo_escena=codigo,herramientas_escena=herramientas)
    control=animacion_nativa.comprobar_movimiento(files['clip'],a.salida/'render_nativo',a.fps)
    # Fuente LOCAL explícita en un proyecto sintético; no finge una respuesta
    # pagada ni una fase completada. P6 debe producir sus recibos mediante render.
    from pasos import p6_assets
    escena_local=dict(id='PRUEBA_LOCAL',narracion='Local Blender render.',prompt='Actor articulado caminando en taberna.',
        t_in=0,t_out=a.duracion)
    plan=dict(animacion_nativa=True,estilo=cambios['assets']['estilo'],escenas=[escena_local],
        resolucion=[a.ancho,a.alto],fps=a.fps)
    params=dict(estilo=cambios['assets']['estilo'])
    from nucleo.estado import Estado
    estado=Estado(proyecto);estado.set_params('assets',params)
    firma=espacio_estilo.huella([animacion_nativa.VERSION,marca,escena_local,plan['resolucion'],a.fps,None])
    respuesta=dict(codigo=codigo,acciones=[dict(tipo='personaje',objetivo='actor_local',accion='Camina con el rig congelado',
        claves=[dict(t=0,estado={'x':140}),dict(t=a.duracion,estado={'x':140+60*a.duracion})])],
        edicion='Plano de prueba local con actuación y cámara fija.')
    escribir_json(proyecto.ruta('estilo_ia','escenas_nativas',escena_local['id'],firma,'fuente.json'),
        dict(respuesta=respuesta,proveedor='local',formato='programa-recursos/1',
            recursos_disponibles={'actor_congelado':base},personajes_recursos={}))
    import copy
    with patch.object(p6_assets,'planificar',side_effect=lambda *a,**k:copy.deepcopy(plan)),\
            patch.object(p6_assets,'_ejecutar_base',side_effect=AssertionError('imágenes prohibidas')),\
            patch.object(animacion_nativa,'consultar',side_effect=AssertionError('proveedores prohibidos')):
        p6=p6_assets.ejecutar(proyecto,params)
        with patch.object(espacio_estilo,'renderizar',side_effect=AssertionError('la recuperación no debe renderizar otra vez')):
            p6_assets.ejecutar(proyecto,params)
    # Mismo cierre de build que usa la aplicación, solo tras producir los clips.
    # No se marcan guion/voz/preparación como hechos ni se inventan firmas.
    version_assets=estado.completar('assets',p6['salidas'],p6['unidades'])
    visible=espacio_estilo.aplicar_recursos(proyecto,copy.deepcopy(plan))['escenas'][0]
    assert visible.get('animacion_estilo'),'P6 no publicó el clip nativo'
    files=dict(files,clip=visible['animacion_estilo']['clip'])
    from pasos import p7_callouts,p8_render
    escena=dict(id='PRUEBA_LOCAL',narracion='Local Blender render.',t_in=0,t_out=a.duracion,
        marcas=[[0,a.duracion/3],[a.duracion/3,a.duracion*2/3],[a.duracion*2/3,a.duracion]],
        animacion_estilo=dict(clip=files['clip']))
    svg,fichas=p7_callouts.capa_fija_de(escena,dict(subtitulo_perfil='ricksclips_v1'),salida=(a.ancho,a.alto))
    fuente=p8_render._fuente_para_enlace(escena,{},str(a.salida),{},proyecto,True,salida=(a.ancho,a.alto))
    assert fuente['video']==files['clip']
    tarea=dict(fuente,id=escena['id'],fps=a.fps,frames=round(a.duracion*a.fps),carpeta=str(a.salida/'montaje_frames'),
        hyper=files['poster'],capa_fija=svg,resolucion=[a.ancho,a.alto],calidad='media',
        clip=str(a.salida/'montado.mp4'),ultimo=str(a.salida/'ultimo.png'),conservar_frames=True)
    navegador=p8_render.Navegador(a.ancho,a.alto)
    try:montaje=p8_render.renderizar_plano(tarea,navegador)
    finally:navegador.cerrar()
    escribir_json(str(a.salida/'marcas_de_prueba.json'),dict(escena=escena,fichas=fichas,voz_generada=False))
    copia=proyecto.duplicar(str(trabajo/'copias'),'Copia portable')
    espacio_copia=Path(copia.ruta('estilo_ia','paquetes',marca['huella']))
    espacio_estilo.verificar(espacio_copia,marca['huella'])
    for nombre in ('dependencias','cache','trabajo'):assert not (espacio_copia/nombre).exists(),nombre
    assert recursos_animacion.cargar(copia,base)==recursos_animacion.cargar(proyecto,base)
    assert copia.version_activa('assets')==version_assets
    portable=espacio_estilo.aplicar_recursos(copia,copy.deepcopy(plan))['escenas'][0]
    clip_portable=Path(portable['animacion_estilo']['clip'])
    assert clip_portable.is_relative_to(Path(copia.raiz)) and clip_portable.is_file()
    assert hashlib.sha256(clip_portable.read_bytes()).hexdigest()==hashlib.sha256(Path(files['clip']).read_bytes()).hexdigest()
    # Reconstrucción independiente desde requisitos, no copiar binarios del original.
    repetido=espacio_estilo.renderizar(espacio_copia,pedido,a.salida/'render_duplicado',lambda *args:None,
        codigo_escena=codigo,herramientas_escena=recursos_animacion.fuentes(copia,{'actor_congelado':base}))
    from PIL import Image,ImageChops
    with Image.open(files['poster']) as im,Image.open(repetido['poster']) as otro:
        assert ImageChops.difference(im.convert('RGB'),otro.convert('RGB')).getbbox() is None
    espacio_estilo.verificar(espacio_copia,marca['huella'])
    resultado=dict(espacio=marca,congelar=True,render_nativo=files,movimiento=control,
        perfil_subtitulos=cambios['callouts']['subtitulo_perfil'],duplicado_portable=True,
        proveedores_consultados=0,proyecto=proyecto.raiz,preparacion_real=preparacion,
        render_duplicado=repetido,poster_duplicado_identico=True,reconstruccion_dependencias=True)
    resultado.update(montaje_p8_real=montaje,subtitulos_p7_reales=True,
        clip_montado=tarea['clip'],marcas_sinteticas=True,voz_generada=False)
    resultado.update(p6_nativo_real=True,recuperacion_p6_sin_regenerar=True,clips_portables=True,
        version_assets=version_assets,clip_portable=str(clip_portable))
    resultado['fuentes']={p.relative_to(espacio).as_posix():hashlib.sha256(p.read_text(encoding='utf8').encode('utf8')).hexdigest()
        for carpeta in ('motores','herramientas') for p in (espacio/carpeta).glob('*.py')}
    if (espacio/'requisitos/blender.json').is_file():
        resultado['fuentes']['ejecutor.py']=hashlib.sha256((espacio/'ejecutor.py').read_text(encoding='utf8').encode('utf8')).hexdigest()
    escribir_json(str(a.salida/'integracion.json'),resultado)
    print(json.dumps(resultado,ensure_ascii=False))


if __name__=='__main__':main()
