"""Contratos de escenografía nativa sin bpy, GPU, red ni proveedores."""
import importlib
import os
from pathlib import Path
import sys
import types
import unittest
import tempfile
from unittest.mock import patch
import numpy  # Cargar extensiones antes de restaurar sys.modules entre pruebas.
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
_DATOS=tempfile.TemporaryDirectory(prefix='ricksclips_blender_')
for clave in ('ESTUDIO_SECRETOS','ESTUDIO_ESTADISTICAS','ESTUDIO_AJUSTES','ESTUDIO_RECURSOS_ANIMACION'):
    os.environ[clave]=str(Path(_DATOS.name)/clave)


class Escenografia(unittest.TestCase):
    def setUp(self):
        self.mods=patch.dict(sys.modules,{'moderngl':types.ModuleType('moderngl')})
        self.mods.start();self.addCleanup(self.mods.stop)
        self.path=str(ROOT/'motores/ricksclips');sys.path.insert(0,self.path)
        self.addCleanup(lambda:sys.path.remove(self.path))
        for name in ('espacio3d','decorados3d','artesania3d'):sys.modules.pop(name,None)
        self.e=importlib.import_module('espacio3d')
        self.d=importlib.import_module('decorados3d')
        self.a=importlib.import_module('artesania3d')

    def test_opengl_sin_opciones_blender(self):
        _,_,amb=self.d.escena('cocina',0)
        self.assertNotIn('blender',amb)

    def test_cocina_nativa_no_duplica_cuencos(self):
        self.e.Renderer.backend='blender'
        with patch.object(self.d,'cuenco') as uno,patch.object(self.a,'cuenco') as dos:
            _,_,amb=self.d.escena('cocina',0)
        uno.assert_not_called();dos.assert_not_called()
        self.assertEqual(amb['blender'],dict(t=0,cocina=True,ollas=[]))

    def test_tren_y_paredes_solo_nativos(self):
        self.e.Renderer.backend='blender'
        with patch.object(self.d,'tren') as tren,patch.object(self.d,'pared_canon') as pared:
            _,_,amb=self.d.escena('canon',1.2)
        tren.assert_not_called();pared.assert_not_called()
        self.assertTrue(amb['blender']['tren'])
        self.assertEqual(amb['blender']['t'],1.2)

    def test_opciones_no_mutadas_y_tren_opcional(self):
        self.e.Renderer.backend='blender'
        opciones={'tren':False,'torcido':.8}
        _,_,amb=self.d.escena('puente',.5,opciones)
        self.assertEqual(opciones,{'tren':False,'torcido':.8})
        self.assertFalse(amb['blender']['tren'])

    def test_ambiente_nativo_no_comparte_estado_cacheado(self):
        self.e.Renderer.backend='blender'
        _,_,amb=self.d.escena('cocina',0)
        amb['blender']['ollas'].append({'mano':[0,2,0]})
        _,_,otro=self.d.escena('cocina',1)
        self.assertEqual(otro['blender']['ollas'],[])
        self.assertEqual(otro['blender']['t'],1)


