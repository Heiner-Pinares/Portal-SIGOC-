import os
from pathlib import Path


class SecretConfigurationError(RuntimeError):
    """Error de configuración que nunca incluye el contenido del secreto."""


def resolve_secret(*, file_env: str, value_env: str, base_dir: Path, default: str = "") -> str:
    """Lee un secreto desde archivo; usa la variable directa solo como compatibilidad.

    La ruta configurada en ``file_env`` siempre tiene prioridad. Las rutas relativas
    se resuelven desde la raíz del proyecto para que el servicio Windows no dependa
    de su directorio de trabajo.
    """
    configured_path = os.getenv(file_env, "").strip()
    if configured_path:
        path = Path(configured_path).expanduser()
        if not path.is_absolute():
            path = base_dir / path
        try:
            if not path.is_file():
                raise SecretConfigurationError(
                    f"El archivo configurado en {file_env} no existe o no es un archivo"
                )
            if path.stat().st_size > 65_536:
                raise SecretConfigurationError(
                    f"El archivo configurado en {file_env} supera el tamaño permitido"
                )
            # utf-8-sig acepta archivos UTF-8 normales y elimina el BOM que
            # algunas versiones de Notepad agregan al inicio del archivo.
            value = path.read_text(encoding="utf-8-sig").rstrip("\r\n")
        except SecretConfigurationError:
            raise
        except (OSError, UnicodeError) as exc:
            raise SecretConfigurationError(
                f"No se pudo leer el archivo configurado en {file_env}"
            ) from exc
        if not value:
            raise SecretConfigurationError(f"El archivo configurado en {file_env} está vacío")
        return value
    direct_value = os.getenv(value_env)
    return default if direct_value is None or direct_value == "" else direct_value


def secret_source(*, file_env: str, value_env: str) -> str:
    """Describe la fuente sin revelar el secreto."""
    if os.getenv(file_env, "").strip():
        return f"archivo ({file_env})"
    if os.getenv(value_env, ""):
        return f"variable directa ({value_env}, compatibilidad)"
    return "no configurado"

