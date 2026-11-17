from datetime import date


TABLE = "USRFACT.TBL_MAESTRA_CONFIGURACION_OFERTA_PROMOCIONAL"


class DWORepository:
    def __init__(self, pools, config):
        self.pools = pools
        self.config = config

    def inspect_schema(self):
        with self.pools.pool("dwo").acquire() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT COLUMN_NAME, DATA_TYPE, DATA_LENGTH, DATA_PRECISION,
                                      DATA_SCALE, NULLABLE
                       FROM ALL_TAB_COLUMNS
                       WHERE OWNER = :owner
                         AND TABLE_NAME = :table_name
                       ORDER BY COLUMN_ID""",
                    owner="USRFACT",
                    table_name="TBL_MAESTRA_CONFIGURACION_OFERTA_PROMOCIONAL",
                )
                names = [item[0].lower() for item in cursor.description]
                return [dict(zip(names, row)) for row in cursor]

    def list_offers(self, query="", state="", page=1, page_size=20):
        where = []
        binds = {"offset": (page - 1) * page_size, "limit": page_size}
        if query:
            where.append("(TO_CHAR(CAMPANA) LIKE :query OR UPPER(DSC_PLAN) LIKE :query OR UPPER(LLAVE) LIKE :query)")
            binds["query"] = f"%{query.upper()}%"
        if state:
            where.append("ESTADO_NP = :state")
            binds["state"] = state
        clause = " WHERE " + " AND ".join(where) if where else ""
        sql = f"""SELECT * FROM {TABLE}{clause}
                  ORDER BY FECHA_CARGA DESC
                  OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY"""
        with self.pools.pool("dwo").acquire() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, binds)
                columns = [item[0].lower() for item in cursor.description]
                return [dict(zip(columns, row)) for row in cursor]

    def existing_by_keys(self, keys):
        if not keys:
            return {}
        placeholders = ", ".join(f":k{index}" for index in range(len(keys)))
        binds = {f"k{index}": key for index, key in enumerate(keys)}
        sql = f"SELECT * FROM {TABLE} WHERE LLAVE IN ({placeholders})"
        with self.pools.pool("dwo").acquire() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, binds)
                columns = [item[0].lower() for item in cursor.description]
                rows = [dict(zip(columns, row)) for row in cursor]
        result = {}
        for row in rows:
            key = str(row["llave"])
            if key in result:
                raise ValueError(f"LLAVE ambigua en DWO: {key}")
            result[key] = row
        return result

    def update_validity(self, key, starts_on, ends_on):
        self._assert_write_gate()
        # Las columnas reales de vigencia deben ser verificadas antes de habilitar este método.
        raise RuntimeError("Mapeo de vigencia DWO pendiente de confirmación")

    def update_state(self, key, state):
        self._assert_write_gate()
        # Los valores permitidos de ESTADO_NP deben provenir de metadatos/reglas confirmadas.
        raise RuntimeError("Valores ESTADO_NP pendientes de confirmación")

    def apply_batch(self, operations):
        self._assert_write_gate()
        raise RuntimeError("Mapeo INSERT/UPDATE pendiente de la inspección real de DWO")

    def _assert_write_gate(self):
        if not all(
            self.config[name]
            for name in (
                "DWO_WRITE_ENABLED", "DWO_MAPPING_VERIFIED",
                "DWO_BUSINESS_RULES_VERIFIED", "DWO_KEY_VERIFIED",
            )
        ):
            raise PermissionError("La compuerta de escritura DWO está cerrada")


class DemoDWORepository:
    def __init__(self):
        self.rows = {
            "PL100-3504-1001": {
                "llave": "PL100-3504-1001", "campana": "3504", "dsc_campana": "CAMPAÑA DEMO 3504",
                "dsc_plan": "Internet Fibra 400 Mbps", "sncode": "1001", "dscto": "10.00",
                "estado_np": "PENDIENTE", "fecha_carga": "2026-11-01T10:00:00",
            }
        }

    def existing_by_keys(self, keys):
        return {key: self.rows[key] for key in keys if key in self.rows}

    def list_offers(self, query="", state="", page=1, page_size=20):
        rows = list(self.rows.values())
        if query:
            needle = query.lower()
            rows = [row for row in rows if needle in " ".join(map(str, row.values())).lower()]
        if state:
            rows = [row for row in rows if row.get("estado_np") == state]
        start = (page - 1) * page_size
        return rows[start:start + page_size]

    def inspect_schema(self):
        return []

    def update_validity(self, key, starts_on, ends_on):
        if key not in self.rows:
            raise KeyError(key)
        if starts_on > ends_on:
            raise ValueError("La fecha de inicio no puede ser posterior a la fecha de fin")
        self.rows[key]["fecha_inicio_demo"] = date.fromisoformat(starts_on).isoformat()
        self.rows[key]["fecha_fin_demo"] = date.fromisoformat(ends_on).isoformat()
        return self.rows[key]

    def update_state(self, key, state):
        if state not in {"PENDIENTE", "INACTIVO", "ANULADO"}:
            raise ValueError("Estado de demostración no permitido")
        self.rows[key]["estado_np"] = state
        return self.rows[key]

    def apply_batch(self, operations):
        inserted = updated = unchanged = 0
        for operation in operations:
            key = operation["key"]
            row = self.rows.get(key)
            if row is None:
                self.rows[key] = operation.copy()
                inserted += 1
            elif all(str(row.get(k)) == str(v) for k, v in operation.items() if k in row):
                unchanged += 1
            else:
                row.update(operation)
                updated += 1
        return {"inserted": inserted, "updated": updated, "unchanged": unchanged}

