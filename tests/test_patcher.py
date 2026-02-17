"""Tests for patcher.py."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from dature.metadata import LoadMetadata
from dature.patcher import load_as_function, make_decorator
from dature.sources_loader.json_ import JsonLoader


class TestMakeDecorator:
    def test_not_dataclass_raises(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "test"}')
        metadata = LoadMetadata(file_=str(json_file))

        decorator = make_decorator(loader_instance=JsonLoader(), file_path=json_file, metadata=metadata)

        with pytest.raises(TypeError, match="must be a dataclass"):

            @decorator
            class NotADataclass:
                pass

    def test_patches_init(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "test"}')
        metadata = LoadMetadata(file_=str(json_file))

        @dataclass
        class Config:
            name: str

        original_init = Config.__init__
        decorator = make_decorator(loader_instance=JsonLoader(), file_path=json_file, metadata=metadata)
        decorator(Config)

        assert Config.__init__ is not original_init

    def test_patches_post_init(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "test"}')
        metadata = LoadMetadata(file_=str(json_file))

        @dataclass
        class Config:
            name: str

        decorator = make_decorator(loader_instance=JsonLoader(), file_path=json_file, metadata=metadata)
        decorator(Config)

        assert hasattr(Config, "__post_init__")

    def test_loads_on_init(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "from_file", "port": 8080}')
        metadata = LoadMetadata(file_=str(json_file))

        @dataclass
        class Config:
            name: str
            port: int

        decorator = make_decorator(loader_instance=JsonLoader(), file_path=json_file, metadata=metadata)
        decorator(Config)

        config = Config()
        assert config.name == "from_file"
        assert config.port == 8080

    def test_init_args_override_loaded(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "from_file", "port": 8080}')
        metadata = LoadMetadata(file_=str(json_file))

        @dataclass
        class Config:
            name: str
            port: int

        decorator = make_decorator(loader_instance=JsonLoader(), file_path=json_file, metadata=metadata)
        decorator(Config)

        config = Config(name="overridden")
        assert config.name == "overridden"
        assert config.port == 8080

    def test_returns_same_class(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "test"}')
        metadata = LoadMetadata(file_=str(json_file))

        @dataclass
        class Config:
            name: str

        decorator = make_decorator(loader_instance=JsonLoader(), file_path=json_file, metadata=metadata)
        result = decorator(Config)

        assert result is Config

    def test_preserves_original_post_init(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "test"}')
        metadata = LoadMetadata(file_=str(json_file))

        post_init_called = []

        @dataclass
        class Config:
            name: str

            def __post_init__(self):
                post_init_called.append(True)

        decorator = make_decorator(loader_instance=JsonLoader(), file_path=json_file, metadata=metadata)
        decorator(Config)

        Config()
        assert len(post_init_called) == 1


class TestCache:
    def test_cache_returns_same_data(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "original", "port": 8080}')
        metadata = LoadMetadata(file_=str(json_file))

        @dataclass
        class Config:
            name: str
            port: int

        decorator = make_decorator(loader_instance=JsonLoader(), file_path=json_file, metadata=metadata, cache=True)
        decorator(Config)

        first = Config()
        json_file.write_text('{"name": "updated", "port": 9090}')
        second = Config()

        assert first.name == "original"
        assert second.name == "original"
        assert second.port == 8080

    def test_no_cache_rereads_file(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "original", "port": 8080}')
        metadata = LoadMetadata(file_=str(json_file))

        @dataclass
        class Config:
            name: str
            port: int

        decorator = make_decorator(loader_instance=JsonLoader(), file_path=json_file, metadata=metadata, cache=False)
        decorator(Config)

        first = Config()
        json_file.write_text('{"name": "updated", "port": 9090}')
        second = Config()

        assert first.name == "original"
        assert second.name == "updated"
        assert second.port == 9090

    def test_cache_allows_override(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "original", "port": 8080}')
        metadata = LoadMetadata(file_=str(json_file))

        @dataclass
        class Config:
            name: str
            port: int

        decorator = make_decorator(loader_instance=JsonLoader(), file_path=json_file, metadata=metadata, cache=True)
        decorator(Config)

        first = Config()
        assert first.name == "original"
        assert first.port == 8080

        second = Config(name="overridden")
        assert second.name == "overridden"
        assert second.port == 8080


class TestLoadAsFunction:
    def test_returns_loaded_dataclass(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"name": "test", "port": 3000}')
        metadata = LoadMetadata(file_=str(json_file))

        @dataclass
        class Config:
            name: str
            port: int

        result = load_as_function(
            loader_instance=JsonLoader(),
            file_path=json_file,
            dataclass_=Config,
            metadata=metadata,
            debug=False,
        )

        assert result.name == "test"
        assert result.port == 3000

    def test_with_prefix(self, tmp_path: Path):
        json_file = tmp_path / "config.json"
        json_file.write_text('{"app": {"name": "nested"}}')
        metadata = LoadMetadata(file_=str(json_file))

        @dataclass
        class Config:
            name: str

        result = load_as_function(
            loader_instance=JsonLoader(prefix="app"),
            file_path=json_file,
            dataclass_=Config,
            metadata=metadata,
            debug=False,
        )

        assert result.name == "nested"
