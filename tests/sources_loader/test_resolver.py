"""Tests for sources_loader/resolver.py."""

from dataclasses import dataclass
from pathlib import Path

from dature.field_path import F
from dature.metadata import LoadMetadata
from dature.sources_loader.env_ import EnvFileLoader, EnvLoader
from dature.sources_loader.json_ import JsonLoader
from dature.sources_loader.resolver import resolve_loader


class TestResolveLoader:
    def test_returns_correct_loader_type(self) -> None:
        metadata = LoadMetadata(file_="config.json")

        loader = resolve_loader(metadata)

        assert isinstance(loader, JsonLoader)

    def test_passes_prefix(self) -> None:
        metadata = LoadMetadata(prefix="APP_")

        loader = resolve_loader(metadata)

        assert loader._prefix == "APP_"

    def test_passes_name_style(self) -> None:
        metadata = LoadMetadata(file_="config.json", name_style="lower_snake")

        loader = resolve_loader(metadata)

        assert loader._name_style == "lower_snake"

    def test_passes_field_mapping(self) -> None:
        @dataclass
        class Config:
            key: str

        mapping = {F[Config].key: "value"}
        metadata = LoadMetadata(file_="config.json", field_mapping=mapping)

        loader = resolve_loader(metadata)

        assert loader._field_mapping == mapping

    def test_default_metadata_returns_env_loader(self) -> None:
        metadata = LoadMetadata()

        loader = resolve_loader(metadata)

        assert isinstance(loader, EnvLoader)

    def test_env_with_file_path(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=VALUE")
        metadata = LoadMetadata(file_=str(env_file))

        loader = resolve_loader(metadata)

        assert isinstance(loader, EnvFileLoader)
