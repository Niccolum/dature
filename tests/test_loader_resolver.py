import pytest

from dature.loader_resolver import resolve_loader_class
from dature.sources_loader.env_ import EnvFileLoader, EnvLoader
from dature.sources_loader.ini_ import IniLoader
from dature.sources_loader.json5_ import Json5Loader
from dature.sources_loader.json_ import JsonLoader
from dature.sources_loader.toml_ import TomlLoader
from dature.sources_loader.yaml_ import Yaml11Loader, Yaml12Loader


class TestResolveLoaderClass:
    def test_explicit_loader(self) -> None:
        assert resolve_loader_class(loader=Yaml11Loader, file_="config.json") is Yaml11Loader

    def test_no_file_returns_env(self) -> None:
        assert resolve_loader_class(loader=None, file_=None) is EnvLoader

    @pytest.mark.parametrize(
        ("extension", "expected"),
        [
            (".env", EnvFileLoader),
            (".yaml", Yaml12Loader),
            (".yml", Yaml12Loader),
            (".json", JsonLoader),
            (".json5", Json5Loader),
            (".toml", TomlLoader),
            (".ini", IniLoader),
            (".cfg", IniLoader),
        ],
    )
    def test_extension_mapping(self, extension: str, expected: type) -> None:
        assert resolve_loader_class(loader=None, file_=f"config{extension}") is expected

    @pytest.mark.parametrize(
        "filename",
        [".env.local", ".env.development", ".env.production"],
    )
    def test_dotenv_patterns(self, filename: str) -> None:
        assert resolve_loader_class(loader=None, file_=filename) is EnvFileLoader

    def test_unknown_extension_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot determine loader type"):
            resolve_loader_class(loader=None, file_="config.xyz")

    def test_uppercase_extension(self) -> None:
        assert resolve_loader_class(loader=None, file_="config.JSON") is JsonLoader

    def test_env_loader_with_file_raises(self) -> None:
        with pytest.raises(ValueError, match="EnvLoader reads from environment variables") as exc_info:
            resolve_loader_class(loader=EnvLoader, file_="config.json")

        assert str(exc_info.value) == (
            "EnvLoader reads from environment variables and does not use files. "
            "Remove file_ or use a file-based loader instead (e.g. EnvFileLoader)."
        )

    def test_env_file_loader_with_file_allowed(self) -> None:
        assert resolve_loader_class(loader=EnvFileLoader, file_=".env.local") is EnvFileLoader
