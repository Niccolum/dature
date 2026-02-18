import types
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Union, get_args

from adaptix.load_error import (
    AggregateLoadError,
    BadVariantLoadError,
    ExtraFieldsLoadError,
    LoadError,
    LoadExceptionGroup,
    NoRequiredFieldsLoadError,
    TypeLoadError,
    ValidationLoadError,
    ValueLoadError,
)
from adaptix.struct_trail import get_trail

from dature.errors import DatureConfigError, DatureError, FieldLoadError, LineRange, SourceLocation
from dature.source_locators.base import PathFinder
from dature.source_locators.ini_ import TablePathFinder

if TYPE_CHECKING:
    from dature.metadata import LoadMetadata
from dature.source_locators.json5_ import Json5PathFinder
from dature.source_locators.json_ import JsonPathFinder
from dature.source_locators.toml_ import TomlPathFinder
from dature.source_locators.yaml_ import YamlPathFinder

_PATH_FINDER_MAP: dict[str, type[PathFinder]] = {
    "yaml": YamlPathFinder,
    "yaml1.1": YamlPathFinder,
    "yaml1.2": YamlPathFinder,
    "json": JsonPathFinder,
    "json5": Json5PathFinder,
    "toml": TomlPathFinder,
    "ini": TablePathFinder,
}


@dataclass(frozen=True)
class ErrorContext:
    dataclass_name: str
    loader_type: str
    file_path: Path | None
    prefix: str | None
    split_symbols: str


def _describe_error(exc: BaseException) -> str:
    if isinstance(exc, (ValidationLoadError, ValueLoadError)):
        return str(exc.msg)

    if isinstance(exc, TypeLoadError):
        expected = exc.expected_type
        if isinstance(expected, types.UnionType) or getattr(expected, "__origin__", None) is Union:
            names = [arg.__name__ for arg in get_args(expected)]
            expected_name = " | ".join(names)
        else:
            expected_name = expected.__name__
        return f"Expected {expected_name}, got {type(exc.input_value).__name__}"

    if isinstance(exc, ExtraFieldsLoadError):
        field_names = ", ".join(sorted(exc.fields))
        return f"Unknown field(s): {field_names}"

    if isinstance(exc, BadVariantLoadError):
        return f"Invalid variant: {exc.input_value!r}"

    return str(exc)


def _walk_exception(
    exc: BaseException,
    parent_path: list[str],
    result: list[FieldLoadError],
) -> None:
    trail = list(get_trail(exc))
    current_path = parent_path + [str(elem) for elem in trail]

    if isinstance(exc, LoadExceptionGroup):
        for sub_exc in exc.exceptions:
            _walk_exception(sub_exc, current_path, result)
        return

    if isinstance(exc, NoRequiredFieldsLoadError):
        result.extend(
            FieldLoadError(
                field_path=[*current_path, field_name],
                message="Missing required field",
                input_value=None,
            )
            for field_name in sorted(exc.fields)
        )
        return

    result.append(
        FieldLoadError(
            field_path=current_path,
            message=_describe_error(exc),
            input_value=getattr(exc, "input_value", None),
        ),
    )


def extract_field_errors(exc: BaseException) -> list[FieldLoadError]:
    result: list[FieldLoadError] = []
    _walk_exception(exc, [], result)
    return result


def read_file_content(file_path: Path | None) -> str | None:
    if file_path is None:
        return None

    with suppress(OSError):
        return file_path.read_text()

    return None


def _build_env_var_name(
    field_path: list[str],
    prefix: str | None,
    split_symbols: str,
) -> str:
    var_name = split_symbols.join(part.upper() for part in field_path)
    if prefix is not None:
        return prefix + var_name
    return var_name


def _build_search_path(field_path: list[str], prefix: str | None) -> list[str]:
    if not prefix:
        return field_path
    prefix_parts = prefix.split(".")
    return prefix_parts + field_path


def _find_env_line(content: str, var_name: str) -> SourceLocation:
    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        if key == var_name:
            return SourceLocation(
                source_type="envfile",
                file_path=None,
                line_range=LineRange(start=i, end=i),
                line_content=[stripped],
                env_var_name=var_name,
            )
    return SourceLocation(
        source_type="envfile",
        file_path=None,
        line_range=None,
        line_content=None,
        env_var_name=var_name,
    )


