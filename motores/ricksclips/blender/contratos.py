"""Regresiones locales bpy sin render ni proveedores. No certifican acabado."""
import bpy
import sys
import math
import json
from pathlib import Path


def main():
    args=sys.argv[sys.argv.index('--')+1:];entrada=Path(args[0]);salida=Path(args[1])
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import artesania as a
    bpy.ops.wm.read_factory_settings(use_empty=True)
    pot=a.Olla();contacts=[];minimos=[]
    mat=a.mate('prueba_normales',(.5,.5,.5))
    cylinder=a.torno('prueba_torno',(0,0,0),[(1,0),(1,1)],mat,n=32)
    cylinder.data.update()
    assert all(p.normal.x*p.center.x+p.normal.y*p.center.y>.9 for p in cylinder.data.polygons)
    for folder in sorted(entrada.iterdir()):
        data=json.loads((folder/'escena.json').read_text(encoding='utf8'))
        result=pot.actualizar(data['sprites'][0]['mano_d'],data['t']);bpy.context.view_layer.update()
        assert result['error_agarre_m']<1e-6,result
        contacts.append(result)
        low=min((ob.matrix_world@a.Vector(v)).z for ob in pot.objetos for v in ob.bound_box)
        assert low>=1.45-1e-5,(data['t'],low,result)
        minimos.append(low)
    try:pot.actualizar((0,1,0),1.3)
    except ValueError:pass
    else:raise AssertionError('Un agarre imposible debe fallar, no atravesar la mesa')
    train=a.Locomotora();checks=[]
    for t in (0,.4,1,1.3,2.16):
        train.actualizar(t);bpy.context.view_layer.update()
        assert abs(train.raiz.location.y- (14-t*1.7))<1e-5
        assert all(abs(w.rotation_euler.x-t*1.7/.36)<1e-5 for w in train.ruedas)
        assert abs(train.origen[1]+.51-.36-.345)<1e-6
        checks.append(dict(t=t,angulo=train.ruedas[0].rotation_euler.x))
    result=dict(contactos=len(contacts),error_maximo_m=max(x['error_agarre_m'] for x in contacts),
        cota_minima_olla=min(minimos),mesa_cota_superior=1.43,
        olla_no_penetra_mesa_verticalmente=min(minimos)>=1.43,
        rodadura_sin_deslizamiento_analitico=True,altura_ruedas_sobre_cabeza_riel=True,
        normales_torno_hacia_fuera=True,
        locomotora=checks,limite='Comprueba muestras y ecuaciones; no colisiones universales ni fidelidad')
    salida.write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
