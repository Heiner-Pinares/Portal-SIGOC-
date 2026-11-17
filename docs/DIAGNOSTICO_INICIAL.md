# Diagnóstico inicial del repositorio

Fecha: 17 de noviembre de 2026.

- La carpeta `/Users/heinerpinares/Documents/Notas de Producto Portal` estaba vacía.
- No existían framework, versión de Python declarada, frontend, backend, rutas, modelos, usuarios, roles, sesiones, configuración Oracle, autenticación, pruebas, migraciones ni scripts Windows.
- El equipo de ejecución dispone de Python 3.9.6, pero inicialmente no tenía Flask, pytest, python-oracledb, ldap3 ni pycryptodome instalados.
- No se encontró `SIGOC_prototipo(1).html` con ese nombre en la carpeta, pero se localizaron en Descargas `SIGOC_prototipo.html` y `SIGOC_PVUDB_DWO_prototipo.html`; se verificó que coinciden con las capturas y se conservó su lenguaje visual.
- No se encontró `Texto pegado(5).txt`, pero se localizó `00_CAMPAÑAS_HFC 1.sql` en Descargas. Coincide con la estructura descrita (16 columnas y dos bloques `UNION ALL`) y se incorporó sin modificar JOIN/filtros, sustituyendo solo la lista fija de campañas por `:codigo_campana`. Falta confirmación del dueño técnico sobre el nombre alternativo.
- No hubo credenciales, Oracle Instant Client, acceso a la red corporativa ni metadatos DWO. No se intentaron conexiones reales.

Decisión arquitectónica: Flask modular, como exige el prompt cuando el repositorio no tiene backend, con adaptadores de repositorio para que la simulación local y Oracle estén explícitamente separadas.

