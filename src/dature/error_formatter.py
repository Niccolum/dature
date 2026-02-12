from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

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

from dature.errors import DatureConfigError, FieldError, FieldErrorInfo, SourceLocation
from dature.source_locators.ini_ import TablePathFinder
from dature.source_locators.json5_ import Json5PathFinder
from dature.source_locators.json_ import JsonPathFinder
from dature.source_locators.toml_ import TomlPathFinder
from dature.source_locators.yaml_ import YamlPathFinder

_PATH_FINDER_MAP: dict[
    str,
    type[YamlPathFinder | JsonPathFinder | Json5PathFinder | TomlPathFinder | TablePathFinder],
] = {
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
    if isinstance(exc, ValidationLoadError):
        return str(exc.msg)

    if isinstance(exc, ValueLoadError):
        return str(exc.msg)

    if isinstance(exc, TypeLoadError):
        return f"Expected {exc.expected_type.__name__}, got {type(exc.input_value).__name__}"

    if isinstance(exc, ExtraFieldsLoadError):
        field_names = ", ".join(sorted(exc.fields))
        return f"Unknown field(s): {field_names}"

    if isinstance(exc, BadVariantLoadError):
        return f"Invalid variant: {exc.input_value!r}"

    return str(exc)


def _walk_exception(
    exc: BaseException,
    parent_path: list[str],
    result: list[FieldErrorInfo],
) -> None:
    trail = list(get_trail(exc))
    current_path = parent_path + [str(elem) for elem in trail]

    if isinstance(exc, LoadExceptionGroup):
        for sub_exc in exc.exceptions:
            _walk_exception(sub_exc, current_path, result)
        return

    if isinstance(exc, NoRequiredFieldsLoadError):
        result.extend(
            FieldErrorInfo(
                field_path=[*current_path, field_name],
                message="Missing required field",
                input_value=None,
            )
            for field_name in sorted(exc.fields)
        )
        return

    result.append(
        FieldErrorInfo(
            field_path=current_path,
            message=_describe_error(exc),
            input_value=getattr(exc, "input_value", None),
        ),
    )


def extract_field_errors(exc: BaseException) -> list[FieldErrorInfo]:
    result: list[FieldErrorInfo] = []
    _walk_exception(exc, [], result)
    return result


def _read_file_content(file_path: Path | None) -> str | None:
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


def _find_env_line(content: str, var_name: str) -> tuple[int | None, str | None]:
    for i, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        if key == var_name:
            return i, stripped
    return None, None


def _resolve_file_location(
    field_path: list[str],
    loader_type: str,
    file_path: Path | None,
    file_content: str | None,
    prefix: str | None,
) -> SourceLocation:
    line_number = None
    line_content = None

    if file_content is not None and field_path:
        finder_class = _PATH_FINDER_MAP.get(loader_type)
        if finder_class is not None:
            search_path = _build_search_path(field_path, prefix)
            finder = finder_class(file_content)
            found_line = finder.find_line(search_path)
            if found_line != -1:
                line_number = found_line
                lines = file_content.splitlines()
                if 0 < line_number <= len(lines):
                    line_content = lines[line_number - 1].strip()

    return SourceLocation(
        source_type=loader_type,
        file_path=file_path,
        line_number=line_number,
        line_content=line_content,
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
            line_number=None,
            line_content=None,
            env_var_name=env_var_name,
        )

    if ctx.loader_type == "envfile":
        env_var_name = _build_env_var_name(field_path, ctx.prefix, ctx.split_symbols)
        line_number = None
        line_content = None
        if file_content is not None:
            line_number, line_content = _find_env_line(file_content, env_var_name)
        return SourceLocation(
            source_type="envfile",
            file_path=ctx.file_path,
            line_number=line_number,
            line_content=line_content,
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
        file_content = _read_file_content(ctx.file_path)
        field_errors = extract_field_errors(exc)
        enriched: list[FieldError] = []
        for fe in field_errors:
            location = resolve_source_location(fe.field_path, ctx, file_content)
            enriched.append(FieldError(error=fe, location=location))
        raise DatureConfigError(enriched, ctx.dataclass_name) from exc
