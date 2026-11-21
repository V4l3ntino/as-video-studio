"""Construcción explícita local de RicksClips, sin proveedores.

python herramientas/preparar_ricksclips.py --estilo <carpeta> --borrador <json>
Añadir --publicar ejecuta instalación, muestras, biblioteca y publicación reales.
El servicio debe estar libre de trabajos; no se reinicia ni se tocan proyectos.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import urllib.request
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nucleo.proyecto import escribir_json
from pasos import espacio_estilo,estilos_ia,presets_canal

FUENTES=Path(__file__).resolve().parents[1]/'motores'/'ricksclips'


def huellas_fuentes(paquete):
    fuentes={'motores/escena.py':paquete['codigo'],**{k:v for k,v in paquete['archivos'].items() if k.endswith('.py')}}
    if paquete.get('blender'):
        fuentes['motores/blender_cliente_estudio.py']=espacio_estilo.CLIENTE_BLENDER.read_text(encoding='utf8')
        fuentes['ejecutor.py']=espacio_estilo.EJECUTOR.read_text(encoding='utf8')
    return {k:hashlib.sha256(v.encode('utf8')).hexdigest() for k,v in fuentes.items()}


def compilar_rig(codigo):
    """Edición explícita del rig heredado SOLO en el paquete nuevo; contratos iguales."""
    cambios={
        'anchoB = 11.0 * k * math.sqrt(cu)':'anchoB = 2.7 * k * math.sqrt(cu)',
        'q = 9.5 * k':'q = 4.0 * k',
        "_miembro(dr, pts, 8.5 * k, col['pantalon'], ow * 0.75)":"_miembro(dr, pts, 2.2 * k, col['pantalon'], ow * 0.30)",
        '13 * k + 2 * ow':'4 * k + ow * .7',
        "13 * k, col['zapatos']":"4 * k, col['zapatos']",
        '    out = dict((kk, v) for kk, v in P.items() if isinstance(v, tuple))':
            '    _vestir(lienzo, estado, P, COLORES, ROPA)\n    out = dict((kk, v) for kk, v in P.items() if isinstance(v, tuple))',
    }
    for antes,despues in cambios.items():
        if codigo.count(antes)!=1:raise ValueError('Rig heredado distinto: '+antes)
        codigo=codigo.replace(antes,despues)
    # Assets de biblioteca autocontenidos: no añadir dependencia mutable al rig.
    ropa=(FUENTES/'vestuario.py').read_text(encoding='utf8')
    ropa=ropa.replace('def dibujar(im,e,p,colores,ropa):','def _vestir(im,e,p,colores,ropa):')
    return codigo+'\n\nVESTUARIO_VERSION=1\n'+ropa


def construir(estilo, evidencias=None, backend='opengl'):
    if backend not in ('opengl','blender'):raise ValueError('backend no válido')
    estilo=Path(estilo)
    ficha=json.loads((estilo/'estilo.json').read_text(encoding='utf-8'))
    anterior=estilo/'versiones'/'v1'
    base=json.loads((anterior/'paquete.json').read_text(encoding='utf-8'))
    espacio_estilo.verificar(anterior,json.loads((anterior/'espacio.json').read_text(encoding='utf-8'))['huella'])
    archivos=dict(base['archivos'])
    archivos['herramientas/personaje_base.py']=compilar_rig(archivos['herramientas/personaje_base.py'])
    base['biblioteca']['recursos']['personaje_base']['interfaz']+=' Vestuario v4 en estado: sombrero oeste|chef|gorra|chistera, bigote bool y cinturon bool opcionales. Siguen anclas e inclinación de cabeza/torso; no cambian identidad global.'
    for p in sorted(FUENTES.glob('*.py')):
        if p.name!='escena.py':archivos['herramientas/'+p.name]=p.read_text(encoding='utf-8')
    informe=json.loads((estilo/'analisis_visual'/'informe_actual.json').read_text(encoding='utf-8'))
    evidencia=[w for lote in informe['lotes'] for w in lote['ventanas']]
    archivos['recursos/observaciones_existentes.json']=json.dumps(evidencia,ensure_ascii=False,indent=2)
    archivos['recursos/analisis_existente.json']=json.dumps(ficha['analisis'],ensure_ascii=False,indent=2)
    archivos['recursos/LEEME.txt']=(FUENTES/'LEEME.txt').read_text(encoding='utf-8')
    archivos['recursos/revision_visual.txt']=(FUENTES/'REVISION.txt').read_text(encoding='utf-8')
    integracion={}
    for ruta in ('pasos/p3_guion.py','pasos/voz_cartesia.py','pasos/p4_voz.py',
            'pasos/subtitulos.py','pasos/p7_callouts.py','pasos/p8_render.py','pasos/sonido.py'):
        p=FUENTES.parents[1]/ruta
        if p.is_file():integracion[ruta]=hashlib.sha256(p.read_bytes()).hexdigest()
    archivos['recursos/integracion_estudio.json']=json.dumps(dict(archivos=integracion,
        voz='Proveedor de voz existente; NO se ha sintetizado ni certificado una voz nueva.',
        musica='No observada por el analista. El montaje del Estudio excluye música por política; no se activa ni se promete.',
        subtitulos='Los añade el Estudio con marcas de voz. El motor no escribe narración en sus fotogramas.',
        formato='Renderer con aspect ratio real; muestra de tarjeta 720x1280/25fps y revisión separada 1080x1920/25fps. El formato de cada vídeo lo decide su encargo.',
        fidelidad='Calidad equivalente NO alcanzada; escenografía y recursos originales, no copia píxel a píxel.'),ensure_ascii=False,indent=2)
    fuentes=['motores/escena.py','herramientas/espacio3d.py','herramientas/decorados3d.py',
        'herramientas/utileria3d.py','herramientas/realizacion.py','recursos/LEEME.txt']
    notas={
        'guia_visual':'Renderer OpenGL: perspectiva, z-buffer, shadow map PCF y luz direccional/puntual. Madera, arenisca, acero y agua diferenciados; seis escenarios enriquecidos con carpintería/aparejo/perfiles/ballasto. Rig articulado heredado con miembros finos, vestuario anclado y apariencias independientes, compilado autocontenido. DOF por z; no alcanza riqueza pictórica equivalente.',
        'area:visual':'Arquitectura, cañón, barco, tren, vías y puente con profundidad; rig/ropa/apariencias originales v1 y accesorios. Render real, no fondos Pillow ni imágenes generadas.',
        'area:animacion':'Cámara keyframes en metros/FOV, dolly, tilt, aéreo; rig caminar/sentarse/saludar, IK de captura, expresiones y parpadeo. Malla de olas/vías animadas, aceite, partículas y humo por raymarch integrado contra z-buffer.',
        'area:montaje':'realizacion.transicion acepta dos fotogramas de escenas: fundido, whip y pupila/mirilla. Reloj/edición de planos permanecen en el Estudio; no se cambian tiempos de proyectos.',
        'area:tipografia':'Perfil explícito ricksclips_v1 en p7_callouts.capa_ricksclips: una palabra por marca, blanco/Arial Bold con contorno negro grueso, sin caja, a 70-73.6% de altura y fuera de cámara. Se propaga por rotulos.subtitulo_perfil solo a nuevos vídeos. No se afirma tener la fuente exacta de la referencia.',
        'recurso:0':'personaje_base compilado por compilar_rig sobre v1 preservada: apariencia/1, mismas anclas/FK/IK y movimientos, miembros más finos, botones/costuras/cinturón y sombreros ligados a cabeza/torso; sprite RGBA con profundidad y sombra. vestuario.py es fuente de la extensión autocontenida, no dependencia compartida mutable.',
        'recurso:1':'decorados3d.escena: oeste, taberna, cocina, mar, canon, puente. Geometría original, luces y sombras GPU. Sin generación externa.',
        'recurso:2':'p7_callouts.capa_ricksclips y subtitulos.de_escena(palabra_a_palabra=True), fuera del motor, con marcas de voz reales. Perfil explícito con contorno negro y escalonado limitado por grupos. No se incrusta una transcripción ficticia en la muestra muda; no se afirma posición exacta de cada plano de la referencia.',
        'recurso:3':'Cámara real 3D y realización local con FOV/eye/target/apertura y claves interpoladas. Whip/desenfoque solo como postproceso explícito, no como prueba de 3D.',
        'recurso:4':'realizacion.transicion implementa pupila/mirilla circular, whip y fundido; el código de escena puede enlazar sus fotogramas sin alterar voz.',
        'recurso:5':'Partículas originales reutilizadas: chispas/sudor/velocidad/aura/lluvia. Volumen procedural del motor para humo/hongo, sin simularlo con discos desenfocados.',
        'recurso:6':'Integración con locución existente del Estudio: guía editorial en inglés conservada, marcas reales. Este paquete NO genera, instala ni verifica una voz ni afirma timbre equivalente; requiere voz/sesión del usuario al crear vídeos con locución.',
        'recurso:7':'realizacion.audio sintetiza SFX originales whoosh/disparo/olas/tren/explosión y devuelve WAV separado. Música no verificada en referencia y excluida del montaje por política actual; NO se declara reproducida.',
        'recurso:8':'PIL RGB a resolución pedida -> ejecutor FFmpeg H264; WAV separado hacia pista Sonidos. Montaje/voz del Estudio, nunca audio duplicado en clip. Aspect ratio nativo sin barras obligatorias.',
        'recurso:9':'Guía de guion íntegra preservada al publicar por estilos_ia.publicar_espacio. Programas de escena libres con biblioteca; la ejecución de guiones futuros no forma parte de estas comprobaciones sin proveedores.',
    }
    requisitos=espacio_estilo.requisitos_constructor(ficha['analisis'])
    cumplimiento=dict(version=1,alcance='Capacidades locales e integración; NO certificación de fidelidad equivalente.',
        limitaciones='Ver recursos/revision_visual.txt y comprobaciones/mejora_v5: riqueza pictórica no equivalente; agua/tren todavía simplificados; fuente no identificada; voz/música no generadas.',
        requisitos=[dict(id=r['id'],estado='implementado',
        implementacion=notas[r['id']],archivos=fuentes+(['herramientas/personaje_base.py'] if r['id'] in ('recurso:0','area:visual') else [])+
        (['recursos/integracion_estudio.json'] if r['id'] in ('area:tipografia','recurso:2','recurso:6','recurso:7','recurso:8','recurso:9') else [])) for r in requisitos])
    cumplimiento['revision_visual']={
        'implementado_comprobado_visualmente':['carpintería y utilería de seis escenarios','casco curvo y aparejo','cuenco con cavidad','vías con perfil y balasto','miembros finos, vestuario anclado y sombreros','encuadres general/medio/rostro','paredes continuas en vez de torres','cabina trasera abierta y techo abovedado','móvil ligado a mano real tras IK'],
        'implementado_no_equivalente':['materiales procedurales sin texturas pictóricas pintadas','agua y cresta sin simulación de fluidos','humo volumétrico procedural','paredes con relieve sin acabado pictórico equivalente','locomotora aún estilizada y simplificada','profundidad de campo y actuación facial heredadas'],
        'pendiente':['acabado pictórico equivalente y mayor variedad arquitectónica','constraint espacial general de mano/asa; el agarre IK de muestra es aproximado','identificación de fuente original','equivalencia temporal fina de gestos y transiciones'],
        'evidencias':'comprobaciones/mejora_v5 y el histórico mejora_v4: consultar informe para distinguir inspección real de render técnico; referencias solo para comparar, nunca entrada del motor.'}
    archivos['recursos/cumplimiento.json']=json.dumps(cumplimiento,ensure_ascii=False,indent=2)
    archivos['herramientas/LEEME.txt']+='\nVersión híbrida: usar espacio3d, decorados3d, utileria3d, realizacion. No utilizar auxiliar.fondo para sustituir escenarios 3D.'
    paquete=dict(codigo=(FUENTES/'escena.py').read_text(encoding='utf-8'),
        archivos=archivos,biblioteca=base['biblioteca'],cumplimiento=cumplimiento,descargas=[],
        dependencias=['pillow==12.3.0','numpy==2.5.2','moderngl==5.12.0','glcontext==3.0.0'],
        parametros=dict(escenario='galeria',subtitulo_perfil='ricksclips_v1',formato_video='vertical'),direccion=archivos['recursos/LEEME.txt'])
    if backend=='blender':
        from pasos import runtime_blender
        for origen,nombre in [('servidor.py','rc_blender_servidor.py'),
                ('renderizar.py','rc_blender_render.py'),('artesania.py','rc_blender_artesania.py')]:
            archivos['herramientas/'+nombre]=(FUENTES/'blender'/origen).read_text(encoding='utf8')
        archivos['herramientas/espacio3d.py']+='\n\n# Backend opt-in; el ejecutor registra el cliente antes de importar escenas.\nfrom rc_blender_cliente import Renderer\n'
        paquete['blender']=runtime_blender.requisito('herramientas/rc_blender_servidor.py')
        guia='''
Backend Blender 4.5.16 LTS/Eevee nativo. El coordinador prepara y abre el runtime;
no iniciar bpy ni subprocess desde una escena. Renderer devuelve PIL RGB y
last_depth axial normalizada; permite varios renders por frame y postprocesos.
decorados3d.escena conserva los seis escenarios y activa recursos Blender sin
cambiar su firma. Sus opciones de decorado siguen siendo libres. amb['blender']
permite extender/componer paredes, tren y cocina. Para recipientes agarrados,
amb['blender']['ollas'] es una lista de {mano:[x,y,z],piel:'#RRGGBB'} con la mano
REAL tras IK y proyección del sprite al mundo; t usa el reloj de la escena.
No dibujar otra olla/chorro ni cuenco sobre los del decorado. La escena principal
incluye un ejemplo de esta conversión con sprite(...,con_anclas=True). Los rigs,
apariencias independientes, expresiones y FK/IK no se sustituyen por personajes bpy.
Se puede construir cualquier Malla, actuar con el rig o ampliar objetos mediante
código Python propio; no existe una lista cerrada de planos obligatorios.
Materiales/agua/espuma/vapor son procedurales: no equivalen a simulación física ni
al acabado artístico de la referencia. Ver evidencias del candidato, no las de v5.
'''
        archivos['recursos/LEEME.txt']+=guia
        archivos['recursos/LEEME.txt']=archivos['recursos/LEEME.txt'].replace(
            'RicksClips híbrido local, OpenGL 3.3.', 'RicksClips híbrido local, Blender 4.5.16 LTS / Eevee.').replace(
            'GPU/contexto OpenGL 3.3 local obligatorio.', 'GPU compatible con Blender 4.5.16/Eevee obligatoria; comprobado en RTX 4060 Laptop.')
        archivos['herramientas/LEEME.txt']+=guia
        paquete['direccion']=archivos['recursos/LEEME.txt']
        # El candidato no hereda la certificación visual de los paquetes OpenGL.
        cumplimiento['alcance']='Candidato Blender experimental; integración y fidelidad aún en comprobación.'
        cumplimiento['limitaciones']='Acabado artístico no equivalente; agua, espuma, vapor y explosión procedurales sin simulación física. Voz y música no generadas ni certificadas.'
        cumplimiento['revision_visual']={
            'implementado_pendiente_revision':['seis escenarios en Eevee','olla y dedos con ancla real tras IK y límite de mesa',
                'locomotora con ruedas, bielas y vapor','cañón procedural','espuma espacial','niebla, profundidad, alfa y sombras',
                'cámara, transiciones y postprocesos Python'],
            'calidad_equivalente_verificada':False,
            'evidencias':'La publicación exige evidencias nuevas de estas fuentes; no hereda revisión del piloto ni de v5.'}
        for requisito in cumplimiento['requisitos']:
            requisito['implementacion']=requisito['implementacion'].replace('Renderer OpenGL:','Renderer Blender Eevee:').replace(
                'shadow map PCF','sombras Eevee').replace('humo por raymarch integrado contra z-buffer',
                'humo/vapor y explosión bpy en el mismo espacio de profundidad')
            requisito['archivos']+=['herramientas/rc_blender_servidor.py','herramientas/rc_blender_artesania.py']
        archivos['recursos/cumplimiento.json']=json.dumps(cumplimiento,ensure_ascii=False,indent=2)
    if evidencias is not None:
        pruebas=json.loads((Path(evidencias)/'muestra'/'pruebas_gpu.json').read_text(encoding='utf-8'))
        esperado=huellas_fuentes(paquete)
        if pruebas.get('fuentes')!=esperado:
            raise ValueError('las pruebas GPU no corresponden a estas fuentes; verifica este borrador antes de publicar')
        archivos['recursos/pruebas_gpu.json']=json.dumps(pruebas,ensure_ascii=False,indent=2)
    return espacio_estilo.validar(paquete,exigir_biblioteca=True)


def comprobar_servicio(url):
    def get(path):
        with urllib.request.urlopen(url.rstrip('/')+path,timeout=10) as r:return json.load(r)
    if get('/api/trabajos?activos=1')['trabajos']:
        raise ValueError('hay trabajos activos; no preparar ahora')
    if any((f.get('trabajo') or {}).get('estado') in ('ejecutando','pendiente') for f in get('/api/estilos-ia')['estilos']):
        raise ValueError('hay trabajos de estilos activos; no preparar ahora')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--estilo',required=True,type=Path);p.add_argument('--borrador',required=True,type=Path)
    p.add_argument('--publicar',action='store_true');p.add_argument('--servicio',default='http://127.0.0.1:8020')
    p.add_argument('--evidencias',type=Path,help='carpeta creada por verificar_ricksclips, fuentes idénticas')
    p.add_argument('--backend',choices=['opengl','blender'],default='opengl')
    args=p.parse_args()
    if args.publicar and args.evidencias is None:raise ValueError('verifica antes el paquete y aporta --evidencias')
    paquete=construir(args.estilo,args.evidencias,args.backend)
    if args.publicar and args.backend=='blender':
        from herramientas.validacion_blender import comprobar
        prueba=comprobar(args.evidencias,huellas_fuentes(paquete))
        paquete['cumplimiento']['alcance']='Motor Blender local comprobado por fuentes; calidad artística no equivalente a la referencia.'
        paquete['cumplimiento']['revision_visual']=dict(calidad_equivalente_verificada=False,
            evidencia='recursos/pruebas_blender.json: revisión HD ligada a SHA de clips y fuentes, con límites artísticos declarados.',
            capacidades_comprobadas=paquete['cumplimiento']['revision_visual']['implementado_pendiente_revision'])
        paquete['archivos']['recursos/cumplimiento.json']=json.dumps(paquete['cumplimiento'],ensure_ascii=False,indent=2)
        revision=json.loads(Path(prueba['revision_visual']).read_text(encoding='utf8'))
        paquete['archivos']['recursos/revision_visual.txt']='Revisión del motor Blender publicado; calidad no equivalente.\n\n'+'\n\n'.join(
            nombre+': '+dato['observaciones'] for nombre,dato in revision['planos'].items())
        paquete['archivos']['recursos/pruebas_blender.json']=json.dumps(dict(fuentes=huellas_fuentes(paquete),
            blender='4.5.16 LTS',backend='BLENDER_EEVEE_NEXT',preparacion_aislada=True,p6_nativo=True,
            p7_p8=True,duplicacion_con_clips=True,reconstruccion_dependencias=True,
            recuperacion=True,hd_revisado=True,calidad_equivalente_verificada=False,
            revision_visual=revision),ensure_ascii=False,indent=2)
        paquete=espacio_estilo.validar(paquete,exigir_biblioteca=True)
    if args.borrador.exists():raise ValueError('el borrador ya existe; elige otro nombre para conservarlo')
    escribir_json(str(args.borrador),paquete)
    print('Paquete local validado:',args.borrador,flush=True)
    if args.publicar:
        comprobar_servicio(args.servicio)
        archivo_pruebas=Path(args.evidencias)/'muestra'
        pruebas_fijas=args.estilo/'comprobaciones'/('local_'+espacio_estilo.huella(paquete)[:16])
        pruebas_fijas.parent.mkdir(parents=True,exist_ok=True)
        if pruebas_fijas.exists():raise ValueError('ya existen estas muestras archivadas; no se sobrescriben')
        shutil.copytree(archivo_pruebas,pruebas_fijas)
        print('Muestras adicionales conservadas en:',pruebas_fijas,flush=True)
        # Fallar cerrado si una futura modificación intenta consultar al constructor.
        with patch.object(espacio_estilo,'consultar_constructor',side_effect=AssertionError('proveedores prohibidos')):
            ultimo=['']
            def avisar(valor,mensaje):
                if mensaje!=ultimo[0]:print(mensaje,flush=True);ultimo[0]=mensaje
            resultado=estilos_ia.preparar(avisar,str(args.estilo.parent),args.estilo.name,presets_canal,
                paquete_local=paquete,muestra_local=dict(ancho=720,alto=1280,fps=25,duracion=18))
        print(json.dumps(resultado,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
