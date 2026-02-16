import logging
from collections.abc import Callable
from dataclasses import asdict, dataclass, fields, is_dataclass
from pathlib import Path
from typing import cast

from dature.deep_merge import deep_merge, deep_merge_last_wins, raise_on_conflict
from dature.error_formatter import ErrorContext, handle_load_errors, read_file_content
from dature.errors import DatureConfigError, SourceLoadError, SourceLocation
from dature.load_report import (
    FieldOrigin,
    LoadReport,
    SourceEntry,
    attach_load_report,
    compute_field_origins,
    get_load_report,
)
from dature.metadata import FieldMergeStrategy, LoadMetadata, MergeMetadata, MergeStrategy
from dature.patcher import ensure_retort, merge_fields
from dature.predicate import build_field_merge_map
from dature.sources_loader.base import ILoader
from dature.sources_loader.resolver import get_loader_type, resolve_loader
from dature.types import JSONValue
from dature.validators.protocols import DataclassInstance

logger = logging.getLogger("dature")


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
    *,
    loaders: tuple[ILoader, ...] | None,
    index: int,
    source_meta: LoadMetadata,
) -> ILoader:
    if loaders is not None:
        return loaders[index]
    return resolve_loader(source_meta)


def _log_merge_step(
    *,
    dataclass_name: str,
    step_idx: int,
    strategy: MergeStrategy,
    before: JSONValue,
    source_data: JSONValue,
    after: JSONValue,
) -> None:
    if isinstance(before, dict) and isinstance(source_data, dict) and isinstance(after, dict):
        added_keys = set(source_data.keys()) - set(before.keys())
        overwritten_keys = set(source_data.keys()) & set(before.keys())
        logger.debug(
            "[%s] Merge step %d (strategy=%s): added=%s, overwritten=%s",
            dataclass_name,
            step_idx,
            strategy.value,
            sorted(added_keys),
            sorted(overwritten_keys),
        )
    logger.debug(
        "[%s] State after step %d: %s",
        dataclass_name,
        step_idx,
        after,
    )


def _log_field_origins(
    *,
    dataclass_name: str,
    field_origins: tuple[FieldOrigin, ...],
) -> None:
    for origin in field_origins:
        logger.debug(
            "[%s] Field '%s' = %r  <-- source %d (%s)",
            dataclass_name,
            origin.key,
            origin.value,
            origin.source_index,
            origin.source_file or "<env>",
        )


def _build_merge_report(
    *,
    dataclass_name: str,
    strategy: MergeStrategy,
    source_entries: tuple[SourceEntry, ...],
    field_origins: tuple[FieldOrigin, ...],
    merged_data: JSONValue,
) -> LoadReport:
    return LoadReport(
        dataclass_name=dataclass_name,
        strategy=strategy,
        sources=source_entries,
        field_origins=field_origins,
        merged_data=merged_data,
    )


def _merge_raw_dicts(
    *,
    raw_dicts: list[JSONValue],
    strategy: MergeStrategy,
    dataclass_name: str,
    field_merge_map: dict[str, FieldMergeStrategy] | None = None,
) -> JSONValue:
    merged: JSONValue = {}
    for step_idx, raw in enumerate(raw_dicts):
        before = merged
        if strategy == MergeStrategy.RAISE_ON_CONFLICT:
            merged = deep_merge_last_wins(merged, raw, field_merge_map=field_merge_map)
        else:
            merged = deep_merge(merged, raw, strategy=strategy, field_merge_map=field_merge_map)

        _log_merge_step(
            dataclass_name=dataclass_name,
            step_idx=step_idx,
            strategy=strategy,
            before=before,
            source_data=raw,
            after=merged,
        )

    return merged


def _should_skip_broken(source_meta: LoadMetadata, merge_meta: MergeMetadata) -> bool:
    if source_meta.skip_if_broken is not None:
        return source_meta.skip_if_broken
    return merge_meta.skip_broken_sources


@dataclass(frozen=True, slots=True)
class _LoadedSources:
    raw_dicts: list[JSONValue]
    source_ctxs: list[tuple[ErrorContext, str | None]]
    source_entries: list[SourceEntry]
    last_loader: ILoader


