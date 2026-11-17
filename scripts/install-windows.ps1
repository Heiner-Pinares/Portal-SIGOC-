$ErrorActionPreference = "Stop"
py -3.12 -m venv .venv
& .venv\Scripts\python.exe -m pip install --upgrade pip
& .venv\Scripts\python.exe -m pip install -r requirements-lock.txt
Write-Host "Copie .env.example a .env y configure rutas *_PASSWORD_FILE hacia archivos protegidos."
Write-Host "No escriba contraseñas directamente en .env. Luego ejecute:"
Write-Host ".venv\Scripts\python.exe -m flask --app wsgi diagnose"

