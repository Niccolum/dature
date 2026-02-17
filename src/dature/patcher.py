import logging
from collections.abc import Callable
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from dature.error_formatter import enrich_skipped_errors, handle_load_errors
from dature.errors import DatureConfigError
from dature.load_report import FieldOrigin, LoadReport, SourceEntry, attach_load_report
from dature.loader_type import get_loader_type
from dature.loading_context import (
    apply_skip_invalid,
    build_error_ctx,
    ensure_retort,
    make_validating_post_init,
    merge_fields,
)
from dature.metadata import LoadMetadata
from dature.sources_loader.base import ILoader
from dature.types import JSONValue
from dature.validators.protocols import DataclassInstance

if TYPE_CHECKING:
    from adaptix import Retort

logger = logging.getLogger("dature")


def _log_single_source_load(
    *,
    dataclass_name: str,
    loader_type: str,
    file_path: str,
    data: JSONValue,
) -> None:
    logger.debug(
        "[%s] Single-source load: loader=%s, file=%s",
        dataclass_name,
        loader_type,
        file_path,
    )
    logger.debug(
        "[%s] Loaded data: %s",
        dataclass_name,
        data,
    )


def _build_single_source_report(
    *,
    dataclass_name: str,
    loader_type: str,
    file_path: str | None,
    raw_data: JSONValue,
) -> LoadReport:
    source = SourceEntry(
        index=0,
        file_path=file_path,
        loader_type=loader_type,
        raw_data=raw_data,
    )

    origins: list[FieldOrigin] = []
    if isinstance(raw_data, dict):
        for key, value in sorted(raw_data.items()):
            origins.append(
                FieldOrigin(
                    key=key,
                    value=value,
                    source_index=0,
                    source_file=file_path,
                    source_loader_type=loader_type,
                ),
            )

    return LoadReport(
        dataclass_name=dataclass_name,
        strategy=None,
        sources=(source,),
        field_origins=tuple(origins),
        merged_data=raw_data,
    )


class _PatchContext:
    def __init__(
        self,
        *,
        loader_instance: ILoader,
        file_path: Path,
        cls: type[DataclassInstance],
        metadata: LoadMetadata,
        cache: bool,
        debug: bool,
    ) -> None:
        ensure_retort(loader_instance, cls)
        validating_retort = loader_instance.create_validating_retort(cls)

        self.loader_instance = loader_instance
        self.file_path = file_path
        self.cls = cls
        self.metadata = metadata
        self.cache = cache
        self.debug = debug
        self.cached_data: DataclassInstance | None = None
        self.field_list = fields(cls)
        self.original_init = cls.__init__
        self.original_post_init = getattr(cls, "__post_init__", None)
        self.validation_loader: Callable[[JSONValue], DataclassInstance] = validating_retort.get_loader(cls)
        self.validating = False
        self.loading = False

        self.loader_type = get_loader_type(metadata.loader, metadata.file_)
        self.error_ctx = build_error_ctx(metadata, cls.__name__)

        # probe_retort создаётся заранее, чтобы adaptix увидел оригинальную сигнатуру
        self.probe_retort: Retort | None = None
        if metadata.skip_if_invalid:
            self.probe_retort = loader_instance.create_probe_retort()
            self.probe_retort.get_loader(cls)


def _load_single_source(ctx: _PatchContext) -> DataclassInstance:
    raw_data = handle_load_errors(
        func=lambda: ctx.loader_instance.load_raw(ctx.file_path),
        ctx=ctx.error_ctx,
    )

    filter_result = apply_skip_invalid(
        raw=raw_data,
        skip_if_invalid=ctx.metadata.skip_if_invalid,
        loader_instance=ctx.loader_instance,
        dataclass_=ctx.cls,
        log_prefix=f"[{ctx.cls.__name__}]",
        probe_retort=ctx.probe_retort,
    )
    raw_data = filter_result.cleaned_dict

    skipped_fields: dict[str, list[LoadMetadata]] = {}
    for path in filter_result.skipped_paths:
        skipped_fields.setdefault(path, []).append(ctx.metadata)

    def _transform(rd: JSONValue = raw_data) -> DataclassInstance:
        return ctx.loader_instance.transform_to_dataclass(rd, ctx.cls)

    try:
        loaded_data = handle_load_errors(
            func=_transform,
            ctx=ctx.error_ctx,
        )
    except DatureConfigError as exc:
        if skipped_fields:
            raise enrich_skipped_errors(exc, skipped_fields) from exc
        raise

    return loaded_data


