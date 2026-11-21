"""Servidor bpy por stdin/stdout del ejecutor, sin ventana ni llamadas de red.

Intercambio de geometría libre; no un catálogo de planos. Devuelve RGB renderizado
y profundidad real. Escenografía nativa opcional: recursos parametrizables del
estilo, no imágenes de referencia ni un .blend compartido mutable.
"""
import bpy
import gpu
import numpy as np
import json
import math
import os
import random
import sys
import time
import traceback
from pathlib import Path
from mathutils import Vector

sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rc_blender_render import malla,sprite,luz,punto,material,memoria_proceso
import rc_blender_artesania as artesania


def informar(dato):print('ESTUDIO_BLENDER '+json.dumps(dato,ensure_ascii=True),flush=True)


def eliminar(objects):
    for ob in list(objects):
        if ob.name not in bpy.data.objects:continue
        data=ob.data;bpy.data.objects.remove(ob,do_unlink=True)
        if data is not None and data.users==0:
            if isinstance(data,bpy.types.Mesh):bpy.data.meshes.remove(data)
            elif isinstance(data,bpy.types.Curve):bpy.data.curves.remove(data)
            elif isinstance(data,bpy.types.Light):bpy.data.lights.remove(data)


def explosion(datos):
    """Volumen y trayectorias procedurales; NO simulación física de fluidos."""
    t=max(0,float(datos['t']));amount=max(0,min(1,float(datos.get('cantidad',1))))
    if amount<=0:return
    center=datos.get('pos',(0,0,-6));rng=random.Random(74)
    mat=bpy.data.materials.new('humo_fuego');mat.use_nodes=True
    n=mat.node_tree.nodes;l=mat.node_tree.links;n.clear()
    out=n.new('ShaderNodeOutputMaterial');vol=n.new('ShaderNodeVolumePrincipled')
    noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=3.1;noise.inputs['Detail'].default_value=3
    density=n.new('ShaderNodeMath');density.operation='MULTIPLY';density.inputs[1].default_value=amount*1.8
    l.new(noise.outputs['Fac'],density.inputs[0]);l.new(density.outputs[0],vol.inputs['Density'])
    vol.inputs['Color'].default_value=(.12,.075,.10,1)
    fire=math.exp(-max(0,t-.4)*2.1)
    vol.inputs['Emission Color'].default_value=(1,.19,.015,1)
    power=n.new('ShaderNodeMath');power.operation='MULTIPLY';power.inputs[1].default_value=fire*8
    l.new(noise.outputs['Fac'],power.inputs[0]);l.new(power.outputs[0],vol.inputs['Emission Strength']);l.new(vol.outputs[0],out.inputs['Volume'])
    for i in range(9):
        angle=i*math.tau/9;r=(.65+min(t,3)*1.1)*(1+.13*math.sin(i*4))
        pos=(center[0]+math.cos(angle)*r*.65,center[1]+1.1+t*.8+(.6 if i%2 else 0),center[2]+math.sin(angle)*r*.65)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=punto(pos))
        ob=bpy.context.object;ob.name='volumen_explosion';ob.scale=(r,r*.85,r*(.8+.2*math.sin(i)))
        ob.data.materials.append(mat)
    for i in range(3):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=.65+i*.1,location=punto((center[0],center[1]+.6+i*.8,center[2])))
        bpy.context.object.data.materials.append(mat)
    luz('rebote_explosion','POINT',(center[0],center[1]+2,center[2]),12000*fire*amount,(1,.28,.055))
    if datos.get('escombros',True):
        metal=artesania.mate('fragmentos_explosion',(.20,.14,.10),.45,.5)
        for i in range(28):
            az=rng.uniform(0,math.tau);speed=rng.uniform(1,5);up=rng.uniform(2,7)
            y=center[1]+1+up*t-4*t*t
            if y<0:continue
            size=rng.uniform(.04,.14)
            ob=artesania.caja('fragmento',(center[0]+math.cos(az)*speed*t,y,center[2]+math.sin(az)*speed*t),(size,size*1.4,size*.7),metal,.006)
            ob.rotation_euler=(t*speed,t*(i%3+1),t*2)


