from pathlib import Path
from types import MappingProxyType
from typing import Literal

from dature.metadata import LoadMetadata
from dature.sources_loader.base import ILoader
from dature.sources_loader.env_ import EnvFileLoader, EnvLoader
from dature.sources_loader.ini_ import IniLoader
from dature.sources_loader.json_ import JsonLoader
from dature.sources_loader.toml_ import TomlLoader

LoaderType = Literal["env", "envfile", "yaml", "json", "toml", "ini"]

EXTENSION_MAP: MappingProxyType[str, LoaderType] = MappingProxyType(
    {
        ".env": "envfile",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
    },
)


def _get_loader_class(loader_type: LoaderType) -> type[ILoader]:
    match loader_type:
        case "env":
            return EnvLoader
        case "envfile":
            return EnvFileLoader
        case "yaml":
            from dature.sources_loader.yaml_ import YamlLoader  # noqa: PLC0415

            return YamlLoader
        case "json":
            return JsonLoader
        case "toml":
            return TomlLoader
        case "ini":
            return IniLoader
        case _:
            msg = f"Unknown loader type: {loader_type}"
            raise ValueError(msg)


def _get_loader_type(metadata: LoadMetadata) -> LoaderType:
    if metadata.loader:
        return metadata.loader

    if not metadata.file_:
        return "env"

    file_path = Path(metadata.file_)

    if (extension := file_path.suffix.lower()) in EXTENSION_MAP:
        return EXTENSION_MAP[extension]

    if file_path.name.startswith(".env"):
        return "envfile"

    supported = ", ".join(EXTENSION_MAP.keys())
    msg = (
        f"Cannot determine loader type for file '{metadata.file_}'. "
        f"Please specify loader explicitly or use a supported extension: {supported}"
    )
    raise ValueError(msg)


def resolve_loader(metadata: LoadMetadata) -> ILoader:
    loader_type = _get_loader_type(metadata)
    loader_class = _get_loader_class(loader_type)
    return loader_class(
        prefix=metadata.prefix,
        name_style=metadata.name_style,
        field_mapping=metadata.field_mapping,
        root_validators=metadata.root_validators,
    )
