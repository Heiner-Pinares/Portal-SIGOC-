param([string]$Bind = "0.0.0.0:8000")
$ErrorActionPreference = "Stop"
if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "No existe .venv. Ejecute la instalación primero." }
& .venv\Scripts\python.exe -m waitress --listen=$Bind wsgi:app