class Motor:
    def __init__(self,config):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene=bpy.context.scene;s=self.scene
        s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=config['samples']
        s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.render.fps=config['fps']
        s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast'
        s.world=bpy.data.worlds.new('ambiente');s.world.use_nodes=True
        self.mats=[material(i) for i in range(7)]
        cd=bpy.data.cameras.new('camara');self.cam=bpy.data.objects.new('camara',cd);bpy.context.collection.objects.link(self.cam);s.camera=self.cam
        cd.sensor_fit='VERTICAL';cd.sensor_height=32;cd.clip_start=.1;cd.clip_end=180
        s.view_layers[0].use_pass_z=True;s.use_nodes=True
        nodes=s.node_tree.nodes;nodes.clear();links=s.node_tree.links
        layers=nodes.new('CompositorNodeRLayers');comp=nodes.new('CompositorNodeComposite')
        # Atmósfera por distancia axial real, equivalente al efecto de profundidad
        # anterior. NO volumen infinito de mundo: absorbería toda la luz del cielo.
        self.niebla=nodes.new('CompositorNodeMath');self.niebla.operation='MULTIPLY'
        links.new(layers.outputs['Depth'],self.niebla.inputs[0])
        exponencial=nodes.new('CompositorNodeMath');exponencial.operation='EXPONENT'
        links.new(self.niebla.outputs[0],exponencial.inputs[0])
        inversa=nodes.new('CompositorNodeMath');inversa.operation='SUBTRACT';inversa.inputs[0].default_value=1
        links.new(exponencial.outputs[0],inversa.inputs[1])
        self.atmosfera=nodes.new('CompositorNodeMixRGB');self.atmosfera.blend_type='MIX'
        links.new(inversa.outputs[0],self.atmosfera.inputs[0]);links.new(layers.outputs['Image'],self.atmosfera.inputs[1])
        links.new(self.atmosfera.outputs[0],comp.inputs[0])
        self.depth=nodes.new('CompositorNodeOutputFile');self.depth.format.file_format='OPEN_EXR';self.depth.format.color_depth='32';self.depth.format.color_mode='RGB'
        self.depth.file_slots[0].path='depth_';links.new(layers.outputs['Depth'],self.depth.inputs[0])
        self.static=[];self.static_mats=set();self.extra_key=None;self.tren=None;self.olla=None;self.ollas=[]

    def extras(self,options,data):
        key=json.dumps({**{k:options.get(k) for k in ('paredes','tren','cocina','cuenco','piel')},
            'pieles':[o['piel'] for o in options.get('ollas',[])]},sort_keys=True)
        if key!=self.extra_key:
            eliminar([o.chorro for o in self.ollas if o.chorro is not None])
            eliminar(self.static);self.static=[];self.tren=None;self.olla=None;self.ollas=[];self.extra_key=key
            before=set(bpy.data.objects)
            materials=set(bpy.data.materials)
            if options.get('paredes'):
                cfg=options['paredes'] if isinstance(options['paredes'],dict) else {}
                artesania.pared(-1,seed=3,**cfg);artesania.pared(1,seed=9,**cfg)
            if options.get('tren'):self.tren=artesania.Locomotora()
            if options.get('cocina'):
                for item in options.get('ollas',[]):self.ollas.append(artesania.Olla(piel=item['piel']))
                self.olla=bool(self.ollas)
                artesania.armario_cocina(x=1,ancho=3.8);artesania.encimera_y_cuenco()
            self.static=list(set(bpy.data.objects)-before)
            self.static_mats=set(bpy.data.materials)-materials
        t=float(options.get('t',0))
        if self.tren:self.tren.actualizar(t)
        contacto=None
        if self.ollas:
            contacto=[olla.actualizar(item['mano'],t,destino=options.get('destino',(1.65,1.65,-5)),altura_mesa=1.44)
                for olla,item in zip(self.ollas,options['ollas'])]
        return contacto

    def render(self,folder,data):
        s=self.scene;w,h=data['ancho'],data['alto'];s.render.resolution_x=w;s.render.resolution_y=h
        if not(16<=w<=4096 and 16<=h<=4096):raise ValueError('resolución Blender no válida')
        options=data['ambiente'].get('blender',{});contacto=self.extras(options,data)
        before=set(bpy.data.objects)
        array=np.load(folder/'malla.npy',allow_pickle=False)
        if array.ndim!=2 or array.shape[1]!=10 or len(array)%3 or len(array)>3000000:raise ValueError('malla Blender no válida')
        if len(array):malla(array,self.mats)
        for item in data['sprites']:
            file=(folder/item['imagen']).resolve()
            if not file.is_relative_to(folder.resolve()) or file.suffix!='.png':raise ValueError('imagen fuera del intercambio')
            sprite(item,folder)
        c=data['camara'];a=data['ambiente'];cam=self.cam;cd=cam.data
        cam.location=punto(c['eye']);cam.rotation_euler=(Vector(punto(c['target']))-cam.location).to_track_quat('-Z','Y').to_euler()
        cd.lens=16/math.tan(math.radians(c.get('fov',48))/2)
        cd.dof.use_dof=bool(c.get('apertura',0));cd.dof.focus_distance=(Vector(punto(c['target']))-cam.location).length
        cd.dof.aperture_fstop=float(c.get('fstop',8/max(.1,c.get('apertura',.1))))
        bg=s.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(*a.get('cielo',(.12,.4,.78)),1);bg.inputs['Strength'].default_value=.8 if self.tren else .45
        self.niebla.inputs[1].default_value=-max(0,min(.05,float(a.get('niebla',0))))
        self.atmosfera.inputs[2].default_value=(*a.get('cielo',(.12,.4,.78)),1)
        sun=np.asarray(a.get('sol',(-.6,1,.5)));target=np.asarray(c['target'])
        luz('sol','SUN',target+sun*30,.25 if options.get('cocina') else 2.3,(1,.76,.52),target=target)
        if a.get('potencia',0):luz('lampara','AREA',a.get('lampara',(0,5,0)),350,(1,.55,.24),target=target)
        if options.get('cocina'):
            luz('clave','AREA',(3.5,4,-6),650,(1,.78,.53),size=2.5,target=(0,1.6,-6))
            luz('relleno','AREA',(-3,3,-7),100,(.32,.5,1),target=(0,1,-6))
            luz('ventana','AREA',(0,3.6,-11.3),400,(.34,.53,1),size=1.3,target=(0,1,-5))
        if self.tren:
            zz=-14+float(options.get('t',0))*1.7
            luz('clave_tren','AREA',(2.5,6,zz-4),1700,(1,.8,.57),size=5,target=(0,1,zz))
            luz('relleno_tren','AREA',(-3,4,zz+3),650,(.42,.57,1),size=5,target=(0,1,zz))
        if data.get('volumen'):explosion(data['volumen'])
        s.render.filepath=str(folder/'frame.png');self.depth.base_path=str(folder);s.frame_set(1)
        start=time.perf_counter();bpy.ops.render.render(write_still=True);seconds=time.perf_counter()-start
        depthfile=folder/'depth_0001.exr'
        im=bpy.data.images.load(str(depthfile),check_existing=False)
        z=np.asarray(im.pixels[:],dtype='f4').reshape(h,w,4)[::-1,:,0]
        # El pase Z real de Eevee se conserva además del z-buffer normalizado.
        np.save(folder/'depth_lineal.npy',z,allow_pickle=False)
        depth=np.where(z>1e9,1,np.clip(180/179.9-18/(179.9*np.maximum(z,.1)),0,1)).astype('f4')
        np.save(folder/'depth.npy',depth,allow_pickle=False)
        eliminar(set(bpy.data.objects)-before)
        for image in list(bpy.data.images):
            if image.name not in ('Render Result','Viewer Node'):bpy.data.images.remove(image)
        for mat in list(bpy.data.materials):
            if mat.users==0 and mat not in self.mats and mat not in self.static_mats:bpy.data.materials.remove(mat)
        return dict(segundos_render=seconds,contacto=contacto,memoria=memoria_proceso(),
            gpu=dict(vendor=gpu.platform.vendor_get(),renderer=gpu.platform.renderer_get(),driver=gpu.platform.version_get(),backend=gpu.platform.backend_type_get()))


