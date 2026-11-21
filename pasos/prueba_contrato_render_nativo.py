"""Regresiones offline: formato de composición y Blender real frente a Pillow."""
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
from motores.estilo_ia import ejecutor
from pasos import animacion_nativa


class ContratoRender(unittest.TestCase):
    def setUp(self):
        self.contrato=dict(version=1,motor='blender',resolucion=[320,180])
        self.pedido=dict(ancho=320,alto=180,contrato_render=self.contrato)

    def test_prompt_blender_y_formato_prevalecen_sobre_referencia(self):
        prompt=animacion_nativa.encargo(dict(t_in=0,t_out=2),
            dict(resolucion=[1920,1080]),dict(analisis={'guia_visual':'Vertical 9:16'}),None,
            contrato_render=self.contrato)
        for texto in ('Blender real','Malla','renderer.render','horizontal 16:9',
                'NO centres un lienzo vertical','PIL.Image es SOLO el contrato'):
            self.assertIn(texto,prompt)
        self.assertNotIn('Usa solo Pillow',prompt)
        self.assertNotIn('mediante dibujo procedural\nPillow',prompt)

    def test_fuente_antigua_no_exige_blender_ni_rechaza_bandas(self):
        imagen=Image.new('RGB',(320,180))
        ImageDraw.Draw(imagen).rectangle((110,0,210,179),fill='red')
        ejecutor.comprobar_formato(imagen,dict(ancho=320,alto=180))
        ejecutor.comprobar_formato(imagen,dict(contrato_render=dict(motor='nativo')))
        self.assertIsNone(ejecutor.vigilar_blender(None,{}))

    def test_rechaza_short_centrado_en_horizontal(self):
        imagen=Image.new('RGB',(320,180))
        ImageDraw.Draw(imagen).rectangle((110,0,210,179),fill='red')
        with self.assertRaisesRegex(ValueError,'bandas negras'):
            ejecutor.comprobar_formato(imagen,self.pedido)

    def test_horizontal_completo_y_fundido_negro_validos(self):
        for color in ('black','red'):
            ejecutor.comprobar_formato(Image.new('RGB',(320,180),color),self.pedido)
        ejecutor.comprobar_formato(Image.new('RGB',(180,320),'red'),self.pedido)

    def test_blender_obligatorio_no_es_import_ni_arranque(self):
        with self.assertRaisesRegex(ValueError,'Blender real'):
            ejecutor.vigilar_blender(None,self.pedido)
        sesion=SimpleNamespace(render=Mock(return_value=('rgb','z')))
        pruebas=ejecutor.vigilar_blender(SimpleNamespace(_sesion=sesion),self.pedido)
        self.assertEqual(pruebas,[])  # arrancar Blender no cuenta como usarlo
        malla=SimpleNamespace(vertices=[1,2,3])
        self.assertEqual(sesion.render(320,180,malla,{},[],{},None),('rgb','z'))
        self.assertEqual(pruebas,[dict(ancho=320,alto=180,vertices=3,sprites=0)])
        for w,h,vertices in ((180,320,[1,2,3]),(320,180,[])):
            with self.assertRaisesRegex(ValueError,'geometría 3D'):
                sesion.render(w,h,SimpleNamespace(vertices=vertices),{},[],{},None)

    def test_blender_fallido_no_publica_evidencia(self):
        sesion=SimpleNamespace(render=Mock(side_effect=RuntimeError('fallo real')))
        pruebas=ejecutor.vigilar_blender(SimpleNamespace(_sesion=sesion),self.pedido)
        with self.assertRaises(RuntimeError):
            sesion.render(320,180,SimpleNamespace(vertices=[1,2,3]),{},[],{},None)
        self.assertEqual(pruebas,[])


if __name__=='__main__':
    unittest.main()
