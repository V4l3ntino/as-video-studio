"""Montaje vertical de imágenes y voz existentes. Contrato de ficheros, sin IA."""
import json
import math
import os
import shutil
import subprocess
import textwrap
import time
import wave

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ANCHO, ALTO, FPS = 1080, 1920, 30
SIN_VENTANA = {"creationflags": 0x08000000} if os.name == "nt" else {}


def _correr(orden, carpeta, avisar, progreso):
    """El log va a disco: no bloquea una tubería y permite cancelar ffmpeg."""
    log = os.path.join(carpeta, "ffmpeg.log")
    with open(log, "w", encoding="utf-8") as salida:
        proceso = subprocess.Popen(orden, cwd=carpeta, stdout=salida,
                                   stderr=subprocess.STDOUT, **SIN_VENTANA)
        limite = time.monotonic() + 1800
        try:
            while proceso.poll() is None:
                avisar(progreso, "montando el Short vertical")
                if time.monotonic() > limite:
                    raise RuntimeError("el montaje del Short ha superado el tiempo de espera")
                time.sleep(0.25)
            if proceso.returncode:
                with open(log, encoding="utf-8") as fh:
                    detalle = fh.read()[-2500:]
                raise RuntimeError("ffmpeg no pudo montar el Short: " + detalle)
        finally:
            if proceso.poll() is None:
                proceso.kill()
                proceso.wait()


def _fondo(ruta, destino):
    with Image.open(ruta) as original:
        imagen = original.convert("RGB")
        fondo = ImageOps.fit(imagen, (ANCHO, ALTO)).filter(ImageFilter.GaussianBlur(35))
        fondo = ImageEnhance.Brightness(fondo).enhance(0.45)
        # Contener la ilustración evita cortar al protagonista o los textos de
        # una cartela horizontal. El fondo llena el 9:16 sin barras negras.
        frente = ImageOps.contain(imagen, (ANCHO, int(ALTO * 0.73)), Image.Resampling.LANCZOS)
        fondo.paste(frente, ((ANCHO - frente.width) // 2,
                            (ALTO - frente.height) // 2 - int(ALTO * 0.052)))
        fondo.save(destino, "JPEG", quality=93)


def _reloj(segundos):
    cs = round(max(0, segundos) * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02}:{cs // 100 % 60:02}.{cs % 100:02}"


def _subtitulos(escenas, destino):
    cabecera = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,60,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,4,1,2,95,145,360,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lineas = [cabecera]
    for escena in escenas:
        for sub in escena["subtitulos"]:
            texto = str(sub["texto"]).replace("\\", "").replace("{", "").replace("}", "")
            texto = "\\N".join(textwrap.wrap(" ".join(texto.split()), width=25,
                                            break_long_words=False, break_on_hyphens=False))
            lineas.append(f"Dialogue: 0,{_reloj(escena['t_in'] + sub['desde'])},"
                          f"{_reloj(escena['t_in'] + sub['hasta'])},Default,,0,0,0,,{texto}\n")
    with open(destino, "w", encoding="utf-8") as fh:
        fh.write("".join(lineas))


def montar(contrato, carpeta, avisar):
    """{escenas, audio_origen, video_origen, minimo, maximo} -> MP4 y duración."""
    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError("el montaje de Shorts necesita ffmpeg y ffprobe")
    escenas = contrato["escenas"]
    os.makedirs(carpeta, exist_ok=True)
    duracion = sum(e["duracion"] for e in escenas)
    # WAV PCM común: se reutiliza la voz del centro y solo se sustituyen los
    # extremos. La mezcla no hereda música ni subtítulos horizontales cocidos.
    audios = []
    videos = []
    for i, escena in enumerate(escenas):
        avisar(0.02 + 0.75 * i / len(escenas), "preparando las imágenes reutilizadas")
        imagen = escena.get("imagen")
        if not imagen or not os.path.isfile(imagen):
            imagen = os.path.join(carpeta, f"fuente-{i}.jpg")
            _correr([ffmpeg, "-y", "-v", "error", "-ss", str(escena["origen_frame"]),
                     "-i", contrato["video_origen"], "-frames:v", "1", imagen],
                    carpeta, avisar, 0.02 + 0.75 * i / len(escenas))
        fondo = f"fondo-{i}.jpg"
        _fondo(imagen, os.path.join(carpeta, fondo))
        frames = max(1, round(escena["t_out"] * FPS) - round(escena["t_in"] * FPS))
        clip = f"clip-{i}.mp4"
        _correr([ffmpeg, "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS),
                 "-i", fondo, "-frames:v", str(frames), "-an", "-c:v", "libx264",
                 "-preset", "veryfast", "-tune", "stillimage", "-crf", "22",
                 "-pix_fmt", "yuv420p", "-threads", "2", clip], carpeta, avisar,
                 0.02 + 0.75 * i / len(escenas))
        videos.append(clip)
        audio = f"audio-{i}.wav"
        orden = [ffmpeg, "-y", "-v", "error"]
        if escena.get("audio"):
            orden += ["-i", escena["audio"], "-af", f"atempo={escena['tempo']:.8f},apad"]
        else:
            orden += ["-ss", str(escena["origen_t"]), "-i", contrato["audio_origen"]]
        orden += ["-t", str(escena["duracion"]), "-ac", "1", "-ar", "44100",
                  "-c:a", "pcm_s16le", audio]
        _correr(orden, carpeta, avisar, 0.03 + 0.75 * i / len(escenas))
        audios.append(audio)
    narracion = os.path.join(carpeta, "narracion.wav")
    with wave.open(narracion, "wb") as salida:
        salida.setnchannels(1)
        salida.setsampwidth(2)
        salida.setframerate(44100)
        for audio in audios:
            with wave.open(os.path.join(carpeta, audio), "rb") as entrada:
                salida.writeframes(entrada.readframes(entrada.getnframes()))
    with open(os.path.join(carpeta, "clips.txt"), "w", encoding="utf-8") as fh:
        fh.write("".join(f"file '{nombre}'\n" for nombre in videos))
    _subtitulos(escenas, os.path.join(carpeta, "subtitulos.ass"))
    _correr([ffmpeg, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "clips.txt",
             "-i", "narracion.wav", "-vf", "ass=subtitulos.ass", "-t", str(duracion),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-threads", "2",
             "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "short.tmp.mp4"],
            carpeta, avisar, 0.85)
    meta = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                           "-of", "json", "short.tmp.mp4"], cwd=carpeta,
                          capture_output=True, text=True, timeout=30, **SIN_VENTANA)
    real = float(json.loads(meta.stdout)["format"]["duration"])
    if not math.isfinite(real) or not contrato["minimo"] <= real <= contrato["maximo"]:
        raise RuntimeError(f"el Short resultó de {real:.2f}s, fuera del rango solicitado")
    destino = os.path.join(carpeta, "short.mp4")
    os.replace(os.path.join(carpeta, "short.tmp.mp4"), destino)
    avisar(1.0, "Short vertical listo")
    return {"mp4": destino, "duracion": real, "resolucion": [ANCHO, ALTO]}