def main():
    folder=Path(sys.argv[sys.argv.index('--')+1]).resolve()
    # El Python embebido/bpy no hereda el soporte de rutas largas del Python del
    # Estudio. P6 añade proyecto + SHA + nombre de escena: supera MAX_PATH aunque
    # la raíz del proyecto sea corta. No truncar IDs ni sacar archivos del trabajo.
    if os.name=='nt' and not str(folder).startswith('\\\\?\\'):
        ruta=str(folder)
        folder=Path('\\\\?\\UNC\\'+ruta[2:] if ruta.startswith('\\\\') else '\\\\?\\'+ruta)
    config=json.loads((folder/'config.json').read_text(encoding='utf8'))
    if bpy.app.version_string!='4.5.16 LTS' or config['version']!='4.5.16' or config['protocolo']!=1:raise ValueError('runtime/protocolo Blender incompatible')
    motor=Motor(config)
    # En background el contexto GPU se crea al primer render, no al iniciar bpy.
    informar(dict(estado='listo',version='4.5.16',motor='BLENDER_EEVEE_NEXT',protocolo=1,
        gpu=dict(renderer='pendiente del primer render')))
    for line in sys.stdin:
        try:
            command=json.loads(line)
            if command.get('terminar'):break
            target=(folder/command['render']).resolve()
            if not target.is_relative_to(folder/'intercambio'):raise ValueError('ruta de intercambio no válida')
            data=json.loads((target/'escena.json').read_text(encoding='utf8'))
            result=motor.render(target,data);informar(dict(render=command['render'],**result))
        except Exception as error:
            traceback.print_exc(file=sys.stderr);informar(dict(error=str(error)))


if __name__=='__main__':main()
