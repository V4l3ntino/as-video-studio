"""Proyecta límites de utilería con las fuentes/cámaras congeladas de una prueba.

No renderiza, no califica arte y no usa siluetas aproximadas de texto. Complementa
la inspección de los PNG y de la capa p7; no prueba oclusiones internas.
"""
import bpy
import math
import json
import sys
import importlib.util
import inspect
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view


def main():
    args=sys.argv[sys.argv.index('--')+1:];folder=Path(args[0]);out=Path(args[1])
    sys.path.insert(0,str(folder/'fuentes'))
    import artesania as a
    from renderizar import punto
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s=bpy.context.scene;s.render.resolution_x=1080;s.render.resolution_y=1920;s.render.resolution_percentage=100
    bpy.ops.object.camera_add();cam=bpy.context.object;cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=32;s.camera=cam
    frames=sorted((folder/'intercambio').iterdir());first=json.loads((frames[0]/'escena.json').read_text(encoding='utf8'))
    targets={};pot=None;train=None
    if first['plano']=='cocina':
        kwargs={'piel':first['sprites'][0].get('piel','#FFF0DB')} if 'piel' in inspect.signature(a.Olla).parameters else {}
        pot=a.Olla(**kwargs);targets['olla']=pot.objetos
        if first.get('composicion')=='cocina_reencuadrada':
            a.encimera_y_cuenco();targets['cuenco']=[bpy.data.objects['cuenco_hueco']]
    else:
        train=a.Locomotora();targets['locomotora']=train.objetos
    program=None;ctx=dict(camara=cam,escena=s,salida=folder,artesania=a)
    source=folder/'fuentes/programa_bpy.py'
    if source.is_file():
        spec=importlib.util.spec_from_file_location('camara_comprobada',source);program=importlib.util.module_from_spec(spec);spec.loader.exec_module(program);program.preparar(ctx)
    rows=[]
    for i,frame in enumerate(frames):
        data=json.loads((frame/'escena.json').read_text(encoding='utf8'));c=data['camara'];t=data['t']
        cam.location=punto(c['eye']);cam.rotation_euler=(Vector(punto(c['target']))-cam.location).to_track_quat('-Z','Y').to_euler()
        cam.data.lens=16/math.tan(math.radians(c['fov']/2))
        if pot:
            hero=data.get('composicion')=='cocina_reencuadrada'
            kwargs={'altura_mesa':1.44 if hero else 1.43} if 'altura_mesa' in inspect.signature(pot.actualizar).parameters else {}
            pot.actualizar(data['sprites'][0]['mano_d'],t,destino=(1.65,1.65,-5) if hero else (1.8,1.66,-5),**kwargs)
        if train:train.actualizar(t)
        if program:ctx['intercambio']=data;program.actualizar(ctx,t)
        bpy.context.view_layer.update()
        for name,objects in targets.items():
            points=[world_to_camera_view(s,cam,obj.matrix_world@Vector(v)) for obj in objects if obj.type in ('MESH','CURVE') for v in obj.bound_box]
            bounds=dict(x_min=min(v.x for v in points),x_max=max(v.x for v in points),y_min=min(v.y for v in points),y_max=max(v.y for v in points),z_min=min(v.z for v in points))
            good=bounds['x_min']>=0 and bounds['y_min']>=0 and bounds['x_max']<=1 and bounds['y_max']<=1 and bounds['z_min']>0
            rows.append(dict(frame=i,t=t,objeto=name,completo=good,**bounds))
    result=dict(frames=len(frames),limites=rows,fuera=[r for r in rows if not r['completo']],limite='Geometría y cámara; no prueba de arte ni seguridad de subtítulos')
    if out.exists():raise ValueError('no se sobrescribe una auditoría')
    out.write_text(json.dumps(result,indent=2),encoding='utf8');print(dict(frames=len(frames),fuera=len(result['fuera'])),flush=True)
    if result['fuera']:raise ValueError('Hay utilería fuera de cuadro; consultar la auditoría guardada')


if __name__=='__main__':main()
