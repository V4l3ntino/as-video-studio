"""Whisper local en un proceso independiente, con dependencias y modelos propios."""
import json
import os
from pathlib import Path
import sys


def guardar(ruta, dato):
    temporal = ruta.with_suffix('.tmp')
    temporal.write_text(json.dumps(dato, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    os.replace(temporal, ruta)


def main():
    base, entrada = map(Path, sys.argv[1:3])
    sys.path.insert(0, str(base / 'dependencias'))
    # Ni tokens del usuario ni un banco global de Hugging Face: todo vive en el
    # espacio de este estilo. CTranslate2 permite CPU/int8 sin instalar PyTorch.
    os.environ['HF_HOME'] = str(base / 'cache' / 'huggingface')
    os.environ['HF_HUB_CACHE'] = str(base / 'cache' / 'huggingface' / 'hub')
    os.environ['HF_HUB_DISABLE_XET'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
    os.environ['HF_HUB_DISABLE_IMPLICIT_TOKEN'] = '1'
    os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = '120'
    pedido = json.loads(entrada.read_text(encoding='utf-8'))
    progreso = Path(pedido['progreso'])
    guardar(progreso, dict(etapa='modelo', segundos=0))
    from faster_whisper import WhisperModel
    modelo = WhisperModel(pedido['modelo'], device='cpu', compute_type='int8',
        cpu_threads=min(4, max(1, os.cpu_count() or 1)), num_workers=1,
        download_root=str(base / 'modelos'))
    guardar(progreso, dict(etapa='transcribiendo', segundos=0))
    segmentos, info = modelo.transcribe(pedido['audio'], task='transcribe',
        beam_size=5, word_timestamps=True, vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        condition_on_previous_text=False)
    trozos = []
    for segmento in segmentos:
        texto = segmento.text.strip()
        if texto:
            trozos.append(dict(t_in=float(segmento.start), t_out=float(segmento.end), texto=texto,
                palabras=[dict(texto=p.word.strip(), t_in=float(p.start), t_out=float(p.end),
                               probabilidad=float(p.probability)) for p in (segmento.words or []) if p.word.strip()]))
        guardar(progreso, dict(etapa='transcribiendo', segundos=float(segmento.end)))
    guardar(Path(pedido['resultado']), dict(origen='whisper', motor='faster-whisper',
        modelo=pedido['modelo'], idioma=info.language if trozos else None,
        probabilidad_idioma=float(info.language_probability) if trozos else None,
        duracion_s=float(info.duration), texto=' '.join(t['texto'] for t in trozos), segmentos=trozos,
        estado='transcrito' if trozos else 'sin_habla'))
    guardar(progreso, dict(etapa='listo', segundos=float(info.duration)))


if __name__ == '__main__':
    main()