class Publicacion(unittest.TestCase):
    def _evidencias(self,root):
        import json
        from herramientas import validacion_blender as v
        fuentes={'escena':'fuente de prueba'}
        integracion=dict(fuentes=fuentes,copia_sellada=True,pixeles_identicos=True,guarda_procesos=True,cierre_en_error=True)
        proyecto=dict(fuentes=fuentes,congelar=True,duplicado_portable=True,poster_duplicado_identico=True,
            reconstruccion_dependencias=True,subtitulos_p7_reales=True,p6_nativo_real=True,
            recuperacion_p6_sin_regenerar=True,clips_portables=True,preparacion_real={'prueba':True},montaje_p8_real={'prueba':True})
        recuperacion=dict(fuentes=fuentes,**{k:dict(sin_huerfanos=True,entradas_conservadas=True) for k in ('parar','timeout','error_bpy')})
        hd=root/'hd';hd.mkdir();clip=hd/'clip.mp4';clip.write_bytes(b'clip simulado para probar puerta, no render')
        revision=dict(fuentes=fuentes,calidad_equivalente_verificada=False,planos={k:
            dict(sha256_clip=v.sha(clip),observaciones='Fixture de prueba, no revisión real',
                revisado=True,fallos_bloqueantes=[]) for k in v.PLANOS})
        gpu=dict(fuentes=fuentes,backend='blender',sombra_sprite_pixeles=35,
            runtime={'version':'4.5.16','motor':'BLENDER_EEVEE_NEXT'},**{k:True for k in
                ('oclusion','profundidad','camara','volumen','determinismo','normales')})
        (root/'muestra').mkdir()
        datos={'integracion.json':integracion,'proyecto.json':proyecto,'recuperacion.json':recuperacion,
            'revision.json':revision,'muestra/pruebas_gpu.json':gpu,'hd/fuentes.json':fuentes,
            'hd/renders.json':[dict(plano=k,clip=str(clip)) for k in v.PLANOS],
            'reproduccion.json':dict(secuencias=[dict(plano=k,fin=True,sha256_clip=v.sha(clip)) for k in v.PLANOS])}
        for name,dato in datos.items():(root/name).write_text(json.dumps(dato),encoding='utf8')
        prueba=dict(fuentes=fuentes,integracion=str(root/'integracion.json'),proyecto=str(root/'proyecto.json'),
            recuperacion=str(root/'recuperacion.json'),hd=str(hd),revision_visual=str(root/'revision.json'),
            reproduccion=str(root/'reproduccion.json'))
        (root/'blender_publicacion.json').write_text(json.dumps(prueba),encoding='utf8')
        return fuentes,clip

    def test_clip_alterado_despues_de_revision_bloquea(self):
        import json
        from herramientas import validacion_blender as v
        probe=json.dumps({'streams':[dict(width=1080,height=1920,avg_frame_rate='25/1',nb_frames='55')]})
        with tempfile.TemporaryDirectory() as tmp:
            fuentes,clip=self._evidencias(Path(tmp))
            with patch.object(v.subprocess,'check_output',return_value=probe.encode()):
                v.comprobar(tmp,fuentes)
                clip.write_bytes(b'otro clip no revisado')
                with self.assertRaisesRegex(ValueError,'sin revisión visual'):v.comprobar(tmp,fuentes)

    def test_no_acepta_carpeta_sin_evidencia_completa(self):
        import tempfile
        from herramientas.validacion_blender import comprobar
        with tempfile.TemporaryDirectory() as tmp,self.assertRaisesRegex(ValueError,'no publicable'):
            comprobar(tmp,{})

    def test_fuentes_distintas_bloquean(self):
        import json
        from herramientas.validacion_blender import comprobar
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'blender_publicacion.json').write_text(json.dumps({'fuentes':{'escena':'anterior'}}))
            with self.assertRaisesRegex(ValueError,'otras fuentes'):comprobar(tmp,{'escena':'actual'})

    def test_no_basta_copia_ni_bandera_de_preparacion(self):
        import json
        from herramientas.validacion_blender import comprobar
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fuentes={'escena':'actual'}
            integracion=dict(fuentes=fuentes,copia_sellada=True,pixeles_identicos=True,
                guarda_procesos=True,cierre_en_error=True)
            proyecto=dict(fuentes=fuentes,congelar=True,duplicado_portable=True,poster_duplicado_identico=True,
                reconstruccion_dependencias=True,subtitulos_p7_reales=True,preparacion_real={'version':6},
                p6_nativo_real=True,recuperacion_p6_sin_regenerar=True,clips_portables=True)
            for name,dato in [('integracion',integracion),('proyecto',proyecto)]:
                (root/(name+'.json')).write_text(json.dumps(dato))
            (root/'blender_publicacion.json').write_text(json.dumps(dict(fuentes=fuentes,
                integracion=str(root/'integracion.json'),proyecto=str(root/'proyecto.json'))))
            with self.assertRaisesRegex(ValueError,'montaje real'):comprobar(root,fuentes)


if __name__=='__main__':unittest.main()