def _load_sources(
    *,
    merge_meta: MergeMetadata,
    dataclass_name: str,
    loaders: tuple[ILoader, ...] | None = None,
) -> _LoadedSources:
    raw_dicts: list[JSONValue] = []
    source_ctxs: list[tuple[ErrorContext, str | None]] = []
    source_entries: list[SourceEntry] = []
    last_loader: ILoader | None = None

    for i, source_meta in enumerate(merge_meta.sources):
        loader_instance = _resolve_loader_for_source(loaders=loaders, index=i, source_meta=source_meta)
        file_path = Path(source_meta.file_) if source_meta.file_ else Path()
        error_ctx = _build_error_ctx(source_meta, dataclass_name)

        def _load_raw(li: ILoader = loader_instance, fp: Path = file_path) -> JSONValue:
            return li.load_raw(fp)

        try:
            raw = handle_load_errors(
                func=_load_raw,
                ctx=error_ctx,
            )
        except (DatureConfigError, FileNotFoundError):
            if not _should_skip_broken(source_meta, merge_meta):
                raise
            logger.warning(
                "[%s] Source %d skipped (broken): file=%s",
                dataclass_name,
                i,
                source_meta.file_ or "<env>",
            )
            continue
        except Exception as exc:
            if not _should_skip_broken(source_meta, merge_meta):
                location = SourceLocation(
                    source_type=get_loader_type(source_meta),
                    file_path=error_ctx.file_path,
                    line_number=None,
                    line_content=None,
                    env_var_name=None,
                )
                source_error = SourceLoadError(
                    message=str(exc),
                    location=location,
                )
                raise DatureConfigError(dataclass_name, [source_error]) from exc
            logger.warning(
                "[%s] Source %d skipped (broken): file=%s",
                dataclass_name,
                i,
                source_meta.file_ or "<env>",
            )
            continue

        raw_dicts.append(raw)

        loader_type = get_loader_type(source_meta)

        logger.debug(
            "[%s] Source %d loaded: loader=%s, file=%s, keys=%s",
            dataclass_name,
            i,
            loader_type,
            source_meta.file_ or "<env>",
            sorted(raw.keys()) if isinstance(raw, dict) else "<non-dict>",
        )
        logger.debug(
            "[%s] Source %d raw data: %s",
            dataclass_name,
            i,
            raw,
        )

        source_entries.append(
            SourceEntry(
                index=i,
                file_path=source_meta.file_,
                loader_type=loader_type,
                raw_data=raw,
            ),
        )

        file_content = read_file_content(error_ctx.file_path)
        source_ctxs.append((error_ctx, file_content))
        last_loader = loader_instance

    if last_loader is None:
        if merge_meta.sources:
            msg = f"All {len(merge_meta.sources)} source(s) failed to load"
        else:
            msg = "MergeMetadata.sources must not be empty"
        source_error = SourceLoadError(message=msg)
        raise DatureConfigError(dataclass_name, [source_error])

    return _LoadedSources(
        raw_dicts=raw_dicts,
        source_ctxs=source_ctxs,
        source_entries=source_entries,
        last_loader=last_loader,
    )


