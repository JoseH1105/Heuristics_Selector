# Crea (o actualiza) el entorno virtual .venv del proyecto e instala las dependencias.
# Uso, desde la raíz del proyecto:   powershell -ExecutionPolicy Bypass -File setup_env.ps1
# Opcional: -Torch cuda | cpu   para instalar también PyTorch.
param([ValidateSet("none", "cuda", "cpu")][string]$Torch = "none")

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creando .venv con Python 3.12..."
    py -3.12 -m venv .venv
}
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt
& $py -m pip install -e . --no-deps

switch ($Torch) {
    "cuda" { & $py -m pip install torch --index-url https://download.pytorch.org/whl/cu126 }
    "cpu"  { & $py -m pip install torch }
}

& $py -m pytest -q
Write-Host "Entorno listo. En VS Code se selecciona solo (.vscode/settings.json)."
