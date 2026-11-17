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


def referencia_calle_comercial():
    def peaton(ident,x,y,s,destino,aura=False):
        return dict(id=ident,x=x,y=y,escala=s,rol='figurante',mirar=1 if destino>x else -1,
            movimiento='caminar',actuacion=dict(silueta='#7d8088',respiracion=0,
                **(dict(aura=dict(color='#ffad45',intensidad=.20)) if aura else {})),
            claves=[dict(t=0,pose='relaxed'),dict(t=4,x=destino)])
    return dict(ambiente='golden',decorado='ciudad',atmosfera='ninguna',
        realizacion=dict(encuadre='general',escenografia_detallada=True,color_fiel=True,
            acabado=True,expresiones_fieles=True,vineta=.14,grano=0,
            escenario=dict(id='calle_tiendas',tipo='calle_comercial',semilla=9)),
        personajes=[peaton('gris1',.22,.78,1.6,.30),peaton('gris2',.48,.69,1,.55),
            peaton('cruce',.68,.85,2.3,.59,True),peaton('gris3',.82,.78,1.6,.76),
            dict(id='tu',x=.37,y=.92,escala=3,movimiento='caminar',expresion='neutral',
                claves=[dict(t=0,pose='relaxed'),dict(t=4,x=.43)])])


def referencia_cine():
    return dict(ambiente='night',decorado='vacio',atmosfera='ninguna',camara=[],personajes=[],objetos=[],
        realizacion=dict(encuadre='general',escenografia_detallada=True,color_fiel=True,acabado=True,
            vineta=.12,grano=0,escenario=dict(id='cine',tipo='cine',semilla=7,
                proyeccion='silueta_amenazante',publico=True,luz='#ffb456')))


def narrativa(base, **cambios):
    return dict(ambiente='night', decorado='vacio', atmosfera='ninguna',
        realizacion=dict(encuadre='conjunto', escenario=dict(id='fiesta_principal', tipo='fiesta', semilla=7),
            acabado=True, grano=.015, vineta=.25),
        personajes=[dict(id='ana',x=.32,y=.87,escala=2.6,claves=[dict(t=0,pose='relaxed'),dict(t=1,pose='explain')]),
            dict(id='bruno',x=.68,y=.87,escala=2.6,mirar=-1,claves=[dict(t=0,pose='think'),dict(t=2,pose='shrug')])], **cambios)


def grafica(tipo, opciones):
    return dict(ambiente='void', decorado='vacio', personajes=[dict(id='ana',x=.5,y=.88,escala=2.4)]
        if tipo=='bocadillo' else [], realizacion=dict(encuadre='grafico',
        escenario=dict(id='esquemas', tipo='vacio'), acabado=True),
        graficos=[dict(tipo='blueprint',capa='fondo'), dict(tipo=tipo,opciones=opciones,inicio=.1,fin=.4 if tipo=='enfasis' else 4)])


def referencia_poblacion():
    return dict(ambiente='void',decorado='vacio',personajes=[],realizacion=dict(encuadre='grafico',
        paleta='arctic',particulas=True,malla=True,desfase_ambiente=12,color_fiel=True,grano=0,vineta=0,
        escenario=dict(id='poblacion',tipo='vacio',semilla=23)),graficos=[dict(tipo='poblacion',opciones=dict(
            titulo='EJEMPLO ILUSTRATIVO',total=100,filas=5,columnas=20,color_base='#46617c',color='#76ccff',
             indices_destacados=[23,65,94],neon_destacados=.35))])


def referencia_tipografia():
    return dict(ambiente='void',decorado='vacio',personajes=[],realizacion=dict(encuadre='grafico',
        tipografia='redondeada',fondo='#080e1c',particulas=True,color_fiel=True,grano=0,vineta=.2),
        objetos=[dict(tipo='texto',texto=texto,color=color,x=x,y=.49,w=820,h=200,fuente=150,neon=.4,
            claves=[dict(t=0,x=x),dict(t=2,x=x),dict(t=3,x=.5,opacidad=0)])
            for texto,color,x in [('PSICÓPATA','#83d9f7',.25),('SOCIÓPATA','#ffad42',.75)]]+
        [dict(tipo='texto',texto='PSICÓPATASOCIÓPATA',color='#fff3d6',x=.5,y=.49,w=1650,h=210,
            fuente=150,neon=.4,inicio=2.5,opacidad=0,claves=[dict(t=3,opacidad=1)]),
         *[dict(tipo='redondeado',color='#ffcd42',x=.5,y=y,w=150,h=28,neon=.4)
            for y in (.24,.30)]])


def referencia_tachado():
    return dict(ambiente='void',decorado='vacio',personajes=[],realizacion=dict(encuadre='grafico',
        tipografia='redondeada',paleta='arctic',fondo='#08121f',color_fiel=True,grano=0,vineta=0),
        objetos=[dict(tipo='texto',texto='PLANIFICACIÓN',color='#ffcb52',x=.5,y=.26,w=1100,h=180,fuente=130),
            dict(tipo='texto',texto='Errores torpes',color='#b97676',x=.5,y=.52,w=1100,h=180,
                fuente=130,tachado=dict(inicio=1,fin=1.5))])


def referencia_interaccion(base):
    d=narrativa(base)
    d['realizacion']=dict(encuadre='conjunto',tipografia='redondeada',paleta='ember',
        fondo='#120b09',particulas=True,color_fiel=True,expresiones_fieles=True,grano=0,vineta=.2)
    d['personajes']=[dict(id='ana',x=.16,y=.83,escala=2.2,expresion='scared',
        claves=[dict(t=0,pose='recoil')]),dict(id='bruno',x=.48,y=.83,escala=2.2,mirar=-1,
        expresion='angry',claves=[dict(t=0,pose='shout')])]
    d['objetos']=[dict(tipo='etiqueta',texto='DA MÁS MIEDO',x=.47,y=.2,w=650,h=140,
        fuente=100,color='#ffad31',neon=.55),dict(tipo='etiqueta',texto='MÁS DIFÍCIL\nDE DETECTAR',
        x=.48,y=.36,w=490,h=180,fuente=70,color='#ffb638',neon=.45,transito=True,
        claves=[dict(t=0,x=.48,y=.36,opacidad=0),dict(t=.5,opacidad=1),
            dict(t=1.5,x=.79,y=.57,rot=.08),dict(t=2.5,x=.79,y=.57),dict(t=3.5,x=1.5)])]
    return d


def referencia_rostro(base,modo='dialogo'):
    d=narrativa(base)
    d['personajes']=d['personajes'][:1]
    d['personajes'][0].update(x=.5,expresion='surprised',claves=[dict(t=0,pose='talk'),dict(t=2,pose='think')])
    d['realizacion'].update(encuadre='primer_plano',sujeto='ana',desenfoque=6,
        particulas=True,malla=False,color_fiel=True,grano=0,vineta=.18)
    d['graficos']=[dict(tipo='bocadillo',opciones=dict(personaje='ana',modo=modo,
        texto='No te mentiría.' if modo=='dialogo' else '¿Puedo confiar?'))]
    return d


def referencia_rostro_rotulado(base, encuadre='primer_plano', tipo='texto'):
    d=referencia_rostro(base)
    d['graficos']=[]
    d['personajes'][0].update(x=.6,y=.86,escala=2.4,expresion='smile',
        claves=[dict(t=0,pose='stand'),dict(t=.9,pose='relaxed')])
    d['realizacion'].update(encuadre=encuadre,tipografia='redondeada',expresiones_fieles=True,
        escenario=dict(id='oficina',tipo='oficina',semilla=7))
    d['objetos']=[dict(tipo=tipo,texto='DIFÍCIL',color='#ffcb52',x=.29,y=.4,w=600,h=150,
        fuente=120,neon=.35,claves=[dict(t=0,x=.05,opacidad=0),
            dict(t=.2,x=.1,opacidad=1,curva='out'),dict(t=.75,x=.29,curva='outBack')])]
    return d


def referencia_documento_luminoso():
    d=grafica('documento',dict(titulo='DIAGNÓSTICOS OFICIALES',estilo='neon',
        filas=['——','——','——'],color='#5bd8da',excluidos=['PSICÓPATA','SOCIÓPATA']))
    d['graficos']=d['graficos'][1:]
    d['realizacion'].update(fondo='#08121f',resplandor=True,color_fiel=True,grano=0,vineta=0)
    return d


def referencia_lista_limpia(base):
    d=referencia_rostro_rotulado(base,'medio')
    d['objetos']=[]
    d['realizacion'].update(fondo='#120b09',escenario=dict(id='preguntas',tipo='vacio'))
    d['graficos']=[dict(tipo='lista',capa='pantalla',opciones=dict(estilo='texto',numerada=True,
        filas=['¿En qué se diferencian?','¿Qué pregunta te protege?'],color='#fff1dc',
        colores_numeros=['#fff1dc','#ffcb52'],size=80,x=100,y=330,w=1100,intervalo=1.6))]
    return d


def referencia_comparacion(base):
    d=narrativa(base)
    d['realizacion'].update(encuadre='dividido',comparacion={},particulas=True,malla=False,
        color_fiel=True,grano=0,vineta=.12,desfase_ambiente=10)
    for actor,x,panel in zip(d['personajes'],(.17,.84),('izquierda','derecha')):
        actor.update(x=x,y=.89,panel=panel)
    d['graficos']=[dict(tipo='comparacion',opciones=dict(titulo='DOS FORMAS DE ACTUAR',
        izquierda='FRÍO',derecha='CALIENTE',rasgos_izquierdos=['Planificador','Casi sin miedo'],
        rasgos_derechos=['Impulsivo','Errático']))]
    return d


def referencia_termometros():
    utileria={}
    for nombre,y,color in [('frio',555,'#83d9f7'),('caliente',155,'#ff8d38')]:
        utileria[nombre]=dict(concepto='termometro-'+nombre,nombre='Termómetro '+nombre,
            descripcion='Termómetro de vidrio con columna y bulbo.',ancho=200,alto=800,partes=[
                dict(id='vidrio',formas=[dict(tipo='rectangulo',x=65,y=20,w=70,h=650,radio=35,
                    relleno=None,trazo='$claro',grosor=4)]),
                dict(id='liquido',formas=[dict(tipo='rectangulo',x=82,y=y,w=36,h=680-y,radio=18,
                    relleno='$principal'),dict(tipo='elipse',x=40,y=640,w=120,h=120,relleno='$principal')]),
                dict(id='escala',formas=[dict(tipo='trazo',comandos=[['M',140,yy],['L',156,yy]],
                    relleno=None,trazo='$claro',grosor=3) for yy in range(70,620,80)])])
    return dict(ambiente='void',decorado='vacio',personajes=[],utileria=utileria,
        realizacion=dict(encuadre='grafico',comparacion={},particulas=True,color_fiel=True,grano=0,vineta=.12),
        objetos=[dict(tipo='vector',recurso=nombre,panel=panel,x=x,y=.57,w=430,h=790,neon=.35,color=color,
            paleta=dict(principal=color,claro='#c7dbea' if nombre=='frio' else '#ffd6ae'))
            for nombre,panel,x,color in [('frio','izquierda',.25,'#83d9f7'),('caliente','derecha',.75,'#ff8d38')]],
        graficos=[dict(tipo='bigLine',opciones=dict(str='LA MISMA ESCALA',y=105,size=78,color='#ffdb83'))])


def referencia_capitulo(numero,titulo,estilo,fin=4):
    return dict(ambiente='void',decorado='vacio',personajes=[],
        realizacion=dict(encuadre='grafico',particulas=True,color_fiel=True,grano=0,vineta=0),
        graficos=[dict(tipo='capitulo',inicio=0,fin=fin,capa='pantalla',
            opciones=dict(numero=numero,titulo=titulo,estilo=estilo))])


def referencia_escenario_detallado(base,tipo='teatro'):
    d=narrativa(base)
    d['personajes']=d['personajes'][:1]
    d['personajes'][0].update(x=.45,y=.87,expresion='neutral',claves=[dict(t=0,pose='stand'),dict(t=2,pose='explain')])
    d['realizacion'].update(encuadre='conjunto',sujeto='ana',escenografia_detallada=True,
        escenario=dict(id='escenario_'+tipo,tipo=tipo,semilla=17),particulas=True,color_fiel=True,grano=0,vineta=0)
    if tipo=='teatro':
        d['realizacion']['escenario'].update(atril=True,publico=True)
    return d


def escena_neon(paleta='arctic'):
    import math
    p=editorial.PALETAS[paleta]
    objetos=[]
    for i in range(12):
        y=.16+i*.057
        apertura=.045+.09*abs(math.cos(i*.68))
        x=.32-apertura
        objetos.append(dict(tipo='linea',x=x,y=y,w=apertura*3840,h=0,color=p['sombra'],grosor=4))
        for j,xx in enumerate((x,.32+apertura)):
            objetos.append(dict(tipo='circulo',x=xx,y=y,w=22,h=22,
                color=p['acento'] if (i+j)%3 else p['texto'],neon=.25 if (i+j)%3 else 0))
    return dict(ambiente='void',decorado='vacio',personajes=[],objetos=objetos,
        realizacion=dict(encuadre='grafico',paleta=paleta,color_fiel=True,grano=0,vineta=.15,
            escenario=dict(id='genetica',tipo='vacio')),
        graficos=[dict(tipo='blueprint',capa='fondo',opciones=dict(a=.025,grid=75)),
            dict(tipo='badge',opciones=dict(str='FUERTEMENTE INFLUIDO POR',x=1740,y=400,size=40,
                color=p['detalle'] if paleta=='arctic' else p['texto'])),
            dict(tipo='badge',neon=.35,opciones=dict(str='LOS GENES',x=1740,y=550,size=96))])