def _make_new_init(ctx: _PatchContext) -> Callable[..., None]:
    def new_init(self: DataclassInstance, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        if ctx.loading:
            ctx.original_init(self, *args, **kwargs)
            return

        if ctx.cache and ctx.cached_data is not None:
            loaded_data = ctx.cached_data
        else:
            ctx.loading = True
            try:
                loaded_data = _load_single_source(ctx)
            finally:
                ctx.loading = False

            _log_single_source_load(
                dataclass_name=ctx.cls.__name__,
                loader_type=ctx.loader_type,
                file_path=str(ctx.file_path),
                data=asdict(loaded_data),
            )

            if ctx.cache:
                ctx.cached_data = loaded_data

        complete_kwargs = merge_fields(loaded_data, ctx.field_list, args, kwargs)
        ctx.original_init(self, *args, **complete_kwargs)

        if ctx.debug:
            result_dict = asdict(self)
            report = _build_single_source_report(
                dataclass_name=ctx.cls.__name__,
                loader_type=ctx.loader_type,
                file_path=str(ctx.file_path) if ctx.metadata.file_ is not None else None,
                raw_data=result_dict,
            )
            attach_load_report(self, report)

        if ctx.original_post_init is None:
            self.__post_init__()  # type: ignore[attr-defined]

    return new_init


def load_as_function(
    *,
    loader_instance: ILoader,
    file_path: Path,
    dataclass_: type[DataclassInstance],
    metadata: LoadMetadata,
    debug: bool,
) -> DataclassInstance:
    loader_type = get_loader_type(metadata.loader, metadata.file_)
    error_ctx = build_error_ctx(metadata, dataclass_.__name__)

    raw_data = handle_load_errors(
        func=lambda: loader_instance.load_raw(file_path),
        ctx=error_ctx,
    )

    filter_result = apply_skip_invalid(
        raw=raw_data,
        skip_if_invalid=metadata.skip_if_invalid,
        loader_instance=loader_instance,
        dataclass_=dataclass_,
        log_prefix=f"[{dataclass_.__name__}]",
    )
    raw_data = filter_result.cleaned_dict

    skipped_fields: dict[str, list[LoadMetadata]] = {}
    for path in filter_result.skipped_paths:
        skipped_fields.setdefault(path, []).append(metadata)

    report: LoadReport | None = None
    if debug:
        report = _build_single_source_report(
            dataclass_name=dataclass_.__name__,
            loader_type=loader_type,
            file_path=metadata.file_,
            raw_data=raw_data,
        )

    _log_single_source_load(
        dataclass_name=dataclass_.__name__,
        loader_type=loader_type,
        file_path=str(file_path),
        data=raw_data if isinstance(raw_data, dict) else {},
    )

    try:
        result = handle_load_errors(
            func=lambda: loader_instance.transform_to_dataclass(raw_data, dataclass_),
            ctx=error_ctx,
        )
    except DatureConfigError as exc:
        if report is not None:
            attach_load_report(dataclass_, report)
        if skipped_fields:
            raise enrich_skipped_errors(exc, skipped_fields) from exc
        raise

    result_dict = asdict(result)

    validating_retort = loader_instance.create_validating_retort(dataclass_)
    validation_loader = validating_retort.get_loader(dataclass_)

    try:
        handle_load_errors(
            func=lambda: validation_loader(result_dict),
            ctx=error_ctx,
        )
    except DatureConfigError as exc:
        if report is not None:
            attach_load_report(dataclass_, report)
        if skipped_fields:
            raise enrich_skipped_errors(exc, skipped_fields) from exc
        raise

    if report is not None:
        attach_load_report(result, report)

    return result


def make_decorator(
    *,
    loader_instance: ILoader,
    file_path: Path,
    metadata: LoadMetadata,
    cache: bool = True,
    debug: bool = False,
) -> Callable[[type[DataclassInstance]], type[DataclassInstance]]:
    def decorator(cls: type[DataclassInstance]) -> type[DataclassInstance]:
        if not is_dataclass(cls):
            msg = f"{cls.__name__} must be a dataclass"
            raise TypeError(msg)

        ctx = _PatchContext(
            loader_instance=loader_instance,
            file_path=file_path,
            cls=cls,
            metadata=metadata,
            cache=cache,
            debug=debug,
        )
        cls.__init__ = _make_new_init(ctx)  # type: ignore[method-assign]
        cls.__post_init__ = make_validating_post_init(ctx)  # type: ignore[attr-defined]
        return cls

    return decorator
