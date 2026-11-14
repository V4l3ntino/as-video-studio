"""Contrato y renders editoriales sin proveedores: python ... [--real]."""
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEMP = tempfile.TemporaryDirectory(prefix='prueba_editorial_')
for clave in ('ESTUDIO_ESTADISTICAS', 'ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_UTILERIA_STICKMAN'):
    os.environ[clave] = str(Path(TEMP.name) / clave)
os.environ['ESTUDIO_SIMULAR'] = '1'
from pasos import stickman, realizacion_stickman as editorial

REAL = '--real' in sys.argv
if REAL:
    sys.argv.remove('--real')


def actores(base):
    return {'ana': dict(base, ropa='tshirt', color='#33769b', contorno='#8dd1f2'),
            'bruno': dict(base, ropa='tshirt', color='#e18a39', contorno='#ffbc75')}


def narrativa(base, **cambios):
    return dict(ambiente='night', decorado='vacio', atmosfera='ninguna',
        realizacion=dict(encuadre='conjunto', escenario=dict(id='fiesta_principal', tipo='fiesta', semilla=7),
            acabado=True, grano=.015, vineta=.25),
        personajes=[dict(id='ana',x=.32,y=.87,escala=2.6,claves=[dict(t=0,pose='relaxed'),dict(t=1,pose='explain')]),
            dict(id='bruno',x=.68,y=.87,escala=2.6,mirar=-1,claves=[dict(t=0,pose='think'),dict(t=2,pose='shrug')])], **cambios)


def grafica(tipo, opciones):
    return dict(ambiente='void', decorado='vacio', personajes=[], realizacion=dict(encuadre='grafico',
        escenario=dict(id='esquemas', tipo='vacio'), acabado=True),
        graficos=[dict(tipo='blueprint',capa='fondo'), dict(tipo=tipo,opciones=opciones,inicio=.1,fin=4)])


CASOS_GRAFICOS = {
    'titleCard': dict(lines=['UNA DIFERENCIA', 'QUE IMPORTA'],sub='Conocer y sentir'),
    'bigLine': dict(str='¿Qué cambia realmente?'),
    'badge': dict(str='CAPÍTULO 1'),
    'readout': dict(label='GRUPO',value='A'),
    'callout': dict(str='El elemento importante',at=[500,600],to=[1100,350]),
    'dimension': dict(str='Intervalo observado'),
    'dataCard': dict(title='Ejemplo ilustrativo',subtitle='No son datos de una investigación',to=40,unit='%'),
    'compareBars': dict(rows=[dict(label='Antes',v=.3),dict(label='Después',v=.7)]),
    'meter': dict(label='PROGRESIÓN'),
    'blueprint': {},
    'lineFigure': dict(x=960,y=900,s=2),
    'bubble': dict(str='Una pregunta',w=700,h=160),
    'captions': {},
    'endScreen': dict(question='¿Qué harías tú?',suscribir='Suscríbete'),
    'lista': dict(titulo='UNA IDEA A LA VEZ',filas=['Situación reconocible','Acción principal','Resultado visible'],intervalo=.8),
    'barras': dict(titulo='DOS CONDICIONES',filas=[dict(label='Condición A',v=.3),dict(label='Condición B',v=.75)]),
    'poblacion': dict(titulo='UN GRUPO DENTRO DEL CONJUNTO',total=100,destacados=8),
    'cronologia': dict(titulo='UN PATRÓN EN EL TIEMPO',etiquetas=['Inicio','Cambio','Resultado']),
    'documento': dict(titulo='QUÉ DICE EL DOCUMENTO',filas=['Primer elemento','La distinción importante','Una consecuencia'],destacar=1,sello='REVISADO'),
    'comparacion': dict(izquierda='COMPRENDER',derecha='SENTIR',detalle_izquierdo='Reconoce la emoción',detalle_derecho='Comparte la emoción'),
    'interruptor': dict(titulo='UNA CAPACIDAD ACTIVABLE',activo=True,cambio=2),
    'dial': dict(titulo='UN UMBRAL',valor=30,maximo=40),
}


