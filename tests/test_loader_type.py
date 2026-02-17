import pytest

from dature.loader_type import get_loader_type


class TestGetLoaderType:
    def test_explicit_loader(self):
        assert get_loader_type(loader="yaml", file_="config.json") == "yaml"

    def test_no_file_returns_env(self):
        assert get_loader_type(loader=None, file_=None) == "env"

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
        assert get_loader_type(loader=None, file_=f"config{extension}") == expected

    @pytest.mark.parametrize(
        "filename",
        [".env.local", ".env.development", ".env.production"],
    )
    def test_dotenv_patterns(self, filename: str):
        assert get_loader_type(loader=None, file_=filename) == "envfile"

    def test_unknown_extension_raises(self):
        with pytest.raises(ValueError, match="Cannot determine loader type"):
            get_loader_type(loader=None, file_="config.xyz")

    def test_uppercase_extension(self):
        assert get_loader_type(loader=None, file_="config.JSON") == "json"
