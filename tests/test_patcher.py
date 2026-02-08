"""Tests for patcher.py."""

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

import pytest

from dature.patcher import _merge_fields, load_as_function, make_decorator
from dature.sources_loader.json_ import JsonLoader


class TestMergeFields:
    @dataclass
    class Config:
        name: str
        port: int
        debug: bool

    @dataclass
    class Loaded:
        name: str = "loaded_name"
        port: int = 8080
        debug: bool = True

    def _field_list(self) -> tuple[Any, ...]:
        return fields(self.Config)

    def test_no_explicit_fields(self):
        loaded = self.Loaded()

        result = _merge_fields(loaded, self._field_list(), (), {})

        assert result == {"name": "loaded_name", "port": 8080, "debug": True}

    def test_all_kwargs_explicit(self):
        loaded = self.Loaded()
        kwargs = {"name": "explicit", "port": 9090, "debug": False}

        result = _merge_fields(loaded, self._field_list(), (), kwargs)

        assert result == {"name": "explicit", "port": 9090, "debug": False}

    def test_partial_kwargs(self):
        loaded = self.Loaded()

        result = _merge_fields(loaded, self._field_list(), (), {"name": "explicit"})

        assert result == {"name": "explicit", "port": 8080, "debug": True}

    def test_positional_args(self):
        loaded = self.Loaded()

        result = _merge_fields(loaded, self._field_list(), ("positional_name",), {})

        assert result == {"port": 8080, "debug": True}

    def test_mixed_args_and_kwargs(self):
        loaded = self.Loaded()

        result = _merge_fields(
            loaded,
            self._field_list(),
            ("positional_name",),
            {"debug": False},
        )

        assert result == {"port": 8080, "debug": False}

    def test_args_beyond_field_count_ignored(self):
        loaded = self.Loaded()

        result = _merge_fields(
            loaded,
            self._field_list(),
            ("a", "b", "c", "extra"),
            {},
        )

        assert result == {}


class TestMakeDecorator:
    def test_not_dataclass_raises(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "test"}')

        decorator = make_decorator(JsonLoader(), json_file)

        with pytest.raises(TypeError, match="must be a dataclass"):

            @decorator
            class NotADataclass:
                pass

    def test_patches_init(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "test"}')

        @dataclass
        class Config:
            name: str

        original_init = Config.__init__
        decorator = make_decorator(JsonLoader(), json_file)
        decorator(Config)

        assert Config.__init__ is not original_init

    def test_patches_post_init(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "test"}')

        @dataclass
        class Config:
            name: str

        decorator = make_decorator(JsonLoader(), json_file)
        decorator(Config)

        assert hasattr(Config, "__post_init__")

    def test_loads_on_init(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "from_file", "port": 8080}')

        @dataclass
        class Config:
            name: str
            port: int

        decorator = make_decorator(JsonLoader(), json_file)
        decorator(Config)

        config = Config()
        assert config.name == "from_file"
        assert config.port == 8080

    def test_init_args_override_loaded(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "from_file", "port": 8080}')

        @dataclass
        class Config:
            name: str
            port: int

        decorator = make_decorator(JsonLoader(), json_file)
        decorator(Config)

        config = Config(name="overridden")
        assert config.name == "overridden"
        assert config.port == 8080

    def test_returns_same_class(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "test"}')

        @dataclass
        class Config:
            name: str

        decorator = make_decorator(JsonLoader(), json_file)
        result = decorator(Config)

        assert result is Config

    def test_preserves_original_post_init(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "test"}')

        post_init_called = []

        @dataclass
        class Config:
            name: str

            def __post_init__(self):
                post_init_called.append(True)

        decorator = make_decorator(JsonLoader(), json_file)
        decorator(Config)

        Config()
        assert len(post_init_called) == 1


class TestLoadAsFunction:
    def test_returns_loaded_dataclass(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "test", "port": 3000}')

        @dataclass
        class Config:
            name: str
            port: int

        result = load_as_function(JsonLoader(), json_file, Config)

        assert result.name == "test"
        assert result.port == 3000

    def test_with_prefix(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"app": {"name": "nested"}}')

        @dataclass
        class Config:
            name: str

        result = load_as_function(JsonLoader(prefix="app"), json_file, Config)

        assert result.name == "nested"
