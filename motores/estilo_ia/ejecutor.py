"""Contrato del motor de un estilo. Se copia y sella dentro de cada paquete.

Proceso independiente, Python -I -S, dependencias locales. No es una VM ni una
frontera de seguridad: el código de dibujo pertenece al espacio de trabajo.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


def configurar_fuente_texto(pedido):
    """Sustituye SOLO la fuente limitada por defecto, dentro de este renderer.

    Medición y dibujo obtienen el mismo FreeTypeFont. No se recodifica texto ni
    se sustituyen fuentes explícitas elegidas por el estilo.
    """
    if not pedido.get('fuente_texto'):
        return
    from PIL import ImageFont
    ruta = Path(pedido['fuente_texto']).resolve()
    if not ruta.is_relative_to(Path(pedido['salida']).resolve()) or not ruta.is_file():
        raise ValueError('falta la fuente Unicode preparada para este render')
    def cargar(size=None):
        return ImageFont.truetype(str(ruta),size=10 if size is None else size)
    # Antes de importar motor/recursos: también cubre alias from ... import y
    # fuentes creadas al cargar el módulo o en cachés de geometría.
    ImageFont.load_default = cargar


def main():
    paquete, pedido_path = map(Path, sys.argv[1:3])
    sys.path[:0] = [str(paquete / 'dependencias'), str(paquete / 'herramientas'), str(paquete / 'motores')]
    pedido = json.loads(pedido_path.read_text(encoding='utf-8'))
    salida = Path(pedido['salida'])
    salida.mkdir(parents=True, exist_ok=True)
    ancho, alto, fps = pedido['ancho'], pedido['alto'], pedido['fps']
    orden = [pedido['ffmpeg'], '-nostdin', '-v', 'error', '-y', '-f', 'rawvideo',
             '-pix_fmt', 'rgb24', '-s', f'{ancho}x{alto}', '-r', str(fps), '-i', '-',
             '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p',
             '-movflags', '+faststart', str(salida / 'clip.mp4')]
    raices = [salida.resolve(), (paquete / 'cache').resolve(), (paquete / 'trabajo').resolve()]
    codigo_nativo = pedido.get('codigo_escena')
    if codigo_nativo:
        codigo_nativo = Path(codigo_nativo).resolve()
        if not codigo_nativo.is_relative_to(salida.resolve()) or pedido.get('imagen'):
            raise ValueError('la escena nativa necesita código propio dentro de su salida, sin imagen de fondo')
        sys.path.insert(0, str(codigo_nativo.parent / 'herramientas'))
    def escritura(ruta):
        if isinstance(ruta, int):
            return  # descriptores abiertos por el ejecutor (stdout/ffmpeg)
        if os.path.normcase(os.fsdecode(ruta)) == os.path.normcase(os.devnull):
            return  # dispositivo nulo usado por subprocess, no un fichero ajeno
        final = Path(os.fsdecode(ruta)).resolve()
        if not any(final.is_relative_to(raiz) for raiz in raices):
            raise PermissionError('el motor solo puede escribir en el trabajo y caché de su estilo')
    def auditar(evento, args):
        # Guardas contra errores de un motor: no sustituyen una frontera de
        # seguridad frente a extensiones nativas o código deliberadamente hostil.
        if evento == 'open' and args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            escritura(args[0])
        elif evento == 'open' and codigo_nativo and not isinstance(args[0], int):
            ruta = Path(os.fsdecode(args[0])).resolve()
            if ruta.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.bmp') and not ruta.is_relative_to((paquete / 'recursos').resolve()) and not ruta.is_relative_to(salida.resolve()):
                raise PermissionError('una escena nativa no puede utilizar ilustraciones ni fotogramas de referencia como fondo')
        elif evento in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.utime'):
            escritura(args[0])
        elif evento in ('os.rename', 'os.link', 'os.symlink'):
            escritura(args[0]); escritura(args[1])
        elif evento in ('os.chdir', 'os.system', 'os.exec', 'os.posix_spawn'):
            raise PermissionError('el motor no puede cambiar de espacio de trabajo ni ejecutar órdenes propias')
        elif evento == 'subprocess.Popen':
            comando = args[1]
            coincide = comando == subprocess.list2cmdline(orden) if isinstance(comando, str) else list(comando) == orden
            if not coincide:
                raise PermissionError('los procesos externos los coordina el ejecutor del estilo')
        elif evento.startswith('socket.'):
            raise PermissionError('los recursos se preparan antes del render, no mediante llamadas de red del motor')
    sys.addaudithook(auditar)
    configurar_fuente_texto(pedido)
    modulo = importlib.util.spec_from_file_location('motor_del_estilo', codigo_nativo or paquete / 'motores' / 'escena.py')
    motor = importlib.util.module_from_spec(modulo)
    modulo.loader.exec_module(motor)
    pedido['recursos'] = str(paquete / 'recursos')
    if hasattr(motor, 'preparar'):
        motor.preparar(pedido)
    total = max(1, round(pedido['duracion'] * fps))
    with (salida / 'ffmpeg.log').open('wb') as registro:
        proceso = subprocess.Popen(orden, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                   stderr=registro)
        try:
            for i in range(total):
                frame = motor.pintar(pedido, i / fps).convert('RGB')
                if frame.size != (ancho, alto):
                    raise ValueError('el motor debe devolver fotogramas del tamaño solicitado')
                if i == 0:
                    frame.save(salida / 'poster.png')
                proceso.stdin.write(frame.tobytes())
                if i % max(1, fps) == 0:
                    print(json.dumps(dict(fotograma=i, total=total)), flush=True)
            proceso.stdin.close()
            if proceso.wait(timeout=90):
                raise ValueError('ffmpeg no pudo codificar la animación del estilo')
        finally:
            if proceso.poll() is None:
                proceso.kill()
            proceso.wait()
    audio = salida / 'sonido.wav'
    if hasattr(motor, 'crear_audio'):
        motor.crear_audio(pedido, str(audio))
    (salida / 'resultado.json').write_text(json.dumps(dict(audio=audio.is_file())), encoding='utf-8')


if __name__ == '__main__':
    main()
