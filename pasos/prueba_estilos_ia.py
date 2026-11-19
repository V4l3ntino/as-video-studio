"""Estilos encapsulados: contratos/API y navegador opcional, sin consumir IA."""
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

REAL = '--real' in sys.argv
if REAL:
    sys.argv.remove('--real')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_DATOS = tempfile.TemporaryDirectory(prefix='prueba_estilos_ia_')
for clave in ('ESTUDIO_SECRETOS', 'ESTUDIO_AJUSTES', 'ESTUDIO_ESTADISTICAS',
              'ESTUDIO_PRESETS', 'ESTUDIO_BANCO_PRESETS', 'ESTUDIO_ESTILOS_IA',
              'ESTUDIO_PROYECTOS', 'ESTUDIO_BITACORA_GLOBAL'):
    os.environ[clave] = str(Path(_DATOS.name) / clave)

from nucleo.proyecto import Proyecto, escribir_json, leer_json
from nucleo.trabajos import Cancelado
from pasos import estilos_ia as ia, presets_canal as presets, espacio_estilo as espacio

ANALISIS = dict(resumen='Dibujo editorial con movimiento de cámara suave.',
    guia_visual='Draw original editorial illustrations with clean outlines and warm light.',
    guia_guion='Plantea una pregunta y responde con ejemplos; no copies la referencia.',
    idioma='no verificado', areas={a: 'Observado visualmente.' if a == 'visual' else 'No verificado.' for a in ia.AREAS},
    recursos=[dict(nombre='Ilustraciones originales', motivo='Conservar el acabado visual.', motor='imagen'),
              dict(nombre='Rig propio', motivo='Requiere adaptación y pruebas.', motor='nuevo')])

# Motor original de prueba, solo biblioteca estándar: el proceso -I -S no
# necesita paquetes del intérprete anfitrión ni llamadas de IA para renderizarlo.
CODIGO = '''import struct, zlib, wave
class Frame:
    def __init__(self,w,h,r): self.size=(w,h); self.r=r
    def convert(self,modo): return self
    def tobytes(self): return bytes((self.r,50,180))*self.size[0]*self.size[1]
    def save(self,ruta):
        w,h=self.size
        def bloque(nombre,d): return struct.pack('>I',len(d))+nombre+d+struct.pack('>I',zlib.crc32(nombre+d)&0xffffffff)
        datos=b''.join(b'\\0'+self.tobytes()[i*w*3:(i+1)*w*3] for i in range(h))
        with open(ruta,'wb') as f: f.write(b'\\x89PNG\\r\\n\\x1a\\n'+bloque(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+bloque(b'IDAT',zlib.compress(datos))+bloque(b'IEND',b''))
def pintar(pedido,t): return Frame(pedido['ancho'],pedido['alto'],int(t*100)%255)
def crear_audio(pedido,ruta):
    with wave.open(ruta,'wb') as f:
        f.setparams((1,2,16000,0,'NONE','not compressed'))
        f.writeframes(b'\\0\\0'*round(pedido['duracion']*16000))
'''
PAQUETE = dict(codigo=CODIGO, dependencias=[], archivos={'recursos/colores.json': '{"color":"violeta"}'},
               parametros={}, direccion='', descargas=[])


