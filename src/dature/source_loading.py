import logging
from dataclasses import dataclass
from pathlib import Path

from dature.error_formatter import ErrorContext, handle_load_errors, read_file_content
from dature.errors import DatureConfigError, SourceLoadError, SourceLocation
from dature.field_path import FieldPath
from dature.load_report import SourceEntry
from dature.loader_type import get_loader_type
from dature.loading_context import apply_skip_invalid, build_error_ctx
from dature.metadata import LoadMetadata, MergeMetadata
from dature.skip_field_provider import FilterResult
from dature.sources_loader.base import ILoader
from dature.sources_loader.resolver import resolve_loader
from dature.types import JSONValue
from dature.validators.protocols import DataclassInstance

logger = logging.getLogger("dature")


def resolve_loader_for_source(
    *,
    loaders: tuple[ILoader, ...] | None,
    index: int,
    source_meta: LoadMetadata,
) -> ILoader:
    if loaders is not None:
        return loaders[index]
    return resolve_loader(source_meta)


def should_skip_broken(source_meta: LoadMetadata, merge_meta: MergeMetadata) -> bool:
    if source_meta.skip_if_broken is not None:
        return source_meta.skip_if_broken
    return merge_meta.skip_broken_sources


def resolve_skip_invalid(
    source_meta: LoadMetadata,
    merge_meta: MergeMetadata,
) -> bool | tuple[FieldPath, ...]:
    if source_meta.skip_if_invalid is not None:
        return source_meta.skip_if_invalid
    return merge_meta.skip_invalid_fields


def apply_merge_skip_invalid(
    *,
    raw: JSONValue,
    source_meta: LoadMetadata,
    merge_meta: MergeMetadata,
    loader_instance: ILoader,
    dataclass_: type[DataclassInstance],
    source_index: int,
) -> FilterResult:
    skip_value = resolve_skip_invalid(source_meta, merge_meta)
    if not skip_value:
        return FilterResult(cleaned_dict=raw, skipped_paths=[])

    return apply_skip_invalid(
        raw=raw,
        skip_if_invalid=skip_value,
        loader_instance=loader_instance,
        dataclass_=dataclass_,
        log_prefix=f"[{dataclass_.__name__}] Source {source_index}:",
    )


@dataclass(frozen=True, slots=True)
class LoadedSources:
    raw_dicts: list[JSONValue]
    source_ctxs: list[tuple[ErrorContext, str | None]]
    source_entries: list[SourceEntry]
    last_loader: ILoader
    skipped_fields: dict[str, list[LoadMetadata]]


def load_sources(
    *,
    merge_meta: MergeMetadata,
    dataclass_name: str,
    dataclass_: type[DataclassInstance],
    loaders: tuple[ILoader, ...] | None = None,
) -> LoadedSources:
    raw_dicts: list[JSONValue] = []
    source_ctxs: list[tuple[ErrorContext, str | None]] = []
    source_entries: list[SourceEntry] = []
    last_loader: ILoader | None = None
    skipped_fields: dict[str, list[LoadMetadata]] = {}

    for i, source_meta in enumerate(merge_meta.sources):
        loader_instance = resolve_loader_for_source(loaders=loaders, index=i, source_meta=source_meta)
        file_path = Path(source_meta.file_) if source_meta.file_ else Path()
        error_ctx = build_error_ctx(source_meta, dataclass_name)

        def _load_raw(li: ILoader = loader_instance, fp: Path = file_path) -> JSONValue:
            return li.load_raw(fp)

        try:
            raw = handle_load_errors(
                func=_load_raw,
                ctx=error_ctx,
            )
        except (DatureConfigError, FileNotFoundError):
            if not should_skip_broken(source_meta, merge_meta):
                raise
            logger.warning(
                "[%s] Source %d skipped (broken): file=%s",
                dataclass_name,
                i,
                source_meta.file_ or "<env>",
            )
            continue
        except Exception as exc:
            if not should_skip_broken(source_meta, merge_meta):
                location = SourceLocation(
                    source_type=get_loader_type(source_meta.loader, source_meta.file_),
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

        filter_result = apply_merge_skip_invalid(
            raw=raw,
            source_meta=source_meta,
            merge_meta=merge_meta,
            loader_instance=loader_instance,
            dataclass_=dataclass_,
            source_index=i,
        )

        for path in filter_result.skipped_paths:
            skipped_fields.setdefault(path, []).append(source_meta)

        raw = filter_result.cleaned_dict
        raw_dicts.append(raw)

        loader_type = get_loader_type(source_meta.loader, source_meta.file_)

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

    return LoadedSources(
        raw_dicts=raw_dicts,
        source_ctxs=source_ctxs,
        source_entries=source_entries,
        last_loader=last_loader,
        skipped_fields=skipped_fields,
    )