CASOS_GRAFICOS = {
    'enfasis': dict(modo='impacto',punto=[.5,.5]),
    'capitulo': dict(numero=1,titulo='Una pregunta importante',estilo='arctic'),
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
    'bocadillo': dict(personaje='ana',modo='dialogo',texto='Puedo ayudarte.'),
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


def referencia_enfasis(modo='sorpresa',encuadre='conjunto'):
    opciones=dict(modo=modo,color='#ffcc44')
    if modo=='impacto':opciones['punto']=[.7,.54]
    else:opciones['personaje']='bruno'
    return dict(ambiente='void',decorado='vacio',atmosfera='ninguna',
        realizacion=dict(encuadre=encuadre,sujeto='bruno',fondo='#22252b',color_fiel=True,
            expresiones_fieles=True,grano=0,vineta=0,desenfoque=0),
        personajes=[dict(id='bruno',x=.6,y=.9,escala=2.6,expresion='neutral',
            actuacion=dict(respiracion=0),claves=[dict(t=0,pose='stand')])],
        graficos=[dict(tipo='enfasis',inicio=.8,fin=1.1,opciones=opciones)])


def referencia_rascado():
    return dict(ambiente='void',decorado='vacio',atmosfera='ninguna',
        realizacion=dict(encuadre='conjunto',fondo='#22252b',color_fiel=True,
            expresiones_fieles=True,tipografia='redondeada',grano=0,vineta=0),
        personajes=[dict(id='bruno',x=.70,y=.9,escala=3,expresion='neutral',
            actuacion=dict(mirada=[-1,0],respiracion=0,mezcla_pose=.2),
            claves=[dict(t=0,pose='relaxed'),dict(t=.4,pose='scratchHead'),dict(t=2.8,pose='relaxed')])],
        objetos=[dict(tipo='texto',texto=s,x=.29,y=y,w=800,h=100,fuente=size,color=color)
            for s,y,size,color in [('CONDUCTA',.23,100,'#ffc052'),('Impulsividad',.4,65,'#86d8f7'),
                ('Irresponsabilidad',.53,65,'#86d8f7'),('Sin metas a largo plazo',.66,65,'#86d8f7')]])


def referencia_portazo():
    return dict(ambiente='void',decorado='vacio',atmosfera='ninguna',
        realizacion=dict(encuadre='conjunto',fondo='#22252b',color_fiel=True,grano=0,vineta=0),
        personajes=[dict(id='bruno',x=.38,y=.86,escala=2.2,mirar=-1,actuacion=dict(respiracion=0,mezcla_pose=.08),
            claves=[dict(t=0,pose='pushReady'),dict(t=.55,pose='push'),dict(t=.9,pose='relaxed'),
                dict(t=1.2,x=.38,mirar=1,movimiento='caminar'),dict(t=3.5,x=.85)])],
        objetos=[dict(tipo='puerta',x=.32,y=.53,w=290,h=710,color='#795538',marco='#a18f73',
            bisagra='derecha',apertura=.8,cierre=dict(inicio=.4,fin=.65))])


class Editorial(unittest.TestCase):
    def setUp(self):
        self.base=stickman.familias()[0]
        self.reparto=actores(self.base)

    def validar(self,d):
        return stickman.validar_puesta_en_escena(d,4,self.reparto,[1920,1080])

    def test_enfasis_breve_anclado_y_sin_convertir_historicos(self):
        for modo in ('sorpresa','sobresalto','descubrimiento','enfado','confusion','impacto'):
            d=self.validar(referencia_enfasis(modo))
            self.assertEqual(stickman.escena(d,4,self.reparto),d)
            self.assertEqual(d['personajes'][0]['expresion'],'neutral')
        self.assertNotIn('graficos',stickman.escena(dict(personajes=[dict(id='bruno')]),4,self.reparto))
        for cambio in (dict(fin=2),dict(fin=.9),dict(desfase=1),dict(duracion_total=4),dict(capa='frente'),
                dict(opciones=dict(modo='sorpresa',personaje='nadie')),
                dict(opciones=dict(modo='impacto',personaje='bruno')),
                dict(opciones=dict(modo='impacto',punto=[2,.5])),dict(opciones=dict(personaje='bruno')),
                dict(opciones=dict(modo='confusion',punto=[.5,.5])),
                dict(opciones=dict(modo='sorpresa',personaje='bruno',punto=[.5,.5]))):
            d=referencia_enfasis();d['graficos'][0].update(cambio)
            with self.subTest(cambio=cambio),self.assertRaises(ValueError):self.validar(d)
        d=referencia_enfasis();del d['graficos'][0]['fin']
        self.assertAlmostEqual(self.validar(d)['graficos'][0]['fin'],1.1)

    def test_enfasis_pulso_no_se_repite_y_refuerza_tamano(self):
        import subprocess
        programa='''
            import assert from 'node:assert';
            const {pulsoEnfasis:p}=await import(process.argv[1]);
            for(const fps of [24,30,60])for(const dur of [.2,.3,.4]){
                for(const t of [-1,0,dur,dur+1,20])assert.equal(p(t,dur,fps).alpha,0);
                const medio=p(dur/2,dur,fps);
                assert.equal(medio.alpha,1);assert.ok(medio.escala>1);
                assert.ok(p(.01,dur,fps).alpha<medio.alpha);
                assert.ok(p(dur-.01,dur,fps).alpha<medio.alpha);
                assert.ok(p(.01,dur,fps,true).alpha>=p(.01,dur,fps).alpha);
            }
        '''
        subprocess.run(['node','--input-type=module','-e',programa,
            (stickman.RAIZ/'motores/stickman/enfasis.js').as_uri()],check=True,capture_output=True,text=True)

    @unittest.skipUnless(REAL,'usa --real para los seis acentos y su pulso en cámara general/corta')
    def test_enfasis_render_real(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        def comprobar(nav,destino=None):
            r=nav.evaluar('''(() => {
                const P=CanvasRenderingContext2D.prototype,stroke=P.stroke;
                const frames=[];let trazos;
                P.stroke=function(...a){
                    if(this.strokeStyle==='#ffcc44'&&this.globalAlpha>0)trazos.push(this.globalAlpha);
                    return stroke.apply(this,a);
                };
                try{for(const t of [.79,.83,.94,1.06,1.11,2]){
                    trazos=[];window.pintar(t);frames.push([...trazos]);
                }}finally{P.stroke=stroke;}
                window.pintar(.94);return frames;
            })()''')
            self.assertEqual([len(f) for f in r],[0,cuenta,cuenta,cuenta,0,0])
            self.assertLess(r[1][0],r[2][0])
            self.assertLess(r[3][0],r[2][0])
            return original(nav,destino)
        for modo,cuenta in [('sorpresa',3),('sobresalto',3),('descubrimiento',5),('enfado',3),('confusion',2),('impacto',6)]:
            for plano in ('conjunto','primer_plano'):
                with self.subTest(modo=modo,plano=plano),patch.object(p8_render.Navegador,'capturar',comprobar):
                    stickman.renderizar(self.base,self.validar(referencia_enfasis(modo,plano)),4,
                        str(Path(TEMP.name)/f'enfasis-{modo}-{plano}.png'),salida=(960,540))

    def test_palma_abierta_mezcla_y_fin_sin_mutar_kit(self):
        import subprocess
        d=stickman.escena(dict(personajes=[dict(id='bruno',claves=[dict(t=0,pose='palmUp')])]),4,self.reparto)
        self.assertEqual(d['personajes'][0]['claves'][0]['pose'],'palmUp')
        programa='''
            import assert from 'node:assert/strict';
            const {poseActuada,aperturaPalma}=await import(process.argv[1]);
            const {POSES}=await import(process.argv[2]);
            const original=JSON.stringify(POSES);
            const keys=[{t:0,pose:'relaxed'},{t:1,pose:'palmUp'},{t:3,pose:'relaxed'}];
            assert.equal(aperturaPalma(.9,keys,.2),0);
            assert.ok(aperturaPalma(1.1,keys,.2)>0&&aperturaPalma(1.1,keys,.2)<1);
            assert.equal(aperturaPalma(2,keys,.2),1);
            assert.ok(aperturaPalma(3.1,keys,.2)>0&&aperturaPalma(3.1,keys,.2)<1);
            assert.equal(aperturaPalma(3.5,keys,.2),0);
            const p=poseActuada(2,keys,.2);
            assert.ok(p.hF[0]>p.eF[0]&&p.eF[0]>p.sh[0]);
            assert.ok(p.hB[1]>p.sh[1]);
            assert.deepEqual(poseActuada(3.5,keys,.2),POSES.relaxed);
            assert.equal(JSON.stringify(POSES),original);
        '''
        subprocess.run(['node','--input-type=module','-e',programa,
            (stickman.RAIZ/'motores/stickman/actuacion.js').as_uri(),
            (stickman.KIT/'engine/rig2d.js').as_uri()],check=True,capture_output=True,text=True)

    @unittest.skipUnless(REAL,'usa --real para palma visible en Classic y familias')
    def test_palma_render_real(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        def comprobar(nav,destino=None):
            # Comprobar puntas, huecos y pulgar en el espacio de la figura.
            r=nav.evaluar('''(() => {
                window.pintar(0);
                const c=document.querySelector('canvas'),g=c.getContext('2d');
                const pix=(x,y)=>Array.from(g.getImageData(Math.round(x),Math.round(y),1,1).data);
                // Pies (.4,.88), escala 3, lienzo 960x540 sin cámara adicional.
                const px=(x,y)=>pix(384+x*1.5,475.2+y*1.5);
                return {dedo:px(90,-167),hueco:px(90,-173),pulgar:px(63,-171),aire:px(57,-178)};
            })()''')
            self.assertNotEqual(r['dedo'],r['hueco'])
            self.assertNotEqual(r['pulgar'],r['aire'])
            return original(nav,destino)
        for familia in ('classic','rubber','bean','geometric'):
            diseno=dict(self.base,familia=familia,ropa='hoodie',color='#32bc77',contorno='#f4e5b8')
            datos=dict(ambiente='day',decorado='vacio',atmosfera='ninguna',personajes=[
                dict(id='bruno',x=.4,y=.88,escala=3,actuacion=dict(respiracion=0),
                    claves=[dict(t=0,pose='palmUp')])])
            with self.subTest(familia=familia),patch.object(p8_render.Navegador,'capturar',comprobar):
                stickman.renderizar(diseno,stickman.escena(datos,4,{'bruno':diseno}),4,
                    str(Path(TEMP.name)/f'palma-{familia}.png'),salida=(960,540))

    def test_rascar_cabeza_contacto_ciclo_y_fin_sin_mutar_kit(self):
        import subprocess
        d=self.validar(referencia_rascado())
        self.assertEqual(stickman.escena(d,4,self.reparto),d)
        programa='''
            import assert from 'node:assert/strict';
            const {poseActuada,POSES_ACTUACION}=await import(process.argv[1]);
            const {POSES}=await import(process.argv[2]);
            const original=JSON.stringify(POSES_ACTUACION),kit=JSON.stringify(POSES);
            const keys=[{t:0,pose:'relaxed'},{t:.4,pose:'scratchHead'},{t:2.8,pose:'relaxed'}];
            for(const [cabeza,cuerpo] of [[1,1],[1.4,.8],[.8,1.3]]){
                const muestras=[.8,.87,.94,1.01].map(t=>poseActuada(t,keys,.2,cabeza,cuerpo));
                for(const p of muestras){
                    const dx=(p.hF[0]-p.head[0])/cabeza,dy=(p.hF[1]-p.head[1])*cuerpo/cabeza;
                    assert.ok(Math.abs(Math.hypot(dx,dy)-28)<1e-9);
                    assert.ok(p.hB[1]>p.sh[1]);
                    assert.deepEqual(p.fF,muestras[0].fF);
                    assert.deepEqual(p.hB,muestras[0].hB);
                }
                assert.notDeepEqual(muestras[0].hF,muestras[1].hF);
                assert.ok(Math.hypot(...muestras[0].hF.map((v,i)=>v-muestras[1].hF[i]))<8);
                assert.deepEqual(poseActuada(3.5,keys,.2,cabeza,cuerpo),POSES.relaxed);
            }
            assert.equal(JSON.stringify(POSES_ACTUACION),original);
            assert.equal(JSON.stringify(POSES),kit);
        '''
        subprocess.run(['node','--input-type=module','-e',programa,
            (stickman.RAIZ/'motores/stickman/actuacion.js').as_uri(),
            (stickman.KIT/'engine/rig2d.js').as_uri()],check=True,capture_output=True,text=True)

    @unittest.skipUnless(REAL,'usa --real para rascado visible en Classic y familias')
    def test_rascado_render_real(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        def comprobar(nav,destino=None):
            r=nav.evaluar('''(() => {
                const c=document.querySelector('canvas'),g=c.getContext('2d');
                const frame=t=>{window.pintar(t);return g.getImageData(0,0,c.width,c.height).data;};
                const a=frame(.8),b=frame(.87);let cambios=0,piernas=0;
                for(let i=0;i<a.length;i+=4)if(a[i]!==b[i]||a[i+1]!==b[i+1]||a[i+2]!==b[i+2]){
                    cambios++;if(Math.floor(i/4/c.width)>c.height*.7)piernas++;
                }
                window.pintar(1);return {cambios,piernas};
            })()''')
            self.assertGreater(r['cambios'],20)
            self.assertEqual(r['piernas'],0)
            return original(nav,destino)
        for familia in ('classic','rubber','bean','geometric'):
            diseno=dict(self.reparto['bruno'],familia=familia,ropa='hoodie',accesorio='spiky')
            if familia!='classic':diseno.update(cabeza=1.2,cuerpo=.9)
            with self.subTest(familia=familia),patch.object(p8_render.Navegador,'capturar',comprobar):
                stickman.renderizar(diseno,stickman.escena(referencia_rascado(),4,{'bruno':diseno}),4,
                    str(Path(TEMP.name)/f'rascado-{familia}.png'),salida=(960,540))

    def test_portazo_contrato_y_tiempos(self):
        d=self.validar(referencia_portazo())
        self.assertEqual(stickman.escena(d,4,self.reparto),d)
        for cierre in (dict(inicio=.5,fin=.5),dict(inicio=.7,fin=.6),dict(inicio=0,fin=5),dict(inicio=0)):
            malo=referencia_portazo();malo['objetos'][0]['cierre']=cierre
            with self.subTest(cierre=cierre),self.assertRaises(ValueError):
                self.validar(malo)
        malo=referencia_portazo();malo['objetos'][0]['apertura']=float('nan')
        with self.assertRaises(ValueError):self.validar(malo)

    @unittest.skipUnless(REAL,'usa --real para giro de puerta, impacto y estabilización en Canvas')
    def test_portazo_render_real(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        def comprobar(navegador,destino=None):
            r=navegador.evaluar('''(() => {
                const P=CanvasRenderingContext2D.prototype,fill=P.fill,rect=P.fillRect,stroke=P.stroke;
                const frames=[];let hoja,marcos,puntos,rayos=0;
                const move=P.moveTo,line=P.lineTo;
                P.moveTo=function(x,y){puntos=[[x,y]];return move.call(this,x,y);};
                P.lineTo=function(x,y){puntos?.push([x,y]);return line.call(this,x,y);};
                P.fill=function(...a){if(this.fillStyle==='#795538')hoja=puntos?.map(p=>[...p]);return fill.apply(this,a);};
                P.fillRect=function(...a){if(this.fillStyle==='#a18f73')marcos=a;return rect.apply(this,a);};
                P.stroke=function(...a){if(this.strokeStyle==='#ffc052')rayos++;return stroke.apply(this,a);};
                try{for(const t of [0,.6,.65,.67,.71,1.3,3]){
                    rayos=0;window.pintar(t);frames.push({t,hoja,marcos,rayos});
                }}finally{Object.assign(P,{fill,fillRect:rect,moveTo:move,lineTo:line,stroke});}
                return frames;
            })()''')
            abierta,cerrando,impacto,vibra1,vibra2,estable,final=r
            self.assertEqual(abierta['marcos'],estable['marcos'])
            for f in r:
                self.assertAlmostEqual(f['hoja'][0][0],abierta['hoja'][0][0])
                self.assertEqual(f['hoja'][0][1],abierta['hoja'][0][1])
            ancho=lambda f:abs(f['hoja'][1][0]-f['hoja'][0][0])
            self.assertLess(ancho(abierta),ancho(cerrando))
            self.assertLess(ancho(cerrando),ancho(impacto))
            self.assertNotEqual(abierta['hoja'][0][1],abierta['hoja'][1][1])
            self.assertEqual(impacto['hoja'][0][1],impacto['hoja'][1][1])
            self.assertNotEqual(vibra1['hoja'],vibra2['hoja'])
            self.assertEqual(estable['hoja'],final['hoja'])
            self.assertEqual([f['rayos'] for f in r],[0,0,6,6,6,0,0])
            return original(navegador,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            for bisagra in ('izquierda','derecha'):
                d=referencia_portazo();d['objetos'][0]['bisagra']=bisagra
                stickman.renderizar(self.base,self.validar(d),4,
                    str(Path(TEMP.name)/f'portazo-{bisagra}.png'),salida=(960,540))

    def test_documentos_nuevos_y_aura_tienen_contrato_sin_mutar_historicos(self):
        d=stickman.escena(referencia_documento_luminoso(),4,{})
        self.assertEqual(stickman.escena(d,4,{}),d)
        antiguo=stickman.escena(grafica('documento',dict(titulo='INFORME',filas=['Dato'])),4,{})
        self.assertNotIn('estilo',antiguo['graficos'][-1]['opciones'])
        self.assertNotIn('resplandor',antiguo['realizacion'])
        nuevo=copy.deepcopy(antiguo)
        editorial.preparar_documentos_nuevos(nuevo,[1920,1080])
        self.assertEqual(nuevo['graficos'][-1]['opciones']['estilo'],'neon')
        nuevo['objetos']=[dict(tipo='texto',texto='EXCLUIDO',x=.7,y=.5,w=400,h=100)]
        with self.assertRaisesRegex(ValueError,'invade la hoja'):
            editorial.preparar_documentos_nuevos(stickman.escena(nuevo,4,{}),[1920,1080])
        for aura in (dict(color='#ffad32',intensidad=1.1),dict(color='#ffad32'),dict(intensidad=.8)):
            d=narrativa(self.base);d['personajes'][0]['actuacion']=dict(aura=aura)
            with self.subTest(aura=aura),self.assertRaises(ValueError):
                stickman.escena(d,4,self.reparto)
        d=narrativa(self.base);d['personajes'][0]['actuacion']=dict(aura=dict(color='#ffad32',intensidad=.85))
        d=stickman.escena(d,4,self.reparto)
        self.assertEqual(stickman.escena(d,4,self.reparto),d)

    @unittest.skipUnless(REAL,'usa --real para documento luminoso sin superposiciones')
    def test_documento_luminoso_render_real(self):
        from pasos import p8_render
        capturar=p8_render.Navegador.capturar
        def comprobar(navegador,destino=None):
            r=navegador.evaluar('''(() => {
                const P=CanvasRenderingContext2D.prototype,original=P.strokeText,rotulos={};
                P.strokeText=function(s,x,y,...a){
                    if(['PSICÓPATA','SOCIÓPATA'].includes(s)){
                        const m=this.getTransform(),p=m.transformPoint({x,y});
                        rotulos[s]={x:p.x,w:this.measureText(s).width*Math.hypot(m.a,m.b)};
                    }return original.call(this,s,x,y,...a);
                };
                try{window.pintar(3);}finally{P.strokeText=original;}
                const c=document.querySelector('canvas'),g=c.getContext('2d'),d=g.getImageData(0,0,c.width,c.height).data;
                let turquesa=0,amarillo=0;
                for(let i=0;i<d.length;i+=4){
                    if(d[i]<150&&d[i+1]>150&&d[i+2]>150)turquesa++;
                    if(d[i]>200&&d[i+1]>130&&d[i+2]<100)amarillo++;
                }return {rotulos,w:c.width,turquesa,amarillo};
            })()''')
            izq=r['rotulos']['PSICÓPATA'];der=r['rotulos']['SOCIÓPATA']
            self.assertGreater(izq['x']-izq['w']/2,0)
            self.assertLess(izq['x']+izq['w']/2,r['w']*.32)
            self.assertGreater(der['x']-der['w']/2,r['w']*.68)
            self.assertLess(der['x']+der['w']/2,r['w'])
            self.assertGreater(r['turquesa'],1500)
            self.assertGreater(r['amarillo'],1000)
            return capturar(navegador,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            stickman.renderizar(self.base,stickman.escena(referencia_documento_luminoso(),4,{}),4,
                str(Path(TEMP.name)/'documento-luminoso.png'),salida=(960,540))

    @unittest.skipUnless(REAL,'usa --real para comprobar aura local y fidelidad de la figura')
    def test_aura_sigue_silueta_sin_recolorear_personaje(self):
        from pasos import p8_render
        capturar=p8_render.Navegador.capturar
        d=narrativa(self.base);d['realizacion'].update(color_fiel=True,grano=0,vineta=0)
        d['personajes']=d['personajes'][:1]
        d['personajes'][0].update(x=.5,actuacion=dict(aura=dict(color='#ffad32',intensidad=.9)))
        def comprobar(navegador,destino=None):
            r=navegador.evaluar('''(() => {
                const c=document.querySelector('canvas'),g=c.getContext('2d'),actor=window.STICKMAN.escena.personajes[0];
                const imagen=()=>{window.pintar(.5);return g.getImageData(0,0,c.width,c.height).data;};
                const aura=actor.actuacion.aura,con=imagen();actor.actuacion.aura=null;const sin=imagen();actor.actuacion.aura=aura;
                let iluminados=0,lejanos=0,interior=0;
                for(let y=0;y<c.height;y++)for(let x=0;x<c.width;x++){
                    const i=(y*c.width+x)*4,d=Math.abs(con[i]-sin[i])+Math.abs(con[i+1]-sin[i+1])+Math.abs(con[i+2]-sin[i+2]);
                    if(d>20)iluminados++;
                    if((x<c.width*.1||x>c.width*.9)&&d>3)lejanos++;
                    if(x>c.width*.495&&x<c.width*.505&&y>c.height*.54&&y<c.height*.58&&d>3)interior++;
                }window.pintar(.5);return {iluminados,lejanos,interior};
            })()''')
            self.assertGreater(r['iluminados'],1500)
            self.assertEqual(r['lejanos'],0)
            self.assertEqual(r['interior'],0)
            return capturar(navegador,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            stickman.renderizar(self.base,stickman.escena(d,4,self.reparto),4,
                str(Path(TEMP.name)/'aura-silueta.png'),salida=(960,540))

    @unittest.skipUnless(REAL,'usa --real para comprobar resplandor por defecto y apagado explícito')
    def test_resplandor_selectivo_por_defecto_respeta_neon_cero(self):
        from pasos import p8_render
        d=grafica('badge',dict(str='ACENTO',x=960,y=220,color='#ffbc32'))
        d['graficos']=d['graficos'][1:]
        d['realizacion'].update(resplandor=True,color_fiel=True,grano=0,vineta=0)
        d['objetos']=[dict(tipo='texto',texto='RÓTULO',x=.3,y=.5,w=600,h=160,fuente=120,color='#ffbf32'),
            dict(tipo='redondeado',x=.7,y=.5,w=280,h=30,color='#62dede')]
        capturar=p8_render.Navegador.capturar
        def comprobar(navegador,destino=None):
            r=navegador.evaluar('''(() => {
                const s=window.STICKMAN.escena,c=document.querySelector('canvas');
                const imagen=()=>{window.pintar(2);return c.toDataURL();};
                const con=imagen();s.realizacion.resplandor=false;const sin=imagen();
                s.realizacion.resplandor=true;[...s.objetos,...s.graficos].forEach(o=>o.neon=0);const apagado=imagen();
                return {visible:con!==sin,apagado:apagado===sin};
            })()''')
            self.assertEqual(r,dict(visible=True,apagado=True))
            return capturar(navegador,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            stickman.renderizar(self.base,stickman.escena(d,4,{}),4,
                str(Path(TEMP.name)/'resplandor-por-defecto.png'),salida=(960,540))

    def test_actuacion_y_etiquetas_con_salida(self):
        d=stickman.escena(referencia_interaccion(self.base),4,self.reparto)
        self.assertEqual(stickman.escena(d,4,self.reparto),d)
        for campo,valor in [('transito',1),('texto',''),('texto','a\nb\nc\nd'),('h',20)]:
            roto=copy.deepcopy(d);roto['objetos'][1][campo]=valor
            with self.subTest(campo=campo,valor=valor),self.assertRaises(ValueError):
                stickman.escena(roto,4,self.reparto)

    @unittest.skipUnless(REAL,'usa --real para comprobar texto legible en marcos oscuros')
    def test_etiqueta_oscura_elige_tinta_legible_y_admite_colores_independientes(self):
        from pasos import p8_render
        d=grafica('badge',{})
        d['graficos']=[]
        d['realizacion'].update(tipografia='redondeada',color_fiel=True,grano=0,vineta=0)
        d['objetos']=[dict(tipo='etiqueta',texto='¿En qué se\ndiferencian?',color='#12263f',
            x=.5,y=.5,w=800,h=240,fuente=100)]
        capturar=p8_render.Navegador.capturar
        def comprobar(navegador,destino=None):
            r=navegador.evaluar('''(() => {
                const s=window.STICKMAN.escena,o=s.objetos[0],c=document.querySelector('canvas');
                const imagen=()=>{window.pintar(2);return c.toDataURL();};
                const automatico=imagen();o.tinta='#fff1dc';const claro=imagen();
                o.fondo='#fff1dc';o.tinta='#12263f';const inverso=imagen();
                return {legible:automatico===claro,separados:inverso!==claro};
            })()''')
            self.assertEqual(r,dict(legible=True,separados=True))
            return capturar(navegador,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            stickman.renderizar(self.base,stickman.escena(d,4,{}),4,
                str(Path(TEMP.name)/'contraste-etiqueta.png'),salida=(960,540))
        d['objetos'][0].update(tinta='#fff1dc',fondo='#12263f')
        escena=stickman.escena(d,4,{})
        self.assertEqual(stickman.escena(escena,4,{}),escena)

    @unittest.skipUnless(REAL,'usa --real para comprobar lista progresiva limpia y colores')
    def test_lista_numerada_limpia_conserva_colores_y_espacio_para_el_actor(self):
        from pasos import p8_render
        capturar=p8_render.Navegador.capturar
        def comprobar(navegador,destino=None):
            r=navegador.evaluar('''(() => {
                const c=document.querySelector('canvas'),P=CanvasRenderingContext2D.prototype;
                const original=P.strokeText,arc=P.arc;let textos=[],caras=[];
                P.strokeText=function(str,x,y,...a){
                    const m=this.getTransform(),p=m.transformPoint({x,y});
                    if(this.globalAlpha>.1)textos.push({str,x:p.x,y:p.y,w:this.measureText(str).width*Math.hypot(m.a,m.b),color:this.fillStyle});
                    return original.call(this,str,x,y,...a);
                };
                P.arc=function(x,y,r,a,b,...rest){
                    const m=this.getTransform(),radio=r*Math.hypot(m.a,m.b);
                    if(this.canvas===c&&radio>30&&b-a>6){const p=m.transformPoint({x,y});caras.push({x:p.x,r:radio});}
                    return arc.call(this,x,y,r,a,b,...rest);
                };
                try{
                    window.pintar(.7);const primera=textos.map(t=>t.str);textos=[];caras=[];
                    window.pintar(2.5);return {primera,textos,cara:caras.sort((a,b)=>b.r-a.r)[0]};
                }finally{P.strokeText=original;P.arc=arc;}
            })()''')
            self.assertIn('¿En qué se diferencian?',r['primera'])
            self.assertNotIn('¿Qué pregunta te protege?',r['primera'])
            textos={t['str']:t for t in r['textos']}
            self.assertEqual(textos['1. ']['color'],'#fff1dc')
            self.assertEqual(textos['2. ']['color'],'#ffcb52')
            for numero,frase in [('1. ','¿En qué se diferencian?'),('2. ','¿Qué pregunta te protege?')]:
                self.assertEqual(textos[frase]['color'],'#fff1dc')
                self.assertAlmostEqual(textos[numero]['y'],textos[frase]['y'])
                self.assertGreater(textos[frase]['x'],textos[numero]['x'])
                self.assertLess(textos[frase]['x']+textos[frase]['w'],r['cara']['x']-r['cara']['r'])
            return capturar(navegador,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            stickman.renderizar(self.base,stickman.escena(referencia_lista_limpia(self.base),4,self.reparto),4,
                str(Path(TEMP.name)/'lista-limpia.png'),salida=(960,540))

    @unittest.skipUnless(REAL,'usa --real para comprobar rótulos junto al primer plano')
    def test_rotulos_entran_y_caben_junto_al_rostro_sin_perder_primer_plano(self):
        from pasos import p8_render
        capturar=p8_render.Navegador.capturar
        def comprobar(navegador,destino=None):
            r=navegador.evaluar('''(() => {
                const canvas=document.querySelector('canvas'),P=CanvasRenderingContext2D.prototype;
                const arc=P.arc,strokeText=P.strokeText;let letras=[],caras=[];
                P.arc=function(x,y,r,a,b,...rest){
                    const m=this.getTransform(),radio=r*Math.hypot(m.a,m.b);
                    if(this.canvas===canvas&&radio>30&&b-a>=Math.PI*1.99){
                        const p=m.transformPoint({x,y});
                        caras.push({x:p.x,y:p.y,r:radio});
                    }return arc.call(this,x,y,r,a,b,...rest);
                };
                P.strokeText=function(s,x,y,...rest){
                    if(s==='DIFÍCIL'){
                        const m=this.getTransform(),p=m.transformPoint({x,y}),w=this.measureText(s).width*Math.hypot(m.a,m.b);
                        letras.push({x:p.x,y:p.y,w});
                    }return strokeText.call(this,s,x,y,...rest);
                };
                try{
                    const toma=t=>{letras=[];caras=[];window.pintar(t);
                        return {texto:letras.at(-1),cara:caras.sort((a,b)=>b.r-a.r)[0]};};
                    const entrada=toma(.25),lectura=toma(1.1),despues=toma(2);
                    return {entrada,lectura,despues,w:canvas.width,h:canvas.height};
                }finally{P.arc=arc;P.strokeText=strokeText;}
            })()''')
            texto=r['lectura']['texto'];cara=r['lectura']['cara']
            self.assertGreater(texto['x']-texto['w']/2,0)
            self.assertLess(texto['x']+texto['w']/2,r['w'])
            self.assertLess(texto['x']+texto['w']/2,cara['x']-cara['r'])
            self.assertGreater(cara['r'],r['h']*(.18 if encuadre=='primer_plano' else .1))
            self.assertLess(r['entrada']['texto']['x'],texto['x'])
            self.assertAlmostEqual(r['entrada']['cara']['x'],cara['x'],delta=3)
            self.assertAlmostEqual(r['despues']['cara']['x'],cara['x'],delta=3)
            return capturar(navegador,destino)
        for encuadre in ('primer_plano','medio'):
            for tipo in ('texto','etiqueta'):
                with self.subTest(encuadre=encuadre,tipo=tipo),patch.object(p8_render.Navegador,'capturar',comprobar):
                    d=stickman.escena(referencia_rostro_rotulado(self.base,encuadre,tipo),4,self.reparto)
                    stickman.renderizar(self.base,d,4,str(Path(TEMP.name)/f'rostro-{encuadre}-{tipo}.png'),salida=(960,540))

    @unittest.skipUnless(REAL,'usa --real para comprobar actuación y salida en Canvas')
    def test_interaccion_render_real(self):
        from pasos import p8_render
        capturar=p8_render.Navegador.capturar
        def comprobar(navegador,destino=None):
            r=navegador.evaluar('''(() => {
                const s=window.STICKMAN.escena,canvas=document.querySelector('canvas');
                const imagen=t=>{window.pintar(t);return canvas.toDataURL();};
                const visible=imagen(1.8),salida=imagen(3.8),etiqueta=s.objetos.pop();
                const sinEtiqueta=imagen(1.8),fuera=imagen(3.8);s.objetos.push(etiqueta);
                const actuando=imagen(1.8),poses=s.personajes.map(c=>c.claves[0].pose);
                s.personajes.forEach(c=>c.claves[0].pose='stand');const rigido=imagen(1.8);
                s.personajes.forEach((c,i)=>c.claves[0].pose=poses[i]);window.pintar(1.8);
                return {visible:visible!==sinEtiqueta,sale:salida===fuera,actua:actuando!==rigido};
            })()''')
            self.assertEqual(r,dict(visible=True,sale=True,actua=True))
            return capturar(navegador,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            stickman.renderizar(self.base,stickman.escena(referencia_interaccion(self.base),4,self.reparto),
                4,str(Path(TEMP.name)/'interaccion.png'),salida=(960,540))

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

    def test_paletas_y_neon_selectivo_son_datos_validados_y_opcionales(self):
        for paleta in editorial.PALETAS:
            d=stickman.escena(escena_neon(paleta),4,{})
            self.assertEqual(d['realizacion']['paleta'],paleta)
            self.assertEqual(d['graficos'][-1]['neon'],.35)
            self.assertEqual(d['objetos'][1]['neon'],0)
            self.assertEqual(stickman.escena(d,4,{}),d)
        historico=stickman.escena(grafica('bigLine',{}),4,{})
        self.assertNotIn('paleta',historico['realizacion'])
        self.assertNotIn('neon',historico['graficos'][-1])
        for d in (dict(realizacion=dict(paleta='inventada')),
                dict(graficos=[dict(tipo='bigLine',neon=1.1)]),
                dict(objetos=[dict(tipo='circulo',neon=-.1)]),
                dict(objetos=[dict(tipo='texto',neon=True)]),
                dict(efectos_visuales=[dict(tipo='dust',neon=.3)])):
            with self.subTest(d=d),self.assertRaises(ValueError):
                stickman.escena(d,4,{})
        prompt=editorial.instruccion()
        for nombre in ('Ember Forge','Arctic Glass','Sakura Bloom','Retro Print','neon:.2–.4'):
            self.assertIn(nombre,prompt)

    @unittest.skipUnless(REAL,'usa --real para comprobar halo, nitidez y paletas en Canvas')
    def test_neon_real_preserva_interiores_y_colores_y_se_puede_apagar(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        for paleta in editorial.PALETAS:
            d=escena_neon(paleta)
            d['realizacion']['vineta']=0
            # Incluye un vector con tinta distinta al acento para comprobar la máscara.
            d['utileria']={'prueba':dict(concepto='silueta',nombre='Silueta',descripcion='Cuadrado de prueba',
                ancho=100,alto=100,partes=[dict(id='silueta',pivote=[50,50],formas=[
                dict(tipo='rectangulo',x=0,y=0,w=100,h=100,radio=0,relleno='#b58b60',trazo=None)])])}
            d['objetos'].append(dict(tipo='vector',recurso='prueba',x=.7,y=.8,w=180,h=90,neon=.3,
                color=editorial.PALETAS[paleta]['acento']))
            d=stickman.escena(d,4,{})
            def comprobar(nav,destino=None):
                resultado=nav.evaluar('''(() => {
                  const d=window.STICKMAN.escena,ctx=document.querySelector('canvas').getContext('2d');
                  const items=[...d.objetos,...d.graficos],valores=items.map(o=>o.neon);
                  const pixels=()=>ctx.getImageData(0,0,ctx.canvas.width,ctx.canvas.height).data;
                  items.forEach(o=>o.neon=0);window.pintar(2);const base=pixels();
                  items.forEach((o,i)=>o.neon=valores[i]);window.pintar(2);const neon=pixels();
                  const rgb=COLOR_ESPERADO.match(/[a-f0-9]{2}/gi).map(n=>parseInt(n,16));
                  let diferentes=0,madera=0,maderaIgual=0,acento=0,acentoIgual=0,amarillo=0;
                  for(let i=0;i<base.length;i+=4){
                    if(neon[i]===255&&neon[i+1]===203&&neon[i+2]===82)amarillo++;
                    if(base[i]!==neon[i]||base[i+1]!==neon[i+1]||base[i+2]!==neon[i+2])diferentes++;
                    if(base[i]===181&&base[i+1]===139&&base[i+2]===96){
                      madera++;if(base[i]===neon[i]&&base[i+1]===neon[i+1]&&base[i+2]===neon[i+2])maderaIgual++;
                    }
                    if(base[i]===rgb[0]&&base[i+1]===rgb[1]&&base[i+2]===rgb[2]){
                      acento++;if(base[i]===neon[i]&&base[i+1]===neon[i+1]&&base[i+2]===neon[i+2])acentoIgual++;
                    }
                  }
                  window.pintar(2);const repetida=pixels();let estable=true;
                  for(let i=0;i<neon.length;i++)if(neon[i]!==repetida[i]){estable=false;break;}
                  return {diferentes,madera,maderaIgual,acento,acentoIgual,amarillo,estable};
                })()'''.replace('COLOR_ESPERADO',json.dumps(editorial.PALETAS[paleta]['acento'])))
                self.assertGreater(resultado['diferentes'],300)
                self.assertGreater(resultado['madera'],100)
                self.assertEqual(resultado['madera'],resultado['maderaIgual'])
                self.assertGreater(resultado['acento'],300)
                self.assertEqual(resultado['acento'],resultado['acentoIgual'])
                self.assertTrue(resultado['estable'])
                if paleta=='arctic':
                    self.assertGreater(resultado['amarillo'],100)
                return original(nav,destino)
            with self.subTest(paleta=paleta),patch.object(p8_render.Navegador,'capturar',comprobar):
                stickman.renderizar(self.base,d,4,str(Path(TEMP.name)/f'neon-{paleta}.png'),salida=(960,540))

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
        invalidos.extend([dict(realizacion=dict(particulas=1)),dict(realizacion=dict(malla='sí')),
            dict(realizacion=dict(escenografia_detallada='sí')),
            dict(realizacion=dict(escenario=dict(id='teatro',tipo='teatro',atril_x=2))),
            grafica('capitulo',dict(numero=0,titulo='Un punto',estilo='arctic')),
            grafica('capitulo',dict(numero=1.2,titulo='Un punto',estilo='arctic')),
            grafica('capitulo',dict(numero=1,titulo='',estilo='arctic')),
            dict(realizacion=dict(desfase_ambiente=-1)),
            grafica('bocadillo',dict(personaje='inventado',texto='Hola')),
            grafica('bocadillo',dict(personaje='ana',texto='')),
            grafica('bocadillo',dict(personaje='ana',texto='Hola',modo='grito')),
            dict(graficos=[dict(tipo='bocadillo',opciones=dict(personaje='ana',texto='Hola'))])])
        for d in invalidos:
            with self.subTest(d=d),self.assertRaises(ValueError):
                stickman.escena(d,4,self.reparto)

    def test_expresiones_nuevas_necesitan_motivo_actual_sin_contagiar_emociones(self):
        from pasos import expresiones_stickman as faciales
        casos=[('El vecino gesticula con los brazos y un halo naranja lo envuelve.', 'angry'),
            ('La compañera sigue tecleando sin levantar la vista mientras pasa el jefe.', 'determined')]
        for descripcion,expresion in casos:
            entrega=narrativa(self.base)
            entrega['personajes']=entrega['personajes'][:1]
            entrega['personajes'][0]['expresion']=expresion
            # La lectura de planes pagados no exige un campo nuevo ni los neutraliza.
            antigua=stickman.escena(entrega,4,self.reparto)
            self.assertEqual(antigua['personajes'][0]['expresion'],expresion)
            neutral=copy.deepcopy(entrega)
            neutral['personajes'][0]['expresion']='neutral'
            e=dict(t_in=0,t_out=4,narracion='Una acción.',descripcion_visual=descripcion,continuidad_bloque=dict(anterior=dict(contenido=antigua)))
            with self.subTest(expresion=expresion),patch.dict(os.environ,ESTUDIO_SIMULAR='0'), \
                    patch.object(stickman,'_consultar',side_effect=[entrega,neutral]) as consulta:
                nueva=stickman.generar_escena(e,self.base,self.reparto,None,lambda *a:None)
            self.assertEqual(consulta.call_count,2)
            self.assertIn('motivo_expresion',consulta.call_args.args[0])
            self.assertIn('DIRECCIÓN FACIAL POR PERSONAJE',consulta.call_args_list[0].args[0])
            self.assertEqual(nueva['personajes'][0]['expresion'],'neutral')
            self.assertTrue(nueva['realizacion']['expresiones_fieles'])
            # Una edición histórica conserva las expresiones y las bocas, pero
            # recibe siempre el dibujo corregido de cejas.
            e['indicaciones_usuario']=dict(edicion_stickman=dict(ancla=e['narracion'],contenido=antigua))
            with patch.dict(os.environ,ESTUDIO_SIMULAR='0'),patch.object(stickman,'_consultar',return_value=entrega):
                retoque=stickman.generar_escena(e,self.base,self.reparto,None,lambda *a:None)
            self.assertEqual(retoque['personajes'][0]['expresion'],expresion)
            self.assertNotIn('expresiones_fieles',retoque['realizacion'])
            self.assertTrue(retoque['realizacion']['cejas_fieles'])
        descripcion='Ana frunce el ceño enfadada; Bruno sonríe tranquilo.'
        entrega=narrativa(self.base)
        entrega['personajes'][0].update(expresion='angry',motivo_expresion='Ana frunce el ceño enfadada',
            claves=[dict(t=0,pose='stand'),dict(t=1,pose='point',expresion='angry'),
                dict(t=2,expresion='neutral'),dict(t=3,expresion='angry',motivo_expresion='Ana frunce el ceño enfadada')])
        entrega['personajes'][1].update(expresion='smile',motivo_expresion='Bruno sonríe tranquilo')
        nueva=stickman.escena(entrega,4,self.reparto)
        faciales.validar(nueva,descripcion)
        self.assertEqual(stickman.escena(nueva,4,self.reparto)['personajes'],nueva['personajes'])
        for campo in (nueva['personajes'][0],nueva['personajes'][0]['claves'][-1]):
            motivo=campo['motivo_expresion']
            campo['motivo_expresion']='Ana está preocupada'
            with self.assertRaisesRegex(ValueError,'cita literal'):
                faciales.validar(nueva,descripcion)
            campo['motivo_expresion']=motivo
        with patch.dict(os.environ,ESTUDIO_SIMULAR='0'),patch.object(stickman,'_consultar',return_value=entrega):
            generada=stickman.generar_escena(dict(t_in=0,t_out=4,descripcion_visual=descripcion),
                self.base,self.reparto,None,lambda *a:None)
        self.assertEqual([c['expresion'] for c in generada['personajes']],['angry','smile'])
        tardia=copy.deepcopy(nueva)
        tardia['personajes'][1]['claves'].append(dict(t=3,expresion='worried'))
        with self.assertRaisesRegex(ValueError,'bruno, clave.*worried'):
            faciales.validar(tardia,descripcion)
        quieta=copy.deepcopy(entrega)
        quieta['personajes']=quieta['personajes'][:1]
        quieta['personajes'][0]['claves']=[dict(t=0,pose='stand'),dict(t=2,motivo_expresion=descripcion)]
        with self.assertRaisesRegex(ValueError,'estática'):
            stickman.validar_puesta_en_escena(quieta,4,self.reparto,[1920,1080])

    def test_editar_enfado_heredado_activa_cejas_sin_depender_del_proveedor(self):
        original=narrativa(self.base)
        original['personajes'][0]['claves']=[dict(t=t,pose=pose,expresion='neutral')
            for t,pose in [(0,'explain'),(.7,'pointUp'),(1.4,'explain'),(4,'point')]]
        original['personajes'][0]['expresion']='neutral'
        entrega=copy.deepcopy(original)
        entrega['personajes'][0]['expresion']='angry'
        for k in entrega['personajes'][0]['claves']:
            k['expresion']='angry'
        e=dict(t_in=0,t_out=4,narracion='Una acción.',descripcion_visual='Ana gesticula; Bruno observa.',
            indicaciones_usuario=dict(edicion_stickman=dict(ancla='Una acción.',contenido=original,
                mensajes=[dict(autor='usuario',texto='Modifica el rostro naranja para que esté enfadado.')])) )
        antes=copy.deepcopy(original)
        for valor in (None,False):
            respuesta=copy.deepcopy(entrega)
            if valor is not None:
                respuesta['realizacion']['cejas_fieles']=valor
            with self.subTest(marca_proveedor=valor),patch.dict(os.environ,ESTUDIO_SIMULAR='0'), \
                    patch.object(stickman,'_consultar',return_value=respuesta) as consulta:
                resultado=stickman.generar_escena(e,self.base,self.reparto,None,lambda *a:None)
            self.assertEqual(consulta.call_count,1)
            self.assertTrue(resultado['realizacion']['cejas_fieles'])
            self.assertNotIn('expresiones_fieles',resultado['realizacion'])
            self.assertEqual(resultado['personajes'][0]['expresion'],'angry')
            self.assertTrue(all(k['expresion']=='angry' for k in resultado['personajes'][0]['claves']))
            self.assertEqual(resultado['personajes'][1],stickman.escena(original,4,self.reparto)['personajes'][1])
            self.assertEqual(resultado['personajes'][0]['claves'],entrega['personajes'][0]['claves'])
            self.assertEqual(resultado['realizacion']['escenario'],original['realizacion']['escenario'])
            self.assertEqual(stickman.escena(resultado,4,self.reparto)['realizacion'],resultado['realizacion'])
            self.assertEqual(original,antes)

    @unittest.skipUnless(REAL,'usa --real para pendientes de cejas en rig, familias y primeros planos')
    def test_cejas_fieles_neutral_enfado_y_preocupacion_en_todas_las_rutas(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        def comprobar(nav,destino=None):
            resultado=nav.evaluar('''(() => {
                const ctx=document.querySelector('canvas').getContext('2d');
                const begin=ctx.beginPath,move=ctx.moveTo,line=ctx.lineTo,stroke=ctx.stroke;
                let puntos=[],cejas=[],bocas=0;
                ctx.beginPath=function(){puntos=[];return begin.call(this);};
                ctx.moveTo=function(x,y){puntos=[[x,y]];return move.call(this,x,y);};
                ctx.lineTo=function(x,y){puntos.push([x,y]);return line.call(this,x,y);};
                ctx.stroke=function(...args){
                    if(puntos.length===2){
                        const dx=puntos[1][0]-puntos[0][0],dy=puntos[1][1]-puntos[0][1];
                        if(dx>0&&Math.abs(this.lineWidth/dx-.25)<.001&&
                            [.4,.16/.3].some(p=>Math.abs(Math.abs(dy/dx)-p)<.001))cejas.push(dy/dx);
                        if(dx>0&&Math.abs(dy)<.001&&Math.abs(this.lineWidth/dx-.085/.24)<.001)bocas++;
                    }
                    return stroke.apply(this,args);
                };
                const actor=window.STICKMAN.escena.personajes[0],r=window.STICKMAN.escena.realizacion;
                const pintar=exp=>{actor.expresion=exp;cejas=[];bocas=0;window.pintar(.5);return [...cejas];};
                try {
                    const neutral=pintar('neutral'),bocasNeutras=bocas;
                    const angry=pintar('angry'),worried=pintar('worried'),sad=pintar('sad');
                    r.expresiones_fieles=false;const antigua=pintar('angry');
                    r.cejas_fieles=true;const editada=pintar('angry'),neutralEditado=pintar('neutral'),bocasEditadas=bocas;
                    r.expresiones_fieles=true;delete r.cejas_fieles;actor.expresion='neutral';window.pintar(.5);
                    return {neutral,bocasNeutras,angry,worried,sad,antigua,editada,neutralEditado,bocasEditadas};
                } finally {ctx.beginPath=begin;ctx.moveTo=move;ctx.lineTo=line;ctx.stroke=stroke;}
            })()''')
            self.assertEqual(resultado['neutral'],[])
            self.assertEqual(resultado['bocasNeutras'],1)
            self.assertEqual(resultado['neutralEditado'],[])
            self.assertEqual(resultado['bocasEditadas'],0)  # Conserva smallSmile histórico, no lo convierte en smallFlat.
            for expresion,signos in [('angry',[1,-1]),('worried',[-1,1]),('sad',[-1,1]),('antigua',[-1,1]),('editada',[1,-1])]:
                self.assertEqual(len(resultado[expresion]),2,resultado)
                self.assertEqual([1 if v>0 else -1 for v in resultado[expresion]],signos)
            return original(nav,destino)
        for nombre,diseno,encuadre in [('rig',self.base,'general'),('familia',dict(self.base,familia='geometric'),'general'),
                ('rostro',self.base,'primer_plano')]:
            datos=dict(ambiente='void',decorado='vacio',realizacion=dict(encuadre=encuadre,sujeto='ana',
                expresiones_fieles=True,color_fiel=True,grano=0,vineta=0),
                personajes=[dict(id='ana',x=.5,y=.9,escala=2.8,claves=[dict(t=0,pose='stand')])])
            with self.subTest(ruta=nombre),patch.object(p8_render.Navegador,'capturar',comprobar):
                stickman.renderizar(diseno,stickman.escena(datos,4,{'ana':diseno}),4,
                    str(Path(TEMP.name)/f'expresiones-{nombre}.png'),salida=(960,540))

    def test_cine_contrato_proyeccion_y_generacion_sin_vector_gigante(self):
        d=stickman.validar_puesta_en_escena(referencia_cine(),4,{},[1920,1080])
        self.assertEqual(stickman.escena(d,4,{}),d)
        self.assertEqual(d['personajes'],[])
        self.assertEqual(d['objetos'],[])
        vacia=referencia_cine();vacia['realizacion']['escenario']['proyeccion']='vacia'
        with self.assertRaisesRegex(ValueError,'sin contenido'):
            stickman.validar_puesta_en_escena(vacia,4,{},[1920,1080])
        antigua=referencia_cine();antigua['realizacion']['escenario'].pop('proyeccion')
        antigua['realizacion']['escenario']['tipo']='teatro'
        antigua['objetos']=[dict(tipo='circulo',x=.5,y=.4,w=300,h=300,claves=[dict(t=1,escala=1.1)])]
        descripcion='Sala de cine con butacas de terciopelo burdeos: en la pantalla, una silueta amenazante a contraluz; siluetas de público en el borde inferior.'
        with patch.dict(os.environ,ESTUDIO_SIMULAR='0'),patch.object(stickman,'_consultar',
                side_effect=[antigua,referencia_cine()]) as consulta:
            nueva=stickman.generar_escena(dict(t_in=0,t_out=4,descripcion_visual=descripcion),
                self.base,self.reparto,None,lambda *a:None)
        self.assertEqual(consulta.call_count,2)
        self.assertIn('Una sala de cine requiere',consulta.call_args_list[1].args[0])
        self.assertEqual(nueva['realizacion']['escenario']['proyeccion'],'silueta_amenazante')
        self.assertEqual(stickman.escena(antigua,4,{})['realizacion']['escenario']['tipo'],'teatro')
        con_crowd=copy.deepcopy(d);con_crowd['efectos_visuales']=[dict(tipo='crowd')]
        with self.assertRaisesRegex(ValueError,'público entre las butacas'):
            editorial.preparar_escenografia_nueva(con_crowd,[1920,1080])
        detalle=copy.deepcopy(d);detalle['realizacion']['encuadre']='detalle'
        with self.assertRaisesRegex(ValueError,'ocultar las butacas'):
            editorial.preparar_escenografia_nueva(detalle,[1920,1080],descripcion)

    @unittest.skipUnless(REAL,'usa --real para cine, proyección recortada y público entre butacas')
    def test_cine_render_recorta_pelicula_y_publico_sin_tapar_pantalla(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        d=stickman.validar_puesta_en_escena(referencia_cine(),4,{},[1920,1080])
        def comprobar(nav,destino=None):
            r=nav.evaluar('''(() => {
                const c=document.querySelector('canvas'),g=c.getContext('2d'),lugar=window.STICKMAN.escena.realizacion.escenario;
                const frame=t=>{window.pintar(t);return g.getImageData(0,0,c.width,c.height).data;};
                const pix=(x,y)=>Array.from(g.getImageData(Math.round(c.width*x),Math.round(c.height*y),1,1).data);
                const con=frame(.5),cabeza=pix(.51,.20),lateral=pix(.23,.25),butaca=pix(.45,.95);
                lugar.proyeccion='vacia';const vacia=frame(.5);let pelicula=0,fuera=0;
                for(let i=0;i<con.length;i+=4)if(con[i]!==vacia[i]||con[i+1]!==vacia[i+1]||con[i+2]!==vacia[i+2]){
                    pelicula++;const x=i/4%c.width,y=Math.floor(i/4/c.width);
                    if(x<c.width*.18-1||x>c.width*.82+1||y<c.height*.085-1||y>c.height*.625+1)fuera++;
                }
                lugar.proyeccion='silueta_amenazante';const a=frame(.5),b=frame(.9);let animados=0;
                for(let i=0;i<a.length;i+=4)if(a[i]!==b[i])animados++;
                lugar.publico=false;const sinPublico=frame(.9);let publico=0,invade=0;
                for(let i=0;i<b.length;i+=4)if(b[i]!==sinPublico[i]){
                    publico++;const x=i/4%c.width;
                    if(x>c.width*.18&&x<c.width*.82&&Math.floor(i/4/c.width)<c.height*.625)invade++;
                }
                lugar.publico=true;window.pintar(.5);
                return {pelicula,fuera,animados,publico,invade,cabeza,lateral,butaca};
            })()''')
            self.assertGreater(r['pelicula'],5000,r)
            self.assertEqual(r['fuera'],0,r)
            self.assertGreater(r['animados'],100,r)
            self.assertGreater(r['publico'],500,r)
            self.assertEqual(r['invade'],0,r)
            self.assertLess(max(r['cabeza'][:3]),40,r)
            self.assertGreater(sum(r['lateral'][:3]),sum(r['cabeza'][:3]),r)
            self.assertGreater(r['butaca'][0],r['butaca'][1]*1.5,r)
            return original(nav,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            stickman.renderizar(self.base,d,4,str(Path(TEMP.name)/'cine.png'),salida=(960,540))

    def test_calle_comercial_contrato_y_direccion_sin_casas_aisladas(self):
        base=dict(self.base,ropa='hoodie',color='#16b96b')
        reparto={k:base for k in ('tu','gris1','gris2','cruce','gris3')}
        entrega=referencia_calle_comercial()
        normalizada=stickman.validar_puesta_en_escena(entrega,4,reparto,[1920,1080])
        self.assertEqual(stickman.escena(normalizada,4,reparto),normalizada)
        self.assertEqual(normalizada['personajes'][0]['actuacion']['silueta'],'#7d8088')
        self.assertEqual(sum('aura' in p.get('actuacion',{}) for p in normalizada['personajes']),1)
        descripcion='Acera de ciudad al atardecer con fachadas de ladrillo y escaparates: Tú camina entre transeúntes.'
        incorrecta=copy.deepcopy(entrega);incorrecta['realizacion']['escenario']['tipo']='barrio'
        with patch.dict(os.environ,ESTUDIO_SIMULAR='0'),patch.object(stickman,'_consultar',
                side_effect=[incorrecta,entrega]) as consulta:
            corregida=stickman.generar_escena(dict(t_in=0,t_out=4,descripcion_visual=descripcion),
                base,reparto,None,lambda *a:None)
        self.assertEqual(consulta.call_count,2)
        self.assertIn('no dos casas',consulta.call_args_list[1].args[0])
        self.assertEqual(corregida['realizacion']['escenario']['tipo'],'calle_comercial')
        # Leer un plano anterior no lo convierte ni persiste el nuevo escenario.
        self.assertEqual(stickman.escena(incorrecta,4,reparto)['realizacion']['escenario']['tipo'],'barrio')

    @unittest.skipUnless(REAL,'usa --real para calle comercial, siluetas y halo selectivo')
    def test_calle_comercial_render_real(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        base=dict(self.base,ropa='hoodie',color='#16b96b')
        reparto={k:base for k in ('tu','gris1','gris2','cruce','gris3')}
        datos=stickman.escena(referencia_calle_comercial(),4,reparto)
        def comprobar(nav,destino=None):
            r=nav.evaluar('''(() => {
                const c=document.querySelector('canvas'),g=c.getContext('2d');
                const frame=t=>{window.pintar(t);return g.getImageData(0,0,c.width,c.height).data;};
                const pix=(x,y)=>Array.from(g.getImageData(Math.round(c.width*x),Math.round(c.height*y),1,1).data);
                const a=frame(0),cabeza=pix(.225,.47),cielo=pix(.5,.1),ocaso=pix(.52,.37);
                const b=frame(.15);let andando=0;
                for(let i=0;i<a.length;i+=4)if(Math.floor(i/4/c.width)>c.height*.6&&a[i]!==b[i])andando++;
                const escena=window.STICKMAN.escena,actor=escena.personajes.find(p=>p.id==='cruce');
                const con=frame(0);actor.actuacion.aura.intensidad=0;const sin=frame(0);
                let halo=0,contamina=0;
                for(let i=0;i<con.length;i+=4)if(con[i]!==sin[i]||con[i+1]!==sin[i+1]||con[i+2]!==sin[i+2]){
                    halo++;if(i/4%c.width<c.width*.45)contamina++;
                }
                actor.actuacion.aura.intensidad=.2;window.pintar(0);
                return {cabeza,cielo,ocaso,andando,halo,contamina};
            })()''')
            self.assertLess(max(r['cabeza'][:3])-min(r['cabeza'][:3]),25,r)
            self.assertGreater(min(r['cabeza'][:3]),90,r)  # Gris opaco, sin ropa verde heredada.
            self.assertGreater(r['cielo'][2],r['cielo'][1],r)  # Violeta, no azul de mediodía.
            self.assertGreater(r['cielo'][0],r['cielo'][1],r)
            self.assertGreater(r['ocaso'][0],r['ocaso'][2],r)
            self.assertGreater(r['andando'],100,r)
            self.assertGreater(r['halo'],100,r)
            self.assertEqual(r['contamina'],0,r)
            return original(nav,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            stickman.renderizar(base,datos,4,str(Path(TEMP.name)/'calle-comercial.png'),salida=(960,540))

    def test_ciudad_arquitectura_unica_materiales_y_continuidad(self):
        lugar=dict(id='calle',tipo='ciudad',fachada='#e8e2d6',tejado='#46515c',luz_ventanas='#91c9ed')
        datos=dict(ambiente='night',decorado='ciudad',personajes=[],
            realizacion=dict(encuadre='general',escenografia_detallada=True,escenario=lugar))
        d=stickman.escena(datos,4,{})
        self.assertEqual(d['realizacion']['escenario'],lugar)
        d['utileria']['casa']=dict(concepto='casa-de-yeso',nombre='Casa de yeso',etiquetas=['vivienda'])
        d['objetos']=[dict(tipo='vector',recurso='casa')]
        anterior=copy.deepcopy(d)
        with self.assertRaisesRegex(ValueError,'duplica los edificios'):
            editorial.preparar_escenografia_nueva(d,[1920,1080])
        self.assertEqual(d,anterior)  # Pide corregir, no borra la utilería.
        d['realizacion']['escenario']['edificios']=False
        editorial.preparar_escenografia_nueva(d,[1920,1080])
        siguiente=dict(realizacion=dict(escenario=dict(id='calle',tipo='ciudad')))
        editorial.heredar_escenografia(siguiente,dict(anterior=dict(contenido=d)))
        self.assertEqual(siguiente['realizacion']['escenario'],dict(lugar,edificios=False))
        # Un laboratorio exterior añadido no equivale a duplicar las viviendas.
        d['realizacion']['escenario'].pop('edificios')
        d['utileria']['casa']=dict(concepto='laboratorio-exterior',nombre='Laboratorio',etiquetas=['laboratorio'])
        editorial.preparar_escenografia_nueva(d,[1920,1080])
        for campo in ('fachada','tejado','luz_ventanas'):
            malo=copy.deepcopy(datos);malo['realizacion']['escenario'][campo]='azul'
            with self.assertRaises(ValueError):stickman.escena(malo,4,{})

    @unittest.skipUnless(REAL,'usa --real para casas únicas, pizarra y ventanas azules')
    def test_ciudad_materiales_render_real(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        datos=dict(ambiente='night',decorado='ciudad',personajes=[],realizacion=dict(
            encuadre='general',escenografia_detallada=True,acabado=False,color_fiel=True,
            escenario=dict(id='calle',tipo='ciudad',fachada='#e8e2d6',tejado='#46515c',luz_ventanas='#91c9ed')))
        def comprobar(nav,destino=None):
            r=nav.evaluar('''(() => {
                const c=document.querySelector('canvas'),g=c.getContext('2d');
                const pix=(x,y)=>Array.from(g.getImageData(Math.round(c.width*x),Math.round(c.height*y),1,1).data);
                window.pintar(0);
                const tejados=[pix(.185,.30),pix(.82,.25)],ventana=pix(.102,.53),pared=pix(.06,.65);
                window.STICKMAN.escena.realizacion.escenario.edificios=false;window.pintar(0);
                const sin=[pix(.185,.30),pix(.82,.25),pix(.06,.65)];
                window.STICKMAN.escena.realizacion.escenario.edificios=true;window.pintar(0);
                return {tejados,ventana,pared,sin};
            })()''')
            for i,color in enumerate(r['tejados']):
                self.assertGreater(color[2],color[0])  # Pizarra fría, no terracota roja.
                self.assertNotEqual(color,r['sin'][i])
            self.assertGreater(r['ventana'][2],r['ventana'][0])
            self.assertGreater(r['ventana'][2],r['ventana'][1])
            self.assertGreater(r['pared'][0],r['pared'][2])  # Yeso cálido, no verde de marca.
            self.assertNotEqual(r['pared'],r['sin'][2])
            return original(nav,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            stickman.renderizar(self.base,stickman.escena(datos,4,{}),4,
                str(Path(TEMP.name)/'ciudad-materiales.png'),salida=(960,540))

    def test_escenografia_detallada_nueva_respeta_historial_y_pide_no_taparla(self):
        entrega=referencia_escenario_detallado(self.base)
        entrega['realizacion'].pop('escenografia_detallada')
        historica=stickman.escena(entrega,4,self.reparto)
        self.assertNotIn('escenografia_detallada',historica['realizacion'])
        tapada=copy.deepcopy(entrega)
        tapada['objetos']=[dict(tipo='rectangulo',capa='fondo',x=.5,y=.5,w=1920,h=800,color='#771122')]
        con_crowd=copy.deepcopy(entrega)
        con_crowd['efectos_visuales']=[dict(tipo='crowd',capa='fondo',opciones=dict(rows=2,size=1.5))]
        with patch.dict(os.environ,ESTUDIO_SIMULAR='0'),patch.object(stickman,'_consultar',
                side_effect=[tapada,con_crowd,entrega]) as consulta:
            nueva=stickman.generar_escena(dict(t_in=0,t_out=4),self.base,self.reparto,None,lambda *a:None)
        self.assertEqual(consulta.call_count,3)
        self.assertIn('rectángulo opaco',consulta.call_args_list[1].args[0])
        self.assertIn('público de primer término',consulta.call_args_list[2].args[0])
        self.assertTrue(nueva['realizacion']['escenografia_detallada'])
        self.assertEqual(stickman.escena(nueva,4,self.reparto)['realizacion'],nueva['realizacion'])
        e=dict(t_in=0,t_out=4,continuidad_bloque=dict(anterior=dict(contenido=historica)))
        with patch.dict(os.environ,ESTUDIO_SIMULAR='0'),patch.object(stickman,'_consultar',return_value=tapada):
            continuada=stickman.generar_escena(e,self.base,self.reparto,None,lambda *a:None)
        self.assertFalse(continuada['realizacion']['escenografia_detallada'])
        self.assertEqual(len(continuada['objetos']),1)  # Continúa el plano antiguo, no cambia su acabado a mitad de bloque.
        with patch.dict(os.environ,ESTUDIO_SIMULAR='0'),patch.object(stickman,'_consultar',
                side_effect=[copy.deepcopy(tapada),copy.deepcopy(entrega)]) as consulta:
            renovada=stickman.generar_escena(dict(e,renovar_escenografia=True),self.base,self.reparto,None,lambda *a:None)
        self.assertEqual(consulta.call_count,2)
        self.assertTrue(renovada['realizacion']['escenografia_detallada'])
        incompleta=copy.deepcopy(entrega)
        for campo in ('semilla','atril','publico'):
            incompleta['realizacion']['escenario'].pop(campo,None)
        e['continuidad_bloque']['anterior']['contenido']=nueva
        with patch.dict(os.environ,ESTUDIO_SIMULAR='0'),patch.object(stickman,'_consultar',return_value=incompleta):
            continuada=stickman.generar_escena(e,self.base,self.reparto,None,lambda *a:None)
        self.assertTrue(continuada['realizacion']['escenografia_detallada'])
        self.assertTrue(continuada['realizacion']['escenario']['atril'])
        self.assertEqual(continuada['realizacion']['escenario']['semilla'],17)
        propia=copy.deepcopy(con_crowd)
        propia['realizacion']['escenario']['publico']=False
        editorial.preparar_escenografia_nueva(stickman.escena(propia,4,self.reparto),[1920,1080])
        from pasos import personajes
        for prompt in (editorial.instruccion(),personajes.instruccion_visual_stickman()):
            for pauta in ('terciopelo','tarima','foco','laboratorio','cocina'):
                self.assertIn(pauta,prompt)

    @unittest.skipUnless(REAL,'usa --real para telón, tarima, público, luz anclada y decorados materiales')
    def test_teatro_detallado_y_escenarios_reales_con_camara_y_materiales(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        def comprobar_teatro(nav,destino=None):
            resultado=nav.evaluar('''(() => {
                const d=window.STICKMAN.escena,r=d.realizacion,ctx=document.querySelector('canvas').getContext('2d');
                const pixels=t=>{window.pintar(t);return ctx.getImageData(0,0,ctx.canvas.width,ctx.canvas.height).data;};
                const a=pixels(2.2),b=pixels(2.8),c=pixels(2.2);
                let publico=0,sinPublico=0,madera=0,movimiento=0,estable=true;
                for(let i=0;i<a.length;i+=4){
                    const y=Math.floor(i/4/ctx.canvas.width);
                    if(a[i]===6&&a[i+1]===6&&a[i+2]===7)publico++;
                    if(y>ctx.canvas.height*.82&&a[i]>a[i+1]*1.1&&a[i+1]>a[i+2]*1.1&&a[i]>40)madera++;
                    if(y<ctx.canvas.height*.25&&(a[i]!==b[i]||a[i+1]!==b[i+1]||a[i+2]!==b[i+2]))movimiento++;
                    if(a[i]!==c[i]||a[i+1]!==c[i+1]||a[i+2]!==c[i+2])estable=false;
                }
                r.escenario.publico=false;const sin=pixels(2.2);
                for(let i=0;i<sin.length;i+=4)if(sin[i]===6&&sin[i+1]===6&&sin[i+2]===7)sinPublico++;
                r.escenario.publico=true;
                const antes=d.camara,arc=ctx.arc,translate=ctx.translate,actor=d.personajes[0];let focos=[],pies=[];
                ctx.arc=function(x,y,rad,...args){
                    if(Math.abs(rad-1920*.17)<.01){const p=this.getTransform().transformPoint({x,y});focos.push({x:p.x,y:p.y});}
                    return arc.call(this,x,y,rad,...args);
                };
                ctx.translate=function(x,y){
                    if(this.globalCompositeOperation==='source-over'&&Math.abs(x-actor.x*1920)<.01&&
                      Math.abs(y-actor.y*(1920*ctx.canvas.height/ctx.canvas.width))<.01){
                        const p=this.getTransform().transformPoint({x,y});pies.push({x:p.x,y:p.y});
                    }return translate.call(this,x,y);
                };
                try{d.camara=[{t:0,x:.04,y:.025,escala:1.15}];window.pintar(2.2);}
                finally{ctx.arc=arc;ctx.translate=translate;d.camara=antes;window.pintar(2.2);}
                return {publico,sinPublico,madera,movimiento,estable,focos,pies};
            })()''')
            self.assertGreater(resultado['publico'],1500)
            self.assertLess(resultado['sinPublico'],resultado['publico']*.1)
            self.assertGreater(resultado['madera'],1000)
            self.assertGreater(resultado['movimiento'],50)
            self.assertTrue(resultado['estable'])
            self.assertTrue(resultado['focos'])
            self.assertTrue(resultado['pies'])
            foco,pie=resultado['focos'][0],resultado['pies'][0]
            self.assertAlmostEqual(foco['x'],pie['x'],places=4)
            self.assertAlmostEqual(foco['y'],pie['y'],places=4)
            return original(nav,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar_teatro):
            stickman.renderizar(self.base,stickman.escena(referencia_escenario_detallado(self.base),4,self.reparto),
                4,str(Path(TEMP.name)/'teatro-detallado.png'),salida=(960,540))
        muestras=set()
        for tipo in ('salon','oficina','laboratorio','cocina','aula','barrio','parque','fiesta'):
            png=Path(TEMP.name)/f'escenario-detallado-{tipo}.png'
            stickman.renderizar(self.base,stickman.escena(referencia_escenario_detallado(self.base,tipo),4,self.reparto),
                4,str(png),salida=(640,360))
            muestras.add(png.read_bytes())
        self.assertEqual(len(muestras),8)

    def test_portadas_programaticas_respetan_tiempo_y_no_se_repiten_por_continuidad(self):
        capitulo=dict(numero=1,titulo='La pregunta',estilo='arctic')
        breve=dict(t_in=0,t_out=2.5,narracion='Una pregunta concreta.',capitulo=capitulo,
            apertura_capitulo=dict(capitulo,duracion_s=2.5))
        with patch.dict(os.environ,ESTUDIO_SIMULAR='0'),patch.object(stickman,'_consultar') as cli:
            portada=stickman.generar_escena(breve,self.base,self.reparto,None,lambda *a:None)
        cli.assert_not_called()
        self.assertEqual(portada['personajes'],[])
        self.assertEqual(portada['graficos'][0]['opciones'],capitulo)
        self.assertEqual(portada['graficos'][0]['fin'],2.5)
        larga=dict(breve,t_out=8,apertura_capitulo=dict(capitulo,duracion_s=2.8))
        entrega=dict(personajes=[dict(id='ana',x=.5,y=.88,escala=2.6,
            claves=[dict(t=0,pose='stand'),dict(t=3,pose='wave'),dict(t=7,pose='explain')])],
            graficos=[dict(tipo='capitulo',opciones=dict(numero=99,titulo='Portada repetida',estilo='ember'))])
        siguiente=dict(larga,t_in=8,t_out=16)
        siguiente.pop('apertura_capitulo')
        with patch.dict(os.environ,ESTUDIO_SIMULAR='0'),patch.object(stickman,'_consultar',
                side_effect=[copy.deepcopy(entrega),copy.deepcopy(entrega)]):
            abierta=stickman.generar_escena(larga,self.base,self.reparto,None,lambda *a:None)
            desarrollo=stickman.generar_escena(siguiente,self.base,self.reparto,None,lambda *a:None)
        self.assertEqual(abierta['graficos'][0]['opciones'],capitulo)
        self.assertEqual(abierta['graficos'][0]['fin'],2.8)
        self.assertEqual(abierta['personajes'][0]['claves'][-1]['t'],7)
        self.assertFalse(desarrollo['graficos'])

    @unittest.skipUnless(REAL,'usa --real para portadas de capítulos con fuentes, luz y partículas')
    def test_portadas_reales_legibles_animadas_y_salida_al_contenido_sin_cambiar_reloj(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        casos=[('arctic','#76ccff'),('ember','#ff8d38'),('mixto','#ffcf70'),('sakura','#ff78b9'),('retro','#e9b938')]
        for numero,(estilo,color) in enumerate(casos,1):
            d=referencia_capitulo(numero,'Qué cambia en el cerebro y en la conducta',estilo,fin=2.5)
            d['objetos']=[dict(tipo='rectangulo',x=.5,y=.5,w=1920,h=1080,color='#00ff00')]
            def comprobar(nav,destino=None):
                resultado=nav.evaluar('''(() => {
                    const d=window.STICKMAN.escena,ctx=document.querySelector('canvas').getContext('2d');
                    const pixels=t=>{window.pintar(t);return ctx.getImageData(0,0,ctx.canvas.width,ctx.canvas.height).data;};
                    const a=pixels(1.3),b=pixels(1.9),c=pixels(1.3),rgb=COLOR.match(/../g).map(h=>parseInt(h,16));
                    let numero=0,titulo=0,movimiento=0,verdeDentro=0,verdeDespues=0,estable=true;
                    for(let i=0;i<a.length;i+=4){
                        if(a[i]===rgb[0]&&a[i+1]===rgb[1]&&a[i+2]===rgb[2])numero++;
                        if(a[i]===255&&a[i+1]===241&&a[i+2]===220)titulo++;
                        if(a[i]===0&&a[i+1]===255&&a[i+2]===0)verdeDentro++;
                        if(a[i]!==b[i]||a[i+1]!==b[i+1]||a[i+2]!==b[i+2])movimiento++;
                        if(a[i]!==c[i]||a[i+1]!==c[i+1]||a[i+2]!==c[i+2])estable=false;
                    }
                    const despues=pixels(2.6);
                    for(let i=0;i<despues.length;i+=4)if(despues[i]===0&&despues[i+1]===255&&despues[i+2]===0)verdeDespues++;
                    window.pintar(1.3);return {numero,titulo,movimiento,estable,verdeDentro,verdeDespues};
                })()'''.replace('COLOR',json.dumps(color[1:])))
                self.assertGreater(resultado['numero'],500)
                self.assertGreater(resultado['titulo'],500)
                self.assertGreater(resultado['movimiento'],100)
                self.assertTrue(resultado['estable'])
                self.assertEqual(resultado['verdeDentro'],0)
                self.assertGreater(resultado['verdeDespues'],10000)
                return original(nav,destino)
            with self.subTest(estilo=estilo),patch.object(p8_render.Navegador,'capturar',comprobar):
                stickman.renderizar(self.base,stickman.escena(d,4,{}),4,
                    str(Path(TEMP.name)/f'capitulo-{estilo}.png'),salida=(960,540))

    def test_ambiente_y_bocadillos_conservan_contrato_y_no_modifican_historicos(self):
        for d in (referencia_poblacion(),referencia_rostro(self.base),referencia_rostro(self.base,'pensamiento')):
            normal=stickman.escena(d,4,self.reparto)
            self.assertEqual(stickman.escena(normal,4,self.reparto),normal)
            self.assertTrue(normal['realizacion']['particulas'])
        historico=stickman.escena(narrativa(self.base),4,self.reparto)
        self.assertNotIn('particulas',historico['realizacion'])
        self.assertNotIn('malla',historico['realizacion'])
        d=referencia_rostro(self.base)
        d['graficos'][0]['capa']='fondo'
        with self.assertRaisesRegex(ValueError,'capa pantalla'):
            stickman.escena(d,4,self.reparto)
        from pasos import personajes
        for prompt in (editorial.instruccion(),personajes.instruccion_visual_stickman()):
            for pauta in ('partículas','malla','rostro','pensamiento'):
                self.assertIn(pauta,prompt)

    def test_ambiente_por_defecto_solo_al_generar_y_respeta_desactivacion_y_edicion(self):
        entrega=dict(realizacion=dict(encuadre='grafico'),graficos=[dict(tipo='bigLine',opciones=dict(str='Una idea'))])
        escena=dict(narracion='Una idea.',t_in=12,t_out=16)
        base=dict(self.base,acabado='arctic')
        desactivada=copy.deepcopy(entrega)
        desactivada['realizacion'].update(particulas=False,malla=False,escenografia_detallada=False)
        editada=dict(escena,indicaciones_usuario=dict(edicion_stickman=dict(ancla=escena['narracion'],contenido=entrega)))
        with patch.dict(os.environ,ESTUDIO_SIMULAR='0'),patch.object(stickman,'_consultar',
                side_effect=[copy.deepcopy(entrega),desactivada,copy.deepcopy(entrega)]):
            nueva=stickman.generar_escena(escena,base,self.reparto,None,lambda *a:None)
            sinEfectos=stickman.generar_escena(escena,base,self.reparto,None,lambda *a:None)
            retoque=stickman.generar_escena(editada,base,self.reparto,None,lambda *a:None)
        self.assertTrue(nueva['realizacion']['particulas'])
        self.assertTrue(nueva['realizacion']['malla'])
        self.assertTrue(nueva['realizacion']['escenografia_detallada'])
        self.assertEqual(nueva['realizacion']['desfase_ambiente'],12)
        self.assertFalse(sinEfectos['realizacion']['particulas'])
        self.assertFalse(sinEfectos['realizacion']['malla'])
        self.assertFalse(sinEfectos['realizacion']['escenografia_detallada'])
        self.assertNotIn('particulas',retoque['realizacion'])
        self.assertNotIn('malla',retoque['realizacion'])
        self.assertNotIn('escenografia_detallada',retoque['realizacion'])

    def test_comparacion_nueva_corrige_paneles_planos_y_conserva_lectura_historica(self):
        plana=referencia_comparacion(self.base)
        plana['realizacion'].pop('comparacion')
        plana['objetos']=[dict(tipo='rectangulo',x=x,y=.5,w=964,h=1080,capa='fondo',color=color)
            for x,color in ((.25,'#2f6fd6'),(.75,'#d93a3a'))]
        historica=stickman.escena(plana,4,self.reparto)
        self.assertNotIn('comparacion',historica['realizacion'])
        self.assertEqual(len(historica['objetos']),2)
        with self.assertRaisesRegex(ValueError,'paneles planos'):
            editorial.preparar_comparacion_nueva(copy.deepcopy(historica),[1920,1080])
        with patch.dict(os.environ,ESTUDIO_SIMULAR='0'),patch.object(stickman,'_consultar',
                side_effect=[plana,referencia_comparacion(self.base)]) as cli:
            nueva=stickman.generar_escena(dict(t_in=0,t_out=4),self.base,self.reparto,None,lambda *a:None)
        self.assertEqual(cli.call_count,2)
        self.assertIn('paneles planos',cli.call_args.args[0])
        self.assertIn('comparacion',nueva['realizacion'])
        self.assertFalse(nueva['objetos'])
        self.assertEqual(stickman.escena(nueva,4,self.reparto)['realizacion'],nueva['realizacion'])
        con_edicion=dict(t_in=0,t_out=4,narracion='Un contraste.',indicaciones_usuario=dict(
            edicion_stickman=dict(ancla='Un contraste.',contenido=plana)))
        with patch.dict(os.environ,ESTUDIO_SIMULAR='0'),patch.object(stickman,'_consultar',return_value=plana):
            retoque=stickman.generar_escena(con_edicion,self.base,self.reparto,None,lambda *a:None)
        self.assertNotIn('comparacion',retoque['realizacion'])
        self.assertEqual(len(retoque['objetos']),2)
        for objeto in (dict(tipo='rectangulo',x=.25,y=.89,w=964,h=238,capa='fondo'),
                dict(tipo='linea',x=.5,y=0,w=0,h=1080,color='#ffffff')):
            mala=referencia_comparacion(self.base)
            mala['objetos']=[objeto]
            with self.assertRaisesRegex(ValueError,'suelo con reflejos'):
                editorial.preparar_comparacion_nueva(stickman.escena(mala,4,self.reparto),[1920,1080])
        # Magnitudes y objetos comparados no requieren dos personajes inventados.
        termometros=stickman.escena(referencia_termometros(),4,{})
        self.assertEqual(termometros['personajes'],[])
        self.assertEqual([o['panel'] for o in termometros['objetos']],['izquierda','derecha'])

    def test_tachado_contrato_opcional_y_tiempos(self):
        datos=referencia_tachado()
        contenido=stickman.escena(datos,4,{})
        self.assertEqual(contenido['objetos'][1]['tachado'],dict(inicio=1,fin=1.5))
        self.assertNotIn('tachado',contenido['objetos'][0])
        for cambio in (dict(inicio=-1,fin=1),dict(inicio=2,fin=1),dict(inicio=1,fin=5),
                       dict(inicio=1,fin=1),dict(inicio=1,fin=2,color='#83d9f7')):
            datos['objetos'][1]['tachado']=cambio
            with self.assertRaises(ValueError):
                stickman.escena(datos,4,{})
        datos['objetos'][1].update(tipo='linea',tachado=dict(inicio=1,fin=2))
        with self.assertRaisesRegex(ValueError,'objeto texto'):
            stickman.escena(datos,4,{})

    @unittest.skipUnless(REAL,'usa --real para tachado rojo por delante de las letras en Canvas')
    def test_tachado_rojo_superpuesto_real(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        def comprobar(nav,destino=None):
            r=nav.evaluar('''(() => {
                const c=document.querySelector('canvas'),g=c.getContext('2d');
                const frame=t=>{window.pintar(t);return g.getImageData(0,0,c.width,c.height).data;};
                const a=frame(.5),b=frame(1.25),d=frame(3);
                let medio=0,rojos=0,sobreLetras=0,x0=c.width,x1=0,y0=c.height,y1=0;
                for(let i=0;i<d.length;i+=4){
                    const rojo=p=>p[i]>180&&p[i+1]<90&&p[i+2]<90;
                    if(rojo(b))medio++;
                    if(!rojo(d))continue;
                    rojos++;const x=i/4%c.width,y=Math.floor(i/4/c.width);
                    x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y);
                    if(a[i]>100&&a[i+1]>50)sobreLetras++;
                }
                return {medio,rojos,sobreLetras,x0,x1,y0,y1,w:c.width,h:c.height};
            })()''')
            self.assertGreater(r['rojos'],1000)
            self.assertGreater(r['sobreLetras'],300)
            self.assertGreater(r['medio'],r['rojos']*.4)
            self.assertLess(r['medio'],r['rojos']*.65)
            self.assertLess(abs((r['x0']+r['x1'])/2-r['w']/2),3)
            self.assertLess(r['y1']-r['y0'],r['h']*.03)
            return original(nav,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            muestras=Path(os.environ.get('ESTUDIO_PRUEBA_STICKMAN_MUESTRAS',TEMP.name))
            muestras.mkdir(parents=True,exist_ok=True)
            stickman.renderizar(self.base,stickman.escena(referencia_tachado(),4,{}),4,
                str(muestras/'stickman_tachado.png'),salida=(1280,720))

    def test_tipografia_nueva_y_retoque_historico(self):
        datos=referencia_tipografia()
        contenido=stickman.escena(datos,4,{})
        self.assertEqual(contenido['objetos'][0]['fuente'],150)
        self.assertEqual(contenido['realizacion']['tipografia'],'redondeada')
        datos['realizacion'].pop('tipografia')
        self.assertNotIn('tipografia',stickman.escena(datos,4,{})['realizacion'])
        with patch.dict(os.environ,ESTUDIO_SIMULAR='0'),patch.object(stickman,'_consultar',return_value=datos):
            nueva=stickman.generar_escena(dict(t_in=0,t_out=4),self.base,self.reparto,None,lambda *a:None)
        self.assertEqual(nueva['realizacion']['tipografia'],'redondeada')
        e=dict(t_in=0,t_out=4,narracion='Un contraste.',indicaciones_usuario=dict(
            edicion_stickman=dict(ancla='Un contraste.',contenido=datos)))
        with patch.dict(os.environ,ESTUDIO_SIMULAR='0'),patch.object(stickman,'_consultar',return_value=datos):
            retoque=stickman.generar_escena(e,self.base,self.reparto,None,lambda *a:None)
        self.assertNotIn('tipografia',retoque['realizacion'])

    @unittest.skipUnless(REAL,'usa --real para comprobar Fredoka, halo y fusión animada')
    def test_rotulos_redondeados_reales(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        def comprobar(nav,destino=None):
            resultado=nav.evaluar('''(() => {
                const ctx=document.querySelector('canvas').getContext('2d'),proto=CanvasRenderingContext2D.prototype;
                const medir=proto.measureText,fuentes=[];
                proto.measureText=function(...args){fuentes.push(this.font);return medir.apply(this,args);};
                const pintar=t=>{window.pintar(t);return ctx.getImageData(0,0,ctx.canvas.width,ctx.canvas.height).data;};
                const a=pintar(1),b=pintar(2.7),c=pintar(3.5),d=pintar(1);
                proto.measureText=medir;
                let cambio=0,estable=true,tinta=0;
                for(let i=0;i<a.length;i+=4){
                    if(a[i]!==b[i]||b[i]!==c[i])cambio++;
                    if(a[i]!==d[i]||a[i+1]!==d[i+1]||a[i+2]!==d[i+2])estable=false;
                    if(a[i]>100&&a[i+1]>100&&a[i+2]>100)tinta++;
                }
                return {fuentes,cambio,estable,tinta};
            })()''')
            self.assertTrue(resultado['fuentes'])
            self.assertTrue(all('Fredoka' in f for f in resultado['fuentes']))
            self.assertGreater(resultado['cambio'],3000)
            self.assertGreater(resultado['tinta'],5000)
            self.assertTrue(resultado['estable'])
            return original(nav,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            stickman.renderizar(self.base,stickman.escena(referencia_tipografia(),4,{}),4,
                str(Path(TEMP.name)/'tipografia.png'),salida=(1280,720))

    @unittest.skipUnless(REAL,'usa --real para luz fría/cálida, tipografía y recorte luminoso')
    def test_comparaciones_reales_profundidad_particulas_y_paneles_tras_camara(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        def comprobar(nav,destino=None):
            resultado=nav.evaluar('''(() => {
                const d=window.STICKMAN.escena,ctx=document.querySelector('canvas').getContext('2d');
                const pintar=t=>{window.pintar(t);return ctx.getImageData(0,0,ctx.canvas.width,ctx.canvas.height).data;};
                const a=pintar(2),b=pintar(3),c=pintar(2),colores=new Set();
                let cambia=0,estable=true,azules=0,calidos=0;
                for(let y=0;y<ctx.canvas.height*.28;y++)for(let x=0;x<ctx.canvas.width*.15;x++){
                    const i=(y*ctx.canvas.width+x)*4;colores.add(`${a[i]},${a[i+1]},${a[i+2]}`);
                    if(a[i]!==b[i]||a[i+1]!==b[i+1]||a[i+2]!==b[i+2])cambia++;
                }
                for(let i=0;i<a.length;i+=4){
                    if(a[i]!==c[i]||a[i+1]!==c[i+1]||a[i+2]!==c[i+2])estable=false;
                    if(a[i+2]>a[i]*1.4&&a[i+2]>60)azules++;
                    if(a[i]>a[i+2]*1.4&&a[i]>60)calidos++;
                }
                // Sonda que cruza la unión en el mundo: el clip debe seguir en pantalla con zoom y desplazamiento.
                const camara=d.camara;
                d.objetos.push({tipo:'rectangulo',color:'#00ff00',x:.58,y:.72,w:900,h:50,
                    inicio:0,fin:4,capa:'frente',panel:'izquierda',escala:1,claves:[],opacidad:1});
                d.camara=[{t:0,x:.04,escala:1.2}];const probe=pintar(2);
                let verdes=0,maxX=0;
                for(let i=0;i<probe.length;i+=4)if(probe[i]===0&&probe[i+1]===255&&probe[i+2]===0){
                    verdes++;maxX=Math.max(maxX,(i/4)%ctx.canvas.width);
                }
                d.objetos.pop();d.camara=camara;window.pintar(2);
                return {colores:colores.size,cambia,estable,azules,calidos,verdes,maxX,w:ctx.canvas.width,
                    fuente:document.fonts.check('700 78px "Fredoka"')};
            })()''')
            self.assertGreater(resultado['colores'],100)
            self.assertGreater(resultado['cambia'],30)
            self.assertTrue(resultado['estable'])
            self.assertGreater(resultado['azules'],1000)
            self.assertGreater(resultado['calidos'],1000)
            self.assertGreater(resultado['verdes'],100)
            self.assertLess(resultado['maxX'],resultado['w']*.54)
            self.assertTrue(resultado['fuente'])
            return original(nav,destino)
        for nombre,datos in [('personajes',referencia_comparacion(self.base)),('termometros',referencia_termometros())]:
            with self.subTest(caso=nombre),patch.object(p8_render.Navegador,'capturar',comprobar):
                stickman.renderizar(self.base,stickman.escena(datos,4,self.reparto),4,
                    str(Path(TEMP.name)/f'comparacion-{nombre}.png'),salida=(1280,720))

    @unittest.skipUnless(REAL,'usa --real para partículas, malla y bocadillos en el navegador')
    def test_referencias_visuales_fondo_animado_y_rostros_con_bocadillos(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        def comprobar_fondo(nav,destino=None):
            resultado=nav.evaluar('''(() => {
                const d=window.STICKMAN.escena,r=d.realizacion,ctx=document.querySelector('canvas').getContext('2d');
                const pintar=t=>{window.pintar(t);return ctx.getImageData(0,0,ctx.canvas.width,ctx.canvas.height).data;};
                const a=pintar(2),b=pintar(3),c=pintar(2);
                let movimiento=0,repetida=true,malla=0,maxDiferencia=0;
                for(let i=0;i<a.length;i++){if(a[i]!==b[i])movimiento++;if(a[i]!==c[i])repetida=false;}
                r.particulas=false;const conMalla=pintar(2);r.malla=false;const liso=pintar(2);
                for(let i=0;i<liso.length;i++){const dif=Math.abs(liso[i]-conMalla[i]);if(dif)malla++;maxDiferencia=Math.max(maxDiferencia,dif);}
                r.particulas=true;r.malla=true;window.pintar(2);
                return {movimiento,repetida,malla,maxDiferencia};
            })()''')
            self.assertGreater(resultado['movimiento'],300)
            self.assertTrue(resultado['repetida'])
            self.assertGreater(resultado['malla'],1000)
            self.assertGreater(resultado['maxDiferencia'],0)
            self.assertLess(resultado['maxDiferencia'],40)
            return original(nav,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar_fondo):
            stickman.renderizar(self.base,stickman.escena(referencia_poblacion(),4,{}),4,
                str(Path(TEMP.name)/'referencia-poblacion.png'),salida=(960,540))
        imagenes=[]
        for modo in ('dialogo','pensamiento'):
            d=stickman.escena(referencia_rostro(self.base,modo),4,self.reparto)
            def comprobar_bocadillo(nav,destino=None):
                resultado=nav.evaluar('''(() => {
                    const d=window.STICKMAN.escena,ctx=document.querySelector('canvas').getContext('2d');
                    const original=ctx.fillText,arc=ctx.arc,lineTo=ctx.lineTo,camara=d.camara;
                    let arcos=[],puntos=[];const textos=[];
                    ctx.arc=function(x,y,r,...args){
                        const m=this.getTransform(),p=m.transformPoint({x,y});arcos.push({...p,x:p.x,y:p.y,r:r*Math.hypot(m.a,m.b)});
                        return arc.call(this,x,y,r,...args);
                    };
                    ctx.lineTo=function(x,y){const p=this.getTransform().transformPoint({x,y});puntos.push({x:p.x,y:p.y});return lineTo.call(this,x,y);};
                    ctx.fillText=function(str,x,y,...args){
                        const m=this.getTransform(),ancho=this.measureText(str).width;
                        const a=m.transformPoint({x:x-ancho/2,y}),b=m.transformPoint({x:x+ancho/2,y});
                        textos.push({str,izquierda:a.x,derecha:b.x,y:a.y});return original.call(this,str,x,y,...args);
                    };
                    const ancla=()=>{
                        const head=arcos.sort((a,b)=>b.r-a.r)[0],p=puntos.at(-2);
                        return p&&head?{x:p.x,distancia:Math.hypot(p.x-head.x,p.y-head.y)/head.r}:null;
                    };
                    let antes,despues;
                    try{
                        window.pintar(2);antes=ancla();
                        arcos=[];puntos=[];ctx.fillText=original;
                        d.camara=[{t:0,x:.04}];window.pintar(2);despues=ancla();
                    }finally{ctx.fillText=original;ctx.arc=arc;ctx.lineTo=lineTo;d.camara=camara;window.pintar(2);}
                    return {textos,antes,despues,w:ctx.canvas.width,h:ctx.canvas.height};
                })()''')
                self.assertTrue(resultado['textos'])
                self.assertEqual(' '.join(t['str'] for t in resultado['textos']),d['graficos'][0]['opciones']['texto'])
                for texto in resultado['textos']:
                    self.assertGreaterEqual(texto['izquierda'],0)
                    self.assertLessEqual(texto['derecha'],resultado['w'])
                    self.assertTrue(0<texto['y']<resultado['h'])
                if modo=='dialogo':
                    for ancla in (resultado['antes'],resultado['despues']):
                        self.assertTrue(.75<ancla['distancia']<1.05)
                    self.assertGreater(abs(resultado['antes']['x']-resultado['despues']['x']),10)
                imagenes.append(original(nav))
                return original(nav,destino)
            with patch.object(p8_render.Navegador,'capturar',comprobar_bocadillo):
                stickman.renderizar(self.base,d,4,str(Path(TEMP.name)/f'referencia-{modo}.png'),salida=(960,540))
        self.assertNotEqual(imagenes[0],imagenes[1])

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
        d['personajes'][1]['x']=.4
        with self.assertRaisesRegex(ValueError,'dividido'):
            self.validar(d)
        d['personajes'][1]['x']=.68
        for c,p in zip(d['personajes'],['izquierda','derecha']):c['panel']=p
        self.validar(d)

    def test_dividido_completa_paneles_inequivocos_sin_cambiar_la_entrega(self):
        for proveedor in ('Claude','ChatGPT'):
            for parcial in (False,True):
                entrega=narrativa(self.base)
                entrega['realizacion']['encuadre']='dividido'
                entrega['personajes'].reverse()  # El orden no determina el panel.
                if parcial:
                    entrega['personajes'][0]['panel']='derecha'
                original=copy.deepcopy(entrega)
                with self.subTest(proveedor=proveedor,parcial=parcial),\
                        patch.dict(os.environ,ESTUDIO_SIMULAR='0'),\
                        patch.object(stickman,'_consultar',return_value=entrega) as consultar:
                    resultado=stickman.generar_escena(dict(id='S001',t_in=0,t_out=4),
                        self.base,self.reparto,None,lambda *a:None,proveedor)
                self.assertEqual(consultar.call_count,1)
                self.assertEqual([c['panel'] for c in resultado['personajes']],['derecha','izquierda'])
                self.assertEqual(entrega,original)
                self.assertEqual(self.validar(resultado),resultado)

    def test_dividido_ambiguo_pide_correccion_sin_inventar_actores(self):
        for caso in ('un_actor','figurante','cruza_panel','panel_contradictorio'):
            entrega=narrativa(self.base)
            entrega['realizacion']['encuadre']='dividido'
            if caso=='un_actor':
                entrega['personajes'].pop()
            elif caso=='figurante':
                entrega['personajes'][1]['rol']='figurante'
            elif caso=='cruza_panel':
                entrega['personajes'][0]['claves'][-1]['x']=.7
            else:
                entrega['personajes'][0]['panel']='derecha'
            with self.subTest(caso=caso),self.assertRaisesRegex(ValueError,'Actores recibidos:.*no inventes actores'):
                self.validar(entrega)
        corregida=narrativa(self.base)
        with patch.object(stickman,'_consultar',side_effect=[entrega,corregida]) as consultar:
            resultado=stickman.consultar('encargo',validar=self.validar)
        self.assertEqual(resultado['realizacion']['encuadre'],'conjunto')
        self.assertIn('encuadre="grafico"',consultar.call_args.args[0])

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

    def test_movimiento_temporal_y_transito_respetan_el_contrato(self):
        d=narrativa(self.base)
        c=d['personajes'][0]
        c.update(transito=True,movimiento='caminar')
        c['claves']=[dict(t=0,x=.32,pose='stand'),dict(t=1,x=.45,movimiento='gesto',pose='talk'),
            dict(t=2,x=.45,movimiento='correr'),dict(t=3,x=1.4)]
        resultado=self.validar(d)
        self.assertEqual(resultado['personajes'][0]['claves'][1]['movimiento'],'gesto')
        self.assertEqual(stickman.escena(resultado,4,self.reparto),resultado)
        for cambio in (dict(transito=False),dict(transito='true'),dict(y=.1),dict(escala=.1)):
            copia=copy.deepcopy(d)
            copia['personajes'][0].update(cambio)
            with self.subTest(cambio=cambio),self.assertRaises(ValueError):
                self.validar(copia)
        for modo in ('caminar','correr'):
            with self.subTest(modo=modo),self.assertRaisesRegex(ValueError,'estática'):
                self.validar(dict(personajes=[dict(id='ana',movimiento=modo)]))
        with self.assertRaises(ValueError):
            stickman.claves([dict(t=0,movimiento='volar')],4)

    def test_movimiento_sigue_traslados_y_se_detiene_en_las_esperas(self):
        import subprocess
        modulo=(stickman.RAIZ/'motores/stickman/movimiento.js').as_uri()
        programa='''
            const {movimientoEn}=await import(process.argv[1]);
            const c={x:.2,y:.87,movimiento:'caminar',claves:[
                {t:0,x:.2},{t:1,x:.2},{t:2,x:.45},{t:3,x:.45},
                {t:4,x:1.4,movimiento:'gesto'}]};
            const tiempos=[0,.5,1,1.5,2,2.5,3,3.5,4,5];
            const salida=[tiempos.map(t=>movimientoEn(c,t))];
            c.claves[3].movimiento='correr';
            salida.push(movimientoEn(c,3.5));
            c.claves[3].movimiento='gesto';
            salida.push(movimientoEn(c,3.5));
            salida.push(movimientoEn({x:.2,y:.87,movimiento:'caminar',claves:[]},1));
            salida.push(movimientoEn({x:.2,y:.87,movimiento:'caminar',claves:[{t:2,y:.8}]},1));
            console.log(JSON.stringify(salida));
        '''
        r=subprocess.run(['node','--input-type=module','-e',programa,modulo],capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(r.stdout),[
            ['gesto','gesto','caminar','caminar','gesto','gesto','caminar','caminar','gesto','gesto'],
            'correr','gesto','gesto','caminar'])

    @unittest.skipUnless(REAL,'usa --real para comprobar paradas y salidas en Canvas')
    def test_movimiento_y_transito_render_real(self):
        from pasos import p8_render
        d=narrativa(self.base)
        d['realizacion'].update(acabado=False,grano=0,vineta=0)
        c=d['personajes'][0]
        c.update(transito=True,movimiento='caminar',x=.2)
        c['claves']=[dict(t=0,x=.2,pose='stand'),dict(t=1,x=.42),
            dict(t=2,x=.42),dict(t=3,x=1.4)]
        d['objetos']=[dict(tipo='movil',w=54,h=90,ancla=dict(personaje='ana',punto='mano'))]
        contenido=self.validar(d)
        capturar=p8_render.Navegador.capturar
        def comprobar(navegador,destino=None):
            r=navegador.evaluar('''(() => {
                const s=window.STICKMAN.escena,c=s.personajes[0],canvas=document.querySelector('canvas');
                const imagen=t=>{window.pintar(t);return canvas.toDataURL();};
                const andando=imagen(.5);c.movimiento='gesto';const quieto=imagen(.5);
                c.movimiento='caminar';const llegada=imagen(1.5);c.movimiento='gesto';const espera=imagen(1.5);
                c.movimiento='caminar';const salida=imagen(3.5);
                c.claves.push({t:3,opacidad:0});const sinActor=imagen(3.5);
                const objetos=s.objetos;s.objetos=[];const sinUtileria=imagen(3.5);s.objetos=objetos;
                c.claves.pop();
                return {anda:andando!==quieto,para:llegada===espera,
                    sale:salida===sinActor,utileriaSale:sinActor===sinUtileria};
            })()''')
            self.assertEqual(r,dict(anda=True,para=True,sale=True,utileriaSale=True))
            return capturar(navegador,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            stickman.renderizar(self.base,contenido,4,str(Path(TEMP.name)/'transito.png'),salida=(640,360))

    def test_poblacion_rechaza_distribuciones_e_indices_imposibles(self):
        for ops in (dict(filas=2.5),dict(total=100,filas=2,columnas=3),
                dict(total=100,columnas=2.5),dict(indices_destacados=[100]),
                dict(indices_destacados=[20,20]),dict(indices_destacados=[20.5]),
                dict(indices_destacados=[20],destacados=2),dict(inicio_destacado=5)):
            with self.subTest(ops=ops),self.assertRaisesRegex(ValueError,'poblacion|columnas'):
                stickman.escena(grafica('poblacion',ops),4,self.reparto)

    def test_vestuario_local_no_muta_identidad_y_sobrevive_normalizacion(self):
        original=copy.deepcopy(self.reparto)
        d=narrativa(self.base)
        d['personajes'][0]['vestuario']=dict(ropa='suit',color='#888888')
        d=self.validar(d)
        self.assertEqual(d['personajes'][0]['diseno']['color'],'#888888')
        self.assertEqual(d['personajes'][0]['diseno']['familia'],self.base['familia'])
        self.assertEqual(self.reparto,original)
        self.assertEqual(stickman.escena(d,4,self.reparto),d)

    @unittest.skipUnless(REAL,'usa --real para fidelidad de colores, matriz y rótulos')
    def test_render_fidelidad_matriz_y_rotulos_sobre_fondo_del_mismo_color(self):
        from pasos import p8_render
        from PIL import Image
        d=grafica('poblacion',dict(total=100,filas=10,columnas=10,color_base='#888888',
            color='#9b2020',indices_destacados=[20],atenuacion=.3,inicio_destacado=.5,duracion_destacado=.5))
        d['graficos']=d['graficos'][1:]
        d['graficos'][0]['inicio']=0
        d['realizacion'].update(color_fiel=True,fondo='#101010',vineta=0,grano=0)
        d['objetos']=[dict(tipo='rectangulo',color='#888888',x=.5,y=.12,w=100,h=100)]
        original=p8_render.Navegador.capturar
        muestras=Path(os.environ.get('ESTUDIO_PRUEBA_STICKMAN_MUESTRAS',TEMP.name))
        muestras.mkdir(parents=True,exist_ok=True)
        def comprobar(navegador,destino=None):
            def imagen(t):
                navegador.pintar(t)
                return Image.open(io.BytesIO(original(navegador))).convert('RGB')
            # Centro de la cabeza de cada figura en un lienzo de 960x540.
            def punto(i):return (round(960*(.11+.078*(i%10+.5))),round(540*(.3+.058*(i//10+.2))))
            inicio=imagen(0)
            self.assertEqual(inicio.getpixel((480,65)),(136,136,136))
            for i in range(100):self.assertEqual(inicio.getpixel(punto(i)),(136,136,136))
            fin=imagen(2)
            self.assertEqual(fin.getpixel(punto(20)),(155,32,32))
            self.assertLess(max(fin.getpixel(punto(0))),70)
            fin.save(muestras/'fidelidad_poblacion.png')
            # Tinta oscura en fondo idéntico: conserva el relleno y añade contorno claro,
            # incluso con Emerald y acabado activado. Prueba el texto nativo y el del kit.
            rotulos=stickman.escena(dict(personajes=[],decorado='vacio',
                realizacion=dict(encuadre='grafico',fondo='#10261e',acabado=True,vineta=0,grano=0),
                objetos=[dict(tipo='texto',texto='Psicópata',color='#10261e',x=.25,y=.2,w=750,h=100,fuente=80)],
                graficos=[dict(tipo='badge',opciones=dict(str='Sociópata',color='#10261e',x=1440,y=216,size=80))]),4,{})
            navegador.evaluar('window.STICKMAN.escena='+json.dumps(rotulos))
            img=imagen(2)
            img.save(muestras/'fidelidad_rotulos.png')
            # El texto del mundo se coloca bajo la franja reservada al rótulo de pantalla.
            for caja in ((30,140,440,230),(520,75,930,140)):
                colores=list(img.crop(caja).getdata())
                self.assertGreater(sum(min(c)>230 for c in colores),50)
                self.assertIn((16,38,30),colores)
            # Retirar la matriz en la frase siguiente no deja residuos del frame anterior.
            rotulos['objetos']=[];rotulos['graficos']=[]
            rotulos['realizacion'].update(color_fiel=True,fondo='#101010')
            navegador.evaluar('window.STICKMAN.escena='+json.dumps(rotulos))
            self.assertEqual(imagen(2).getpixel(punto(20)),(16,16,16))
            return original(navegador,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            stickman.renderizar(dict(self.base,acabado='emerald'),stickman.escena(d,4,{}),4,
                str(muestras/'fidelidad.png'),salida=(960,540))

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
            capas['personajes']=[]  # Aísla la capa: aquí no hay sujetos que deba encajar la cámara.
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

    @unittest.skipUnless(REAL,'usa --real para encuadres detalle y bordes seguros')
    def test_detalles_encajan_ficha_lista_y_dial_durante_toda_la_animacion(self):
        from pasos import p8_render
        original=p8_render.Navegador.capturar
        def texto(str,x,y,w=700):
            return dict(tipo='texto',texto=str,x=x,y=y,w=w,h=100,fuente=80,color='#302820')
        escenarios={
            'ficha':[dict(tipo='tarjeta',x=.5,y=.43,w=1380,h=600,color='#f3e9d5'),
                texto('1930',.5,.25,260),texto('George Partridge',.5,.37,1100),texto('Sociopatía',.5,.54,768)],
            'lista':[dict(tipo='tarjeta',x=.5,y=.5,w=760,h=920,color='#f3e9d5'),
                *[texto(s,.5,.13+i*.145) for i,s in enumerate(['Delirios','Simpático','Inteligente','Tranquilo','Miente','Sin culpa'])]],
            'dial':[dict(tipo='circulo',x=.5,y=.52,w=1200,h=700,color='#f3e9d5'),
                dict(tipo='linea',x=.5,y=.7,w=500,h=-200,color='#302820',claves=[dict(t=0,rot=0),dict(t=3,rot=-.4)]),
                texto('0',.2,.65,120),texto('10',.28,.35,120),texto('20',.5,.25,120),
                texto('30',.72,.35,120),texto('40',.8,.65,120)]}
        escenas={nombre:stickman.escena(dict(personajes=[],decorado='vacio',objetos=objetos,
            realizacion=dict(encuadre='detalle',foco=[.5,.43],color_fiel=True,grano=0,vineta=0),
            camara=[dict(t=0,escala=1),dict(t=2,escala=1.5,x=.1,rot=.08)]),4,{})
            for nombre,objetos in escenarios.items()}
        escenas['dial']['graficos']=[dict(tipo='badge',capa='pantalla',inicio=0,fin=4,
            opciones=dict(str='Escala',x=960,y=110,size=42))]
        muestras=Path(os.environ.get('ESTUDIO_PRUEBA_STICKMAN_MUESTRAS',TEMP.name))
        muestras.mkdir(parents=True,exist_ok=True)
        def comprobar(navegador,destino=None):
            for nombre,d in escenas.items():
                navegador.evaluar('window.STICKMAN.escena='+json.dumps(d))
                for t in (0,.5,1,2,3.9):
                    cajas=navegador.evaluar('''(() => {
                        const ctx=document.querySelector('canvas').getContext('2d'),orig=ctx.fillText,out=[];
                        ctx.fillText=function(str,x,y,...args){
                            const m=this.measureText(str),a=this.getTransform();
                            const pts=[[-m.actualBoundingBoxLeft,-m.actualBoundingBoxAscent],
                                [m.actualBoundingBoxRight,-m.actualBoundingBoxAscent],
                                [m.actualBoundingBoxRight,m.actualBoundingBoxDescent],
                                [-m.actualBoundingBoxLeft,m.actualBoundingBoxDescent]];
                            out.push({str,pts:pts.map(([dx,dy])=>({x:a.a*(x+dx)+a.c*(y+dy)+a.e,y:a.b*(x+dx)+a.d*(y+dy)+a.f}))});
                            return orig.call(this,str,x,y,...args);
                        };
                        try{pintar('''+str(t)+''');return out;}finally{ctx.fillText=orig;}
                    })()''')
                    self.assertEqual(len(cajas),sum(o['tipo']=='texto' for o in d['objetos'])+len(d.get('graficos',[])))
                    for caja in cajas:
                        for p in caja['pts']:
                            self.assertTrue(960*.039<=p['x']<=960*.961,(nombre,t,caja))
                            self.assertTrue(540*.039<=p['y']<=540*.961,(nombre,t,caja))
                    if nombre=='dial':
                        titulo=next(c for c in cajas if c['str']=='Escala')
                        marca=next(c for c in cajas if c['str']=='20')
                        self.assertGreater(min(p['y'] for p in marca['pts']),max(p['y'] for p in titulo['pts'])+4)
                original(navegador,str(muestras/('encuadre_'+nombre+'.png')))
            return original(navegador,destino)
        with patch.object(p8_render.Navegador,'capturar',comprobar):
            stickman.renderizar(self.base,escenas['ficha'],4,str(muestras/'encuadre.png'),salida=(960,540))

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
