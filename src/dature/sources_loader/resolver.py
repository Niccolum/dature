from typing import Any

from dature.loader_resolver import resolve_loader_class
from dature.metadata import LoadMetadata
from dature.protocols import LoaderProtocol
from dature.sources_loader.env_ import EnvLoader
from dature.types import ExpandEnvVarsMode


def resolve_loader(
    metadata: LoadMetadata,
    *,
    expand_env_vars: ExpandEnvVarsMode | None = None,
) -> LoaderProtocol:
    loader_class = resolve_loader_class(metadata.loader, metadata.file_)

    resolved_expand = expand_env_vars or metadata.expand_env_vars or "default"

    kwargs: dict[str, Any] = {
        "prefix": metadata.prefix,
        "name_style": metadata.name_style,
        "field_mapping": metadata.field_mapping,
        "root_validators": metadata.root_validators,
        "expand_env_vars": resolved_expand,
    }

    if issubclass(loader_class, EnvLoader):
        kwargs["split_symbols"] = metadata.split_symbols

    return loader_class(**kwargs)
