# Consulta PVUDB requerida

El archivo `pvudb_campaign.sql` se incorporó desde la consulta disponible en Descargas como `00_CAMPAÑAS_HFC 1.sql`, cuyo contenido coincide con las 16 columnas, tablas, subconsultas y dos bloques `UNION ALL` descritos en el prompt maestro.

El único cambio realizado fue sustituir la lista fija `CAMPANA IN (3504,3216,3454)` por el parámetro enlazado `CAMPANA = :codigo_campana`. Antes de desactivar `SIGOC_DEMO_MODE`, el dueño técnico debe confirmar que `00_CAMPAÑAS_HFC 1.sql` es efectivamente la consulta corporativa autorizada. El validador exige que el SQL:

- sea exclusivamente de lectura;
- conserve `UNION ALL`;
- devuelva las 16 columnas documentadas;
- use `:codigo_campana`;
- no contenga operaciones DML o DDL.

No se alteraron JOIN, columnas, exclusiones ni filtros del negocio.

