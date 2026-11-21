"""Regresiones locales de geometría, vestuario y aislamiento. Sin proveedores.

--estilo señala únicamente dependencias instaladas de una versión existente.
No modifica paquetes ni proyectos.
"""
import argparse
import copy
from pathlib import Path
import sys
import types
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


class Contratos(unittest.TestCase):
    def test_pared_continua_normales_hacia_el_corredor(self):
        from espacio3d import Malla
        from decorados3d import pared_canon
        for side in (-1,1):
            m=Malla();pared_canon(m,side)
            self.assertEqual(len(m.vertices),100*36*6)
            self.assertTrue(all(v[3]*side<0 for v in m.vertices))
            # Triangles on either side of every longitudinal seam share positions.
            strip=36*6
            for i in range(99):
                a={tuple(v[:3]) for v in m.vertices[i*strip:(i+1)*strip]}
                b={tuple(v[:3]) for v in m.vertices[(i+1)*strip:(i+2)*strip]}
                self.assertEqual(len(a&b),37)

    def test_contacto_rotado_independiente_de_escala(self):
        from contactos import centro_por_agarre,transformar
        for scale in (.7,1,2.4):
            for angle in (-80,0,35):
                hand=(261*scale,379*scale)
                center=centro_por_agarre(hand,(-14,8),angle,scale)
                actual=transformar((-14,8),center,angle,scale)
                for a,b in zip(actual,hand):self.assertAlmostEqual(a,b,places=9)

    def test_normales_ellipsoide_lisses(self):
        from espacio3d import Malla
        import numpy as np
        m=Malla();m.esfera((0,0,0),(3,1,2),'#FFFFFF')
        for v in m.vertices:
            expected=np.array(v[:3])/np.array((9,1,4))
            expected/=np.linalg.norm(expected)
            self.assertLess(np.linalg.norm(np.array(v[3:6])-expected),1e-5)

    def test_torno_normales_exteriores_y_cavidad(self):
        import numpy as np
        from espacio3d import Malla
        m=Malla();m.torno((0,0,0),[(1,0),(1,1)],'#FFFFFF')
        self.assertTrue(all(v[0]*v[3]+v[2]*v[5]>.9 for v in m.vertices))
        top=Malla();top.torno((0,0,0),[(1,0),(0,0)],'#FFFFFF')
        self.assertGreater(sum(v[4] for v in top.vertices),0)

    def test_arquitectura_cache_no_se_contamina(self):
        from decorados3d import escena
        a,cam,amb=escena('oeste',0);n=len(a.vertices)
        a.caja((0,2,0),(1,1,1),'#FF0000');cam['fov']=3;amb['potencia']=999
        b,c,d=escena('oeste',1)
        self.assertEqual(len(b.vertices),n);self.assertNotEqual(c['fov'],3)
        self.assertNotEqual(d.get('potencia'),999)

    def test_agua_normales_y_movimiento(self):
        from espacio3d import Malla
        from decorados3d import oceano
        a,b=Malla(),Malla();oceano(a,0);oceano(b,.5)
        self.assertTrue(all(v[4]>.1 for v in a.vertices))
        self.assertNotEqual(a.vertices,b.vertices)
        self.assertTrue(all(v[-1]==-4 for v in a.vertices))

    def test_rig_autocontenido_anclas_sombrero_y_mirada(self):
        import ast
        from PIL import Image,ImageChops
        from herramientas.preparar_ricksclips import compilar_rig
        code=compilar_rig((ESTILO/'versiones/v1/herramientas/personaje_base.py').read_text(encoding='utf8'))
        imports={n.names[0].name.split('.')[0] for n in ast.walk(ast.parse(code)) if isinstance(n,ast.Import)}
        self.assertNotIn('vestuario',imports)
        rig=types.ModuleType('rig_nuevo');exec(code,rig.__dict__)
        e=rig.estado_base();e.update(x=200,y=530,esc=1.3,sombra=0,sombrero='oeste')
        a=Image.new('RGBA',(400,560));anchors=rig.dibujar(a,e,{'t':1})
        self.assertTrue({'cabeza','mano_i','mano_d','ojo_i','ojo_d','pie_i','pie_d'}.issubset(anchors))
        e.update(cabeza_inc=18,mirada=[.8,-.4]);b=Image.new('RGBA',a.size);rig.dibujar(b,e,{'t':1})
        self.assertIsNotNone(ImageChops.difference(a,b).getbbox())

    def test_escena_libre_planos_no_mutables(self):
        from planos_revision import plano
        a=plano('medio');a['actores'][0]['apariencia']['ropa']='vestido'
        self.assertEqual(plano('medio')['actores'][0]['apariencia']['ropa'],'chaqueta')
        from realizacion import camara
        keys=[dict(t=0,eye=[0,1,3]),dict(t=1,eye=[0,1,1])]
        original=copy.deepcopy(keys);self.assertEqual(camara(keys,.5)['eye'],[0,1,2])
        self.assertEqual(keys,original)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--estilo',type=Path,required=True)
    args,rest=parser.parse_known_args();ESTILO=args.estilo
    sys.path[:0]=[str(ESTILO/'versiones/v3/dependencias'),str(ROOT/'motores/ricksclips')]
    unittest.main(argv=[sys.argv[0],*rest])
