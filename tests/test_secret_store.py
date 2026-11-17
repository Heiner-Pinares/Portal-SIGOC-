import pytest

from app.secret_store import SecretConfigurationError, resolve_secret, secret_source


def test_reads_secret_from_relative_file_and_removes_newline(tmp_path, monkeypatch):
    secret_dir = tmp_path / "secrets"
    secret_dir.mkdir()
    secret_file = secret_dir / "database.txt"
    secret_file.write_text("clave-con-espacios internos\r\n", encoding="utf-8")
    monkeypatch.setenv("DATABASE_PASSWORD_FILE", "secrets/database.txt")
    monkeypatch.setenv("DATABASE_PASSWORD", "valor-directo-no-usado")

    value = resolve_secret(
        file_env="DATABASE_PASSWORD_FILE",
        value_env="DATABASE_PASSWORD",
        base_dir=tmp_path,
    )

    assert value == "clave-con-espacios internos"


def test_file_has_priority_over_direct_value(tmp_path, monkeypatch):
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("desde-archivo", encoding="utf-8")
    monkeypatch.setenv("PASSWORD_FILE", str(secret_file))
    monkeypatch.setenv("PASSWORD", "desde-variable")

    assert resolve_secret(
        file_env="PASSWORD_FILE", value_env="PASSWORD", base_dir=tmp_path
    ) == "desde-archivo"


def test_missing_secret_file_fails_without_exposing_a_value(tmp_path, monkeypatch):
    missing = tmp_path / "no-existe.txt"
    monkeypatch.setenv("PASSWORD_FILE", str(missing))
    monkeypatch.setenv("PASSWORD", "secreto-que-no-debe-aparecer")

    with pytest.raises(SecretConfigurationError) as error:
        resolve_secret(file_env="PASSWORD_FILE", value_env="PASSWORD", base_dir=tmp_path)

    assert "PASSWORD_FILE" in str(error.value)
    assert "secreto-que-no-debe-aparecer" not in str(error.value)


def test_empty_secret_file_is_rejected(tmp_path, monkeypatch):
    secret_file = tmp_path / "empty.txt"
    secret_file.write_text("\n", encoding="utf-8")
    monkeypatch.setenv("PASSWORD_FILE", str(secret_file))

    with pytest.raises(SecretConfigurationError, match="vacío"):
        resolve_secret(file_env="PASSWORD_FILE", value_env="PASSWORD", base_dir=tmp_path)


def test_source_description_never_contains_secret(monkeypatch):
    monkeypatch.delenv("PASSWORD_FILE", raising=False)
    monkeypatch.setenv("PASSWORD", "valor-super-secreto")

    description = secret_source(file_env="PASSWORD_FILE", value_env="PASSWORD")

    assert description == "variable directa (PASSWORD, compatibilidad)"
    assert "valor-super-secreto" not in description


def test_empty_legacy_variable_uses_safe_default(tmp_path, monkeypatch):
    monkeypatch.delenv("APP_SECRET_KEY_FILE", raising=False)
    monkeypatch.setenv("APP_SECRET_KEY", "")

    value = resolve_secret(
        file_env="APP_SECRET_KEY_FILE",
        value_env="APP_SECRET_KEY",
        base_dir=tmp_path,
        default="development-only-change-me",
    )

    assert value == "development-only-change-me"
