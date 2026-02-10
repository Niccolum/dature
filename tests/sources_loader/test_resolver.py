"""Tests for sources_loader/resolver.py."""

from pathlib import Path

import pytest

from dature.metadata import LoadMetadata
from dature.sources_loader.env_ import EnvFileLoader, EnvLoader
from dature.sources_loader.ini_ import IniLoader
from dature.sources_loader.json5_ import Json5Loader
from dature.sources_loader.json_ import JsonLoader
from dature.sources_loader.resolver import (
    _get_loader_class,
    _get_loader_type,
    resolve_loader,
)
from dature.sources_loader.toml_ import TomlLoader
from dature.sources_loader.yaml_ import Yaml11Loader, Yaml12Loader


class TestGetLoaderType:
    def test_explicit_loader(self):
        metadata = LoadMetadata(file_="config.json", loader="yaml")

        assert _get_loader_type(metadata) == "yaml"

    def test_no_file_returns_env(self):
        metadata = LoadMetadata()

        assert _get_loader_type(metadata) == "env"

    @pytest.mark.parametrize(
        ("extension", "expected"),
        [
            (".env", "envfile"),
            (".yaml", "yaml"),
            (".yml", "yaml"),
            (".json", "json"),
            (".json5", "json5"),
            (".toml", "toml"),
            (".ini", "ini"),
            (".cfg", "ini"),
        ],
    )
    def test_extension_mapping(self, extension: str, expected: str):
        metadata = LoadMetadata(file_=f"config{extension}")

        assert _get_loader_type(metadata) == expected

    @pytest.mark.parametrize(
        "filename",
        [".env.local", ".env.development", ".env.production"],
    )
    def test_dotenv_patterns(self, filename: str):
        metadata = LoadMetadata(file_=filename)

        assert _get_loader_type(metadata) == "envfile"

    def test_unknown_extension_raises(self):
        metadata = LoadMetadata(file_="config.xyz")

        with pytest.raises(ValueError, match="Cannot determine loader type"):
            _get_loader_type(metadata)

    def test_uppercase_extension(self):
        metadata = LoadMetadata(file_="config.JSON")

        assert _get_loader_type(metadata) == "json"


class TestGetLoaderClass:
    @pytest.mark.parametrize(
        ("loader_type", "expected_class"),
        [
            ("env", EnvLoader),
            ("envfile", EnvFileLoader),
            ("yaml", Yaml11Loader),
            ("yaml1.1", Yaml11Loader),
            ("yaml1.2", Yaml12Loader),
            ("json", JsonLoader),
            ("json5", Json5Loader),
            ("toml", TomlLoader),
            ("ini", IniLoader),
        ],
    )
    def test_known_types(self, loader_type: str, expected_class: type):
        assert _get_loader_class(loader_type) is expected_class

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown loader type"):
            _get_loader_class("nonexistent")


class TestResolveLoader:
    def test_returns_correct_loader_type(self):
        metadata = LoadMetadata(file_="config.json")

        loader = resolve_loader(metadata)

        assert isinstance(loader, JsonLoader)

    def test_passes_prefix(self):
        metadata = LoadMetadata(prefix="APP_")

        loader = resolve_loader(metadata)

        assert loader._prefix == "APP_"

    def test_passes_name_style(self):
        metadata = LoadMetadata(file_="config.json", name_style="lower_snake")

        loader = resolve_loader(metadata)

        assert loader._name_style == "lower_snake"

    def test_passes_field_mapping(self):
        mapping = {"key": "value"}
        metadata = LoadMetadata(file_="config.json", field_mapping=mapping)

        loader = resolve_loader(metadata)

        assert loader._field_mapping == mapping

    def test_default_metadata_returns_env_loader(self):
        metadata = LoadMetadata()

        loader = resolve_loader(metadata)

        assert isinstance(loader, EnvLoader)

    def test_env_with_file_path(self, tmp_path: Path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=VALUE")
        metadata = LoadMetadata(file_=str(env_file))

        loader = resolve_loader(metadata)

        assert isinstance(loader, EnvFileLoader)
