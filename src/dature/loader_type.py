from pathlib import Path
from types import MappingProxyType
from typing import Literal

LoaderType = Literal["env", "envfile", "yaml", "yaml1.1", "yaml1.2", "json", "json5", "toml", "ini"]

EXTENSION_MAP: MappingProxyType[str, LoaderType] = MappingProxyType(
    {
        ".env": "envfile",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".json": "json",
        ".json5": "json5",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
    },
)


def get_loader_type(loader: LoaderType | None, file_: str | None) -> LoaderType:
    if loader is not None:
        return loader

    if file_ is None:
        return "env"

    file_path = Path(file_)

    if (extension := file_path.suffix.lower()) in EXTENSION_MAP:
        return EXTENSION_MAP[extension]

    if file_path.name.startswith(".env"):
        return "envfile"

    supported = ", ".join(EXTENSION_MAP.keys())
    msg = (
        f"Cannot determine loader type for file '{file_}'. "
        f"Please specify loader explicitly or use a supported extension: {supported}"
    )
    raise ValueError(msg)
