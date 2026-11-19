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

    def test_constructor_conserva_entrega_invalida_sin_repetir_cuota(self):
        respuesta=json.dumps(dict(codigo=MOTOR,archivos={},dependencias=[]))
        with patch.object(cli_claude,'ejecutar',return_value=(respuesta,{})) as cli:
            for _ in range(2):
                with self.assertRaisesRegex(ValueError,'biblioteca'):
                    espacio.consultar_constructor(self.raiz,{},[],lambda *a:None)
        self.assertEqual(cli.call_count,1)
        self.assertIn('BIBLIOTECA OBLIGATORIA',cli.call_args.args[0])
        self.assertEqual(cli.call_args.kwargs['esfuerzo'],'medium')
        self.assertEqual(cli.call_args.kwargs['tiempo_max_s'],-1)
        self.assertEqual(next((self.raiz/'constructor_respuestas').glob('*.txt')).read_text(encoding='utf-8'),respuesta)

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

    def test_asset_sellado_alterado_no_se_regenera(self):
        local=self.raiz/'paquete'
        espacio.materializar(local,espacio.validar(paquete()),[])
        (local/'herramientas/casa.py').write_text(OBJETO+'\n# alterado',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'sellado ha cambiado'):biblioteca.leer(local)


if __name__=='__main__':unittest.main()
