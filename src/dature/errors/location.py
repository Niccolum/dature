from contextlib import suppress
from dataclasses import dataclass, field, replace
from pathlib import Path

from dature.config import ErrorDisplayConfig, MaskingConfig
from dature.errors.loc_types import CaretSpan, LineRange, SourceLocation
from dature.masking.detection import canonical_secret_leaf_names
from dature.masking.masking import is_secret_path, mask_env_line
from dature.naming import canonical_name
from dature.sources.presentation import build_search_path, find_key_in_line
from dature.sources.protocol import FileSourceProtocol, SourceProtocol
from dature.type_aliases import JSONValue, NestedConflict, NestedConflicts


@dataclass(frozen=True, kw_only=True)
class ErrorContext:
    dataclass_name: str
    source: SourceProtocol
    masking: MaskingConfig
    """Explicit ``MaskingConfig`` for the effective ``masking_mode``, mask string, prefix/suffix,
    and heuristic thresholds."""
    error_display: ErrorDisplayConfig = field(default_factory=ErrorDisplayConfig)
    secret_paths: frozenset[str] = frozenset()
    nested_conflicts: NestedConflicts | None = None


@dataclass(frozen=True, slots=True)
class SourceContext:
    error_ctx: ErrorContext
    file_content: str | None
    loaded_data: "JSONValue"


@dataclass(frozen=True, slots=True)
class SkippedFieldSource:
    source: SourceProtocol
    error_ctx: ErrorContext
    file_content: str | None
    loaded_data: "JSONValue"


def read_file_content(file_path: Path | None, encoding: str | None = None) -> str | None:
    if file_path is None:
        return None

    with suppress(OSError, UnicodeDecodeError):
        return file_path.read_text(encoding=encoding)

    return None


def _ranges_overlap(a: LineRange, b: LineRange) -> bool:
    return a.start <= b.end and b.start <= a.end


def _canonicalize_index(line_index: dict[tuple[str, ...], LineRange]) -> dict[tuple[str, ...], LineRange]:
    return {tuple(canonical_name(part) for part in key): value for key, value in line_index.items()}


def _secret_overlaps_lines(
    *,
    canonical_line_index: dict[tuple[str, ...], LineRange],
    line_range: LineRange,
    secret_paths: frozenset[str],
    prefix: str | None,
) -> bool:
    for secret_path in secret_paths:
        search_path = build_search_path(secret_path.split("."), prefix)
        canonical_search_path = tuple(canonical_name(part) for part in search_path)
        secret_range = canonical_line_index.get(canonical_search_path)
        if secret_range is not None and _ranges_overlap(line_range, secret_range):
            return True
    return False


def _resolve_conflict(
    field_path: list[str],
    ctx: ErrorContext,
) -> NestedConflict | None:
    if ctx.nested_conflicts is None:
        return None
    field_key = field_path[0] if field_path else ""
    return ctx.nested_conflicts.get(field_key)


def _carets_for_key(content_lines: list[str], key: str) -> "list[CaretSpan] | None":
    """Point every line's caret at *key*'s own text, not at its value.

    Searches each line in order; the first line where the key is found gets its
    span, every other line gets an empty caret. Returns ``None`` if the key isn't
    found in any line, so the caller can fall back to the existing carets.
    """
    for index, line in enumerate(content_lines):
        found = find_key_in_line(line, key)
        if found is not None:
            return [found if i == index else CaretSpan(start=0, end=0) for i in range(len(content_lines))]
    return None


def _build_canonical_line_index(
    ctx: ErrorContext,
    file_content: str | None,
) -> dict[tuple[str, ...], LineRange] | None:
    if not (ctx.secret_paths and file_content is not None and isinstance(ctx.source, FileSourceProtocol)):
        return None
    line_index = ctx.source.build_line_index(file_content)
    if line_index is None:
        return None
    return _canonicalize_index(line_index)


