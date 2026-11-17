# Matriz de mapeo DWO — pendiente de validación

Esta matriz no autoriza escrituras. Debe completarse con los metadatos reales del ambiente corporativo y aprobación funcional.

| Origen PVUDB | Destino DWO | Tipo origen | Tipo destino | Transformación | Obligatorio | Regla actualización |
|---|---|---|---|---|---|---|
| PLAN | Pendiente | Oracle real | Pendiente | Sin confirmar | Pendiente | Pendiente |
| DSC_PLAN | Pendiente | Oracle real | Pendiente | Sin confirmar | Pendiente | Pendiente |
| CAMPANA | Pendiente | Oracle real | Pendiente | Sin confirmar | Pendiente | Pendiente |
| DSC_CAMPANA | Pendiente | Oracle real | Pendiente | Sin confirmar | Pendiente | Pendiente |
| TMCODE | Pendiente | Oracle real | Pendiente | Sin confirmar | Pendiente | Pendiente |
| SPCODE | Pendiente | Oracle real | Pendiente | Sin confirmar | Pendiente | Pendiente |
| SNCODE | Pendiente | Oracle real | Pendiente | Sin confirmar | Pendiente | Pendiente |
| CF_SIN_IGV | Pendiente | Decimal | Pendiente | `Decimal`, sin `float` | Pendiente | Pendiente |
| CF_CON_IGV | Pendiente | texto/Decimal | Pendiente | Conversión segura a `Decimal` | Pendiente | Pendiente |
| LLAVE | Pendiente | texto | Pendiente | Candidata `PLAN-CAMPANA-SNCODE`; unicidad no confirmada | Pendiente | Bloquear si es ambigua |
| selección usuario | PERIODO | entero | Pendiente | Valores autorizados pendientes | Pendiente | Pendiente |
| selección usuario | DSCTO | Decimal/porcentaje | Pendiente | Significado pendiente | Pendiente | Pendiente |
| calculado backend | DSCTO_SIN_IGV | Decimal | Pendiente | Fórmula pendiente | Pendiente | Pendiente |
| calculado backend | DSCTO_IGV | Decimal | Pendiente | Semántica/fórmula pendiente | Pendiente | Pendiente |
| regla DWO | ESTADO_NP | Pendiente | Pendiente | Valores pendientes | Pendiente | Pendiente |
| servidor/Oracle | FECHA_CARGA | fecha | Pendiente | Autoridad temporal pendiente | Pendiente | No sobrescribir sin regla |
| selección usuario | TIPO_DESCUENTO | texto/código | Pendiente | Códigos pendientes | Pendiente | Pendiente |

Consultas de validación requeridas:

```sql
SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION, DATA_SCALE, NULLABLE
FROM ALL_TAB_COLUMNS
WHERE OWNER = 'USRFACT'
  AND TABLE_NAME = 'TBL_MAESTRA_CONFIGURACION_OFERTA_PROMOCIONAL'
ORDER BY COLUMN_ID;
```

También deben revisarse `ALL_CONSTRAINTS`, `ALL_CONS_COLUMNS`, `ALL_INDEXES`, `ALL_IND_COLUMNS` y triggers accesibles.

