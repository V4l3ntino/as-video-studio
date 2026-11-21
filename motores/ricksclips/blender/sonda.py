"""Sonda ejecutada exclusivamente con blender --background --factory-startup."""
import bpy
import gpu
import json
import sys
import time
from pathlib import Path

out=Path(sys.argv[sys.argv.index('--')+1])
out.mkdir(parents=True,exist_ok=False)
bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene
s.render.engine='BLENDER_EEVEE_NEXT'
s.render.resolution_x=1080
s.render.resolution_y=1920
s.render.resolution_percentage=100
s.eevee.taa_render_samples=16
bpy.ops.mesh.primitive_uv_sphere_add(location=(0,0,0))
bpy.ops.object.camera_add(location=(3,-5,2))
cam=bpy.context.object
from mathutils import Vector
cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler()
s.camera=cam
bpy.ops.object.light_add(type='AREA',location=(2,-3,4))
bpy.context.object.data.energy=800
bpy.context.object.data.shape='DISK'
bpy.context.object.data.size=3
s.world=bpy.data.worlds.new('Cielo')
s.world.color=(.1,.16,.3)
s.render.filepath=str(out/'sonda.png')
start=time.perf_counter()
bpy.ops.render.render(write_still=True)
data=dict(version=bpy.app.version_string,engine=s.render.engine,
    vendor=gpu.platform.vendor_get(),renderer=gpu.platform.renderer_get(),
    driver=gpu.platform.version_get(),backend=gpu.platform.backend_type_get(),
    segundos=time.perf_counter()-start,ancho=1080,alto=1920,samples=16,
    nota='Render real Eevee; cycles.device no identifica el dispositivo Eevee.')
(out/'sonda.json').write_text(json.dumps(data,indent=2),encoding='utf8')
print(json.dumps(data),flush=True)
