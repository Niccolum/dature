"""Tests for main.py — public load() API."""

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from dature import LoadMetadata, load


class TestLoadAsDecorator:
    def test_loads_from_file(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "FromFile", "port": 8080}')

        metadata = LoadMetadata(file_=str(json_file))

        @load(metadata)
        @dataclass
        class Config:
            name: str
            port: int

        config = Config()
        assert config.name == "FromFile"
        assert config.port == 8080

    def test_loads_from_env(self, monkeypatch):
        monkeypatch.setenv("APP_NAME", "EnvApp")
        monkeypatch.setenv("APP_PORT", "3000")

        metadata = LoadMetadata(prefix="APP_")

        @load(metadata)
        @dataclass
        class Config:
            name: str
            port: int

        config = Config()
        assert config.name == "EnvApp"
        assert config.port == 3000

    def test_default_metadata(self, monkeypatch):
        monkeypatch.setenv("MY_VAR", "test_value")

        @load()
        @dataclass
        class Config:
            my_var: str

        config = Config()
        assert config.my_var == "test_value"

    def test_explicit_loader_overrides_extension(self, tmp_path: Path):
        txt_file = tmp_path / "config.txt"
        txt_file.write_text('{"app_name": "OverrideApp"}')

        metadata = LoadMetadata(file_=str(txt_file), loader="json")

        @load(metadata)
        @dataclass
        class Config:
            app_name: str

        config = Config()
        assert config.app_name == "OverrideApp"

    def test_priority(self, monkeypatch):
        monkeypatch.setenv("LOADED_VAR", "loaded")
        monkeypatch.setenv("OVERRIDDEN_VAR", "loaded")

        @load()
        @dataclass
        class Config:
            overridden_var: str
            default_var: str = field(default="default")
            loaded_var: str = field(default="default")

        config = Config(overridden_var="from_init")

        assert config.default_var == "default"
        assert config.loaded_var == "loaded"
        assert config.overridden_var == "from_init"

    def test_invalid_decorator_order(self):
        with pytest.raises(TypeError, match="Config must be a dataclass"):

            @dataclass
            @load()
            class Config:
                pass


class TestLoadAsFunction:
    def test_loads_from_file(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "FromFile", "port": 9090}')

        @dataclass
        class Config:
            name: str
            port: int

        metadata = LoadMetadata(file_=str(json_file))
        result = load(metadata, Config)

        assert result.name == "FromFile"
        assert result.port == 9090

    def test_loads_from_env(self, monkeypatch):
        monkeypatch.setenv("APP_NAME", "EnvFunc")
        monkeypatch.setenv("APP_DEBUG", "true")

        @dataclass
        class Config:
            name: str
            debug: bool

        metadata = LoadMetadata(prefix="APP_")
        result = load(metadata, Config)

        assert result.name == "EnvFunc"
        assert result.debug is True

    def test_default_metadata(self, monkeypatch):
        monkeypatch.setenv("MY_VAR", "from_env")

        @dataclass
        class Config:
            my_var: str

        result = load(None, Config)

        assert result.my_var == "from_env"
