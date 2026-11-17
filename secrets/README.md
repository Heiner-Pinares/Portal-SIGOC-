# Archivos secretos

Esta carpeta contiene únicamente este instructivo en el repositorio. Los archivos
reales están excluidos por `.gitignore` y deben instalarse directamente en el
servidor mediante el procedimiento seguro de Infraestructura.

Archivos esperados cuando se usan las rutas de `.env.example`:

- `app_secret_key.txt`: clave aleatoria larga para proteger sesiones.
- `pvudb_password.txt`: contraseña del usuario PVUDB.
- `dwo_password.txt`: contraseña del usuario DWO.
- `demo_password.txt`: opcional; solo para el usuario automático de simulación.

Cada archivo debe contener solamente el secreto, en una única línea. SIGOC elimina
únicamente el salto de línea final. Nunca imprime el contenido en diagnósticos o logs.

En producción se recomiendan rutas absolutas, por ejemplo:

```dotenv
APP_SECRET_KEY_FILE=C:\SIGOC\secrets\app_secret_key.txt
PVUDB_PASSWORD_FILE=C:\SIGOC\secrets\pvudb_password.txt
DWO_PASSWORD_FILE=C:\SIGOC\secrets\dwo_password.txt
```

La cuenta que ejecuta el servicio necesita permiso de lectura; otros usuarios no
deben tener acceso. No coloque estos archivos en Git, correo o carpetas compartidas.

Ejemplo para Infraestructura en PowerShell, reemplazando la cuenta por la identidad
real que ejecutará el servicio:

```powershell
New-Item -ItemType Directory -Force C:\SIGOC\secrets
notepad C:\SIGOC\secrets\app_secret_key.txt
notepad C:\SIGOC\secrets\pvudb_password.txt
notepad C:\SIGOC\secrets\dwo_password.txt

icacls C:\SIGOC\secrets /inheritance:r
icacls C:\SIGOC\secrets /grant:r "DOMINIO\CuentaServicio:(OI)(CI)R" "BUILTIN\Administrators:(OI)(CI)F"
```

`notepad` es solo una opción manual para el ambiente de pruebas. En producción,
Infraestructura debe instalar los archivos mediante su gestor de secretos o proceso
autorizado, sin compartir los valores por correo o chat.
