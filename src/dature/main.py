from collections.abc import Callable
from pathlib import Path
from typing import Any, overload

from dature.merge import merge_load_as_function, merge_make_decorator
from dature.metadata import LoadMetadata, MergeMetadata
from dature.patcher import load_as_function, make_decorator
from dature.sources_loader.resolver import resolve_loader
from dature.validators.protocols import DataclassInstance


@overload
def load[T](
    metadata: LoadMetadata | MergeMetadata | tuple[LoadMetadata, ...] | None,
    /,
    dataclass_: type[T],
) -> T: ...


@overload
def load(
    metadata: LoadMetadata | MergeMetadata | tuple[LoadMetadata, ...] | None = None,
    /,
    dataclass_: None = None,
    *,
    cache: bool = True,
) -> Callable[[type[DataclassInstance]], type[DataclassInstance]]: ...


def load(
    metadata: LoadMetadata | MergeMetadata | tuple[LoadMetadata, ...] | None = None,
    /,
    dataclass_: type[Any] | None = None,
    *,
    cache: bool = True,
) -> Any:
    if isinstance(metadata, tuple):
        metadata = MergeMetadata(sources=metadata)

    if isinstance(metadata, MergeMetadata):
        if dataclass_ is not None:
            return merge_load_as_function(metadata, dataclass_)
        return merge_make_decorator(metadata, cache=cache)

    if metadata is None:
        metadata = LoadMetadata()

    loader_instance = resolve_loader(metadata)
    file_path = Path(metadata.file_) if metadata.file_ else Path()

    if dataclass_ is not None:
        return load_as_function(
            loader_instance=loader_instance,
            file_path=file_path,
            dataclass_=dataclass_,
            metadata=metadata,
        )

    return make_decorator(
        loader_instance=loader_instance,
        file_path=file_path,
        metadata=metadata,
        cache=cache,
    )
