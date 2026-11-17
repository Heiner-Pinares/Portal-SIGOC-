import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


class Config:
    APP_ENV = os.getenv("APP_ENV", "development")
    SECRET_KEY = os.getenv("APP_SECRET_KEY") or "development-only-change-me"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE")
    PERMANENT_SESSION_LIFETIME = int(os.getenv("SESSION_IDLE_MINUTES", "30")) * 60
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024

    SIGOC_DEMO_MODE = _bool("SIGOC_DEMO_MODE", True)
    DEMO_USER = os.getenv("SIGOC_DEMO_LOCAL_USER", "demo")
    DEMO_PASSWORD = os.getenv("SIGOC_DEMO_LOCAL_PASSWORD", "")
    DATABASE_PATH = str(BASE_DIR / "instance" / "sigoc.db")
    AUDIT_LOG_PATH = os.getenv("AUDIT_LOG_PATH", str(BASE_DIR / "instance" / "audit.log"))

    ORACLE_CLIENT_LIB_DIR = os.getenv("ORACLE_CLIENT_LIB_DIR", "")
    PVUDB_CAMPAIGN_SQL_FILE = os.getenv("PVUDB_CAMPAIGN_SQL_FILE", str(BASE_DIR / "sql" / "pvudb_campaign.sql"))
    PVUDB_HOST = os.getenv("PVUDB_HOST", "scan-pvu.tim.com.pe")
    PVUDB_PORT = int(os.getenv("PVUDB_PORT", "1521"))
    PVUDB_SERVICE_NAME = os.getenv("PVUDB_SERVICE_NAME", "PVUDB")
    PVUDB_USER = os.getenv("PVUDB_USER", "C27826")
    PVUDB_PASSWORD = os.getenv("PVUDB_PASSWORD", "")
    PVUDB_POOL_MIN = int(os.getenv("PVUDB_POOL_MIN", "1"))
    PVUDB_POOL_MAX = int(os.getenv("PVUDB_POOL_MAX", "4"))

    DWO_HOST = os.getenv("DWO_HOST", "scan-dwo.tim.com.pe")
    DWO_PORT = int(os.getenv("DWO_PORT", "1521"))
    DWO_SERVICE_NAME = os.getenv("DWO_SERVICE_NAME", "DWO")
    DWO_USER = os.getenv("DWO_USER", "USRFACDOC")
    DWO_PASSWORD = os.getenv("DWO_PASSWORD", "")
    DWO_SCHEMA = os.getenv("DWO_SCHEMA", "USRFACT")
    DWO_POOL_MIN = int(os.getenv("DWO_POOL_MIN", "1"))
    DWO_POOL_MAX = int(os.getenv("DWO_POOL_MAX", "4"))
    DWO_WRITE_ENABLED = _bool("DWO_WRITE_ENABLED")
    DWO_MAPPING_VERIFIED = _bool("DWO_MAPPING_VERIFIED")
    DWO_BUSINESS_RULES_VERIFIED = _bool("DWO_BUSINESS_RULES_VERIFIED")
    DWO_KEY_VERIFIED = _bool("DWO_KEY_VERIFIED")

    LDAP_HOST = os.getenv("LDAP_HOST", "claro.pe")
    LDAP_NETBIOS = os.getenv("LDAP_DOMINIO_NETBIOS", "CLARO")
    LDAP_BASE_DN = os.getenv("LDAP_BASE_DN", "dc=claro,dc=pe")
    LDAP_MODE = os.getenv("LDAP_MODO", "plano")
    LDAP_CONNECT_TIMEOUT = int(os.getenv("LDAP_TIMEOUT_CONEXION", "5"))
    LDAP_RESPONSE_TIMEOUT = int(os.getenv("LDAP_TIMEOUT_RESPUESTA", "10"))
    LDAP_CA_CERT = os.getenv("LDAP_CA_CERT", "")
    CLARO_EMAIL_DOMAINS = tuple(
        item.strip().lower()
        for item in os.getenv("DOMINIOS_CORREO_CLARO", "claro.com.pe").split(",")
        if item.strip()
    )

    @classmethod
    def oracle_ready(cls) -> bool:
        return bool(cls.ORACLE_CLIENT_LIB_DIR and cls.PVUDB_PASSWORD and cls.DWO_PASSWORD)

    @classmethod
    def write_gate_open(cls) -> bool:
        return all(
            [
                cls.DWO_WRITE_ENABLED,
                cls.DWO_MAPPING_VERIFIED,
                cls.DWO_BUSINESS_RULES_VERIFIED,
                cls.DWO_KEY_VERIFIED,
            ]
        )

