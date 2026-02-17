from typing import Any

from dature.loader_type import LoaderType, get_loader_type
from dature.metadata import LoadMetadata
from dature.sources_loader.base import ILoader
from dature.sources_loader.env_ import EnvFileLoader, EnvLoader
from dature.sources_loader.ini_ import IniLoader
from dature.sources_loader.json_ import JsonLoader
from dature.sources_loader.toml_ import TomlLoader


def _get_loader_class(loader_type: LoaderType) -> type[ILoader]:
    match loader_type:
        case "env":
            return EnvLoader
        case "envfile":
            return EnvFileLoader
        case "yaml" | "yaml1.1":
            from dature.sources_loader.yaml_ import Yaml11Loader  # noqa: PLC0415

            return Yaml11Loader
        case "yaml1.2":
            from dature.sources_loader.yaml_ import Yaml12Loader  # noqa: PLC0415

            return Yaml12Loader
        case "json":
            return JsonLoader
        case "json5":
            from dature.sources_loader.json5_ import Json5Loader  # noqa: PLC0415

            return Json5Loader
        case "toml":
            return TomlLoader
        case "ini":
            return IniLoader
        case _:
            msg = f"Unknown loader type: {loader_type}"
            raise ValueError(msg)


def resolve_loader(metadata: LoadMetadata) -> ILoader:
    loader_type = get_loader_type(metadata.loader, metadata.file_)
    loader_class = _get_loader_class(loader_type)

    kwargs: dict[str, Any] = {
        "prefix": metadata.prefix,
        "name_style": metadata.name_style,
        "field_mapping": metadata.field_mapping,
        "root_validators": metadata.root_validators,
        "enable_expand_env_vars": metadata.enable_expand_env_vars,
    }

    if issubclass(loader_class, EnvLoader):
        kwargs["split_symbols"] = metadata.split_symbols

    return loader_class(**kwargs)
