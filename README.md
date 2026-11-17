# SIGOC — Sistema de Gestión de Ofertas Comerciales

Aplicación Flask para consultar campañas en PVUDB, preparar promociones y administrar ofertas en DWO. Conserva la experiencia visual del prototipo elegido y separa frontend, autenticación, reglas comerciales y repositorios Oracle.

## Estado real

Clasificación actual: **backend implementado con integraciones simuladas e integraciones reales preparadas, pendientes de validación corporativa**.

- El flujo visual completo funciona en `SIGOC_DEMO_MODE=true` y se identifica permanentemente como simulación.
- Oracle Thick, pools PVUDB/DWO, LDAP/NTLM, seguridad de sesiones, roles, auditoría y diagnósticos están implementados.
- La escritura Oracle permanece cerrada. No se activa automáticamente.
- La consulta se recuperó de `00_CAMPAÑAS_HFC 1.sql`, coincidente con la estructura descrita; falta que el dueño técnico confirme que es la versión autorizada equivalente a `Texto pegado(5).txt`.
- Faltan acceso de red, secretos, Oracle Instant Client 19 x64 y metadatos reales de la tabla DWO.
- Las fórmulas definitivas de `DSCTO_SIN_IGV` y `DSCTO_IGV`, los códigos de `TIPO_DESCUENTO`/`ESTADO_NP`, la llave y las columnas de vigencia siguen pendientes de confirmación. Por ello, el repositorio Oracle no ejecuta INSERT/UPDATE todavía.

## Arquitectura

```text
Navegador (HTML/CSS/JS, CSRF)
         |
         v
Flask: sesión + RBAC + endpoints
   |           |            |
   v           v            v
LDAP/NTLM   Servicio     Auditoría SQLite/log
             ofertas
          /           \
       PVUDB          DWO
    solo lectura   lectura/escritura con compuerta
```

- Python: 3.9+; recomendado 3.12 x64 en Windows.
- Framework: Flask 3.
- Servidor Windows: Waitress.
- Sesiones: cookie firmada, `HttpOnly`, `SameSite=Lax`, `Secure` configurable, expiración de 30 minutos.
- Usuarios y auditoría local: SQLite. No se almacenan contraseñas de dominio.
- Roles: `consulta`, `editor`, `administrador`.

## Instalación local

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
flask --app wsgi create-local-user --username editor --display-name "Editor local" --role editor
flask --app wsgi run
```

Abra `http://127.0.0.1:5000`. La contraseña del usuario local se solicita de forma interactiva.

## Instalación en Windows

