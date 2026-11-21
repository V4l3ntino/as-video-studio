"""Muestras editoriales sin cambiar motores ni versiones históricas."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pasos import muestra_tarjeta as m


class Muestras(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.marca=dict(id='a'*32,version=5,huella='b'*64)
        self.ficha=json.dumps(dict(espacio=self.marca))
        (self.root/'estilo.json').write_text(self.ficha,encoding='utf8')
        self.clip=self.root/'nuevo.mp4';self.clip.write_bytes(b'clip de prueba')

    def instalar(self):
        with patch('pasos.medios_escena.informacion_video',return_value=dict(ancho=1080,alto=1920,duracion=17.6)):
            return m.instalar(self.root,self.clip,'Blender experimental; Crear vídeo usa v5')

    def test_ausencia_conserva_camino_clasico(self):
        self.assertIsNone(m.leer(self.root,self.marca))

    def test_muestra_no_modifica_motor_y_viaja_por_sha(self):
        dato=self.instalar()
        self.assertEqual((self.root/'estilo.json').read_text(encoding='utf8'),self.ficha)
        self.assertEqual(dato,m.leer(self.root,self.marca))
        self.assertEqual((self.root/dato['ruta']).read_bytes(),self.clip.read_bytes())

    def test_nueva_version_no_hereda_preview_anterior(self):
        self.instalar()
        self.assertIsNone(m.leer(self.root,dict(self.marca,version=6)))

    def test_alteracion_rechazada(self):
        dato=self.instalar();(self.root/dato['ruta']).write_bytes(b'alterado')
        with self.assertRaises(ValueError):m.leer(self.root,self.marca)

    def test_ruta_fuera_rechazada(self):
        dato=self.instalar();dato['ruta']='../clip.mp4'
        (self.root/'muestra_tarjeta.json').write_text(json.dumps(dato),encoding='utf8')
        with self.assertRaises(ValueError):m.leer(self.root,self.marca)

    def test_lectura_ignora_preview_persistida_de_otra_version_sin_escribir(self):
        from pasos import estilos_ia
        dato=self.instalar();sid='a'*32
        ficha=dict(id=sid,espacio=dict(self.marca,version=6),estado='preparado',muestra_tarjeta=dato)
        ruta=self.root/'estilo.json';ruta.write_text(json.dumps(ficha),encoding='utf8')
        antes=ruta.read_bytes()
        with patch.object(estilos_ia,'carpeta',return_value=self.root):
            resultado=estilos_ia.leer('no se usa',sid)
        self.assertNotIn('muestra_tarjeta',resultado)
        self.assertEqual(antes,ruta.read_bytes())

    def test_limpieza_solo_retira_campo_derivado(self):
        dato=self.instalar()
        ficha=dict(espacio=dict(self.marca,version=6),estado='preparado',otro='conservar')
        ruta=self.root/'estilo.json';ruta.write_text(json.dumps(dict(ficha,muestra_tarjeta=dato)),encoding='utf8')
        descriptor=(self.root/'muestra_tarjeta.json').read_bytes()
        self.assertEqual(m.limpiar_derivada(self.root),dato)
        self.assertEqual(json.loads(ruta.read_text(encoding='utf8')),ficha)
        self.assertEqual((self.root/'muestra_tarjeta.json').read_bytes(),descriptor)
        self.assertTrue((self.root/dato['ruta']).is_file())


if __name__=='__main__':unittest.main()
