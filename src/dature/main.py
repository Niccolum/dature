from collections.abc import Callable
from pathlib import Path
from typing import overload

from dature.metadata import LoadMetadata
from dature.patcher import load_as_function, make_decorator
from dature.sources_loader.resolver import resolve_loader
from dature.validators.base import DataclassInstance


@overload
def load(
    metadata: LoadMetadata | None,
    /,
    dataclass_: type[DataclassInstance],
) -> DataclassInstance: ...


@overload
def load(
    metadata: LoadMetadata | None = None,
    /,
    dataclass_: None = None,
) -> Callable[[type[DataclassInstance]], type[DataclassInstance]]: ...


def load(
    metadata: LoadMetadata | None = None,
    /,
    dataclass_: type[DataclassInstance] | None = None,
) -> DataclassInstance | Callable[[type[DataclassInstance]], type[DataclassInstance]]:
    if metadata is None:
        metadata = LoadMetadata()

    loader_instance = resolve_loader(metadata)
    file_path = Path(metadata.file_) if metadata.file_ else Path()

    if dataclass_ is not None:
        return load_as_function(loader_instance, file_path, dataclass_)

    return make_decorator(loader_instance, file_path)