class Contratos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = str(Path(self.tmp.name) / 'proyectos')
        self.entorno = patch.dict(os.environ, ESTUDIO_ESTILOS_IA=str(Path(self.tmp.name) / 'estilos'),
            ESTUDIO_PRESETS=str(Path(self.tmp.name) / 'presets.json'),
            ESTUDIO_BANCO_PRESETS=str(Path(self.tmp.name) / 'banco'))
        self.entorno.start(); self.addCleanup(self.entorno.stop)
        self.presets = patch.multiple(presets, FICHERO=os.environ['ESTUDIO_PRESETS'], BANCO=os.environ['ESTUDIO_BANCO_PRESETS'])
        self.presets.start(); self.addCleanup(self.presets.stop)

    def crear(self, nombre='Estilo de prueba'):
        return ia.crear(self.raiz, io.BytesIO(b'video de prueba'), 'entrada.MP4', nombre)

    def preparado(self):
        from PIL import Image
        ficha = self.crear()
        carpeta = ia.carpeta(self.raiz, ficha['id'])
        (carpeta / 'referencias').mkdir()
        for i in range(24):
            Image.new('RGB', (48, 27), 'blue').save(carpeta / 'referencias' / f'{i:02d}.jpg')
        Image.new('RGB', (96, 54), 'red').save(carpeta / 'miniatura.jpg')
        ficha.update(estado='analizado', analisis=ia.validar_analisis(ANALISIS))
        escribir_json(str(carpeta / 'estilo.json'), ficha)
        return ficha

    def test_carpetas_independientes_y_rutas_contenidas(self):
        a, b = self.crear(), self.crear()
        self.assertNotEqual(a['id'], b['id'])
        antes = (ia.carpeta(self.raiz, b['id']) / 'referencia.mp4').read_bytes()
        (ia.carpeta(self.raiz, a['id']) / 'referencia.mp4').write_bytes(b'otra referencia')
        self.assertEqual((ia.carpeta(self.raiz, b['id']) / 'referencia.mp4').read_bytes(), antes)
        for sid in ('../fuera', 'A' * 32, '/absoluta', 'a' * 31):
            with self.assertRaises(ValueError): ia.carpeta(self.raiz, sid)

    def test_subida_invalida_sin_restos(self):
        for contenido, nombre in ((b'', 'a.mp4'), (b'abc', 'a.exe')):
            with self.assertRaises(ValueError):
                ia.crear(self.raiz, io.BytesIO(contenido), nombre, 'Nombre')
        self.assertEqual(ia.listar(self.raiz), [])

    def test_subida_acepta_mkv_tambien_en_mayusculas(self):
        for extension in ('.mkv', '.MKV'):
            ficha = ia.crear(self.raiz, io.BytesIO(b'contenido matroska'), 'video' + extension, 'Estilo MKV')
            self.assertEqual(ficha['referencia'], 'referencia.mkv')
            self.assertEqual((ia.carpeta(self.raiz, ficha['id']) / ficha['referencia']).read_bytes(), b'contenido matroska')

    def test_subida_no_rechaza_mas_de_300_mib(self):
        from unittest.mock import Mock
        class Bloque(bytes):
            # Simula el contador de una subida grande sin ocupar 301 MiB.
            def __len__(self): return 301 * 1024 * 1024
        archivo = Mock()
        archivo.read.side_effect = [Bloque(b'fragmento'), b'']
        ficha = ia.crear(self.raiz, archivo, 'grande.mp4', 'Referencia grande')
        self.assertEqual((ia.carpeta(self.raiz, ficha['id']) / 'referencia.mp4').read_bytes(), b'fragmento')
        archivo.read.assert_called_with(1024 * 1024)

    def test_endpoint_no_rechaza_por_tamano_de_upload(self):
        from types import SimpleNamespace
        import app
        archivo = SimpleNamespace(size=301 * 1024 * 1024, file=io.BytesIO(b'fragmento'), filename='grande.mp4')
        with patch.object(app, 'raiz_proyectos', return_value=self.raiz), \
                patch.object(app.TRABAJOS_ESTILOS_IA, 'listar', return_value=[]), \
                patch.object(app.TRABAJOS_ESTILOS_IA, 'lanzar', return_value='sin_llamar_ia') as trabajo, \
                patch.object(app, '_ficha_estilo_ia', return_value={'estado': 'pendiente'}):
            respuesta = app.crear_estilo_ia(archivo, 'Referencia grande', '', 'Claude')
        self.assertEqual(respuesta['estilo']['estado'], 'pendiente')
        trabajo.assert_called_once()

    def test_no_confunde_propuesta_con_capacidad_preparada(self):
        analisis = ia.validar_analisis(ANALISIS)
        self.assertEqual(analisis['recursos'][0]['estado'], 'requiere_preparacion')
        self.assertEqual(analisis['recursos'][1]['estado'], 'requiere_preparacion')
        for cambio in (dict(areas={}), dict(recursos=[]), dict(guia_visual=12),
                       dict(recursos=[dict(nombre='shell', motivo='ejecutar', motor='bash')])):
            with self.assertRaises(ValueError): ia.validar_analisis(dict(ANALISIS, **cambio))

    def test_aplicar_estilo_copia_motor_y_cambiar_a_normal_lo_retira(self):
        marca = dict(id='a' * 32, version=1, huella='b' * 64)
        ficha = dict(tipo='estilo', datos=dict(guia='Dibujo 2D', espacio_ia=marca))
        antes = copy.deepcopy(ficha)
        cambios = presets.cambios_para(ficha)
        self.assertEqual(cambios['assets']['estilo']['espacio_ia'], marca)
        self.assertEqual(ficha, antes)
        extraido = presets.datos_de_params(cambios)
        self.assertEqual(extraido['estilo']['espacio_ia'], marca)
        normal = presets.cambios_para(dict(tipo='estilo', datos=dict(guia='Otro estilo')), cambios)
        self.assertNotIn('espacio_ia', normal['assets']['estilo'])

    def test_resumen_real_de_1617_caracteres_no_se_rechaza_ni_se_recorta(self):
        dato = dict(ANALISIS, resumen='R' * 1617)
        self.assertEqual(ia.validar_analisis(dato)['resumen'], dato['resumen'])

    def test_limites_esquema_coinciden_con_validador_y_error_nombra_campo(self):
        from pasos import analisis_video
        esquema = analisis_video._esquema_consulta('Sintetiza la inspección')['properties']
        for campo in ('resumen', 'guia_visual', 'guia_guion', 'idioma'):
            maximo = ia.LIMITES_TEXTO_ANALISIS[campo]
            self.assertEqual(esquema[campo]['maxLength'], maximo)
            self.assertEqual(ia.validar_analisis(dict(ANALISIS, **{campo: 'x' * maximo}))[campo], 'x' * maximo)
            with self.assertRaisesRegex(ValueError, f'{campo}.*{maximo + 1}.*{maximo}'):
                ia.validar_analisis(dict(ANALISIS, **{campo: 'x' * (maximo + 1)}))
        self.assertEqual(esquema['areas']['properties']['visual']['maxLength'], ia.LIMITES_TEXTO_ANALISIS['area'])
        self.assertEqual(esquema['recursos']['maxItems'], 30)

    def test_respuesta_global_se_conserva_antes_de_validar_sin_repetir_cuota(self):
        from pasos import analisis_video
        ficha = self.crear()
        destino = ia.carpeta(self.raiz, ficha['id'])
        invalido = dict(ANALISIS, idioma='x' * 51)
        with patch.object(analisis_video, 'consultar', return_value=invalido) as modelo:
            for _ in range(2):
                with self.assertRaisesRegex(ValueError, 'idioma'):
                    ia.consultar(destino, ficha, {}, [], lambda *a: None)
        self.assertEqual(modelo.call_count, 1)
        archivos = list((destino / 'analisis_visual' / 'informes_globales').glob('*.json'))
        self.assertEqual(len(archivos), 1)
        self.assertEqual(leer_json(str(archivos[0]))['respuesta'], invalido)

    def test_cache_global_separa_cambios_del_encargo_y_los_adjuntos(self):
        from pasos import analisis_video
        ficha = self.crear()
        destino = ia.carpeta(self.raiz, ficha['id'])
        hoja = destino / 'hoja.jpg'
        hoja.write_bytes(b'referencia inicial')
        with patch.object(analisis_video, 'consultar', return_value=ANALISIS) as modelo:
            ia.consultar(destino, ficha, {}, [str(hoja)], lambda *a: None)
            ia.consultar(destino, ficha, {}, [str(hoja)], lambda *a: None)
            self.assertEqual(modelo.call_count, 1)
            hoja.write_bytes(b'referencia distinta')
            ia.consultar(destino, ficha, {}, [str(hoja)], lambda *a: None)
            ia.consultar(destino, dict(ficha, transcripcion='Texto corregido'), {}, [str(hoja)], lambda *a: None)
        self.assertEqual(modelo.call_count, 3)

    def test_endpoint_sintetiza_sin_lanzar_otro_trabajo_si_el_analisis_esta_activo(self):
        import app
        from pasos import analisis_video
        ficha = dict(id='a' * 32, estado='analizando', trabajo=dict(estado='ejecutando'),
                     inspeccion_visual=dict(etapa='lotes'))
        with patch.object(app, '_ficha_estilo_ia', return_value=ficha), \
                patch.object(app, 'raiz_proyectos', return_value=self.raiz), \
                patch.object(analisis_video, 'solicitar_sintesis', return_value={}) as solicitar, \
                patch.object(app.TRABAJOS_ESTILOS_IA, 'lanzar') as lanzar:
            app.sintetizar_lotes_estilo_ia(ficha['id'])
        solicitar.assert_called_once()
        lanzar.assert_not_called()

    def test_endpoint_sintetizar_rechaza_publicados_y_lotes_vacios(self):
        import app
        from pasos import analisis_video
        for ficha in (dict(id='a' * 32, estado='preparado', preset_id='publicado'),
                      dict(id='a' * 32, estado='analizando', trabajo=dict(estado='ejecutando'))):
            with patch.object(app, '_ficha_estilo_ia', return_value=ficha), \
                    patch.object(app, 'raiz_proyectos', return_value=self.raiz), \
                    patch.object(analisis_video, 'solicitar_sintesis', side_effect=ValueError('no hay lotes')), \
                    patch.object(app.TRABAJOS_ESTILOS_IA, 'lanzar') as lanzar:
                with self.assertRaises(app.ErrorApi): app.sintetizar_lotes_estilo_ia(ficha['id'])
            lanzar.assert_not_called()

    def test_endpoint_sintetizar_retoma_un_analisis_interrumpido(self):
        import app
        from pasos import analisis_video
        ficha = dict(id='a' * 32, estado='interrumpido', trabajo=None)
        with patch.object(app, '_ficha_estilo_ia', return_value=ficha), \
                patch.object(app, 'raiz_proyectos', return_value=self.raiz), \
                patch.object(analisis_video, 'solicitar_sintesis', return_value={}), \
                patch.object(app.TRABAJOS_ESTILOS_IA, 'listar', return_value=[]), \
                patch.object(app.TRABAJOS_ESTILOS_IA, 'lanzar', return_value='doble') as lanzar, \
                patch.object(app, 'INDICE_ESTILOS_IA', {}):
            app.sintetizar_lotes_estilo_ia(ficha['id'])
        lanzar.assert_called_once()

    def test_analista_no_puede_escribir_instalar_ni_ejecutar(self):
        from pasos import cli_claude
        ficha = self.crear()
        destino = ia.carpeta(self.raiz, ficha['id'])
        hoja = str(destino / 'secuencia_0.jpg')
        with patch.object(cli_claude, 'ejecutar', return_value=(json.dumps(ANALISIS), {})) as modelo:
            ia.consultar(destino, ficha, {}, [hoja], lambda *a: None)
        opciones = modelo.call_args.kwargs
        self.assertEqual(opciones['extra'][:2], ['--tools', 'Read'])
        self.assertIn('--json-schema', opciones['extra'])
        self.assertNotIn('Read', opciones['herramientas_permitidas'])
        self.assertEqual(opciones['herramientas_permitidas'], (f'Read({Path(hoja).as_posix()})',))
        self.assertTrue({'Bash', 'Write', 'Edit', 'WebFetch'}.issubset(opciones['herramientas_vetadas']))
        self.assertIn('No has escuchado audio', modelo.call_args.args[0])

    def test_error_y_cancelacion_se_conservan(self):
        for error, estado in ((ValueError('fallo controlado'), 'error'), (Cancelado(), 'cancelado')):
            ficha = self.crear()
            with patch.object(ia, 'extraer', side_effect=error), self.assertRaises(type(error)):
                ia.analizar(lambda *a: None, self.raiz, ficha['id'])
            self.assertEqual(ia.leer(self.raiz, ficha['id'])['estado'], estado)

    def test_no_publica_sin_analisis(self):
        ficha = self.crear()
        with self.assertRaises(ValueError): ia.publicar_base(self.raiz, ficha['id'], presets)

    def test_base_copia_referencias_y_video_conserva_instantanea(self):
        ficha = self.preparado()
        nueva = ia.publicar_base(self.raiz, ficha['id'], presets)
        self.assertEqual(ia.publicar_base(self.raiz, ficha['id'], presets)['id'], nueva['id'])
        refs = nueva['datos']['estilo']['referencias']
        self.assertEqual(len(refs), 6)
        self.assertTrue(all(Path(p).is_relative_to(Path(presets.BANCO)) for p in refs))
        proyecto = Proyecto.crear(self.raiz, 'Vídeo encapsulado')
        ia.congelar(presets, nueva, proyecto)
        manifiesto = leer_json(proyecto.ruta('estilo_ia', 'manifiesto.json'))
        self.assertFalse(manifiesto['calidad_verificada'])
        copia = proyecto.duplicar(self.raiz, 'Copia encapsulada')
        self.assertEqual(leer_json(copia.ruta('estilo_ia', 'manifiesto.json')), manifiesto)
        from pasos import paquete_estilo
        paquete = str(Path(self.tmp.name) / 'estilo.zip')
        paquete_estilo.exportar(presets, nueva['id'], None, paquete)
        with patch.multiple(presets, FICHERO=str(Path(self.tmp.name) / 'importados.json'),
                            BANCO=str(Path(self.tmp.name) / 'importados')):
            with open(paquete, 'rb') as entrada:
                importada = paquete_estilo.importar(presets, entrada, self.raiz)
            ia.congelar(presets, importada, copia)
            self.assertEqual(leer_json(copia.ruta('estilo_ia', 'manifiesto.json')), manifiesto)
        fuente = Path(presets.carpeta_de(nueva['id'])) / 'estilo_ia' / 'manifiesto.json'
        modificado = dict(manifiesto, version=999)
        escribir_json(str(fuente), modificado)
        with self.assertRaises(ValueError): ia.congelar(presets, nueva, proyecto)
        self.assertEqual(leer_json(proyecto.ruta('estilo_ia', 'manifiesto.json')), manifiesto)

    def test_api_validacion_opt_in_y_reinicio(self):
        import app
        with patch.object(app, 'raiz_proyectos', return_value=self.raiz):
            ficha = self.preparado()
            sid = ficha['id']
            self.assertNotIn('transcripcion', app.listar_estilos_ia()['estilos'][0])
            for codigo, llamada in ((400, lambda: app.preparar_base_estilo_ia(sid, {})),
                                     (409, lambda: app.reanudar_estilo_ia(sid)),
                                     (404, lambda: app.obtener_estilo_ia('invalido'))):
                with self.assertRaises(app.ErrorApi) as error: llamada()
                self.assertEqual(error.exception.codigo, codigo)
            publicado = app.preparar_base_estilo_ia(sid, {'aceptar_limitaciones': True})['preset']
            creado = app.crear_video_light(publicado['id'], {'nombre': 'Vídeo de prueba', 'material': 'Tema original.'})
            proyecto = app.contexto(creado['proyecto']['id']).proyecto
            self.assertTrue(Path(proyecto.ruta('estilo_ia', 'manifiesto.json')).is_file())
            estado = app.contexto(proyecto.id).estado
            self.assertEqual(estado.params('assets')['estilo']['guia'], ANALISIS['guia_visual'])
            self.assertEqual(estado.params('brief')['instrucciones'], ANALISIS['guia_guion'])
            self.assertTrue(all(Path(r).is_relative_to(Path(proyecto.raiz)) for r in estado.params('assets')['estilo']['referencias']))
            pendiente = self.crear()
            foto = app.obtener_estilo_ia(pendiente['id'])['estilo']
            self.assertEqual(foto['estado'], 'interrumpido')

    def test_paquete_rechaza_rutas_y_dependencias_globales(self):
        self.assertEqual(espacio.validar(PAQUETE)['dependencias'], [])
        for cambios in (dict(archivos={'../app.py': 'mal'}), dict(archivos={'motores/../../app.py': 'mal'}),
                        dict(dependencias=['--upgrade pip']), dict(dependencias=['pillow']),
                        dict(dependencias=['https://servidor/paquete.whl']), dict(codigo='print("sin motor")')):
            with self.assertRaises(ValueError): espacio.validar(dict(PAQUETE, **cambios))
        with self.assertRaises(ValueError): espacio._url_publica('http://localhost/recurso')
        with self.assertRaises(ValueError): espacio._url_publica('https://127.0.0.1/recurso')

    def test_dependencias_solo_se_instalan_en_el_estilo(self):
        ficha = self.preparado()
        destino = ia.carpeta(self.raiz, ficha['id']) / 'espacio'
        paquete = espacio.validar(dict(PAQUETE, dependencias=['pillow==12.3.0']))
        espacio.materializar(destino, paquete, [])
        with patch.object(espacio, 'correr') as proceso:
            espacio.instalar(destino, lambda *a: None)
            espacio.instalar(destino, lambda *a: None)
        self.assertEqual(proceso.call_count, 1)
        orden = proceso.call_args.args[0]
        self.assertIn('--target', orden)
        self.assertTrue(Path(orden[orden.index('--target') + 1]).is_relative_to(destino))
        self.assertNotIn('--user', orden)
        env = espacio.entorno(destino)
        self.assertNotIn('ANTHROPIC_API_KEY', env)
        self.assertTrue(Path(env['PIP_CACHE_DIR']).is_relative_to(destino))
        self.assertTrue(Path(env['TEMP']).is_relative_to(destino))

    def test_espacio_inmutable_y_copia_sin_caches(self):
        ficha = self.preparado()
        destino = ia.carpeta(self.raiz, ficha['id']) / 'espacio'
        espacio.materializar(destino, espacio.validar(PAQUETE), [])
        sello = espacio.huella(espacio.inventario(destino))
        copia = destino.parent / 'copia'
        espacio.copiar(destino, copia, sello)
        self.assertFalse((copia / 'dependencias').exists())
        self.assertFalse((copia / 'trabajo').exists())
        espacio.verificar(copia, sello)
        (copia / 'motores' / 'escena.py').write_text('otra versión', encoding='utf-8')
        with self.assertRaises(ValueError): espacio.verificar(copia, sello)
        espacio.verificar(destino, sello)

    def test_muestra_fallida_no_publica_y_el_reintento_recibe_diagnostico(self):
        ficha = self.preparado()
        with patch.object(espacio, 'consultar_constructor', return_value=espacio.validar(PAQUETE)) as constructor, \
                patch.object(espacio, 'renderizar', side_effect=ValueError('fallo de pintar')):
            for _ in range(2):
                with self.assertRaisesRegex(ValueError, 'fallo de pintar'):
                    ia.preparar(lambda *a: None, self.raiz, ficha['id'], presets)
        self.assertEqual(constructor.call_count, 2)
        self.assertEqual(constructor.call_args.kwargs['correccion']['error'], 'fallo de pintar')
        self.assertEqual(ia.leer(self.raiz, ficha['id'])['estado'], 'error_preparacion')
        self.assertEqual(presets.listar()['presets'].get('canal', []), [])

    @unittest.skipUnless(REAL, 'usa --real para comprobar el motor con ffmpeg, sin IA')
    def test_motor_no_puede_escribir_fuera_de_su_espacio(self):
        ajeno = Path(self.tmp.name) / 'codigo_compartido.py'
        ajeno.write_text('original', encoding='utf-8')
        destino = Path(self.tmp.name) / 'motor'
        codigo = f"open({str(ajeno)!r},'w').write('cambiado')\n" + CODIGO
        espacio.materializar(destino, espacio.validar(dict(PAQUETE, codigo=codigo)), [])
        with self.assertRaisesRegex(ValueError, 'solo puede escribir'):
            espacio.renderizar(destino, dict(ancho=160, alto=90, fps=12, duracion=1,
                imagen='', escena={}, parametros={}), destino / 'muestra', lambda *a: None)
        self.assertEqual(ajeno.read_text(encoding='utf-8'), 'original')

    @unittest.skipUnless(REAL, 'usa --real para comprobar el motor con ffmpeg, sin IA')
    def test_preparacion_motor_local_pipeline_audio_y_portabilidad(self):
        from PIL import Image
        from pasos import p6_assets, paquete_estilo, p8_render, sonido
        ficha = self.preparado()
        with patch.object(espacio, 'consultar_constructor', return_value=espacio.validar(PAQUETE)):
            resultado = ia.preparar(lambda *a: None, self.raiz, ficha['id'], presets)
        nueva = presets.leer(resultado['preset_id'])
        marca = nueva['datos']['estilo']['espacio_ia']
        self.assertTrue((ia.carpeta(self.raiz, ficha['id']) / 'versiones' / 'v1' / 'muestra' / 'clip.mp4').is_file())
        proyecto = Proyecto.crear(self.raiz, 'Motor propio')
        ia.congelar(presets, nueva, proyecto)
        aplicados = presets.cambios_para(nueva)
        estilo_aplicado = aplicados['assets']['estilo']
        self.assertEqual(estilo_aplicado['espacio_ia'], marca)
        local = espacio.espacio_del_video(proyecto, marca)
        self.assertTrue(local.is_relative_to(Path(proyecto.raiz)))
        trabajo = Path(proyecto.ruta_trabajo('assets'))
        (trabajo / 'escenas').mkdir()
        Image.new('RGB', (160, 90), 'red').save(trabajo / 'escenas' / 'S001.png')
        escena = dict(id='S001', narracion='Un plano original.', prompt='Un entorno cálido.', t_in=0, t_out=1)
        plan = dict(estilo=estilo_aplicado, escenas=[escena], resolucion=[160, 90], fps=12)
        base = dict(unidades={'escena:S001': dict(png='escenas/S001.png')},
                    todas={'escena:S001': dict(png='escenas/S001.png')}, plan=plan)
        with patch.object(p6_assets, '_ejecutar_base', return_value=copy.deepcopy(base)):
            animada = p6_assets.ejecutar(proyecto, {'estilo': estilo_aplicado})
        self.assertTrue(animada['unidades']['escena:S001']['animacion_estilo']['clip'].endswith('.mp4'))
        with patch.object(espacio, 'renderizar', side_effect=AssertionError('no debe renderizar otra vez')), \
                patch.object(p6_assets, '_ejecutar_base', return_value=copy.deepcopy(base)):
            p6_assets.ejecutar(proyecto, {'estilo': nueva['datos']['estilo']})
        visible = espacio.aplicar_recursos(proyecto, copy.deepcopy(plan))
        self.assertTrue(Path(visible['escenas'][0]['animacion_estilo']['clip']).is_file())
        eventos = sonido._eventos_automaticos(visible['escenas'], {}, {})
        self.assertTrue(any(e['papel'] == 'estilo_ia:0' for e in eventos))
        fuente = p8_render._fuente_para_enlace(visible['escenas'][0], {}, str(trabajo), {}, proyecto, False, salida=(160, 90))
        self.assertEqual(fuente['video'], visible['escenas'][0]['animacion_estilo']['clip'])
        tarea = dict(fuente, id='S001', fps=6, frames=6, carpeta=str(trabajo / 'render'),
            hyper=str(trabajo / 'escenas' / 'S001.png'),
            capa_fija='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 90"><rect width="20" height="10" fill="#00ff00"/></svg>',
            resolucion=[160, 90], calidad='media', clip=str(trabajo / 'montado.mp4'),
            ultimo=str(trabajo / 'ultimo.png'), conservar_frames=True)
        navegador = p8_render.Navegador(160, 90)
        try: p8_render.renderizar_plano(tarea, navegador)
        finally: navegador.cerrar()
        self.assertNotEqual((trabajo / 'render' / 'f00001.png').read_bytes(), (trabajo / 'render' / 'f00006.png').read_bytes())
        with Image.open(trabajo / 'render' / 'f00001.png') as frame:
            self.assertEqual(frame.convert('RGB').getpixel((5, 5)), (0, 255, 0))
        cambiada = copy.deepcopy(plan); cambiada['escenas'][0]['narracion'] = 'Otro texto.'
        self.assertNotIn('animacion_estilo', espacio.aplicar_recursos(proyecto, cambiada)['escenas'][0])
        copia = proyecto.duplicar(self.raiz, 'Copia del motor propio')
        self.assertFalse((Path(copia.ruta('estilo_ia', 'paquetes', marca['huella'])) / 'dependencias').exists())
        archivo = str(Path(self.tmp.name) / 'motor.zip')
        paquete_estilo.exportar(presets, nueva['id'], None, archivo)
        with patch.multiple(presets, FICHERO=str(Path(self.tmp.name) / 'importados.json'), BANCO=str(Path(self.tmp.name) / 'importados')):
            with open(archivo, 'rb') as entrada: importada = paquete_estilo.importar(presets, entrada, self.raiz)
            ia.congelar(presets, importada, copia)
            espacio.verificar(espacio.espacio_del_video(copia, marca), marca['huella'])

    @unittest.skipUnless(REAL, 'usa --real para ffmpeg y navegador; nunca llama a IA')
    def test_navegador_subida_analisis_y_formulario_normal(self):
        import socket
        import subprocess
        import time
        import urllib.request
        from playwright.sync_api import sync_playwright
        from pasos import medios
        video = str(Path(self.tmp.name) / 'referencia.mkv')
        subprocess.run([medios.ffmpeg(), '-v', 'error', '-y', '-f', 'lavfi', '-i',
                        'testsrc2=size=640x360:rate=24', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=16000',
                        '-t', '2', '-pix_fmt', 'yuv420p', '-c:a', 'pcm_s16le', video], check=True)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); puerto = sock.getsockname()[1]
        entorno = dict(os.environ, ESTUDIO_PROYECTOS=self.raiz)
        transcripcion = dict(origen='whisper', motor='faster-whisper', modelo='small', idioma='es', estado='transcrito',
            duracion_s=2, texto='Este es el guion de referencia.',
            segmentos=[dict(t_in=0, t_out=1.9, texto='Este es el guion de referencia.', palabras=[])])
        programa = ("import uvicorn, app; from pasos import estilos_ia as ia, espacio_estilo as espacio, transcripcion_estilo as voz, analisis_video as av; "
                    "av.SEGUNDOS_VENTANA=0.3; "
                    "informe_lote=lambda ventanas: dict(conclusiones='Capas y cámara suave.', ventanas=[dict(id=v['id'],areas={a:'Detalle observado en la secuencia.' for a in av.AREAS},evidencias=[f\"F{v['fotogramas'][0]:07d}\"],incertidumbres='Fuente no verificable.') for v in ventanas]); "
                    "exec(\"def consultar(analista,prompt,refs,destino,avisar,mensaje):\\n"
                    " import json,time\\n"
                    " if not prompt.startswith('Inspecciona MINUCIOSAMENTE'): return ANALISIS\\n"
                    " ventanas=json.loads(prompt.split('Ventanas y mediciones locales:\\\\n')[1].split('\\\\nFotogramas disponibles:')[0])\\n"
                    " if analista=='ChatGPT' and ventanas[0]['id']=='V0003':\\n"
                    "  fin=time.monotonic()+30\\n"
                    "  while not (destino/'analisis_visual'/'sintesis_solicitada.json').exists() and time.monotonic()<fin:\\n"
                    "   avisar(None,'Lote en curso: esperando la decisión del usuario');time.sleep(.05)\\n"
                    " return informe_lote(ventanas)\\n\"); "
                    f"ANALISIS={ANALISIS!r}; av.consultar=consultar; "
                    f"espacio.consultar_constructor=lambda *a,**kw: espacio.validar({PAQUETE!r}); "
                    "voz.preparar_motor=lambda destino,*a: destino/'whisper'; "
                    f"voz.reconocer=lambda *a: {transcripcion!r}; "
                    f"uvicorn.run(app.app,host='127.0.0.1',port={puerto},log_level='error')")
        proceso = subprocess.Popen([sys.executable, '-c', programa], env=entorno,
                                   cwd=Path(__file__).resolve().parents[1])
        try:
            url = f'http://127.0.0.1:{puerto}'
            for _ in range(100):
                try:
                    urllib.request.urlopen(url, timeout=1).close(); break
                except OSError: time.sleep(.1)
            with sync_playwright() as pw:
                navegador = pw.chromium.launch(headless=True, executable_path=medios.edge())
                pagina = navegador.new_page(viewport=dict(width=1440, height=1000))
                errores = []
                pagina.on('pageerror', lambda error: errores.append(str(error)))
                pagina.goto(url)
                pagina.wait_for_function('APP.light.datos && !APP.light.cargando')
                pagina.evaluate("document.querySelector('#inicio')?.remove()")
                self.assertEqual(pagina.locator('#btn-inicio-estilos').get_attribute('aria-current'), 'page')
                self.assertEqual(pagina.locator('.inicio-pestanas button svg').count(), 2)
                self.assertTrue(pagina.locator('.marca-simbolo').is_visible())
                pagina.locator('#btn-estilos-ia').focus()
                pagina.keyboard.press('Enter')
                pagina.wait_for_function("document.querySelector('#btn-estilos-ia').getAttribute('aria-current') === 'page'")
                pagina.get_by_label('Nombre del estilo', exact=True).fill('Prueba encapsulada')
                pagina.get_by_role('button', name='ChatGPT', exact=True).click()
                self.assertEqual(pagina.get_by_role('button', name='ChatGPT', exact=True).get_attribute('aria-pressed'), 'true')
                self.assertTrue(pagina.get_by_text('La voz del vídeo se transcribe automáticamente con Whisper local.', exact=False).is_visible())
                self.assertFalse(pagina.get_by_label('Texto alternativo para sustituir el reconocimiento automático').is_visible())
                self.assertIn('.mkv', pagina.get_by_label('Vídeo de referencia', exact=True).get_attribute('accept'))
                pagina.get_by_label('Vídeo de referencia', exact=True).set_input_files(video)
                pagina.get_by_role('button', name='Analizar vídeo', exact=True).click()
                sintetizar = pagina.get_by_role('button', name='Finalizar lotes y sintetizar', exact=True).first
                sintetizar.wait_for(timeout=60000)
                capturas = Path(os.environ.get('LOCALAPPDATA', tempfile.gettempdir())) / 'Temp' / 'opencode'
                capturas.mkdir(parents=True, exist_ok=True)
                pagina.screenshot(path=str(capturas / 'estilos-ia-sintetizar.png'), full_page=True)
                pagina.set_viewport_size(dict(width=390, height=844))
                sintetizar.scroll_into_view_if_needed()
                self.assertLessEqual(pagina.evaluate('document.documentElement.scrollWidth'), 390)
                pagina.screenshot(path=str(capturas / 'estilos-ia-sintetizar-movil.png'), full_page=True)
                pagina.set_viewport_size(dict(width=1440, height=1000))
                sintetizar.click()
                pagina.get_by_role('button', name='Preparar herramientas y motor', exact=True).wait_for(timeout=60000)
                self.assertTrue(pagina.evaluate('ESTILOS_IA_UI.fichas[0].metadatos.cobertura_visual.parcial'))
                self.assertEqual(pagina.evaluate('ESTILOS_IA_UI.fichas[0].metadatos.cobertura_visual.lotes_completos'), 2)
                self.assertTrue(pagina.get_by_text('Informe parcial ·', exact=False).is_visible())
                pagina.locator('.estilo-ia-parcial').scroll_into_view_if_needed()
                pagina.screenshot(path=str(capturas / 'estilos-ia-informe-parcial.png'), full_page=True)
                self.assertEqual(pagina.evaluate('ESTILOS_IA_UI.fichas[0].proveedor_analisis'), 'ChatGPT')
                self.assertTrue(pagina.get_by_text('PySceneDetect · cortes adaptativos y fundidos a negro/blanco', exact=False).is_visible())
                pagina.get_by_text('Ver el informe detallado por intervalos', exact=True).click()
                pagina.get_by_text('Informe realizado con ChatGPT', exact=True).wait_for()
                pagina.locator('.estilo-ia-intervalo summary').first.click()
                self.assertTrue(pagina.get_by_text('Detalle observado en la secuencia.', exact=True).first.is_visible())
                pagina.get_by_role('button', name='Claude', exact=True).click()
                pagina.get_by_role('button', name='Volver a analizar con Claude', exact=True).click()
                pagina.wait_for_function("ESTILOS_IA_UI.fichas[0].analista_del_informe === 'Claude' && ESTILOS_IA_UI.fichas[0].estado === 'analizado'")
                self.assertFalse(pagina.evaluate('ESTILOS_IA_UI.fichas[0].metadatos.cobertura_visual.parcial'))
                pagina.get_by_role('button', name='Preparar herramientas y motor', exact=True).wait_for(timeout=60000)
                pagina.locator('.estilo-ia-transcripcion summary').click()
                pagina.get_by_label('Transcripción reconocida', exact=True).wait_for()
                self.assertEqual(pagina.get_by_label('Transcripción reconocida', exact=True).input_value(), transcripcion['texto'])
                self.assertTrue(pagina.get_by_role('button', name='Corregir y volver a analizar', exact=True).is_visible())
                pagina.get_by_label('Transcripción reconocida', exact=True).fill('Texto revisado de la referencia.')
                pagina.get_by_role('button', name='Corregir y volver a analizar', exact=True).click()
                pagina.wait_for_function("document.querySelector('.estilo-ia-transcripcion summary')?.textContent.includes('Texto aportado')")
                pagina.get_by_role('button', name='Preparar herramientas y motor', exact=True).wait_for(timeout=60000)
                pagina.locator('.estilo-ia-transcripcion summary').click()
                pagina.get_by_label('Transcripción reconocida', exact=True).wait_for()
                self.assertEqual(pagina.get_by_label('Transcripción reconocida', exact=True).input_value(), 'Texto revisado de la referencia.')
                capturas = Path(os.environ.get('LOCALAPPDATA', tempfile.gettempdir())) / 'Temp' / 'opencode'
                capturas.mkdir(parents=True, exist_ok=True)
                pagina.screenshot(path=str(capturas / 'estilos-ia-analisis.png'), full_page=True)
                pagina.on('dialog', lambda dialogo: dialogo.accept())
                pagina.get_by_role('button', name='Preparar herramientas y motor', exact=True).click()
                pagina.get_by_role('button', name='Crear vídeo con este estilo', exact=True).wait_for(timeout=60000)
                self.assertTrue(pagina.get_by_label('Muestra animada del motor del estilo').is_visible())
                pagina.screenshot(path=str(capturas / 'estilos-ia-motor-preparado.png'), full_page=True)
                pagina.get_by_role('button', name='Crear vídeo con este estilo', exact=True).click()
                pagina.get_by_role('heading', name='Un vídeo nuevo', exact=True).wait_for(timeout=20000)
                self.assertTrue(pagina.get_by_text('Este vídeo utiliza las referencias, el motor de animación', exact=False).is_visible())
                def peticion_json(ruta, cuerpo):
                    solicitud = urllib.request.Request(url + ruta, data=json.dumps(cuerpo).encode('utf-8'),
                        headers={'Content-Type': 'application/json'}, method='POST')
                    with urllib.request.urlopen(solicitud) as respuesta:
                        return json.load(respuesta)
                creado = peticion_json('/api/proyectos', dict(nombre='Reparto de animaciones'))
                pid_reparto = creado['proyecto']['id']
                preset_id = pagina.evaluate('ESTILOS_IA_UI.fichas[0].preset_id')
                peticion_json(f'/api/proyectos/{pid_reparto}/presets-canal/{preset_id}/aplicar', {})
                pagina.evaluate("async pid => { APP.light.video.vista='encargo'; await cargarVideoLight(pid); }", pid_reparto)
                slider = pagina.get_by_role('slider', name='Porcentaje de escenas para ChatGPT', exact=True)
                slider.wait_for()
                self.assertEqual(slider.input_value(), '0')
                self.assertIsNone(pagina.evaluate('APP.light.video.fichas.assets.params.reparto_animaciones || null'))
                previos = pagina.evaluate('JSON.stringify(APP.light.video.fichas.guion.params)')
                slider.evaluate("n => { n.value='70'; n.dispatchEvent(new Event('input', {bubbles:true})); }")
                self.assertEqual(slider.get_attribute('aria-valuetext'), 'Claude 30% · ChatGPT 70%')
                pagina.evaluate('volcarEncargoLight(pedidoDelVideoLight())')
                self.assertEqual(pagina.evaluate('APP.light.video.fichas.assets.params.reparto_animaciones.carga_claude'), 30)
                self.assertEqual(pagina.evaluate('JSON.stringify(APP.light.video.fichas.guion.params)'), previos)
                pagina.set_viewport_size(dict(width=390, height=844))
                pagina.evaluate("document.querySelector('[data-foco=\"reparto-animaciones-chatgpt\"]').scrollIntoView({block:'center'})")
                self.assertLessEqual(pagina.evaluate('document.documentElement.scrollWidth'), 390)
                pagina.screenshot(path=str(capturas / 'encargo-reparto-animaciones-movil.png'), full_page=True)
                pagina.set_viewport_size(dict(width=1440, height=1000))
                pagina.evaluate("async pid => { APP.light.video.vista='encargo'; await cargarVideoLight(pid); }", pid_reparto)
                self.assertEqual(pagina.get_by_role('slider', name='Porcentaje de escenas para ChatGPT', exact=True).input_value(), '70')
                pagina.evaluate("document.querySelector('[data-foco=\"reparto-animaciones-chatgpt\"]').scrollIntoView({block:'center'})")
                pagina.screenshot(path=str(capturas / 'encargo-reparto-animaciones.png'), full_page=True)
                # El SSE da un primer progreso y queda abierto: el estado final
                # debe descubrirse sin recargar y sin lanzar trabajo alguno.
                recuperado = pagina.evaluate("""async () => {
                  const pedirAnterior = pedir, fuenteAnterior = window.EventSource;
                  let consultas = 0;
                  window.EventSource = class {
                    constructor() { queueMicrotask(() => this.onmessage?.({ data: JSON.stringify({
                      estado:'ejecutando', progreso:.1, mensaje:'Esperando al proveedor' }) })); }
                    addEventListener() {}
                    close() {}
                  };
                  pedir = async (ruta, ...args) => ruta === API.trabajo('prueba-cuota-sse')
                    ? (++consultas, {estado:'error', error:'LimiteAgotado: cuota de prueba agotada', progreso:.1})
                    : pedirAnterior(ruta, ...args);
                  try {
                    return await new Promise(resolve => seguirTrabajo(CLAVE_VIDEO_LIGHT, 'prueba-cuota-sse',
                      datos => resolve({estado:datos.estado, consultas, error:ERRORES[CLAVE_VIDEO_LIGHT]})));
                  } finally {
                    pedir = pedirAnterior; window.EventSource = fuenteAnterior;
                    delete APP.trabajos[CLAVE_VIDEO_LIGHT];
                  }
                }""")
                self.assertEqual(recuperado['estado'], 'error')
                self.assertEqual(recuperado['consultas'], 1)
                self.assertIn('cuota de prueba agotada', recuperado['error'])
                pagina.evaluate("APP.light.video.vista='previa'; PREVIA.ficha={escenas:[]}; PREVIA.error=''; pintarLight()")
                pagina.get_by_text('cuota de prueba agotada', exact=False).first.wait_for()
                pagina.screenshot(path=str(capturas / 'previa-error-cuota-persistente.png'), full_page=True)
                pagina.evaluate("APP.light.video.fichas.assets.params.animacion_nativa=true; pintarLight()")
                pagina.get_by_role('heading', name='Las animaciones, una a una', exact=True).wait_for()
                pagina.screenshot(path=str(capturas / 'animacion-nativa-previa.png'), full_page=True)
                pagina.set_viewport_size(dict(width=390, height=844))
                self.assertLessEqual(pagina.evaluate('document.documentElement.scrollWidth'), 390)
                pagina.screenshot(path=str(capturas / 'animacion-nativa-previa-movil.png'), full_page=True)
                pagina.set_viewport_size(dict(width=1440, height=1000))
                pagina.evaluate('delete ERRORES[CLAVE_VIDEO_LIGHT]')
                # Una tanda de montaje no emite eventos por cada clip. El tic
                # debe descubrirlo y parchear la galería sin cortar la escucha.
                pagina.evaluate("""() => {
                  window.pruebaRefrescoNativo = {pedir, fuente:window.EventSource};
                  const prueba = window.pruebaRefrescoNativo;
                  const pid=APP.light.video.pid;
                  const escenas=[{id:'S001',t_in:0,t_out:2,duracion:2,imagen:null,clip:null},
                    {id:'S002',t_in:2,t_out:4,duracion:2,imagen:null,clip:null}];
                  PREVIA.ficha={escenas}; PREVIA.i=1; PREVIA.t=2.5; PREVIA.sonando=true;
                  APP.light.video.planos=[]; APP.light.video.vista='previa';
                  const caja=document.querySelector('.light-previa');
                  caja.appendChild(galeriaImagenesPrevia(escenas));
                  prueba.reproductor=document.createElement('video'); caja.appendChild(prueba.reproductor);
                  window.EventSource=class { addEventListener() {} close() {} };
                  pedir=async (ruta,...args) => {
                    if(ruta===API.planosHechos(pid,true)) return {plan:['S001','S002'],planos:{S001:{ruta:'poster-nuevo.png',sello:123}}};
                    if(ruta===`${API.proyecto(pid)}/previsualizacion`) return {escenas:[{...escenas[0],imagen:'poster-nuevo.png',clip:'clip-nuevo.mp4'},escenas[1]]};
                    if(ruta===API.paso(pid,'assets')) return APP.light.video.fichas.assets;
                    return prueba.pedir(ruta,...args);
                  };
                  seguirTrabajo(CLAVE_VIDEO_LIGHT,'montaje-nativo-sin-eventos',()=>{});
                }""")
                try:
                    pagina.wait_for_function("document.querySelector('.previa-lateral [data-escena=\"S001\"]') && PREVIA.ficha.escenas[0].clip==='clip-nuevo.mp4'", timeout=10000)
                    self.assertTrue(pagina.evaluate('pruebaRefrescoNativo.reproductor.isConnected'))
                    self.assertEqual(pagina.evaluate('[PREVIA.i,PREVIA.t,PREVIA.sonando]'), [1,2.5,True])
                finally:
                    pagina.evaluate("""() => {
                      soltarSeguimiento(CLAVE_VIDEO_LIGHT); pedir=pruebaRefrescoNativo.pedir;
                      window.EventSource=pruebaRefrescoNativo.fuente; PREVIA.sonando=false;
                      delete APP.trabajos[CLAVE_VIDEO_LIGHT]; delete window.pruebaRefrescoNativo;
                    }""")
                pagina.locator('#btn-inicio-estilos').click()
                self.assertEqual(pagina.locator('.ficha-estilo .nombre').filter(has_text='Prueba encapsulada').count(), 0)
                pagina.locator('#btn-estilos-ia').click()
                pagina.wait_for_selector('.estilos-ia')
                pagina.screenshot(path=str(capturas / 'estilos-ia-galeria.png'), full_page=True)
                pagina.set_viewport_size(dict(width=390, height=844))
                self.assertLessEqual(pagina.evaluate('document.documentElement.scrollWidth'), 390)
                cabecera = pagina.locator('#cabecera').bounding_box()
                pestanas = pagina.locator('.inicio-pestanas').bounding_box()
                self.assertLessEqual(pestanas['y'] + pestanas['height'], cabecera['y'] + cabecera['height'])
                self.assertGreaterEqual(pagina.locator('#btn-estilos-ia').bounding_box()['height'], 38)
                pagina.screenshot(path=str(capturas / 'estilos-ia-menu-movil.png'), full_page=True)
                self.assertEqual(errores, [])
                navegador.close()
        finally:
            proceso.terminate(); proceso.wait(timeout=15)


    @unittest.skipUnless(REAL, 'usa --real para navegador, sin IA ni instalaciones')
    def test_borrar_estilo_ia_quita_card_y_restaurar_lo_devuelve(self):
        import socket
        import subprocess
        import time
        import urllib.request
        from playwright.sync_api import sync_playwright
        from pasos import medios
        ficha = self.preparado()
        publicado = ia.publicar_base(self.raiz,ficha['id'],presets)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); puerto=sock.getsockname()[1]
        programa = f"import app,uvicorn; uvicorn.run(app.app,host='127.0.0.1',port={puerto},log_level='error')"
        proceso = subprocess.Popen([sys.executable,'-c',programa],env=dict(os.environ,ESTUDIO_PROYECTOS=self.raiz),
            cwd=Path(__file__).resolve().parents[1])
        try:
            url=f'http://127.0.0.1:{puerto}'
            for _ in range(100):
                try:
                    urllib.request.urlopen(url,timeout=1).close();break
                except OSError: time.sleep(.1)
            with sync_playwright() as pw:
                navegador=pw.chromium.launch(headless=True,executable_path=medios.edge())
                pagina=navegador.new_page(viewport=dict(width=390,height=844))
                errores=[]
                pagina.on('pageerror',lambda error:errores.append(str(error)))
                pagina.on('dialog',lambda dialogo:dialogo.accept())
                def abrir():
                    pagina.goto(url)
                    pagina.wait_for_function('APP.light.datos && !APP.light.cargando')
                    pagina.evaluate("document.querySelector('#inicio')?.remove()")
                    pagina.locator('#btn-estilos-ia').click()
                    pagina.wait_for_function('ESTILOS_IA_UI.fichas !== null')
                abrir()
                self.assertEqual(pagina.locator('.galeria-estilos .ficha-estilo').count(),1)
                pagina.evaluate('async id => { await borrarPresetLight(fichaLight(id)); }',publicado['id'])
                pagina.locator('#btn-estilos-ia').click()
                pagina.wait_for_function("document.querySelectorAll('.galeria-estilos .ficha-estilo').length===0")
                capturas=Path(os.environ.get('LOCALAPPDATA',tempfile.gettempdir()))/'Temp'/'opencode'
                pagina.screenshot(path=str(capturas/'estilos-ia-borrado-sin-card.png'),full_page=True)
                abrir()
                self.assertEqual(pagina.locator('.galeria-estilos .ficha-estilo').count(),0)
                self.assertTrue((ia.carpeta(self.raiz,ficha['id'])/'estilo.json').is_file())
                respuesta=pagina.request.post(url+f"/api/presets-canal/papelera/{publicado['id']}/restaurar",data={})
                self.assertTrue(respuesta.ok)
                pagina.evaluate('async () => { await cargarGaleriaLight(true); await cargarEstilosIA(); }')
                pagina.wait_for_function("document.querySelectorAll('.galeria-estilos .ficha-estilo').length===1")
                self.assertEqual(errores,[])
                navegador.close()
        finally:
            proceso.terminate();proceso.wait(timeout=15)


if __name__ == '__main__':
    unittest.main()
