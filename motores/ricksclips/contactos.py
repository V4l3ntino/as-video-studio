"""Contactos rígidos en el plano articulado del actor (píxeles, Y abajo).

No es un constraint 3D entre objetos a distinta profundidad. Una vez resuelto
el IK, colocar un objeto por su agarre conserva el contacto incluso si el brazo
no alcanza el objetivo, cambia la apariencia o se reproyecta el billboard.
"""
import math


def transformar(punto,centro,angulo=0,escala=1):
    a=math.radians(angulo);c,s=math.cos(a),math.sin(a)
    x,y=punto
    return (centro[0]+escala*(c*x-s*y),centro[1]+escala*(s*x+c*y))


def centro_por_agarre(mano,agarre,angulo=0,escala=1):
    dx,dy=transformar(agarre,(0,0),angulo,escala)
    return (mano[0]-dx,mano[1]-dy)