def _should_mask_location(
    location: SourceLocation,
    *,
    is_secret: bool,
    ctx: ErrorContext,
    canonical_line_index: dict[tuple[str, ...], LineRange] | None,
) -> bool:
    if is_secret:
        return True
    if not (ctx.secret_paths and location.line_range is not None and canonical_line_index is not None):
        return False
    return _secret_overlaps_lines(
        canonical_line_index=canonical_line_index,
        line_range=location.line_range,
        secret_paths=ctx.secret_paths,
        prefix=ctx.source.prefix,
    )


def _mask_location(
    location: SourceLocation,
    ctx: ErrorContext,
    *,
    input_value: JSONValue,
    field_key: str | None,
    secret_leaf_names: frozenset[str],
) -> SourceLocation:
    masked_lines = (
        [
            mask_env_line(line, secret_leaf_names=secret_leaf_names, masking=ctx.masking)
            for line in location.line_content
        ]
        if location.line_content is not None
        else None
    )
    masked_carets: list[CaretSpan] | None = None
    if masked_lines is not None:
        masked_carets = ctx.source.compute_line_carets(masked_lines, input_value=input_value, field_key=field_key)
    return replace(
        location,
        line_content=masked_lines,
        line_carets=masked_carets,
        env_var_value=None,  # dropped on masking, regardless of what else changes
    )


def _mask_locations(
    locations: list[SourceLocation],
    ctx: ErrorContext,
    file_content: str | None,
    *,
    is_secret: bool,
    field_path: list[str],
    input_value: JSONValue,
) -> list[SourceLocation]:
    field_key = field_path[-1] if field_path else None
    canonical_line_index = _build_canonical_line_index(ctx, file_content)
    secret_leaf_names = canonical_secret_leaf_names(ctx.secret_paths)
    result: list[SourceLocation] = []
    for location in locations:
        should_mask = _should_mask_location(
            location,
            is_secret=is_secret,
            ctx=ctx,
            canonical_line_index=canonical_line_index,
        )
        if should_mask and (location.line_content is not None or location.env_var_value is not None):
            result.append(
                _mask_location(
                    location,
                    ctx,
                    input_value=input_value,
                    field_key=field_key,
                    secret_leaf_names=secret_leaf_names,
                ),
            )
        else:
            result.append(location)
    return result


def _repoint_carets_at_key(locations: list[SourceLocation], key: str) -> list[SourceLocation]:
    keyed: list[SourceLocation] = []
    for location in locations:
        if location.line_content is None:
            keyed.append(location)
            continue
        key_carets = _carets_for_key(location.line_content, key)
        keyed.append(location if key_carets is None else replace(location, line_carets=key_carets))
    return keyed


def resolve_source_location(
    field_path: list[str],
    ctx: ErrorContext,
    file_content: str | None,
    *,
    input_value: JSONValue = None,
    loaded_data: "JSONValue | None" = None,
    caret_key: str | None = None,
) -> list[SourceLocation]:
    """Resolve *field_path*'s source location(s), mask secrets, then re-point carets.

    Masking runs first because it can change line lengths (e.g. ``HOSTT=<REDACTED>``),
    and *caret_key* — when given — overrides the (possibly re-masked) caret to point
    at the key's own text within each line instead of at *input_value*, so it must
    run against the already-masked lines. Used for key-level diagnostics (e.g.
    strict-mode unknown-key reports) where the value itself is not the defect. Left
    as ``None`` for value-level diagnostics (the default).
    """
    is_secret = is_secret_path(field_path, secret_paths=ctx.secret_paths, masking=ctx.masking)
    conflict = _resolve_conflict(field_path, ctx)

    locations = ctx.source.resolve_location(
        field_path=field_path,
        nested_conflict=conflict,
        input_value=input_value,
        loaded_data=loaded_data,
    )

    masked = _mask_locations(
        locations,
        ctx,
        file_content,
        is_secret=is_secret,
        field_path=field_path,
        input_value=input_value,
    )

    if caret_key is None:
        return masked
    return _repoint_carets_at_key(masked, caret_key)