def _empty_file_location(loader_type: str, file_path: Path | None) -> SourceLocation:
    return SourceLocation(
        source_type=loader_type,
        file_path=file_path,
        line_range=None,
        line_content=None,
        env_var_name=None,
    )


def _strip_common_indent(raw_lines: list[str]) -> list[str]:
    indents = [len(line) - len(line.lstrip()) for line in raw_lines if line.strip()]
    if not indents:
        return raw_lines
    min_indent = min(indents)
    return [line[min_indent:] for line in raw_lines]


def _resolve_file_location(
    field_path: list[str],
    loader_type: str,
    file_path: Path | None,
    file_content: str | None,
    prefix: str | None,
) -> SourceLocation:
    if file_content is None or not field_path:
        return _empty_file_location(loader_type, file_path)

    finder_class = _PATH_FINDER_MAP.get(loader_type)
    if finder_class is None:
        return _empty_file_location(loader_type, file_path)

    search_path = _build_search_path(field_path, prefix)
    finder = finder_class(file_content)
    line_range = finder.find_line_range(search_path)
    if line_range is None:
        return _empty_file_location(loader_type, file_path)

    lines = file_content.splitlines()
    content_lines: list[str] | None = None
    if 0 < line_range.start <= len(lines):
        end = min(line_range.end, len(lines))
        raw = lines[line_range.start - 1 : end]
        content_lines = _strip_common_indent(raw)

    return SourceLocation(
        source_type=loader_type,
        file_path=file_path,
        line_range=line_range,
        line_content=content_lines,
        env_var_name=None,
    )


def resolve_source_location(
    field_path: list[str],
    ctx: ErrorContext,
    file_content: str | None,
) -> SourceLocation:
    if ctx.loader_type == "env":
        env_var_name = _build_env_var_name(field_path, ctx.prefix, ctx.split_symbols)
        return SourceLocation(
            source_type="env",
            file_path=None,
            line_range=None,
            line_content=None,
            env_var_name=env_var_name,
        )

    if ctx.loader_type == "envfile":
        env_var_name = _build_env_var_name(field_path, ctx.prefix, ctx.split_symbols)
        if file_content is not None:
            location = _find_env_line(file_content, env_var_name)
            return SourceLocation(
                source_type="envfile",
                file_path=ctx.file_path,
                line_range=location.line_range,
                line_content=location.line_content,
                env_var_name=env_var_name,
            )
        return SourceLocation(
            source_type="envfile",
            file_path=ctx.file_path,
            line_range=None,
            line_content=None,
            env_var_name=env_var_name,
        )

    return _resolve_file_location(field_path, ctx.loader_type, ctx.file_path, file_content, ctx.prefix)


def handle_load_errors[T](
    *,
    func: Callable[[], T],
    ctx: ErrorContext,
) -> T:
    try:
        return func()
    except (AggregateLoadError, LoadError) as exc:
        file_content = read_file_content(ctx.file_path)
        field_errors = extract_field_errors(exc)
        enriched: list[FieldLoadError] = []
        for fe in field_errors:
            location = resolve_source_location(fe.field_path, ctx, file_content)
            enriched.append(
                FieldLoadError(
                    field_path=fe.field_path,
                    message=fe.message,
                    input_value=fe.input_value,
                    location=location,
                ),
            )
        raise DatureConfigError(ctx.dataclass_name, enriched) from exc


def enrich_skipped_errors(
    err: DatureConfigError,
    skipped_fields: "dict[str, list[LoadMetadata]]",
) -> DatureConfigError:
    updated: list[DatureError] = []
    for exc in err.exceptions:
        if not isinstance(exc, FieldLoadError):
            if isinstance(exc, DatureError):
                updated.append(exc)
            continue

        if exc.message != "Missing required field":
            updated.append(exc)
            continue

        field_name = exc.field_path[-1] if exc.field_path else ""
        sources = skipped_fields.get(field_name)
        if sources is None:
            updated.append(exc)
            continue

        source_reprs = ", ".join(repr(meta) for meta in sources)
        updated.append(
            FieldLoadError(
                field_path=exc.field_path,
                message=f"Missing required field (invalid in: {source_reprs})",
                input_value=exc.input_value,
                location=exc.location,
            ),
        )
    return DatureConfigError(err.dataclass_name, updated)
