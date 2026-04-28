import copy
import dataclasses
import logging
from dataclasses import dataclass

from dature.config import config
from dature.errors.location import ErrorContext
from dature.field_path import FieldPath
from dature.loading.context import apply_skip_invalid
from dature.loading.merge_config import MergeConfig, SourceParams
from dature.protocols import DataclassInstance
from dature.skip_field_provider import FilterResult
from dature.sources.base import Source
from dature.types import (
    JSONValue,
    TypeLoaderMap,
)

logger = logging.getLogger("dature")


def apply_source_init_params(source: Source, params: SourceParams) -> Source:
    """Inject load-level params into source fields (source > load > config).

    Iterates SourceParams fields by name and matches them against the source's
    dataclass fields. For each matching field currently None: applies
    load-level value, or falls back to config.loading.<same_name> if available.
    """
    source_field_names = {f.name for f in dataclasses.fields(source) if f.init}
    overrides: dict[str, object] = {}

    for f in dataclasses.fields(params):
        name = f.name
        if name not in source_field_names:
            continue
        if getattr(source, name, None) is not None:
            continue  # source-level takes priority
        load_val = getattr(params, name)
        config_val = getattr(config.loading, name, None)
        effective = load_val if load_val is not None else config_val
        if effective is not None:
            overrides[name] = effective

    if not overrides:
        return source

    new_source = copy.copy(source)
    vars(new_source).update(overrides)
    return new_source


def resolve_type_loaders(
    source: Source,
    load_type_loaders: TypeLoaderMap | None,
) -> TypeLoaderMap | None:
    merged = {**config.type_loaders, **(load_type_loaders or {}), **(source.type_loaders or {})}
    return merged or None


def should_skip_broken(source: Source, merge_meta: MergeConfig) -> bool:
    if source.skip_if_broken is not None:
        if source.file_display() is None:
            logger.warning(
                "skip_if_broken has no effect on non-file sources — they cannot be broken",
            )
        return source.skip_if_broken
    return merge_meta.skip_broken_sources


def resolve_skip_invalid(
    source: Source,
    merge_meta: MergeConfig,
) -> bool | tuple[FieldPath, ...]:
    if source.skip_if_invalid is not None:
        return source.skip_if_invalid
    return merge_meta.skip_invalid_fields


def apply_merge_skip_invalid(
    *,
    raw: JSONValue,
    source: Source,
    merge_meta: MergeConfig,
    schema: type[DataclassInstance],
    source_index: int,
) -> FilterResult:
    skip_value = resolve_skip_invalid(source, merge_meta)
    if not skip_value:
        return FilterResult(cleaned_dict=raw, skipped_paths=[])

    return apply_skip_invalid(
        raw=raw,
        skip_if_invalid=skip_value,
        source=source,
        schema=schema,
        log_prefix=f"[{schema.__name__}] Source {source_index}:",
    )


@dataclass(frozen=True, slots=True)
class SourceContext:
    error_ctx: ErrorContext
    file_content: str | None


@dataclass(frozen=True, slots=True)
class SkippedFieldSource:
    source: Source
    error_ctx: ErrorContext
    file_content: str | None
