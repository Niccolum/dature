from collections.abc import Callable
from pathlib import Path
from typing import Any, overload

from dature.merge import merge_load_as_function, merge_make_decorator
from dature.metadata import LoadMetadata, MergeMetadata
from dature.patcher import load_as_function, make_decorator
from dature.protocols import DataclassInstance
from dature.sources_loader.resolver import resolve_loader


@overload
def load[T](
    metadata: LoadMetadata | MergeMetadata | tuple[LoadMetadata, ...] | None,
    /,
    dataclass_: type[T],
    *,
    debug: bool = False,
) -> T: ...


@overload
def load(
    metadata: LoadMetadata | MergeMetadata | tuple[LoadMetadata, ...] | None = None,
    /,
    dataclass_: None = None,
    *,
    cache: bool = True,
    debug: bool = False,
) -> Callable[[type[DataclassInstance]], type[DataclassInstance]]: ...


def load(
    metadata: LoadMetadata | MergeMetadata | tuple[LoadMetadata, ...] | None = None,
    /,
    dataclass_: type[Any] | None = None,
    *,
    cache: bool = True,
    debug: bool = False,
) -> Any:
    if isinstance(metadata, tuple):
        metadata = MergeMetadata(sources=metadata)

    if isinstance(metadata, MergeMetadata):
        if dataclass_ is not None:
            return merge_load_as_function(metadata, dataclass_, debug=debug)
        return merge_make_decorator(metadata, cache=cache, debug=debug)

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
            debug=debug,
        )

    return make_decorator(
        loader_instance=loader_instance,
        file_path=file_path,
        metadata=metadata,
        cache=cache,
        debug=debug,
    )
