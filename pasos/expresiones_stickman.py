"""Expresiones justificadas por la descripción actual, no por el perfil del actor."""


INSTRUCCIONES = '''
DIRECCIÓN FACIAL POR PERSONAJE: la descripcion_visual actual es la autoridad, por encima
de la narración abstracta, el perfil del reparto, el ambiente, los colores y los planes previos.
Si no describe una emoción o un gesto facial para ese personaje, usa expresion:"neutral":
cejas en reposo y boca neutra, sin imponer tampoco una sonrisa permanente.
Gesticular con los brazos NO implica enfado ni preocupación; teclear o concentrarse NO implica
determined, worried ni cejas fruncidas; caminar despacio NO implica smirk. Un halo naranja,
la luz azul o palabras como "frío", "caliente", "psicópata" o "sociópata" no definen una cara.
No repartas una emoción entre todos los actores: quien observa no hereda la cara de quien grita.
Anima brazos, pies, postura, mirada o utilería para desarrollar la acción; no inventes cambios
faciales para superar la validación de movimiento. neutral también permite hablar y parpadear.
Para CADA expresion distinta de neutral añade motivo_expresion:"cita literal de la descripción
actual que pide esa emoción o gesto facial PARA ESE ACTOR", tanto en el actor como en sus claves.
Las claves que repiten la misma expresión pueden conservar el motivo anterior. La cita debe
pedir realmente esa expresión, no solo mencionar al personaje, el color, el lugar o una acción
neutra. Por ejemplo: "el vecino frunce el ceño enfadado" justifica angry; "la compañera sigue
tecleando sin levantar la vista" exige neutral, no es motivo para determined ni worried.
Una sonrisa explícita justifica smile/happy según su intensidad, no nerviosismo. No cambies una
emoción por otra. No fabriques ni añadas palabras a la cita. Si no hay motivo, vuelve a neutral.
Al continuar una secuencia conserva posiciones/ropa/acción, pero reevalúa cada rostro contra
la descripción ACTUAL: las emociones son estados temporales, no rasgos permanentes del diseño.
En un retoque local conserva las expresiones no afectadas; si se pide corregirlas, sigue la petición.
Las entregas nuevas usan realizacion.expresiones_fieles:true. En retoques el motor aplica
cejas_fieles:true automáticamente: angry se dibuja con cejas de enfado, no de preocupación,
sin cambiar la boca de los personajes neutros ni requerir una marca del proveedor.
'''


def validar(contenido, descripcion):
    """Solo en entregas nuevas con descripción visual; la lectura histórica es intacta."""
    if not isinstance(descripcion, str) or not descripcion.strip():
        return
    fuente = ' '.join(descripcion.split()).casefold()
    for actor in contenido['personajes']:
        expresion, motivo = 'neutral', ''
        for indice, estado in enumerate([actor, *actor['claves']]):
            if 'expresion' not in estado:
                continue
            nueva = estado['expresion']
            cita = estado.get('motivo_expresion', motivo if nueva == expresion else '')
            if nueva != 'neutral' and (not cita.strip() or ' '.join(cita.split()).casefold() not in fuente):
                donde = 'base' if indice == 0 else f'clave {indice - 1}, t={estado["t"]}'
                raise ValueError(f'{actor["id"]}, {donde}: expresion={nueva} necesita motivo_expresion '
                    'con una cita literal de la descripción visual ACTUAL para ese personaje. '
                    'Si no se pide esa emoción o gesto facial, usa neutral; no lo deduzcas del perfil, '
                    'los colores, teclear o gesticular. No heredes expresiones sin motivo de otra escena.')
            expresion, motivo = nueva, cita
