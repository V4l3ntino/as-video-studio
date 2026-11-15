"""Contratos offline y render real opcional: python pasos/prueba_stickman.py --real."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
TEMP = tempfile.TemporaryDirectory(prefix='prueba_stickman_')
for clave in ('ESTUDIO_ESTADISTICAS', 'ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_PRESETS', 'ESTUDIO_BANCO_PRESETS', 'ESTUDIO_UTILERIA_STICKMAN'):
    os.environ[clave] = str(Path(TEMP.name) / clave)
os.environ['ESTUDIO_SIMULAR'] = '1'

from nucleo.proyecto import Proyecto
from nucleo.estado import Estado
from pasos import stickman, medios, personajes, presets_canal, presets_light, sonido, editor_escena, utileria_stickman

REAL = '--real' in sys.argv
if REAL:
    sys.argv.remove('--real')


def escena_mensajes(base):
    """Regresión del relato: atención, planes y retirada al llegar la intimidad."""
    return stickman.validar_puesta_en_escena(dict(ambiente='interiorCool', decorado='vacio', atmosfera='ninguna',
        personajes=[dict(id='lucia', x=.25, y=.88, escala=2.6, expresion='smile', claves=[
            dict(t=0, pose='phone'), dict(t=4.5, pose='phone', expresion='worried')]),
            dict(id='daniel', x=.73, y=.88, escala=2.6, mirar=-1, claves=[dict(t=0, pose='phone', expresion='smile'),
                dict(t=2, pose='point'), dict(t=4.5, pose='crossArms', expresion='worried'), dict(t=6, x=.79)])],
        objetos=[dict(tipo='movil', ancla=dict(personaje='lucia', punto='mano'), y=-.025, w=55, h=92, color='#b9e9ff'),
            dict(tipo='linea', x=.35, y=.63, w=570, h=0, color='#ff9d3e', capa='fondo', claves=[
                dict(t=0, progreso=0), dict(t=1, progreso=1), dict(t=4, opacidad=1), dict(t=5, opacidad=.15)]),
            *[dict(tipo='mensaje', x=.42, y=.30+i*.11, w=210, h=90, inicio=.4+i*.65, color='#d2f4e5') for i in range(3)],
            dict(tipo='calendario', x=.55, y=.28, w=250, h=220, inicio=1.8, color='#ed9b54',
                claves=[dict(t=1.8, progreso=0), dict(t=3.6, progreso=1)]),
            dict(tipo='corazon', x=.43, y=.63, w=70, h=65, inicio=3.8, fin=4.6, color='#f2798b'),
            dict(tipo='nube', ancla=dict(personaje='daniel', punto='cabeza'), y=-.12,
                w=160, h=100, inicio=4.5, color='#a8b1bc')]), 6,
        {'lucia': dict(base, color='#f2798b', accesorio='ponytail'), 'daniel': base}, [1920, 1080])


def avion_vectorial():
    """Dibujo de prueba, no un objeto incorporado al catálogo del programa."""
    return dict(concepto='avion', nombre='Avión ligero', descripcion='Avión de hélice de perfil, con alas, cola y ventanas.',
        etiquetas=['avión', 'airplane', 'vuelo', 'transporte', 'viajes'], ancho=1000, alto=500, partes=[
        dict(id='cola', formas=[dict(tipo='trazo', comandos=[['M', 100, 260], ['L', 70, 65], ['L', 140, 65],
            ['L', 265, 260], ['Z']], relleno='$principal', trazo='$oscuro', grosor=9)]),
        dict(id='fuselaje', formas=[dict(tipo='trazo', comandos=[['M', 95, 240], ['C', 330, 240, 630, 110, 760, 185],
            ['Q', 880, 210, 895, 270], ['Q', 840, 340, 580, 315], ['L', 140, 300], ['Z']],
            relleno='$claro', trazo='$oscuro', grosor=10),
            *[dict(tipo='elipse', x=x, y=218, w=50, h=46, relleno='$secundario', trazo='$oscuro', grosor=5) for x in (450, 540, 630)],
            dict(tipo='trazo', comandos=[['M', 740, 195], ['Q', 805, 200, 845, 240], ['L', 735, 240], ['Z']],
                relleno='$secundario', trazo='$oscuro', grosor=7)]),
        dict(id='ala', pivote=[450, 275], formas=[dict(tipo='trazo', comandos=[['M', 365, 270], ['L', 590, 410],
            ['L', 700, 410], ['L', 585, 265], ['Z']], relleno='$principal', trazo='$oscuro', grosor=9)]),
        dict(id='helice', pivote=[900, 265], formas=[dict(tipo='elipse', x=885, y=160, w=28, h=210,
            relleno='$oscuro'), dict(tipo='elipse', x=876, y=242, w=46, h=46, relleno='$principal')],
            animacion=dict(duracion=.8, claves=[dict(t=0, rot=0), dict(t=.8, rot=6.283185)]))])


def escena_pizarra(base):
    return stickman.validar_puesta_en_escena(dict(decorado='vacio', ambiente='interiorCool',
        personajes=[dict(id='lucia', x=.5, y=.90, escala=2.6, claves=[dict(t=0, pose='think'), dict(t=1, pose='point')])],
        objetos=[dict(tipo='pizarra', x=.5, y=.28, w=1450, h=480, color='#285247', capa='fondo'),
            *[dict(tipo='tarjeta', x=x, y=.26, w=500, h=220, color='#fff8ee', capa='fondo') for x in (.28, .72)],
            *[dict(tipo='texto', texto=t, x=x, y=.26, w=450, h=70, fuente=42, color='#162532', capa='fondo')
              for x, t in ((.28, 'APEGO EVITATIVO'), (.72, 'NARCISISMO'))]]), 3, {'lucia': base}, [1920, 1080])


def utileria_domestica():
    # Slots heredados del catálogo que provocaron fachadas verdes y cunas de neón.
    def rect(x, y, w, h, relleno):
        return dict(tipo='rectangulo', x=x, y=y, w=w, h=h, relleno=relleno, trazo='$contorno', grosor=4)
    casa = dict(concepto='casa', nombre='Casa', descripcion='Fachada, tejado y puerta.', etiquetas=['casa'],
        ancho=400, alto=300, partes=[
            dict(id='fachada', formas=[rect(40, 100, 320, 190, '$principal')]),
            dict(id='tejado', formas=[dict(tipo='trazo', comandos=[['M', 15, 105], ['L', 200, 10],
                ['L', 385, 105], ['Z']], relleno='$secundario', trazo='$contorno', grosor=4)]),
            dict(id='puerta', formas=[rect(175, 190, 50, 100, '$secundario')])])
    cuna = dict(concepto='cuna', nombre='Cuna con bebé', descripcion='Madera, colchón y bebé envuelto.',
        etiquetas=['cuna', 'bebé'], ancho=400, alto=300, partes=[
            dict(id='estructura', formas=[rect(15, 90, 370, 180, '$principal'), rect(30, 105, 340, 115, '$claro')]),
            dict(id='bebe', formas=[dict(tipo='elipse', x=140, y=140, w=180, h=65, relleno='$secundario', trazo='$contorno'),
                dict(tipo='elipse', x=70, y=125, w=85, h=85, relleno='#EBCDB2', trazo='$contorno'),
                rect(93, 153, 5, 6, '$contorno'), rect(126, 153, 5, 6, '$contorno')]),
            dict(id='barrotes', formas=[rect(x, 220, 8, 70, '$principal') for x in (20, 90, 160, 230, 300, 372)])])
    return dict(casa=casa, cuna=cuna)


class Stickman(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TEMP.name)
        self.addCleanup(self.temp.cleanup)
        self.entorno = patch.dict(os.environ, ESTUDIO_UTILERIA_STICKMAN=str(Path(self.temp.name) / 'catalogo'))
        self.entorno.start()
        self.addCleanup(self.entorno.stop)
        self.base = stickman.familias()[0]
        self.config = dict(seleccionada=0, variantes=stickman.familias())

    def test_edicion_conserva_plan_publicado_y_conversacion_sin_generar(self):
        from pasos import edicion_stickman as editor
        p = Proyecto.crear(self.temp.name, 'Retoque')
        estado = Estado(p)
        e = dict(id='S001', narracion='El personaje saluda.', t_in=0, t_out=3)
        contenido = stickman.escena(dict(personajes=[dict(id='ana', escala=2.6, y=.9,
            claves=[dict(t=0, pose='stand'), dict(t=2, pose='wave')])]), 3, {'ana': self.base})
        carpeta = Path(p.ruta_trabajo('assets')) / 'escenas'
        medios.escribir_json(str(carpeta / 'S001.json'), dict(origen='stickman', narracion=e['narracion'], firma_stickman='original'))
        medios.escribir_json(str(carpeta / 'S001.animacion.json'), dict(firma='original', contenido=contenido))
        estado.completar('assets', {})
        escena, original = editor.fuente(p, dict(escenas=[e]), 'S001')
        with patch.object(stickman, '_consultar', return_value={'mensaje': 'Alejaré el zoom sin cambiar la actuación.'}), \
                patch.object(stickman, 'renderizar') as render:
            charla = editor.conversar(p, escena, original, 'Aleja el zoom', lambda *a: None)
            render.assert_not_called()
        self.assertEqual(len(charla['mensajes']), 2)
        encargo = editor.encargo(p, escena, original, 'Conserva los colores', 50)
        self.assertEqual(encargo['proveedor'], 'ChatGPT')
        self.assertEqual(editor.encargo(p, escena, original, '', 40)['proveedor'], 'Claude')
        self.assertEqual(encargo['contenido'], contenido)
        self.assertEqual(encargo['mensajes'][-1]['texto'], 'Conserva los colores')
        contexto = dict(e, indicaciones_usuario=dict(edicion_stickman=encargo))
        with patch.dict(os.environ, ESTUDIO_SIMULAR='0'), \
                patch.object(stickman, '_consultar', return_value=contenido) as consultar:
            stickman.generar_escena(contexto, self.base, {'ana': self.base}, p, lambda *a: None, 'ChatGPT')
        self.assertTrue(consultar.call_args.args[0].startswith('EDITA'))
        self.assertIn('Aleja el zoom', consultar.call_args.args[0])
        self.assertIn('wave', consultar.call_args.args[0])
        with self.assertRaisesRegex(ValueError, 'genera primero'):
            editor.fuente(p, dict(escenas=[dict(e, narracion='Texto nuevo')]), 'S001')
        self.assertEqual(editor.leer(p, dict(e, narracion='Texto nuevo'))['mensajes'], [])
        copia = p.duplicar(str(Path(self.temp.name) / 'copias'), 'Copia')
        self.assertEqual(editor.leer(copia, e), charla)

    def test_tiempos_decimales_se_ajustan_al_limite_sin_admitir_excesos_reales(self):
        duracion=3.8029999999999973
        d=dict(personajes=[dict(id='ana',claves=[dict(t=0,pose='stand'),dict(t=3.803,pose='wave')])],
            camara=[dict(t=3.803,escala=1)],
            objetos=[dict(tipo='texto',texto='Final',fin=3.803,claves=[dict(t=3.803,opacidad=0)])],
            sfx=[dict(name='pop',at=0,dur=3.803)],
            graficos=[dict(tipo='badge',inicio=0,fin=3.803)],
            palabras=[dict(word='Final',start=0,end=3.803)])
        r=stickman.escena(d,duracion,{'ana':self.base})
        for fin in (r['personajes'][0]['claves'][-1]['t'],r['camara'][0]['t'],
                r['objetos'][0]['fin'],r['objetos'][0]['claves'][0]['t'],r['sfx'][0]['dur'],
                r['graficos'][0]['fin'],r['palabras'][0]['end']):
            self.assertEqual(fin,duracion)
        self.assertEqual(utileria_stickman.claves([dict(t=3.803,rot=1)],duracion)[0]['t'],duracion)
        for valor in (3.804,-.001,float('nan'),float('inf'),True):
            d['objetos'][0]['fin']=valor
            with self.subTest(valor=valor),self.assertRaisesRegex(ValueError,r'objetos\[0\]\.fin: tiempo'):
                stickman.escena(d,duracion,{'ana':self.base})

    def test_estilo_viaja_por_preset_y_no_modifica_historicos(self):
        cambios = presets_canal.cambios_para(dict(tipo='estilo', datos=dict(stickman=self.config)))
        self.assertEqual(cambios['assets']['estilo']['stickman'], self.config)
        reconstruida = presets_canal.datos_de_params(cambios)
        self.assertEqual(reconstruida['estilo']['stickman'], self.config)
        viejo = dict(assets=dict(estilo=dict(prompt='mi estilo')))
        antes = copy.deepcopy(viejo)
        presets_canal.datos_de_params(viejo)
        self.assertEqual(viejo, antes)
        e = presets_light.validar_encargo(dict(nombre='Stickman', idioma='es', tono_prompt='Cercano y educativo',
            stickman=self.config, montaje=dict(incorporar_voz=False)))
        self.assertTrue(e['montaje']['generar_personajes'])
        self.assertEqual(presets_light.plan_de(e)['imagenes'], 0)

    def test_rechaza_datos_que_no_se_pueden_animar(self):
        for datos in (dict(self.base, familia='foto'), dict(self.base, altura=float('nan')),
                      dict(self.base, color='url(x)'), dict(self.base, cabeza=30)):
            with self.assertRaises(ValueError):
                stickman.variante(datos)
        with self.assertRaises(ValueError):
            stickman.escena(dict(personajes=[dict(id='inventado')]), 2, {'real': self.base})
        with self.assertRaises(ValueError):
            stickman.escena(dict(sfx=[dict(name='pop', at=4)]), 2, {'real': self.base})

    def test_reparto_asigna_los_restos_a_claude_y_respeta_extremos(self):
        for total, porcentaje_claude, esperado in ((7, 50, (4, 3)), (3, 10, (1, 2)),
                (10, 30, (3, 7)), (7, 0, (0, 7)), (7, 100, (7, 0)), (1, 50, (1, 0)), (0, 50, (0, 0))):
            with self.subTest(total=total, porcentaje_claude=porcentaje_claude):
                self.assertEqual(stickman.reparto_escenas(total, porcentaje_claude), esperado)

    def test_utileria_anclada_y_secuencia_del_relato(self):
        contenido = escena_mensajes(self.base)
        self.assertEqual(contenido['objetos'][0]['ancla'], dict(personaje='lucia', punto='mano'))
        self.assertEqual(contenido['objetos'][1]['h'], 0)
        self.assertEqual(contenido['objetos'][1]['claves'][-1]['opacidad'], .15)
        self.assertEqual(contenido['objetos'][-1]['inicio'], 4.5)
        with self.assertRaises(ValueError):
            stickman.escena(dict(objetos=[dict(tipo='movil', ancla=dict(personaje='ausente'))]), 6, {'lucia': self.base})

    def test_direccion_por_frase_viaja_del_guion_al_plan_sin_reiniciar_el_bloque(self):
        from pasos import p3_guion
        opciones = dict(sistema_personajes=dict(stickman=True, generar_personajes=True))
        visuales = [dict(texto='El niño pide consuelo.', descripcion_visual='El niño levanta los brazos.', personajes_visibles=['auto_nino']),
            dict(texto='El cuidador responde.', descripcion_visual='El cuidador se arrodilla junto al niño y extiende los brazos.',
                 personajes_visibles=['auto_nino', 'auto_cuidador'])]
        bloque = dict(id='B001', texto='El niño pide consuelo. El cuidador responde.', personaje_id='',
            personajes_visibles=['auto_nino', 'auto_cuidador'], descripcion_visual='Secuencia completa de consuelo.', escenas_visuales=visuales)
        datos = dict(bloques=[bloque], personajes_automaticos=[dict(id='auto_nino', nombre='Niño', descripcion='Niño pequeño'),
            dict(id='auto_cuidador', nombre='Cuidador', descripcion='Adulto que cuida al niño')])
        bloques = p3_guion._normalizar_bloques(datos)
        personajes.preparar_intervenciones(datos, bloques, opciones)
        escenas = [dict(id=f'S00{i+1}', narracion=v['texto'], origen=dict(bloque='B001')) for i, v in enumerate(visuales)]
        personajes.aplicar_a_escenas(escenas, dict(guion=bloques), opciones)
        self.assertEqual([e['prompt'] for e in escenas], [v['descripcion_visual'] for v in visuales])
        self.assertEqual(escenas[0]['personajes'], ['auto_nino'])
        self.assertEqual(escenas[1]['intervencion']['descripcion_visual'], visuales[1]['descripcion_visual'])
        # Regrabar/editar la frase no debe aplicar una dirección de texto anterior.
        editada = dict(id='S003', narracion='El cuidador se aleja.', origen=dict(bloque='B001'), prompt='El adulto retrocede.')
        personajes.aplicar_a_escenas([editada], dict(guion=bloques), opciones)
        self.assertEqual(editada['prompt'], 'El adulto retrocede.')
        for cambio in (dict(escenas_visuales=visuales[:1]),
                dict(escenas_visuales=[visuales[0], dict(visuales[1], texto='Otra frase.')]),
                dict(escenas_visuales=[visuales[0], dict(visuales[1], descripcion_visual=visuales[0]['descripcion_visual'])])):
            with self.subTest(cambio=cambio), self.assertRaises(ValueError):
                personajes.preparar_intervenciones(datos, [dict(bloque, **cambio)], opciones)

    def test_pizarra_y_tarjetas_tienen_tipo_propio_sin_romper_primitivas_antiguas(self):
        contenido = stickman.escena(dict(objetos=[dict(tipo='pizarra', w=1200, h=550),
            dict(tipo='tarjeta', w=360, h=240), dict(tipo='rectangulo')]), 3, {})
        self.assertEqual([o['tipo'] for o in contenido['objetos']], ['pizarra', 'tarjeta', 'rectangulo'])

    def test_continuidad_del_decorado_retoma_y_cruza_proveedores_sin_cruzar_bloques(self):
        from pasos import p6_assets
        p = Proyecto.crear(self.temp.name, 'Continuidad B004')
        params = dict(estilo=dict(stickman=self.config), bibliotecas=dict(carga_claude=50))
        escenas = [dict(id=f'S00{i+1}', narracion=f'Frase {i+1}.', prompt=descripcion,
            origen=dict(bloque='B004' if i < 3 else 'B005'), t_in=i*3, t_out=(i+1)*3)
            for i, descripcion in enumerate(['Escenario rojo con dos focos.', 'Se intensifica el foco izquierdo.',
                'Ahora se ilumina el derecho.', 'Otro lugar.'])]
        plan = dict(escenas=escenas, assets={}, dependencias={}, resolucion=[1920, 1080],
            conservacion=dict(retirados=[]), duracion_total=12)
        raiz = stickman.escena(dict(ambiente='interiorWarm', decorado='vacio',
            realizacion=dict(encuadre='general',escenario=dict(id='telon_rojo',tipo='teatro',semilla=9)),
            personajes=[dict(id='protagonista', claves=[dict(t=0, pose='think'), dict(t=3, x=.6, pose='point')])],
            objetos=[dict(tipo='rectangulo', color='#882222', capa='fondo', w=1920, h=700),
                *[dict(tipo='circulo', color='#ffe0aa', x=x, y=.85, w=400, h=90) for x in (.25, .75)]]),
            3, {'protagonista': self.base})
        segunda = copy.deepcopy(raiz)
        segunda['objetos'][1]['opacidad'] = .9
        segunda['personajes'][0]['claves'][-1]['x'] = .7
        def render(diseno, contenido, duracion, png, clip, *a, **kw):
            Path(png).write_bytes(b'poster')
            Path(clip).write_bytes(b'clip')
        with patch.object(p6_assets, 'planificar', side_effect=lambda *a, **kw: copy.deepcopy(plan)), \
                patch.object(p6_assets, '_catalogo_de', return_value={}), \
                patch.object(stickman, 'renderizar', side_effect=render), \
                patch.object(stickman, '_sonidos', return_value=[]):
            with patch.object(stickman, 'generar_escena', side_effect=[raiz, RuntimeError('interrupción')]):
                with self.assertRaisesRegex(RuntimeError, 'interrupción'):
                    stickman.ejecutar(p, params, lambda *a: None)
            with patch.object(stickman, 'generar_escena', side_effect=[segunda, segunda, raiz]) as generar:
                stickman.ejecutar(p, params, lambda *a: None)
            self.assertEqual(generar.call_count, 3)  # La raíz publicada se recupera del disco.
            contexto2 = generar.call_args_list[0].args[0]['continuidad_bloque']
            contexto3 = generar.call_args_list[1].args[0]['continuidad_bloque']
            self.assertEqual(contexto2['raiz'], stickman.memoria_visual(escenas[0], raiz))
            self.assertEqual(contexto2['anterior'], contexto2['raiz'])
            self.assertEqual(contexto3['raiz'], contexto2['raiz'])
            self.assertEqual(contexto3['anterior'], stickman.memoria_visual(escenas[1], segunda))
            self.assertEqual(contexto3['escenas'][0]['descripcion_visual'], escenas[0]['prompt'])
            self.assertEqual([c.args[-1] for c in generar.call_args_list], ['Claude', 'ChatGPT', 'ChatGPT'])
            nuevo = generar.call_args_list[2].args[0]['continuidad_bloque']
            self.assertIsNone(nuevo['raiz'])
            self.assertIsNone(nuevo['anterior'])
            self.assertEqual(generar.call_args_list[2].args[0]['escenarios_video'],
                [dict(id='telon_rojo',tipo='teatro',semilla=9)])
            # Regenerar solo la tercera también recupera raíz y anterior.
            with patch.object(stickman, 'generar_escena', return_value=segunda) as generar:
                stickman.ejecutar(p, params, lambda *a: None, unidades=['escena:S003'], rehacer=True)
            self.assertEqual(generar.call_count, 1)
            self.assertEqual(generar.call_args.args[0]['continuidad_bloque'], contexto3)
        # El contexto llega al prompt del adaptador común a ambos proveedores.
        e = dict(escenas[2], continuidad_bloque=contexto3)
        with patch.dict(os.environ, ESTUDIO_SIMULAR='0'), \
                patch.object(stickman, '_consultar', return_value=segunda) as consultar:
            stickman.generar_escena(e, self.base, {'protagonista': self.base}, p, lambda *a: None, 'ChatGPT')
        prompt = consultar.call_args.args[0]
        self.assertIn('Escenario rojo con dos focos.', prompt)
        self.assertIn('#882222', prompt)
        self.assertIn('estado final', prompt)

    def test_entregas_invalidas_no_bloquean_otras_escenas_y_reintento_selectivo(self):
        from pasos import p6_assets
        p = Proyecto.crear(self.temp.name, 'Tanda con huecos')
        params = dict(estilo=dict(stickman=self.config))
        escenas = [dict(id=f'S00{i+1}', narracion=f'Frase {i+1}.', prompt='Saluda.',
            origen=dict(bloque='B001'), t_in=i*3, t_out=(i+1)*3) for i in range(4)]
        plan = dict(escenas=escenas, assets={}, dependencias={}, resolucion=[1920, 1080],
            conservacion=dict(retirados=[]), duracion_total=12)
        contenido = stickman.escena(dict(personajes=[dict(id='protagonista',
            claves=[dict(t=0, pose='stand'), dict(t=2, pose='wave')])]), 3, {'protagonista': self.base})
        def render(diseno, contenido, duracion, png, clip, *a, **kw):
            Path(png).write_bytes(b'poster')
            Path(clip).write_bytes(b'clip')
        avisos = []
        with patch.object(p6_assets, 'planificar', side_effect=lambda *a, **kw: copy.deepcopy(plan)), \
                patch.object(p6_assets, '_catalogo_de', return_value={}), \
                patch.object(stickman, 'renderizar', side_effect=render) as motor, \
                patch.object(stickman, '_sonidos', return_value=[]):
            # Se recorre la tanda entera y se informa de todos los huecos al final.
            fallo = stickman.ErrorValidacion('una parte solo anima t,x,y,rot,escala,opacidad')
            with patch.object(stickman, 'generar_escena', side_effect=[contenido, fallo, fallo, contenido]) as generar:
                with self.assertRaises(stickman.ErrorEscenas) as error:
                    stickman.ejecutar(p, params, lambda f, msg: avisos.append(msg))
            self.assertEqual([c.args[0]['id'] for c in generar.call_args_list], [e['id'] for e in escenas])
            self.assertEqual(set(error.exception.errores), {'S002', 'S003'})
            self.assertIn('t,x,y,rot,escala,opacidad', str(error.exception))
            self.assertEqual(motor.call_count, 2)
            trabajo = Path(p.ruta_trabajo('assets'))
            self.assertFalse((trabajo / 'escenas/S002.json').exists())
            self.assertFalse((trabajo / 'escenas/S003.json').exists())
            self.assertIsNone(p.version_activa('assets'))
            previa = copy.deepcopy(plan)
            previa['estilo'] = params['estilo']
            stickman.aplicar_recursos(p, previa)
            self.assertEqual([e['id'] for e in previa['escenas'] if e.get('stickman')], ['S001', 'S004'])
            self.assertTrue(any('S002' in msg and 'Continuando' in msg for msg in avisos))
            publicados = {sid: (trabajo / f'escenas/{sid}.json').read_bytes() for sid in ('S001', 'S004')}
            # Reintentar los huecos conserva incluso las escenas posteriores.
            with patch.object(stickman, 'generar_escena', return_value=contenido) as generar:
                resultado = stickman.ejecutar(p, params, lambda *a: None,
                    unidades=['escena:S002', 'escena:S003'])
            self.assertEqual([c.args[0]['id'] for c in generar.call_args_list], ['S002', 'S003'])
            self.assertEqual(set(resultado['unidades']), {'escena:S002', 'escena:S003'})
            for sid, recibo in publicados.items():
                self.assertEqual((trabajo / f'escenas/{sid}.json').read_bytes(), recibo)
            # Los errores globales y Parar no se convierten en fallos locales.
            from nucleo.trabajos import Cancelado
            from pasos.cli_claude import LimiteAgotado
            for fallo in (Cancelado('parar'), LimiteAgotado('sin cuota'), RuntimeError('motor')):
                with self.subTest(fallo=type(fallo).__name__), \
                        patch.object(stickman, 'generar_escena', side_effect=fallo) as generar:
                    with self.assertRaises(type(fallo)):
                        stickman.ejecutar(p, params, lambda *a: None, rehacer=True)
                    self.assertEqual(generar.call_count, 1)

    def test_consultar_distingue_entrega_invalida_tras_agotar_correcciones(self):
        with patch.object(stickman, '_consultar', return_value={}) as consulta:
            with self.assertRaisesRegex(stickman.ErrorValidacion, 'falta contenido'):
                stickman.consultar('escena', validar=lambda d: (_ for _ in ()).throw(ValueError('falta contenido')))
        self.assertEqual(consulta.call_count, 3)

    def test_puesta_en_escena_corrige_personajes_ilegibles_y_no_acepta_estaticos(self):
        validar = lambda d: stickman.validar_puesta_en_escena(d, 6, {'ana': self.base}, [1920, 1080])
        for actor in (dict(escala=.4), dict(x=.99), dict(y=.4, escala=3)):
            with self.subTest(actor=actor), self.assertRaisesRegex(ValueError, 'encuadre'):
                validar(dict(personajes=[dict(id='ana', **actor)]))
        with self.assertRaisesRegex(ValueError, 'estática'):
            validar(dict(personajes=[dict(id='ana', claves=[dict(t=0, pose='stand'), dict(t=2, pose='stand')])]))
        self.assertEqual(validar(dict(personajes=[dict(id='ana', movimiento='caminar',
            claves=[dict(t=0,x=.2),dict(t=2,x=.5)])]))['personajes'][0]['movimiento'], 'caminar')
        with patch.object(stickman, '_consultar', side_effect=[dict(personajes=[dict(id='ana', escala=.4)]),
                dict(personajes=[dict(id='ana', claves=[dict(t=0, pose='stand'), dict(t=2, pose='phone')])])]) as consulta:
            resultado = stickman.consultar('escena', validar=validar)
        self.assertEqual(consulta.call_count, 2)
        self.assertEqual(resultado['personajes'][0]['claves'][-1]['pose'], 'phone')

    def test_corrige_contrato_sin_reintentar_cancelaciones_o_cuota(self):
        validar = lambda d: stickman.escena(d, 2, {'real': self.base})
        with patch.object(stickman, '_consultar', side_effect=[dict(personajes=[dict(id='inexistente')]),
                dict(personajes=[dict(id='real')])]) as consulta:
            resultado = stickman.consultar('encargo', validar=validar)
            self.assertEqual(consulta.call_count, 2)
            self.assertEqual(resultado['personajes'][0]['id'], 'real')
        with patch.object(stickman, '_consultar', side_effect=RuntimeError('cancelado')) as consulta:
            with self.assertRaisesRegex(RuntimeError, 'cancelado'):
                stickman.consultar('encargo', validar=validar)
            self.assertEqual(consulta.call_count, 1)

    def test_crea_utileria_y_la_reutiliza_en_otro_video_y_otro_estilo(self):
        primero = Proyecto.crear(self.temp.name, 'Viajes')
        segundo = Proyecto.crear(self.temp.name, 'Historia de la aviación')
        e = dict(id='S001', narracion='El avión despega.', t_in=0, t_out=3)
        objeto = dict(tipo='vector', recurso='avión', x=.5, y=.4, w=650, h=325,
            paleta=dict(principal='#b6bfc4', secundario='#78929d', claro='#f5f2eb', oscuro='#27313a'),
            claves=[dict(t=0, x=.3), dict(t=3, x=.7)])
        entrega = dict(utileria=dict(avion=avion_vectorial()), objetos=[objeto])
        with patch.dict(os.environ, ESTUDIO_SIMULAR='0'), patch.object(stickman, '_consultar', side_effect=[dict(objetos=[objeto]), entrega, dict(objetos=[objeto])]) as consulta:
            nueva = stickman.generar_escena(e, self.base, {'ana': self.base}, primero, lambda *a: None)
            otro_estilo = dict(self.base, color='#fa6b32')
            reutilizada = stickman.generar_escena(e, otro_estilo, {'ana': otro_estilo}, segundo, lambda *a: None, 'ChatGPT')
        ident = nueva['objetos'][0]['recurso']
        self.assertEqual(reutilizada['objetos'][0]['recurso'], ident)
        self.assertEqual(nueva['utileria'], reutilizada['utileria'])
        self.assertEqual(len(list(utileria_stickman.carpeta_catalogo().glob('*.json'))), 1)
        self.assertEqual(consulta.call_count, 3)
        self.assertIn('falta utilería', consulta.call_args_list[1].args[0])
        self.assertIn(ident, consulta.call_args_list[2].args[0])
        self.assertIn('catalogo_utileria', consulta.call_args_list[2].args[0])

    def test_colores_domesticos_explicitos_corrigen_herencia_del_estilo(self):
        recursos = {d['id']: d for d in map(utileria_stickman.definicion, utileria_domestica().values())}
        utileria_stickman.guardar(recursos)
        objetos = [dict(tipo='vector', recurso=k, x=x, y=.5, w=650, h=490,
            claves=[dict(t=0, opacidad=.8), dict(t=2, opacidad=1)]) for k, x in (('casa', .25), ('cuna', .75))]
        corregidos = copy.deepcopy(objetos)
        corregidos[0]['paleta'] = dict(principal='#e5d8c1', secundario='#925540', contorno='#42382f')
        corregidos[1]['paleta'] = dict(principal='#b58b60', secundario='#b8c8c5', contorno='#42382f', claro='#faf6ed')
        with patch.dict(os.environ, ESTUDIO_SIMULAR='0'), patch.object(stickman, '_consultar',
                side_effect=[dict(objetos=objetos), dict(objetos=corregidos)]) as consulta:
            resultado = stickman.generar_escena(dict(t_in=0, t_out=3), self.base, {'ana': self.base}, None, lambda *a: None)
        self.assertEqual(consulta.call_count, 2)
        self.assertIn('Colores de «casa»', consulta.call_args.args[0])
        self.assertIn('colores por parte', consulta.call_args_list[0].args[0])
        for objeto, esperado in zip(resultado['objetos'], corregidos):
            self.assertEqual(objeto['paleta'], esperado['paleta'])
        self.assertEqual(utileria_stickman.catalogo(), recursos)  # Fichas inmutables.
        # La lectura histórica sigue admitiendo planes sin paleta; no invalida clips.
        historico = stickman.escena(dict(objetos=objetos), 3, {}, recursos)
        self.assertEqual(historico['objetos'][0]['paleta'], {})
        incompleta = copy.deepcopy(resultado)
        del incompleta['objetos'][1]['paleta']['contorno']
        with self.assertRaisesRegex(ValueError, 'cuna.*contorno'):
            utileria_stickman.validar_colores(incompleta)
        # Un dibujo con materiales fijos no necesita slots ni adoptar el estilo.
        fija = utileria_domestica()['casa']
        for p in fija['partes']:
            for f in p['formas']:
                f['relleno'], f['trazo'] = '#e5d8c1', '#42382f'
        utileria_stickman.validar_colores(stickman.escena(dict(utileria=dict(casa=fija),
            objetos=[dict(tipo='vector', recurso='casa')]), 3, {}))

    @unittest.skipUnless(REAL, 'usa --real para colores domésticos en Chromium')
    def test_render_materiales_no_heredan_colores_del_personaje(self):
        from PIL import Image
        contenido = stickman.escena(dict(decorado='vacio', utileria=utileria_domestica(), objetos=[
            dict(tipo='vector', recurso='casa', x=.25, y=.5, w=700, h=530,
                paleta=dict(principal='#e5d8c1', secundario='#925540', contorno='#42382f')),
            dict(tipo='vector', recurso='cuna', x=.75, y=.5, w=700, h=530,
                paleta=dict(principal='#b58b60', secundario='#b8c8c5', contorno='#42382f', claro='#faf6ed'))]), 3, {})
        utileria_stickman.validar_colores(contenido)
        for i, color in enumerate(('#00ff00', '#ff00ff')):
            png = Path(self.temp.name) / f'materiales-{i}.png'
            stickman.renderizar(dict(self.base, color=color, secundario='#0000ff', contorno='#ccff00'),
                contenido, 3, str(png), salida=(960, 540))
            with Image.open(png) as img:
                colores = {c for _, c in img.convert('RGB').getcolors(img.width * img.height)}
            for tinta in ('e5d8c1', '925540', 'b58b60', 'b8c8c5', 'faf6ed', 'ebcdb2', '42382f'):
                self.assertIn(tuple(bytes.fromhex(tinta)), colores)
            for tinta in ('00ff00', 'ff00ff', '0000ff', 'ccff00'):
                self.assertNotIn(tuple(bytes.fromhex(tinta)), colores)

    def test_catalogo_persistente_fuera_del_programa_tambien_en_servicio(self):
        datos = Path(self.temp.name) / 'datos'
        with patch.dict(os.environ, ESTUDIO_UTILERIA_STICKMAN='', ESTUDIO_BANCO=str(datos / 'banco')):
            self.assertEqual(utileria_stickman.carpeta_catalogo(), datos / 'utileria_stickman')
        with patch.dict(os.environ, ESTUDIO_UTILERIA_STICKMAN='', ESTUDIO_BANCO='', ESTUDIO_PROYECTOS=str(datos / 'proyectos')):
            self.assertEqual(utileria_stickman.carpeta_catalogo(), datos / 'utileria_stickman')

    def test_definiciones_fijadas_no_cambian_y_no_se_guardan_elementos_sin_usar(self):
        original = utileria_stickman.definicion(avion_vectorial())
        variante = utileria_stickman.definicion(dict(avion_vectorial(), descripcion='Otra versión de avión.'))
        datos = dict(utileria={original['id']: original}, objetos=[dict(tipo='vector', recurso=original['id'])])
        fija = stickman.escena(datos, 2, {}, {variante['id']: variante})
        self.assertEqual(fija['utileria'], {original['id']: original})
        # Una nueva entrega que redibuja el mismo concepto reutiliza el existente.
        redibujada = stickman.escena(dict(utileria=dict(avion=avion_vectorial()),
            objetos=[dict(tipo='vector', recurso='avion')]), 2, {}, {variante['id']: variante})
        self.assertEqual(redibujada['objetos'][0]['recurso'], variante['id'])
        sin_usar = stickman.escena(dict(utileria=dict(avion=avion_vectorial())), 2, {})
        self.assertEqual(sin_usar['utileria'], {})
        with self.assertRaisesRegex(ValueError, 'falta utilería'):
            stickman.escena(dict(objetos=[dict(tipo='vector', recurso='tren')]), 2, {})

    def test_utileria_rechaza_geometria_invalida_sin_publicarla(self):
        invalidos = []
        for cambio in (dict(comandos=[['M', 0, 0], ['C', 'alert(1)', 2, 3, 4, 5, 6]]),
                dict(comandos=[['M', 0, 0], ['L', 1001, 0]]), dict(relleno='url(https://ejemplo.com/a.svg)')):
            d = avion_vectorial()
            d['partes'][0]['formas'][0].update(cambio)
            invalidos.append(d)
        d = avion_vectorial()
        d['partes'][0]['animacion'] = dict(duracion=1, claves=[dict(t=2, rot=1)])
        invalidos.append(d)
        for d in invalidos:
            with self.subTest(datos=d), self.assertRaises(ValueError):
                utileria_stickman.definicion(d)
        entrega = dict(utileria=dict(avion=invalidos[0]), objetos=[dict(tipo='vector', recurso='avion')])
        with patch.dict(os.environ, ESTUDIO_SIMULAR='0'), patch.object(stickman, '_consultar', return_value=entrega):
            with self.assertRaises(ValueError):
                stickman.generar_escena(dict(t_in=0, t_out=3), self.base, {'ana': self.base}, None, lambda *a: None)
        self.assertEqual(utileria_stickman.catalogo(), {})

    def test_publicacion_concurrente_es_inmutable_y_el_catalogo_no_mueve_firmas(self):
        from concurrent.futures import ThreadPoolExecutor
        d = utileria_stickman.definicion(avion_vectorial())
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: utileria_stickman.guardar({d['id']: d}), range(8)))
        self.assertEqual(utileria_stickman.catalogo(), {d['id']: d})
        self.assertEqual(len(list(utileria_stickman.carpeta_catalogo().glob('*.json'))), 1)
        escena = stickman.escena(dict(objetos=[dict(tipo='vector', recurso=d['id'])]), 2, {}, utileria_stickman.catalogo())
        firma = stickman.huella(escena)
        otra = utileria_stickman.definicion(dict(avion_vectorial(), concepto='avioneta', nombre='Avioneta'))
        utileria_stickman.guardar({otra['id']: otra})
        self.assertEqual(stickman.huella(stickman.escena(escena, 2, {})), firma)

    def test_animacion_de_partes_y_busqueda_en_catalogo_grande(self):
        d = utileria_stickman.definicion(avion_vectorial())
        catalogo = {d['id']: d}
        for i in range(110):
            otra = utileria_stickman.definicion(dict(avion_vectorial(), concepto=f'objeto-{i}', nombre=f'Objeto {i}', etiquetas=[]))
            catalogo[otra['id']] = otra
        indice = utileria_stickman.indice(catalogo, 'El avión despega al empezar el viaje.', maximo=10)
        self.assertEqual(indice[0]['concepto'], 'avion')
        self.assertEqual(len(indice), 10)
        objeto = dict(tipo='vector', recurso='avion', partes=[dict(id='ala', claves=[dict(t=0, rot=0), dict(t=2, rot=.3)])])
        escena = stickman.validar_puesta_en_escena(dict(objetos=[objeto]), 2, {}, [1920, 1080], catalogo)
        self.assertEqual(escena['objetos'][0]['partes'][0]['id'], 'ala')
        objeto['partes'][0]['id'] = 'inexistente'
        with self.assertRaises(ValueError):
            stickman.escena(dict(objetos=[objeto]), 2, {}, catalogo)

    def test_personajes_no_admiten_pov_ni_foto_con_diseno_inventado(self):
        p = Proyecto.crear(self.temp.name, 'Personaje')
        f = dict(id='ana', nombre='Ana', descripcion='Profesora', categoria='personaje',
                 imagen='medios_usuario/animaciones/' + 'a' * 32 + '.png', stickman=self.base)
        from PIL import Image
        destino = Path(p.ruta(f['imagen']))
        destino.parent.mkdir(parents=True)
        Image.new('RGB', (32, 32)).save(destino)
        with self.assertRaises(ValueError):
            personajes.normalizar(dict(activo=True, items=[f]), p)
        medios.escribir_json(str(destino) + '.json', dict(stickman=self.base))
        normal = personajes.normalizar(dict(activo=True, items=[f]), p)
        self.assertEqual(normal['items'][0]['stickman'], self.base)
        with self.assertRaises(ValueError):
            personajes.normalizar(dict(activo=True, items=[dict(f, primera_persona=True)]), p)
        self.assertIsNone(personajes.personaje_pov(dict(sistema_personajes=dict(stickman=True, generar_personajes=True),
            personajes=dict(activo=True, items=[dict(f, primera_persona=True)]))))

    def test_sonidos_del_plugin_se_editan_y_se_mezclan_una_vez(self):
        contenido = stickman.escena(dict(sfx=[dict(name='pop', at=.2, dur=.12, gain=-12),
            dict(name='roomtone', at=0, dur=1, gain=-26)]), 1, {'ana': self.base})
        recursos = stickman._sonidos(contenido, self.temp.name, 'S001')
        e = dict(id='S001', t_in=3, t_out=4, narracion='Ana saluda.', sonidos_stickman=[
            dict(r, archivo=str(Path(self.temp.name) / r['archivo'])) for r in recursos])
        eventos = sonido.eventos([e], {}, {})
        self.assertEqual(len(eventos), 2)
        self.assertAlmostEqual(eventos[0]['t'], 0)
        fuentes, actual = sonido.bloques_de_escena([e], {}, {}, 'S001')
        self.assertIsNone(actual)
        self.assertEqual({f['nombre'] for f in fuentes}, {'pop', 'roomtone'})
        from pasos import animaciones
        ajuste = dict(ancla=animaciones.ancla_de(e), bloques=[dict(id='stickman:0', inicio=.5, fin=.6)])
        # El editor admite los mismos IDs que la pista de sonido del montaje.
        editor_escena.validar(dict(sonidos=ajuste), e, [1920, 1080])
        manual = sonido.eventos([e], {}, dict(unidades={'escena:S001': dict(sonidos=ajuste)}))
        self.assertEqual(len(manual), 1)
        self.assertAlmostEqual(manual[0]['t'], .5)
        salida = str(Path(self.temp.name) / 'efectos.wav')
        sonido.pista_de_efectos(eventos, 1, salida, igualar=False)
        from scipy.io import wavfile
        _, pcm = wavfile.read(salida)
        self.assertGreater(abs(pcm).max(), 0)

    def test_todos_los_efectos_del_plugin_admiten_recortes_cortos(self):
        contenido = dict(sfx=[dict(name=n, dur=.1, at=0, gain=-20, seed=1, pitch=1) for n in stickman.EFECTOS])
        recursos = stickman._sonidos(contenido, self.temp.name, 'S001')
        self.assertEqual(len(recursos), len(stickman.EFECTOS))
        self.assertTrue(all((Path(self.temp.name) / r['archivo']).is_file() for r in recursos))

    def test_recurso_versionado_se_resuelve_tras_completar_y_no_por_id_solo(self):
        p = Proyecto.crear(self.temp.name, 'Recursos')
        estado = Estado(p)
        trabajo = Path(p.ruta_trabajo('assets'))
        (trabajo / 'escenas').mkdir()
        (trabajo / 'escenas/S001.mp4').write_bytes(b'clip')
        medios.escribir_json(str(trabajo / 'escenas/S001.json'), dict(origen='stickman', narracion='Ana saluda.',
            firma_stickman='firma', clip='escenas/S001.mp4', sonidos_stickman=[]))
        plan = dict(estilo=dict(stickman=self.config), escenas=[dict(id='S001', narracion='Ana saluda.')])
        stickman.aplicar_recursos(p, plan)
        self.assertIn('trabajo', plan['escenas'][0]['stickman']['clip'])
        estado.completar('assets', {})
        stickman.aplicar_recursos(p, plan)
        self.assertIn('v1', plan['escenas'][0]['stickman']['clip'])
        plan['escenas'][0]['narracion'] = 'Otro texto.'
        stickman.aplicar_recursos(p, plan)
        self.assertNotIn('stickman', plan['escenas'][0])

    @unittest.skipUnless(REAL, 'usa --real para Chromium y ffmpeg')
    def test_creacion_y_edicion_del_estilo_conservan_las_referencias(self):
        import app
        app.fijar_raiz_proyectos(self.temp.name)
        encargo = presets_light.validar_encargo(dict(nombre='Estilo completo', idioma='es',
            tono_prompt='Narrativo y cercano.', stickman=self.config, montaje=dict(incorporar_voz=False)))
        ctx = app._crear_taller(encargo)
        app._sembrar_taller(ctx, encargo)
        def tono(avisar, ctx, encargo):
            ctx.estado.actualizar_params('brief', dict(instrucciones=encargo['tono_prompt']))
        with patch.dict(app._LIGHT_QUE_HACE, tono=tono):
            resultado = app._correr_preset_light(lambda *a: None, ctx, encargo, None, None)
        preset = presets_canal.leer(resultado['preset'])
        anteriores = preset['datos']['estilo']['referencias']
        config = dict(self.config, seleccionada=2)
        editado = app.editar_preset_light(preset['id'], dict(stickman=config))['preset']
        self.assertEqual(editado['datos']['estilo']['stickman']['seleccionada'], 2)
        self.assertTrue(all(Path(r).is_file() for r in anteriores))
        self.assertTrue(all(Path(r).is_file() for r in editado['datos']['estilo']['referencias']))

    @unittest.skipUnless(REAL, 'usa --real para Chromium y ffmpeg')
    def test_pipeline_interrumpido_retoma_y_monta_con_los_sonidos(self):
        from pasos import p6_assets, p7_callouts, p8_render
        import wave
        p = Proyecto.crear(self.temp.name, 'Pipeline')
        estado = Estado(p)
        voz = Path(p.ruta_trabajo('voz'))
        with wave.open(str(voz / 'narracion.wav'), 'wb') as wav:
            wav.setparams((2, 2, 48000, 0, 'NONE', 'not compressed'))
            wav.writeframes(b'\0' * (2 * 48000 * 4))
        estado.completar('voz', dict(wav='narracion.wav'))
        params = dict(estilo=dict(stickman=self.config), generar_personajes=True)
        estado.actualizar_params('assets', params)
        escenas = [dict(id=f'S00{i+1}', narracion=t, t_in=i, t_out=i+1, duracion=1,
                       marcas=[[i+.1, i+.8]], personajes=[], transicion='corte')
                   for i, t in enumerate(['Ana saluda.', 'Ana señala.'])]
        plan = dict(estilo=params['estilo'], escenas=escenas, assets={}, dependencias={e['id']: [] for e in escenas},
            conservacion=dict(retirados=[]), resolucion=[320, 180], generacion=[320, 180],
            duracion_total=2, idioma='es', semilla=7, fps=30, formato='horizontal')
        contenido = stickman.escena(dict(personajes=[dict(id='protagonista')],
            realizacion=dict(encuadre='general',escenario=dict(id='laboratorio_prueba',tipo='laboratorio'),acabado=True),
            graficos=[dict(tipo='callout',opciones=dict(str='El avión',at=[1200,200],to=[1400,300]))],
            utileria=dict(avion=avion_vectorial()), objetos=[dict(tipo='vector', recurso='avion', x=.65, y=.18, w=300, h=150)],
            sfx=[dict(name='pop', at=.3, dur=.4, gain=-12)]), 1, {'protagonista': self.base})
        with patch.object(p6_assets, 'planificar', side_effect=lambda *a, **k: copy.deepcopy(plan)), \
             patch.object(stickman, 'generar_escena', side_effect=[contenido, RuntimeError('interrupción')]):
            with self.assertRaisesRegex(RuntimeError, 'interrupción'):
                p6_assets.ejecutar(p, params)
        parcial = stickman.aplicar_recursos(p, copy.deepcopy(plan))
        self.assertTrue(parcial['escenas'][0].get('stickman'))
        self.assertFalse(parcial['escenas'][1].get('stickman'))
        with patch.object(p6_assets, 'planificar', side_effect=lambda *a, **k: copy.deepcopy(plan)), \
             patch.object(stickman, 'generar_escena', return_value=contenido) as generar:
            resultado = p6_assets.ejecutar(p, params)
            self.assertEqual(generar.call_count, 1)
        estado.completar('assets', resultado['salidas'], resultado['unidades'])
        capas = p7_callouts.ejecutar(p, dict(previsualizar=False, escala_hyper=1))
        estado.completar('callouts', capas['salidas'], capas['unidades'])
        render = p8_render.ejecutar(p, dict(resolucion=[320, 180], fps=12, lotes=1, subtitulos=False))
        final = Path(p.ruta_trabajo('render')) / render['salidas']['mp4']
        self.assertTrue(final.is_file())
        # Narración muda: cualquier energía audible tiene que venir de los efectos.
        audio = subprocess.run([medios.ffmpeg(), '-v', 'error', '-i', str(final), '-f', 'f32le', '-ac', '1', '-'],
            capture_output=True, check=True).stdout
        import numpy as np
        self.assertGreater(np.abs(np.frombuffer(audio, dtype=np.float32)).max(), .001)
        estado.completar('render', render['salidas'], render['unidades'])
        from pasos import paquete_video
        archivo = str(Path(self.temp.name) / 'animacion.video.zip')
        paquete_video.exportar(p, archivo)
        destino = Path(self.temp.name) / 'importados'
        destino.mkdir()
        importado = paquete_video.importar(archivo, str(destino))
        recuperado = stickman.aplicar_recursos(importado, copy.deepcopy(plan))
        for e in recuperado['escenas']:
            self.assertTrue(Path(e['stickman']['clip']).is_relative_to(Path(importado.raiz)))
            self.assertTrue(Path(e['sonidos_stickman'][0]['archivo']).is_file())
        ident = contenido['objetos'][0]['recurso']
        # Otro servidor, sin acceso al catálogo original: las instantáneas de
        # la versión permiten retomar y volver a compartir el objeto.
        with patch.dict(os.environ, ESTUDIO_UTILERIA_STICKMAN=str(Path(self.temp.name) / 'otro_catalogo')):
            self.assertEqual(utileria_stickman.catalogo(), {})
            self.assertIn(ident, utileria_stickman.catalogo(importado))
            fuente = medios.leer_json(str(Path(importado.ruta_paso('assets')) / 'escenas/S001.animacion.json'))
            self.assertEqual(fuente['contenido']['utileria'][ident], contenido['utileria'][ident])
            utileria_stickman.guardar(fuente['contenido']['utileria'])
            self.assertIn(ident, utileria_stickman.catalogo())
        copia = p.duplicar(str(Path(self.temp.name) / 'copias'), 'Copia con avión')
        self.assertTrue((Path(copia.ruta_paso('assets')) / 'utileria_stickman' / (ident + '.json')).is_file())

    @unittest.skipUnless(REAL, 'usa --real para Chromium y ffmpeg')
    def test_giro_del_actor_y_ancla_pecho_por_debajo_del_cuello(self):
        from pasos import p8_render
        contenido = stickman.escena(dict(personajes=[dict(id='ana', y=.9, escala=2.6,
            claves=[dict(t=0, pose='stand'), dict(t=1, mirar=-1)])],
            objetos=[dict(tipo='circulo', color='#ed1234', w=40, h=40, ancla=dict(personaje='ana', punto='pecho'))]),
            2, {'ana': self.base})
        original = p8_render.Navegador.capturar
        def comprobar(navegador, destino=None):
            resultado = navegador.evaluar('''(() => {
                const ctx = document.querySelector('canvas').getContext('2d');
                const scale = ctx.scale, ellipse = ctx.ellipse;
                let escalas = [], pecho = [];
                ctx.scale = function(x,y) { escalas.push([x,y]); return scale.call(this,x,y); };
                ctx.ellipse = function(...args) {
                    if (this.fillStyle === '#ed1234') pecho.push(this.getTransform().f);
                    return ellipse.apply(this,args);
                };
                try {
                    window.pintar(0); const inicio=escalas; escalas=[];
                    window.pintar(1.5); return {inicio, fin:escalas, pecho};
                } finally {ctx.scale=scale; ctx.ellipse=ellipse;}
            })()''')
            self.assertIn([2.6, 2.6], resultado['inicio'])
            self.assertIn([-2.6, 2.6], resultado['fin'])
            self.assertTrue(all(280 < y < 325 for y in resultado['pecho']))
            self.assertEqual(len(resultado['pecho']), 2)
            return original(navegador, destino)
        with patch.object(p8_render.Navegador, 'capturar', comprobar):
            stickman.renderizar(self.base, contenido, 2, str(Path(self.temp.name) / 'pecho.png'), salida=(960, 540))

    @unittest.skipUnless(REAL, 'usa --real para Chromium y ffmpeg')
    def test_render_pizarra_con_marco_bandeja_y_tarjetas_legibles(self):
        from PIL import Image
        png = Path(self.temp.name) / 'pizarra.png'
        stickman.renderizar(self.base, escena_pizarra(self.base), 3, str(png), salida=(960, 540))
        with Image.open(png) as img:
            colores = {c for _, c in img.convert('RGB').getcolors(img.width * img.height)}
        for color in ((121, 83, 59), (186, 145, 107), (40, 82, 71), (255, 248, 238)):
            self.assertIn(color, colores)

    @unittest.skipUnless(REAL, 'usa --real para Chromium y ffmpeg')
    def test_render_vectorial_con_curvas_paleta_y_partes_animadas(self):
        from pasos import p8_render
        from PIL import Image
        contenido = stickman.escena(dict(decorado='vacio', ambiente='day', utileria=dict(avion=avion_vectorial()),
            objetos=[dict(tipo='vector', recurso='avion', x=.5, y=.5, w=1450, h=725,
                partes=[dict(id='ala', claves=[dict(t=0, rot=0), dict(t=2, rot=.3)])])]), 3, {})
        original = p8_render.Navegador.capturar
        fotogramas = []
        def capturar(navegador, destino=None):
            for t in (0, .2, 2):
                navegador.pintar(t)
                fotogramas.append(original(navegador))
            navegador.pintar(1.35)
            return original(navegador, destino)
        png = Path(self.temp.name) / 'avion.png'
        with patch.object(p8_render.Navegador, 'capturar', capturar):
            stickman.renderizar(self.base, contenido, 3, str(png), salida=(640, 360))
        self.assertEqual(len(set(fotogramas)), 3)
        with Image.open(png) as img:
            colores = {c for _, c in img.convert('RGB').getcolors(img.width * img.height)}
        self.assertIn((66, 213, 120), colores)  # $principal del estilo, no fijado en el dibujo.
        otro = Path(self.temp.name) / 'avion-otro-estilo.png'
        stickman.renderizar(dict(self.base, color='#ff8030'), contenido, 3, str(otro), salida=(640, 360))
        with Image.open(otro) as img:
            self.assertIn((255, 128, 48), {c for _, c in img.convert('RGB').getcolors(img.width * img.height)})

    @unittest.skipUnless(REAL, 'usa --real para Chromium y ffmpeg')
    def test_render_relato_y_limites_del_texto_e_interpolacion(self):
        from pasos import p8_render
        contenido = escena_mensajes(self.base)
        contenido['objetos'].append(dict(tipo='texto', texto='Semanas', color='#ffffff', x=.5, y=.1,
            w=900, h=80, escala=1, inicio=0, fin=6, capa='frente', claves=[]))
        contenido = stickman.escena(contenido, 6, {'lucia': self.base, 'daniel': self.base})
        original = p8_render.Navegador.capturar
        def comprobar(navegador, destino=None):
            # Instrumentar Canvas real: comprueba el tamaño final de letra y que
            # la posición tardía de Daniel no se aplique desde el frame cero.
            resultado = navegador.evaluar('''(() => {
                const ctx = document.querySelector('canvas').getContext('2d');
                const translate = ctx.translate, fillText = ctx.fillText;
                let xs = [], fuentes = [];
                ctx.translate = function(x,y) { xs.push(x); return translate.call(this,x,y); };
                ctx.fillText = function(...args) { fuentes.push(this.font); return fillText.apply(this,args); };
                try {
                    window.pintar(0); const inicio = xs.includes(.73*1920); xs=[];
                    window.pintar(6); const fin = xs.includes(.79*1920);
                    return {inicio, fin, fuentes};
                } finally {ctx.translate=translate; ctx.fillText=fillText; window.pintar(2.7);}
            })()''')
            self.assertTrue(resultado['inicio'])
            self.assertTrue(resultado['fin'])
            self.assertTrue(all(float(f.split('px')[0].split()[-1]) <= 96 for f in resultado['fuentes']))
            return original(navegador, destino)
        with patch.object(p8_render.Navegador, 'capturar', comprobar):
            stickman.renderizar(self.base, contenido, 6, str(Path(self.temp.name) / 'relato.png'), salida=(640, 360))

    @unittest.skipUnless(REAL, 'usa --real para Chromium y ffmpeg')
    def test_render_real_familias_y_mp4_con_efectos_del_plugin(self):
        from PIL import Image
        imagenes = []
        for v in stickman.familias():
            png = str(Path(self.temp.name) / (v['familia'] + '.png'))
            stickman.renderizar(v, stickman.muestra(v), 2, png, salida=(320, 180))
            with Image.open(png) as img:
                imagenes.append(img.tobytes())
        self.assertEqual(len(set(imagenes)), 4)
        contenido = stickman.muestra(self.base)
        contenido['sfx'] = [dict(name='pop', at=.3, dur=.5, gain=-10, seed=1, pitch=1)]
        clip = str(Path(self.temp.name) / 'escena.mp4')
        stickman.renderizar(self.base, contenido, 2, str(Path(self.temp.name) / 'poster.png'), clip, salida=(320, 180), fps=12)
        recursos = stickman._sonidos(contenido, self.temp.name, 'S001')
        e = dict(id='S001', t_in=0, t_out=2, sonidos_stickman=[dict(s, archivo=str(Path(self.temp.name) / s['archivo'])) for s in recursos])
        audio = str(Path(self.temp.name) / 'audio.wav')
        sonido.pista_de_efectos(sonido.eventos([e], {}, {}), 2, audio, igualar=False)
        final = str(Path(self.temp.name) / 'final.mp4')
        subprocess.run([medios.ffmpeg(), '-v', 'error', '-y', '-i', clip, '-i', audio, '-c:v', 'copy', '-c:a', 'aac', final], check=True)
        r = subprocess.run([medios.ffprobe(), '-v', 'error', '-show_streams', '-of', 'json', final], capture_output=True, text=True, check=True)
        self.assertEqual({s['codec_type'] for s in json.loads(r.stdout)['streams']}, {'video', 'audio'})


if __name__ == '__main__':
    unittest.main()
