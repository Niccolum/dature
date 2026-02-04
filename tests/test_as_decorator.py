"""Tests for main functionality.

This module tests the @load main itself, not the underlying loaders.
Loader functionality is tested in tests/sources_loader/.
"""

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from dature import load


class TestmainAutodetection:
    """Tests for automatic loader type detection by file extension."""

    @pytest.mark.parametrize(
        ("extension", "content", "prefix"),
        [
            (".env", "test_var=value", None),
            (".yaml", "test_var: value", None),
            (".yml", "test_var: value", None),
            (".json", '{"test_var": "value"}', None),
            (".toml", 'test_var = "value"', None),
            (".ini", "[DEFAULT]\ntest_var = value", "DEFAULT"),
            (".cfg", "[DEFAULT]\ntest_var = value", "DEFAULT"),
        ],
    )
    def test_extension_autodetection(self, tmp_path: Path, extension: str, content: str, prefix: str):
        """Test that main correctly detects loader type by file extension."""
        config_file = tmp_path / f"config{extension}"
        config_file.write_text(content)

        @load(file_=str(config_file), prefix=prefix)
        @dataclass
        class Config:
            test_var: str

        config = Config()
        assert config.test_var == "value"

    @pytest.mark.parametrize(
        "filename",
        [".env", ".env.local", ".env.development", ".env.production", ".env.test"],
    )
    def test_dotenv_filename_patterns(self, tmp_path: Path, filename: str):
        """Test detection of various .env file naming patterns."""
        env_file = tmp_path / filename
        env_file.write_text("APP_NAME=EnvApp")

        @load(file_=str(env_file))
        @dataclass
        class Config:
            app_name: str

        config = Config()
        assert config.app_name == "EnvApp"


class TestmainLoaderOverride:
    """Tests for explicit loader type specification."""

    def test_explicit_loader_overrides_extension(self, tmp_path: Path):
        """Test that explicit loader parameter overrides file extension detection."""
        txt_file = tmp_path / "config.txt"
        txt_file.write_text('{"app_name": "OverrideApp"}')

        @load(file_=str(txt_file), loader="json")
        @dataclass
        class Config:
            app_name: str

        config = Config()
        assert config.app_name == "OverrideApp"

    def test_explicit_envfile_loader(self, tmp_path: Path):
        """Test explicit 'envfile' loader type."""
        env_file = tmp_path / ".env"
        env_file.write_text("APP_NAME=ExplicitEnv\nAPP_PORT=8080")

        @load(file_=str(env_file), loader="envfile", prefix="APP_")
        @dataclass
        class Config:
            name: str
            port: int

        config = Config()
        assert config.name == "ExplicitEnv"
        assert config.port == 8080


class TestmainEnvMode:
    """Tests for main behavior without file parameter (environment variables mode)."""

    def test_load_without_file_uses_env_loader(self, monkeypatch):
        """Test that main without file parameter loads from environment variables."""
        monkeypatch.setenv("APP_NAME", "EnvOnlyApp")
        monkeypatch.setenv("APP_DEBUG", "true")
        monkeypatch.setenv("APP_PORT", "3000")

        @load(prefix="APP_")
        @dataclass
        class Config:
            name: str
            debug: bool
            port: int

        config = Config()
        assert config.name == "EnvOnlyApp"
        assert config.debug is True
        assert config.port == 3000

    def test_env_mode_with_no_prefix(self, monkeypatch):
        """Test environment variables loading without prefix."""
        monkeypatch.setenv("MY_VAR", "test_value")

        @load()
        @dataclass
        class Config:
            my_var: str

        config = Config()
        assert config.my_var == "test_value"


class TestPriority:
    def test_raw_override_priority(self, monkeypatch):
        """Test that init arguments override loaded values and loaded values override defaults."""
        monkeypatch.setenv("OVERRIDED_DEFAULT_VAR_BY_LOADING_FROM_FILE", "loaded_var")
        monkeypatch.setenv("OVERRIDED_LOADING_VAR_BY_INIT_ARGUMENT", "loaded_var")

        @load()
        @dataclass
        class Config:
            overrided_loading_var_by_init_argument: str
            default_var: str = "default_var"
            overrided_default_var_by_init_argument: str = "default_var"
            overrided_default_var_by_loading_from_file: str = "default_var"

        config = Config(
            overrided_default_var_by_init_argument="init_var",
            overrided_loading_var_by_init_argument="init_var",
        )

        assert config.default_var == "default_var"
        assert config.overrided_default_var_by_init_argument == "init_var"
        assert config.overrided_default_var_by_loading_from_file == "loaded_var"
        assert config.overrided_loading_var_by_init_argument == "init_var"

    def test_field_override_priority(self, monkeypatch):
        """Test that init arguments override loaded values and loaded values override defaults."""
        monkeypatch.setenv("OVERRIDED_DEFAULT_VAR_BY_LOADING_FROM_FILE", "loaded_var")
        monkeypatch.setenv("OVERRIDED_LOADING_VAR_BY_INIT_ARGUMENT", "loaded_var")

        @load()
        @dataclass
        class Config:
            overrided_loading_var_by_init_argument: str
            default_var: str = field(default="default_var")
            overrided_default_var_by_init_argument: str = field(default="default_var")
            overrided_default_var_by_loading_from_file: str = field(default="default_var")

        config = Config(
            overrided_default_var_by_init_argument="init_var",
            overrided_loading_var_by_init_argument="init_var",
        )

        assert config.default_var == "default_var"
        assert config.overrided_default_var_by_init_argument == "init_var"
        assert config.overrided_default_var_by_loading_from_file == "loaded_var"
        assert config.overrided_loading_var_by_init_argument == "init_var"


class TestmainErrorHandling:
    """Tests for main error handling."""

    def test_unknown_extension_raises_error(self, tmp_path: Path):
        """Test that unknown file extension raises ValueError."""
        unknown_file = tmp_path / "config.xyz"
        unknown_file.write_text("some data")

        with pytest.raises(ValueError, match="Cannot determine loader type"):

            @load(file_=str(unknown_file))
            @dataclass
            class Config:
                pass

    def test_invalid_loader_name(self, tmp_path: Path):
        """Test that invalid loader name is handled properly."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"name": "test"}')

        # This should raise an error for non-existent loader
        with pytest.raises((ValueError, KeyError, AttributeError)):

            @load(file_=str(config_file), loader="nonexistent_loader")
            @dataclass
            class Config:
                name: str

    def test_not_dataclass(self):
        """Test that non-dataclass class raises TypeError."""
        with pytest.raises(TypeError, match="Config must be a dataclass"):

            @load()
            class Config:
                pass

    def test_invalid_decorator_order(self):
        """Test that non-dataclass class raises TypeError."""
        with pytest.raises(TypeError, match="Config must be a dataclass"):

            @dataclass
            @load()
            class Config:
                pass
