from pathlib import Path
from typing import TYPE_CHECKING

from dature.sources_loader.env_ import EnvFileLoader, EnvLoader
from dature.sources_loader.ini_ import IniLoader
from dature.sources_loader.json_ import JsonLoader
from dature.sources_loader.toml_ import TomlLoader

if TYPE_CHECKING:
    from dature.protocols import LoaderProtocol

SUPPORTED_EXTENSIONS = (".cfg", ".env", ".ini", ".json", ".json5", ".toml", ".yaml", ".yml")


def _resolve_by_extension(extension: str) -> "type[LoaderProtocol]":
    match extension:
        case ".json":
            return JsonLoader
        case ".toml":
            return TomlLoader
        case ".ini" | ".cfg":
            return IniLoader
        case ".env":
            return EnvFileLoader
        case ".yaml" | ".yml":
            from dature.sources_loader.yaml_ import Yaml12Loader  # noqa: PLC0415

            return Yaml12Loader
        case ".json5":
            from dature.sources_loader.json5_ import Json5Loader  # noqa: PLC0415

            return Json5Loader
        case _:
            supported = ", ".join(SUPPORTED_EXTENSIONS)
            msg = (
                f"Cannot determine loader type for extension '{extension}'. "
                f"Please specify loader explicitly or use a supported extension: {supported}"
            )
            raise ValueError(msg)


def resolve_loader_class(
    loader: "type[LoaderProtocol] | None",
    file_: str | None,
) -> "type[LoaderProtocol]":
    if loader is not None:
        if file_ is not None and loader is EnvLoader:
            msg = (
                "EnvLoader reads from environment variables and does not use files. "
                "Remove file_ or use a file-based loader instead (e.g. EnvFileLoader)."
            )
            raise ValueError(msg)
        return loader

    if file_ is None:
        return EnvLoader

    file_path = Path(file_)

    if file_path.name.startswith(".env"):
        return EnvFileLoader

    return _resolve_by_extension(file_path.suffix.lower())
