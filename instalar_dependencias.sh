#!/usr/bin/env bash
# Instala TODAS las dependencias Python del estudio en Linux/macOS:
#
#   .venv       el servicio (requirements.txt)
#   .depthflow  el motor opcional de parallax (requirements-depthflow.txt)
#
# Uso:
#
#   bash instalar_dependencias.sh
#
# Se puede volver a lanzar: no borra los entornos que ya existen y solo
# instala lo que falte o haya cambiado en los requirements.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
cd "$RAIZ"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "No encuentro '$PYTHON'. Instala Python 3.12 o superior y vuelve a intentarlo." >&2
  exit 1
fi

if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
  echo "El estudio necesita Python 3.12 o superior; '$PYTHON' es $("$PYTHON" --version 2>&1)." >&2
  exit 1
fi

entorno() {
  local ruta="$1" requisitos="$2"
  if [ ! -x "$ruta/bin/python" ]; then
    echo "Creando $ruta con $("$PYTHON" --version 2>&1)..."
    "$PYTHON" -m venv "$ruta"
  fi
  echo "Instalando las dependencias de $ruta..."
  "$ruta/bin/python" -m pip install --quiet --upgrade pip wheel
  "$ruta/bin/python" -m pip install --quiet -r "$requisitos"
}

entorno .venv requirements.txt
echo "Servicio instalado en .venv"

entorno .depthflow requirements-depthflow.txt
echo "DepthFlow instalado en .depthflow"

".venv/bin/python" -c "import fastapi, uvicorn, PIL, numpy, requests, websocket; print('Servicio verificado')"
".depthflow/bin/python" -c "from depthflow.scene import DepthScene; print('DepthFlow verificado')"

if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "AVISO: faltan ffmpeg y/o ffprobe. Instalalos con el gestor de paquetes del sistema." >&2
fi

echo
echo "Listo. Arranca el estudio con:"
echo "  .venv/bin/python app.py --puerto 8020"
echo
echo "Si mueves .depthflow, exporta ESTUDIO_DEPTHFLOW_PYTHON con su ruta."

# Motor adicional: la aplicación Python sigue siendo independiente de Node.
if command -v node >/dev/null 2>&1 && node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 22 ? 0 : 1)'; then
  npm ci --prefix "$RAIZ/motores/remotion" --no-audit --no-fund
  echo "Motor Remotion instalado"
else
  echo "Remotion opcional: instala Node >=22 y ejecuta npm ci --prefix motores/remotion"
fi
