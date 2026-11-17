import threading


class OracleUnavailable(RuntimeError):
    pass


class OraclePools:
    _init_lock = threading.Lock()
    _thick_initialized = False

    def __init__(self, config):
        self.config = config
        self._pools = {}

    def _driver(self):
        try:
            import oracledb
        except ImportError as exc:
            raise OracleUnavailable("python-oracledb no está instalado") from exc
        return oracledb

    def initialize_thick(self):
        if self.__class__._thick_initialized:
            return
        lib_dir = self.config["ORACLE_CLIENT_LIB_DIR"]
        if not lib_dir:
            raise OracleUnavailable("ORACLE_CLIENT_LIB_DIR no está configurado")
        with self._init_lock:
            if not self.__class__._thick_initialized:
                self._driver().init_oracle_client(lib_dir=lib_dir)
                self.__class__._thick_initialized = True

    def pool(self, name):
        if name in self._pools:
            return self._pools[name]
        self.initialize_thick()
        driver = self._driver()
        prefix = name.upper()
        password = self.config[f"{prefix}_PASSWORD"]
        if not password:
            raise OracleUnavailable(
                f"{prefix}_PASSWORD_FILE no está configurado o el secreto no está disponible"
            )
        dsn = driver.makedsn(
            self.config[f"{prefix}_HOST"],
            self.config[f"{prefix}_PORT"],
            service_name=self.config[f"{prefix}_SERVICE_NAME"],
        )
        pool = driver.create_pool(
            user=self.config[f"{prefix}_USER"],
            password=password,
            dsn=dsn,
            min=self.config[f"{prefix}_POOL_MIN"],
            max=self.config[f"{prefix}_POOL_MAX"],
            increment=1,
            getmode=driver.POOL_GETMODE_TIMEDWAIT,
            wait_timeout=10_000,
        )
        self._pools[name] = pool
        return pool

    def health(self, name):
        try:
            with self.pool(name).acquire() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM DUAL")
                    return {"ok": cursor.fetchone()[0] == 1, "message": "Conexión verificada"}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def close(self):
        for pool in self._pools.values():
            pool.close(force=True)
        self._pools.clear()

