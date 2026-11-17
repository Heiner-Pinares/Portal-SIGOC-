$ErrorActionPreference = "Stop"
py -3.12 -m venv .venv
& .venv\Scripts\python.exe -m pip install --upgrade pip
& .venv\Scripts\python.exe -m pip install -r requirements-lock.txt
Write-Host "Copie .env.example a .env, complete secretos mediante el mecanismo autorizado y ejecute:"
Write-Host ".venv\Scripts\python.exe -m flask --app wsgi diagnose"

