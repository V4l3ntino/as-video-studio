"""Biblioteca al preparar el estilo y reutilización entre vídeos; sin cuota/red."""
import copy
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
_DATOS = tempfile.TemporaryDirectory(prefix='biblioteca_estilo_')
for clave in ('ESTUDIO_SECRETOS','ESTUDIO_AJUSTES','ESTUDIO_ESTADISTICAS',
        'ESTUDIO_PRESETS','ESTUDIO_BANCO_PRESETS','ESTUDIO_ESTILOS_IA',
        'ESTUDIO_PROYECTOS','ESTUDIO_BITACORA_GLOBAL','ESTUDIO_RECURSOS_ANIMACION'):
    os.environ[clave] = str(Path(_DATOS.name)/clave)

from nucleo.proyecto import Proyecto,escribir_json,leer_json
from pasos import biblioteca_estilo as biblioteca,espacio_estilo as espacio,estilos_ia as estilos
from pasos import recursos_animacion as recursos,animacion_nativa as nativa,presets_canal as presets,p6_assets,cli_claude
ESCRIBIENDO_REAL = cli_claude.escribiendo


RIG = '''import math
from PIL import ImageDraw
APARIENCIA_VERSION=1
PAL={'ropa':'#dddddd'}
def aplicar_apariencia(datos):
    PAL['ropa']=datos['colores']['ropa']
def estado_base():return dict(x=.5,y=.9,brazo=1.2)
def interpolar(a,b,u):
    return {k:a[k]+(b.get(k,a[k])-a[k])*u for k in a}
def caminar(t):return dict(brazo=math.sin(t*4))
def sentarse(u):return dict(y=.9-.2*u,brazo=-u)
def saludar(t):return dict(brazo=math.sin(t*6))
def dibujar(im,estado,contexto):
    W,H=im.size;e=dict(estado_base(),**estado);x=e['x']*W;y=e['y']*H
    d=ImageDraw.Draw(im);a=e['brazo'];col=PAL['ropa']
    d.ellipse((x-.06*W,y-.65*H,x+.06*W,y-.45*H),fill=col)
    d.line([(x,y-.45*H),(x,y-.12*H)],fill=col,width=5)
    mano=(x+.18*W*math.cos(a),y-.35*H+.24*H*math.sin(a))
    d.line([(x,y-.35*H),mano],fill=col,width=5)
    d.line([(x-.08*W,y),(x,y-.12*H),(x+.08*W,y)],fill=col,width=4)
    return {'mano':mano}
'''
OBJETO = '''from PIL import ImageDraw
def dibujar(im,estado,contexto):
    W,H=im.size;x=estado.get('x',.75)*W;y=estado.get('y',.5)*H
    d=ImageDraw.Draw(im);r=estado.get('radio',.1)*W
    d.rectangle((x-r,y-r,x+r,y+r),fill=estado.get('color','#35a5ff'))
    return {'centro':(x,y)}
'''
MOTOR = '''from PIL import Image
import personaje_base
def pintar(pedido,t):
    im=Image.new('RGB',(pedido['ancho'],pedido['alto']),'#202838')
    personaje_base.dibujar(im,dict(brazo=1.2-t),dict(t=t))
    return im
'''


def paquete():
    entradas = dict(personaje_base=dict(tipo='personaje',concepto='base',nombre='Monigote base',
        interfaz='dibujar(im,estado,contexto), estado_base, aplicar_apariencia. x/y normalizados; brazo radianes. interpolar(a,b,u), caminar(t), sentarse(u), saludar(t) devuelven estados articulados.',
        muestra=[dict(x=.5,y=.9,brazo=1.2),dict(x=.5,y=.9,brazo=-1.2)]))
    archivos = {'herramientas/personaje_base.py':RIG}
    for nombre in sorted(biblioteca.OBJETOS):
        entradas[nombre] = dict(tipo='objeto',concepto=nombre,nombre=nombre,
            interfaz='dibujar(im,estado,contexto); x,y,radio normalizados; color #RRGGBB.',
            muestra=[dict(x=.4,y=.5,radio=.08),dict(x=.7,y=.5,radio=.15)])
        archivos['herramientas/'+nombre+'.py'] = OBJETO
    return dict(codigo=MOTOR,archivos=archivos,dependencias=[],descargas=[],parametros={},direccion='',
        biblioteca=dict(version=1,rig='personaje_base',partes=sorted(biblioteca.PARTES),
            movimientos={n:n for n in biblioteca.MOVIMIENTOS},recursos=entradas))


