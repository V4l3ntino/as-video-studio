"""Backend experimental bpy. Metros, Y arriba en intercambio; Z arriba en Blender.

Se ejecuta fuera del servicio. Mallas, materiales y sprites participan en el mismo
render de profundidad/sombras. Sin fotogramas de referencia ni .blend monolítico.
"""
import bpy
import gpu
import numpy as np
import json
import math
import sys
import time
import ctypes
import importlib.util
from pathlib import Path
from mathutils import Vector


def memoria_proceso():
    if sys.platform!='win32':return None
    class Memoria(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong),
            *[(k,ctypes.c_size_t) for k in ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage',
            'QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]]
    m=Memoria();m.cb=ctypes.sizeof(m)
    kernel=ctypes.windll.kernel32;kernel.GetCurrentProcess.restype=ctypes.c_void_p
    get=ctypes.windll.psapi.GetProcessMemoryInfo
    get.argtypes=[ctypes.c_void_p,ctypes.POINTER(Memoria),ctypes.c_ulong]
    if not get(kernel.GetCurrentProcess(),ctypes.byref(m),m.cb):return dict(error=ctypes.GetLastError())
    return dict(working_set_bytes=m.WorkingSetSize,pico_working_set_bytes=m.PeakWorkingSetSize)


def punto(v): return (float(v[0]),-float(v[2]),float(v[1]))


def material(tipo):
    mat=bpy.data.materials.new('material_'+str(tipo));mat.use_nodes=True
    n=mat.node_tree.nodes;l=mat.node_tree.links
    p=n.get('Principled BSDF')
    attr=n.new('ShaderNodeVertexColor');attr.layer_name='tinta'
    l.new(attr.outputs['Color'],p.inputs['Base Color'])
    p.inputs['Roughness'].default_value={1:.58,2:.87,3:.42,4:.16}.get(tipo,.65)
    p.inputs['Metallic'].default_value=.50 if tipo==3 else 0
    if tipo==4:
        p.inputs['IOR'].default_value=1.333
        p.inputs['Coat Weight'].default_value=.35
        p.inputs['Coat Roughness'].default_value=.1
    if tipo==6:
        l.new(attr.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=2
    if tipo in (1,2,3):
        tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=5 if tipo==2 else 12
        tex.inputs['Detail'].default_value=3
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16
        bump.inputs['Distance'].default_value=.055 if tipo==2 else .012
        l.new(tex.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
    return mat


def malla(datos,mats):
    xyz=datos[:,:3][:,[0,2,1]].copy();xyz[:,1]*=-1
    # Triángulos explícitos conservan posición y normales del motor v5.
    mesh=bpy.data.meshes.new('escenografia')
    mesh.from_pydata(xyz.tolist(),[],np.arange(len(xyz)).reshape(-1,3).tolist())
    mesh.update()
    for mat in mats:mesh.materials.append(mat)
    colors=np.ones((len(datos),4),dtype='f4');colors[:,:3]=datos[:,6:9]
    # RGB del motor es sRGB, no energía lineal.
    colors[:,:3]=np.where(colors[:,:3]<=.04045,colors[:,:3]/12.92,((colors[:,:3]+.055)/1.055)**2.4)
    mesh.color_attributes.new(name='tinta',type='FLOAT_COLOR',domain='CORNER').data.foreach_set('color',colors.ravel())
    kinds=np.where(datos[::3,9]>0,6,np.clip(-datos[::3,9],0,5)).astype('i4')
    mesh.polygons.foreach_set('material_index',kinds)
    normals=datos[:,3:6][:,[0,2,1]].copy();normals[:,1]*=-1
    mesh.polygons.foreach_set('use_smooth',np.ones(len(kinds),dtype=bool))
    mesh.normals_split_custom_set(normals.tolist())
    obj=bpy.data.objects.new('escenario',mesh);bpy.context.collection.objects.link(obj)
    return obj


def sprite(item,folder):
    mesh=bpy.data.meshes.new('rig_plano');mesh.from_pydata([punto(v) for v in item['vertices']],[],[(0,1,2,3)])
    mesh.uv_layers.new(name='UVMap')
    for loop,uv in zip(mesh.uv_layers.active.data,[(0,0),(1,0),(1,1),(0,1)]):loop.uv=uv
    obj=bpy.data.objects.new('rig_articulado',mesh);bpy.context.collection.objects.link(obj)
    mat=bpy.data.materials.new('rig_alfa');mat.use_nodes=True
    mat.surface_render_method='DITHERED'
    n=mat.node_tree.nodes;l=mat.node_tree.links;p=n.get('Principled BSDF')
    tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(folder/item['imagen']),check_existing=False)
    l.new(tex.outputs['Color'],p.inputs['Base Color'])
    # Corte explícito: huecos transparentes no deben tapar fondo ni sombrearlo.
    cut=n.new('ShaderNodeMath');cut.operation='GREATER_THAN';cut.inputs[1].default_value=.3
    l.new(tex.outputs['Alpha'],cut.inputs[0]);l.new(cut.outputs[0],p.inputs['Alpha'])
    l.new(tex.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=.35
    p.inputs['Roughness'].default_value=.9
    mesh.materials.append(mat)
    return obj


def luz(nombre,tipo,pos,energia,color,size=3,target=None):
    d=bpy.data.lights.new(nombre,tipo);d.energy=energia;d.color=color
    if tipo=='AREA': d.shape='DISK';d.size=size
    if tipo=='SUN':d.angle=math.radians(9)
    o=bpy.data.objects.new(nombre,d);bpy.context.collection.objects.link(o);o.location=punto(pos)
    if target is not None:o.rotation_euler=(Vector(punto(target))-o.location).to_track_quat('-Z','Y').to_euler()
    return o


def main():
    if bpy.app.version!=(4,5,16):raise RuntimeError('Este piloto requiere Blender 4.5.16; no se ha validado otra versión')
    args=sys.argv[sys.argv.index('--')+1:];out=Path(args[0]);samples=int(args[1]);acabado=args[2]
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import artesania
    (out/'frames').mkdir(exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s=bpy.context.scene;s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=samples
    s.render.resolution_x=1080;s.render.resolution_y=1920;s.render.resolution_percentage=100
    s.render.fps=25;s.render.image_settings.file_format='PNG'
    s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
    s.world=bpy.data.worlds.new('ambiente');s.world.use_nodes=True
    mats=[material(i) for i in range(7)]
    camdata=bpy.data.cameras.new('camara');cam=bpy.data.objects.new('camara',camdata)
    bpy.context.collection.objects.link(cam);s.camera=cam;camdata.clip_end=250
    frames=sorted((out/'intercambio').iterdir());medidas=[]
    programa=None;contexto=dict(escena=s,camara=cam,salida=out,artesania=artesania)
    fuente=Path(__file__).resolve().parent/'programa_bpy.py'
    if fuente.is_file():
        spec=importlib.util.spec_from_file_location('programa_bpy_del_plano',fuente)
        programa=importlib.util.module_from_spec(spec);spec.loader.exec_module(programa)
        programa.preparar(contexto)
    extra=None;olla=None;contactos=[]
    if acabado=='dirigido':
        first=json.loads((frames[0]/'escena.json').read_text(encoding='utf8'))
        if first.get('plano')=='cocina':
            olla=artesania.Olla(piel=first['sprites'][0].get('piel','#FFF0DB'))
            if first.get('composicion')=='cocina_reencuadrada':
                artesania.armario_cocina(x=1.0,ancho=3.8)
                artesania.encimera_y_cuenco()
            else:artesania.armario_cocina()
        else:
            artesania.pared(-1,seed=3);artesania.pared(1,seed=9)
            extra=artesania.Locomotora()
    for i,folder in enumerate(frames):
        data=json.loads((folder/'escena.json').read_text(encoding='utf8'))
        if data.get('volumen') is not None and programa is None:
            raise NotImplementedError('El volumen OpenGL necesita una implementación bpy explícita; no se omite silenciosamente')
        objs=[malla(np.load(folder/'malla.npy',allow_pickle=False),mats)]
        objs.extend(sprite(item,folder) for item in data['sprites'])
        if extra:extra.actualizar(data['t'])
        if olla:
            hero=data.get('composicion')=='cocina_reencuadrada'
            destino=(1.65,1.65,-5) if hero else (1.8,1.66,-5)
            contactos.append(dict(t=data['t'],**olla.actualizar(data['sprites'][0]['mano_d'],data['t'],destino,
                altura_mesa=1.44 if hero else 1.43)))
        c=data['camara'];a=data['ambiente']
        cam.location=punto(c['eye']);cam.rotation_euler=(Vector(punto(c['target']))-cam.location).to_track_quat('-Z','Y').to_euler()
        # v5 FOV vertical; Blender sensor_fit VERTICAL evita cambiar encuadre.
        camdata.sensor_fit='VERTICAL';camdata.sensor_height=32
        camdata.lens=16/math.tan(math.radians(c['fov']/2));camdata.dof.use_dof=False
        bg=s.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(*a.get('cielo',(.12,.4,.78)),1)
        bg.inputs['Strength'].default_value=.45
        if extra:bg.inputs['Strength'].default_value=.8
        sun=a.get('sol',(-.6,1,.5));target=c['target']
        pos=np.array(target)+np.array(sun)*30
        objs.append(luz('sol','SUN',pos,.25 if olla else 2.3,(1,.76,.52),target=target))
        if a.get('potencia',0)>0:
            objs.append(luz('lampara','AREA',a.get('lampara',(0,5,0)),350,(1,.55,.24),size=3,target=target))
        if acabado=='dirigido':
            if olla:
                objs.append(luz('clave','AREA',(3.5,4,-6),650,(1,.78,.53),size=2.5,target=(0,1.6,-6)))
                objs.append(luz('relleno_frio','AREA',(-3,3,-7),100,(.32,.5,1),size=3,target=(0,1,-6)))
                objs.append(luz('ventana','AREA',(0,3.6,-11.3),400,(.34,.53,1),size=1.3,target=(0,1,-5)))
            elif extra:
                zz=-14+data['t']*1.7
                objs.append(luz('cielo_clave','AREA',(2.5,6,zz-4),1700,(1,.80,.57),size=5,target=(0,1,zz)))
                objs.append(luz('cielo_rebote','AREA',(-3,4,zz+3),650,(.42,.57,1),size=5,target=(0,1,zz)))
                if data['sprites']:
                    objs.append(luz('clave_actor','AREA',(1,5,2),550,(1,.82,.64),size=4,target=(2.3,1,-1.5)))
        if programa:
            contexto['intercambio']=data
            programa.actualizar(contexto,data['t'])
        s.render.filepath=str(out/'frames'/f'{i:04}.png')
        start=time.perf_counter();bpy.ops.render.render(write_still=True)
        medidas.append(dict(frame=i,t=data['t'],segundos=time.perf_counter()-start))
        for obj in objs:
            dat=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
            if isinstance(dat,bpy.types.Mesh):bpy.data.meshes.remove(dat)
            elif isinstance(dat,bpy.types.Light):bpy.data.lights.remove(dat)
        for image in list(bpy.data.images):
            if image.name not in ('Render Result','Viewer Node'):bpy.data.images.remove(image)
        for mat in list(bpy.data.materials):
            if mat.name.startswith('rig_alfa'):bpy.data.materials.remove(mat)
        result=dict(version=bpy.app.version_string,backend=s.render.engine,
            gpu=dict(vendor=gpu.platform.vendor_get(),renderer=gpu.platform.renderer_get(),
                driver=gpu.platform.version_get(),backend=gpu.platform.backend_type_get()),
            samples=samples,ancho=1080,alto=1920,fps=25,frames=medidas,
            profundidad_campo=False,acabado=acabado,
            memoria_proceso=memoria_proceso(),contactos=contactos,
            limites=['Piloto no integrado en publicación','Sin garantía de colisiones generales ni coreografía equivalente'])
        (out/'medidas.json').write_text(json.dumps(result,indent=2),encoding='utf8')


if __name__=='__main__':main()
