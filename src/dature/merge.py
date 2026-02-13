from collections.abc import Callable
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import cast

from dature.error_formatter import ErrorContext, _read_file_content, handle_load_errors, resolve_source_location
from dature.errors import FieldErrorInfo, MergeConflictError, SourceLocation
from dature.metadata import LoadMetadata, MergeMetadata, MergeStrategy
from dature.patcher import _ensure_retort, _merge_fields
from dature.sources_loader.base import ILoader
from dature.sources_loader.resolver import get_loader_type, resolve_loader
from dature.types import JSONValue
from dature.validators.protocols import DataclassInstance

_MIN_CONFLICT_SOURCES = 2


def _deep_merge_last_wins(base: JSONValue, override: JSONValue) -> JSONValue:
    if isinstance(base, dict) and isinstance(override, dict):
        result = dict(base)
        for key, value in override.items():
            if key in result:
                result[key] = _deep_merge_last_wins(result[key], value)
            else:
                result[key] = value
        return result
    return override


def _deep_merge_first_wins(base: JSONValue, override: JSONValue) -> JSONValue:
    if isinstance(base, dict) and isinstance(override, dict):
        result = dict(base)
        for key, value in override.items():
            if key in result:
                result[key] = _deep_merge_first_wins(result[key], value)
            else:
                result[key] = value
        return result
    return base


def _collect_conflicts(
    dicts: list[JSONValue],
    source_contexts: list[tuple[ErrorContext, str | None]],
    path: list[str],
    conflicts: list[tuple[list[str], list[tuple[int, JSONValue]]]],
) -> None:
    key_sources: dict[str, list[tuple[int, JSONValue]]] = {}

    for i, d in enumerate(dicts):
        if not isinstance(d, dict):
            continue
        for key, value in d.items():
            if key not in key_sources:
                key_sources[key] = []
            key_sources[key].append((i, value))

    for key, sources in key_sources.items():
        if len(sources) < _MIN_CONFLICT_SOURCES:
            continue

        nested_dicts = [v for _, v in sources if isinstance(v, dict)]
        if len(nested_dicts) == len(sources):
            _collect_conflicts(
                [v for _, v in sources],
                [source_contexts[i] for i, _ in sources],
                [*path, key],
                conflicts,
            )
        else:
            conflicts.append(([*path, key], sources))


def _raise_on_conflict(
    dicts: list[JSONValue],
    source_ctxs: list[tuple[ErrorContext, str | None]],
    dataclass_name: str,
) -> None:
    conflicts: list[tuple[list[str], list[tuple[int, JSONValue]]]] = []
    _collect_conflicts(dicts, source_ctxs, [], conflicts)

    if not conflicts:
        return

    conflict_errors: list[tuple[FieldErrorInfo, list[SourceLocation]]] = []
    for field_path, sources in conflicts:
        info = FieldErrorInfo(
            field_path=field_path,
            message="Conflicting values in multiple sources",
            input_value=None,
        )
        locations: list[SourceLocation] = []
        for source_idx, _ in sources:
            ctx, file_content = source_ctxs[source_idx]
            loc = resolve_source_location(field_path, ctx, file_content)
            locations.append(loc)
        conflict_errors.append((info, locations))

    raise MergeConflictError(conflict_errors, dataclass_name)


def deep_merge(
    base: JSONValue,
    override: JSONValue,
    strategy: MergeStrategy,
) -> JSONValue:
    if strategy == MergeStrategy.LAST_WINS:
        return _deep_merge_last_wins(base, override)
    if strategy == MergeStrategy.FIRST_WINS:
        return _deep_merge_first_wins(base, override)
    msg = "Use merge_sources for RAISE_ON_CONFLICT strategy"
    raise ValueError(msg)


def _build_error_ctx(metadata: LoadMetadata, dataclass_name: str) -> ErrorContext:
    loader_type = get_loader_type(metadata)
    error_file_path = Path(metadata.file_) if metadata.file_ else None
    return ErrorContext(
        dataclass_name=dataclass_name,
        loader_type=loader_type,
        file_path=error_file_path,
        prefix=metadata.prefix,
        split_symbols=metadata.split_symbols,
    )


def _resolve_loader_for_source(
    loaders: tuple[ILoader, ...] | None,
    index: int,
    source_meta: LoadMetadata,
) -> ILoader:
    if loaders is not None:
        return loaders[index]
    return resolve_loader(source_meta)


