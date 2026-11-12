# =============================================================================
#  AS Video Studio - instalador de dependencias para Windows.
#
#  Crea los mismos dos entornos que instalar_dependencias.sh en Linux/macOS:
#
#    .venv       el servicio (requirements.txt)
#    .depthflow  el motor opcional de parallax (requirements-depthflow.txt)
#    motores/remotion/node_modules  Remotion, si hay Node >=22 y npm
#
#  Uso:
#
#    powershell -NoProfile -ExecutionPolicy Bypass -File .\instalar_dependencias.ps1
#
#  Opciones:
#
#    -SinDepthflow       no instala el motor opcional (ahorra varios GB)
#    -Python RUTA        usa ese interprete en vez del que se encuentre
#
#  Se puede volver a lanzar: no borra los entornos que ya existen y solo
#  instala lo que falte o haya cambiado en los requirements.
# =============================================================================

[CmdletBinding()]
param(
  [string]$Python = "",
  [switch]$SinDepthflow
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$Raiz = $PSScriptRoot

function Escribir-Paso([string]$Texto) {
  Write-Host ""
  Write-Host "==> $Texto" -ForegroundColor Cyan
}

function Escribir-Bien([string]$Texto) {
  Write-Host "    OK  $Texto" -ForegroundColor Green
}

function Escribir-Nota([string]$Texto) {
  Write-Host "    -   $Texto" -ForegroundColor DarkGray
}

function Escribir-Aviso([string]$Texto) {
  Write-Host "    !   $Texto" -ForegroundColor Yellow
}

function Fallar([string]$Texto) {
  Write-Host ""
  Write-Host "ERROR: $Texto" -ForegroundColor Red
  exit 1
}

function Version-Python([string]$Exe) {
  $salida = & $Exe -c "import sys; print('%d.%d.%d' % sys.version_info[:3])" 2>$null
  if ($LASTEXITCODE -ne 0 -or -not $salida) { return $null }
  return ([string]($salida | Select-Object -First 1)).Trim()
}

function Resolver-Python([string]$Pedido) {
  if ($Pedido) {
    $ruta = Resolve-Path -LiteralPath $Pedido -ErrorAction SilentlyContinue
    if (-not $ruta) { Fallar "No encuentro el interprete indicado: $Pedido" }
    return $ruta.Path
  }

  # El lanzador `py` es la forma fiable de pedir 3.12 sin depender del PATH.
  $lanzador = Get-Command py -ErrorAction SilentlyContinue
  if ($lanzador) {
    $ruta = & $lanzador.Source -3.12 -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $ruta) {
      return ([string]($ruta | Select-Object -First 1)).Trim()
    }
  }

  $comando = Get-Command python -ErrorAction SilentlyContinue
  if ($comando) { return $comando.Source }
  return $null
}

function Comprobar-Python([string]$Exe, [string]$Etiqueta) {
  $version = Version-Python $Exe
  if (-not $version) {
    Fallar "$Etiqueta no responde. Comprueba que es un Python real y vuelve a lanzar."
  }
  & $Exe -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)" 2>$null
  if ($LASTEXITCODE -ne 0) {
    Fallar "El estudio necesita Python 3.12 o superior; $Etiqueta es $version. Instala Python 3.12 y vuelve a lanzar."
  }
  return $version
}

function Instalar-Entorno([string]$Nombre, [string]$RutaRelativa, [string]$Requisitos, [string]$BasePython) {
  $ruta = Join-Path $Raiz $RutaRelativa
  $python = Join-Path $ruta "Scripts\python.exe"

  if (-not (Test-Path -LiteralPath $python)) {
    $version = Version-Python $BasePython
    Escribir-Nota "Creando $RutaRelativa con Python $version..."
    & $BasePython -m venv $ruta
    if ($LASTEXITCODE -ne 0) {
      Fallar "No se ha podido crear $RutaRelativa. Si la carpeta existe a medias, borrala o renombrala y vuelve a lanzar."
    }
  }

  if (-not (Test-Path -LiteralPath $python)) {
    Fallar "La carpeta $RutaRelativa no contiene Scripts\python.exe. Borrala o renombrala y vuelve a lanzar."
  }

  $version = Comprobar-Python $python $Nombre
  Escribir-Nota "Instalando $Requisitos en $RutaRelativa (Python $version)..."
  & $python -m pip install --quiet --disable-pip-version-check --upgrade pip wheel
  if ($LASTEXITCODE -ne 0) {
    Fallar "No se ha podido actualizar pip/wheel en $RutaRelativa."
  }
  & $python -m pip install --quiet --disable-pip-version-check -r (Join-Path $Raiz $Requisitos)
  if ($LASTEXITCODE -ne 0) {
    Fallar "No se han podido instalar las dependencias de $Requisitos en $RutaRelativa."
  }
}

