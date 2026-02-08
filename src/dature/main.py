from collections.abc import Callable
from pathlib import Path
from typing import Any, overload

from dature.metadata import LoadMetadata
from dature.patcher import load_as_function, make_decorator
from dature.sources_loader.resolver import resolve_loader
from dature.validators.protocols import DataclassInstance


@overload
def load[T](
    metadata: LoadMetadata | None,
    /,
    dataclass_: type[T],
) -> T: ...


@overload
def load(
    metadata: LoadMetadata | None = None,
    /,
    dataclass_: None = None,
) -> Callable[[type[DataclassInstance]], type[DataclassInstance]]: ...


def load(
    metadata: LoadMetadata | None = None,
    /,
    dataclass_: type[Any] | None = None,
) -> Any:
    if metadata is None:
        metadata = LoadMetadata()

    loader_instance = resolve_loader(metadata)
    file_path = Path(metadata.file_) if metadata.file_ else Path()

    if dataclass_ is not None:
        return load_as_function(loader_instance, file_path, dataclass_)

    return make_decorator(loader_instance, file_path)
