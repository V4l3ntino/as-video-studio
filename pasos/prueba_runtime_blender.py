"""Contratos aislados del runtime opt-in. Sin Blender real, red ni proveedores."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pasos import runtime_blender as r,espacio_estilo as e
from motores.estilo_ia import blender_cliente


class Contratos(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.paquete=dict(codigo='def pintar(p,t): return None',archivos={'herramientas/servidor.py':'pass'})

    def test_ausencia_no_introduce_metadata(self):
        validado=e.validar(self.paquete)
        self.assertNotIn('blender',validado)
        e.materializar(self.root/'viejo',validado,[])
        self.assertFalse((self.root/'viejo/requisitos/blender.json').exists())
        self.assertFalse((self.root/'viejo/motores/blender_cliente_estudio.py').exists())

    def test_metadata_viaja_y_se_sella(self):
        self.paquete['blender']=r.requisito('herramientas/servidor.py')
        validado=e.validar(self.paquete);e.materializar(self.root/'nuevo',validado,[])
        inv=e.inventario(self.root/'nuevo');marca=e.huella(inv)
        self.assertIn('requisitos/blender.json',inv)
        self.assertIn('motores/blender_cliente_estudio.py',inv)
        e.copiar(self.root/'nuevo',self.root/'copia',marca)
        e.verificar(self.root/'copia',marca)
        (self.root/'copia/requisitos/blender.json').write_text('{}')
        with self.assertRaises(ValueError):e.verificar(self.root/'copia',marca)

    def test_pedido_no_activa_blender_en_paquete_antiguo(self):
        destino=self.root/'viejo';e.materializar(destino,e.validar(self.paquete),[])
        with patch.object(e,'instalar'),patch.object(e,'correr',side_effect=RuntimeError('fin de prueba')),\
                patch.object(r,'resolver',side_effect=AssertionError('runtime no solicitado')):
            with self.assertRaisesRegex(RuntimeError,'fin de prueba'):
                e.renderizar(destino,dict(ancho=16,alto=16,fps=1,duracion=1,blender={'ejecutable':'ajeno'}),
                    self.root/'salida',lambda *a:None)
        self.assertNotIn('blender',json.loads((self.root/'salida/pedido.json').read_text(encoding='utf8')))

    def test_requisito_rechaza_version_ruta_y_distribucion(self):
        for campo,valor in [('version','4.4'),('servidor','../servidor.py'),
                ('servidor','herramientas/ausente.py'),('distribucion',{})]:
            dato=r.requisito('herramientas/servidor.py');dato[campo]=valor
            with self.subTest(campo=campo,valor=valor),self.assertRaises(ValueError):r.validar(dato,self.paquete['archivos'])

    def test_ejecutable_explicito_version_incorrecta(self):
        exe=self.root/'blender.exe';exe.write_bytes(b'prueba')
        with patch.dict(os.environ,ESTUDIO_BLENDER=str(exe)),patch.object(r.subprocess,'run') as run:
            run.return_value.returncode=0;run.return_value.stdout='Blender 4.4.0\n'
            with self.assertRaises(ValueError):r.resolver(r.requisito('herramientas/servidor.py'),lambda *a:None)

    def test_arranque_no_hereda_python_y_no_escribe_bytecode(self):
        exe=self.root/'blender.exe';exe.write_bytes(b'prueba')
        server=self.root/'herramientas/servidor.py';server.parent.mkdir();server.write_text('pass')
        pedido=dict(salida=str(self.root/'render'),ancho=16,alto=16,fps=1,
            blender={**r.requisito('herramientas/servidor.py'),'ejecutable':str(exe),
                'sha256_ejecutable':hashlib.sha256(exe.read_bytes()).hexdigest()})
        with patch.dict(os.environ,PYTHONPATH='ruta ajena',PYTHONHOME='otro Python'),\
                patch.object(blender_cliente.subprocess,'Popen') as popen,\
                patch.object(blender_cliente.Sesion,'_respuesta',return_value={'estado':'listo','version':r.VERSION}):
            popen.return_value.poll.return_value=0;popen.return_value.returncode=0;popen.return_value.pid=123
            sesion=blender_cliente.Sesion(self.root,pedido);sesion.cerrar()
            args,kw=popen.call_args
            self.assertIn('--python-use-system-env',args[0])
            self.assertNotIn('PYTHONPATH',kw['env']);self.assertNotIn('PYTHONHOME',kw['env'])
            self.assertEqual(kw['env']['PYTHONDONTWRITEBYTECODE'],'1')
            self.assertEqual(kw['env']['PYTHONNOUSERSITE'],'1')
            self.assertEqual(kw['cwd'],str(self.root.resolve()/'cache'))
            self.assertNotEqual(kw['cwd'],str(sesion.raiz))

    def _instalacion(self):
        archive=self.root/'oficial_simulado.zip'
        with zipfile.ZipFile(archive,'w') as z:z.writestr('blender-4.5.16-windows-x64/blender.exe',b'binario de prueba')
        dist={**r.DISTRIBUCION,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
        env={k:v for k,v in os.environ.items() if k not in ('ESTUDIO_BLENDER','ESTUDIO_RUNTIMES','ESTUDIO_BLENDER_ARCHIVO')}
        env.update(ESTUDIO_RUNTIMES=str(self.root/'runtimes'),ESTUDIO_BLENDER_ARCHIVO=str(archive))
        return archive,dist,env

    @unittest.skipUnless(os.name=='nt','instalador Windows x64')
    def test_instalacion_local_sello_y_alteraciones(self):
        archive,dist,env=self._instalacion()
        with patch.dict(os.environ,env,clear=True),patch.object(r,'DISTRIBUCION',dist),patch.object(r.urllib.request,'urlopen',side_effect=AssertionError('sin red')):
            result=r.resolver(r.requisito('herramientas/servidor.py'),lambda *a:None)
            exe=Path(result['ejecutable']);folder=exe.parent.parent
            self.assertEqual(r.verificar_instalacion(folder),exe)
            extra=folder/'inyectado.py';extra.write_text('pass')
            with self.assertRaises(ValueError):r.verificar_instalacion(folder)
            extra.unlink();exe.write_bytes(b'alterado')
            with self.assertRaises(ValueError):r.verificar_instalacion(folder)
            self.assertTrue(archive.is_file())

    @unittest.skipUnless(os.name=='nt','instalador Windows x64')
    def test_archivo_incorrecto_no_se_instala(self):
        archive,dist,env=self._instalacion();dist['sha256']='0'*64
        with patch.dict(os.environ,env,clear=True),patch.object(r,'DISTRIBUCION',dist):
            with self.assertRaises(ValueError):r.resolver(r.requisito('herramientas/servidor.py'),lambda *a:None)
            self.assertFalse((self.root/'runtimes/blender'/('0'*20)).exists())


if __name__=='__main__':unittest.main()
