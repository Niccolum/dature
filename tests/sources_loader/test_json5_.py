"""Tests for json5_ module (Json5Loader)."""

from dataclasses import dataclass
from pathlib import Path

from dature.sources_loader.json5_ import Json5Loader
from tests.sources_loader.all_types_dataclass import (
    EXPECTED_ALL_TYPES,
    AllPythonTypesCompact,
    assert_all_types_equal,
)


class TestJson5Loader:
    """Tests for Json5Loader class."""

    def test_comprehensive_type_conversion(self, all_types_json5_file: Path):
        """Test loading JSON5 with full type coercion to dataclass."""
        loader = Json5Loader()
        result = loader.load(all_types_json5_file, AllPythonTypesCompact)

        assert_all_types_equal(result, EXPECTED_ALL_TYPES)

    def test_json5_with_prefix(self, prefixed_json5_file: Path):
        @dataclass
        class PrefixedConfig:
            name: str
            port: int
            debug: bool
            environment: str

        expected_data = PrefixedConfig(
            name="PrefixedApp",
            port=9000,
            debug=False,
            environment="production",
        )
        loader = Json5Loader(prefix="app")

        result = loader.load(prefixed_json5_file, PrefixedConfig)

        assert result == expected_data

    def test_json5_empty_object(self, tmp_path: Path):
        """Test loading empty JSON5 object."""
        json5_file = tmp_path / "empty.json5"
        json5_file.write_text("{}")

        loader = Json5Loader()
        data = loader._load(json5_file)

        assert data == {}

    def test_json5_env_var_substitution(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("DB_HOST", "db.example.com")
        monkeypatch.setenv("DB_PORT", "5432")

        json5_file = tmp_path / "env.json5"
        json5_file.write_text('{host: "$DB_HOST", port: "$DB_PORT"}')

        @dataclass
        class DbConfig:
            host: str
            port: int

        loader = Json5Loader()
        result = loader.load(json5_file, DbConfig)

        assert result.host == "db.example.com"
        assert result.port == 5432

    def test_json5_env_var_partial_substitution(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("HOST", "localhost")
        monkeypatch.setenv("PORT", "8080")

        json5_file = tmp_path / "env.json5"
        json5_file.write_text('{url: "http://${HOST}:${PORT}/api"}')

        @dataclass
        class Config:
            url: str

        loader = Json5Loader()
        result = loader.load(json5_file, Config)

        assert result.url == "http://localhost:8080/api"

    def test_json5_dollar_sign_mid_string_existing_var(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("abc", "replaced")

        json5_file = tmp_path / "dollar.json5"
        json5_file.write_text('{value: "prefix$abc/suffix"}')

        @dataclass
        class Config:
            value: str

        loader = Json5Loader()
        result = loader.load(json5_file, Config)

        assert result.value == "prefixreplaced/suffix"

    def test_json5_dollar_sign_mid_string_missing_var(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("nonexistent", raising=False)

        json5_file = tmp_path / "dollar.json5"
        json5_file.write_text('{value: "prefix$nonexistent/suffix"}')

        @dataclass
        class Config:
            value: str

        loader = Json5Loader()
        result = loader.load(json5_file, Config)

        assert result.value == "prefix$nonexistent/suffix"
