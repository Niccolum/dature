import logging
from collections.abc import Callable
from dataclasses import asdict, fields, is_dataclass
from typing import cast

from dature.deep_merge import deep_merge, deep_merge_last_wins, raise_on_conflict
from dature.error_formatter import enrich_skipped_errors, handle_load_errors
from dature.errors import DatureConfigError
from dature.field_group import FieldGroupContext, validate_field_groups
from dature.load_report import (
    FieldOrigin,
    LoadReport,
    SourceEntry,
    attach_load_report,
    compute_field_origins,
    get_load_report,
)
from dature.loading_context import build_error_ctx, ensure_retort, make_validating_post_init, merge_fields
from dature.metadata import FieldMergeStrategy, MergeMetadata, MergeStrategy
from dature.predicate import ResolvedFieldGroup, build_field_group_paths, build_field_merge_map
from dature.protocols import DataclassInstance
from dature.source_loading import load_sources
from dature.sources_loader.base import ILoader
from dature.sources_loader.resolver import resolve_loader
from dature.types import JSONValue

logger = logging.getLogger("dature")


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


def _collect_leaf_paths(data: JSONValue, prefix: str = "") -> list[str]:
    if not isinstance(data, dict):
        return [prefix] if prefix else []
    paths: list[str] = []
    for key, value in data.items():
        child_path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            paths.extend(_collect_leaf_paths(value, child_path))
        else:
            paths.append(child_path)
    return paths


def _validate_all_field_groups(
    *,
    raw_dicts: list[JSONValue],
    field_group_paths: tuple[ResolvedFieldGroup, ...],
    dataclass_name: str,
    source_reprs: tuple[str, ...],
) -> None:
    merged: JSONValue = {}
    field_origins: dict[str, int] = {}
    ctx = FieldGroupContext(
        source_reprs=source_reprs,
        field_origins=field_origins,
        dataclass_name=dataclass_name,
    )
    for step_idx, raw in enumerate(raw_dicts):
        validate_field_groups(
            base=merged,
            source=raw,
            field_group_paths=field_group_paths,
            source_index=step_idx,
            ctx=ctx,
        )
        for leaf_path in _collect_leaf_paths(raw):
            field_origins[leaf_path] = step_idx
        merged = deep_merge_last_wins(merged, raw, field_merge_map=None)


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


def _load_and_merge[T: DataclassInstance](
    *,
    merge_meta: MergeMetadata,
    dataclass_: type[T],
    loaders: tuple[ILoader, ...] | None = None,
    debug: bool = False,
) -> T:
    loaded = load_sources(
        merge_meta=merge_meta,
        dataclass_name=dataclass_.__name__,
        dataclass_=dataclass_,
        loaders=loaders,
    )

    field_merge_map: dict[str, FieldMergeStrategy] | None = None
    if merge_meta.field_merges:
        field_merge_map = build_field_merge_map(merge_meta.field_merges, dataclass_)

    field_group_paths: tuple[ResolvedFieldGroup, ...] = ()
    if merge_meta.field_groups:
        field_group_paths = build_field_group_paths(merge_meta.field_groups, dataclass_)

    if field_group_paths:
        source_reprs = tuple(repr(merge_meta.sources[entry.index]) for entry in loaded.source_entries)
        _validate_all_field_groups(
            raw_dicts=loaded.raw_dicts,
            field_group_paths=field_group_paths,
            dataclass_name=dataclass_.__name__,
            source_reprs=source_reprs,
        )

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
    except DatureConfigError as exc:
        if report is not None:
            attach_load_report(dataclass_, report)
        if loaded.skipped_fields:
            raise enrich_skipped_errors(exc, loaded.skipped_fields) from exc
        raise

    if report is not None:
        attach_load_report(result, report)

    return result


def merge_load_as_function[T: DataclassInstance](
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

    last_error_ctx = build_error_ctx(last_meta, dataclass_.__name__)
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
        self.validation_loader: Callable[[JSONValue], DataclassInstance] = validating_retort.get_loader(cls)

        last_meta = merge_meta.sources[-1]
        self.error_ctx = build_error_ctx(last_meta, cls.__name__)

    @staticmethod
    def _prepare_loaders(
        *,
        merge_meta: MergeMetadata,
        cls: type[DataclassInstance],
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
        cls.__post_init__ = make_validating_post_init(ctx)  # type: ignore[attr-defined]
        return cls

    return decorator
