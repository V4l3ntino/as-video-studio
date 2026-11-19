"""Utilería procedural opcional. Las escenas eligen materiales y pueden ampliarla.

Coordenadas normalizadas; x,y es el centro de la caja, w,h su tamaño.
No impone una paleta ni sustituye el dibujo específico que necesite un estilo.
"""
from PIL import ImageDraw


def dibujar(lienzo, estado, contexto):
    d = ImageDraw.Draw(lienzo)
    W, H = lienzo.size
    x, y = estado.get('x', .5)*W, estado.get('y', .5)*H
    w, h = estado.get('w', .25)*W, estado.get('h', .4)*H
    l, t, r, b = x-w/2, y-h/2, x+w/2, y+h/2
    tinta = estado.get('contorno', '#263044')
    grosor = max(1, round(estado.get('trazo', .003)*W))
    tipo = estado.get('tipo', 'casa')
    if tipo in ('casa', 'edificio'):
        fachada = estado.get('fachada', '#d7c4a6')
        tejado = estado.get('tejado', '#845744')
        cristal = estado.get('cristal', '#a9c9da')
        cima = t + (.24*h if tipo == 'casa' else .06*h)
        d.rectangle((l,cima,r,b), fill=fachada, outline=tinta, width=grosor)
        if tipo == 'casa':
            d.polygon([(l-.06*w,cima),(x,t),(r+.06*w,cima)], fill=tejado, outline=tinta)
            d.line([(l-.06*w,cima),(x,t),(r+.06*w,cima)], fill=tinta,width=grosor)
        else:
            d.rectangle((l-.03*w,t,r+.03*w,cima),fill=tejado,outline=tinta,width=grosor)
        filas = int(estado.get('filas', 1 if tipo == 'casa' else 4))
        columnas = int(estado.get('columnas', 2 if tipo == 'casa' else 3))
        filas, columnas = max(1,min(12,filas)), max(1,min(12,columnas))
        for iy in range(filas):
            for ix in range(columnas):
                cx = l+w*(ix+1)/(columnas+1)
                cy = cima+(b-cima)*(.14+.56*(iy+.5)/filas)
                a, z = .22*w/columnas, .2*(b-cima)/filas
                d.rectangle((cx-a,cy-z,cx+a,cy+z),fill=cristal,outline=tinta,width=grosor)
                d.line((cx,cy-z,cx,cy+z),fill=tinta,width=grosor)
        d.rectangle((x-.09*w,b-.21*h,x+.09*w,b),fill=estado.get('puerta','#735341'),outline=tinta,width=grosor)
    elif tipo == 'arbol':
        d.rectangle((x-.07*w,y,x+.07*w,b),fill=estado.get('tronco','#795438'),outline=tinta,width=grosor)
        follaje = estado.get('follaje','#52815b')
        for cx,cy,rx,ry in ((x,y-.1*h,.43*w,.3*h),(x-.22*w,y,.28*w,.23*h),(x+.22*w,y,.28*w,.23*h)):
            d.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),fill=follaje,outline=tinta,width=grosor)
    elif tipo == 'movil':
        radio = max(1,round(min(w,h)*.12))
        d.rounded_rectangle((l,t,r,b),radius=radio,fill=estado.get('carcasa','#30394b'),outline=tinta,width=grosor)
        d.rounded_rectangle((l+.07*w,t+.07*h,r-.07*w,b-.08*h),radius=max(1,radio//2),fill=estado.get('pantalla','#b9dce8'))
        d.line((x-.12*w,t+.035*h,x+.12*w,t+.035*h),fill=estado.get('detalle','#9ea8b8'),width=grosor)
        avance = max(0,min(1,estado.get('progreso',1)))
        for i in range(round(avance*3)):
            cy=t+(.24+i*.19)*h
            d.rounded_rectangle((l+.15*w,cy,r-.15*w,cy+.1*h),radius=max(1,radio//3),fill=estado.get('mensaje','#6e9eaa'))
    else:
        raise ValueError('Utilería base desconocida; crea un recurso nuevo, no un sustituto genérico')
    return {'centro': (x,y), 'base': (x,b)}