def _load_and_merge[T](
    *,
    merge_meta: MergeMetadata,
    dataclass_: type[T],
    loaders: tuple[ILoader, ...] | None = None,
    debug: bool = False,
) -> T:
    loaded = _load_sources(
        merge_meta=merge_meta,
        dataclass_name=dataclass_.__name__,
        loaders=loaders,
    )

    field_merge_map: dict[str, FieldMergeStrategy] | None = None
    if merge_meta.field_merges:
        field_merge_map = build_field_merge_map(merge_meta.field_merges)

    if merge_meta.strategy == MergeStrategy.RAISE_ON_CONFLICT:
        raise_on_conflict(loaded.raw_dicts, loaded.source_ctxs, dataclass_.__name__, field_merge_map=field_merge_map)

    merged = _merge_raw_dicts(
        raw_dicts=loaded.raw_dicts,
        strategy=merge_meta.strategy,
        dataclass_name=dataclass_.__name__,
        field_merge_map=field_merge_map,
    )

    logger.debug(
        "[%s] Merged result (strategy=%s, %d sources): %s",
        dataclass_.__name__,
        merge_meta.strategy.value,
        len(loaded.raw_dicts),
        merged,
    )

    frozen_entries = tuple(loaded.source_entries)
    field_origins = compute_field_origins(
        raw_dicts=loaded.raw_dicts,
        source_entries=frozen_entries,
        strategy=merge_meta.strategy,
    )

    _log_field_origins(
        dataclass_name=dataclass_.__name__,
        field_origins=field_origins,
    )

    report: LoadReport | None = None
    if debug:
        report = _build_merge_report(
            dataclass_name=dataclass_.__name__,
            strategy=merge_meta.strategy,
            source_entries=frozen_entries,
            field_origins=field_origins,
            merged_data=merged,
        )

    last_error_ctx = loaded.source_ctxs[-1][0]
    try:
        result = handle_load_errors(
            func=lambda: loaded.last_loader.transform_to_dataclass(merged, dataclass_),
            ctx=last_error_ctx,
        )
    except DatureConfigError:
        if report is not None:
            attach_load_report(dataclass_, report)
        raise

    if report is not None:
        attach_load_report(result, report)

    return result


def merge_load_as_function[T](
    merge_meta: MergeMetadata,
    dataclass_: type[T],
    *,
    debug: bool = False,
) -> T:
    result = _load_and_merge(
        merge_meta=merge_meta,
        dataclass_=dataclass_,
        debug=debug,
    )

    last_meta = merge_meta.sources[-1]
    last_loader = resolve_loader(last_meta)
    validating_retort = last_loader.create_validating_retort(dataclass_)
    validation_loader = validating_retort.get_loader(dataclass_)
    result_dict = asdict(cast("DataclassInstance", result))

    last_error_ctx = _build_error_ctx(last_meta, dataclass_.__name__)
    try:
        handle_load_errors(
            func=lambda: validation_loader(result_dict),
            ctx=last_error_ctx,
        )
    except DatureConfigError:
        if debug:
            report = get_load_report(result)
            if report is not None:
                attach_load_report(dataclass_, report)
        raise

    return result


class _MergePatchContext:
    def __init__(
        self,
        *,
        merge_meta: MergeMetadata,
        cls: type[DataclassInstance],
        cache: bool,
        debug: bool,
    ) -> None:
        self.loaders = self._prepare_loaders(merge_meta=merge_meta, cls=cls)

        self.merge_meta = merge_meta
        self.cls = cls
        self.cache = cache
        self.debug = debug
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
        *,
        merge_meta: MergeMetadata,
        cls: type,
    ) -> tuple[ILoader, ...]:
        loaders: list[ILoader] = []
        for source_meta in merge_meta.sources:
            loader_instance = resolve_loader(source_meta)
            ensure_retort(loader_instance, cls)
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
                loaded_data = _load_and_merge(
                    merge_meta=ctx.merge_meta,
                    dataclass_=ctx.cls,
                    loaders=ctx.loaders,
                    debug=ctx.debug,
                )
            finally:
                ctx.loading = False
            if ctx.cache:
                ctx.cached_data = loaded_data

        complete_kwargs = merge_fields(loaded_data, ctx.field_list, args, kwargs)
        ctx.original_init(self, *args, **complete_kwargs)

        if ctx.debug:
            report = get_load_report(loaded_data)
            if report is not None:
                attach_load_report(self, report)

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
    debug: bool = False,
) -> Callable[[type[DataclassInstance]], type[DataclassInstance]]:
    def decorator(cls: type[DataclassInstance]) -> type[DataclassInstance]:
        if not is_dataclass(cls):
            msg = f"{cls.__name__} must be a dataclass"
            raise TypeError(msg)

        ctx = _MergePatchContext(
            merge_meta=merge_meta,
            cls=cls,
            cache=cache,
            debug=debug,
        )
        cls.__init__ = _make_merge_new_init(ctx)  # type: ignore[method-assign]
        cls.__post_init__ = _make_merge_new_post_init(ctx)  # type: ignore[attr-defined]
        return cls

    return decorator