En PowerShell, desde la raíz del proyecto:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-windows.ps1
Copy-Item .env.example .env
.\.venv\Scripts\Activate.ps1
python -m flask --app wsgi create-local-user --username soporte --display-name "Soporte SIGOC" --role consulta
python -m flask --app wsgi diagnose
python -m pytest -q
.\scripts\start-windows.ps1 -Bind "0.0.0.0:8000"
```

Para servicio Windows, registre `scripts/start-windows.ps1` con el mecanismo corporativo autorizado (NSSM, WinSW o Programador de tareas). No se inventó un nombre de servicio porque debe alinearse con Operaciones. Reinicie usando ese mismo mecanismo; para un proceso interactivo, deténgalo con `Ctrl+C` y vuelva a ejecutar el script.

## Configuración Oracle Thick

1. Instale Oracle Instant Client 19 x64 en una ruta aprobada.
2. Use Python x64 (`python -c "import struct; print(struct.calcsize('P')*8)"`).
3. Configure `ORACLE_CLIENT_LIB_DIR` en `.env`.
4. Configure `PVUDB_PASSWORD` y `DWO_PASSWORD` desde el almacén de secretos autorizado; no las agregue al repositorio.
5. Confirme la procedencia del SQL incluido en `sql/pvudb_campaign.sql` siguiendo [sql/README.md](sql/README.md).
6. Ejecute:

```powershell
python -c "import oracledb; print(oracledb.__version__)"
python -c "import oracledb, os; oracledb.init_oracle_client(lib_dir=os.environ['ORACLE_CLIENT_LIB_DIR']); print(oracledb.clientversion())"
python -m flask --app wsgi diagnose
```

PVUDB usa `scan-pvu.tim.com.pe:1521/PVUDB`, usuario `C27826`, exclusivamente para `SELECT`. DWO usa `scan-dwo.tim.com.pe:1521/DWO`, usuario `USRFACDOC`, esquema `USRFACT`.

## Inspección y habilitación DWO

`flask --app wsgi diagnose` ejecuta `SELECT 1 FROM DUAL` e inspecciona `ALL_TAB_COLUMNS` sin escribir. Antes de habilitar cualquier cambio:

1. Validar columnas, restricciones, índices y triggers de `USRFACT.TBL_MAESTRA_CONFIGURACION_OFERTA_PROMOCIONAL`.
2. Completar y aprobar la matriz de [docs/MAPEO_DWO.md](docs/MAPEO_DWO.md).
3. Confirmar la unicidad de `PLAN-CAMPANA-SNCODE`.
4. Confirmar fórmulas y códigos comerciales.
5. Implementar el SQL de escritura con lista explícita de columnas tras la aprobación.
6. Ejecutar pruebas de integración en un ambiente no productivo.
7. Solo entonces establecer las cuatro variables:

```dotenv
DWO_WRITE_ENABLED=true
DWO_MAPPING_VERIFIED=true
DWO_BUSINESS_RULES_VERIFIED=true
DWO_KEY_VERIFIED=true
```

Si una sola permanece en `false`, el backend bloquea la escritura. No se utilizan pruebas de escritura para verificar conectividad.

## Active Directory

- `C27826`, `E12345` y correos con esos códigos usan exclusivamente NTLM (`CLARO\\CODIGO`).
- Un correo nominal `@claro.com.pe` solo se acepta si existe una correspondencia única con un usuario LDAP previamente sincronizado.
- Nunca existe fallback local para identidades corporativas.
- Después del bind se busca `(sAMAccountName=CODIGO)` con escape LDAP, se valida cuenta habilitada y se sincronizan nombre/correo sin tocar rol ni datos organizacionales.
- `LDAP_MODO` admite `plano`, `starttls` y `ldaps`. Producción debería migrar a StartTLS/LDAPS con certificado válido.

Validación:

```powershell
python -c "import ldap3; print(ldap3.__version__)"
python -c "from Crypto.Hash import MD4; print(MD4.new(b'test').hexdigest())"
```

## API

- `POST /login`, `POST /logout`
- `GET /api/status`
- `GET /api/campanas/<codigo>`
- `POST /api/ofertas/previsualizar`
- `POST /api/ofertas/guardar`
- `GET /api/ofertas?q=&state=&page=`
- `PATCH /api/ofertas/<llave>/vigencia`
- `PATCH /api/ofertas/<llave>/estado`

Los importes originales nunca se aceptan del navegador: el backend vuelve a consultar la campaña y recalcula la previsualización. Guardar exige una previsualización con la misma huella, lo que reduce dobles clics y solicitudes obsoletas.

## Pruebas

```bash
python -m pytest -q
python -m pytest --cov=app --cov-report=term-missing
```

Las pruebas usan proveedores locales; nunca contactan AD ni Oracle. Cubren autenticación local, rechazo de identidades corporativas al backend local, CSRF, permisos, búsqueda, validaciones monetarias con `Decimal`, selección duplicada, vista previa/guardado y requisito de previsualización.

## Seguridad y operación

- `.env`, secretos, certificados privados y bases locales están ignorados por Git.
- Los logs nunca incluyen contraseñas.
- El SQL PVUDB se valida como solo lectura y requiere parámetros enlazados.
- Las consultas DWO usan binds y paginación.
- Producción debe configurar `APP_SECRET_KEY` aleatoria, `SESSION_COOKIE_SECURE=true`, HTTPS y un almacenamiento central de rate limiting si hay varios procesos.
- Para rollback de aplicación, detenga el servicio, restaure la versión de código aprobada y reinicie. No se requieren migraciones DWO. La base SQLite local debe respaldarse antes de una actualización; el código solo crea tablas locales idempotentes.

## Archivos clave

- `app/web.py`: rutas y control de permisos.
- `app/services/auth.py`: LDAP/NTLM y autenticación local restringida.
- `app/services/offers.py`: validación y cálculo con `Decimal`.
- `app/repositories/pvudb.py`: consulta parametrizada, validación de SQL y procesamiento.
- `app/repositories/dwo.py`: consulta/paginación, metadatos y compuerta de escritura.
- `app/templates/app.html`, `app/static/`: interfaz SIGOC responsive.
- `tests/`: pruebas automatizadas sin conexiones reales.