function Resolver-Herramienta([string]$Nombre, [string]$Variable) {
  $ruta = [Environment]::GetEnvironmentVariable($Variable)
  if ($ruta) {
    if (Test-Path -LiteralPath $ruta -PathType Leaf) { return $ruta }
    return $null
  }
  $comando = Get-Command $Nombre -ErrorAction SilentlyContinue
  if ($comando) { return $comando.Source }
  return $null
}

function Resolver-Navegador() {
  $candidatos = @()
  $puesto = [Environment]::GetEnvironmentVariable('ESTUDIO_EDGE')
  if ($puesto) { $candidatos += $puesto }

  if ($env:ProgramFiles) {
    $candidatos += (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe')
    $candidatos += (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe')
  }
  if (${env:ProgramFiles(x86)}) {
    $candidatos += (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe')
    $candidatos += (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe')
  }
  if ($env:LOCALAPPDATA) {
    $candidatos += (Join-Path $env:LOCALAPPDATA 'Microsoft\Edge\Application\msedge.exe')
    $candidatos += (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe')
  }

  foreach ($candidato in $candidatos) {
    if ($candidato -and (Test-Path -LiteralPath $candidato -PathType Leaf)) {
      return $candidato
    }
  }
  return $null
}

if (-not [Environment]::Is64BitOperatingSystem) {
  Fallar "Hace falta Windows de 64 bits: el navegador que dibuja los planos y DepthFlow no existen para 32 bits."
}

Escribir-Paso "Buscando Python 3.12 o superior"
$BasePython = Resolver-Python $Python
if (-not $BasePython) {
  Fallar "No encuentro Python. Instala Python 3.12 desde https://www.python.org/downloads/windows/ y marca 'Add python.exe to PATH'."
}
$VersionBase = Comprobar-Python $BasePython "el Python encontrado ($BasePython)"
Escribir-Bien "Python $VersionBase en $BasePython"

Escribir-Paso "El servicio (.venv)"
Instalar-Entorno "el servicio" ".venv" "requirements.txt" $BasePython
$PythonServicio = Join-Path $Raiz ".venv\Scripts\python.exe"
& $PythonServicio -c "import fastapi, uvicorn, PIL, numpy, requests, websocket; print('Servicio verificado')"
if ($LASTEXITCODE -ne 0) {
  Fallar "Las dependencias del servicio se han instalado, pero no se pueden importar. Revisa el error de arriba."
}
Escribir-Bien "Servicio verificado en .venv"

if ($SinDepthflow) {
  Escribir-Paso "DepthFlow (omitido con -SinDepthflow)"
  Escribir-Nota "El estudio arrancara igual; el parallax quedara desactivado."
} else {
  Escribir-Paso "El motor de parallax (.depthflow)"
  Escribir-Nota "Descarga torch y ocupa varios GB. Puede tardar bastante."
  Instalar-Entorno "DepthFlow" ".depthflow" "requirements-depthflow.txt" $BasePython
  $PythonDepthflow = Join-Path $Raiz ".depthflow\Scripts\python.exe"
  # ShaderFlow deja un observador no daemon: en Windows hay que cerrarlo o el
  # proceso se queda esperando para siempre despues de importar. El finally lo
  # cierra tambien cuando la importacion falla.
  $verificacion = @'
import sys

try:
    from depthflow.scene import DepthScene
    print("DepthFlow verificado")
finally:
    modulo = sys.modules.get("shaderflow.shader")
    observador = getattr(modulo, "WATCHDOG", None)
    if observador is not None:
        observador.stop()
        observador.join(timeout=5)
'@
  $verificacion | & $PythonDepthflow -X utf8 -
  if ($LASTEXITCODE -ne 0) {
    Fallar "DepthFlow se ha instalado, pero no se puede importar. Revisa el error de arriba."
  }
  Escribir-Bien "DepthFlow verificado en .depthflow"
}

Escribir-Paso "Herramientas del sistema"
$ffmpeg = Resolver-Herramienta "ffmpeg" "ESTUDIO_FFMPEG"
$ffprobe = Resolver-Herramienta "ffprobe" "ESTUDIO_FFPROBE"
if (-not $ffmpeg -or -not $ffprobe) {
  Escribir-Aviso "Faltan ffmpeg y/o ffprobe. Sin ellos no hay voz ni video."
  Escribir-Aviso "Instalalos con: winget install --id Gyan.FFmpeg -e"
  Escribir-Aviso "Despues cierra y abre la consola para que el PATH se actualice."
} else {
  $versionFfmpeg = (& $ffmpeg -version 2>$null | Select-Object -First 1)
  Escribir-Bien "ffmpeg: $versionFfmpeg"
}
$navegador = Resolver-Navegador
if (-not $navegador) {
  Escribir-Aviso "No encuentro Microsoft Edge ni Chrome. Sin navegador no se rasteriza ningun plano."
  Escribir-Aviso "Instala Edge o define ESTUDIO_EDGE con la ruta a msedge.exe."
} else {
  Escribir-Bien "Navegador: $navegador"
}

$mayorNode = 0
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
  Escribir-Aviso "No encuentro Node 20 o superior; los CLI de Claude y Codex lo necesitan."
  Escribir-Aviso "Instalalo con: winget install --id OpenJS.NodeJS.LTS -e"
} else {
  $versionNode = (& node --version 2>$null | Select-Object -First 1)
  $mayorNode = 0
  if ($versionNode -match '^v(\d+)') { $mayorNode = [int]$Matches[1] }
  if ($mayorNode -lt 20) {
    Escribir-Aviso "Node $versionNode es demasiado antiguo: hace falta Node 20 o superior."
  } else {
    Escribir-Bien "Node: $versionNode"
  }
}

Escribir-Paso "El motor adicional de Remotion"
# npm.cmd evita que la politica de PowerShell bloquee npm.ps1 en Windows.
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npm) { $npm = Get-Command npm -ErrorAction SilentlyContinue }
if ($mayorNode -ge 22 -and $npm) {
  & $npm.Source ci --prefix (Join-Path $Raiz "motores\remotion") --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) {
    Fallar "No se han podido instalar las dependencias de Remotion. Revisa el error de npm de arriba y vuelve a lanzar."
  }
  Escribir-Bien "Remotion instalado"
} else {
  Escribir-Aviso "Remotion necesita Node 22 o superior y npm. Instala Node LTS y vuelve a ejecutar este archivo."
  Escribir-Nota "Tambien puedes ejecutar despues: npm ci --prefix motores/remotion"
}

$claude = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claude) {
  Escribir-Aviso "No encuentro el CLI de Claude. Sin el no se genera el guion."
  Escribir-Aviso "Instalalo con: npm install -g @anthropic-ai/claude-code"
} else {
  $versionClaude = (& claude --version 2>$null | Select-Object -First 1)
  Escribir-Bien "Claude: $versionClaude"
}

$codex = Get-Command codex -ErrorAction SilentlyContinue
if (-not $codex) {
  Escribir-Aviso "No encuentro el CLI de Codex. Sin el no se generan imagenes con ChatGPT."
  Escribir-Aviso "Instalalo con: npm install -g @openai/codex@0.165.0"
} else {
  $versionCodex = (& codex --version 2>$null | Select-Object -First 1)
  Escribir-Bien "Codex: $versionCodex"
}

Write-Host ""
Write-Host "Listo. Si el estudio ya estaba en marcha, reinicia el servicio para que use .venv."
Write-Host "Arranca el estudio con:" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\python.exe app.py --puerto 8020"
Write-Host ""
if (-not $SinDepthflow) {
  Write-Host "Si mueves .depthflow, define ESTUDIO_DEPTHFLOW_PYTHON con su ruta:"
  Write-Host '  $env:ESTUDIO_DEPTHFLOW_PYTHON = (Resolve-Path .depthflow\Scripts\python.exe).Path'
  Write-Host ""
}
