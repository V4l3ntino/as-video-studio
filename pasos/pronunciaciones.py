"""Diccionario local de locución; nunca modifica el guion ni sus subtítulos.

Las sustituciones se hacen después de sanear SSML. Las marcas se devuelven al
texto original antes de repartir escenas. No requiere diccionarios remotos ni
cambiar la versión de la API de Cartesia.
"""
import difflib
import re

FONEMAS = set('p b t d k ɡ tʃ dʒ f v θ ð s z ʃ ʒ h m n ŋ l ɹ j w '
              'i ɪ ɛ æ ɑ ɔ ʊ u ə ɝ eɪ aɪ ɔɪ aʊ oʊ ˈ ˌ'.split())
_IPA = re.compile(r'<<([^<>]+)>>')
_PROTEGIDO = re.compile(r'(<spell\b[^>]*>.*?</spell>|<[^<>]*>)', re.I | re.S)


def normalizar(valor):
    """Texto editable «original = pronunciación», una entrada por línea."""
    if valor is None:
        return []
    if not isinstance(valor, str):
        raise ValueError('Pronunciaciones debe ser un texto, una entrada por línea.')
    if len(valor) > 20000:
        raise ValueError('Pronunciaciones supera los 20.000 caracteres.')
    entradas, vistas = [], set()
    for numero, linea in enumerate(valor.splitlines(), 1):
        if not linea.strip():
            continue
        original, separador, lectura = linea.partition('=')
        original, lectura = original.strip(), lectura.strip()
        if not separador or not original or not lectura:
            raise ValueError(f'Pronunciaciones, línea {numero}: usa Nombre = pronunciación.')
        if len(original) > 200 or len(lectura) > 1000:
            raise ValueError(f'Pronunciaciones, línea {numero}: entrada demasiado larga.')
        if any(c in original for c in '<>=') or '=' in lectura:
            raise ValueError(f'Pronunciaciones, línea {numero}: caracteres no permitidos.')
        resto = _IPA.sub('', lectura)
        if '<' in resto or '>' in resto:
            raise ValueError(f'Pronunciaciones, línea {numero}: fonemas con formato inválido.')
        for ipa in _IPA.findall(lectura):
            if any(f not in FONEMAS for f in ipa.split('|')):
                raise ValueError(f'Pronunciaciones, línea {numero}: fonema no admitido por Sonic 3.')
        clave = original.casefold()
        if clave in vistas:
            raise ValueError(f'Pronunciaciones: «{original}» aparece más de una vez.')
        vistas.add(clave)
        entradas.append((original, lectura))
    if len(entradas) > 200:
        raise ValueError('Pronunciaciones admite hasta 200 entradas.')
    return entradas


def aplicar(texto, diccionario):
    """Sustitución única, por palabras completas; gana el nombre más largo.

    Las etiquetas y los deletreos explícitos no se tocan. Las sustituciones no
    se encadenan, aunque una lectura coincida con otra entrada del diccionario.
    """
    entradas = normalizar(diccionario)
    if not entradas:
        return texto
    entradas.sort(key=lambda e: len(e[0]), reverse=True)
    patron = re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(e[0]) for e in entradas)
                        + r')(?!\w)', re.I)
    lecturas = {nombre.casefold(): lectura for nombre, lectura in entradas}
    piezas = _PROTEGIDO.split(texto)
    for i in range(0, len(piezas), 2):
        piezas[i] = patron.sub(lambda m: lecturas[m[0].casefold()], piezas[i])
    return ''.join(piezas)


def restaurar(original, palabras):
    """Recupera la ortografía original conservando los tiempos del audio.

    Las palabras que coinciden son anclas y conservan sus marcas exactas. Solo
    se reparte el intervalo de un tramo sustituido cuando su lectura tiene un
    número distinto de palabras. No se inventan marcas si el proveedor las omite.
    """
    tokens = original.split()
    normal = lambda s: re.sub(r'[^\w]', '', s.casefold())
    alineacion = difflib.SequenceMatcher(None, [normal(t) for t in tokens],
        [normal(p['w']) for p in palabras], autojunk=False)
    resultado = []
    for tipo, a, b, c, d in alineacion.get_opcodes():
        if tipo == 'equal' or b - a == d - c:
            resultado.extend(dict(p, w=t) for t, p in zip(tokens[a:b], palabras[c:d]))
        elif a != b:
            tramo = palabras[c:d]
            if not tramo:
                raise RuntimeError('Cartesia omitió marcas de una pronunciación; '
                                   'no se puede sincronizar el audio.')
            inicio, fin = tramo[0]['s'], tramo[-1]['e']
            pesos = [max(1, len(normal(t))) for t in tokens[a:b]]
            total, acumulado = sum(pesos), 0
            for token, peso in zip(tokens[a:b], pesos):
                resultado.append({'w': token,
                    's': round(inicio + (fin - inicio) * acumulado / total, 3),
                    'e': round(inicio + (fin - inicio) * (acumulado + peso) / total, 3)})
                acumulado += peso
    return resultado
