from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

from app.domain import ServiceRecord
from app.repositories.oracle import OracleUnavailable


REQUIRED_COLUMNS = (
    "PLAN", "DSC_PLAN", "CAMPANA", "DSC_CAMPANA", "FEC_INI_CAMPANA",
    "FEC_FIN_CAMPANA", "DSC_SOLUCION", "TMCODE", "SPCODE", "SNCODE",
    "SERVICIO", "DSC_SERVICIO", "CF_SIN_IGV", "CF_CON_IGV",
    "DSC_TIPO_SERVICIO", "LLAVE",
)


def _money(value):
    try:
        return Decimal(str(value or "0").replace(",", ".")).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"Importe Oracle inválido: {value!r}") from exc


class PVUDBRepository:
    def __init__(self, pools, sql_file):
        self.pools = pools
        self.sql_file = Path(sql_file)

    def _load_sql(self):
        if not self.sql_file.exists():
            raise OracleUnavailable(
                "Falta sql/pvudb_campaign.sql. Debe copiarse allí la consulta original autorizada."
            )
        sql = self.sql_file.read_text(encoding="utf-8").strip()
        upper = re.sub(r"--.*?$|/\*.*?\*/", " ", sql, flags=re.M | re.S).upper()
        forbidden = {"INSERT", "UPDATE", "DELETE", "MERGE", "TRUNCATE", "DROP", "ALTER", "CREATE"}
        if any(re.search(rf"\b{word}\b", upper) for word in forbidden):
            raise ValueError("El SQL PVUDB contiene una operación no permitida")
        if ":codigo_campana" not in sql:
            raise ValueError("El SQL PVUDB debe usar el parámetro enlazado :codigo_campana")
        if "UNION ALL" not in upper:
            raise ValueError("El SQL PVUDB autorizado debe conservar sus dos bloques UNION ALL")
        return sql

    def find_campaign(self, campaign_code):
        sql = self._load_sql()
        with self.pools.pool("pvudb").acquire() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, codigo_campana=int(campaign_code))
                columns = [item[0].upper() for item in cursor.description]
                missing = set(REQUIRED_COLUMNS) - set(columns)
                if missing:
                    raise ValueError(f"La consulta PVUDB no devolvió columnas requeridas: {sorted(missing)}")
                return [self._record(dict(zip(columns, row))) for row in cursor]

    @staticmethod
    def _record(row):
        return ServiceRecord(
            plan=str(row["PLAN"]), plan_name=str(row["DSC_PLAN"]),
            campaign=str(row["CAMPANA"]), campaign_name=str(row["DSC_CAMPANA"]),
            solution=str(row.get("DSC_SOLUCION") or ""), tmcode=str(row.get("TMCODE") or ""),
            spcode=str(row.get("SPCODE") or ""), sncode=str(row["SNCODE"]),
            service=str(row.get("SERVICIO") or ""), service_name=str(row["DSC_SERVICIO"]),
            charge_without_tax=_money(row["CF_SIN_IGV"]), charge_with_tax=_money(row["CF_CON_IGV"]),
            service_type=str(row.get("DSC_TIPO_SERVICIO") or ""), key=str(row["LLAVE"]),
        )

