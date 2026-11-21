"""Perfil opt-in sin modificar narración, marcas ni el dibujo clásico."""
import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
_DATOS=tempfile.TemporaryDirectory(prefix='ricksclips_subtitulos_')
for clave in ('ESTUDIO_SECRETOS','ESTUDIO_AJUSTES','ESTUDIO_ESTADISTICAS','ESTUDIO_PRESETS','ESTUDIO_BANCO_PRESETS'):
    os.environ[clave]=str(Path(_DATOS.name)/clave)
from pasos import p7_callouts as p7,subtitulos,presets_canal as presets


class SubtitulosRicksClips(unittest.TestCase):
    def setUp(self):
        self.escena=dict(id='S001',narracion='The rail bends. ¿Por qué?',t_in=10,t_out=12,
            marcas=[[10,10.2],[10.2,10.5],[10.5,10.8],[10.8,11.2],[11.2,12]])

    def test_cada_palabra_conserva_su_marca_y_no_muta_entradas(self):
        antes=copy.deepcopy(self.escena)
        trozos=subtitulos.de_escena(self.escena,palabra_a_palabra=True)
        self.assertEqual([t['texto'] for t in trozos],self.escena['narracion'].split())
        self.assertEqual([t['desde'] for t in trozos],[0,.2,.5,.8,1.2])
        self.assertEqual(self.escena,antes)

    def test_sin_marcas_fiables_no_inventa_sincronia(self):
        self.escena['marcas'].pop()
        self.assertEqual(subtitulos.de_escena(self.escena,palabra_a_palabra=True),[])

    def test_blanco_contorno_negro_sin_caja_y_fuera_de_zoom(self):
        p=dict(subtitulo_perfil='ricksclips_v1')
        svg,fichas=p7.capa_fija_de(self.escena,p,salida=(360,640))
        self.assertEqual(len(fichas),5)
        self.assertIn('stroke="#000000"',svg)
        self.assertIn('fill="#ffffff"',svg)
        self.assertIn('paint-order="stroke fill"',svg)
        self.assertIn('y="448"',svg)
        self.assertIn('y="459.52"',svg)
        self.assertNotIn('<rect',svg)
        self.assertIn('¿Por',svg)

    def test_ausencia_perfil_y_clasico_dan_mismos_bytes(self):
        a=p7.capa_fija_de(self.escena,{},salida=(360,640))
        b=p7.capa_fija_de(self.escena,dict(subtitulo_perfil='clasico'),salida=(360,640))
        self.assertEqual(a,b)
        self.assertIn('<rect',a[0])

    def test_preset_propaga_y_exporta_perfil_sin_anadirlo_a_otros(self):
        ficha=dict(tipo='rotulos',datos=dict(subtitulo_perfil='ricksclips_v1'))
        cambios=presets.cambios_para(ficha)
        self.assertEqual(cambios,dict(callouts=dict(subtitulo_perfil='ricksclips_v1')))
        self.assertEqual(presets.datos_de_params(cambios,incluir=['rotulos']),dict(rotulos=ficha['datos']))
        self.assertNotIn('subtitulo_perfil',presets.datos_de_params({},incluir=['rotulos']).get('rotulos',{}))

    def test_rechaza_perfil_desconocido(self):
        with self.assertRaisesRegex(presets.ErrorPreset,'perfil'):
            presets.guardar('rotulos','Prueba',dict(subtitulo_perfil='desconocido'))

    def test_formato_explicito_del_estilo_solo_va_al_brief(self):
        cambios=presets.cambios_para(dict(tipo='montaje',datos=dict(formato='vertical',subtitulos=True)))
        self.assertEqual(cambios,dict(brief=dict(formato='vertical'),render=dict(subtitulos=True)))
        self.assertNotIn('brief',presets.cambios_para(dict(tipo='montaje',datos=dict(subtitulos=True))))


if __name__=='__main__':unittest.main()