class Editorial(unittest.TestCase):
    def setUp(self):
        self.base=stickman.familias()[0]
        self.reparto=actores(self.base)

    def validar(self,d):
        return stickman.validar_puesta_en_escena(d,4,self.reparto,[1920,1080])

    def test_todos_los_componentes_tienen_contrato_y_conservan_sus_opciones(self):
        self.assertEqual(set(CASOS_GRAFICOS),set(editorial.GRAFICOS))
        for tipo,ops in CASOS_GRAFICOS.items():
            with self.subTest(tipo=tipo):
                d=stickman.escena(grafica(tipo,ops),4,self.reparto)
                self.assertEqual(d['graficos'][-1]['opciones'],ops)
                self.assertEqual(stickman.escena(d,4,self.reparto),d)
        for tipo in editorial.EFECTOS:
            with self.subTest(tipo=tipo):
                d=stickman.escena(dict(efectos_visuales=[dict(tipo=tipo)]),4,{})
                self.assertEqual(d['efectos_visuales'][0]['tipo'],tipo)

    def test_rechaza_inyecciones_magnitudes_no_finitas_y_referencias_rotas(self):
        invalidos=[grafica('barras',dict(filas=[dict(label='A',v=float('nan'))])),
            grafica('barras',dict(filas=[dict(label='A',v=1.2)])),
            grafica('documento',dict(filas=['A'],html='<script>')),
            grafica('poblacion',dict(total=3,destacados=4)),
            grafica('poblacion',dict(total=3.2)),
            grafica('dial',dict(valor=50,maximo=40)),
            grafica('interruptor',dict(cambio=20)),
            dict(efectos_visuales=[dict(tipo='eval',opciones={})]),
            dict(efectos_visuales=[dict(tipo='rain',opciones=dict(count=100000))]),
            dict(realizacion=dict(encuadre='primer_plano',sujeto='inventado')),
            dict(espacio3d=dict(objetos=[dict(tipo='figure3D',opciones=dict(personaje='inventado'))]))]
        for d in invalidos:
            with self.subTest(d=d),self.assertRaises(ValueError):
                stickman.escena(d,4,self.reparto)

    def test_encuadres_permiten_figurantes_pero_no_ocultan_un_principal(self):
        d=narrativa(self.base)
        d['personajes'].append(dict(id='extra',rol='figurante',x=.15,y=.87,escala=.8))
        r=dict(self.reparto,extra=self.base)
        stickman.validar_puesta_en_escena(d,4,r,[1920,1080])
        d['personajes'][-1].pop('rol')
        with self.assertRaisesRegex(ValueError,'encuadre'):
            stickman.validar_puesta_en_escena(d,4,r,[1920,1080])
        d=narrativa(self.base)
        d['realizacion'].update(encuadre='primer_plano',sujeto='ana')
        self.validar(d)
        d['realizacion'].update(encuadre='dividido')
        with self.assertRaisesRegex(ValueError,'dividido'):
            self.validar(d)
        for c,p in zip(d['personajes'],['izquierda','derecha']):c['panel']=p
        self.validar(d)

    def test_escenarios_estables_y_marcas_reales_llegan_a_ambos_proveedores(self):
        entrada=dict(id='S001',narracion='Ana entiende.',t_in=10,t_out=14,marcas=[[10.2,10.7],[11,11.8]],
            escenarios_video=[dict(id='fiesta_principal',tipo='fiesta',semilla=7)])
        entrega=narrativa(self.base)
        for proveedor in ('Claude','ChatGPT'):
            with self.subTest(proveedor=proveedor),patch.dict(os.environ,ESTUDIO_SIMULAR='0'),\
                    patch.object(stickman,'_consultar',return_value=entrega) as consultar:
                resultado=stickman.generar_escena(entrada,self.base,self.reparto,None,lambda *a:None,proveedor)
                self.assertEqual(resultado['palabras'][0]['word'],'Ana')
                self.assertAlmostEqual(resultado['palabras'][0]['start'],.2)
                self.assertIn('fiesta_principal',consultar.call_args.args[0])
                self.assertIn('primer_plano',consultar.call_args.args[0])
                self.assertIn('espacio3d',consultar.call_args.args[0])

    def test_plan_historico_no_recibe_acabado_ni_graficos_al_leerlo(self):
        antes=stickman.escena(dict(personajes=[dict(id='ana')]),4,self.reparto)
        self.assertNotIn('realizacion',antes)
        self.assertNotIn('graficos',antes)
        copia=copy.deepcopy(antes)
        self.assertEqual(stickman.escena(antes,4,self.reparto),copia)
        self.assertEqual(antes,copia)

    @unittest.skipUnless(REAL,'usa --real para todos los componentes en Chromium')
    def test_render_catalogo_completo_fuentes_relojes_y_determinismo(self):
        from pasos import p8_render
        from PIL import Image,ImageStat
        escenas={}
        for tipo,ops in CASOS_GRAFICOS.items():escenas['grafico_'+tipo]=stickman.escena(grafica(tipo,ops),4,self.reparto)
        for lugar in editorial.ESCENARIOS:
            d=narrativa(self.base);d['realizacion']['escenario'].update(tipo=lugar,id=lugar)
            escenas['escenario_'+lugar]=self.validar(d)
        d=narrativa(self.base);d['realizacion'].update(encuadre='primer_plano',sujeto='ana',desenfoque=6)
        escenas['primer_plano']=self.validar(d)
        d=narrativa(self.base);d['realizacion'].update(encuadre='dividido')
        for c,p,x in zip(d['personajes'],['izquierda','derecha'],[.25,.75]):c.update(panel=p,x=x)
        d['graficos']=[dict(tipo='comparacion',opciones=CASOS_GRAFICOS['comparacion'])]
        escenas['dividido']=self.validar(d)
        for tipo in editorial.EFECTOS:
            d=narrativa(self.base);d['efectos_visuales']=[dict(tipo=tipo,opciones=dict(x=960,y=600))] if 'x' in editorial.EFECTOS[tipo] else [dict(tipo=tipo)]
            # Opciones necesarias para los constructores que no definen tamaño por defecto.
            if tipo in ('windowFrame','facade','counter','screen'):
                d['efectos_visuales'][0]['opciones'].update(w=500,h=300)
            escenas['efecto_'+tipo]=self.validar(d)
        original=p8_render.Navegador.capturar
        muestras=Path(os.environ.get('ESTUDIO_PRUEBA_STICKMAN_MUESTRAS',TEMP.name))
        muestras.mkdir(parents=True,exist_ok=True)
        def comprobar(navegador,destino=None):
            fuentes=navegador.evaluar('[document.fonts.check(\'700 40px "Fredoka"\'),document.fonts.check(\'900 40px "Nunito"\'),document.fonts.check(\'italic 900 40px "Playfair Display"\')]')
            self.assertTrue(all(fuentes))
            for nombre,d in escenas.items():
                with self.subTest(nombre=nombre):
                    navegador.evaluar('window.STICKMAN.escena='+json.dumps(d))
                    navegador.pintar(1.5)
                    antes=original(navegador)
                    with Image.open(io.BytesIO(antes)) as img:
                        self.assertGreater(sum(ImageStat.Stat(img.convert('RGB')).var),.2 if nombre=='grafico_blueprint' else 20)
                        if not nombre.startswith('efecto_'):img.save(muestras/(nombre+'.png'))
                    navegador.pintar(.3);navegador.pintar(1.5)
                    self.assertEqual(antes,original(navegador),nombre+' depende del orden de reproducción')
            # Los estados semánticos deben cambiar; no basta con aceptar el JSON.
            navegador.evaluar('window.STICKMAN.escena='+json.dumps(escenas['grafico_interruptor']))
            navegador.pintar(1);encendido=original(navegador)
            navegador.pintar(3);self.assertNotEqual(encendido,original(navegador))
            # El mismo revelado continúa entre dos frases sin repetir la entrada.
            continuo=copy.deepcopy(escenas['grafico_lista']);continuo['realizacion']['grano']=0
            continuo['graficos'][-1]['duracion_total']=3.9
            navegador.evaluar('window.STICKMAN.escena='+json.dumps(continuo));navegador.pintar(2)
            primer_tramo=original(navegador)
            continuo['graficos'][-1].update(inicio=0,fin=2,desfase=1.9)
            navegador.evaluar('window.STICKMAN.escena='+json.dumps(continuo));navegador.pintar(0)
            self.assertEqual(primer_tramo,original(navegador))
            # El texto de pantalla queda fuera de la cámara; el del mundo la sigue.
            capas=self.validar(narrativa(self.base));capas['camara']=[dict(t=0,escala=1.5)]
            capas['graficos']=[dict(tipo='badge',inicio=0,fin=4,capa=c,opciones=dict(str=c))
                for c in ('fondo','pantalla')]
            navegador.evaluar('window.STICKMAN.escena='+json.dumps(capas))
            escalas=navegador.evaluar('''(() => {
                const ctx=document.querySelector('canvas').getContext('2d'),orig=ctx.fillText,out={};
                ctx.fillText=function(str,...args){if(str==='fondo'||str==='pantalla')out[str]=this.getTransform().a;return orig.call(this,str,...args);};
                try{pintar(1);return out;}finally{ctx.fillText=orig;}
            })()''')
            self.assertAlmostEqual(escalas['pantalla'],.5)
            self.assertAlmostEqual(escalas['fondo'],.6625)
            return original(navegador,destino)
        inicial=self.validar(narrativa(self.base))
        inicial['palabras']=[dict(word='Una',start=0,end=1),dict(word='idea',start=1,end=2),dict(word='clara',start=2,end=4)]
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            stickman.renderizar(self.base,inicial,4,str(muestras/'catalogo.png'),salida=(960,540))

    @unittest.skipUnless(REAL,'usa --real para Three.js, órbita y recorrido')
    def test_render_3d_completo_con_sombras_materiales_y_camara(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        d=narrativa(self.base)
        objetos=[dict(tipo='ground',color='#334044',opciones=dict(w=40,d=40,textura='tiles')),
            dict(tipo='building',posicion=[-3,0,-4],color='#263346',opciones=dict(w=4,h=8,d=3)),
            dict(tipo='figure3D',posicion=[0,0,0],opciones=dict(personaje='ana'))]
        for i,tipo in enumerate(editorial.TIPOS3D):
            if tipo not in ('ground','building','figure3D'):
                objetos.append(dict(tipo=tipo,posicion=[(i%5-2)*3,0,-5-(i//5)*4],color='#5c6d79'))
        d['espacio3d']=dict(objetos=objetos,camara=dict(modo='orbit',radius=14,height=5))
        contenido=self.validar(d)
        def comprobar(navegador,destino=None):
            navegador.pintar(.1);inicio=original(navegador)
            navegador.pintar(2);fin=original(navegador)
            self.assertNotEqual(inicio,fin)
            navegador.pintar(.1);self.assertEqual(inicio,original(navegador))
            d2=copy.deepcopy(contenido);d2['espacio3d']['camara']=dict(modo='dolly',posicion=[0,4,14],destino=[3,4,11])
            navegador.evaluar('window.STICKMAN.escena='+json.dumps(d2));navegador.pintar(2)
            self.assertNotEqual(fin,original(navegador))
            return original(navegador,destino)
        muestras=Path(os.environ.get('ESTUDIO_PRUEBA_STICKMAN_MUESTRAS',TEMP.name))
        muestras.mkdir(parents=True,exist_ok=True)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            stickman.renderizar(self.base,contenido,4,str(muestras/'espacio3d.png'),salida=(640,360))


if __name__=='__main__':
    unittest.main()
