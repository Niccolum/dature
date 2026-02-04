from collections.abc import Callable
from dataclasses import fields, is_dataclass
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal, overload

from dature.sources_loader.env_ import EnvFileLoader, EnvLoader
from dature.sources_loader.ini_ import IniLoader
from dature.sources_loader.json_ import JsonLoader
from dature.sources_loader.toml_ import TomlLoader
from dature.types import DotSeparatedPath, FieldMapping, NameStyle

if TYPE_CHECKING:
    from dature.sources_loader.base import ILoader

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


def _get_loader_class(loader_type: LoaderType) -> type["ILoader"]:
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


def _get_loader_type(file_: str | None, loader: LoaderType | None) -> LoaderType:
    if loader:
        return loader

    if not file_:
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


@overload
def load[T](
    file_: str | None = None,
    loader: LoaderType | None = None,
    prefix: DotSeparatedPath | None = None,
    name_style: NameStyle | None = None,
    field_mapping: FieldMapping | None = None,
    *,
    dataclass_: type[T],
) -> T: ...


@overload
def load[T](
    file_: str | None = None,
    loader: LoaderType | None = None,
    prefix: DotSeparatedPath | None = None,
    name_style: NameStyle | None = None,
    field_mapping: FieldMapping | None = None,
    *,
    dataclass_: None = None,
) -> Callable[[type[T]], type[T]]: ...


def load[T](  # noqa: PLR0913
    file_: str | None = None,
    loader: LoaderType | None = None,
    prefix: DotSeparatedPath | None = None,
    name_style: NameStyle | None = None,
    field_mapping: FieldMapping | None = None,
    *,
    dataclass_: type[T] | None = None,
) -> T | Callable[[type[T]], type[T]]:
    loader_type = _get_loader_type(file_, loader)
    loader_class = _get_loader_class(loader_type)
    loader_instance = loader_class(prefix=prefix, name_style=name_style, field_mapping=field_mapping)
    file_path = Path(file_) if file_ else Path()

    def _load_config(cls: type[T]) -> type[T]:
        if not is_dataclass(cls):
            msg = f"{cls.__name__} must be a dataclass"
            raise TypeError(msg)

        loaded_data: Any = loader_instance.load(file_path, cls)
        field_list = fields(cls)
        original_init = cls.__init__

        def new_init(self: T, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
            explicit_fields = set(kwargs.keys())

            for i, _ in enumerate(args):
                if i < len(field_list):
                    explicit_fields.add(field_list[i].name)

            complete_kwargs = dict(kwargs)
            for field in field_list:
                if field.name not in explicit_fields:
                    complete_kwargs[field.name] = getattr(loaded_data, field.name)

            original_init(self, *args, **complete_kwargs)

        cls.__init__ = new_init  # type: ignore[assignment]
        return cls

    if dataclass_ is not None:
        return loader_instance.load(file_path, dataclass_)

    return _load_config
