"""Diagnóstico real de alfa, sombra y profundidad; no prueba de fidelidad artística."""
import bpy
import sys
import json
from pathlib import Path
from mathutils import Vector


def main():
    args=sys.argv[sys.argv.index('--')+1:];image=Path(args[0]);out=Path(args[1]);out.mkdir(exist_ok=False)
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from renderizar import sprite,luz,punto
    from artesania import mate,caja
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s=bpy.context.scene;s.render.engine='BLENDER_EEVEE_NEXT';s.eevee.taa_render_samples=64
    s.render.resolution_x=540;s.render.resolution_y=960;s.render.resolution_percentage=100
    s.world=bpy.data.worlds.new('ambiente');s.world.color=(.05,.08,.15)
    cream=mate('soporte',(.7,.7,.7),rug=.8);red=mate('oclusor',(.55,.12,.08),rug=.5)
    caja('suelo',(0,-.08,0),(6,.15,6),cream)
    caja('pared',(0,1.5,-1.2),(6,3,.1),cream)
    rig=sprite(dict(imagen=image.name,vertices=[(-.8,0,0),(.8,0,0),(.8,2.24,0),(-.8,2.24,0)]),image.parent)
    occ=caja('oclusor',(.5,.78,.8),(.6,1.55,.28),red)
    luz('clave','AREA',(-3,4,4),1000,(1,.85,.7),size=.6,target=(0,1,0))
    bpy.ops.object.camera_add(location=punto((2,2.2,6)));cam=bpy.context.object
    cam.rotation_euler=(Vector(punto((0,1,0)))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=48;s.camera=cam
    for name,actor,oclusor in [('completo',True,True),('sin_oclusor',True,False),('sin_actor',False,False)]:
        rig.hide_render=not actor;occ.hide_render=not oclusor
        s.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
    # Pase Z real con los mismos materiales: la tarjeta transparente no debe
    # convertirse en un rectángulo opaco. Se conserva el pase para inspección.
    rig.hide_render=False;occ.hide_render=True;s.view_layers[0].use_pass_z=True
    s.use_nodes=True;n=s.node_tree.nodes;n.clear();l=s.node_tree.links
    layers=n.new('CompositorNodeRLayers');mapping=n.new('CompositorNodeMapRange')
    mapping.inputs['From Min'].default_value=4;mapping.inputs['From Max'].default_value=9
    mapping.inputs['To Min'].default_value=1;mapping.inputs['To Max'].default_value=0
    l.new(layers.outputs['Depth'],mapping.inputs[0]);comp=n.new('CompositorNodeComposite');l.new(mapping.outputs[0],comp.inputs[0])
    s.render.filepath=str(out/'profundidad.png');bpy.ops.render.render(write_still=True)
    (out/'contrato.json').write_text(json.dumps(dict(render_real=True,material='DITHERED + alpha > .3',
        visible='Principled + emisión .35, no composición posterior',sombra='misma malla/material en Eevee',
        profundidad='pase Z de Eevee, no máscara inventada',ancho=540,alto=960),indent=2),encoding='utf8')


if __name__=='__main__':main()