def _load_and_merge[T](
    merge_meta: MergeMetadata,
    dataclass_: type[T],
    loaders: tuple[ILoader, ...] | None = None,
) -> tuple[T, ErrorContext]:
    raw_dicts: list[JSONValue] = []
    source_ctxs: list[tuple[ErrorContext, str | None]] = []
    last_loader: ILoader | None = None

    for i, source_meta in enumerate(merge_meta.sources):
        loader_instance = _resolve_loader_for_source(loaders, i, source_meta)
        file_path = Path(source_meta.file_) if source_meta.file_ else Path()
        error_ctx = _build_error_ctx(source_meta, dataclass_.__name__)

        def _load_raw(li: ILoader = loader_instance, fp: Path = file_path) -> JSONValue:
            return li.load_raw(fp)

        raw = handle_load_errors(
            func=_load_raw,
            ctx=error_ctx,
        )
        raw_dicts.append(raw)

        file_content = _read_file_content(error_ctx.file_path)
        source_ctxs.append((error_ctx, file_content))
        last_loader = loader_instance

    if last_loader is None:
        msg = "MergeMetadata.sources must not be empty"
        raise ValueError(msg)

    if merge_meta.strategy == MergeStrategy.RAISE_ON_CONFLICT:
        _raise_on_conflict(raw_dicts, source_ctxs, dataclass_.__name__)

    merged: JSONValue = {}
    for raw in raw_dicts:
        if merge_meta.strategy == MergeStrategy.RAISE_ON_CONFLICT:
            merged = _deep_merge_last_wins(merged, raw)
        else:
            merged = deep_merge(merged, raw, merge_meta.strategy)

    last_error_ctx = source_ctxs[-1][0]
    result = handle_load_errors(
        func=lambda: last_loader.transform_to_dataclass(merged, dataclass_),
        ctx=last_error_ctx,
    )

    return result, last_error_ctx


def merge_load_as_function[T](
    merge_meta: MergeMetadata,
    dataclass_: type[T],
) -> T:
    result, last_error_ctx = _load_and_merge(merge_meta, dataclass_)

    last_meta = merge_meta.sources[-1]
    last_loader = resolve_loader(last_meta)
    validating_retort = last_loader.create_validating_retort(dataclass_)
    validation_loader = validating_retort.get_loader(dataclass_)
    result_dict = asdict(cast("DataclassInstance", result))

    handle_load_errors(
        func=lambda: validation_loader(result_dict),
        ctx=last_error_ctx,
    )

    return result


class _MergePatchContext:
    def __init__(
        self,
        *,
        merge_meta: MergeMetadata,
        cls: type[DataclassInstance],
        cache: bool,
    ) -> None:
        self.loaders = self._prepare_loaders(merge_meta, cls)

        self.merge_meta = merge_meta
        self.cls = cls
        self.cache = cache
        self.cached_data: DataclassInstance | None = None
        self.field_list = fields(cls)
        self.original_init = cls.__init__
        self.original_post_init = getattr(cls, "__post_init__", None)
        self.loading = False
        self.validating = False

        last_loader = self.loaders[-1]
        validating_retort = last_loader.create_validating_retort(cls)
        self.validation_loader = validating_retort.get_loader(cls)

        last_meta = merge_meta.sources[-1]
        self.error_ctx = _build_error_ctx(last_meta, cls.__name__)

    @staticmethod
    def _prepare_loaders(
        merge_meta: MergeMetadata,
        cls: type,
    ) -> tuple[ILoader, ...]:
        loaders: list[ILoader] = []
        for source_meta in merge_meta.sources:
            loader_instance = resolve_loader(source_meta)
            _ensure_retort(loader_instance, cls)
            loaders.append(loader_instance)
        return tuple(loaders)


def _make_merge_new_init(ctx: _MergePatchContext) -> Callable[..., None]:
    def new_init(self: DataclassInstance, *args: object, **kwargs: object) -> None:
        if ctx.loading:
            ctx.original_init(self, *args, **kwargs)
            return

        if ctx.cache and ctx.cached_data is not None:
            loaded_data = ctx.cached_data
        else:
            ctx.loading = True
            try:
                loaded_data, _ = _load_and_merge(
                    ctx.merge_meta,
                    ctx.cls,
                    loaders=ctx.loaders,
                )
            finally:
                ctx.loading = False
            if ctx.cache:
                ctx.cached_data = loaded_data

        complete_kwargs = _merge_fields(loaded_data, ctx.field_list, args, kwargs)
        ctx.original_init(self, *args, **complete_kwargs)

        if ctx.original_post_init is None:
            self.__post_init__()  # type: ignore[attr-defined]

    return new_init


def _make_merge_new_post_init(ctx: _MergePatchContext) -> Callable[..., None]:
    def new_post_init(self: DataclassInstance) -> None:
        if ctx.loading:
            return

        if ctx.validating:
            return

        if ctx.original_post_init is not None:
            ctx.original_post_init(self)

        ctx.validating = True
        try:
            obj_dict = asdict(self)
            handle_load_errors(
                func=lambda: ctx.validation_loader(obj_dict),
                ctx=ctx.error_ctx,
            )
        finally:
            ctx.validating = False

    return new_post_init


def merge_make_decorator(
    merge_meta: MergeMetadata,
    *,
    cache: bool = True,
) -> Callable[[type[DataclassInstance]], type[DataclassInstance]]:
    def decorator(cls: type[DataclassInstance]) -> type[DataclassInstance]:
        if not is_dataclass(cls):
            msg = f"{cls.__name__} must be a dataclass"
            raise TypeError(msg)

        ctx = _MergePatchContext(
            merge_meta=merge_meta,
            cls=cls,
            cache=cache,
        )
        cls.__init__ = _make_merge_new_init(ctx)  # type: ignore[method-assign]
        cls.__post_init__ = _make_merge_new_post_init(ctx)  # type: ignore[attr-defined]
        return cls

    return decorator