class Biblioteca(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='biblioteca_caso_');self.addCleanup(self.tmp.cleanup)
        self.raiz=Path(self.tmp.name)
        env=patch.dict(os.environ,ESTUDIO_ESTILOS_IA=str(self.raiz/'estilos'),
            ESTUDIO_RECURSOS_ANIMACION=str(self.raiz/'catalogo'))
        env.start();self.addCleanup(env.stop)
        banco=patch.multiple(presets,FICHERO=str(self.raiz/'presets.json'),BANCO=str(self.raiz/'banco'))
        banco.start();self.addCleanup(banco.stop)
        # Instala solo biblioteca estándar y copia Pillow YA INSTALADO; sin PyPI.
        instalar_real=espacio.instalar
        def instalar(destino,avisar):
            import PIL
            instalar_real(destino,avisar)
            local=Path(destino)/'dependencias/PIL'
            if not local.exists():shutil.copytree(Path(PIL.__file__).parent,local)
        for p in (patch.object(espacio,'instalar',side_effect=instalar),
                patch.object(espacio,'descargar',side_effect=AssertionError('No red')),
                patch.object(cli_claude,'ejecutar',side_effect=AssertionError('No CLI real')),
                patch.object(cli_claude,'escribiendo',side_effect=AssertionError('No CLI real')),
                patch.object(nativa,'consultar',side_effect=AssertionError('No proveedor real'))):
            p.start();self.addCleanup(p.stop)

    def preparar(self):
        from PIL import Image
        ficha=estilos.crear(str(self.raiz/'videos'),io.BytesIO(b'video de prueba'),'ref.mp4','Estilo con biblioteca')
        carpeta=estilos.carpeta(str(self.raiz/'videos'),ficha['id'])
        (carpeta/'referencias').mkdir()
        for i in range(24):Image.new('RGB',(48,27),'blue').save(carpeta/'referencias'/f'{i:02d}.jpg')
        Image.new('RGB',(48,27),'blue').save(carpeta/'miniatura.jpg')
        analisis=dict(resumen='Animación procedural original.',guia_visual='Dibujo articulado.',
            guia_guion='Ejemplos propios.',idioma='es',areas={n:'Observado.' for n in estilos.AREAS},
            recursos=[dict(nombre='Biblioteca articulada',motivo='Dibujo reutilizable.',motor='nuevo')])
        ficha.update(estado='analizado',analisis=analisis)
        escribir_json(str(carpeta/'estilo.json'),ficha)
        with patch.object(espacio,'consultar_constructor',return_value=espacio.validar(paquete(),exigir_biblioteca=True)) as consulta:
            resultado=estilos.preparar(lambda *a:None,str(self.raiz/'videos'),ficha['id'],presets)
        self.assertEqual(consulta.call_count,1)
        return resultado,carpeta

    def test_contrato_y_compatibilidad_sin_reescribir_paquetes_anteriores(self):
        valido=espacio.validar(paquete(),exigir_biblioteca=True)
        self.assertEqual(len(valido['biblioteca']['recursos']),5)
        for cambiar in ('objeto','apariencia','movimiento','partes','fuente'):
            roto=paquete()
            if cambiar=='objeto':del roto['biblioteca']['recursos']['casa']
            if cambiar=='apariencia':roto['archivos']['herramientas/personaje_base.py']=RIG.replace('APARIENCIA_VERSION=1','APARIENCIA_VERSION=0')
            if cambiar=='movimiento':roto['biblioteca']['movimientos']['caminar']='inexistente'
            if cambiar=='partes':roto['biblioteca']['partes']=[]
            if cambiar=='fuente':del roto['archivos']['herramientas/movil.py']
            with self.assertRaises(ValueError):espacio.validar(roto,exigir_biblioteca=True)
        antiguo=paquete();del antiguo['biblioteca']
        self.assertNotIn('biblioteca',espacio.validar(antiguo))
        with self.assertRaises(ValueError):espacio.validar(antiguo,exigir_biblioteca=True)

    def test_biblioteca_admite_re_y_copy_sin_dependencias_externas(self):
        dato=paquete()
        dato['archivos']['herramientas/personaje_base.py']='import re, copy\n'+RIG
        valido=espacio.validar(dato,exigir_biblioteca=True)
        self.assertEqual(valido['archivos'],dato['archivos'])
        self.assertEqual(valido['dependencias'],[])

    def test_constructor_exige_requisitos_y_conserva_sus_evidencias(self):
        analisis=dict(guia_visual='Personajes 2D sobre escenarios 3D cel-shaded.',
            areas=dict(animacion='Dolly con oclusiones.'),recursos=[dict(nombre='Taberna 3D',motivo='Profundidad')])
        dato=paquete()
        dato['cumplimiento']=dict(version=1,requisitos=[dict(id=r['id'],estado='implementado',
            implementacion='Geometría proyectada con profundidad; revisar fidelidad en la muestra.',
            archivos=['motores/escena.py']) for r in espacio.requisitos_constructor(analisis)])
        with patch.object(cli_claude,'escribiendo',return_value=(json.dumps(dato),{})) as cli:
            resultado=espacio.consultar_constructor(self.raiz,analisis,[],lambda *a:None)
        self.assertEqual(resultado['cumplimiento'],dato['cumplimiento'])
        prompt=cli.call_args.args[0]
        self.assertIn('no lo rebajes silenciosamente',prompt)
        self.assertIn('NO obliga a dibujar todo en 2D',prompt)
        self.assertIn('Taberna 3D',prompt)
        self.assertIn('no_compatible',prompt)

    def test_requisitos_omitidos_o_no_compatibles_bloquean_sin_reconsultar(self):
        analisis=dict(guia_visual='Escenarios con profundidad 3D.')
        for caso in ('ausente','omitido','no_compatible','archivo_inexistente'):
            with self.subTest(caso=caso):
                destino=self.raiz/caso;dato=paquete()
                entrada=dict(id='guia_visual',estado='implementado',implementacion='Proyección local.',
                    archivos=['motores/escena.py'])
                if caso=='no_compatible':entrada['estado']='no_compatible'
                if caso=='archivo_inexistente':entrada['archivos']=['herramientas/no_existe.py']
                if caso!='ausente':dato['cumplimiento']=dict(version=1,requisitos=[] if caso=='omitido' else [entrada])
                with patch.object(cli_claude,'escribiendo',return_value=(json.dumps(dato),{})) as cli:
                    for _ in range(2):
                        with self.assertRaises(ValueError):
                            espacio.consultar_constructor(destino,analisis,[],lambda *a:None)
                self.assertEqual(cli.call_count,1)

    def test_entrega_anterior_sin_informe_se_recupera_sin_consulta(self):
        analisis=dict(guia_visual='Estilo antiguo conservado.')
        with patch.object(cli_claude,'escribiendo',return_value=(json.dumps(paquete()),{})) as cli:
            with self.assertRaisesRegex(ValueError,'cumplimiento'):
                espacio.consultar_constructor(self.raiz,analisis,[],lambda *a:None)
        prompt_anterior=cli.call_args.args[0].split('\nREQUISITOS DE REALIZACIÓN:')[0]
        cruda=next((self.raiz/'constructor_respuestas').glob('*.txt'))
        cruda.rename(cruda.with_name(espacio.huella([prompt_anterior,[]])+'.txt'))
        with patch.object(cli_claude,'escribiendo',side_effect=AssertionError('No repetir IA')):
            resultado=espacio.consultar_constructor(self.raiz,analisis,[],lambda *a:None)
        self.assertNotIn('cumplimiento',resultado)

    def test_constructor_conserva_entrega_invalida_sin_repetir_cuota(self):
        respuesta=json.dumps(dict(codigo=MOTOR,archivos={},dependencias=[]))
        with patch.object(cli_claude,'escribiendo',return_value=(respuesta,{})) as cli:
            for _ in range(2):
                with self.assertRaisesRegex(ValueError,'biblioteca'):
                    espacio.consultar_constructor(self.raiz,{},[],lambda *a:None)
        self.assertEqual(cli.call_count,1)
        self.assertIn('BIBLIOTECA OBLIGATORIA',cli.call_args.args[0])
        self.assertEqual(cli.call_args.kwargs['esfuerzo'],'medium')
        self.assertEqual(cli.call_args.kwargs['tiempo_max_s'],-1)
        self.assertTrue(cli.call_args.kwargs['entrega_cruda'])
        self.assertFalse(cli.call_args.kwargs['reintentar_cuentas'])
        self.assertNotIn('Write',cli.call_args.kwargs['herramientas_vetadas'])
        self.assertEqual(next((self.raiz/'constructor_respuestas').glob('*.txt')).read_text(encoding='utf-8'),respuesta)

    def test_constructor_truncado_explica_error_y_no_repite_consulta(self):
        respuesta=' = _estado(estado, ancho, alto)\\n resto de código sin principio de JSON\n```'
        with patch.object(cli_claude,'escribiendo',return_value=(respuesta,{})) as cli:
            for _ in range(2):
                with self.assertRaisesRegex(ValueError,'JSON completo.*análisis del vídeo sigue guardado'):
                    espacio.consultar_constructor(self.raiz,{},[],lambda *a:None)
        self.assertEqual(cli.call_count,1)
        self.assertEqual(next((self.raiz/'constructor_respuestas').glob('*.txt')).read_text(encoding='utf-8'),respuesta)

    def test_constructor_nuevo_por_archivo_y_cache_antigua_siguen_validos(self):
        esperado=espacio.validar(paquete(),exigir_biblioteca=True)
        respuesta=json.dumps(paquete(),ensure_ascii=False)
        with patch.object(cli_claude,'escribiendo',return_value=(respuesta,{})) as cli:
            self.assertEqual(espacio.consultar_constructor(self.raiz,{},[],lambda *a:None),esperado)
        ruta=next((self.raiz/'constructor_respuestas').glob('*.txt'))
        self.assertEqual(Path(cli.call_args.kwargs['archivo_entrega']),ruta)
        with patch.object(cli_claude,'escribiendo',side_effect=AssertionError('No repetir')):
            self.assertEqual(espacio.consultar_constructor(self.raiz,{},[],lambda *a:None),esperado)

    def test_reconstruccion_explicita_separa_cache_y_conserva_entrega_fallida(self):
        truncada=' = _estado(estado, ancho, alto)'
        with patch.object(cli_claude,'escribiendo',return_value=(truncada,{})):
            with self.assertRaisesRegex(ValueError,'JSON completo'):
                espacio.consultar_constructor(self.raiz,{},[],lambda *a:None)
        anterior=next((self.raiz/'constructor_respuestas').glob('*.txt'))
        correccion=dict(error='Reconstrucción autorizada: entrega truncada. Escribir JSON completo en archivo.',
            paquete_anterior=None)
        with patch.object(cli_claude,'escribiendo',return_value=(json.dumps(paquete()),{})) as cli:
            nuevo=espacio.consultar_constructor(self.raiz,{},[],lambda *a:None,correccion=correccion)
            repetido=espacio.consultar_constructor(self.raiz,{},[],lambda *a:None,correccion=correccion)
        self.assertEqual(cli.call_count,1)
        self.assertEqual(nuevo,repetido)
        self.assertNotEqual(Path(cli.call_args.kwargs['archivo_entrega']),anterior)
        self.assertEqual(anterior.read_text(encoding='utf-8'),truncada)
        self.assertEqual(len(list((self.raiz/'constructor_respuestas').glob('*.txt'))),2)

    def test_actividad_constructor_solo_mide_archivos_sin_ejecutarlos(self):
        self.assertIn('Aún no hay archivos',espacio._actividad_constructor(None))
        self.assertIn('Aún no hay archivos',espacio._actividad_constructor(self.raiz))
        ruta=self.raiz/'herramientas'/'personaje.py';ruta.parent.mkdir()
        ruta.write_text('raise AssertionError("Nunca ejecutar")',encoding='utf-8')
        entrega=self.raiz/'salida.json';entrega.write_text('{"codigo":',encoding='utf-8')
        os.utime(ruta,(100,100));os.utime(entrega,(110,110))
        with patch.object(espacio.time,'time',return_value=260):
            texto=espacio._actividad_constructor(self.raiz)
        self.assertIn('2 archivos de trabajo',texto)
        self.assertIn('salida.json, hace 150 s',texto)
        self.assertIn('todavía no validada',texto)
        self.assertIn('no confirma que Claude siga avanzando',texto)

    def test_constructor_publica_fase_y_actividad_y_detiene_el_reloj(self):
        mensajes=[];captura={}
        def escribir(*args,**kwargs):
            captura['avance']=kwargs['avance']
            temporal=self.raiz/'temporal';temporal.mkdir()
            kwargs['al_preparar'](str(temporal))
            (temporal/'personaje.py').write_text('codigo parcial',encoding='utf-8')
            avance=kwargs['avance']
            avance.avisar(avance.valor(),avance.texto())
            return json.dumps(paquete()),{}
        with patch.object(cli_claude,'escribiendo',side_effect=escribir):
            espacio.consultar_constructor(self.raiz,{},[],lambda valor,mensaje:mensajes.append((valor,mensaje)))
        self.assertIn('construyendo el motor',mensajes[0][1])
        self.assertTrue(any('1 archivos de trabajo' in m for _,m in mensajes))
        self.assertIn('validando el código',mensajes[-1][1])
        self.assertFalse(captura['avance']._hilo.is_alive())
        self.assertTrue(all(v is None or v==.25 for v,_ in mensajes))

    def test_constructor_cancelado_no_reintenta_y_detiene_el_reloj(self):
        captura={}
        def cancelar(*args,**kwargs):
            captura['avance']=kwargs['avance']
            kwargs['avance'].cancelado=True
            raise RuntimeError('CLI detenido')
        from nucleo.trabajos import Cancelado
        with patch.object(cli_claude,'escribiendo',side_effect=cancelar) as cli:
            with self.assertRaises(Cancelado):
                espacio.consultar_constructor(self.raiz,{},[],lambda *a:None)
        self.assertEqual(cli.call_count,1)
        self.assertFalse(captura['avance']._hilo.is_alive())

    def test_observador_recibe_temporal_antes_del_cli_y_no_cambia_entrega(self):
        # Usa el adaptador real, doblando únicamente la llamada al proveedor.
        carpetas=[]
        def ejecutar(*args,**kwargs):
            self.assertEqual(carpetas,[kwargs['cwd']])
            (Path(kwargs['cwd'])/'salida.json').write_text('{"ok":true}',encoding='utf-8')
            return 'LISTO',{}
        with patch.object(cli_claude,'ejecutar',side_effect=ejecutar):
            resultado=ESCRIBIENDO_REAL('JSON',al_preparar=carpetas.append)
        self.assertEqual(resultado,dict(ok=True))
        self.assertFalse(Path(carpetas[0]).exists())

    def test_prepara_biblioteca_antes_de_publicar_y_la_reutiliza_en_dos_videos(self):
        resultado,carpeta=self.preparar()
        original=carpeta/'versiones/v1'
        self.assertTrue(leer_json(str(original/'espacio.json'))['biblioteca_comprobada'])
        for nombre in paquete()['biblioteca']['recursos']:
            self.assertTrue((original/'muestra/biblioteca'/nombre/'comprobacion.json').exists())
        inventario=espacio.inventario(original)
        preset=presets.leer(resultado['preset_id']);marca=resultado['espacio']
        llamadas=[]
        for numero in (1,2):
            proyecto=Proyecto.crear(str(self.raiz/'videos'),'Vídeo '+str(numero))
            estilos.congelar(presets,preset,proyecto)
            self.assertTrue((recursos.raiz(proyecto)/'rig_base.json').exists())
            basicos=recursos.catalogo(proyecto,marca['huella'])
            self.assertTrue(biblioteca.OBJETOS.issubset({recursos.cargar(proyecto,r)['asset']['concepto'] for r in basicos.values()}))
            escena=dict(id='S001',narracion='Saluda junto a un árbol.',prompt='Acción propia.',t_in=0,t_out=2,personajes_visibles=['ana'])
            plan=dict(estilo={'espacio_ia':marca},escenas=[escena],resolucion=[320,180],fps=12,assets={},dependencias={})
            params=dict(estilo=plan['estilo'],reparto_animaciones={'carga_claude':0})
            def consultar(proveedor,prompt,*a,**kw):
                self.assertEqual(proveedor,'ChatGPT')
                if 'DEFINE SOLO LOS DATOS DE APARIENCIA' in prompt:
                    llamadas.append('datos')
                    return dict(formato='apariencia/1',nombre='Ana',concepto='ana',apariencia={'pelo':'trenzas'})
                self.assertNotIn('DISEÑA SOLO ESTE PERSONAJE',prompt)
                datos=json.loads(prompt[prompt.index('{"escena":'):]);ctx=datos['recursos_animacion']
                self.assertNotIn('personaje_base',datos['herramientas_reutilizables'])
                self.assertNotIn('def aplicar_apariencia',prompt)
                actor=ctx['personajes']['ana'];arbol=next(f['modulo'] for f in ctx['catalogo'] if f['concepto']=='arbol')
                if numero==2:self.assertTrue(any(f['concepto']=='banco_nuevo' for f in ctx['catalogo']))
                llamadas.append('escena')
                banco='banco_nuevo' if numero==1 else next(f['modulo'] for f in ctx['catalogo'] if f['concepto']=='banco_nuevo')
                codigo=f'''from PIL import Image
import {actor} as actor
import {arbol} as arbol
import {banco} as banco
def pintar(pedido,t):
    im=Image.new('RGB',(320,180),'black')
    arbol.dibujar(im,dict(x=.8,y=.5,radio=.12),dict(t=t))
    banco.dibujar(im,dict(x=.6,y=.8,radio=.06),dict(t=t))
    actor.dibujar(im,dict(x=.3,y=.9,brazo=1.2-t),dict(t=t))
    return im
'''
                nuevos={'banco_nuevo':dict(tipo='objeto',concepto='banco_nuevo',nombre='Banco nuevo',interfaz='dibujar; x,y,radio normalizados',codigo=OBJETO)} if numero==1 else {}
                return dict(codigo=codigo,recursos_nuevos=nuevos,acciones=[dict(tipo='personaje',objetivo='ana',accion='Saluda',
                    claves=[dict(t=0,estado={'brazo':1.2}),dict(t=2,estado={'brazo':-.8})])],edicion='Plano general.')
            with patch.object(nativa,'consultar',side_effect=consultar), \
                    patch.object(p6_assets,'planificar',return_value=copy.deepcopy(plan)), \
                    patch.object(p6_assets,'plan_actual',return_value={}), \
                    patch.object(p6_assets,'_catalogo_de',return_value={'reparto':{'ana':{'descripcion':'Ana'}}}), \
                    patch.object(p6_assets,'_ejecutar_base',side_effect=AssertionError('No imágenes')):
                nativa.ejecutar(proyecto,params,lambda *a:None)
            copia=proyecto.duplicar(str(self.raiz/'copias'),'Copia '+str(numero))
            base=leer_json(str(recursos.raiz(proyecto)/'rig_base.json'))
            self.assertEqual(recursos.cargar(copia,base),recursos.cargar(proyecto,base))
        self.assertEqual(llamadas,['datos','escena','escena'])
        self.assertEqual(espacio.inventario(original),inventario)

    def test_asset_fallido_impide_publicar_la_version(self):
        with patch.object(biblioteca,'comprobar',side_effect=ValueError('fallo del asset casa')):
            with self.assertRaisesRegex(ValueError,'asset casa'):self.preparar()
        fichas=estilos.listar(str(self.raiz/'videos'))
        self.assertEqual(fichas[0]['estado'],'error_preparacion')
        self.assertEqual(presets.listar()['presets'].get('canal',[]),[])

    def test_paquete_local_prepara_y_actualiza_tarjeta_sin_cli_ni_tocar_v1(self):
        primero,carpeta=self.preparar()
        from pasos import muestra_tarjeta
        muestra_tarjeta.instalar(carpeta,carpeta/'versiones/v1/muestra/clip.mp4','Previa editorial de prueba')
        anterior=presets.leer(primero['preset_id'])
        anterior['datos']['voz']={'idioma':'en','velocidad':1.1}
        presets.guardar('canal',anterior['nombre'],anterior['datos'],pid=anterior['id'])
        v1=espacio.inventario(carpeta/'versiones/v1')
        ficha=leer_json(str(carpeta/'estilo.json'));local=paquete()
        local['cumplimiento']=dict(version=1,requisitos=[dict(id=r['id'],estado='implementado',
            implementacion='Código de prueba original.',archivos=['motores/escena.py'])
            for r in espacio.requisitos_constructor(ficha['analisis'])])
        pagado=carpeta/'constructor.json';pagado.write_text('entrega pagada que debe conservarse',encoding='utf-8')
        with patch.object(espacio,'consultar_constructor',side_effect=AssertionError('No proveedor')):
            segundo=estilos.preparar(lambda *a:None,str(self.raiz/'videos'),ficha['id'],presets,
                paquete_local=local,muestra_local=dict(ancho=180,alto=320,fps=12,duracion=2))
        self.assertEqual(segundo['espacio']['version'],2)
        self.assertEqual(primero['preset_id'],segundo['preset_id'])
        self.assertEqual(v1,espacio.inventario(carpeta/'versiones/v1'))
        self.assertEqual(pagado.read_text(encoding='utf-8'),'entrega pagada que debe conservarse')
        self.assertTrue((carpeta/'versiones/v2/muestra/comprobacion.json').is_file())
        self.assertEqual(presets.leer(segundo['preset_id'])['datos']['estilo']['espacio_ia'],segundo['espacio'])
        self.assertEqual(presets.leer(segundo['preset_id'])['datos']['voz'],{'idioma':'en','velocidad':1.1})
        self.assertNotIn('muestra_tarjeta',leer_json(str(carpeta/'estilo.json')))
        self.assertNotIn('muestra_tarjeta',estilos.leer(str(self.raiz/'videos'),ficha['id']))

    def test_paquete_local_incompleto_se_rechaza_antes_de_cambiar_estado(self):
        primero,carpeta=self.preparar()
        original=(carpeta/'estilo.json').read_bytes()
        with patch.object(espacio,'consultar_constructor',side_effect=AssertionError('No proveedor')):
            with self.assertRaisesRegex(ValueError,'cumplimiento'):
                estilos.preparar(lambda *a:None,str(self.raiz/'videos'),primero['estilo_id'],presets,paquete_local=paquete())
        self.assertEqual(original,(carpeta/'estilo.json').read_bytes())
        self.assertFalse((carpeta/'versiones/v2').exists())

    def test_preparacion_blender_fallida_conserva_fuentes_y_logs(self):
        from pasos import runtime_blender
        primero,carpeta=self.preparar()
        ficha=leer_json(str(carpeta/'estilo.json'));local=paquete()
        local['archivos']['herramientas/servidor.py']='pass'
        local['blender']=runtime_blender.requisito('herramientas/servidor.py')
        local['cumplimiento']=dict(version=1,requisitos=[dict(id=r['id'],estado='implementado',
            implementacion='Prueba local de conservación, no de bpy.',archivos=['motores/escena.py'])
            for r in espacio.requisitos_constructor(ficha['analisis'])])
        previo=espacio.inventario(carpeta/'versiones/v1')
        def fallar(destino,pedido,salida,avisar):
            salida.mkdir(parents=True,exist_ok=True)
            (salida/'entrada.json').write_text('{}')
            (salida/'blender.log').write_text('fallo bpy conservado')
            raise ValueError('fallo bpy de prueba')
        with patch.object(espacio,'renderizar',side_effect=fallar),\
                patch.object(espacio,'consultar_constructor',side_effect=AssertionError('No proveedor')):
            with self.assertRaisesRegex(ValueError,'fallo bpy de prueba'):
                estilos.preparar(lambda *a:None,str(self.raiz/'videos'),ficha['id'],presets,paquete_local=local)
        fallos=list((carpeta/'versiones').glob('.fallido_*'))
        self.assertEqual(len(fallos),1)
        self.assertTrue((fallos[0]/'muestra/entrada.json').is_file())
        self.assertEqual((fallos[0]/'muestra/blender.log').read_text(),'fallo bpy conservado')
        self.assertTrue((fallos[0]/'herramientas/servidor.py').is_file())
        self.assertFalse((carpeta/'versiones/v2').exists())
        self.assertEqual(espacio.inventario(carpeta/'versiones/v1'),previo)
        self.assertEqual(presets.leer(primero['preset_id'])['datos']['estilo']['espacio_ia'],primero['espacio'])

    def test_asset_sellado_alterado_no_se_regenera(self):
        local=self.raiz/'paquete'
        espacio.materializar(local,espacio.validar(paquete()),[])
        (local/'herramientas/casa.py').write_text(OBJETO+'\n# alterado',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'sellado ha cambiado'):biblioteca.leer(local)


if __name__=='__main__':unittest.main()
